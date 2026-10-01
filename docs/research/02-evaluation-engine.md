# 02 — Evaluation Engine: Research and Recommended Design

Research date: 2026-10-01. Every factual claim carries a source link. Items I could not confirm from a primary source are tagged **[unverified]**. Cost figures tagged **[estimate]** are my own arithmetic from verified list prices and stated assumptions.

---

## Recommended design

1. **Parsing stack (all permissive licences):** `python-pptx` (MIT) custom extractor for PPTX; `pypdfium2` (Apache-2.0/BSD-3) for PDF text and rendering plus `pdfplumber` (MIT) for per-character attributes and tables; Docling (MIT) as the fallback for scanned or layout-heavy PDFs. **Do not ship PyMuPDF (AGPL), Poppler/`pdf2image` (GPL) or Surya OCR weights (commercial licence required).**
2. **One canonical `Deck` JSON** per upload: `slides[] {index, title, body_blocks[], notes, tables[], charts[], images[] {alt_text}, hidden, text_source: native|ocr}` plus a rendered PNG per slide. Every later stage reads this, never the raw file.
3. **Render every deck to images** (PPTX -> LibreOffice headless -> PDF -> pypdfium2 -> PNG at about 1280x720). Used for OCR fallback, hidden-text detection and optional vision scoring.
4. **Treat uploads as hostile:** magic-byte and extension allow-list (`.pptx`, `.pdf` only; reject `.pptm`/`.ppt`), size cap 50 MB, 60 slides/pages, zip limits (entry count, uncompressed size, ratio), hardened XML parser, and all parsing/rendering in a no-network, read-only, resource-capped sandbox (gVisor or nsjail) with a hard timeout.
5. **Score one criterion per call, never all axes in one JSON.** Each call: (a) extract verbatim evidence quotes with slide numbers, (b) pick the matching anchored level, (c) emit score. Enforce with provider-native JSON-schema structured output.
6. **Scale: integer 0–5 per criterion with written anchors for every level** (0 = not addressed). Compute the weighted 0–100 total in code, not in the model.
7. **Verify evidence deterministically:** fuzzy-match each quote against the cited slide's text; a criterion whose quotes fail verification is re-run once, then marked "unverified evidence" and routed to human review.
8. **Three samples per criterion, report the mean and the spread.** If the range is 2 or more points, or the deck sits near the organiser's cut line, escalate to a second model family. Use a panel as an escalation path, not as the default.
9. **Calibrate per rubric against a human gold set** (50–100 decks, two human raters each). Gate releases on quadratic-weighted kappa and Krippendorff's alpha (ordinal) per criterion, plus Spearman, MAE and mean signed error (leniency).
10. **Show users a band, not a point:** score, plus/minus spread, and an agreement label (high/medium/low). Organisers get rank bands and a "needs human review" queue; the product never auto-rejects.
11. **Prompt-injection defence in layers:** sanitise (strip Unicode tag and zero-width characters), detect hidden text by diffing the text layer against OCR of the rendered slide, wrap deck content in delimited data blocks, constrain output by schema, and run a separate injection classifier. Surface hits to organisers as a neutral "integrity flag" with the offending text and location.
12. **Vision is opt-in per rubric:** run one extra vision pass only when the rubric has a design/visual-clarity criterion, the deck is image-only, or charts carry the argument. Otherwise text only.
13. **Provider-agnostic `JudgeClient` interface** with three tiers: Economy (`gpt-6-luna` or Groq `openai/gpt-oss-120b`), Standard (`claude-sonnet-5-5`, `gpt-6.1-sol` or `gemini-3.8-flash`), Escalation (second family from the Standard list). Paid tiers only; no free tiers (Gemini free tier content is used for product improvement).
14. **Originality:** `BAAI/bge-m3` (MIT, 1024-d) self-hosted, per-slide and whole-deck embeddings in pgvector with an HNSW cosine index, combined with a lexical overlap score. Present as "similar prior work" with side-by-side passages; never a plagiarism verdict. Build the corpus from customer-supplied past submissions and API-licensed sources, not scraping.
15. **Every evaluation row stores** provider, exact model id, prompt version hash, rubric version, parser version, deck content hash, sampling parameters, seed where supported, raw responses and token usage. A nightly sentinel set detects silent model drift; a CI gold-set run gates every prompt or model change.

---

## 1. Deck parsing

### 1.1 Library comparison

