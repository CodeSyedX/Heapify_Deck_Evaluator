"""What other contexts may import from ``events``."""

from deck_core.events.domain.presets import PITCH_DECK, PRESET_KEYS, SIH_IDEA, load_preset
from deck_core.events.domain.rubric import (
    Criterion,
    DeckTemplate,
    LevelDescriptor,
    RubricDefinition,
    Scale,
    TemplateSection,
    validate_rubric,
)

__all__ = [
    "PITCH_DECK",
    "PRESET_KEYS",
    "SIH_IDEA",
    "Criterion",
    "DeckTemplate",
    "LevelDescriptor",
    "RubricDefinition",
    "Scale",
    "TemplateSection",
    "validate_rubric",
    "load_preset",
]
