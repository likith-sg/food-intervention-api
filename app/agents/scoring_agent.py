"""
scoring_agent.py
Deterministic health score. Fixed: confidence logic improved for healthy unknowns.
"""

JUNK_FOODS = {"chips","pizza","burger","soda","fries","donut","candy","hotdog","nuggets","nachos"}
MODERATE_FOODS = {"sandwich","pasta","rice","bread","cereal","crackers","muffin","wrap"}

def classify_food(food: str) -> str:
    f = food.strip().lower()
    if f in JUNK_FOODS:
        return "junk"
    if f in MODERATE_FOODS:
        return "moderate"
    return "healthy"

def compute_score(food: str, time_str: str, recent_history: list) -> dict:
    food_lower = food.strip().lower()
    food_class = classify_food(food_lower)
    deductions = []
    score = 10

    if food_class == "junk":
        score -= 4
        deductions.append("Junk food: -4")
    elif food_class == "moderate":
        score -= 2
        deductions.append("Moderate food: -2")

    try:
        hour, minute = map(int, time_str.split(":"))
        time_val = hour + minute / 60.0
    except (ValueError, AttributeError):
        time_val = 12.0

    if time_val >= 22.0:
        score -= 2
        deductions.append("After 22:00: -2")
    elif time_val >= 20.0:
        score -= 1
        deductions.append("Between 20:00-22:00: -1")

    # Only apply history-based deduction if history is non-empty
    if recent_history:
        recent_junk = [
            e for e in recent_history[-5:]
            if classify_food(e.get("food", "")) == "junk"
        ]
        if len(recent_junk) >= 2:
            score -= 2
            deductions.append("Repeated junk (>=2 recent): -2")

    score = max(1, min(10, score))

    # Confidence: known junk/moderate = 0.9, unknown healthy = 0.8
    # (we're confident it's not harmful even if not in our labeled set)
    known_foods = JUNK_FOODS | MODERATE_FOODS
    if food_lower in known_foods:
        confidence = 0.9
    else:
        # Unknown food — if it scores high it's likely healthy, use 0.8
        confidence = 0.8 if score >= 8 else 0.6

    return {
        "score": score,
        "confidence": confidence,
        "food_class": food_class,
        "deductions": deductions,
        "time_val": time_val,
    }
