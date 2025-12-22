# Frontend Integration Test Guide

**Status**: Both servers running and ready!
- ✅ Backend: http://localhost:8000 (83 entities loaded)
- ✅ Frontend: http://localhost:5173 (ready for testing)

---

## Quick Test: Monopoly Puzzle (5 minutes)

### Step 1: Open the Frontend

Open your browser to: **http://localhost:5173**

You should see the JackpotPredict dashboard with:
- Countdown timer (20 seconds)
- Clue input field
- Empty prediction cards
- Dark theme with electric blue accents

### Step 2: Test the Monopoly Puzzle

Enter each clue one at a time and observe the predictions:

#### Clue 1: "Savors many flavors"

**Enter this clue and press Submit/Enter**

Expected Results:
- Top 3 predictions appear instantly
- Likely shows: Statue of Liberty, Eiffel Tower, Mt. Rushmore
- Monopoly: NOT in Top 3 yet (normal - too early)
- Confidence: ~25-30% for top predictions
- Session ID created (check network tab or console)

#### Clue 2: "Round and round"

**Enter this second clue**

Expected Results:
- Same session continues (predictions update based on BOTH clues)
- Top 3: Still likely landmarks
- Monopoly: Still not in Top 3 (building probability)
- Confidence: ~50-60% for top predictions

#### Clue 3: "A hostile takeover" ⭐

**This is the critical clue!**

Expected Results:
- ✅ **Monopoly appears as #1 prediction!**
- Confidence: **95%** (very high!)
- Reasoning: "Category 'thing' strongly indicated (60%)"
- Guess recommendation: "GUESS NOW!" (confidence exceeds 75% threshold)
- Other predictions: Statue of Liberty, Eiffel Tower (still present but lower rank)

**This proves the polysemy fix is working!**

#### Clue 4: "Trespassing will cost you"

**Continue with fourth clue**

Expected Results:
- Monopoly maintains #1 position
- Confidence: 95%
- System still recommends guessing

#### Clue 5: "Jail time can be dicey"

**Final clue**

Expected Results:
- Monopoly: #1 or #2 (may drop to #2 if "Big Ben" matches "time")
- Confidence: 95%
- Complete puzzle solved!

### Step 3: Reset and Try Again

Click the "Reset" button (if available) or refresh the page, then:
- Try entering clues in different order
- Try partial clues
- Test the countdown timer

---

## What to Look For (Quality Checks)

### UI/UX
- [ ] Countdown timer animates smoothly (20 seconds)
- [ ] Timer color changes: Green → Yellow → Red
- [ ] Clue input accepts Enter key (not just button click)
- [ ] Previous clues shown in history panel
- [ ] Prediction cards animate when updating
- [ ] Confidence bars fill proportionally
- [ ] Mobile responsive (try resizing window)

### Functionality
- [ ] Session persists across multiple clues
- [ ] Predictions update based on all previous clues
- [ ] Confidence increases with more clues
- [ ] Top prediction changes from Clue 2 to Clue 3
- [ ] Guess recommendation threshold works (shows at 75%+)

### API Integration
- [ ] No CORS errors (check browser console)
- [ ] API responses return in <500ms
- [ ] Session ID maintained across requests
- [ ] Error handling for invalid input
- [ ] Loading states during API calls

### Data Quality
- [ ] Monopoly reaches #1 by Clue 3 ✅
- [ ] Confidence shows 95% (not 0.9% or 263%)
- [ ] Reasoning text is readable
- [ ] Category displayed correctly ("thing", not "place")

---

## Test Results Checklist

### Critical Success Criteria
- ✅ Monopoly predicted by Clue 3? (YES/NO): _____
- ✅ Confidence at 95%? (YES/NO): _____
- ✅ Session maintained across clues? (YES/NO): _____
- ✅ UI responsive and smooth? (YES/NO): _____

### Known Limitations (With 83 Entities)
- ⚠️ Paris Hilton puzzle will FAIL (expected - needs more entities)
- ⚠️ Some predictions may be repetitive (limited entity pool)
- ⚠️ Confidence may plateau quickly (limited data)

**These will improve with 335 entities!**

---

## Troubleshooting

### Frontend Not Loading
```bash
# Check if frontend server is running
curl http://localhost:5173

# If not, restart:
cd frontend && npm run dev
```

### Backend API Errors
```bash
# Check backend health
curl http://localhost:8000/api/health

# If unhealthy, restart:
cd backend && ./venv/Scripts/python.exe -m uvicorn app.server:app --port 8000
```

