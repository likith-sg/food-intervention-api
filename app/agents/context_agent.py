"""
context_agent.py
Thin layer — scoring thresholds only. All reasoning is now AI-generated.
"""

def get_intervention(score: int) -> str:
    if score >= 8:
        return "none"
    if score >= 5:
        return "soft"
    return "strong"

def get_decision(intervention_level: str) -> str:
    return {"none": "good", "soft": "moderate", "strong": "avoid"}[intervention_level]
