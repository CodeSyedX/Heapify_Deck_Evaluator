"""Rubric value objects.

A rubric is data (ADR 0008): criteria with weights and a written descriptor for
every level on the scale, plus an optional deck template. Instances are immutable;
``content_hash`` identifies a definition independently of key order or whitespace.
"""

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

from deck_core.shared_kernel.errors import ValidationError

ACCEPTED_FORMATS = frozenset({"pdf", "pptx"})
_KEY_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,62}")


@dataclass(frozen=True, slots=True)
class Scale:
    min: int
    max: int

    def levels(self) -> range:
        return range(self.min, self.max + 1)


@dataclass(frozen=True, slots=True)
class LevelDescriptor:
    score: int
    descriptor: str


@dataclass(frozen=True, slots=True)
class Criterion:
    key: str
    name: str
    description: str
    weight: float
    evidence_guidance: str
    levels: tuple[LevelDescriptor, ...]


@dataclass(frozen=True, slots=True)
class TemplateSection:
    key: str
    title: str
    required: bool
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeckTemplate:
    max_slides: int
    accepted_formats: tuple[str, ...]
    sections: tuple[TemplateSection, ...]


@dataclass(frozen=True, slots=True)
class RubricDefinition:
    scale: Scale
    criteria: tuple[Criterion, ...]
    template: DeckTemplate | None = None

    def criterion(self, key: str) -> Criterion:
        for criterion in self.criteria:
            if criterion.key == key:
                return criterion
        raise KeyError(key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scale": {"min": self.scale.min, "max": self.scale.max},
            "criteria": [
                {
                    "key": c.key,
                    "name": c.name,
                    "description": c.description,
                    "weight": c.weight,
                    "evidence_guidance": c.evidence_guidance,
                    "levels": [
                        {"score": level.score, "descriptor": level.descriptor} for level in c.levels
                    ],
                }
                for c in self.criteria
            ],
            "template": None
            if self.template is None
            else {
                "max_slides": self.template.max_slides,
                "accepted_formats": list(self.template.accepted_formats),
                "sections": [
                    {
                        "key": s.key,
                        "title": s.title,
                        "required": s.required,
                        "keywords": list(s.keywords),
                    }
                    for s in self.template.sections
                ],
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Build and validate a definition from its JSON form."""
        try:
            template = data.get("template")
            rubric = cls(
                scale=Scale(min=_integer(data["scale"]["min"]), max=_integer(data["scale"]["max"])),
                criteria=tuple(
                    Criterion(
                        key=str(c["key"]),
                        name=str(c["name"]),
                        description=str(c["description"]),
                        weight=_number(c["weight"]),
                        evidence_guidance=str(c["evidence_guidance"]),
                        levels=tuple(
                            LevelDescriptor(
                                score=_integer(level["score"]), descriptor=str(level["descriptor"])
                            )
                            for level in c["levels"]
                        ),
                    )
                    for c in data["criteria"]
                ),
                template=None
                if template is None
                else DeckTemplate(
                    max_slides=_integer(template["max_slides"]),
                    accepted_formats=tuple(str(f) for f in template["accepted_formats"]),
                    sections=tuple(
                        TemplateSection(
                            key=str(s["key"]),
                            title=str(s["title"]),
                            required=bool(s["required"]),
                            keywords=tuple(str(k) for k in s.get("keywords", ())),
                        )
                        for s in template["sections"]
                    ),
                ),
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValidationError("Rubric definition is malformed", details={"cause": repr(exc)}) from exc
        validate_rubric(rubric)
        return rubric

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def validate_rubric(rubric: RubricDefinition) -> None:
    """Raise ``ValidationError`` listing every problem that makes the rubric unusable."""
    problems: list[str] = []
    scale = rubric.scale
    if scale.min < 0 or scale.max <= scale.min:
        problems.append("scale must satisfy 0 <= min < max")
    if not rubric.criteria:
        problems.append("at least one criterion is required")

    keys = [c.key for c in rubric.criteria]
    problems.extend(f"duplicate criterion key '{k}'" for k in sorted(_duplicates(keys)))
    expected_levels = list(scale.levels())
    for criterion in rubric.criteria:
        label = f"criterion '{criterion.key}'"
        if not _KEY_PATTERN.fullmatch(criterion.key):
            problems.append(f"{label}: key must be lower snake case")
        if not criterion.name.strip() or not criterion.description.strip():
            problems.append(f"{label}: name and description are required")
        if not math.isfinite(criterion.weight) or criterion.weight <= 0:
            problems.append(f"{label}: weight must be a positive number")
        if sorted(level.score for level in criterion.levels) != expected_levels:
            problems.append(
                f"{label}: exactly one descriptor is required for each of {expected_levels}"
            )
        if any(not level.descriptor.strip() for level in criterion.levels):
            problems.append(f"{label}: level descriptors must not be empty")

    if rubric.template is not None:
        problems.extend(_template_problems(rubric.template))
    if problems:
        raise ValidationError("Rubric definition is invalid", details={"problems": problems})


def _template_problems(template: DeckTemplate) -> list[str]:
    problems: list[str] = []
    if template.max_slides < 1:
        problems.append("template: max_slides must be at least 1")
    if not template.accepted_formats:
        problems.append("template: at least one accepted format is required")
    unknown = sorted(set(template.accepted_formats) - ACCEPTED_FORMATS)
    if unknown:
        problems.append(f"template: unsupported formats {unknown}")
    problems.extend(
        f"template: duplicate section key '{k}'"
        for k in sorted(_duplicates([s.key for s in template.sections]))
    )
    for section in template.sections:
        if not _KEY_PATTERN.fullmatch(section.key):
            problems.append(f"template section '{section.key}': key must be lower snake case")
        if not section.title.strip():
            problems.append(f"template section '{section.key}': title is required")
    return problems


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    return {v for v in values if v in seen or seen.add(v)}  # type: ignore[func-returns-value]  # set.add returns None; used for its side effect


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"expected an integer, got {value!r}")
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"expected a number, got {value!r}")
    return float(value)
