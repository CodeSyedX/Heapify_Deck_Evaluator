# Evaluation pipeline

Status: accepted · 2026-10-01. Evidence for these choices is in [the evaluation-engine research](../research/02-evaluation-engine.md).

## Principles

1. Deck content is untrusted data. It is parsed in a constrained subprocess, sanitised, and passed to models only inside a delimited data block.
2. The model supplies evidence and a level; code verifies the evidence and computes every number shown to a user.
3. A stored evaluation can always be traced to its inputs: deck hash, parser version, rubric version, prompt version, model id.
4. The pipeline ranks and explains. It never rejects a deck on its own.

## Steps

| Step | What it does | Fails the run when |
|---|---|---|
| `scanning` | Sniffs magic bytes, checks size, zip limits and macro content; malware scan through the `MalwareScanner` port | File type not allowed, limits exceeded, malware found (`quarantined`) |
| `parsing` | Produces the canonical `DeckDocument` and a PNG per slide | File is corrupt, encrypted, or exceeds slide limit |
| `structure_check` | Compares the deck with the rubric's template: slide count, required sections | Never; produces a report |
| `integrity_check` | Detects hidden, tiny, off-canvas and invisible-character text and evaluator-directed phrasing | Never; produces flags |
| `scoring` | Scores each criterion (protocol below) | Provider errors persist beyond retries |
| `similarity` | Embeds the deck and compares it with other submissions in the same event | Never; a failure is recorded and the run continues |
| `reporting` | Aggregates totals, bands, confidence and feedback; captures the credit | — |

## Canonical deck

Every later stage reads `DeckDocument`, never the uploaded file.

```
DeckDocument
  source_format: pdf | pptx      parser_version      sha256      slide_count
  slides[]:
    index (1-based)   title   blocks[] (text, kind, font_size, visible)
    notes   tables[]   image_count   text_source: native | ocr | none
  removed_characters: count of stripped invisible characters
```

Parsing uses python-pptx for PPTX and pypdfium2 with pdfplumber for PDF. PPTX is rendered to images through LibreOffice headless when it is installed; rendering is optional and its absence lowers nothing but the hidden-text check's coverage. Libraries under AGPL or GPL (PyMuPDF, Poppler) are not used.

## Rubric

A rubric version is immutable once published. Scores are comparable only within one version.

```
RubricDefinition
  scale: {min: 0, max: 5}
  criteria[]: key, name, description, weight, evidence_guidance,
              levels[]: {score, descriptor}        one per integer on the scale
  template (optional): max_slides, accepted_formats,
              sections[]: {key, title, required, keywords[]}
```

The SIH preset carries the nine official criteria with equal weights, because no official weights are published, and the six-section idea template.

## Scoring protocol

For each criterion, independently:

1. **Sample.** Call the judge model `samples` times (default 3). The prompt holds the instructions, then the deck as a delimited data block, then the criterion and its level descriptors last, so the deck prefix is cached across calls.
2. **Structured output.** Fields in this order: `evidence[] {slide, quote, supports}`, `missing[]`, `level_reasoning`, `score`, `abstain`. Evidence comes before the score so the score is conditioned on it.
3. **Verify.** Each quote is matched against the text of the slide it cites, after normalisation. A sample with no verified evidence and a score above the minimum is discarded and re-run once.
4. **Aggregate.** Criterion score is the mean of valid samples; spread is their range.
5. **Agreement.** `high` when all samples agree, `medium` when the range is 1, `low` when it is 2 or more, evidence is unverified, the slide text came from OCR, or the deck has a high-severity integrity flag.

The total is the weighted mean of criterion scores scaled to 0–100, computed in code. The band is the total recomputed from each criterion's lowest and highest sample.

Sampling temperature is not relied on for reproducibility: some current models reject non-default sampling parameters. Reproducibility comes from stored raw responses.

## Integrity flags

Flags are neutral findings for the organiser: kind, severity (`info`, `review`, `high`), slide, excerpt. Hidden text has innocent causes, so a flag never changes a score by itself. Scoring always runs on sanitised content with hidden text excluded.

## Similarity

Each run stores one deck-level vector. Within an event, pairs are compared on cosine similarity and on lexical overlap (shingle Jaccard). High semantic similarity with low lexical overlap is a shared theme; high lexical overlap is copied text and worth a human look. Results are labelled "similar submissions", never plagiarism. There is no cross-tenant comparison.

The embedding model sits behind an `Embedder` port. The production adapter is `BAAI/bge-m3` (MIT, 1024 dimensions); a deterministic hashing adapter serves tests and machines without the model.

## Model providers

All model calls go through the `LLMGateway` port, which records each call in `llm_calls`. Adapters: Anthropic, OpenAI-compatible (OpenAI, Groq and others), and a deterministic fake for tests and keyless local runs. Only paid API tiers are suitable, because free tiers may use submitted content for product improvement.

A run stores a snapshot of its scoring profile (provider, model, samples). Decks in one event are scored under one profile; changing it means re-scoring the event.

## Measuring the scorer

`evals/` holds the harness: a gold set of human-scored decks, injection canaries and verbosity pairs, and a runner that reports agreement per criterion (quadratic-weighted kappa, Spearman, mean absolute and signed error). The harness ships with synthetic fixtures; real human-scored decks have to be collected before any agreement figure can be published.
