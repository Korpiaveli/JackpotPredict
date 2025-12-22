# JackpotPredict: AI-Powered Best Guess Live Assistant

## Product Requirements Document (PRD)
**Version:** 1.0  
**Date:** December 21, 2025  
**Author:** Matt (with Claude Research)

---

## Executive Summary

JackpotPredict is a real-time AI inference engine designed to assist players of Netflix's "Best Guess Live" game show. The system ingests progressive clues, applies game-specific semantic analysis, and generates ranked probability lists of potential answers within a 12-second reaction window. The goal is to maximize early-clue correct guesses where jackpot payouts are highest.

---

## Game Context & Mechanics

### Show Format
- **Platform:** Netflix mobile app (Best Guess Live)
- **Schedule:** Weeknights 8 PM ET / 5 PM PT
- **Structure:** 2 puzzles per episode (~30 min total, 6-8 min per puzzle)
- **Prize Pool:** $5,000 (Puzzle 1) + $10,000 (Puzzle 2) = $15,000 daily

### Core Rules
| Rule | Detail |
|------|--------|
| **Clues** | 5 progressive clues, revealed sequentially |
| **Time Window** | 20 seconds after each clue to submit |
| **Guess Limit** | ONE guess per puzzle (wrong = elimination) |
| **Spelling** | Must be exact (case-insensitive, no abbreviations) |
| **Winner Selection** | Earliest correct guessers split the jackpot |
| **Full Names Required** | "Paris Hilton" not "Paris"; "International Olympic Committee" not "IOC" |

### Clue Progression Pattern (Apploff Framework)
| Clue # | Type | Description | Example (Monopoly) |
|--------|------|-------------|-------------------|
| 1 | **Polysemy Trap** | Pun/duality using word's secondary meaning | "Savors many flavors" |
| 2 | **Functional/Attribute** | Vague action or characteristic | "Round and round" |
| 3 | **Pop Culture Pivot** | Reference to media, celebrity, or cultural touchstone | "A hostile takeover" |
| 4 | **Direct Hint** | Factual or contextual clue | "Trespassing will cost you" |
| 5 | **Giveaway** | Near-explicit answer reveal | "Jail time can be dicey" |

### Answer Distribution (Documented)
- **Things:** 60% (household items, games, food, brands)
- **Places:** 25% (landmarks, locations with dual meanings)
- **People:** 15% (celebrities, fictional characters, single-name icons)

---

## Historical Answer Database

### Confirmed Answers from First Two Weeks
| Answer | Category | Notable Clue Pattern |
|--------|----------|---------------------|
| Paris Hilton | Person | "Back to basics" (Simple Life), "That's hot" |
| Monopoly | Thing | "Savors many flavors" (editions), "Jail time can be dicey" |
| Barbie | Person/Thing | First puzzle ever; guessed on Clue 1 |
| Titanic | Thing | "Ups and downs," split references |
| Mt. Rushmore | Place | "Natural but not natural" |
| Oreo | Thing | "Leader of the pack" (first cookie) |
| Bowling | Thing | "Surrounded by success and failure" |
| Pickleball | Thing | Guessed on Clue 1 |
| Goodyear Blimp | Thing | Likely "high above the crowd" style clue |
| Birthday Cake | Thing | "Layers of celebration" style |
| M&M's | Thing | Colorful, melting references |

### Common Clue Tropes
- **"Leader of the pack"** → First item in a package/group (Oreo)
- **"Natural but not natural"** → Man-made landmark in nature (Mt. Rushmore)
- **"Savors many flavors"** → Product with many variations (Monopoly editions)
- **"Surrounded by success and failure"** → Metaphorical context (Bowling: strikes vs gutters)
- **Hotel/hospitality references** → Hilton family connection

---

## Technical Requirements

