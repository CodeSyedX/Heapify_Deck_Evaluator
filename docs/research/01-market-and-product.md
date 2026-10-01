# 01 — Market and Product Research: Hackathon Deck Evaluator

Research date: 2026-10-01. All factual claims carry a source link. Anything marked **[unverified]** is an estimate, inference, or a claim found only in a low-quality/secondary source. Recommendations (sections 4, 5, 7) are judgement, not fact.

---

## Key decisions for the build

1. **Build the organiser/SPOC side as the product, and the student side as the free funnel.** Students in India pay ₹249–₹1,499 at most for career tools; organiser/judging software sells at $699 per event to $6,250 per year. The money is with whoever has to screen a pile of decks.
2. **The 2026 SIH idea-PPT window is gone.** sih.gov.in shows nomination and idea submission closing 5 Oct 2026. Do not plan a v1 launch around SIH 2026 deck submission. Target (a) Dec 2026 Grand Finale Q&A prep for the ~1,300 finalist teams, (b) the Jan–Apr college tech-fest season, (c) SIH 2027 internal hackathons (Aug–Sep 2027) as the first real revenue season.
3. **Rubrics must be data, not code.** The official SIH criteria are nine unweighted items that do not map cleanly onto the six axes in the current design. Ship a rubric schema (criteria, weights, scale, anchors, evidence requirement) with SIH as preset #1.
4. **PDF is the primary input, PPTX secondary.** The official SIH template requires PDF upload and rejects PPT. Slide-image (vision) parsing is required because the template tells teams to use diagrams instead of text.
5. **Every score must cite slide-level evidence and carry a confidence band.** Published research shows LLM judges are consistent but biased; a bare number will not survive a faculty panel.
6. **Treat deck text as untrusted input.** Prompt-injection and verbosity gaming are the obvious attacks; build detection and a "flags" column from day one.
7. **Bulk mode is v1, not v2:** ZIP/CSV upload of 50–500 decks, ranked table, per-criterion scores, CSV/XLSX export, and a judge-override column. This is the feature a SPOC pays for.
8. **Position as "judge-assist / pre-screen", never "AI judge".** Humans decide; the tool ranks, flags and explains. This is also how Devfolio frames its own AI judge.
9. **Meter by deck evaluated, sell by event or season.** One "evaluation" = one deck against one rubric. Institution/organiser plans are packs of evaluations with a time window.
10. **Defer the past-winners originality corpus until licensing is clear.** Start with similarity *within* a submission batch (duplicate/near-duplicate ideas across teams), which needs no external corpus and is directly useful to SPOCs.

---

## 1. Competitive landscape

### 1a. Startup pitch-deck analysers (adjacent, not direct)

