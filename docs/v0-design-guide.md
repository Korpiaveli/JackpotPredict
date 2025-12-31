# JackpotPredict UI Design Guide for Vercel v0

## Executive Summary

JackpotPredict is a real-time trivia prediction system for Netflix's "Best Guess Live" game show. It uses a **Mixture of Agents (MoA)** architecture with 5 specialized AI agents + an Oracle meta-synthesizer to predict answers from cryptic clues.

**Primary User Goal**: Get the best possible answer prediction within seconds, with confidence levels to inform betting/guessing decisions.

**Core UX Principle**: Information density with clarity. Users need to see multiple predictions, confidence levels, and reasoning at a glance while under time pressure.

---

## 1. Application Context

### What This App Does
1. User enters a cryptic trivia clue (up to 5 clues per puzzle)
2. 5 specialized AI agents analyze the clue in parallel
3. An Oracle (Claude Sonnet 4) synthesizes all predictions into a final recommendation
4. User sees: recommended answer, confidence %, agent consensus, trap detection, cultural references
5. Process repeats for clues 2-5, with confidence evolving
6. After puzzle ends, user provides feedback with correct answer

### Time Pressure Context
- Netflix's game show has ~20 seconds between clues
- Users need to quickly scan results and decide whether to guess
- The UI must prioritize the **single best answer** while providing supporting context

### Target Users
- Trivia enthusiasts playing along with the Netflix show
- Users who want AI assistance for real-time decision making
- People who appreciate seeing "how the AI thinks"

---

## 2. Information Hierarchy (Critical)

### Tier 1: Primary Decision (Must See Instantly)
- **Recommended Answer** - THE answer to guess (large, prominent)
- **Confidence %** - How sure is the system (color-coded)
- **"GUESS NOW" indicator** - When confidence is high enough

### Tier 2: Supporting Context (Scan Quickly)
- **Oracle's Top 3** - Alternative answers with explanations
- **Trap Detection Alert** - Warning if clue is misleading
- **Agreement Strength** - How many agents agree

### Tier 3: Deep Analysis (Glance or Ignore)
- **Individual Agent Predictions** - What each specialist thinks
- **Cultural References Detected** - Quotes/patterns found in clue
- **Confidence Trend** - How predictions evolved across clues
- **Clue History** - Previous clues for context

### Tier 4: Administrative
- **Clue Input** - Where user types next clue
- **Countdown Timer** - Time pressure (when active)
- **Session Info** - Metadata, reset button

---

## 3. Current Component Inventory

### Components to Preserve/Enhance

| Component | Purpose | Keep/Redesign |
|-----------|---------|---------------|
| **RecommendedPick** | Primary answer display | ENHANCE - Make more prominent |
| **OracleInsight** | Top 3 + analysis | ENHANCE - Better visual hierarchy |
| **StatusBar** | Metadata strip | KEEP - Works well |
| **AgentRow** | 5-agent grid | REDESIGN - Currently cramped |
| **ConfidenceTrend** | Historical chart | OPTIONAL - Nice to have |
| **ClueInput** | Text input | KEEP - Simple, effective |
| **CountdownTimer** | Time pressure | KEEP - Creates urgency |
| **AnswerFeedback** | Post-game form | KEEP - Functional |

### Current Pain Points
1. **Visual Noise**: Too many equally-weighted elements compete for attention
2. **Agent Grid**: 5 columns are cramped on smaller screens
3. **Oracle vs Recommended**: Unclear which is the "real" answer
4. **Confidence Colors**: Inconsistent across components
5. **Copy Actions**: Multiple copy buttons feel redundant
6. **Mobile Experience**: Not optimized for phone screens

---

## 4. Design Requirements

### Must Have
- [ ] Single, unmistakable "THIS IS THE ANSWER" display
- [ ] One-tap copy to clipboard
- [ ] Clear confidence indicator (color + number)
- [ ] "GUESS NOW" alert when confidence is high
- [ ] Trap/misdirection warning (red alert)
- [ ] Works on mobile (responsive)
- [ ] Dark theme (matches Netflix aesthetic)

### Should Have
- [ ] Oracle's top 3 alternatives visible
- [ ] Agent consensus visualization
- [ ] Clue history for context
- [ ] Smooth animations (not distracting)
- [ ] Cultural reference badges

