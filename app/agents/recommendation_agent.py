"""
recommendation_agent.py
Kept for fallback only. Primary alternatives now come from AI agent.
"""

DEFAULT_ALTERNATIVES = [
    "light home-cooked meal with vegetables and protein",
    "fresh seasonal fruit with a small protein source",
    "warm soup with whole grain bread",
]

def get_alternatives(food: str, time_str: str = "12:00", mood: str | None = None) -> list[str]:
    """Fallback only — AI agent is the primary source."""
    return DEFAULT_ALTERNATIVES
