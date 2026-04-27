"""
behavior_agent.py
Fixed: pattern detection now requires minimum history length before firing.
Prevents false positives on fresh/empty history.
"""

def detect_pattern(recent_history: list, current_time: str):
    from app.agents.scoring_agent import classify_food

    # Need at least 2 entries in history to detect any pattern
    if len(recent_history) < 2:
        return None

    late_count = 0
    try:
        hour = int(current_time.split(":")[0])
        if hour >= 22:
            late_count = 1
    except (ValueError, IndexError):
        pass

    for entry in recent_history[-5:]:
        try:
            h = int(entry.get("time", "00:00").split(":")[0])
            if h >= 22:
                late_count += 1
        except (ValueError, IndexError):
            pass

    if late_count >= 2:
        return "late_night_pattern"

    # Need at least 3 entries to detect junk pattern
    if len(recent_history) >= 3:
        junk_count = sum(
            1 for e in recent_history[-5:]
            if classify_food(e.get("food", "")) == "junk"
        )
        if junk_count >= 3:
            return "junk_pattern"

    return None
