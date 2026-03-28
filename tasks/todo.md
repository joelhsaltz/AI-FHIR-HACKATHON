# Notebook Redesign TODO

Status: Complete — resolved issues, moving to API-agnostic provider support
Last updated: 2026-03-27

## Resolved Issues

### 1. Case variety — all cases are the same phenotype ✓ FIXED
- [x] Root cause: shuffle + sequential scan was fragile — replaced with deterministic round-robin
- [x] Verified: pool produces mixed phenotype selection

### 2. UI — combined dropdown ✓ RESOLVED
- [x] Investigate (Step 5) and Classify (Step 6) are now separate cells

### 3. Task too simple ✓ RESOLVED
- [x] Classification changed from Type 1/Type 2/No diabetes to complexity assessment (Routine/Moderate/High/No diabetes) requiring multiple queries

### 4. Student perspective review ✓ ADDRESSED
- [x] Use `/edu-review` agent for UX/pedagogy assessment on current notebook

## Completed
- [x] Two-activity notebook structure (Activity 1: human agent, Activity 2: prompt engineer)
- [x] Separate investigate/classify cells (Steps 5 and 6)
- [x] Immediate feedback on classification
- [x] Multi-case flow with auto-advance
- [x] Prompt editor with run history
- [x] Summary comparison spreadsheet
- [x] Colab verification with screenshots

## Next: API-Agnostic Provider Support
See plan: `~/.claude/plans/twinkling-tinkering-crane.md`
