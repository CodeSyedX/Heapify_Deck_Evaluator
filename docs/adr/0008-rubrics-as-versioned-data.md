# 8. Rubrics are versioned data

Status: accepted · 2026-10-01

## Context
The official SIH criteria are nine unweighted items and differ from the six axes in the original design. Other events have other criteria, and templates change yearly.

## Decision
A rubric is data: criteria, weights, level descriptors and an optional deck template. Published versions are immutable, and every evaluation run references one. Presets such as SIH are seed data.

## Consequences
New events need no code change. Scores are comparable only within a rubric version, so an event is pinned to one.
