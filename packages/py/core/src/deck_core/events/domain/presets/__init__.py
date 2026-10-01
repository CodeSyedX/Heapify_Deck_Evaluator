"""Built-in rubrics, stored as JSON so they can be seeded and diffed as data."""

import json
from functools import cache
from importlib import resources

from deck_core.events.domain.rubric import RubricDefinition
from deck_core.shared_kernel.errors import NotFoundError

SIH_IDEA = "sih_idea"
PITCH_DECK = "pitch_deck"
PRESET_KEYS = (SIH_IDEA, PITCH_DECK)


@cache
def load_preset(key: str) -> RubricDefinition:
    if key not in PRESET_KEYS:
        raise NotFoundError(f"No rubric preset named '{key}'")
    text = resources.files(__package__).joinpath(f"{key}.json").read_text(encoding="utf-8")
    return RubricDefinition.from_dict(json.loads(text))
