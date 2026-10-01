# Product Requirements — Deck Evaluator

Status: draft v1 · 2026-10-01 · Working product name: **DeckJury** (domain and trademark not yet checked)

Sources: [original system design](../reference/original-system-design.pdf), [market research](../research/01-market-and-product.md).

## 1. Problem

Hackathon organisers and college SPOCs must shortlist from hundreds of idea decks in a few days, usually with volunteer or faculty judges and no tooling beyond a spreadsheet. Scores are inconsistent between judges, the reasoning is not recorded, and duplicate ideas across teams go unnoticed. Students, on the other side, submit decks with no feedback against the criteria they will be judged on.

## 2. Product

A judge-assist tool. It scores every deck against the event's own rubric, shows the slide evidence behind each score, flags duplicates and attempts to game the scorer, and gives the panel a ranked, exportable shortlist. Humans make the final decision. Students get the same rubric-based critique before they submit.

It is not an "AI judge", a hackathon management platform, a deck generator, or a code auditor.

## 3. What changed from the original design

| Original design | Commercial product | Reason |
|---|---|---|
| Students are the user | Organisers and SPOCs are the paying customer; students are the free funnel | Single-deck AI feedback is priced between free and about $30; organiser judging tools sell from $699 per event |
| Six hardcoded axes | Rubrics are versioned data; SIH is a preset | The official SIH criteria are nine unweighted items and do not match the six axes |
| PPTX first | PDF first, PPTX second, slide images used for scoring | SIH accepts PDF only and tells teams to use diagrams |
| One LLM call returns six numbers | Per-criterion scores with cited evidence, a confidence band and a stored run record | A bare number will not survive a faculty panel |
| Bulk screening in v2 | Bulk screening in v1 | It is the feature the paying customer buys |
| Originality against scraped past winners | Similarity within a submission batch | No licensing risk and directly useful to a SPOC |
| Free-tier services | Portable, self-hostable stack | Free tiers forbid commercial use or cap out; the team deploys it themselves |

## 4. Users and roles

| Role | Who | Main jobs |
|---|---|---|
| Owner | Person who created the organisation | Billing, members, everything an admin can do |
| Admin | Organiser, SPOC | Create events and rubrics, bulk intake, run screening, export, release feedback |
| Judge | Faculty or invited reviewer | Read AI brief, override scores, add notes |
| Member | Student, team member | Upload a deck, read feedback, practise Q&A |

Every user has a personal workspace. Organisations are separate workspaces with their own members, events and credit balance.

## 5. Scope by release

### v1 — screening product

Student side
- Upload PDF or PPTX (50 MB, 40 slides)
- Template conformance check: slide count, required sections, title-slide fields
- Per-criterion score with quoted slide evidence and one concrete fix
- Re-evaluate after edits and see what moved

Organiser side
- Organisation workspace with members and roles
- Events with a rubric: SIH preset, or custom criteria, weights, scale and level descriptors
- Bulk intake of many decks into an event, with team metadata
- Ranked table: per-criterion scores, confidence, integrity flags
- Human override and notes per deck; the ranking follows the human score where one exists
- Export to CSV and XLSX
- Near-duplicate detection within the event

Platform
- Deck content treated as untrusted input; injection and hidden text flagged
- Every score stores rubric version, prompt version and model
- Credit ledger: one credit is one deck evaluated against one rubric
- Data export and deletion on request; retention period per workspace
- Audit log of administrative actions

### v1.5

- Judge Q&A simulator grounded in the deck's weak points
- Judge-assist brief with suggested questions
- Organiser-controlled release of feedback to teams
- PDF summary page for the SPOC's internal-hackathon report

### v2

- Calibration against human-scored decks per event, and agreement reporting
- Judge consistency report (leniency, divergence)
- Rubric ingestion from a URL or pasted text
- Payment provider integration and self-serve plans
- SSO for institutions; API keys for organiser integrations

### Out of scope

Registration and team formation, certificates, code or repository auditing, deck generation, investor-style startup scoring, a scraped past-winners corpus.

## 6. Packaging

Prices are recommendations to test, not validated. See the market research for comparables.

| Plan | Buyer | Price | Evaluations |
|---|---|---|---|
| Free | Student | ₹0 | 2 per month |
| Team Pass | Student team | ₹199 per event | 25 |
| Institution Season | SPOC, innovation cell | ₹14,999 per season | 300 |
| Institution Year | College | ₹39,999 per year | 1,500 |
| Organiser Event | Corporate, government, large fest | ₹49,999 per event | 1,000 |

Plans are data in the system, so prices and quotas can change without a code change. Judge seats are bundled and not metered.

## 7. Quality requirements

| Area | Requirement |
|---|---|
| Score defensibility | Every criterion score cites at least one slide; a score with no evidence is rejected by the pipeline |
| Reproducibility | A stored evaluation can be traced to rubric version, prompt version, model id and sampling settings |
| Tenant isolation | No request can read another workspace's data; enforced in the database, not only in application code |
| Turnaround | A single deck completes in under 90 seconds at the standard quality tier; a 300-deck batch within one hour |
| Failure handling | A failed step retries with backoff; a deck that cannot be processed ends in a named failure state and its credit is refunded |
| Privacy | Decks are not used for training and not visible outside the workspace; deletion removes files and derived data |
| Portability | Runs locally with Docker Compose; no dependency on one cloud provider's proprietary services |

## 8. Success measures

- Agreement with human judges on a gold set: rank correlation and mean absolute error per criterion, tracked per prompt and model version
- Share of organiser rankings where the human override changes the shortlist
- Time from batch upload to exported shortlist
- Free-to-paid conversion for teams; season renewals for institutions

## 9. Open questions

1. Will SPOCs pay, and what can they approve without a purchase committee? No evidence was found. Ten to fifteen interviews are needed before pricing is fixed.
2. The official SIH 2026 template and guidelines must be downloaded from sih.gov.in and compared with the mirrored copies the research used.
3. Per-evaluation model cost and score variance have to be measured on real decks before the free quota is set.
4. Product name: domain and trademark checks.
