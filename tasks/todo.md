# Notebook Redesign TODO

Status: In Progress — pausing after initial two-activity redesign
Last updated: 2026-03-21

## Issues from Joel's Manual Review

### 1. Case variety — all cases are the same phenotype ✓ FIXED
- [x] All cases returned from FHIR are Type 1 diabetes with very low C-peptide
- [x] Root cause: shuffle + sequential scan was fragile — replaced with deterministic round-robin
- [x] Fix: group-then-interleave stratified selection (group by _group, shuffle within, round-robin pick)
- [x] Verified: pool has 89 candidates (46 T1D, 32 T2D, 11 no_diabetes), selection produces 4/3/3 mix
- [x] Smoke test passes: 16/16, cases classified as Type 1, Type 2, No diabetes (mix confirmed)

### 2. UI — combined dropdown is confusing
- [ ] Having query actions and classification options in the same dropdown is not intuitive
- [ ] Students don't know where to find the classify options or may accidentally classify when they meant to query
- [ ] Need to discuss: go back to separate cells? Use a different UI pattern? Add a visual separator that actually works in Colab?

### 3. Task is too simple — one query solves it
- [ ] C-peptide alone differentiates Type 1 vs Type 2 — only one tool use needed
- [ ] This defeats the purpose of teaching the agent loop (observe → decide → act → repeat)
- [ ] Need to discuss: add more phenotype classes that require multiple queries to differentiate
- [ ] Look at the existing 6 synthetic phenotypes and consider which distinctions require multi-query reasoning
- [ ] Possible additions: CKD staging (requires eGFR + creatinine), treatment adequacy (requires HbA1c + meds), early vs advanced T2D
- [ ] The classification question itself may need to change — "Type 1 / Type 2 / No diabetes" may be too coarse

### 4. Skill gap — model should review from student perspective
- [ ] Opus 4.6 should be able to evaluate the notebook from a student's viewpoint before declaring it done
- [ ] Currently Claude verifies technical correctness but misses UX/pedagogy issues that Joel catches manually
- [ ] Proposal: add a "student perspective review" step to the verification pipeline — after screenshots pass, have the model critique the notebook as if it were a first-time student
- [ ] This could be a new skill or an extension of the nb-verify workflow
- [ ] Should catch issues like: confusing UI, unclear instructions, tasks that are trivially solvable, missing feedback, unclear navigation

## Completed
- [x] Two-activity notebook structure (Activity 1: human agent, Activity 2: prompt engineer)
- [x] Combined investigate/classify cell (Step 5)
- [x] Immediate feedback on classification
- [x] Multi-case flow with auto-advance
- [x] Prompt editor with run history
- [x] Summary comparison spreadsheet
- [x] Colab verification with screenshots
