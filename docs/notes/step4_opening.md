# Opening the Step 4 report: reading order

*For Jacob and Shannyn's joint opening (D33). Everything that decides a reading is already fixed in D51. This only sets the order, so the session answers the fixed questions first and leaves exploring for last.*

**Open:** `results/step4/report.md`.

1. **Checks** (top of the report, ~2 min). All 11 conditions at 60 runs, clean commits, every connectivity file matching its SHA-256, 0 stuck, 0 unclassified. If anything fails here, stop: nothing is compared.
2. **The intact whole brain** (first row of "Every condition", ~5 min). Read it against the Step 2 subcircuit baseline (29%, 6/60 completed, 33 (d1)). This is the reference for everything below, and a first look at whole brain against subcircuit.
3. **(a) and (d): does play depend on the wiring?** (~5 min) The fixed reading in "Readings fixed in D51", then their rows, against never press (6.3%) and always press.
4. **(b) and (c): the relay** (~15 min). The three bars in this order:
   - progress (the sign test);
   - first-spike θ, against the intact seed range;
   - the (d1) share.

   Remember: if either does better than intact, it's the late-threshold effect, not "a relay plays better". (b)'s prediction ("earlier") stays as recorded, with the dated note.
5. **E5b and E5c: specific?** (~10 min)
   - **Fixed:** "against intact" and "against its recruited-matched control" must both differ at p < 0.05, in the same direction.
   - **Then their rows:** first-spike θ and death classes, against Shannyn's predictions.
   - **E5c doing better** is read as the late-threshold effect.
6. **The controls** (~5 min): the random and recruited-matched lesions against intact. Expected: no clear difference.
7. **The Holm table** (~3 min): which of the 12 results survive. Report both columns.
8. **Predictions, hit or miss** (~5 min), one line each, for `docs/notes/step4_report.md`.
9. **Only then, anything else** (~10 min): what surprised us, and what's worth a sentence in the write-up, labelled as interpretation.

**Total: about 1 hour.** Afterwards Jacob fills in `docs/notes/step4_report.md` and the D51 result; Shannyn reviews.
