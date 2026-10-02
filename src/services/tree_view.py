"""Configuration presets owned by tree views, not by genealogical layout."""

from src.services.tree_layout import TreeLayoutConfiguration


PORTRAIT_TREE_LAYOUT_CONFIGURATION = TreeLayoutConfiguration(
    person_width=160.0,
    person_height=220.0,
)