### Nice to Have
- [ ] Confidence trend chart
- [ ] Individual agent predictions (collapsible)
- [ ] Timer with color-coded urgency
- [ ] Sound/haptic feedback option

---

## 5. Data Available for Display

### Per Clue Submission
```typescript
{
  // PRIMARY
  recommended_pick: "MONOPOLY",           // The answer to show
  key_insight: "jail + dice = board game", // Why this answer

  // CONFIDENCE
  oracle.top_3[0].confidence: 92,         // 0-100 scale
  agreement_strength: "strong",           // strong/moderate/weak/none
  agents_responded: 5,                    // Out of 5

  // ORACLE ANALYSIS
  oracle.top_3: [
    { answer: "MONOPOLY", confidence: 92, explanation: "..." },
    { answer: "RISK", confidence: 45, explanation: "..." },
    { answer: "LIFE", confidence: 25, explanation: "..." }
  ],
  oracle.misdirection_detected: "Business terms are a trap - it's a board game",
  oracle.key_theme: "Board games with business elements",
  oracle.blind_spot: "Could be a video game instead",

  // CULTURAL CONTEXT
  cultural_matches: [
    { keyword: "dicey", answer: "MONOPOLY", source: "pattern", confidence: 0.85 }
  ],

  // CATEGORY PRIORS
  category_probabilities: { thing: 0.65, person: 0.20, place: 0.15 },

  // INDIVIDUAL AGENTS
  agents: {
    lateral: { answer: "MONOPOLY", confidence: 0.88, reasoning: "jail+dice" },
    wordsmith: { answer: "MONOPOLY", confidence: 0.92, reasoning: "dicey=dice" },
    popculture: { answer: "RISK", confidence: 0.65, reasoning: "war game" },
    literal: { answer: "PRISON", confidence: 0.40, reasoning: "(trap)" },
    wildcard: { answer: "LIFE", confidence: 0.55, reasoning: "game of life" }
  },

  // VOTING
  voting: {
    vote_breakdown: [
      { answer: "MONOPOLY", total_votes: 2.8, agents: ["lateral", "wordsmith"] },
      { answer: "RISK", total_votes: 0.65, agents: ["popculture"] }
    ]
  },

  // METADATA
  clue_number: 3,                         // 1-5
  elapsed_time: 4.2,                      // seconds
  clue_history: ["clue 1...", "clue 2...", "clue 3..."]
}
```

---

## 6. Color System

### Current Palette (Dark Theme)
```css
--background: #0a0a0a;      /* Near black */
--surface: #1a1a1a;         /* Card backgrounds */
--border: #333333;          /* Subtle borders */

--primary: #00d4ff;         /* Cyan - primary actions */
--purple: #a855f7;          /* Purple - Oracle branding */

--success: #4caf50;         /* Green - high confidence */
--warning: #ffc107;         /* Yellow/amber - medium */
--danger: #ff6b6b;          /* Red - low confidence, traps */

--text-primary: #ffffff;    /* White - headings */
--text-secondary: #9ca3af;  /* Gray - body text */
--text-muted: #6b7280;      /* Darker gray - metadata */
```

### Confidence Color Mapping
- **≥75%**: Green (`#4caf50`) - "Go ahead and guess"
- **50-74%**: Yellow (`#ffc107`) - "Proceed with caution"
- **<50%**: Red (`#ff6b6b`) - "Risky guess"

### Agent Colors (Optional Theming)
- Lateral: Blue (logical thinking)
- Wordsmith: Green (language/wordplay)
- PopCulture: Pink (entertainment)
- Literal: Gray (straightforward)
- WildCard: Orange (creative/unpredictable)

---

## 7. Layout Concepts

### Option A: Single-Column Focus (Recommended for Mobile-First)
```
┌─────────────────────────────────────┐
│  🎯 MONOPOLY              92% ✓    │  <- Primary answer (HUGE)
│  "jail + dice = board game"        │
│  [Copy Answer]                     │
├─────────────────────────────────────┤
│  ⚠️ TRAP: Business terms mislead   │  <- Alert (if detected)
├─────────────────────────────────────┤
│  Oracle's Alternatives:            │
│  #2 RISK (45%)  #3 LIFE (25%)     │
├─────────────────────────────────────┤
│  📊 4/5 agents agree • Clue 3/5   │  <- Status bar
├─────────────────────────────────────┤
│  [Enter clue 4...]          [→]   │  <- Input
├─────────────────────────────────────┤
│  ▼ Show Agent Details              │  <- Collapsible
│  ▼ Show Clue History               │
└─────────────────────────────────────┘
```

