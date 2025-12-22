# JackpotPredict

> AI-powered real-time inference engine for Netflix's "Best Guess Live" game show

## Overview

JackpotPredict analyzes 5 progressive clues and predicts answers within a 12-second window, outputting top 3 predictions with confidence scores. Designed to maximize early-clue correct guesses where jackpot payouts are highest.

## Game Context

**Best Guess Live** is a Netflix mobile trivia game where:
- Players guess a Person, Place, or Thing based on 5 progressive clues
- Each clue gets more specific (Clue 1 = cryptic pun, Clue 5 = giveaway)
- ONE guess per puzzle - wrong = eliminated
- Earliest correct guessers split up to $10,000 jackpot
- Answers must be EXACTLY spelled (full names, no abbreviations)

## Architecture

### Backend (Python + FastAPI)
- **EntityRegistry**: 10,000+ pop culture entities with semantic metadata
- **ClueAnalyzer**: Polysemy detection, metaphor parsing, NLP analysis
- **BayesianUpdater**: Probability calculations using P(answer|clues)
- **SpellingValidator**: Exact match validation (critical - one typo = elimination)
- **JackpotPredict**: Main orchestrator with session management

### Frontend (React + TypeScript + Vite)
- **Dark theme** optimized for speed reading under time pressure
- **Countdown timer** with color-coded warnings (green→yellow→red)
- **Top 3 prediction cards** with confidence bars and reasoning
- **Real-time updates** via WebSocket or REST polling
- **Mobile responsive** for dual-screen gameplay

### Tech Stack

**Backend:**
- Python 3.11+
- FastAPI 0.104+
- spaCy 3.7+ with en_core_web_lg
- SQLite (entity registry)
- Pydantic 2.5+

**Frontend:**
- React 18.2 + TypeScript 5.3
- Vite 5.0
- TailwindCSS 3.4
- React Query 5.0
- Zustand 4.4
- Framer Motion 10.16

## Project Structure

```
jackpot-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── core/                # Core inference engine
│   │   ├── api/                 # REST API endpoints
│   │   ├── utils/               # Helpers
│   │   └── data/                # Entity database
│   ├── tests/                   # Test suite
│   ├── scripts/                 # Data population scripts
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # UI components
│   │   ├── hooks/               # Custom React hooks
│   │   └── store/               # State management
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Installation

**1. Clone the repository:**
```bash
git clone <repository-url>
cd Jackpot-App
```

**2. Backend setup:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

**3. Frontend setup:**
```bash
cd frontend
npm install
```

### Running the Application

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` to use the dashboard.

## Key Features

### Apploff Clue Framework Detection
The system understands the 5-stage clue pattern:
1. **Polysemy Trap** - Puns using word's secondary meaning
2. **Functional/Attribute** - Vague action descriptions
3. **Pop Culture Pivot** - Media/celebrity references
4. **Direct Hint** - Factual/contextual clues
5. **Giveaway** - Near-explicit reveal

### Answer Distribution Priors
- **Things**: 60% (board games, food, brands, objects)
- **Places**: 25% (landmarks, locations)
- **People**: 15% (celebrities, characters)

### Performance Targets
- **Total pipeline latency**: < 12 seconds
- **AI inference per clue**: < 2 seconds
- **UI render**: < 500ms

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

## Testing

**Run backend tests:**
```bash
cd backend
pytest tests/ -v
```

**Run frontend tests:**
```bash
cd frontend
npm run test
```

## Deployment

### Backend
- Deploy to Railway, Render, or similar Python hosting
- Requires: Python 3.11+, 1GB RAM minimum
- Set environment variables for API keys

### Frontend
- Deploy to Vercel (recommended)
- Build command: `npm run build`
- Output directory: `dist`

## Contributing

This is a personal project for Netflix's Best Guess Live game show. See [PLAN.md](../.claude/plans/elegant-wishing-hammock.md) for detailed implementation roadmap.

## Success Metrics

| Metric | Target |
|--------|--------|
| Correct answer in Top 3 by Clue 3 | >70% |
| Correct answer as #1 by Clue 4 | >85% |
| Inference latency | <2s |
| Spelling accuracy | 100% |

## License

MIT

## Acknowledgments

- Built with Claude Code (Anthropic)
- Inspired by the Apploff Clue Framework analysis
- Leverages production patterns from:
  - prediction-markets-arbitrage (embedding service, ML matching)
  - Epstein-Investigator (entity extraction, NLP)
  - AICompanion (WebSocket real-time, React components)

---

**Status**: 🚧 Active Development
**Version**: 0.1.0
**Last Updated**: December 21, 2025
