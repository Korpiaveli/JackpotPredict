# JackpotPredict

> AI-powered real-time inference engine for Netflix's "Best Guess Live" game show

## Overview

JackpotPredict analyzes 5 progressive clues and predicts answers within a 12-second window, outputting top 3 predictions with confidence scores. Designed to maximize early-clue correct guesses where jackpot payouts are highest.

**Now powered by Google Gemini 2.0 Flash** - No local GPU required!

## Features

- **Gemini 2.0 Flash AI** - Fast, accurate predictions using Google's latest model
- **Self-Validating Predictions** - Semantic match scoring prevents phonetic confusion
- **Few-Shot Learning** - Learns from historical game patterns
- **Error Pattern Tracking** - Records mistakes to improve future predictions
- **Real-time Dashboard** - Beautiful React frontend with live predictions
- **Cross-Platform** - Works on Windows, macOS, and Linux

## Game Context

**Best Guess Live** is a Netflix mobile trivia game where:
- Players guess a Person, Place, or Thing based on 5 progressive clues
- Each clue gets more specific (Clue 1 = cryptic pun, Clue 5 = giveaway)
- ONE guess per puzzle - wrong = eliminated
- Earliest correct guessers split up to $10,000 jackpot
- Answers must be EXACTLY spelled (full names, no abbreviations)

## Quick Start