### Option B: Two-Column (Desktop)
```
┌─────────────────────────┬─────────────────────────┐
│  🎯 MONOPOLY     92%   │  Oracle Analysis        │
│  ━━━━━━━━━━━━━━━━━━━━━  │  #1 MONOPOLY (92%)     │
│  "jail + dice"         │  #2 RISK (45%)         │
│  [COPY]  [GUESS!]      │  #3 LIFE (25%)         │
│                        │                         │
│  ⚠️ TRAP DETECTED      │  Theme: Board games     │
│  Business terms...     │  Blind spot: Video game │
├────────────────────────┼─────────────────────────┤
│  Agent Consensus       │  Confidence Trend       │
│  ██████░░ 4/5 agree   │  [chart across clues]   │
├────────────────────────┴─────────────────────────┤
│  [Enter next clue...]                     [→]   │
├─────────────────────────────────────────────────┤
│  Clue History: 1. "..." 2. "..." 3. "..."       │
└─────────────────────────────────────────────────┘
```

### Option C: Card Stack (Mobile-Optimized)
```
┌─────────────────────────────────────┐
│  ┌─────────────────────────────┐   │
│  │  🏆 MONOPOLY          92%  │   │  <- Floating card
│  │  [TAP TO COPY]             │   │
│  └─────────────────────────────┘   │
│                                     │
│  ⚠️ Trap: Business terms mislead    │
│                                     │
│  ┌──────┐ ┌──────┐ ┌──────┐       │
│  │ #2   │ │ #3   │ │ ?    │       │  <- Alt cards
│  │ RISK │ │ LIFE │ │      │       │
│  │ 45%  │ │ 25%  │ │      │       │
│  └──────┘ └──────┘ └──────┘       │
│                                     │
│  ▓▓▓▓▓▓▓▓░░ 4/5 agents            │
│                                     │
│  [Type clue 4...]            [→]   │
└─────────────────────────────────────┘
```

---

## 8. Component Specifications

### Primary Answer Card (RecommendedPick)
**Purpose**: Single most important element on screen

**Requirements**:
- Answer text: 32-48px, bold, uppercase
- Confidence: Large number with color coding
- Visual state: Glowing border when confidence ≥75%
- "GUESS!" badge: Pulsing animation when should_guess=true
- Copy button: One tap, visual feedback
- Insight text: Smaller, italic, explains reasoning

**States**:
- Loading: Skeleton/shimmer effect
- Low confidence (<50%): Red tint, caution styling
- High confidence (≥75%): Green glow, "GUESS!" badge
- Perfect match: All 5 agents agree indicator

### Trap Alert (Misdirection Warning)
**Purpose**: Warn user when Oracle detects misleading clue

**Requirements**:
- Only shown when `misdirection_detected` exists
- Red/amber warning color scheme
- Icon: ⚠️ or 🚨
- Brief text explaining the trap
- Should NOT overpower the answer

### Oracle Alternatives (Top 3)
**Purpose**: Show backup options if primary seems wrong

**Requirements**:
- Horizontal cards or pills
- #1 is already shown above, so show #2 and #3
- Smaller confidence numbers
- Tap to expand explanation
- Quick copy action

### Agent Consensus Bar
**Purpose**: Visual representation of agreement

**Requirements**:
- Progress bar or dot indicators
- "X/5 agents agree" text
- Color matches agreement strength
- Compact - fits in status bar

### Clue Input
**Purpose**: Enter next clue

**Requirements**:
- Always visible (not hidden)
- Large touch target
- Clear placeholder text
- Submit on Enter key
- Loading state during API call
- Disabled after clue 5

---

## 9. Animation Guidelines

### Appropriate Animations
- **Fade in**: New results appearing (200-300ms)
- **Slide up**: Answer card entrance
- **Pulse**: "GUESS!" badge, countdown timer at <5s
- **Color transition**: Confidence changes
- **Scale**: Copy button feedback (1.0 → 1.1 → 1.0)

