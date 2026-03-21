# Student Perspective Review Checklist

Structured checklist for evaluating Colab notebooks from a BMI 512 student's
perspective. Used by `student_review.py` to systematically assess pedagogy,
UX, and clinical plausibility.

## Student Persona

The reviewer adopts the perspective of a **BMI 512 Clinical Informatics and AI
graduate student** at Stony Brook University:
- Knows clinical medicine and medical terminology
- New to FHIR, REST APIs, and health data standards
- New to AI agents and prompt engineering
- Comfortable with basic Python but not a software engineer
- Expects clear instructions, immediate feedback, and progressive difficulty

## Checklist Items

### task_complexity
**Question:** Does the task require querying multiple FHIR resource types to
reach a correct classification, or can it be solved with a single query?

**Pass criteria:** Correct classification requires evidence from at least 3
different FHIR resource types (e.g., Condition + Observation + MedicationRequest).
No single query provides enough information to classify with certainty.

**Fail indicators:**
- One lab value (e.g., C-peptide alone) differentiates all categories
- The classification question has an obvious answer without any FHIR queries
- All cases can be resolved with the same 1-2 queries

**Auto-fixable:** No — requires redesigning the classification task and
potentially the phenotype definitions.

---

### case_variety
**Question:** Do the cases presented to students span a meaningful variety of
phenotypes, or are they all effectively the same?

**Pass criteria:** Cases are balanced across the available phenotype categories
(e.g., Type 1, Type 2, no diabetes). Each case presents differently enough
that students must adapt their query strategy.

**Fail indicators:**
- All cases have the same condition codes
- Lab values cluster in the same range across cases
- The "correct" classification is the same for every case
- Ground truth distribution is visibly skewed in the summary

**Auto-fixable:** Yes — modify the candidate builder to stratify/shuffle across
phenotype groups.

---

### ui_clarity
**Question:** Are the notebook's interactive elements (dropdowns, buttons,
navigation) intuitive for a first-time user?

**Pass criteria:** A student can look at each step and immediately understand
what to do. Actions are logically grouped. The current state (which case,
what's been done) is always visible.

**Fail indicators:**
- Query actions and classification options mixed in the same dropdown
- No visual separation between investigation and classification phases
- Student might accidentally classify when they meant to query
- Current case number or progress is not visible
- Unclear what "running" a cell will do

**Auto-fixable:** Yes — text, labels, and layout changes in the generator.

---

### fhir_visibility
**Question:** Are FHIR query URLs, resource types, and response structures
visible and labeled so students learn the FHIR concepts?

**Pass criteria:** Every FHIR query shows: the full URL being called, the
resource type being queried, a human-readable summary of what was requested,
and structured results with field names visible.

**Fail indicators:**
- Raw JSON dumped without labels
- FHIR URLs hidden or abbreviated
- Resource type names not mentioned
- Results shown as plain text without FHIR context

**Auto-fixable:** Yes — output formatting changes in the generator.

---

### feedback_quality
**Question:** Does the notebook provide immediate, specific feedback when
students make choices?

**Pass criteria:** After classification, students see: whether they were right
or wrong, what the correct answer was (with explanation), what evidence
supported the correct answer, and what they missed (if wrong).

**Fail indicators:**
- Only "Correct!" or "Incorrect" with no explanation
- Feedback delayed until the end of all cases
- No indication of what evidence was relevant
- No suggested next steps after a wrong answer

**Auto-fixable:** Yes — feedback text and logic changes in the generator.

---

### dashboard_readability
**Question:** Are summary dashboards (evidence, progress, results) readable
and well-organized?

**Pass criteria:** Tables are properly formatted with headers. Progress
indicators are clear. Evidence logs show what was queried and what was found
in a scannable format.

**Fail indicators:**
- Tables overflow the viewport or have misaligned columns
- Evidence log is a wall of text without structure
- Progress information buried in cell output
- Summary statistics unclear or incorrectly calculated

**Auto-fixable:** Yes — layout and formatting changes in the generator.

---

### activity_flow
**Question:** Are Activity 1 (human agent) and Activity 2 (prompt engineer)
clearly distinct, with a natural progression?

**Pass criteria:** Clear visual and textual boundary between activities.
Activity 1 teaches FHIR query mechanics hands-on. Activity 2 builds on
that knowledge to write prompts for an AI agent. The transition explains
why automation is valuable based on what they just experienced manually.

**Fail indicators:**
- Activities blend together without a clear transition
- Activity 2 doesn't reference skills from Activity 1
- The progression from manual to automated feels arbitrary
- Students don't understand why they're switching modes

**Auto-fixable:** No — structural/pedagogical decision.

---

### code_hidden
**Question:** Is all code hidden behind Colab form cells with plain-English
titles?

**Pass criteria:** Every code cell has `cellView: "form"` metadata and a
descriptive `#@title` annotation. No raw code is visible to students by
default. Titles describe what the step does, not what the code does.

**Fail indicators:**
- Code cells visible without titles
- Titles reference code concepts ("Initialize FHIR client")
- Missing `cellView: "form"` on cells
- Code leaked in cell output (tracebacks don't count — those are errors)

**Auto-fixable:** Yes — metadata and title changes in the generator.

---

### game_mechanics
**Question:** Are accuracy tracking, query counting, and scoring clear and
correctly calculated?

**Pass criteria:** Students can see their score at any time. Metrics are
calculated correctly (accuracy = correct/total, query count matches actual
queries made). The scoring feels fair and motivating.

**Fail indicators:**
- Score displayed incorrectly or inconsistently
- Query count doesn't match the number of queries actually run
- No running total during activity
- Final summary metrics don't match individual case results

**Auto-fixable:** Yes — logic and display changes in the generator.

---

### clinical_plausibility
**Question:** Is the clinical data consistent and the ground truth defensible
by a clinician?

**Pass criteria:** Lab values, conditions, and medications are clinically
consistent for each patient's phenotype. A clinician would agree with the
ground truth classification based on the available evidence. Edge cases are
acknowledged, not hidden.

**Fail indicators:**
- Lab values inconsistent with diagnosis (e.g., normal C-peptide with Type 1)
- Medications that don't match the condition
- Ground truth that a clinician would disagree with
- Missing evidence that a real clinician would expect (e.g., no HbA1c for
  a diabetes assessment)

**Auto-fixable:** No — requires clinical domain expertise.

## Severity Levels

- **high**: Issue significantly impairs the learning experience or produces
  incorrect/misleading results. Must be fixed before sharing with students.
- **medium**: Issue is confusing or suboptimal but doesn't prevent learning.
  Should be fixed in the current iteration if possible.
- **low**: Minor polish issue. Can be deferred.

## Output Format

The review produces JSON:
```json
{
  "pass_count": 7,
  "fail_count": 2,
  "unclear_count": 1,
  "issues": [
    {
      "id": "case_variety",
      "severity": "high",
      "description": "All 3 cases are Type 1 diabetes with low C-peptide",
      "evidence": "Screenshot 7 shows candidate table — all same phenotype",
      "auto_fixable": true,
      "suggested_fix": "Stratify _final_candidates to ensure mix of T1/T2/no-diabetes"
    }
  ]
}
```
