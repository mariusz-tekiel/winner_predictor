# Winner Predictor

AI-powered football match outcome predictor (1/X/2) based on historical data.

Built with Python FastAPI backend and React.js frontend, using the football-data.org API and a Random Forest machine learning model.

---

## Features

- Predict match outcomes: Home Win (1) / Draw (X) / Away Win (2)
- Animated probability bars for each outcome
- Team form analysis (last 5 matches)
- Head-to-head statistics
- League table positions
- Model training directly from the UI
- Response caching to minimize API calls

---

## Supported Competitions (Free Tier)

- PL — Premier League (England)
- BL1 — Bundesliga (Germany)
- SA — Serie A (Italy)
- PD — La Liga (Spain)
- FL1 — Ligue 1 (France)
- DED — Eredivisie (Netherlands)
- PPL — Primeira Liga (Portugal)
- ELC — Championship (England)
- BSA — Série A (Brazil)
- CL — UEFA Champions League

---

## Tech Stack

- Backend: Python 3.11+, FastAPI, uvicorn
- ML Model: scikit-learn (RandomForestClassifier, 300 trees)
- Data source: football-data.org API v4
- Cache: SQLite (aiosqlite)
- Frontend: React 18, Vite, TanStack Query, CSS Modules

---

## Prerequisites

- Python 3.11+ — https://www.python.org/downloads/
- Node.js 18+ — https://nodejs.org/
- football-data.org API key (free) — https://www.football-data.org/client/register

---

## Installation

### 1. Get a free API key

Register at football-data.org/client/register — email only, no credit card required.

### 2. Configure the API key

Open `backend/.env` and paste your token:

```
FOOTBALL_API_KEY=your_token_here
MODEL_DIR=data/models
CACHE_DB=data/cache.db
DEBUG=false
```

### 3. Install dependencies

Double-click `install.bat` or run manually:

```bash
cd backend
pip install -r requirements.txt

cd ../frontend
npm install
```

### 4. Start the application

Double-click `start.bat` or run in two separate terminals:

```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Open the app at http://localhost:5173

API docs available at http://localhost:8000/docs

---

## How to Use

1. Select a competition from the dropdown in the top-right corner
2. Click "Trenuj model" (Train model) — fetches historical data and trains the model (1-3 minutes)
3. The status bar shows training progress and final accuracy
4. Click any upcoming match from the left panel to see the prediction
5. The right panel shows the predicted outcome, probability bars, team form, H2H record and league positions

---

## ML Model Details

Algorithm: Random Forest Classifier (300 trees, time-based train/test split 80/20)

Features used (18 total):
- Home/away form: points, goals scored, goals conceded, goal difference (last 5 matches)
- Current league position for both teams
- Season points total for both teams
- Head-to-head record: wins, draws, losses, win rate
- Current matchday number

Typical accuracy: 43-52% (random baseline is 33%).

---

## Project Structure

```
winner_predictor/
├── backend/
│   ├── app/          main.py, config.py
│   ├── api/          competitions.py, matches.py, model.py
│   ├── services/     football_api.py, cache.py, predictor.py
│   ├── ml/           feature_engineering.py, trainer.py, model_store.py
│   ├── data/         cache.db, models/ (auto-created)
│   ├── requirements.txt
│   └── .env
└── frontend/
    └── src/
        ├── components/
        └── api/
```

---

## License

MIT
