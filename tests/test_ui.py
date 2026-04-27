"""
test_ui.py — Live server smoke tests.
Antigravity: start server, run these, then stop server.
Run: pytest tests/test_ui.py -v (server must be running on port 8080)
"""
import pytest
import requests
import time

BASE = "http://localhost:8080"

def _wait_for_server(retries=10, delay=1.0):
    for _ in range(retries):
        try:
            r = requests.get(f"{BASE}/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(delay)
    return False

@pytest.fixture(scope="module", autouse=True)
def server_check():
    if not _wait_for_server():
        pytest.skip("Server not running on port 8080")

def test_ui_root_loads():
    r = requests.get(BASE, timeout=5)
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type","")
    assert "FoodGuard" in r.text or "Food" in r.text

def test_ui_contains_form_elements():
    r = requests.get(BASE, timeout=5)
    html = r.text
    assert 'id="food"' in html
    assert 'id="time"' in html
    assert 'id="analyze-btn"' in html or 'analyze' in html.lower()

def test_ui_has_no_hardcoded_localhost():
    r = requests.get(BASE, timeout=5)
    assert "localhost" not in r.text

def test_health_endpoint_live():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_analyze_endpoint_live():
    r = requests.post(f"{BASE}/analyze",
        json={"food": "chips", "time": "23:00", "mood": "stressed"},
        timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["health_score"] == 4
    assert d["decision"] == "avoid"
    assert len(d["intervention_message"]) > 10
    assert len(d["reasoning"]) >= 1

def test_analyze_healthy_food_live():
    r = requests.post(f"{BASE}/analyze",
        json={"food": "salad", "time": "12:00"},
        timeout=15)
    assert r.status_code == 200
    assert r.json()["decision"] == "good"

def test_analyze_returns_all_fields_live():
    r = requests.post(f"{BASE}/analyze",
        json={"food": "pizza", "time": "21:00", "mood": "hungry"},
        timeout=15)
    d = r.json()
    required = ["health_score","decision","intervention_level","intervention_message",
                "reasoning","pattern_detected","future_risk","better_alternatives","confidence"]
    for field in required:
        assert field in d, f"Missing: {field}"

def test_invalid_input_returns_422_live():
    r = requests.post(f"{BASE}/analyze",
        json={"food": "", "time": "12:00"},
        timeout=5)
    assert r.status_code == 422