| Product | What it does | Who pays | Public pricing | Gap vs. our use case |
|---|---|---|---|---|
| PitchBob (AI VC Analyst / Deck Feedback) | Scores decks on 11 VC criteria, slide-by-slide review, investment memo; CRM integrations for VCs/accelerators | Founders; VCs/accelerators | Feedback tool $29.90; "Improve" service $99; Co-Pilot from $19.9/mo; VC analyst free for first 10 decks in beta, then usage-based ([pitchbob.io/products/vc](https://pitchbob.io/products/vc), [search summary of pitchbob pages](https://pitchbob.io/products/ai-pitch-deck-feedback)) | Investor rubric (traction, exit, moat) is wrong for student hackathons; no custom rubric; USD pricing |
| Inodash AI Pitch Deck Evaluator | Total score + section feedback on 10+ investor criteria; separate "for investors" variant | Founders | $2.49 per detailed report ([inodash.com](https://inodash.com/ai-pitch-deck-evaluator)) | Sets a very low per-report price anchor; no hackathon rubric, no bulk |
| Seed Angels Pitch Deck Analyzer | 34 criteria across 8 themes, result in under 2 minutes | Free (lead-gen) | Free ([seedangels.ai](https://seedangels.ai/pitch-deck-analyzer)) | Shows single-deck scoring is a free commodity |
| DeckCheck | Scores investor decks against expert guidelines | Free | Free ([deckcheck.donnagriffit.com](https://deckcheck.donnagriffit.com/)) | Same |
| PitchGrid | Deck review | Founders | 5 free reviews; $7.99/mo or $4.99/mo annual ([thinkup.global roundup](https://thinkup.global/ai-powered-pitch-deck-analysis-tools/)) — secondary source, **[unverified]** against vendor site | Same |
| Evalyze | Deck analysis plus investor matching | Founders | Not checked ([evalyze.ai](https://www.evalyze.ai/)) | Fundraising-oriented |
| General chat assistants (ChatGPT, Gemini, Claude) | A student can paste a deck and a rubric and ask for a score | Free / existing subscription | — | **The real B2C competitor.** No batch ranking, no consistency across decks, no audit trail. This is my assessment, not sourced. |

Takeaway: single-deck AI feedback is priced between free and about $30. It is not a defensible paid product on its own.

### 1b. Hackathon platforms and their judging tooling

| Platform | Judging capability | Who pays | Pricing | Gap |
|---|---|---|---|---|
| Devpost | Submission portal and judging workflow; no official AI judging feature found in search (only third-party projects hosted on Devpost) ([search result](https://devpost.com/software/ai-powered-hackathon-judge-assistant)) | Corporate organisers | Custom quotes "low five figures to $80K" per a competitor's comparison page ([builderbase.com](https://builderbase.com/compare/devpost/)) — competitor-authored, treat as **[unverified]**; free for student organisations per the same search summary ([help.devpost.com](https://help.devpost.com/article/127-how-do-i-create-a-hackathon)) | No AI pre-screen; deck is just an attachment |
| Devfolio | Rubric judging with score normalisation and sponsor judging ([guide.devfolio.co](https://guide.devfolio.co/docs/guide/sponsor-judging)). Published an AI hackathon judge on 18 May 2026: an "evidence layer" that walks the repo and checks it against the team's claims, producing cited reports; humans keep the final decision; run as an experiment on one hackathon, not yet generally available at publication; no human-agreement numbers given ([devfolio.co/blog/the-discerning-machine](https://devfolio.co/blog/the-discerning-machine/)) | Sponsors/organisers | Not public. A "$25/month" figure on aggregator sites appears to describe a different product with the same name ([spotsaas](https://www.spotsaas.com/product/devfolio/pricing)) — **[unverified]** | Audits code repos, not idea-stage decks. Closest strategic threat: they have the organiser relationships and are already building AI judging |
| Unstop | Hosts competitions, hackathons, quizzes; lists 2,540+ hackathons in India ([unstop.com/hackathons](https://unstop.com/hackathons)). No public AI deck-evaluation feature found | Companies (employer branding/hiring); students via Unstop Pro | Organiser pricing is quote-based ([saasworthy](https://www.saasworthy.com/product/unstop/pricing)); one profile says companies pay about ₹100–150 per student ([professionalsaathi.com](https://professionalsaathi.com/blog/get-hired-with-unstop-platform-connecting-students-with-top-companies)) **[unverified]**; Unstop Pro ₹10,999/yr list, ₹6,599 promo ([unstop.com blog](https://unstop.com/blog/upgrade-your-career-with-unstop-pro)); launched at ₹1,999 ([Outlook Business](https://www.outlookbusiness.com/sector/saas/unstop-launches-subscription-membership-unstop-pro-news-9537)) | Distribution partner and potential competitor. Many colleges ran their SIH 2026 internal round on Unstop ([example listing](https://unstop.com/hackathons/internal-smart-india-hackathon-2026-bharat-ratna-baba-saheb-bhim-rao-ambedkar-rajkiya-engineering-college-pra-1736096)) |
| HackerEarth | Idea shortlisting, project evaluation, plagiarism detection, managed services ([hackerearth.com](https://www.hackerearth.com/recruit/hackathons)) | Enterprises | Assessment plans $99 and $399/month; hackathons by quote ([saasworthy](https://www.saasworthy.com/product/hackerearth/pricing)) | Enterprise hiring focus; out of reach for a college |
| DoraHacks (BUIDL AI) | AI-automated submission review for relevance, originality, completeness — per search summary only; vendor page returned HTTP 405 ([dorahacks.io](https://dorahacks.io/blog/guides/hackathon-judging-plan)) **[unverified]** | Web3 ecosystems | Not found | Web3 focus |
| MLH ecosystem | MLH's organiser guide points to submission portals such as Devpost and Devfolio ([guide.mlh.com](https://guide.mlh.com/organizer-resources/software-for-hackathons)); Gavel is a free AGPLv3 pairwise-comparison expo judging system from HackMIT ([github.com/anishathalye/gavel](https://github.com/anishathalye/gavel)); Jury is a newer open-source take ([github.com/hackutd/jury](https://github.com/hackutd/jury)) | Free | Free | Logistics for human judges; no AI, no decks |
| Mercer Mettl Hackathons | Enterprise hackathon product ([g2.com](https://www.g2.com/products/mercer-mettl-hackathons/discuss)) | Enterprises | Not found | Not examined in detail |

### 1c. AI judging assistants

| Product | Notes |
|---|---|
| EliteScreener | AI screening plus judging plus "blockchain-verified" certificates; credit-based pricing, amounts not shown; self-reported 12,450 AI evaluations ([elitescreener.online](https://www.elitescreener.online/)). Small; self-reported numbers **[unverified]** |
| JudgeFlow, HackJudge-AI, AI-judge, hackathon-judging-agent | Open-source/hackathon projects that screen repos or submissions against criteria and export ranked CSVs ([JudgeFlow](https://github.com/harika-behara/JudgeFlow), [Hackjudge-AI](https://github.com/sachithr19-007/Hackjudge-AI), [Ai-judge](https://github.com/saudkhan11/Ai-judge), [hackathon-judging-agent](https://github.com/JarodTan01/hackathon-judging-agent)). They show the core is easy to prototype; none appears to be a maintained commercial product |
| SIH-specific deck checker | A search for an AI tool that scores SIH decks returned only templates and archives of past decks ([search results, e.g. winners archive](https://github.com/Aadiii00/SIH-Winners-PPt-and-Sources)). Absence in one search is weak evidence; treat "no direct competitor" as **[unverified]** |

### 1d. Awards / application-management software (pricing comparables for the organiser side)

| Product | Pricing | Source |
|---|---|---|
| Judgify | Free up to 100 submissions; Pro $699 per event (500 submissions); Pro Unlimited $2,399/yr | [judgify.me pricing post](https://www.judgify.me/l/blog/new-pricing-plans/) (via search summary) |
| Evalato | €1,900–€4,900 per program | [hub.evalato.com](https://hub.evalato.com/help/pricing-plans) (via search summary) |
| Award Force | $3,125/yr Growth, $6,250/yr Pro | [g2.com](https://www.g2.com/products/award-force/pricing) (via search summary) |
| Submittable | From about $10,000/yr | [capterra.com](https://www.capterra.com/p/158382/Submittable/) (via search summary) |
| AcceleratorApp | From $200/month; $400–$800/month typical | [acceleratorapp.co](https://www.acceleratorapp.co/en/blogs/best-incubator-accelerator-software) — vendor's own blog |

**Where the gap is:** nobody found sells rubric-configurable, evidence-cited, bulk screening of idea-stage decks at a price an Indian college or student-run fest can pay. Platforms own submission intake; pitch analysers own the single founder deck; Devfolio's AI work is on code.

---

## 2. Customer segments and who actually pays

| Segment | Pain | Budget | Urgency | Evidence quality |
|---|---|---|---|---|
| Students / teams (B2C) | "Will my deck get shortlisted?" | Very low. Indian student tools sit at ₹249/mo to ₹1,499/yr ([cv-prime.in](https://www.cv-prime.in/blog/best-ai-resume-builders-india-2026), [resumegyani.in](https://resumegyani.in/)); free analysers and chat assistants exist | High but for a few days per year | Price anchors are sourced; conversion rate is **[unverified]** |
| College SPOC / innovation cell (B2B) | Must run an internal hackathon, pick up to 50 teams, and file a report including the judging process and jury details ([SIH 2026 guidelines, mirrored](https://sih-uit.vercel.app/assets/sih-2026-guidelines.pdf)) | **[unverified]** — I found no data on innovation-cell discretionary budgets or on colleges paying for judging software. Procurement at Indian colleges is typically slow; this is my assumption | Seasonal and deadline-driven; a SPOC is a faculty member doing this on top of teaching | Process is well documented; willingness to pay is not |
| Student-run fest organisers | Hundreds of submissions, volunteer judges | Low; Devpost is free for student orgs, Gavel is free | Medium | Thin |
| Corporate / government organisers | Screening at scale, defensible shortlists | Real. Organiser tooling sells for $699/event to five figures (section 1) | High per event | Pricing is sourced; that they would buy a standalone screening layer rather than use their platform is **[unverified]** |
| Accelerators / incubators | Application triage | Real ($200–$800/month tools) | Continuous, not seasonal | PitchBob and AcceleratorApp already target this; we would be late |

**Honest read.** The segment with both budget and urgency is organisers who must shortlist from a large pool. The SPOC is the most reachable version of that buyer and has a documented, mandatory screening task, but there is no evidence yet that SPOCs pay for software. Students supply volume, data and word of mouth, not revenue. Validate SPOC willingness to pay with 10–15 conversations before building billing; RVCE's own SPOC is the obvious first call.

Channel note: Unstop is both a distribution channel and the incumbent where internal rounds already run. A partnership gives reach; it also teaches them the feature.

---

## 3. Market facts for India

### SIH scale

- SIH 2025 (8th edition): 72,165 ideas from 68,766 student teams against 271 problem statements; 1,360 teams, 8,000+ students and 1,300+ mentors reached the Grand Finale at 60 nodal centres ([News On AIR](https://www.newsonair.gov.in/8th-edition-of-smart-india-hackathon-2025-begins-mic)).
- A college blog states 1,42,715 teams from 2,587 institutes took part at the internal level, and a 26% rise in idea submissions ([lingayasvidyapeeth.edu.in](https://www.lingayasvidyapeeth.edu.in/smart-india-hackathon/)). Single secondary source, **[unverified]**. If right, internal rounds produce roughly twice as many decks as reach the national portal.
- sih.gov.in currently displays 18,04,218+ participating students, 9,406 institutes and 3,158 problem statements ([sih.gov.in](https://sih.gov.in/)). These look like cumulative all-edition counters; the page summary did not say so, **[unverified]**.
- SIH 2026: launched August 2026 with 226 problem statements in the first lot (172 software, 54 hardware) — from third-party guides via search summary ([reskilll.com](https://reskilll.com/blogs/smart-india-hackathon-2026-launched-timeline-registration-how-to-participate/), [firstvidya.com](https://firstvidya.com/sih-2026-guide/)) **[unverified]** against an official release.

### SIH 2026 process (from the SIH 2026 Guidelines PDF)

Source: the guidelines deck as mirrored on a college site ([sih-uit.vercel.app/assets/sih-2026-guidelines.pdf](https://sih-uit.vercel.app/assets/sih-2026-guidelines.pdf)); the official copy sits behind the Guidelines section of [sih.gov.in](https://sih.gov.in/). I read the mirrored PDF text directly.

- Students cannot register themselves; the college SPOC (any senior faculty member) registers and nominates.
- Only teams selected in the college's internal hackathon can be nominated.
- Cap: 50 teams per institute (45 shortlisted + 5 waitlisted), 100 per university, any software/hardware mix.
- Team: 6 members, same college, at least one female member.
- The SPOC uploads an internal-hackathon report of up to 15 pages that includes the judging process, jury panel details and nominated teams.
- A team may submit against at most 2 problem statements. Each problem statement closes after 500 ideas, with a public counter.
- The team leader submits idea title, idea description, and the idea presentation as PDF.
- 4–5 teams per problem statement may reach the finale; prize ₹1,50,000 per problem statement.
- Deadline in the PDF: 15 Sep 2026. The official site now shows it extended to 5 Oct 2026, with an edit window on 2–5 Oct ([sih.gov.in](https://sih.gov.in/)).
- Grand Finale proposed for December 2026.

### Official idea-evaluation criteria (verbatim from the guidelines PDF)

> "Evaluation criteria will include novelty of the idea, complexity, clarity and details in the prescribed format, feasibility, practicability, sustainability, scale of impact, user experience and potential for future work progression."

No weights are published. Blogs that quote percentage weights (for example 20/25/25/20/10, or 20/25/20/20/15) are the authors' own estimates; one says so explicitly ([reskilll.com](https://reskilll.com/blogs/sih-2026-ppt-template-exact-format-slides-evaluators-score/)).

Mapping to the current six-axis design:

| Official SIH criterion | Current axis | Note |
|---|---|---|
| Novelty | Innovation | Direct |
| Complexity | — | Missing |
| Clarity and details in prescribed format | Clarity (+ structure check) | Direct |
| Feasibility | Feasibility | Direct |
| Practicability | Feasibility (partly) | Should be separate |
| Sustainability | — | Missing |
| Scale of impact | Impact, Scalability | Two axes for one criterion |
| User experience | — | Missing |
| Potential for future work | Scalability (partly) | Loose |
| — | Relevance | Not an official criterion; still useful as a "does this answer the problem statement" gate |

### Official idea-PPT template

The SIH 2025 template, as re-uploaded to SlideShare ([slideshare.net](https://www.slideshare.net/slideshow/sih2025-idea-presentation-format-pptx/283066439)):

1. Title — problem statement ID, title, theme, PS category (software/hardware), team ID, team name
2. Idea title / proposed solution — explanation, how it addresses the problem, innovation and uniqueness
3. Technical approach — technologies, methodology and process (flow charts, images, working prototype)
4. Feasibility and viability — feasibility analysis, challenges and risks, strategies to overcome them
5. Impact and benefits — impact on target audience; social, economic, environmental benefits
6. Research and references

Instructions slide: six slides maximum including title; points and diagrams, not paragraphs; do not alter the template's content pointers; save as PDF, no PPT or Word accepted.

The 2026 template file itself was not retrieved; sih.gov.in lists an "Idea Presentation Template" in PowerPoint format ([sih.gov.in](https://sih.gov.in/)). Whether 2026 changed the slide structure is **[unverified]**. One blog describes a 10-slide 2026 format ([reskilll.com](https://reskilll.com/blogs/sih-2026-ppt-template-exact-format-slides-evaluators-score/)); this conflicts with the six-slide official format and I would not trust it without the official file. Action: download the 2026 template from the SPOC/Guidelines section and diff it.

### Other large hackathons

- Flipkart GRiD: close to 1.7 lakh applications in 2025 — search summary of placement blogs ([firstgrade.in](https://firstgrade.in/hackathons)) **[unverified]**.
- HackWithInfy: 1.5 million participants since 2018 — search summary ([Forbes India](https://www.forbesindia.com/article/ai-tracker/hiring-through-a-hackathon/2992405/1)) **[unverified]**. It is mostly a coding contest, so few decks.
- Unstop lists 2,540+ hackathons in India ([unstop.com/hackathons](https://unstop.com/hackathons)).
- Institution's Innovation Councils: "5000+" institutions per one college page, undated ([search summary](https://www.ifheindia.org/IIC/)) **[unverified]**. This is the rough ceiling on institutional buyers.

### How many decks?

- SIH national stage: about 72,000 decks per year (2025 figure, sourced above).
- SIH internal stage: about 140,000 if the Lingaya's figure is right **[unverified]**.
- All other Indian hackathons with an idea/PPT round: no data found. A guess of a few hundred thousand decks per year in total is **[unverified]** and should not be used in a pitch without better evidence.

---

## 4. Feature set recommendation

### Must have for a commercially credible v1

Student side (free funnel):
- PDF and PPTX upload; text plus slide-image understanding
- Template conformance check (slide count, required sections, PDF format, title-slide fields)
- Per-criterion scores with quoted slide evidence and one concrete fix per criterion
- Re-evaluate after edits, with a diff of what moved

Organiser/SPOC side (paid):
- Event workspace with a rubric (SIH preset, plus paste-your-own criteria and weights)
- Bulk intake: ZIP or shared-folder upload, CSV of team metadata
- Ranked table with per-criterion scores, flags, and confidence
- Human override and notes per deck; final ranking is the human's
- Exports: CSV/XLSX, and a PDF summary that can go into the SPOC's internal-hackathon report (the report requires a "judging process" page)
- Within-batch duplicate/near-duplicate idea detection
- Run reproducibility: fixed rubric version, model version and prompt version stored per score

Platform:
- Deck text handled as untrusted input; injection attempts flagged
- Data deletion on request and a clear statement that decks are not used to train or shown to other teams

### Differentiators (v1.5–v2)

- Judge Q&A simulator tuned to the problem statement; best timed for the finale in December
- Judge-assist view: per-deck brief and suggested questions for human panels
- Consistency report: human-vs-AI and judge-vs-judge score divergence, per-judge leniency
- Calibration against a small set of human-scored decks per event
- Rubric ingestion from URL
- Problem-statement fit check using the public SIH problem-statement list
- Feedback release to teams after results (organiser-controlled)
- Hindi/regional-language feedback **[untested idea]**

### Skip for now

- Past-winners originality corpus: copyright and consent are unclear, coverage will be patchy, and a wrong "unoriginal" flag is costly. SIH itself requires ideas to be new ([guidelines](https://sih-uit.vercel.app/assets/sih-2026-guidelines.pdf)), so the need is real, but start with within-batch similarity.
- Full hackathon management (registration, team formation, certificates): Unstop, Devfolio and Devpost own this.
- Code/repo auditing: Devfolio is already there.
- Deck generation: crowded category and bad academic-integrity optics.
- Investor-style startup scoring: PitchBob and many free tools.

---

## 5. Pricing and packaging

Metering unit: **one evaluation = one deck scored against one rubric** (re-runs after edits count). Sell organisers a pack tied to an event or season so the purchase matches how they budget.

USD figures assume roughly ₹88 per $1 **[unverified — check the current rate]**. All prices are recommendations to test, not validated.

| Tier | Buyer | Price (INR) | Price (USD) | Includes | Comparable |
|---|---|---|---|---|---|
| Free | Student | ₹0 | $0 | 2 evaluations per month, SIH preset, top-line scores and 3 fixes | Seed Angels and DeckCheck are free ([seedangels.ai](https://seedangels.ai/pitch-deck-analyzer)) |
| Team Pass | Student team | ₹199 per event (one team, 30 days) | $4.99 | 25 evaluations, full evidence, Q&A simulator, custom rubric | Inodash $2.49 per report ([inodash.com](https://inodash.com/ai-pitch-deck-evaluator)); CV Prime ₹249/mo ([cv-prime.in](https://www.cv-prime.in/blog/best-ai-resume-builders-india-2026)); split six ways it is about ₹33 each |
| Institution Season | College SPOC / innovation cell | ₹14,999 per season (up to 300 decks); ₹39,999 per year (up to 1,500 decks, unlimited events) | $199 / $499 | Bulk screening, ranking, overrides, exports, report page, 5 judge seats | Roughly ₹50 per deck at the season tier; one profile puts Unstop's company-side price at ₹100–150 per student ([professionalsaathi.com](https://professionalsaathi.com/blog/get-hired-with-unstop-platform-connecting-students-with-top-companies)) **[unverified]** |
| Organiser Event | Corporate, government, large fests | ₹49,999 per event (up to 1,000 decks); custom above | $699 per event | Everything above plus consistency report, calibration, feedback release, SSO/DPA on request | Judgify Pro $699 per event for 500 submissions ([judgify.me](https://www.judgify.me/l/blog/new-pricing-plans/)); Evalato from €1,900 per program ([hub.evalato.com](https://hub.evalato.com/help/pricing-plans)) |
| Student-run events | Clubs | Free up to 100 decks with attribution | — | Bulk mode, branded | Devpost is free for student organisations ([help.devpost.com](https://help.devpost.com/article/127-how-do-i-create-a-hackathon)); Judgify free tier is 100 submissions |

Notes:
- Seats are not the meter; judge seats are bundled. Per-seat pricing punishes exactly the behaviour (more human reviewers) that builds trust.
- Unit cost per evaluation (LLM plus vision on 6 slides) was not measured in this research **[unverified]**. Measure it before fixing the free quota; the free tier must cost less than its referral value.
- Institution pricing is the least certain line. I found no direct evidence of what a SPOC can approve without a purchase committee. Ask in discovery calls and consider keeping the season tier under whatever that threshold is.
- UPI and INR invoicing with GST are required for the India tiers ([cv-prime.in on INR/UPI accessibility](https://www.cv-prime.in/blog/best-ai-resume-builders-india-2026)).

---

## 6. Risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Trust in AI scores | A large 2026 evaluation of 21 LLM judges found high test-retest reliability can mask severe position bias, and raw agreement overstates chance-corrected discrimination by 33–41 points ([arXiv 2606.19544](https://arxiv.org/html/2606.19544v1)). Devfolio says its AI judge has "a lower ceiling than a great human judge" ([devfolio.co](https://devfolio.co/blog/the-discerning-machine/)) | Evidence-cited scores; coarse scale (one study finds human–LLM alignment highest on a 0–5 scale, [arXiv 2601.03444](https://arxiv.org/pdf/2601.03444)); multiple runs with spread shown; per-event calibration on human-scored decks; publish agreement numbers; human decides |
| Gaming the scorer | Hidden white text, instructions to the model, keyword stuffing; LLM judges have documented verbosity bias ([arXiv 2606.19544](https://arxiv.org/html/2606.19544v1)) | Treat deck content as data; compare extracted text against rendered slide images to catch hidden text; injection classifier and a flag column; rubric anchors that require specifics; different prompts for the student and organiser modes so optimising for one does not transfer exactly |
| Homogenised decks | If every team tunes to the same scorer, decks converge and the score stops discriminating. Convergence under AI assistance is reported for student essays ([arXiv 2603.21228](https://arxiv.org/pdf/2603.21228)) | Feedback that asks questions and points at gaps, not rewritten text; no deck generation |
| Academic-integrity optics | Faculty may see it as AI doing students' work; organisers may see it as outsourcing judgement | Critique only; "judge-assist" language; audit trail; organiser controls what students see |
| Seasonality | SIH deck demand concentrates in Aug–early Oct ([sih.gov.in](https://sih.gov.in/), [guidelines](https://sih-uit.vercel.app/assets/sih-2026-guidelines.pdf)) | Multi-event rubrics; annual institution plan covering fests, ideathons and capstone reviews; accelerator/incubator intake as a non-seasonal line; finale Q&A product for December |
| Platform absorption | Devfolio is building AI judging; Unstop already hosts internal SIH rounds | Be the rubric-and-evidence layer that works with any platform's export; move fast on SPOC reporting, which platforms do not serve |
| Originality corpus liability | Scraped past decks raise copyright and consent issues; false "copied" flags harm students | Within-batch similarity first; opt-in corpus; show matched passages, never a bare percentage |
| Data protection | Decks contain names, emails and phone numbers of students | Minimise retention, delete on request, India-region hosting if institutions ask. Legal requirements under Indian data-protection law were not researched here **[unverified]** |
| Official-format drift | Template or criteria may change each year; third-party blogs already disagree with the official six-slide format | Rubrics and templates as versioned data; re-verify from the official file each August |

---

## 7. Positioning

**Positioning statement.** For hackathon organisers and college SPOCs who must shortlist from hundreds of idea decks in a few days, this is a judge-assist tool that scores every deck against the event's own rubric, shows the slide evidence behind each score, flags duplicates and gaming, and hands the panel a ranked, exportable shortlist they can defend. Unlike hackathon platforms, which collect submissions and leave reading them to volunteers, and unlike startup pitch analysers built on investor criteria, it is built for idea-stage student submissions and published judging criteria, starting with Smart India Hackathon. Students get the same rubric-based critique free before they submit.

**Candidate names** (availability checked by web search only; domain, trademark and app-store checks not done — all **[unverified]**):

| Name | Check result | Verdict |
|---|---|---|
| DeckJury | No product found in search | Best candidate |
| JuryDeck | No product found in search | Usable alternative |
| PitchProof | No pitch-deck product surfaced in search | Usable; generic, so trademark risk is higher |

Rejected after checks: JuryLens (existing jury-selection software, [jurylens.com](https://jurylens.com/)); RubricLens (existing rubric-review project, [github](https://github.com/seoyuldavidhan/RubricLens)); DeckBench (KDD 2026 benchmark and a separate open-source tool, [zenodo](https://zenodo.org/records/20318469), [github](https://github.com/cwarloe/deckbench)); DeckCheck (existing free deck analyser, [deckcheck.donnagriffit.com](https://deckcheck.donnagriffit.com/)); Rubriq (wealth-management startup, [rubriq.finance](https://rubriq.finance/)).

---

## Open items to verify before committing

1. Download the official SIH 2026 idea template and guidelines from sih.gov.in and confirm slide structure and criteria against the mirrored copies used here.
2. Ten to fifteen SPOC interviews: who reads the decks today, how long it takes, what they can spend without committee approval.
3. Measure per-evaluation model cost and score variance on 50 real SIH decks.
4. Ask Unstop and Devfolio whether they expose submission exports or partner integrations.
5. Domain and trademark search for the chosen name.
6. Legal review of using past winning decks as a corpus, and of student-data handling.
