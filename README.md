# 🥗 FoodGuard — Real-Time Food Intervention System

AI-powered food decision interceptor. Analyzes food choices in real-time based on type, time of day, mood, and behavioral patterns.

## Vertical
Health & Wellness — Real-time behavioral intervention for food decisions.

## Approach and Logic
The system uses a multi-agent pipeline:
1. **Scoring Agent** — Deterministic health score (1–10) based on food type and nutritional profile
2. **Context Agent** — Adjusts score based on time of day and mood; determines intervention level
3. **Behavior Agent** — Detects patterns (e.g. repeated late-night junk food)
4. **Recommendation Agent** — Suggests healthier alternatives
5. **AI Agent** — Optional AI-powered analysis layer for richer coaching messages

## How the Solution Works
User submits food + time + mood via the web UI or POST /analyze.
The agents run in sequence and return a health score, decision (good/moderate/avoid), an intervention message, detected behavioral patterns, future risk assessment, and alternatives.
History is stored locally in data/user_history.json (Firebase integration available).

## Assumptions Made
- Food names are matched against a built-in nutrition database; unknown foods default to score 10 (no penalty for unknown items)
- Time is in HH:MM 24-hour format
- Mood is optional (defaults to neutral)
- Firebase is optional; system works fully with local JSON fallback

## Live Demo
Deployed on Google Cloud Run (asia-south1 — Mumbai region).

## Architecture
app/
main.py                    — FastAPI app, serves UI at /
agents/
scoring_agent.py         — Deterministic health score (1-10)
context_agent.py         — Intervention level and decision
behavior_agent.py        — Pattern detection
recommendation_agent.py  — Food alternatives
ai_agent.py              — AI-powered analysis layer
data/user_history.json       — Local fallback storage
index.html                   — Light-theme UI (served at /)
Dockerfile                   — Cloud Run ready

## Setup
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```
Open browser at `http://localhost:8080`

## API

### GET /health
```json
{"status": "ok", "firebase": false, "ai_powered": false, "version": "3.0.0"}
```

### POST /analyze
Request:
```json
{"food": "chips", "time": "23:00", "mood": "stressed"}
```
Response:
```json
{
  "health_score": 4,
  "decision": "avoid",
  "intervention_level": "strong",
  "intervention_message": "...",
  "reasoning": ["..."],
  "pattern_detected": null,
  "future_risk": "...",
  "better_alternatives": ["..."],
  "confidence": 0.9
}
```

## Test Cases
| Food | Time | Expected Score | Expected Decision |
|------|------|---------------|-------------------|
| chips | 23:00 | 4 | avoid |
| salad | 12:00 | 10 | good |
| pizza | 21:00 | 5 | moderate |
| burger | 22:30 | 4 | avoid |
| unknownfood | 10:00 | 10 | good |

## Deploy to Cloud Run
```bash
gcloud run deploy food-intervention-api \
  --source . --platform managed \
  --region asia-south1 --allow-unauthenticated --port 8080
```

## License
MIT
