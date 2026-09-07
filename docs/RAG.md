# SEC Filing RAG

Ask Warren uses retrieval-augmented generation (RAG) to bring relevant narrative evidence from SEC filings into Deep analysis. The first production use case is deliberately narrow: identify material passages and changes across the latest and prior annual and quarterly filings.

This makes Deep analysis better because the model no longer has to reason only from ratios, filing metadata and recent headlines. It can examine management's own disclosures about risks, demand, competition, margins, liquidity, capital allocation, strategy and outlook.

## What RAG adds

Structured data answers questions such as:

- What was revenue?
- How did margins or cash flow change?
- What valuation does the current price imply?

Filing narrative answers different questions:

- Why did the numbers change?
- Which risks are new, removed or receiving more emphasis?
- Did management's language about demand, competition or liquidity become more cautious?
- Are strategic priorities or capital-allocation plans changing?

RAG retrieves the passages most relevant to those questions and includes them in the same evidence packet used by the Bull, Bear, Risk and Final evaluators.

## Why this improves Ask Warren

### 1. It adds primary-document context

Headlines and market data are useful but compressed. Filing passages provide the company's detailed, legally reviewed description of its business and risks. Ask Warren can therefore connect quantitative movement to disclosed business drivers instead of inventing an explanation.

### 2. It supports filing-to-filing comparison

The corpus contains the latest and prior annual and quarterly filings. Retrieving across comparable periods makes it possible to surface changes in language and emphasis, not merely summarize the newest document in isolation.

### 3. It strengthens both sides of the investment case

The Bull analyst can retrieve evidence of improving demand, strategic progress or financial flexibility. The Bear and Risk reviewers can retrieve concentration, liquidity, regulatory, competitive or execution concerns. All perspectives work from the same source packet, reducing one-sided narrative generation.

### 4. It improves traceability

Retrieved passages retain filing type, filing date, accession information and a source URL. The response records whether full text was retrieved and which retrieval path was used. This makes important claims easier to inspect and challenge.

### 5. It reduces unsupported LLM inference

Gemini receives a bounded set of relevant passages rather than being asked to recall a filing from model memory. The evidence router labels retrieval depth and source authority, while missing or degraded sources reduce confidence instead of disappearing silently.

### 6. It remains cost-aware

Upstash performs hosted dense and sparse embedding, so Ask Warren does not require a separate embedding API or key. Only a bounded set of material chunks is stored. SEC evidence is cached for six hours, each ticker corpus is replaced on refresh, and inactive ticker corpora are pruned after 30 days.

## Retrieval flow

```text
Latest + prior 10-K / 10-Q filings
                 |
        extract visible filing text
                 |
      split into bounded passages
                 |
 rank for material business-change terms
                 |
 replace the ticker's vector corpus
                 |
 hybrid retrieval: semantic + exact terms
                 |
 evidence router assigns provenance and depth
                 |
    Bull / Bear / Risk / Final synthesis
```

The hybrid index combines two useful behaviors:

- Dense retrieval finds conceptually related passages even when the filing uses different wording.
- BM25 sparse retrieval preserves exact matches for financial, legal and company-specific terms.

## Scope and safeguards

RAG is used only for narrative filing text. It is not used to obtain or calculate prices, financial ratios, technical indicators, analyst estimates, macroeconomic observations or DCF values. Those remain structured inputs and deterministic calculations.

The implementation applies the following safeguards:

- At most four comparable filings are selected: up to two annual and two quarterly reports.
- At most 12 material passages are retained per filing.
- The ticker's existing vectors are replaced rather than appended on refresh.
- Inactive ticker data is marked for expiry and pruned after 30 days.
- Retrieved passages remain attached to their filing metadata and URL.
- Retrieval failures are reported in `source_status` and `evidence.metadata.sec_rag`.
- A temporary vector-service failure does not discard already-downloaded evidence; Ask Warren returns the same bounded, materiality-ranked passages locally and reports that fallback.
- Ask Warren uses Yahoo Finance's SEC-document mirror to retrieve filing documents reliably from serverless environments and records that transport explicitly.

## What RAG does not guarantee

RAG improves grounding; it does not make the analysis infallible.

- A relevant passage may fall outside the bounded chunk set.
- Retrieval relevance does not prove that an interpretation is correct.
- Filing disclosures represent management's reporting and may omit developments that occurred after the filing date.
- Mirrored documents and temporary fallbacks may have different source-authority labels from issuer-hosted documents.
- The current version retrieves relevant passages but does not yet produce a deterministic, section-by-section redline of every filing change.

For these reasons, Ask Warren exposes provenance, freshness, source status and confidence. RAG evidence should inform an investment decision, not replace review of the underlying filing.

## Operational behavior

RAG is enabled when these server-side variables are present:

```text
UPSTASH_VECTOR_REST_URL
UPSTASH_VECTOR_REST_TOKEN
```

The `/health` response reports `"rag": "sec-filings-upstash-vector"` when configured. Deep responses expose:

- indexed filing and chunk counts;
- retrieved passage count;
- comparison strategy;
- active retrieval backend;
- any vector warning or fallback;
- source-level status and details.

## Expected product outcome

The intended outcome is not a longer stock report. It is a better-supported one: more primary evidence, clearer explanations for changes in the numbers, stronger adversarial analysis, and a visible trail from an important conclusion back to the filing passage that informed it.

The next major enhancement is deterministic section-level change extraction. That will make additions, removals and shifts in filing language explicit before the LLM evaluates their investment significance.
