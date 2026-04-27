"""
test_api.py — Full API test suite with corrected expected values.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_history():
    from pathlib import Path
    Path("data/user_history.json").write_text("[]")
    yield

REQUIRED_FIELDS = {
    "health_score","decision","intervention_level","intervention_message",
    "reasoning","pattern_detected","future_risk","better_alternatives","confidence",
}

def _analyze(food, time, mood=None):
    body = {"food": food, "time": time}
    if mood:
        body["mood"] = mood
    return client.post("/analyze", json=body)

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert "ai_powered" in d

def test_root_serves_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]

def test_all_fields_present():
    r = _analyze("chips", "23:00")
    assert r.status_code == 200
    for f in REQUIRED_FIELDS:
        assert f in r.json(), f"Missing: {f}"

# Scoring
def test_salad_midday_is_10():
    d = _analyze("salad", "12:00").json()
    assert d["health_score"] == 10
    assert d["decision"] == "good"
    assert d["pattern_detected"] is None  # no history = no pattern

def test_salad_no_mood_no_mood_reasoning():
    d = _analyze("salad", "12:00").json()
    # No mood provided — reasoning must not mention mood
    combined = " ".join(d["reasoning"]).lower()
    assert "mood" not in combined
    assert "hungry" not in combined
    assert "stressed" not in combined

def test_salad_no_history_no_pattern():
    d = _analyze("salad", "12:00").json()
    assert d["pattern_detected"] is None

def test_chips_late_night():
    d = _analyze("chips", "23:00").json()
    assert d["health_score"] == 4
    assert d["decision"] == "avoid"
    assert d["confidence"] == 0.9

def test_pizza_evening():
    d = _analyze("pizza", "21:00").json()
    assert d["health_score"] == 5
    assert d["decision"] == "moderate"

def test_unknown_food_high_score():
    d = _analyze("broccoli", "10:00").json()
    assert d["health_score"] == 10
    assert d["confidence"] == 0.8  # healthy unknown = 0.8

def test_burger_late():
    d = _analyze("burger", "22:30").json()
    assert d["health_score"] == 4
    assert d["decision"] == "avoid"

def test_salad_confidence():
    d = _analyze("salad", "12:00").json()
    assert d["confidence"] == 0.8  # healthy unknown

def test_score_deterministic():
    scores = []
    for _ in range(3):
        from pathlib import Path
        Path("data/user_history.json").write_text("[]")
        scores.append(_analyze("chips", "23:00").json()["health_score"])
    assert len(set(scores)) == 1

def test_intervention_not_empty():
    d = _analyze("pizza", "13:00", "hungry").json()
    assert len(d["intervention_message"]) > 20

def test_reasoning_nonempty():
    d = _analyze("burger", "20:30").json()
    assert isinstance(d["reasoning"], list)
    assert len(d["reasoning"]) >= 1

def test_alternatives_present():
    d = _analyze("chips", "23:00").json()
    assert len(d["better_alternatives"]) >= 1

def test_healthy_food_alternatives_are_complements():
    d = _analyze("salad", "12:00").json()
    alts = " ".join(d["better_alternatives"]).lower()
    # Should be complements (protein, fats) not generic fallback
    assert "warm soup" not in alts or "protein" in alts or "grain" in alts

def test_invalid_time():
    assert client.post("/analyze", json={"food":"chips","time":"99:99"}).status_code == 422

def test_empty_food():
    assert client.post("/analyze", json={"food":"","time":"12:00"}).status_code == 422

def test_mood_optional():
    assert _analyze("salad", "12:00").status_code == 200

def test_special_chars_rejected():
    assert client.post("/analyze", json={"food":"<script>","time":"12:00"}).status_code == 422
