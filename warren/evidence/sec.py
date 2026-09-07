from __future__ import annotations

import os
import re
from datetime import date

import httpx
import yfinance as yf

from ..cache import RedisJSONStore
from ..models import EvidenceBundle, FilingEvidence, MetricSnapshot, SecFactEvidence, SourceStatus


class SecFilingEvidenceProvider:
    """Official recent SEC filing metadata from data.sec.gov.

    SEC's submissions API does not require an API key, but automated clients are
    expected to send an identifying User-Agent. `SEC_USER_AGENT` can override
    the default application identifier.
    """

    TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
    COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    FACT_CONCEPTS = (
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenue", "USD"),
        ("Revenues", "Revenue", "USD"),
        ("NetIncomeLoss", "Net income", "USD"),
        ("OperatingIncomeLoss", "Operating income", "USD"),
        ("NetCashProvidedByUsedInOperatingActivities", "Operating cash flow", "USD"),
        ("PaymentsToAcquirePropertyPlantAndEquipment", "Capital expenditures", "USD"),
        ("Assets", "Total assets", "USD"),
        ("Liabilities", "Total liabilities", "USD"),
        ("StockholdersEquity", "Stockholders' equity", "USD"),
        ("ShareBasedCompensation", "Stock-based compensation", "USD"),
        ("CommonStockSharesOutstanding", "Common shares outstanding", "shares"),
    )
    FORMS = {
        "10-K",
        "10-K/A",
        "10-Q",
        "10-Q/A",
        "8-K",
        "8-K/A",
        "20-F",
        "40-F",
        "6-K",
    }

    def __init__(self, max_filings: int = 8, user_agent: str | None = None, timeout: float = 20.0):
        self.max_filings = max(0, max_filings)
        configured_agent = user_agent or os.getenv("SEC_USER_AGENT")
        self.user_agent = (
            configured_agent
            if configured_agent and "example.com" not in configured_agent.lower() and "@" in configured_agent
            else "AskWarren/0.8 drmaganti@users.noreply.github.com"
        )
        self.timeout = timeout
        self._ticker_map: dict[str, tuple[int, str]] | None = None
        self.relay_store = RedisJSONStore.from_env()

    @staticmethod
    def _relay_key(symbol: str) -> str:
        return f"ask-warren:v1:sec-relay:{symbol}:fresh"

    @staticmethod
    def _relay_queue_key() -> str:
        return "ask-warren:v1:sec-relay:queue"

    def _queue_relay(self, symbol: str) -> None:
        if self.relay_store is not None:
            self.relay_store.sadd(self._relay_queue_key(), symbol)

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
        )

    @staticmethod
    def _resolve_cik_from_yahoo(symbol: str) -> int | None:
        """Resolve a CIK without the SEC ticker-map host when that host blocks Vercel."""
        try:
            rows = yf.Ticker(symbol).sec_filings or []
        except Exception:
            return None
        for row in rows:
            match = re.search(r"/([0-9]{10}-[0-9]{2}-[0-9]{6})_([0-9]+)$", str(row.get("edgarUrl") or ""))
            if match:
                return int(match.group(2))
        return None

    def _load_ticker_map(self, client: httpx.Client) -> dict[str, tuple[int, str]]:
        if self._ticker_map is not None:
            return self._ticker_map
        response = client.get(self.TICKER_MAP_URL)
        response.raise_for_status()
        payload = response.json()
        mapping: dict[str, tuple[int, str]] = {}
        for record in payload.values():
            ticker = str(record.get("ticker") or "").strip().upper()
            cik = record.get("cik_str")
            if not ticker or cik is None:
                continue
            mapping[ticker] = (int(cik), str(record.get("title") or ticker))
        self._ticker_map = mapping
        return mapping

    def _yahoo_filing_mirror(self, symbol: str) -> EvidenceBundle:
        """Fallback to Yahoo's byte-for-byte SEC filing mirror when EDGAR blocks a serverless IP."""
        bundle = EvidenceBundle()
        rows = yf.Ticker(symbol).sec_filings or []
        cik: int | None = None
        for row in rows:
            form = str(row.get("type") or "")
            if form not in self.FORMS:
                continue
            edgar_url = str(row.get("edgarUrl") or "")
            accession_match = re.search(r"/([0-9]{10}-[0-9]{2}-[0-9]{6})_([0-9]+)$", edgar_url)
            accession = accession_match.group(1) if accession_match else None
            if accession_match:
                cik = int(accession_match.group(2))
            exhibits = row.get("exhibits") or {}
            document_url = exhibits.get(form) or next(iter(exhibits.values()), None)
            if not document_url:
                continue
            bundle.filings.append(FilingEvidence(
                form=form,
                filed_at=row.get("date") if isinstance(row.get("date"), date) else self._parse_date(str(row.get("date") or "")),
                accession_number=accession,
                primary_document=str(document_url).rsplit("/", 1)[-1],
                url=str(document_url),
            ))
        essentials: list[FilingEvidence] = []
        family_counts = {"annual": 0, "quarterly": 0}
        for filing in bundle.filings:
            family = "annual" if filing.form in {"10-K", "20-F", "40-F"} else "quarterly" if filing.form == "10-Q" else None
            if family and family_counts[family] < 2:
                essentials.append(filing)
                family_counts[family] += 1
        chosen = essentials + [filing for filing in bundle.filings if filing not in essentials]
        bundle.filings = sorted(
            chosen[: self.max_filings], key=lambda filing: filing.filed_at or date.min, reverse=True
        )
        bundle.metadata.update({"sec_cik": cik, "sec_filing_transport": "Yahoo Finance SEC filing mirror"})
        bundle.source_status.append(SourceStatus(
            source="SEC EDGAR",
            status="partial" if bundle.filings else "unavailable",
            detail=(
                f"EDGAR blocked the serverless request; {len(bundle.filings)} SEC filing documents were recovered from Yahoo Finance's filing mirror."
                if bundle.filings else "EDGAR blocked the serverless request and no mirrored filing documents were available."
            ),
        ))
        return bundle

    @staticmethod
    def _parse_date(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    @classmethod
    def _extract_company_facts(cls, payload: dict, cik: int) -> list[SecFactEvidence]:
        us_gaap = ((payload.get("facts") or {}).get("us-gaap") or {})
        results: list[SecFactEvidence] = []
        seen_labels: set[str] = set()
        for concept, label, preferred_unit in cls.FACT_CONCEPTS:
            if label in seen_labels:
                continue
            fact = us_gaap.get(concept) or {}
            unit_rows = (fact.get("units") or {}).get(preferred_unit) or []
            eligible = [row for row in unit_rows if row.get("form") in {"10-K", "10-Q"} and row.get("val") is not None]
            if not eligible:
                continue
            row = max(eligible, key=lambda item: (str(item.get("filed") or ""), str(item.get("end") or "")))
            accession = str(row.get("accn") or "")
            accession_path = accession.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_path}/" if accession_path else None
            results.append(SecFactEvidence(
                concept=concept,
                label=label,
                value=float(row["val"]),
                unit=preferred_unit,
                period_end=cls._parse_date(row.get("end")),
                filed_at=cls._parse_date(row.get("filed")),
                fiscal_period=row.get("fp"),
                form=row.get("form"),
                accession_number=accession or None,
                url=url,
            ))
            seen_labels.add(label)
        return results

    def _official_bundle(
        self,
        cik: int,
        sec_name: str,
        submissions: dict,
        company_facts: dict | None,
        *,
        transport: str,
    ) -> EvidenceBundle:
        bundle = EvidenceBundle()
        if company_facts:
            bundle.sec_facts = self._extract_company_facts(company_facts, cik)
        recent = (submissions.get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or []
        filed = recent.get("filingDate") or []
        accessions = recent.get("accessionNumber") or []
        documents = recent.get("primaryDocument") or []
        total = min(len(forms), len(filed), len(accessions), len(documents))
        for idx in range(total):
            form = str(forms[idx] or "")
            if form not in self.FORMS:
                continue
            accession = str(accessions[idx] or "")
            document = str(documents[idx] or "")
            accession_path = accession.replace("-", "")
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_path}/{document}"
                if accession_path and document else None
            )
            bundle.filings.append(FilingEvidence(
                form=form,
                filed_at=self._parse_date(str(filed[idx] or "")),
                accession_number=accession or None,
                primary_document=document or None,
                url=url,
            ))
            if len(bundle.filings) >= self.max_filings:
                break
        bundle.metadata.update({"sec_cik": cik, "sec_company_name": sec_name, "sec_filing_transport": transport})
        bundle.source_status.append(SourceStatus(
            source="SEC EDGAR",
            status="ok" if bundle.filings and bundle.sec_facts else "partial",
            detail=f"{len(bundle.filings)} recent material filings and {len(bundle.sec_facts)} latest XBRL facts returned via {transport}",
        ))
        return bundle

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        symbol = ticker.strip().upper()
        bundle = EvidenceBundle()

        if symbol.endswith(".TO"):
            bundle.source_status.append(
                SourceStatus(
                    source="SEC EDGAR",
                    status="unavailable",
                    detail="TSX symbol; Warren does not guess a US cross-listing for SEC evidence.",
                )
            )
            return bundle

        if self.relay_store is not None:
            relayed = self.relay_store.get(self._relay_key(symbol))
            if relayed:
                try:
                    return self._official_bundle(
                        int(relayed["cik"]),
                        str(relayed.get("sec_name") or metrics.company_name or symbol),
                        relayed["submissions"],
                        relayed.get("company_facts"),
                        transport="official EDGAR scheduled relay",
                    )
                except (KeyError, TypeError, ValueError):
                    pass

        with self._client() as client:
            try:
                mapping = self._load_ticker_map(client)
            except httpx.HTTPError:
                mapping = {}
            company = mapping.get(symbol)
            if company is None:
                fallback_cik = self._resolve_cik_from_yahoo(symbol)
                if fallback_cik is not None:
                    company = (fallback_cik, metrics.company_name or symbol)
            if company is None:
                self._queue_relay(symbol)
                bundle.source_status.append(
                    SourceStatus(
                        source="SEC EDGAR",
                        status="unavailable",
                        detail=f"No exact SEC ticker-to-CIK mapping for {symbol}.",
                    )
                )
                return bundle

            cik, sec_name = company
            try:
                response = client.get(self.SUBMISSIONS_URL.format(cik=cik))
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError, TypeError):
                self._queue_relay(symbol)
                return self._yahoo_filing_mirror(symbol)
            facts_payload: dict | None = None
            try:
                facts_response = client.get(self.COMPANY_FACTS_URL.format(cik=cik))
                facts_response.raise_for_status()
                facts_payload = facts_response.json()
            except (httpx.HTTPError, ValueError, TypeError):
                facts_payload = None

        return self._official_bundle(cik, sec_name, payload, facts_payload, transport="direct EDGAR API")