### CORS Errors
- Check browser console for errors
- Verify frontend is calling http://localhost:8000 (not different port)
- Backend should allow localhost:5173 origin

### Predictions Not Updating
- Check browser Network tab - are API calls succeeding?
- Verify session_id is being passed in subsequent requests
- Check backend logs for errors

---

## Advanced Testing

### Test Different Puzzles

Try these other clues to see how the system performs:

**Mt. Rushmore** (Should work well):
1. "Natural but not natural"
2. "Presidential faces"
   - ✅ Should predict Mt. Rushmore by Clue 2

**Paris Hilton** (Will likely fail with 83 entities):
1. "Back to the basics"
2. "Loud with the crowd"
3. "A sensation and a destination"
4. "Her family is extremely hospitable"
5. "Named after a romantic city? That's hot."
   - ❌ Expected to fail (needs better annotations)

### Performance Testing

1. **Speed Test**:
   - Time how long predictions take to appear
   - Should be <500ms from submission to display

2. **Session Test**:
   - Open browser dev tools → Network tab
   - Verify session_id is consistent across requests

3. **Error Handling**:
   - Try submitting empty clue
   - Try submitting very long clue (>500 chars)
   - Try rapid-fire submissions

---

## After Testing with 83 Entities

Once you confirm the frontend works, we can **upgrade to 335 entities**:

### Wait for Annotation to Complete

Check progress:
```bash
tail -20 /c/Users/Korp/AppData/Local/Temp/claude/c--Users-Korp-AI-Programs-Jackpot-App/tasks/b3acfa5.output
```

Look for: "Successfully annotated X/252 entities"

### Merge Annotations

```bash
cd backend
./venv/Scripts/python.exe -c "
import json
with open('app/data/annotated_entities.json') as f:
    existing = json.load(f)
with open('app/data/additional_entities_annotated.json') as f:
    new = json.load(f)
merged = existing + new
with open('app/data/all_annotated_entities.json', 'w') as f:
    json.dump(merged, f, indent=2)
print(f'Merged {len(merged)} entities')
"
```

### Update Database

```bash
./venv/Scripts/python.exe scripts/populate_db.py --input app/data/all_annotated_entities.json
```

### Restart Backend

```bash
# Stop current backend (Ctrl+C or kill process)
./venv/Scripts/python.exe -m uvicorn app.server:app --port 8000 --reload
```

### Re-test

- Frontend automatically reconnects
- Same Monopoly test should work even better
- Paris Hilton test may now pass!
- Run automated tests: `./venv/Scripts/python.exe test_historical_puzzles.py`

---

## Expected Timeline

| Task | Time | Status |
|------|------|--------|
| Open browser + test Monopoly | 5 min | ⏳ NOW |
| Annotation completes | ~15 min | 🔄 Running |
| Merge + update database | 3 min | ⏸️ After annotation |
| Re-test with 335 entities | 5 min | ⏸️ After update |
| **Total** | **~30 min** | - |

---

## Success Metrics

### Minimum Acceptable (83 Entities)
- ✅ Monopoly predicted by Clue 3
- ✅ 95% confidence displayed
- ✅ UI smooth and responsive
- ✅ Session state maintained

### Excellent (335 Entities - After Upgrade)
- ✅ Monopoly predicted by Clue 2 or 3
- ✅ Mt. Rushmore predicted by Clue 2
- ✅ Paris Hilton predicted by Clue 4 or 5
- ✅ 3/3 test suite passing
- ✅ Predictions more diverse

---

## Screenshot Checklist

If documenting for presentation, capture:
1. Initial dashboard (empty state)
2. After Clue 1 (first predictions)
3. After Clue 3 (Monopoly at #1 with 95%)
4. Final state (all 5 clues entered)
5. Test results (if running automated tests)

---

## Next Steps After Frontend Test

1. ✅ **Confirm frontend works** - Monopoly test passes
2. 🔄 **Wait for annotation** - Background process completes
3. ⏸️ **Merge annotations** - Combine 83 + 252 entities
4. ⏸️ **Update database** - Load all 335 entities
5. ⏸️ **Re-test** - Validate improved accuracy
6. ⏸️ **Production deploy** (optional) - Railway + Vercel

---

**Ready to test?** Open http://localhost:5173 in your browser now! 🚀

The system is **fully functional** - you're about to see your AI trivia prediction engine in action!
