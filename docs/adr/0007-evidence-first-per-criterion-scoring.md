# 7. Evidence-first, per-criterion scoring on a 0–5 scale

Status: accepted · 2026-10-01

## Context
The original design scored six axes in one model call. Organisers will use scores to screen hundreds of decks, so scores must be explainable and stable.

## Decision
One model call per criterion per sample. The model returns verbatim evidence with slide numbers, then a level against written descriptors on a 0–5 scale. Code verifies each quote against the slide, aggregates three samples into a mean and a range, and computes the weighted total. Users see a band and an agreement label.

## Alternatives
Single call for all criteria: cheaper, but conflates criteria and gives no per-criterion reliability. A 0–10 or 0–100 scale: research found weaker agreement with human raters.

## Consequences
Roughly three calls per criterion per deck; prompt caching of the deck prefix offsets much of the cost. A score without verifiable evidence cannot reach a user.