### Performance Specifications
| Metric | Requirement |
|--------|-------------|
| **Total Response Time** | < 12 seconds (input → display) |
| **AI Inference Latency** | < 2 seconds per clue |
| **UI Render Time** | < 500ms |
| **Entity Database Size** | 10,000+ pop culture entities |
| **Concurrent Users** | Single user (personal assistant) |

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     JACKPOTPREDICT PIPELINE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┐    ┌──────────────┐    ┌───────────────────┐   │
│  │   INPUT   │───▶│   ANALYSIS   │───▶│     INFERENCE     │   │
│  │  MODULE   │    │    ENGINE    │    │      ENGINE       │   │
│  └───────────┘    └──────────────┘    └───────────────────┘   │
│       │                  │                      │              │
│       ▼                  ▼                      ▼              │
│  ┌───────────┐    ┌──────────────┐    ┌───────────────────┐   │
│  │  Manual   │    │  Polysemy    │    │  Bayesian Weight  │   │
│  │  Text     │    │  Detection   │    │     Updater       │   │
│  │  Entry    │    │              │    │                   │   │
│  └───────────┘    └──────────────┘    └───────────────────┘   │
│                          │                      │              │
│                          ▼                      ▼              │
│                   ┌──────────────┐    ┌───────────────────┐   │
│                   │  Category    │    │  Entity Registry  │   │
│                   │  Classifier  │    │   (10K+ items)    │   │
│                   └──────────────┘    └───────────────────┘   │
│                          │                      │              │
│                          └──────────┬───────────┘              │
│                                     ▼                          │
│                          ┌───────────────────┐                 │
│                          │   RANKING MODULE  │                 │
│                          │  ┌─────────────┐  │                 │
│                          │  │ Confidence  │  │                 │
│                          │  │   Scorer    │  │                 │
│                          │  └─────────────┘  │                 │
│                          │  ┌─────────────┐  │                 │
│                          │  │  Spelling   │  │                 │
│                          │  │  Validator  │  │                 │
│                          │  └─────────────┘  │                 │
│                          └───────────────────┘                 │
│                                     │                          │
│                                     ▼                          │
│                          ┌───────────────────┐                 │
│                          │   OUTPUT / UI     │                 │
│                          │  Top 3 Guesses    │                 │
│                          │  + Confidence %   │                 │
│                          │  + Countdown      │                 │
│                          └───────────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Core Modules

#### 1. Clue Analysis Engine
**Purpose:** Parse and interpret each clue for multiple semantic meanings

**Components:**
- **Polysemy Detector:** Identify words with multiple meanings (e.g., "current" = electricity/water/present)
- **Metaphor Parser:** Detect figurative language patterns
- **Negative Definition Handler:** Recognize "has X but can't Y" patterns
- **Category Signals:** Extract hints about Person/Place/Thing

**Processing Flow:**
```python
def analyze_clue(clue_text, clue_number, previous_clues):
    # Extract key terms and their alternate meanings
    polysemous_terms = detect_polysemy(clue_text)
    
    # Identify clue type based on position
    clue_type = classify_clue_type(clue_number)  # polysemy/functional/pivot/direct/giveaway
    
    # Parse for negative definitions ("has X but can't Y")
    negative_patterns = extract_negative_definitions(clue_text)
    
    # Infer category probabilities
    category_probs = {
        "thing": 0.60,  # Base prior
        "place": 0.25,
        "person": 0.15
    }
    category_probs = update_category_probs(clue_text, previous_clues, category_probs)
    
    return {
        "polysemous_terms": polysemous_terms,
        "clue_type": clue_type,
        "negative_patterns": negative_patterns,
        "category_probs": category_probs
    }
```

#### 2. Entity Registry
**Purpose:** Curated database of 10,000+ pop culture answers

**Categories:**
| Category | Examples | Est. Count |
|----------|----------|------------|
| Celebrities | Paris Hilton, Beyoncé, Michael Jordan | 2,000 |
| Movies/TV | Titanic, Barbie, Stranger Things | 1,500 |
| Brands/Products | Monopoly, Oreo, M&M's, Nike | 1,500 |
| Landmarks | Mt. Rushmore, Eiffel Tower, Hollywood | 1,000 |
| Food/Drinks | Birthday Cake, S'mores, Pizza | 1,000 |
| Games/Sports | Bowling, Pickleball, Chess | 500 |
| Characters | Barbie, Grinch, Santa Claus | 1,000 |
| Miscellaneous | Goodyear Blimp, Umbrella, Piano | 1,500 |

**Entity Schema:**
```python
{
    "canonical_name": "Paris Hilton",  # Exact spelling required
    "aliases": ["Paris", "Hilton"],
    "category": "person",
    "attributes": {
        "family": "hotel dynasty",
        "catchphrase": "That's hot",
        "shows": ["The Simple Life"],
        "city_name": True
    },
    "polysemy_triggers": ["romantic city", "hotel", "basic"],
    "clue_associations": [
        "hospitality",
        "reality TV",
        "2000s icon"
    ],
    "recency_score": 0.7  # How culturally relevant in 2025
}
```

#### 3. Bayesian Inference Engine
**Purpose:** Update answer probabilities as clues accumulate