### Avoid
- Long animations (>500ms)
- Distracting movement during reading
- Animations that delay information display
- Parallax or scroll-jacking

### Loading States
- Skeleton screens preferred over spinners
- Shimmer effect for cards
- Subtle pulse for "processing" indicator

---

## 10. Responsive Breakpoints

```css
/* Mobile first */
@media (min-width: 640px)  { /* sm: Tablet portrait */ }
@media (min-width: 768px)  { /* md: Tablet landscape */ }
@media (min-width: 1024px) { /* lg: Desktop */ }
@media (min-width: 1280px) { /* xl: Large desktop */ }
```

### Mobile (<640px)
- Single column layout
- Stacked cards
- Collapsible sections for agents/history
- Large touch targets (44px minimum)
- Bottom-anchored input

### Tablet (640-1024px)
- Two-column for Oracle + Agents
- Expanded status bar
- Side-by-side alternatives

### Desktop (>1024px)
- Full three-column potential
- All sections expanded
- Confidence trend chart visible
- Agent grid (5 columns)

---

## 11. Accessibility Requirements

- **Color contrast**: 4.5:1 minimum for text
- **Not color-only**: Confidence shown as number + color
- **Keyboard navigation**: Tab through interactive elements
- **Screen reader**: Proper ARIA labels
- **Reduced motion**: Respect `prefers-reduced-motion`
- **Touch targets**: 44x44px minimum on mobile

---

## 12. Technical Constraints

### Framework
- React 18 + TypeScript
- Tailwind CSS for styling
- Framer Motion for animations
- Zustand for state management

### Data Flow
- Props passed from Dashboard parent
- No direct API calls in components
- Subscribe to Zustand store for shared state

### Performance
- Avoid re-renders on unrelated state changes
- Lazy load heavy components (chart)
- Optimize images/icons

---

## 13. What NOT to Change

### Keep These Behaviors
1. Single page application (no routing)
2. Real-time updates after clue submission
3. Session-based puzzle tracking
4. Feedback form after puzzle completion
5. Copy-to-clipboard functionality
6. Dark theme (Netflix aesthetic)

### Keep These Data Displays
1. Recommended answer + confidence
2. Oracle's top 3 predictions
3. Trap/misdirection alerts
4. Agent count and agreement
5. Clue history
6. Category priors (thing/person/place)

---

## 14. Success Metrics

A successful redesign should:
1. **Reduce cognitive load**: User finds answer in <1 second
2. **Increase confidence**: Clear visual hierarchy
3. **Mobile-friendly**: Usable on phone during live game
4. **Maintain information**: No loss of useful data
5. **Feel premium**: Matches Netflix aesthetic quality

---

## 15. Design Prompt for v0

When prompting Vercel v0, consider:

```
Create a dark-themed dashboard for a real-time trivia prediction app.
The UI should prioritize a single "recommended answer" with large text
and confidence percentage. Include:

1. Primary answer card with copy button and "GUESS!" indicator
2. Warning alert for detected traps (red/amber)
3. Secondary predictions (#2, #3) in smaller cards
4. Agent consensus bar (X/5 agree)
5. Clue input at bottom
6. Collapsible sections for detailed agent predictions

Style: Dark background (#0a0a0a), purple accent for Oracle (#a855f7),
green/yellow/red for confidence levels. Mobile-first responsive.

Animations: Subtle fade-ins, pulse on high confidence,
scale feedback on buttons.
```

---

## Appendix: Current File Structure

```
frontend/src/
├── components/
│   ├── Dashboard.tsx        # Main container
│   ├── RecommendedPick.tsx  # Primary answer
│   ├── OracleInsight.tsx    # Top 3 + analysis
│   ├── StatusBar.tsx        # Metadata strip
│   ├── AgentRow.tsx         # 5-agent grid
│   ├── ConfidenceTrend.tsx  # Historical chart
│   ├── ClueInput.tsx        # Text input
│   ├── CountdownTimer.tsx   # Time pressure
│   └── AnswerFeedback.tsx   # Post-game form
├── types/
│   └── api.ts               # TypeScript interfaces
├── store/
│   └── puzzleStore.ts       # Zustand state
├── hooks/
│   └── usePredictions.ts    # React Query hooks
└── lib/
    └── api.ts               # API client
```
