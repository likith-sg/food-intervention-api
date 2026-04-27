"""
ai_agent.py
Fixed:
- Mood reasoning no longer fires when mood is None
- Deduction-based reasoning only fires if deductions actually exist
- Healthy food alternatives are affirming, not generic
- History reasoning only fires if history is non-empty
"""

import os
import json

try:
    import anthropic
    _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    _AI_AVAILABLE = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
except Exception:
    _client = None
    _AI_AVAILABLE = False


def _call_claude_json(prompt: str, max_tokens: int = 800) -> dict | None:
    if not _AI_AVAILABLE or not _client:
        return None
    try:
        msg = _client.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        clean = raw
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:])
            if clean.strip().endswith("```"):
                clean = clean[:clean.rfind("```")]
        return json.loads(clean.strip())
    except Exception:
        return None


def _time_label(hour: int) -> str:
    if 5 <= hour < 11: return "morning"
    if 11 <= hour < 14: return "lunch"
    if 14 <= hour < 18: return "afternoon"
    if 18 <= hour < 21: return "evening"
    if 21 <= hour < 24: return "late evening"
    return "late night"


def _summarize_history(history: list) -> str:
    if not history:
        return "no history yet"
    items = []
    for e in history[-5:]:
        items.append(f"{e.get('food','?')} at {e.get('time','?')} ({e.get('decision','?')})")
    return "; ".join(items)


def generate_ai_analysis(
    food, food_class, score, time_str, mood, pattern,
    recent_history, deductions, confidence
) -> dict:

    history_summary = _summarize_history(recent_history)

    prompt = f"""You are a behavioral nutrition coach inside a real-time food intervention app.

USER CONTEXT:
- Food: {food} (classified as: {food_class})
- Health score: {score}/10
- Time of day: {time_str} ({_time_label(int(time_str.split(':')[0]) if time_str else 12)})
- Mood: {mood if mood else "not provided"}
- Pattern detected: {pattern if pattern else "none"}
- Recent history: {history_summary}
- Score deductions: {", ".join(deductions) if deductions else "none — full marks"}

Generate a JSON object with exactly these keys:
{{
  "reasoning": ["insight 1", "insight 2"],
  "intervention_message": "coaching paragraph",
  "future_risk": "one sentence",
  "better_alternatives": ["alt 1", "alt 2", "alt 3"]
}}

STRICT RULES:
- reasoning: 2-3 items MAX. Only include insights that are TRUE for this specific request. If mood was not provided, do NOT mention mood. If there is no history, do NOT mention patterns or history. Each insight must be specific to THIS food + time combination.
- intervention_message: warm, direct, personalized. If score >= 8, be affirming. If mood was not provided, do not reference it.
- future_risk: if score is 8+, say something positive about continuing good habits. Only warn if score < 8.
- better_alternatives: if food is healthy (score >= 8), suggest complementary foods that pair well or enhance the meal, NOT replacements. If food is junk, suggest specific healthier swaps with context for the time of day.
- Respond ONLY with the JSON object. No preamble, no markdown fences, no extra text."""

    result = _call_claude_json(prompt)
    if result and all(k in result for k in ("reasoning","intervention_message","future_risk","better_alternatives")):
        if (isinstance(result["reasoning"], list) and
            isinstance(result["intervention_message"], str) and
            isinstance(result["future_risk"], str) and
            isinstance(result["better_alternatives"], list)):
            return result

    return _fallback_analysis(food, food_class, score, time_str, mood, pattern, deductions, recent_history)