| Tool | Version checked | Licence | Verdict for closed-source SaaS |
|---|---|---|---|
| python-pptx | 1.0.2 | MIT | **Use** for PPTX. Depends on lxml, Pillow, XlsxWriter. [PyPI](https://pypi.org/project/python-pptx/) |
| pypdf | 6.19.0 | BSD-3-Clause | OK. Good for metadata, encryption checks, page counts. Weaker layout fidelity. [PyPI](https://pypi.org/project/pypdf/) |
| pdfplumber | 0.11.10 | MIT | **Use** for per-character font size/colour and tables. Built on pdfminer.six; README says it "works best on machine-generated, rather than scanned, PDFs". [PyPI](https://pypi.org/project/pdfplumber/) |
| pypdfium2 | 5.13.0 | Apache-2.0 or BSD-3-Clause (PDFium is BSD-style) | **Use** for rendering and fast text. [PyPI](https://pypi.org/project/pypdfium2/) |
| PyMuPDF | 1.28.2 | **AGPL or commercial (Artifex)** | **Do not use** without buying a commercial licence. AGPL's network clause reaches SaaS. [PyMuPDF docs](https://pymupdf.readthedocs.io/en/latest/about.html) |
| pdf2image | n/a | MIT wrapper around **Poppler (GPL)** | **Avoid.** Replace with pypdfium2. [Haystack issue](https://github.com/deepset-ai/haystack/issues/9320), [Poppler](https://en.wikipedia.org/wiki/Poppler_(software)) |
| Docling | 2.131.0 | MIT code; bundled models have their own licences | **Use as fallback** for scanned and complex-layout PDFs. Accepts PDF, PPTX, PNG/JPEG/TIFF/BMP/WEBP; OCR backends include Tesseract, RapidOCR, SuryaOCR. [PyPI](https://pypi.org/project/docling/), [formats](https://docling-project.github.io/docling/usage/supported_formats/), [GitHub](https://github.com/docling-project/docling) |
| Unstructured (OSS) | 0.27.10 | Apache-2.0 | Licence is fine. Heavy dependency tree and element-oriented output rather than slide-oriented; no advantage over python-pptx for decks. [PyPI](https://pypi.org/project/unstructured/) |
| MarkItDown | 0.1.8 | MIT | **Not for the core pipeline.** Output is Markdown "meant to be consumed by text analysis tools", so slide structure is flattened, and the README says "Do not pass untrusted input directly to MarkItDown". [README](https://github.com/microsoft/markitdown), [PyPI](https://pypi.org/project/markitdown/) |
| LibreOffice headless | n/a | MPL-2.0 | **Use** for PPTX -> PDF, as a separate sandboxed process (no linking). [Licences](https://www.libreoffice.org/licenses/) |

Notes on verification gaps:
- Release dates for Docling and Unstructured returned by the PyPI JSON summary looked inconsistent with the version numbers, so treat dates as **[unverified]**; versions and licences are as reported by PyPI.
- Whether Docling's PPTX backend emits speaker notes in the current release is **[unverified]**. A secondary source says it does; the original request is tracked in [docling issue #473](https://github.com/docling-project/docling/issues/473). This is one reason to own the PPTX extractor.
- Docling's default model licences should be checked individually before bundling; the repo states the codebase is MIT and that model licences are in the original packages ([GitHub](https://github.com/docling-project/docling)).

### 1.2 Recommended stack

**PPTX path**
1. Validate and unzip safely (section 1.4).
2. `python-pptx` extractor producing per slide: title placeholder, body text blocks with shape geometry, `notes_slide` text, tables (cells), charts (type, categories, series values), picture alt text, hidden-slide flag, and document core properties.
3. Reading order: sort shapes by (top, left) with a tolerance band, title first. Slide XML z-order is draw order, not reading order, so geometric sorting is the practical default. **[engineering judgement]**
4. Render: LibreOffice headless to PDF, then pypdfium2 to PNG.

**PDF path**
1. `pypdf` for page count, encryption and metadata.
2. `pdfplumber` for characters with size and colour, plus table detection; `pypdfium2` for rendering.
3. Title heuristic: largest font block in the top third of the page. **[engineering judgement]**
4. If a page has little or no text layer, send it to the OCR path.

**Scanned or image-only decks**
- Detect: fewer than about 20 extractable characters on a page that renders with visible content.
- OCR options with clean licences: Tesseract and RapidOCR are Apache-2.0 ([Tesseract](https://en.wikipedia.org/wiki/Tesseract_(software)), [RapidOCR](https://github.com/rapidai/rapidocr)). Surya's weights require a commercial licence above a revenue threshold ([surya-ocr PyPI](https://pypi.org/project/surya-ocr/)), so exclude it.
- Recommended: Docling with RapidOCR for bulk; for decks where OCR confidence is low, transcribe slide images with the cheap vision model instead. Mark `text_source: "ocr"` so the scorer and the UI can lower confidence.

### 1.3 Rendering for vision input

- PPTX: LibreOffice headless is the only practical open renderer. Fidelity differs from PowerPoint when fonts are missing; install a broad font set in the sandbox image and tell users that PDF upload gives exact fidelity. **[engineering judgement]**
- PDF: pypdfium2 directly.
- Target about 1280x720. On Claude this costs `ceil(w/28) * ceil(h/28)` visual tokens, about 1,196 per slide at that size ([Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)).

### 1.4 Security handling of untrusted uploads

| Threat | Control |
|---|---|
| Zip bomb in OOXML | Before parsing, iterate `ZipFile.infolist()`: cap entry count, per-entry and total uncompressed size, and compression ratio; reject nested archives. A reported case shows a 56 KB `.docx` costing 153 s of CPU when parsers had no caps ([issue](https://github.com/PersonalClaw/PersonalClaw/issues/2747)). |
| XXE / entity expansion | OOXML is user-controlled XML. Use an lxml parser with `resolve_entities=False, no_network=True, load_dtd=False` ([CodeQL guidance](https://codeql.github.com/codeql-query-help/python/py-xxe/)). python-pptx reportedly sets `resolve_entities=False` already; confirm in the pinned version **[unverified]**. Any XML you parse yourself must use the hardened parser. |
| Macros and embedded OLE | Reject `.pptm`/`.ppt`/`.potm` by magic bytes and content types; reject packages containing `vbaProject.bin`; never execute or extract embedded objects. |
| Malicious PDFs | PDFium and pdfminer are parsers with CVE histories; run them only inside the sandbox. Reject encrypted PDFs. Ignore JavaScript, embedded files and launch actions. |
| LibreOffice exploitation | Real server-side issues exist: CVE-2024-12425 and CVE-2024-12426 allowed file writes and environment-variable exfiltration in headless conversion scenarios ([Codean Labs](https://codeanlabs.com/2025/02/exploiting-libreoffice-cve-2024-12425-and-cve-2024-12426/)). Run as unprivileged user, macros disabled, no network, fresh profile per job, hard timeout, patched build. [clippyshot](https://github.com/wmetcalf/clippyshot) is a reference design using nsjail/gVisor. |
| External links in decks | No network egress from the sandbox prevents remote image and OLE link fetches (also blocks SSRF). |
| Resource exhaustion | Per-job CPU, memory, wall-clock and output-size limits; kill and mark `parse_failed`. |
| Stored files | Store originals in object storage under a random key, never serve them from the app origin, and scan with ClamAV as defence in depth. **[engineering judgement]** |

Suggested limits: 50 MB file, 60 slides, 500 zip entries, 500 MB total uncompressed, ratio 100:1, 60 s parse, 120 s render. **[engineering judgement]**

---

## 2. LLM-as-judge reliability

### 2.1 What the research says

| Design question | Finding | Source |
|---|---|---|
| Per-criterion vs all-at-once | Analytic, per-criterion evaluation prevents criterion conflation and halo effects and makes per-criterion reliability measurable. | [Autorubric, Rao and Callison-Burch 2026](https://arxiv.org/abs/2603.00077) |
| Clear criteria | Evaluation criteria are the most important factor for reliability. | [Yamauchi et al. 2025](https://arxiv.org/abs/2506.13639) |
| Evidence before score | RULERS locks the rubric, requires structured checklist decisions with extractive quote verification, then post-hoc calibrates; it reports stronger human agreement in most settings across four benchmarks. | [RULERS 2026](https://arxiv.org/abs/2601.08654) |
| Chain-of-thought | CoT "offers minimal gains when clear evaluation criteria are present". Keep reasoning short and evidence-led. | [Yamauchi et al. 2025](https://arxiv.org/abs/2506.13639) |
| Sampling and aggregation | Non-deterministic sampling with mean aggregation aligns better with humans than a single greedy run. | [Yamauchi et al. 2025](https://arxiv.org/abs/2506.13639) |
| Temperature | Higher temperature lowers consistency and raises format errors; it is a task-dependent choice. Temperature 0 is necessary but not sufficient for reproducibility. | [Li et al. 2026](https://arxiv.org/abs/2603.28304), [2606.26185](https://arxiv.org/html/2606.26185v1) |
| Scale | Human–LLM alignment was highest on 0–5 and weakest on 0–10 across six benchmarks. | [Li et al. 2026](https://arxiv.org/abs/2601.03444) |
| Panels | A panel of three smaller models from different families correlated better with humans than one large judge at about one seventh of the cost. | [Verga et al. 2024, PoLL](https://arxiv.org/abs/2404.18796) |
| Panels, the caveat | Nine frontier judges from seven families gave only about two independent votes; the best single judge matched or beat the panel. | [Kohli 2026](https://arxiv.org/abs/2605.29800) |
| No universal recipe | Autorubric found configuration effects that "do not support a universal mitigation stack". You must measure on your own data. | [Autorubric](https://arxiv.org/abs/2603.00077) |

### 2.2 Known biases and what to do about each

| Bias | Evidence | Mitigation in this product |
|---|---|---|
| Verbosity | GPT-4 preferred longer answers more than humans did. | Anchors describe substance, not volume; log tokens per deck and test score-vs-length correlation on the gold set. [Saito et al. 2023](https://arxiv.org/abs/2310.10076) |
| Leniency and score compression | LLM reviewers gave rejected ICLR papers mean scores well above the human mean and avoided extremes; LLM reviewers showed over 95% acceptance in many models. | Anchored levels, few-shot examples at low and high levels, track mean signed error, post-hoc calibration. [Publications 2026](https://doi.org/10.3390/publications14030055), [Keuper 2025](https://arxiv.org/abs/2509.10248), [central tendency](https://arxiv.org/pdf/2605.16386) |
| Position | Listed among 12 quantified judge biases. | Mostly a pairwise problem; for us, randomise criterion call order and keep slide order fixed. [CALM, Ye et al. 2024](https://arxiv.org/abs/2410.02736) |
| Self-preference | Judges recognise and favour their own generations. | Decks may be LLM-written; a second model family on escalation limits single-family bias. [Panickssery et al. 2024](https://proceedings.neurips.cc/paper_files/paper/2024/file/7f1f0218e45f5414c79c0679633e47bc-Paper-Conference.pdf) |
| Demographic subgroup differences | Pooled reliability can hide subgroup differences in alignment. | Redact team and member names before scoring; audit by language and region where data allows. [Li et al. 2026](https://arxiv.org/abs/2601.03444) |

### 2.3 Recommended scoring protocol

**Rubric compilation (once per rubric version).** Each criterion gets: definition, weight, what counts as evidence, and a written descriptor for each level 0–5. Organiser-authored rubrics are compiled into this locked form and versioned; scoring always references an immutable rubric version (the RULERS "locking" idea).

**Per criterion call (schema-constrained):**
```json
{
  "criterion_id": "feasibility",
  "evidence": [{"slide": 7, "quote": "verbatim text", "supports": "positive|negative"}],
  "missing": ["what the rubric expects that the deck lacks"],
  "level_reasoning": "max 3 sentences comparing evidence to anchors",
  "score": 3,
  "abstain": false
}
```
Field order matters: evidence first, score last, so the score is conditioned on the evidence.

**Steps**
1. Deterministic structure check against the event template (required sections, slide count). No LLM needed for most of it.
2. For each criterion, run 3 samples. Do not rely on temperature 0: current Claude Opus and Sonnet models reject non-default sampling parameters ([claude-api skill reference, model table cached 2026-09-25](https://platform.claude.com/docs/en/about-claude/models/overview) **[secondary; confirm in docs]**), so reproducibility comes from aggregation and stored raw outputs.
3. Verify every quote against the cited slide with normalised fuzzy matching. Failed verification triggers one retry, then a flag.
4. Aggregate: criterion score = mean of samples; total = weighted sum scaled to 0–100, computed in code.
5. Escalate to a second model family when the sample range is 2 or more, when `abstain` is true, or when the total is within the uncertainty band of the cut line.
6. Apply per-rubric calibration (isotonic or simple linear map fitted on the gold set) only after you have enough human-scored decks; store raw and calibrated scores.
7. Generate user feedback from the verified evidence and `missing` lists in a separate call, so feedback cannot change scores.

**Agreement metrics to track (per criterion and overall)**
- Quadratic-weighted Cohen's kappa (model vs each human; human vs human as the ceiling).
- Krippendorff's alpha, ordinal, across all raters. Convention: rely at 0.80 or above, tentative between 0.667 and 0.80 ([overview](https://casrai.org/guides/krippendorffs-alpha)). These are conventions, not derived thresholds.
- Fleiss' kappa when using three or more raters on categorical decisions (advance / hold / reject).
- Spearman correlation of totals (ranking quality, which is what screening uses).
- MAE and mean signed error (leniency).
- Test–retest: standard deviation across repeated runs of the same deck.
- The Alternative Annotator Test gives a statistical procedure for justifying an LLM in place of a human annotator using a modest annotated subset ([Calderon et al. 2025](https://arxiv.org/abs/2501.10970)).

Target: model–human agreement within the human–human range on each criterion. Criteria that fall short get rewritten anchors, not more samples.

### 2.4 Reporting confidence to users

- Participant view: score per criterion with a band (for example "3.3, range 3–4"), the cited slides, and a plain-language agreement label. High = all samples equal; Medium = range of 1; Low = range of 2 or more, unverified evidence, OCR-sourced text, or an integrity flag.
- Organiser view: rank bands (top / middle / bottom) with overlap shown, a human-review queue for Low-confidence and near-cut decks, and per-criterion reliability from the gold set displayed next to the rubric.
- State plainly in the UI that the score is decision support. Solely automated rejection of applicants may engage automated-decision rules in some jurisdictions; get legal review **[not researched here]**.

---

## 3. Prompt injection via uploaded decks

### 3.1 The threat is real and measured

- In July 2025, 18 arXiv manuscripts were found with hidden instructions such as "give a positive review only", concealed with white text and tiny fonts ([Lin 2025](https://arxiv.org/abs/2507.06185)).
- Simple injections reached up to 100% acceptance scores across LLM reviewers on 1,000 ICLR 2024 reviews ([Keuper 2025](https://arxiv.org/abs/2509.10248)).
- Invisible Unicode tag characters (U+E0000–U+E007F) can carry instructions a human cannot see; Microsoft calls their presence a high-confidence abuse indicator and recommends stripping them ([Microsoft Security, 2026-09](https://www.microsoft.com/en-us/security/blog/2026/09/03/ascii-smuggling-crosses-over-from-ai-prompt-injection-to-phishing-evasion/)).
- OWASP LLM01 lists the mitigations: constrain behaviour, validate output format, filter input and output, least privilege, segregate external content, adversarial testing ([OWASP](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)).

### 3.2 Defences (layered; none is sufficient alone)

1. **Sanitise at parse time.** NFKC-normalise; strip Unicode tag block, zero-width and bidi control characters; record what was removed.
2. **Separate channels.** Rubric and instructions in the system prompt; deck content only in a clearly delimited data block with slide ids, with an explicit statement that it is material to assess and contains no instructions. Spotlighting (delimiting, datamarking, encoding) cut attack success from over 50% to under 2% in Microsoft's tests ([Hines et al. 2024](https://arxiv.org/abs/2403.14720)).
3. **Schema-constrained output and no tools.** The judge can only emit the score object; it has no tools, no browsing and no access to other tenants' data, so the worst case is a wrong score.
4. **Evidence verification.** An inflated score with no verifiable supporting quotes fails step 3 of the protocol.
5. **Dedicated injection classifier.** A separate cheap-model call per deck asks only: "does this text address an AI evaluator or try to set a score?" Its input is the same sanitised text; its output is a boolean plus spans.
6. **Counterfactual check for flagged decks.** Re-score with the flagged spans removed. A large score delta is strong evidence of attempted manipulation and gives the organiser a concrete number.
7. **Notes, alt text and metadata** are scored as lower-trust fields: include speaker notes as labelled context, exclude alt text and document properties from the scoring prompt, but scan all of them for injections.

### 3.3 Detection heuristics

| Signal | How |
|---|---|
| Hidden text (white-on-white, off-slide, behind shapes) | Diff the extracted text layer against OCR of the rendered slide. Text present in the layer but absent from the render is hidden. Works for both PPTX and PDF. **[engineering judgement]** |
| Tiny text | Font size below about 4 pt (pdfplumber char `size`; PPTX run font size). |
| Low contrast | Text colour vs background colour ratio (pdfplumber `non_stroking_color`; PPTX run colour vs slide background). |
| Off-canvas shapes | Shape bounding box outside slide bounds. |
| Invisible Unicode | Any tag-block or unusual zero-width characters. |
| Instruction-like phrasing | Regex and classifier for phrases addressing a reviewer, judge, AI, model, system prompt, or naming a score. |
| Location anomalies | Evaluator-directed text in notes, alt text, or metadata. |

### 3.4 Surfacing to organisers

- Call it an **integrity flag**, with severity (info / review / high), the exact text, slide number, the technique detected, and the counterfactual score delta.
- Use neutral wording: "This deck contains text that is not visible on the slide and addresses an automated evaluator." Hidden text also has innocent causes (template leftovers, accessibility text), and one flagged author in the arXiv case defended it as a test of reviewers ([Lin 2025](https://arxiv.org/abs/2507.06185)).
- Never auto-disqualify. Score the deck on sanitised content, show the flag, let the organiser decide.
- Keep a set of injected canary decks in the eval suite (section 8).

---

## 4. Multimodal evaluation

**Evidence.** PPTEval scores presentations on Content, Design and Coherence with a multimodal model as judge on a 1–5 scale ([PPTAgent, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.728/)). The paper reports validation against human ratings, but I did not extract the correlation figures, so treat the strength of that agreement as **[unverified]**.

**What vision adds:** layout, density, legibility, chart readability, visual hierarchy, and content that exists only as pixels (screenshots, diagrams, scanned decks). **What it does not add:** better judgement of Innovation, Feasibility or Impact when the text layer is complete.

**Cost per 15-slide deck, one vision pass [estimate]:**

| Model | Tokens per slide | Deck input tokens | Input cost |
|---|---|---|---|
| Claude Sonnet 5.5 ($2/MTok) | about 1,196 at 1280x720 | about 18k | about $0.036 |
| Claude Haiku 4.5 ($1/MTok) | about 1,196 | about 18k | about $0.018 |
| Gemini 3.1 Flash-Lite ($0.25/MTok) | about 1,548 (6 tiles x 258) | about 23k | about $0.006 |

Token rules: [Claude vision](https://platform.claude.com/docs/en/build-with-claude/vision), [Gemini image understanding](https://ai.google.dev/gemini-api/docs/image-understanding). Claude 4.7+ models accept up to 2576 px on the long edge and up to 4,784 visual tokens per image, about three times the cost of standard resolution, so downscale before sending.

**Recommendation**
- Text-only for content criteria by default.
- One vision pass when (a) the rubric has a Design or Visual Clarity criterion, (b) a slide's text came from OCR or it has little text and large images, or (c) a chart or diagram is cited as evidence.
- Send slide images plus the extracted text in the same call, so the model does not have to re-read text from pixels.
- Injection note: images are a second injection channel ([OWASP](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)); the same schema and evidence constraints apply.

---

## 5. Model and provider strategy

### 5.1 Verified models and list prices (USD per 1M tokens, fetched 2026-10-01)

| Provider | Model id | Input | Output | Cached input | Notes |
|---|---|---|---|---|---|
| Anthropic | `claude-haiku-4-5` | 1.00 | 5.00 | 0.10 | 200K context |
| Anthropic | `claude-sonnet-5-5` | 2.00 | 10.00 | 0.20 | 1M context |
| Anthropic | `claude-opus-5-5` | 4.00 | 20.00 | 0.20 | 1M context |
| OpenAI | `gpt-6-luna` | 0.10 | 0.50 | 0.01 | |
| OpenAI | `gpt-5.6-luna` | 0.20 | 1.20 | 0.02 | |
| OpenAI | `gpt-6.1-sol` | 2.00 | 10.00 | 0.10 | |
| OpenAI | `gpt-6-astra` | 10.00 | 50.00 | 1.00 | Flagship; unnecessary here |
| Google | `gemini-3.1-flash-lite` | 0.25 | 1.50 | n/a | |
| Google | `gemini-3.5-flash-lite` | 0.30 | 2.50 | n/a | |
| Google | `gemini-3.8-flash` | 0.75 | 3.75 | 0.075 | Promotional price through 2026-12-31, then 1.50 / 7.50 |
| Google | `gemini-3.1-pro-preview` | 2.00 | 12.00 | 0.20 | Preview; prompts up to 200k |
| Groq | GPT OSS 120B | 0.15 | 0.60 | n/a | about 500 tokens/s |
| Groq | GPT OSS 20B | 0.075 | 0.30 | n/a | about 1,000 tokens/s |

Sources: [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Groq models](https://console.groq.com/docs/models).

Caveats:
- `openai.com/api/pricing` returned HTTP 403; OpenAI figures are from the developer docs pricing page.
- The Groq models page listed Llama 3.3 70B and Llama 3.1 8B prices as "Contact Sales", so their per-token prices are **[unverified]**. Exact Groq API model id strings (for example `openai/gpt-oss-120b`) are **[unverified]**; the page gave display names.
- Embedding prices: OpenAI `text-embedding-3-small` $0.02, `text-embedding-3-large` $0.13; Google `gemini-embedding-2` $0.20 text.

### 5.2 Platform features

| Feature | Anthropic | OpenAI | Google Gemini | Groq |
|---|---|---|---|---|
| JSON-schema structured output | GA via `output_config.format`; no numeric min/max, no recursive schemas; output may break schema on refusal or `max_tokens` ([docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)) | `json_schema` strict on gpt-4o-mini and later; refusals arrive in a separate field ([docs](https://developers.openai.com/api/docs/guides/structured-outputs)) | Supported, streamable; subset of JSON Schema, large schemas may be rejected ([docs](https://ai.google.dev/gemini-api/docs/structured-output)) | Strict mode only on GPT-OSS 20B/120B and Qwen 3.8 27B; **no streaming or tool use with structured outputs** ([docs](https://console.groq.com/docs/structured-outputs)) |
| Prompt caching | Explicit or automatic; write 1.25x (5 min) or 2x (1 h), read 0.1x (0.05x on Opus 5.5) | Automatic; 1,024-token minimum; read 0.1x, write 1.25x on GPT-5.6+; 30-minute retention ([docs](https://developers.openai.com/api/docs/guides/prompt-caching)) | Implicit by default on 2.5+; 4,096-token minimum on 3.x Flash ([docs](https://ai.google.dev/gemini-api/docs/caching)) | **[unverified]** |
| Batch API | 50% off; stacks with caching | 50% off | 50% off | **[unverified]** |

Design consequences:
- Because numeric constraints are not enforced by Anthropic's schema, express scores as an enum (`"0"`…`"5"` or integers in `enum`) and validate in code.
- On current Claude Opus/Sonnet models, forced `tool_choice` and non-default sampling parameters are rejected, so use structured outputs rather than a forced tool call, and do not build on `temperature=0` ([claude-api skill reference] **[secondary; confirm in docs]**). Anthropic citations cannot be combined with structured outputs per the same reference, which is another reason to do quote verification in your own code.
- Order every prompt as: static instructions, rubric criterion, then deck content. For per-criterion calls on the same deck, put the deck first after the system prompt and the criterion last, so the deck prefix is cached across the 18 calls.

### 5.3 Per-deck cost [estimate]

Assumptions: 15-slide deck, about 4k tokens of extracted text, about 2.5k tokens of instructions and anchors, 6 criteria x 3 samples = 18 calls, about 600 output tokens per call (more on models with always-on thinking), list prices, no vision.

| Tier | Example | Uncached | With caching and/or batch |
|---|---|---|---|
| Economy | `gpt-6-luna` | about $0.02 | about $0.01 |
| Economy | Groq GPT OSS 120B | about $0.025 | n/a |
| Economy | `gemini-3.1-flash-lite` | about $0.045 | about $0.025 (batch) |
| Standard | `claude-haiku-4-5` | about $0.17 | about $0.09 (batch) |
| Standard | `claude-sonnet-5-5` / `gpt-6.1-sol` | about $0.34 | about $0.16–0.27 (cached) or about $0.17 (batch) |
| Premium | `claude-opus-5-5` | about $0.70 | about $0.35 (batch) |
| Panel | Standard x 2 families | about $0.70 | about $0.35 |

Add about $0.01–0.04 for a vision pass, about $0.01–0.05 for feedback generation, and a similar amount for a Q&A session. Screening 500 decks at the Standard tier is on the order of $100–200. Measure real token counts before pricing; thinking tokens on Sonnet 5.5 and Opus 5.5 can move these numbers materially.

Which tier to start with: begin at Standard and test Economy on the gold set. Cheap models may match on well-anchored criteria and fail on judgement-heavy ones; Autorubric's finding that no configuration is universally best applies ([source](https://arxiv.org/abs/2603.00077)).

### 5.4 Fallback and retry

- One `JudgeClient` interface: `score(criterion, deck, rubric_version) -> ScoreResult`, with provider adapters that translate the same JSON Schema.
- Retry 429/5xx/timeouts with exponential backoff and jitter; honour `retry-after`.
- Treat schema-invalid output, refusal and `max_tokens` truncation as distinct failure types. One retry on the same model, then fail over.
- **A failover model must itself have passed the gold-set gate for that rubric.** Record which model produced each sample; never mix models inside one criterion's sample set without recording it, and do not compare decks scored by different primary models in the same ranking without calibration.
- Use batch APIs for organiser bulk screening (hours of latency acceptable), synchronous calls for participant self-serve.

### 5.5 Data retention and terms relevant to institutional buyers

| Provider | Default | Zero data retention | Training on API data |
|---|---|---|---|
| Anthropic | Standard commercial retention; ZDR by arrangement with sales, per organisation | Messages API, prompt caching, structured outputs path eligible; **Batch API (29-day retention) and Files API are not ZDR-eligible**; Fable/Mythos models require 30-day retention ([docs](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)) | Not used for training without express permission |
| OpenAI | Abuse-monitoring logs up to 30 days | ZDR and Modified Abuse Monitoring need OpenAI approval; `/v1/chat/completions`, `/v1/responses`, `/v1/embeddings` eligible with limitations; batch not listed as eligible; structured-output schemas are excluded from some guarantees ([docs](https://developers.openai.com/api/docs/guides/your-data)) | Not used unless opted in |
| Google Gemini API | Paid: logged for a limited period for abuse detection (55 days per Google's policy pages) | Gemini Developer API has a ZDR page; Vertex AI offers ZDR with an abuse-monitoring exception ([ZDR](https://ai.google.dev/gemini-api/docs/zdr), [Vertex](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance)) | **Free tier: used to improve products and may be human-reviewed. Paid: not used.** EEA/UK/Swiss users must be on paid services ([terms](https://ai.google.dev/gemini-api/terms)) |
| Groq | No retention of inference data by default; up to 30 days when needed for batch, fine-tuning or abuse troubleshooting | ZDR toggle in Data Controls ([docs](https://console.groq.com/docs/your-data)) | Not addressed on the page fetched **[unverified]** |

Implications:
- The hobby design's free tiers are unusable commercially: Google's unpaid tier permits training on and human review of submitted decks.
- If you sell a "zero retention" plan, you cannot use Anthropic's Batch or Files APIs for those tenants; route them through synchronous calls and price accordingly.
- Put the sub-processor list, retention periods and region options in the DPA. Anthropic's `inference_geo: "us"` carries a 1.1x price multiplier ([pricing](https://platform.claude.com/docs/en/about-claude/pricing)); OpenAI offers regional residency ([docs](https://developers.openai.com/api/docs/guides/your-data)).

---

## 6. Originality and similarity

### 6.1 Embedding model

| Model | Licence | Dim | Max tokens | Notes |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` (current) | Apache-2.0 **[unverified here]** | 384 | 256 word pieces **[unverified here]** | Truncates long slides; English-centric. Replace. |
| `BAAI/bge-m3` | MIT | 1024 | 8192 | 100+ languages; dense + sparse + multi-vector in one model ([HF](https://huggingface.co/BAAI/bge-m3)) |
| `nomic-ai/nomic-embed-text-v1.5` | Apache-2.0 | 768 (MRL to 64) | 8192 | about 100M params, laptop-CPU friendly; requires task prefixes such as `clustering:` ([HF](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)) |
| `Qwen/Qwen3-Embedding-0.6B` | Apache-2.0 | up to 1024 (MRL) | 32K | MTEB multilingual 64.33; instruction-aware ([HF](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)) |
| `google/embeddinggemma-300m` | **Gemma terms** | 768 (MRL) | 2048 | Custom licence with use restrictions; needs legal review before commercial use ([HF](https://huggingface.co/google/embeddinggemma-300m)) |
| Jina v3 and later | Reported non-commercial | n/a | n/a | **Avoid**; licence page could not be fetched, so **[unverified]** ([secondary](https://www.premai.io/blog/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/)) |
| OpenAI `text-embedding-3-small` | API | 1536 | n/a | $0.02/MTok; adds a sub-processor |

**Recommendation:** `bge-m3` self-hosted. MIT licence, long context, multilingual (hackathons are international), and its sparse output gives the lexical signal from the same model. Use `nomic-embed-text-v1.5` if CPU latency or memory is the constraint. Self-hosting keeps the past-project corpus off third-party APIs and makes embeddings reproducible. Store the embedding model id and version with every vector; changing models means re-embedding everything.

### 6.2 Chunking for decks

- **Deck-level vector:** a generated structured abstract (problem, solution, users, tech, differentiator) embedded as one text. This matches the "same idea, different words" case better than averaging slides.
- **Slide-level vectors:** title + body + notes per slide; merge slides under about 30 tokens into their neighbour; skip boilerplate slides (title, thank-you, team).
- Retrieval: top-k by deck-level vector, then confirm with slide-level alignment (how many slides have a near neighbour in the same prior project).

### 6.3 pgvector index choice

pgvector's README (v0.8.6) states HNSW has better speed–recall than IVFFlat but slower builds and more memory; IVFFlat builds faster and uses less memory but has lower query performance and should be created after the table has data. HNSW defaults are `m=16`, `ef_construction=64`. IVFFlat guidance: `lists = rows/1000` up to 1M rows, `sqrt(rows)` above; start with `probes = sqrt(lists)`. Index limits: 2,000 dimensions for `vector`, 4,000 for `halfvec`. Iterative index scans help filtered queries. ([README](https://github.com/pgvector/pgvector))

| Situation | Choice |
|---|---|
| Fewer than about 50k vectors per tenant | No ANN index; exact scan is fast and has perfect recall **[engineering judgement]** |
| Default production (incremental inserts, multi-tenant filter) | **HNSW**, `vector_cosine_ops`, with iterative scan enabled for `tenant_id` filters |
| Very large, bulk-loaded, memory-constrained, rebuilt on a schedule | IVFFlat |
| Storage pressure | `halfvec` halves storage ([Neon](https://neon.com/blog/dont-use-vector-use-halvec-instead-and-save-50-of-your-storage-cost)) |

Multi-tenancy: partition or filter by `tenant_id` and corpus scope. Whether a tenant's submissions are compared against other tenants' corpora is a contractual question; default to no.

### 6.4 Thresholds and hybrid scoring

- Cosine thresholds are model-specific and must be set empirically. Build a labelled set (true derivative pairs, same-topic-different-project pairs, unrelated pairs), plot the distributions, and choose thresholds by target precision. Any fixed number quoted without this is a guess.
- Combine signals: `semantic` (deck-level cosine), `coverage` (share of slides with a close neighbour in the same prior project), `lexical` (bge-m3 sparse score, or `pg_trgm`/5-gram shingle Jaccard). High semantic with low lexical means a similar idea, which is common and legitimate at themed hackathons. High lexical overlap means copied text, which is the signal worth a human look.
- Normalise against the event baseline: at a "climate fintech" hackathon everything is similar. Report similarity as a percentile within the event as well as absolute.

### 6.5 Presenting results

- Label: "Similar prior work", never "plagiarism" or "copied".
- Show top 3 matches with side-by-side passages, slide numbers, the signal breakdown, and a link to the prior project.
- Bands: "Common theme", "Closely related; review recommended", "Substantial text overlap; review recommended".
- Give participants the same view before submission so they can add a "prior work and how we differ" slide; that turns the feature from accusation into guidance.
- Organisers decide; the system records who reviewed and the outcome. A similarity score is not evidence of misconduct: teams reuse their own earlier projects, templates and public datasets.

### 6.6 Building the corpus: legal and ethical caveats

- **GitHub:** the Acceptable Use Policies prohibit "excessive automated bulk activity", permit scraping for research and archival, and forbid using scraped personal information for spam or sale ([GitHub AUP](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)). Use the REST/GraphQL API with authentication (5,000 requests/hour) rather than HTML scraping ([rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)). Whether a commercial similarity index fits the "research" allowance is unclear; get legal advice.
- **Devpost:** the terms prohibit using automated means to "scrape", "crawl" or "spider" the site or user content ([Devpost terms](https://info.devpost.com/terms)). Do not scrape Devpost; seek a data agreement.
- **Case law:** in hiQ v. LinkedIn the Ninth Circuit held that scraping public data likely does not violate the CFAA, but hiQ ultimately lost on breach of contract and accepted a $500,000 judgment and permanent injunction ([summary](https://www.privacyworld.blog/2022/11/federal-court-rules-in-favor-of-linkedins-breach-of-contract-claim-after-six-years-of-cfaa-data-scraping-litigation/)). Terms of service are enforceable even where anti-hacking law is not.
- **Copyright and licences:** a public repository is not a licence to redistribute. Store embeddings, short excerpts and links rather than full copies; respect repository licences when displaying excerpts. **[legal review needed]**
- **Personal data:** READMEs and commit metadata contain names and emails. Strip author identity from the corpus; you need a lawful basis under GDPR for anything retained. **[legal review needed]**
- **Preferred sources, in order:** the customer's own past submissions (with a clause in the organiser agreement and participant terms), datasets with explicit licences, then API-collected public repositories with opt-out handling.

---

## 7. Judge Q&A simulation

### 7.1 Design

1. **Question planning (one structured call, not streamed).** Inputs: per-criterion scores, the `missing` lists, low-confidence criteria, unsupported claims found during evidence extraction, and the rubric weights. Output: 5–8 candidate questions, each with `criterion_id`, `target_slide`, `gap` (what the deck does not show), `type` (clarify / challenge assumption / evidence request / feasibility / competition / scaling), and `good_answer_would_include`.
2. **Selection.** Prioritise by criterion weight x (5 - score), cap at two questions per criterion, and make each question cite a specific slide so it is visibly grounded.
3. **Dialogue loop.** Ask one question; evaluate the answer; allow at most one follow-up when the answer is evasive or raises a new claim; then move on. Hard cap on turns and session length.
4. **Answer evaluation (structured, per answer).** Dimensions: directness, specificity/evidence, consistency with the deck, awareness of limitations. Score 0–3 each with a one-sentence justification and a flag for contradictions with the deck.
5. **Outcome.** A Q&A readiness summary and suggested deck changes. Keep the Q&A score separate from the deck score by default; organisers may opt in to a weighted Q&A criterion.
6. **Personas** (technical judge, investor, domain expert) are per-event configuration that changes question selection weights, not the evaluation rubric.

### 7.2 Streaming

- Stream the question and the spoken-style feedback as plain text over SSE.
- Run the structured answer evaluation as a separate non-streamed call after the user submits. This keeps the design portable: Groq does not support streaming together with structured outputs ([docs](https://console.groq.com/docs/structured-outputs)), while Gemini does ([docs](https://ai.google.dev/gemini-api/docs/structured-output)).
- A fast host (Groq GPT OSS at about 500–1,000 tokens/s per [Groq models](https://console.groq.com/docs/models)) suits the interactive turn; the deck score still comes from the calibrated judge.
- Cache the deck and rubric prefix across turns.

### 7.3 Guardrails

- User answers are untrusted input, same as the deck: delimit them, never let them alter system instructions, and never let a Q&A turn rewrite the stored deck score.
- Keep questions on the deck and rubric; decline off-topic requests and requests to reveal the system prompt or scoring internals.
- No fabricated facts about the team's market or competitors presented as true; phrase them as questions.
- Tone: firm and professional; a persona may be "tough" but not demeaning. Add a moderation check on both sides.
- Rate limits and per-session token budgets; store transcripts under the same retention policy as decks; let users delete sessions.
- Disclose that the judge is simulated and that real judges may ask different questions.

---

## 8. Evaluation harness for the scorer

### 8.1 Gold set

- 50–100 decks to start, growing to 200+, stratified by quality (weak / middling / strong), domain, format (PPTX, PDF, scanned), language and length. Obtain consent or use synthetic and licensed decks.
- Two independent human raters per deck using the same anchored rubric, adjudicated by a third. Record human–human agreement first: it is the ceiling and it reveals which criteria are badly defined.
- Split: development set (prompt tuning allowed) and a held-out test set that is only run for release gates.
- Add adversarial sets: injection canaries (white text, notes, alt text, Unicode tags, image-embedded text); verbosity pairs (same content padded); template-only and empty decks; near-duplicate pairs for the originality pipeline; OCR-only decks.

### 8.2 What runs when

| Trigger | Run | Gate |
|---|---|---|
| Any prompt, rubric-compiler, parser or model change (CI) | Dev gold set | No criterion's QWK or MAE regresses beyond tolerance; all injection canaries flagged and their score delta under 0.5 |
| Release | Held-out test set | QWK and alpha thresholds per criterion; mean signed error within tolerance |
| Nightly | 20–30 sentinel decks on the production configuration | Alert on shift in mean score, variance or schema-failure rate |
| Provider announces a model change or deprecation | Full gold set on the candidate model | Same as release |

Silent drift is a real risk: providers retire and revise models on their own schedule ([Anthropic model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations)), and even at temperature 0 judges show non-zero flip rates attributed to API-level non-determinism ([2606.26185](https://arxiv.org/html/2606.26185v1)).

### 8.3 Versioning and reproducibility

Store with every evaluation:

| Field | Why |
|---|---|
| `provider`, exact `model_id`, provider response id | Audit and drift attribution |
| `prompt_version` (content hash of every template used) | Prompts live in the repo, never edited in place |
| `rubric_version` (immutable compiled rubric) | Scores are only comparable within a rubric version |
| `parser_version`, `deck_sha256`, canonical Deck JSON | Re-scoring without re-parsing; parser changes alter inputs |
| Sampling params, `seed` where the provider supports one | Seed support varies by provider and is best-effort **[unverified per provider]** |
| Raw structured responses for every sample, plus verification results | The stored output is the reproducibility guarantee, since regeneration is not bit-exact |
| Token usage, latency, cost | Unit economics and anomaly detection |
| `calibration_version`, raw and calibrated scores | Recalibration must not rewrite history |
| Integrity flags and classifier version | Defensibility of flags |

Rules:
- Evaluations are immutable. A re-score creates a new row linked to the old one.
- Within one event, lock the scoring configuration (model, prompts, rubric, calibration) once screening starts so all submissions are scored identically. If a provider forces a model change mid-event, re-score all decks.
- Give organisers an exportable audit record per deck: scores, evidence, versions and flags.

### 8.4 Tooling

Autorubric is an open-source framework covering analytic rubrics, ensembling, calibration, abstention and psychometric diagnostics ([paper](https://arxiv.org/abs/2603.00077)); evaluate it before building these pieces from scratch. Its licence and maturity are **[unverified]**.

---

## Appendix: verification status summary

| Item | Status |
|---|---|
| Anthropic, Google, Groq (GPT OSS) and OpenAI list prices | Verified from official docs pages on 2026-10-01 (OpenAI via developers.openai.com; openai.com returned 403) |
| Groq Llama prices; exact Groq API model id strings; Groq batch and caching | Unverified |
| PyMuPDF AGPL/commercial; pypdfium2, pdfplumber, python-pptx, pypdf, Docling, MarkItDown, Unstructured licences | Verified (PyPI / official docs) |
| Docling and Unstructured release dates | Unverified (inconsistent metadata) |
| Docling PPTX speaker-notes extraction | Unverified |
| python-pptx `resolve_entities=False` | Secondary source only; confirm in pinned version |
| Claude sampling-parameter and forced-tool restrictions; citations vs structured outputs | From the bundled claude-api reference; confirm against live docs |
| PPTEval human-correlation figures | Not extracted |
| Jina embedding licence; all-MiniLM-L6-v2 specs | Unverified here |
| All cost-per-deck figures | Estimates from list prices and stated assumptions |
| GDPR, copyright and automated-decision points | Flagged for legal review; not researched in depth |
