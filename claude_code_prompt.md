# JackpotPredict: Claude Code Initialization Prompt

---

## COPY THIS ENTIRE PROMPT INTO CLAUDE CODE TO BEGIN DEVELOPMENT

---

```
You are a senior software engineer and game theorist building "JackpotPredict" - a real-time AI inference engine to solve Netflix's "Best Guess Live" game show.

## PROJECT CONTEXT

Best Guess Live is a live mobile trivia game where:
- Players guess a secret Person, Place, or Thing based on 5 progressive clues
- Each clue gets more specific (Clue 1 = cryptic pun, Clue 5 = giveaway)
- You get ONE guess per puzzle - wrong = eliminated
- Earliest correct guessers split the jackpot (up to $10,000)
- Answers must be EXACTLY spelled, full names required ("Paris Hilton" not "Paris")
- 20-second window after each clue to submit

## THE APPLOFF CLUE FRAMEWORK (CRITICAL)

Clues follow a predictable 5-stage pattern:

| Clue # | Type | Technique | Example (Answer: Monopoly) |
|--------|------|-----------|---------------------------|
| 1 | Polysemy Trap | Puns using word's secondary meaning | "Savors many flavors" (editions) |
| 2 | Functional/Attribute | Vague action description | "Round and round" (board) |
| 3 | Pop Culture Pivot | Media/celebrity reference | "A hostile takeover" (theme) |
| 4 | Direct Hint | Factual/contextual clue | "Trespassing will cost you" (rent) |
| 5 | Giveaway | Near-explicit reveal | "Jail time can be dicey" |

## ANSWER DISTRIBUTION (EMPIRICAL)

- **Things: 60%** - Board games, food, brands, objects (Monopoly, Oreo, Umbrella)
- **Places: 25%** - Landmarks, locations (Mt. Rushmore, Hollywood, Eiffel Tower)
- **People: 15%** - Celebrities, characters (Paris Hilton, Barbie, Michael Jordan)

## CORE LOGIC REQUIREMENTS

### 1. Duality Mapper (Clue 1-2 Analysis)
For early clues, prioritize:
- **Polysemy detection**: Words with multiple meanings ("current" = water/electricity/present)
- **Homophone recognition**: Sound-alike words ("knight"/"night")
- **Negative definitions**: "Has X but can't Y" patterns ("Has teeth but cannot bite" = Comb)
- **Metaphor parsing**: Figurative vs literal interpretation

### 2. Functional Mapper (Clue 2-3 Analysis)
Identify:
- Iconic actions associated with entities
- Physical attributes described abstractly
- Cultural/behavioral associations

### 3. Entity Registry
Maintain a curated database of 10,000+ pop-culture entities with:
```python
{
    "canonical_name": "Paris Hilton",  # EXACT spelling for submission
    "aliases": ["Paris", "Hilton"],
    "category": "person",  # person/place/thing
    "polysemy_triggers": ["hotel", "romantic city", "basic"],
    "clue_associations": ["hospitality", "reality TV", "2000s icon"],
    "common_clue_patterns": ["That's hot", "Simple Life", "hotel family"],
    "recency_score": 0.7  # 2025 cultural relevance
}
```

### 4. Bayesian Probability Updater
```python
def update_answer_probabilities(entities, clue_analysis, prior_probs):
    """
    P(answer|all_clues) ∝ P(new_clue|answer) × P(answer|previous_clues)
    
    Key factors:
    - Polysemy match bonus (1.5x if word's alt meaning fits)
    - Category alignment (weight by 60/25/15 distribution)
    - Clue-entity association score
    - Eliminate answers that contradict any clue
    """
    pass
```

### 5. Output Formatting
**CRITICAL**: All outputs must be:
- Exactly spelled (validate against canonical registry)
- Full names ("Michael Jordan" not "MJ" or "Jordan")
- No abbreviations ("International Olympic Committee" not "IOC")
- Case-insensitive but character-perfect

## TECHNICAL SPECIFICATIONS

### Performance Requirements
- **Total pipeline latency**: < 12 seconds (input → ranked output)
- **AI inference per clue**: < 2 seconds
- **UI render**: < 500ms

### Architecture
```
INPUT (clue text) 
    → CLUE ANALYZER (polysemy, metaphor, category signals)
    → ENTITY MATCHER (query registry with semantic similarity)
    → BAYESIAN UPDATER (combine with prior clue probs)
    → SPELLING VALIDATOR (exact match check)
    → RANKER (top 3 with confidence scores)
    → OUTPUT (formatted predictions)