def _fallback_analysis(food, food_class, score, time_str, mood, pattern, deductions, recent_history) -> dict:
    try:
        hour = int(time_str.split(":")[0])
    except Exception:
        hour = 12
    window = _time_label(hour)
    food_cap = food.capitalize()

    reasoning = []

    # Food classification — always include
    if food_class == "junk":
        reasoning.append(f"{food_cap} is high in calories and low in micronutrients, offering quick energy with poor satiety.")
    elif food_class == "moderate":
        reasoning.append(f"{food_cap} is a moderate choice — adding protein or vegetables would improve its nutritional profile.")
    else:
        reasoning.append(f"{food_cap} is a healthy, nutrient-dense choice that supports stable energy and long-term wellbeing.")

    # Time reasoning — always include
    if hour >= 22:
        reasoning.append(f"Eating at {time_str} (late night) slows digestion and can disrupt sleep quality.")
    elif hour >= 20:
        reasoning.append(f"Evening eating at {time_str} leaves limited digestion time before sleep — a lighter option would be ideal.")
    elif 11 <= hour <= 14:
        reasoning.append(f"Lunchtime ({time_str}) is a peak energy window — {food_cap} supports sustained afternoon performance." if food_class != "junk" else f"Lunchtime ({time_str}) is when your body needs sustained energy — {food_cap} may cause an afternoon energy crash.")
    else:
        reasoning.append(f"Time: {time_str} ({window}) — a reasonable eating window with no timing concerns.")

    # History-based reasoning — ONLY if history exists AND deduction was actually applied
    has_repeated_deduction = any("Repeated" in d for d in deductions)
    if has_repeated_deduction and recent_history:
        reasoning.append("Your recent history shows repeated junk food choices — this request is part of an emerging pattern worth addressing.")

    # Mood reasoning — ONLY if mood was actually provided
    if mood:
        mood_lower = mood.lower()
        if mood_lower in ("hungry", "starving", "very hungry"):
            reasoning.append(f"Feeling {mood} increases preference for high-reward foods — a protein-rich choice will satisfy hunger more effectively.")
        elif mood_lower in ("stressed", "anxious", "tired", "exhausted"):
            reasoning.append(f"Feeling {mood} elevates cortisol, which drives cravings for sugary or fatty foods — being aware of this helps you choose intentionally.")
        elif mood_lower == "bored":
            reasoning.append("Boredom is one of the most common triggers for unplanned eating — check if you're genuinely hungry before eating.")
        else:
            reasoning.append(f"Your mood ('{mood}') may be influencing this choice — emotional awareness is the first step to better food decisions.")

    # Limit to 3 reasoning items max
    reasoning = reasoning[:3]

    # Intervention message
    if score >= 8:
        intervention_message = f"{food_cap} is an excellent choice right now. You're giving your body exactly what it needs — keep building on these good decisions."
    elif score >= 5:
        parts = [f"You're reaching for {food_cap} during {window}."]
        if food_class == "junk":
            parts.append("It's calorie-dense with limited micronutrients — fine occasionally, but not ideal as a regular meal.")
        if mood and mood.lower() in ("hungry", "starving"):
            parts.append("Since you're hungry, a protein-rich option will keep you fuller longer.")
        elif mood and mood.lower() in ("stressed", "anxious"):
            parts.append(f"Feeling {mood} can trigger impulsive food choices — a short pause before eating often helps.")
        intervention_message = " ".join(parts)
    else:
        parts = [f"This is a high-risk choice: {food_cap} at {window}."]
        if hour >= 22:
            parts.append("Late-night eating slows metabolism and disrupts sleep recovery.")
        if pattern == "late_night_pattern":
            parts.append("This is part of a recurring late-night pattern your body is struggling to recover from.")
        elif pattern == "junk_pattern":
            parts.append("A junk-food habit loop is forming — one intentional swap now has outsized long-term impact.")
        if mood:
            parts.append(f"Your mood ('{mood}') may be amplifying the craving — try a 5-minute pause before eating.")
        parts.append("A small swap now prevents a larger health cost later.")
        intervention_message = " ".join(parts)

    # Future risk
    if score >= 8:
        future_risk = f"No risk detected. Choosing {food_cap} consistently builds a strong nutritional foundation over time."
    elif pattern == "late_night_pattern":
        future_risk = "Recurring late-night eating disrupts sleep quality and slows metabolism — addressing this pattern now prevents compounding effects."
    elif pattern == "junk_pattern":
        future_risk = "A junk-food habit loop is forming. Each repetition makes the next one easier — one intentional swap this week can break the cycle."
    elif food_class == "junk":
        future_risk = "Occasional junk food is low risk, but frequency is what turns single choices into habits worth tracking."
    else:
        future_risk = "Low risk. Consistent moderate-to-good choices compound positively over weeks and months."

    # Better alternatives — context-aware
    if food_class == "healthy" or score >= 8:
        # Complement, don't replace
        complements = {
            "salad": ["grilled chicken or tofu to add protein", "olive oil and nuts for healthy fats", "whole grain bread on the side"],
            "fruit": ["Greek yogurt for protein balance", "a handful of nuts for sustained energy", "cottage cheese for a complete snack"],
            "yogurt": ["fresh berries for antioxidants", "granola for fiber and crunch", "a drizzle of honey and walnuts"],
        }
        better_alternatives = complements.get(food.lower(), [
            f"add a protein source alongside {food_cap} for a complete meal",
            f"pair {food_cap} with healthy fats like avocado or olive oil",
            f"add colorful vegetables to complement {food_cap}",
        ])
    else:
        # Late-night swaps
        late_night_map = {
            "chips": ["small handful of almonds", "cucumber slices", "chamomile tea to reduce cravings"],
            "pizza": ["warm vegetable soup", "light omelette with herbs", "whole grain toast with avocado"],
            "burger": ["warm lentil soup", "small chicken salad", "whole grain toast with nut butter"],
            "fries": ["steamed edamame", "light vegetable broth", "small mixed-nut portion"],
            "soda": ["warm herbal tea", "water with cucumber and mint", "warm milk with turmeric"],
            "donut": ["warm milk", "banana", "small bowl of oats"],
            "nachos": ["plain popcorn", "vegetable sticks", "warm herbal tea"],
        }
        # Regular swaps
        base_map = {
            "chips": ["mixed nuts (same crunch, better fats)", "rice cakes with hummus", "carrot sticks with yogurt dip"],
            "pizza": ["grilled chicken rice bowl (high protein, filling)", "whole grain sandwich with vegetables", "egg avocado wrap"],
            "soda": ["sparkling water with lemon", "fresh fruit juice (no added sugar)", "herbal iced tea"],
            "burger": ["grilled chicken wrap with salad", "veggie burger on whole grain bun", "rice bowl with grilled protein"],
            "fries": ["baked sweet potato wedges", "steamed broccoli with olive oil", "hummus with whole grain pita"],
            "donut": ["banana with peanut butter", "yogurt with granola and berries", "oat energy bar"],
            "candy": ["fresh mixed fruit", "dark chocolate one square (70%+)", "dates with almond butter"],
            "hotdog": ["boiled egg sandwich on whole grain", "tuna salad wrap", "grilled paneer skewer"],
            "nuggets": ["grilled chicken strips with dipping sauce", "paneer tikka with mint chutney", "boiled eggs with crackers"],
            "nachos": ["whole grain crackers with salsa", "vegetable crudites with guacamole", "air-popped popcorn"],
        }
        food_key = food.lower()
        if hour >= 22 and food_key in late_night_map:
            better_alternatives = late_night_map[food_key]
        elif food_key in base_map:
            better_alternatives = base_map[food_key]
        else:
            better_alternatives = [
                "light home-cooked meal with vegetables and protein",
                "fresh seasonal fruit with a protein source",
                "warm soup with whole grain bread",
            ]

    return {
        "reasoning": reasoning,
        "intervention_message": intervention_message,
        "future_risk": future_risk,
        "better_alternatives": better_alternatives,
    }