**Algorithm:**
```python
def update_probabilities(entities, new_clue_analysis, previous_probs):
    """
    Bayesian update: P(answer|clues) ∝ P(clues|answer) × P(answer)
    """
    updated_probs = {}
    
    for entity in entities:
        # Prior probability (from previous clues or base rate)
        prior = previous_probs.get(entity.canonical_name, entity.base_probability)
        
        # Likelihood: How well does this clue match the entity?
        likelihood = compute_clue_match_score(new_clue_analysis, entity)
        
        # Polysemy bonus: Extra weight for entities with multiple meanings
        if has_polysemy_match(new_clue_analysis.polysemous_terms, entity):
            likelihood *= 1.5
        
        # Category alignment
        category_multiplier = new_clue_analysis.category_probs[entity.category]
        
        # Posterior (unnormalized)
        posterior = prior * likelihood * category_multiplier
        updated_probs[entity.canonical_name] = posterior
    
    # Normalize
    total = sum(updated_probs.values())
    return {k: v/total for k, v in updated_probs.items()}
```

#### 4. Spelling Validator
**Purpose:** Ensure output matches exact game requirements

**Rules:**
- Full names required ("Michael Jordan" not "Jordan")
- No abbreviations ("International Olympic Committee" not "IOC")
- No articles unless part of official name
- Case-insensitive but spelling-exact

```python
def validate_and_format(guess, entity_registry):
    # Find canonical spelling
    canonical = entity_registry.get_canonical(guess)
    if not canonical:
        return {"valid": False, "suggestion": fuzzy_match(guess)}
    
    # Check for common mistakes
    if is_partial_name(guess, canonical):
        return {"valid": False, "error": f"Use full name: {canonical}"}
    
    if is_abbreviation(guess, canonical):
        return {"valid": False, "error": f"Spell out fully: {canonical}"}
    
    return {"valid": True, "formatted": canonical}
```

---

## User Interface Requirements

### Design Philosophy
- **"Lean & Mean"** - Maximum information density, minimal cognitive load
- **High Contrast** - Instant readability under any conditions
- **Speed-Optimized** - Every millisecond counts with 20-second windows

### UI Layout

```
┌────────────────────────────────────────────────────────────────┐
│  ⏱️ COUNTDOWN: 17 seconds                    [PUZZLE 1 of 2]  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  CLUE 3: "A hostile takeover"                                  │
│  ─────────────────────────────                                 │
│  Previous: "Savors many flavors" → "Round and round"           │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  🥇 #1: MONOPOLY                              87% ████▓  │ │
│  │     Board game • "flavors" = editions, "hostile" = $$    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  🥈 #2: AMAZON                                12% █▓     │ │
│  │     Company • "takeover" = acquisitions                  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  🥉 #3: HOSTILE (Movie)                        1% ▓      │ │
│  │     Film • direct title match                            │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  [ENTER NEW CLUE]                              [RESET PUZZLE]  │
└────────────────────────────────────────────────────────────────┘
```

### UI Components

#### 1. Countdown Timer
- Large, prominent display
- Color shifts: Green (15-20s) → Yellow (8-14s) → Red (0-7s)
- Audio/vibration option at 5 seconds

#### 2. Clue Display Panel
- Current clue prominently displayed
- Previous clues visible but subdued
- Clue number clearly indicated (1-5)

#### 3. Top 3 Prediction Cards
Each card displays:
- Rank indicator (🥇🥈🥉)
- **Answer in large, high-contrast text**
- Confidence percentage with visual bar
- Brief reasoning (1-line explanation)
- Copy-to-clipboard button

#### 4. Input Area
- Text field for manual clue entry
- "Reset Puzzle" button for new round
- History of current puzzle's clues