### Prerequisites

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **Gemini API Key** (free) - [Get API Key](https://aistudio.google.com/app/apikey)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/JackpotPredict.git
cd JackpotPredict

# 2. Run automated setup (installs all dependencies)
python setup.py

# 3. Configure your API key
# Edit backend/.env and add your GEMINI_API_KEY
```

### Running the Application

```bash
# Start both backend and frontend
python run.py
```

**Access the application:**
- **Frontend Dashboard**: http://localhost:5173
- **Backend API Docs**: http://localhost:8000/docs

### Command Options

```bash
python run.py              # Start both servers
python run.py --backend    # Backend only
python run.py --frontend   # Frontend only
python run.py --build      # Build frontend for production

python setup.py            # Full setup
python setup.py --check    # Check installation status
python setup.py --update   # Update dependencies only
```

## Architecture

### Gemini-First Design (v2.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PREDICTION FLOW                               │
└─────────────────────────────────────────────────────────────────┘

Clue Input ──→ Context Manager ──→ Gemini 2.0 Flash ──→ Response Parser
                     │                    │                   │
                     ▼                    ▼                   ▼
              Few-shot Examples    Self-Validation    Confidence Scoring
              (history.json)       (semantic match)   (penalty for weak)
                     │                    │                   │
                     └──────────── Top 3 Predictions ─────────┘
```

### Backend (Python + FastAPI)
- **JackpotPredict** - Main orchestrator with Gemini integration
- **ContextManager** - Few-shot learning from historical games
- **SpellingValidator** - Exact match validation (critical - one typo = elimination)
- **EntityRegistry** - 2,500+ pop culture entities for validation

### Frontend (React + TypeScript + Vite)
- **Dark theme** optimized for speed reading under time pressure
- **Countdown timer** with color-coded warnings (green→yellow→red)
- **Top 3 prediction cards** with confidence bars and semantic match badges
- **Real-time updates** via REST polling
- **Mobile responsive** for dual-screen gameplay

## Project Structure

```
JackpotPredict/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes & models
│   │   ├── core/             # Prediction engine & Gemini integration
│   │   │   ├── jackpot_predict.py    # Main orchestrator
│   │   │   ├── gemini_predictor.py   # Gemini API wrapper
│   │   │   └── context_manager.py    # Few-shot learning
│   │   └── data/             # Learning data
│   │       ├── history.json          # Past game results
│   │       └── error_patterns.json   # Tracked mistakes
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom React hooks
│   │   └── store/            # State management
│   └── package.json
├── setup.py                  # Cross-platform installer
├── run.py                    # Unified run script
└── README.md
```

## Configuration

Edit `backend/.env` with your settings:

```env
# Required: Gemini API Key (free tier: 1,500 requests/day)
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash

# Optional: Inference settings
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=500
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/predict` | POST | Submit clue and get predictions |
| `/api/reset` | POST | Reset session for new puzzle |
| `/api/validate` | POST | Validate answer spelling |
| `/api/feedback` | POST | Submit puzzle feedback for learning |
| `/api/health` | GET | Health check and metrics |

## Learning System

JackpotPredict improves over time through:

### 1. History Tracking (`history.json`)
Records past puzzles and solutions for few-shot learning:
```json
{
  "category": "thing",
  "clues": ["Savors many flavors", "A hostile takeover"],
  "answer": "Monopoly",
  "key_insight": "'hostile takeover' is business term used in the board game"
}
```

### 2. Error Patterns (`error_patterns.json`)
Tracks prediction mistakes to prevent repetition:
```json
{
  "predicted": "Frasier",
  "correct": "Eraser",
  "error_type": "phonetic_confusion",
  "clues_sample": ["removes pencil marks"]
}
```

### 3. Self-Validation
Each prediction includes semantic match scoring:
- **Strong** (green) - High confidence in meaning match
- **Medium** (yellow) - Possible but uncertain
- **Weak** (red) - Sounds similar but meaning unclear

## Deploying to Another Machine

```bash
# 1. Clone from GitHub (includes learning data)
git clone https://github.com/yourusername/JackpotPredict.git
cd JackpotPredict

# 2. Run setup
python setup.py

# 3. Configure API key
cp backend/.env.example backend/.env
# Edit backend/.env and add your GEMINI_API_KEY

# 4. Run the application
python run.py
```

**Note:** Learning data files (`history.json`, `error_patterns.json`) are tracked in git, so your learned patterns sync across machines.

## Historical Puzzle Examples

### Example 1: Paris Hilton
```
C1: "Back to the basics" → The Simple Life reference
C2: "Loud with the crowd" → DJ/celebrity status
C3: "A sensation and a destination" → fame + city name
C4: "Her family is extremely hospitable" → Hilton Hotels
C5: "Named after a romantic city? That's hot." → Paris + catchphrase
```

### Example 2: Monopoly
```
C1: "Savors many flavors" → many themed editions
C2: "Round and round" → circling the board
C3: "A hostile takeover" → economic/property theme
C4: "Trespassing will cost you" → rent mechanic
C5: "Jail time can be dicey" → jail square + dice
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (needs 3.10+)
- Verify setup completed: `python setup.py --check`
- Check API key: Ensure `GEMINI_API_KEY` is set in `backend/.env`

### Frontend won't start
- Check Node version: `node --version` (needs 18+)
- Verify dependencies: Run `python setup.py` again
- Try manual install: `cd frontend && npm install`

### Predictions are slow
- Gemini API typically responds in 1-2 seconds
- Check your internet connection
- Free tier has rate limits (1,500 requests/day)

### Wrong predictions (e.g., "Frasier" vs "Eraser")
- Self-validation should prevent most phonetic confusion
- Submit feedback via `/api/feedback` to record the error
- Error patterns are learned and injected into future prompts

## Success Metrics

| Metric | Target |
|--------|--------|
| Correct answer in Top 3 by Clue 3 | >70% |
| Correct answer as #1 by Clue 4 | >85% |
| Inference latency | <2s |
| Spelling accuracy | 100% |

## Tech Stack

**Backend:**
- Python 3.10+
- FastAPI 0.104+
- Google Gemini 2.0 Flash API
- spaCy 3.7+ (NLP processing)
- SQLite (entity registry)

**Frontend:**
- React 18.2 + TypeScript 5.3
- Vite 5.0
- TailwindCSS 3.4
- React Query 5.0
- Zustand 4.4
- Framer Motion 10.16

## License

MIT License - See LICENSE for details.

## Acknowledgments

- Built with Claude Code (Anthropic)
- [Google Gemini](https://ai.google.dev/) - AI prediction engine
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) + [Vite](https://vitejs.dev/) - Frontend stack
- [Tailwind CSS](https://tailwindcss.com/) - Styling

---

**Status**: 🟢 Production Ready (v2.0)
**Last Updated**: December 22, 2025