```

### UI Requirements (Dashboard)
Build a React or HTML dashboard with:
1. **Countdown Timer** - Large, color-coded (green→yellow→red as time depletes)
2. **Clue Display** - Current clue prominent, previous clues listed
3. **Top 3 Predictions** - Large text boxes with:
   - Answer (large, high-contrast)
   - Confidence % with visual bar
   - 1-line reasoning
4. **Input Field** - For entering new clues manually
5. **Reset Button** - For new puzzle rounds

Design: Dark theme (#0a0a0a), electric blue accents (#00d4ff), high contrast

## HISTORICAL TRAINING DATA

Use these confirmed answers and clue patterns for few-shot learning:

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

### Example 3: Mt. Rushmore
```
C1: "Natural but not natural" → mountain (natural) + carved faces (man-made)
```

### Example 4: Bowling
```
C1: "Surrounded by success and failure" → pins (success) vs gutter (failure)
```

### Example 5: Oreo
```
C1: "Leader of the pack" → first cookie in the pack
```

### Known Answers to Include in Registry
Barbie, Titanic, Pickleball, Goodyear Blimp, Birthday Cake, M&M's, S'mores, 
Hollywood, Eiffel Tower, Amazon, Beyoncé, Michael Jordan, Piano, Umbrella

## DEVELOPMENT PHASES

### Phase 1: Core Engine (Start Here)
1. Create entity registry data structure with 100 high-probability answers
2. Build clue analysis module (keyword extraction, polysemy detection)
3. Implement simple probability ranking
4. Create CLI for testing: input clues → output ranked guesses

### Phase 2: Enhanced Analysis
1. Add Bayesian probability updates across clues
2. Implement negative definition parser
3. Add category probability tracking
4. Expand registry to 1,000+ entities

### Phase 3: Dashboard UI
1. Build React/HTML interface with Tailwind CSS
2. Implement countdown timer with color states
3. Create prediction card components
4. Add clue history tracking

### Phase 4: Optimization
1. Expand to 10,000+ entities
2. Add web search fallback for unknown references
3. Performance tuning for <2s inference
4. Confidence calibration

## IMMEDIATE FIRST TASK

Create a Python module `jackpot_predict.py` with:

1. `EntityRegistry` class - Store and query pop culture entities
2. `ClueAnalyzer` class - Parse clues for polysemy, metaphors, categories
3. `BayesianUpdater` class - Update probabilities across clue sequence
4. `SpellingValidator` class - Ensure exact-match formatting
5. `JackpotPredict` class - Main orchestrator that:
   - Accepts clue input
   - Maintains state across 5 clues
   - Returns top 3 predictions with confidence scores

Include a simple CLI interface for testing:
```
$ python jackpot_predict.py
Enter Clue 1: Savors many flavors
Analyzing...
Top Predictions:
  1. Monopoly (45%) - "flavors" likely means editions/versions
  2. Ice Cream (30%) - literal interpretation of flavors
  3. Baskin Robbins (15%) - 31 flavors tagline

Enter Clue 2: Round and round
Updating probabilities...
Top Predictions:
  1. Monopoly (78%) - board game, go around
  2. Ferris Wheel (12%) - circular motion
  3. Record Player (5%) - spinning disc
```

## KEY CONSTRAINTS

1. **Speed over perfection** - 12-second max, good-enough beats perfect-but-slow
2. **Spelling is everything** - One typo = elimination, validate aggressively
3. **Full names always** - "Paris Hilton" not "Paris", "Michael Jordan" not "Jordan"
4. **Clue 3 is the decision point** - If confident by C3, recommend guessing
5. **Things > Places > People** - 60/25/15 distribution, weight accordingly

Begin building the core engine now. Start with the entity registry and clue analyzer.
```

---

## USAGE INSTRUCTIONS

1. Copy the entire prompt above (between the ``` markers)
2. Paste into Claude Code as the initial project prompt
3. Claude will begin building the JackpotPredict system
4. Follow up with specific requests as development progresses

## SUGGESTED FOLLOW-UP PROMPTS

After initial build, use these to iterate:

**Expand Entity Registry:**
```
Expand the entity registry to include 500 more entries. Focus on:
- 2024-2025 movies and TV shows
- Viral celebrities and internet culture
- Classic brands and household items
- Major landmarks and cities
Ensure each entry has polysemy_triggers and clue_associations populated.
```

**Build Dashboard UI:**
```
Now build the React dashboard UI. Use:
- Tailwind CSS for styling
- Dark theme with electric blue accents
- Three large prediction cards
- Prominent countdown timer
- Clue input field with history

Make it visually striking and easy to read quickly under time pressure.
```

**Add Real-Time Mode:**
```
Add a "Live Mode" that:
- Starts a 20-second countdown when clue is entered
- Auto-updates predictions as you type
- Flashes the top prediction if confidence > 80%
- Plays a sound at 5 seconds remaining
```

**Performance Optimization:**
```
Profile the inference pipeline and optimize for <2 second response time.
Focus on:
- Entity registry lookup speed
- Probability calculation efficiency
- Caching frequently accessed entities
```

---

## APPENDIX: Quick Reference

### Answer Format Rules
| Wrong ❌ | Correct ✅ |
|---------|-----------|
| Paris | Paris Hilton |
| Jordan | Michael Jordan |
| IOC | International Olympic Committee |
| The Eiffel Tower | Eiffel Tower |
| mt rushmore | Mt. Rushmore |

### Clue Pattern Cheat Sheet
| Pattern | Meaning | Example |
|---------|---------|---------|
| "Has X but can't Y" | Negative definition | Comb (teeth, no bite) |
| "Natural but not" | Man-made in nature | Mt. Rushmore |
| "Many flavors/versions" | Product with variants | Monopoly |
| "Leader of the pack" | First in series | Oreo |
| City + descriptor | Celebrity named after place | Paris Hilton |

### Category Priors
- Start with: Thing 60%, Place 25%, Person 15%
- Update based on clue signals (pronouns, verbs, etc.)