### Visual Design Specifications
| Element | Specification |
|---------|---------------|
| **Primary Font** | Mono/fixed-width for answers (ensures spacing) |
| **Background** | Dark (#0a0a0a) for reduced eye strain |
| **Accent Color** | Electric blue (#00d4ff) for high confidence |
| **Warning Color** | Amber (#ffc107) for medium confidence |
| **Danger Color** | Coral (#ff6b6b) for low confidence |
| **Card Borders** | Subtle glow matching confidence level |

---

## AI Inference Strategies

### Clue 1 Strategy: "Spray and Pray"
- Generate 5-7 diverse guesses across all categories
- Prioritize entities with high polysemy scores
- Include one "wild shot" based on abstract interpretation
- Weight toward culturally salient answers (recent movies, viral topics)

### Clue 2 Strategy: "Category Lock"
- Cross-reference Clue 1 + Clue 2 for pattern alignment
- Eliminate guesses that contradict new information
- Begin narrowing to probable category (Thing/Place/Person)
- Maintain 3-5 candidates

### Clue 3 Strategy: "Pivot Point"
- Identify pop culture reference or specific fact
- This is typically where answer becomes inferrable
- High-confidence threshold (>70%) triggers recommendation to guess
- Reduce to 2-3 top candidates

### Clue 4-5 Strategy: "Confirmation Mode"
- Should have single clear answer by Clue 4
- Focus on spelling validation
- If still multiple candidates, rank by most specific match
- Clue 5 = "if you haven't guessed, guess now"

---

## Risk/Reward Heuristics

### When to Recommend Guessing Early
| Clue # | Confidence Threshold | Rationale |
|--------|---------------------|-----------|
| 1 | >50% (rare) | Only if strong polysemy match to iconic answer |
| 2 | >65% | Two clues align perfectly with single entity |
| 3 | >75% | Pop culture pivot confirms hypothesis |
| 4 | >85% | Direct hint validates; most winners here |
| 5 | Any | Last chance, must guess |

### Expected Value Calculation
```python
def calculate_expected_value(confidence, clue_number, estimated_winners):
    """
    EV = P(correct) × (Jackpot / Expected_Winners) - P(wrong) × Future_Value
    """
    jackpot = 10000  # Example: Puzzle 2
    
    # Estimated winners at each clue level (based on game data)
    typical_winners = {
        1: 1,      # Solo jackpot if right
        2: 3,      # Very few get it
        3: 25,     # Some figure it out
        4: 200,    # Many get it
        5: 1000    # Most remaining players
    }
    
    expected_winners = max(estimated_winners, typical_winners[clue_number])
    payout_if_correct = jackpot / expected_winners
    
    # Future value: probability of winning on later clue × expected payout
    future_value = estimate_future_value(clue_number, confidence)
    
    ev_guess_now = confidence * payout_if_correct - (1 - confidence) * future_value
    ev_wait = future_value
    
    return {
        "ev_guess": ev_guess_now,
        "ev_wait": ev_wait,
        "recommendation": "GUESS NOW" if ev_guess_now > ev_wait else "WAIT"
    }
```

---

## Development Phases

### Phase 1: Core Engine (MVP)
- [ ] Entity registry with 1,000 high-frequency answers
- [ ] Basic clue analysis (keyword extraction)
- [ ] Simple probability ranking
- [ ] CLI interface for testing
- **Timeline:** 2-3 days

### Phase 2: Enhanced Analysis
- [ ] Polysemy detection system
- [ ] Negative definition parser
- [ ] Category probability updates
- [ ] Historical clue pattern matching
- **Timeline:** 3-4 days

### Phase 3: UI Dashboard
- [ ] React/HTML dashboard with Tailwind
- [ ] Real-time countdown timer
- [ ] Top 3 prediction cards
- [ ] Clue history panel
- **Timeline:** 2-3 days

### Phase 4: Optimization
- [ ] Expand entity registry to 10,000+
- [ ] Add web search fallback for unknown entities
- [ ] Confidence calibration based on actual results
- [ ] Performance tuning (<2s inference)
- **Timeline:** 3-5 days

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Correct answer in Top 3 by Clue 3 | >70% | Manual testing on historical puzzles |
| Correct answer as #1 by Clue 4 | >85% | Manual testing |
| Inference latency | <2 seconds | Automated timing |
| Full pipeline latency | <12 seconds | End-to-end testing |
| Spelling accuracy | 100% | Validator unit tests |

---

## Appendix: Sample Few-Shot Training Data

### Example 1: Paris Hilton
```
Clue 1: "Back to the basics"
Clue 2: "Loud with the crowd"  
Clue 3: "A sensation and a destination"
Clue 4: "Her family is extremely hospitable"
Clue 5: "Named after a romantic city? That's hot."
Answer: Paris Hilton

Analysis:
- C1: "basics" → The Simple Life show theme
- C2: "loud"/"crowd" → DJ career, celebrity status
- C3: "sensation" = celebrity, "destination" = city name hint
- C4: "hospitable"/"family" → Hilton Hotels
- C5: "Paris" (city) + "That's hot" (catchphrase)
```

### Example 2: Monopoly
```
Clue 1: "Savors many flavors"
Clue 2: "Round and round"
Clue 3: "A hostile takeover"
Clue 4: "Trespassing will cost you"
Clue 5: "Jail time can be dicey"
Answer: Monopoly

Analysis:
- C1: "flavors" = many themed editions (polysemy trap)
- C2: "round" = circling the board
- C3: "takeover" = buying properties, economic theme
- C4: "trespassing cost" = landing on owned property = rent
- C5: "jail" + "dicey" = Go to Jail + dice mechanics
```

### Example 3: Mt. Rushmore
```
Clue 1: "Natural but not natural"
Clue 2: [Unknown]
Clue 3: [Unknown]
Clue 4: [Unknown]
Clue 5: [Unknown]
Answer: Mt. Rushmore

Analysis:
- C1: Mountain (natural) with carved faces (not natural) - perfect negative definition
```

---

## Document Metadata
- **Status:** Ready for Development
- **Priority:** High (Holiday $1M jackpot week Dec 22-26)
- **Owner:** Matt
- **AI Assistant:** Claude (development partner)
