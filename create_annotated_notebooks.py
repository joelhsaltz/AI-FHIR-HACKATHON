#!/usr/bin/env python3
"""
Create annotated versions of the FHIR Hackathon instructor notebooks.

Reads each original .ipynb, inserts 8 new markdown annotation cells at
specified positions, and writes the annotated copy. Original notebooks
are not modified.

Usage:
    python create_annotated_notebooks.py
"""

import json
import copy
import uuid
import os

NOTEBOOK_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "instructor_materials", "notebooks"
)


def make_cell_id():
    """Generate a unique 8-character hex cell ID."""
    return uuid.uuid4().hex[:8]


def make_markdown_cell(source_text):
    """Create a notebook markdown cell dict with the given source text."""
    return {
        "cell_type": "markdown",
        "id": make_cell_id(),
        "metadata": {},
        "source": source_text
    }


def insert_annotations(cells, annotations):
    """Insert annotation cells into a copy of the cell list.

    annotations: list of (insert_before_index, source_text) tuples,
                 ordered by desired appearance in the final notebook.

    Inserts are processed in reverse so that earlier indices remain valid.
    For multiple inserts at the same index, reverse processing preserves
    the intended top-to-bottom order.
    """
    cells = copy.deepcopy(cells)
    for idx, source in reversed(annotations):
        cells.insert(idx, make_markdown_cell(source))
    return cells


def annotate_notebook(src_filename, dst_filename, annotations):
    """Read src notebook, insert annotations, write dst notebook."""
    src_path = os.path.join(NOTEBOOK_DIR, src_filename)
    dst_path = os.path.join(NOTEBOOK_DIR, dst_filename)

    with open(src_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    original_count = len(nb["cells"])
    nb["cells"] = insert_annotations(nb["cells"], annotations)
    new_count = len(nb["cells"])

    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(f"  {dst_filename}: {original_count} -> {new_count} cells "
          f"(+{new_count - original_count} annotations)")
    return new_count


# ──────────────────────────────────────────────────────────────
# Session 1 Annotations (original: 19 cells, indices 0-18)
# ──────────────────────────────────────────────────────────────

SESSION_1_ANNOTATIONS = [
    # A1: Before cell 0 — "What is FHIR?"
    (0, (
        "---\n"
        "### What is FHIR?\n"
        "\n"
        "FHIR (Fast Healthcare Interoperability Resources) is the modern standard "
        "for exchanging healthcare data electronically. Developed by HL7, it "
        "treats every piece of clinical information as a **Resource** — a "
        "structured data object with a standard format.\n"
        "\n"
        "Key concepts:\n"
        "\n"
        "- **Resources** are the building blocks: `Patient`, `Condition`, "
        "`Observation`, `MedicationRequest`, and hundreds more.\n"
        "- **REST API** — FHIR data is accessed via URLs, just like web pages. "
        "If you understand how a URL works, you understand the basics of FHIR.\n"
        "- **References** — Resources point to each other. A `Condition` "
        "references the `Patient` who has that diagnosis.\n"
        "\n"
        "Example: to get a list of patients, you request "
        "`https://server/Patient`. To find a specific diagnosis, you request "
        "`https://server/Condition?code=44054006`. The server returns structured "
        "JSON that your code can parse.\n"
        "\n"
        "In this session you will query a public FHIR server with synthetic "
        "(fake but realistic) patient data to answer a real clinical question."
    )),

    # A2: Before cell 1 — "Clinical Terminologies: SNOMED CT and LOINC"
    (1, (
        "---\n"
        "### Clinical Terminologies: SNOMED CT and LOINC\n"
        "\n"
        "Healthcare relies on standardized code systems so that a diagnosis or "
        "lab test means the same thing everywhere — across hospitals, EHRs, and "
        "countries.\n"
        "\n"
        "- **SNOMED CT** codes clinical concepts, primarily diagnoses and "
        "findings. For example, Type 2 Diabetes Mellitus = `44054006`. Think of "
        "SNOMED as the answer to \"what is wrong with the patient?\"\n"
        "- **LOINC** codes laboratory tests and clinical measurements. For "
        "example, Hemoglobin A1c = `4548-4`. Think of LOINC as the answer to "
        "\"what was measured?\"\n"
        "\n"
        "A helpful analogy: SNOMED is the dictionary of diseases; LOINC is the "
        "catalog of tests. When you search a FHIR server for Conditions, you use "
        "SNOMED codes. When you search for Observations (lab results), you use "
        "LOINC codes.\n"
        "\n"
        "The code reference table below lists the specific codes we will use "
        "across all three sessions. You do not need to memorize them — the table "
        "is here for quick lookup."
    )),

    # A3: Before cell 3 — "Clinical Context: Type 2 Diabetes and HbA1c"
    (3, (
        "---\n"
        "### Clinical Context: Type 2 Diabetes and HbA1c\n"
        "\n"
        "For those without a clinical background, here is the medical context "
        "behind our query.\n"
        "\n"
        "**Type 2 Diabetes** is a chronic condition where the body cannot "
        "regulate blood sugar effectively. It affects over 400 million people "
        "worldwide and is a leading cause of kidney disease, blindness, and "
        "cardiovascular events.\n"
        "\n"
        "**HbA1c** (Hemoglobin A1c) is a blood test that reflects average "
        "blood glucose over the past 2-3 months. Unlike a single glucose "
        "reading, HbA1c shows long-term control:\n"
        "\n"
        "- Below 5.7% — normal\n"
        "- 5.7% to 6.4% — prediabetes\n"
        "- 6.5% or above — diabetes\n"
        "- Above 7.0% — poorly controlled, may need treatment adjustment\n"
        "\n"
        "Our pipeline will find diabetic patients, retrieve their most recent "
        "HbA1c values, and flag those above 7.0%. This is a real clinical "
        "workflow — care coordinators do exactly this to prioritize patient "
        "outreach."
    )),

    # A4: Before cell 3 — "REST APIs and FHIR Queries"
    (3, (
        "---\n"
        "### REST APIs and FHIR Queries\n"
        "\n"
        "For those without a programming background, here is how we talk to the "
        "FHIR server.\n"
        "\n"
        "A **REST API** lets you request data by constructing a URL. Every FHIR "
        "query follows this pattern:\n"
        "\n"
        "```\n"
        "{server base URL}/{Resource type}?{search parameters}\n"
        "```\n"
        "\n"
        "For example:\n"
        "- `https://server/Patient?_count=3` — give me 3 patients\n"
        "- `https://server/Condition?code=44054006` — find conditions with this "
        "SNOMED code\n"
        "- `https://server/Observation?subject=Patient/abc&code=4548-4` — get "
        "HbA1c results for a specific patient\n"
        "\n"
        "In Python, `requests.get(url)` means \"go to this URL and bring back "
        "whatever you find.\" The server returns JSON (structured text), which we "
        "parse into Python dictionaries.\n"
        "\n"
        "The setup cell below imports the libraries we need and verifies that the "
        "FHIR server is reachable."
    )),

    # A5: Before cell 5 — "Understanding FHIR Bundles"
    (5, (
        "---\n"
        "### Understanding FHIR Bundles\n"
        "\n"
        "When you search a FHIR server, the response is always a **Bundle** — a "
        "container that wraps multiple results into a single response.\n"
        "\n"
        "A Bundle has three important fields:\n"
        "\n"
        "- `resourceType`: always `\"Bundle\"` for search results\n"
        "- `total`: how many resources matched your query on the entire server\n"
        "- `entry`: an array of results, each containing one `resource`\n"
        "\n"
        "Think of it like searching a library catalog: the catalog results page "
        "is the Bundle, and each book listing is a resource entry. The `total` "
        "tells you how many books matched; `entry` gives you the ones on the "
        "current page.\n"
        "\n"
        "The `_count` parameter controls how many entries come back in one "
        "response (like choosing how many results per page). This is important "
        "for large result sets — the server may have thousands of matching "
        "resources, but you only need a manageable batch.\n"
        "\n"
        "The cell below fetches 3 Patient resources so you can see this "
        "structure in action."
    )),

    # A6: Before cell 7 — "How FHIR References Link Resources"
    (7, (
        "---\n"
        "### How FHIR References Link Resources\n"
        "\n"
        "FHIR resources do not exist in isolation — they point to each other "
        "through **references**. A reference is a string like `\"Patient/abc123\"` "
        "that identifies another resource on the server.\n"
        "\n"
        "For our clinical question, references are what connect the dots:\n"
        "\n"
        "- A **Condition** has a `subject.reference` field pointing to the "
        "Patient who has that diagnosis.\n"
        "- An **Observation** also has a `subject` reference pointing to the "
        "Patient whose lab result it records.\n"
        "\n"
        "To answer \"which diabetic patients have poor HbA1c control?\" we must "
        "follow a chain of references:\n"
        "\n"
        "1. Search Conditions (find diabetes) -> extract patient references\n"
        "2. Follow references -> retrieve Patient demographics\n"
        "3. Search Observations for each patient -> get HbA1c values\n"
        "\n"
        "This is the fundamental pattern of multi-step FHIR queries. No single "
        "query can answer the full question — you must chain resources together "
        "by following references. The next several cells walk through each step."
    )),

    # A7: Before cell 15 — "Understanding the Combined Analysis Code"
    (15, (
        "---\n"
        "### Understanding the Combined Analysis Code\n"
        "\n"
        "The cell below combines everything from Steps 1-3 into a single "
        "analysis using pandas, Python's data manipulation library. Here is what "
        "each key operation does:\n"
        "\n"
        "- **`pd.DataFrame()`** — converts our lists of dictionaries into "
        "tables (DataFrames) that support filtering, joining, and aggregation.\n"
        "- **`merge(left_on, right_on)`** — works like a SQL JOIN. It matches "
        "rows where `patient_id` in the observations table equals `id` in the "
        "patients table, combining demographics with lab values.\n"
        "- **`pd.to_numeric(errors='coerce')`** — converts text values to "
        "numbers. Values that cannot be parsed (like `\"N/A\"`) become `NaN` "
        "(Not a Number) rather than causing an error.\n"
        "- **`apply(control_flag)`** — runs a classification function on each "
        "row, labeling patients as poor control, diabetic range, or below "
        "threshold based on HbA1c cutoffs.\n"
        "\n"
        "The clinical logic is in the thresholds (7.0%, 6.5%). The code is data "
        "wrangling — cleaning, joining, and classifying."
    )),

    # A8: Before cell 16 — "From Structured Data to Clinical Narrative"
    (16, (
        "---\n"
        "### From Structured Data to Clinical Narrative\n"
        "\n"
        "Up to this point, we have used code to extract and organize data. The "
        "final step is fundamentally different: translating structured results "
        "into prose that a clinician or care coordinator can read.\n"
        "\n"
        "Clinicians communicate through **narrative** — progress notes, "
        "discharge summaries, referral letters. A table of patient IDs and HbA1c "
        "values is useful for analysis, but a written summary is what drives "
        "clinical action.\n"
        "\n"
        "In this step, you use the LLM in a different role:\n"
        "\n"
        "- **Steps 1-3**: LLM as code generator — it wrote Python/FHIR queries "
        "for you to execute.\n"
        "- **Step 4**: LLM as summarizer — it reads structured data and produces "
        "a clinical narrative.\n"
        "\n"
        "Notice the key constraint in the prompt: *\"Use ONLY the data in the "
        "table.\"* Without this, the LLM might hallucinate additional findings. "
        "Grounding the summary in retrieved data is essential for clinical "
        "safety."
    )),
]


# ──────────────────────────────────────────────────────────────
# Session 2 Annotations (original: 16 cells, indices 0-15)
# ──────────────────────────────────────────────────────────────

SESSION_2_ANNOTATIONS = [
    # B1: Before cell 0 — "Recap: What You Built in Session 1"
    (0, (
        "---\n"
        "### Recap: What You Built in Session 1\n"
        "\n"
        "In Session 1, you manually executed a three-step clinical data "
        "pipeline:\n"
        "\n"
        "1. Searched for Conditions (Type 2 Diabetes, SNOMED 44054006)\n"
        "2. Followed references to get Patient demographics\n"
        "3. Searched Observations for each patient's HbA1c values\n"
        "\n"
        "**You** decided the order. **You** wrote each query (with the LLM's "
        "help generating code). **You** chained the results together.\n"
        "\n"
        "Now ask: what if the LLM could decide the order itself? Instead of you "
        "telling it \"first search conditions, then get patients,\" you just ask "
        "the clinical question and let the LLM figure out the steps.\n"
        "\n"
        "That shift — from the LLM as a code-writing assistant to the LLM as a "
        "decision-making agent — is the core idea of this session. The LLM gets "
        "the same tools you used. It decides when and how to call them."
    )),

    # B2: Before cell 2 — "What You Need for This Session"
    (2, (
        "---\n"
        "### What You Need for This Session\n"
        "\n"
        "Session 1 only required an internet connection — the FHIR server is "
        "public. Session 2 adds a new requirement: an **Anthropic API key**.\n"
        "\n"
        "The `anthropic` Python library sends messages to Claude and receives "
        "structured responses, including tool-use requests. The API key "
        "authenticates your requests — without it, the API rejects your calls.\n"
        "\n"
        "If you are running in Google Colab:\n"
        "\n"
        "- Your API key should be stored in **Colab Secrets** (the key icon in "
        "the left sidebar) under the name `ANTHROPIC_API_KEY`.\n"
        "- The setup cell below retrieves it automatically.\n"
        "\n"
        "If you are running locally:\n"
        "\n"
        "- Set the environment variable: "
        "`export ANTHROPIC_API_KEY=\"your-key-here\"`\n"
        "\n"
        "The cell below installs the `anthropic` package. The setup cell after "
        "it initializes the client and verifies your key works."
    )),

    # B3: Before cell 4 — "Why Wrap FHIR Queries as Functions?"
    (4, (
        "---\n"
        "### Why Wrap FHIR Queries as Functions?\n"
        "\n"
        "The cell below contains the same FHIR queries you ran in Session 1, "
        "but now packaged as **reusable Python functions** with clear names, "
        "typed parameters, and structured return values.\n"
        "\n"
        "This is not just good software practice — it is a requirement for tool "
        "use. The LLM needs a **menu of discrete capabilities** it can invoke by "
        "name. Each function becomes a tool:\n"
        "\n"
        "- `search_conditions(code)` — find patients with a diagnosis\n"
        "- `get_patient(patient_id)` — retrieve one patient's demographics\n"
        "- `search_observations(patient_id, loinc_code)` — get lab results\n"
        "\n"
        "Clean function signatures matter because the LLM must understand what "
        "each function does and what arguments to pass — entirely from the "
        "description, not the source code. A vague function with many optional "
        "parameters is harder for the LLM to use correctly than a focused one "
        "with a clear purpose."
    )),

    # B4: Before cell 5 — "Tool Schemas: How the LLM Sees Your Functions"
    (5, (
        "---\n"
        "### Tool Schemas: How the LLM Sees Your Functions\n"
        "\n"
        "The LLM never sees your Python source code. Instead, it reads **JSON "
        "schemas** that describe each tool: its name, what it does, and what "
        "parameters it accepts.\n"
        "\n"
        "A tool schema has three parts:\n"
        "\n"
        "- **`name`** — the function identifier the LLM uses to request a call\n"
        "- **`description`** — a natural-language explanation of what the tool "
        "does and when to use it\n"
        "- **`input_schema`** — the parameters, their types, and descriptions\n"
        "\n"
        "The quality of these descriptions directly affects agent performance. "
        "Vague descriptions lead to wrong tool choices; overly technical ones "
        "confuse the reasoning. Writing good tool schemas is like writing good "
        "API documentation for a reader who cannot see the source code and must "
        "decide which endpoint to call based solely on the docs.\n"
        "\n"
        "Pay attention to the descriptions in the cell below — especially the "
        "example codes embedded in parameter descriptions. The LLM uses these to "
        "choose the right arguments."
    )),

    # B5: Before cell 8 — "The System Prompt: Steering Agent Behavior"
    (8, (
        "---\n"
        "### The System Prompt: Steering Agent Behavior\n"
        "\n"
        "A **system prompt** is a set of instructions given to the LLM at the "
        "start of every conversation. It defines the agent's role, strategy, and "
        "constraints — like standing orders for a medical resident: \"follow this "
        "protocol.\"\n"
        "\n"
        "The system prompt does not give the agent new capabilities. It guides "
        "how existing capabilities (tools) are used:\n"
        "\n"
        "- **Role**: \"You are a clinical data assistant\" — sets context for "
        "reasoning\n"
        "- **Strategy**: \"Think step by step... first identify the condition, "
        "then extract patient references\" — provides a workflow template\n"
        "- **Constraints**: \"NEVER invent data\" — prevents hallucination\n"
        "\n"
        "You can think of it as the difference between giving someone tools "
        "(tool schemas) and giving them a protocol for using those tools (system "
        "prompt). Both matter, but the system prompt shapes the agent's overall "
        "behavior and reliability."
    )),

    # B6: Before cell 9 — "Anatomy of the Agent Loop"
    (9, (
        "---\n"
        "### Anatomy of the Agent Loop\n"
        "\n"
        "The cell below contains `run_agent()`, the core function that drives "
        "the tool-use conversation. Here is what happens step by step:\n"
        "\n"
        "1. **Send** the user's question plus tool schemas to Claude.\n"
        "2. **Claude responds** with either a `tool_use` request (\"I want to "
        "call this function with these arguments\") or a `text` response (the "
        "final answer).\n"
        "3. **If `tool_use`**: your code executes the requested function locally "
        "and sends the result back to Claude.\n"
        "4. **Repeat** until Claude produces a text response or hits the step "
        "limit.\n"
        "\n"
        "The critical insight: **the LLM plans, your code executes.** Claude "
        "never touches the FHIR server directly. It requests function calls, "
        "your Python code runs them, and the results flow back. This separation "
        "is what makes the system auditable and safe — every action is logged, "
        "and the LLM cannot do anything outside the defined tools.\n"
        "\n"
        "The `max_steps` parameter is a safety limit to prevent runaway loops."
    )),

    # B7: Before cell 11 — "Reading the Agent Trace"
    (11, (
        "---\n"
        "### Reading the Agent Trace\n"
        "\n"
        "When the agent runs, it prints a trace showing each tool call: the step "
        "number, function name, and arguments. This trace is your window into "
        "the agent's reasoning.\n"
        "\n"
        "As you read the trace, look for:\n"
        "\n"
        "- **Order of operations** — does the agent follow a logical clinical "
        "workflow? (conditions first, then patients, then labs)\n"
        "- **Arguments chosen** — did it pick the right SNOMED/LOINC codes? "
        "Where did it learn them?\n"
        "- **Call count** — is it efficient, or does it make unnecessary calls?\n"
        "- **Final synthesis** — does the answer accurately reflect the data "
        "returned by the tools?\n"
        "\n"
        "Compare the trace to the manual steps you took in Session 1. The agent "
        "should follow roughly the same sequence — because the clinical logic "
        "has not changed, only who (you vs. the LLM) is deciding the steps.\n"
        "\n"
        "After the agent runs, the next cell breaks down the tool call sequence "
        "into a summary table for easier analysis."
    )),

    # B8: Before cell 15 — "Safety and Failure Modes"
    (15, (
        "---\n"
        "### Safety and Failure Modes\n"
        "\n"
        "Tool-use agents are powerful but not infallible. Common failure modes "
        "include:\n"
        "\n"
        "1. **Wrong tool selection** — the agent calls `search_conditions` when "
        "it should have called `search_observations`, or vice versa.\n"
        "2. **Hallucinated parameters** — the agent invents a SNOMED or LOINC "
        "code that does not exist, returning zero results.\n"
        "3. **Premature stopping** — the agent provides an answer after only one "
        "or two tool calls, missing important data.\n"
        "4. **Exceeding the step limit** — the agent makes too many calls "
        "(fetching every patient individually) and hits `max_steps` before "
        "finishing.\n"
        "\n"
        "Your two main levers for controlling behavior are the **system prompt** "
        "(strategy and constraints) and **tool descriptions** (what each tool "
        "does and when to use it). Better descriptions and clearer instructions "
        "reduce failures.\n"
        "\n"
        "In Session 3, you will run your own questions and actively look for "
        "these failure modes. Finding where the agent breaks is more valuable "
        "than watching it succeed."
    )),
]


# ──────────────────────────────────────────────────────────────
# Session 3 Annotations (original: 21 cells, indices 0-20)
# ──────────────────────────────────────────────────────────────

SESSION_3_ANNOTATIONS = [
    # C1: Before cell 0 — "From Observation to Exploration"
    (0, (
        "---\n"
        "### From Observation to Exploration\n"
        "\n"
        "In Session 2, you watched a 3-tool agent answer a well-defined clinical "
        "question. You traced its reasoning and compared it to your manual steps "
        "from Session 1.\n"
        "\n"
        "Now the dynamic changes:\n"
        "\n"
        "- **More tools** — 6 instead of 3, covering medications, encounters, "
        "and full problem lists\n"
        "- **Open-ended questions** — you choose what to ask, not us\n"
        "- **Goal shift** — success is not just getting an answer; it is finding "
        "where the agent breaks\n"
        "\n"
        "You are now the **quality assurance team** for a clinical AI agent. "
        "Your job is to probe its capabilities, find its limits, and document "
        "what happens when it fails. This is how real AI systems are evaluated "
        "before deployment — through structured adversarial testing by domain "
        "experts."
    )),

    # C2: Before cell 5 — "New Clinical Resources: Medications, Encounters, and Problem Lists"
    (5, (
        "---\n"
        "### New Clinical Resources: Medications, Encounters, and Problem Lists\n"
        "\n"
        "Session 2 used three FHIR resource types: Condition, Patient, and "
        "Observation. The cell below adds functions for three more:\n"
        "\n"
        "- **MedicationRequest** — what drugs has the patient been prescribed? "
        "Includes medication name, code, status (active, stopped, completed), "
        "and the date it was authored.\n"
        "- **Encounter** — what clinical visits has the patient had? Covers "
        "office visits, emergency department visits, and hospitalizations, with "
        "dates and status.\n"
        "- **Condition (all for a patient)** — the patient's complete problem "
        "list. Unlike `search_conditions` which searches by diagnosis code "
        "across all patients, `search_all_conditions` retrieves every diagnosis "
        "for one specific patient.\n"
        "\n"
        "Together with the original three tools, the agent can now build much "
        "richer patient profiles — but it also has more choices to make and more "
        "ways to go wrong."
    )),

    # C3: Before cell 7 — "What 6 Tools Can Do That 3 Could Not"
    (7, (
        "---\n"
        "### What 6 Tools Can Do That 3 Could Not\n"
        "\n"
        "With 3 tools the agent could answer: \"Find patients with diagnosis X "
        "and get their lab value Y.\" That is a narrow but well-defined "
        "pipeline.\n"
        "\n"
        "With 6 tools, the space of answerable questions expands significantly:\n"
        "\n"
        "- What medications are diabetic patients taking?\n"
        "- How often do hypertensive patients visit the ER?\n"
        "- What is the full problem list for patients with high HbA1c?\n"
        "- Are patients with both diabetes and hypertension on appropriate "
        "medications?\n"
        "\n"
        "But more capability brings more complexity. The agent must now decide "
        "**which** of 6 tools to use, not just **when** to use one of 3. Watch "
        "for:\n"
        "\n"
        "- **Suboptimal tool choice** — using `search_conditions` (by code, "
        "all patients) when `search_all_conditions` (all conditions, one "
        "patient) was more appropriate, or vice versa\n"
        "- **Missed tools** — not using a relevant tool at all\n"
        "- **Unnecessary calls** — fetching data that does not help answer "
        "the question"
    )),

    # C4: Before cell 9 — "Same System Prompt, More Tools"
    (9, (
        "---\n"
        "### Same System Prompt, More Tools\n"
        "\n"
        "The system prompt below is identical to Session 2 — the same "
        "behavioral instructions, strategy template, and constraints. The only "
        "change is that the agent now sees 6 tool schemas instead of 3.\n"
        "\n"
        "This is an intentional design choice. By keeping the system prompt "
        "constant, you can isolate the effect of adding tools. Any differences "
        "in behavior come from the expanded tool set, not from new "
        "instructions.\n"
        "\n"
        "Watch for whether the system prompt's five-step strategy still works "
        "with 6 tools. The original steps (identify condition, extract "
        "references, get demographics, look up observations, synthesize) assumed "
        "the 3-tool setup. With medications and encounters now available, the "
        "agent may need to deviate from that template — and the system prompt "
        "does not explicitly guide it on when to use the new tools.\n"
        "\n"
        "This is a common real-world challenge: system prompts that were "
        "adequate for a small tool set may become insufficient as capabilities "
        "grow."
    )),

    # C5: Before cell 11 — "How to Formulate Good Clinical Questions"
    (11, (
        "---\n"
        "### How to Formulate Good Clinical Questions\n"
        "\n"
        "A good test question for the agent should be:\n"
        "\n"
        "- **Specific enough** to evaluate whether the answer is correct — you "
        "need to know what a right answer looks like\n"
        "- **Complex enough** to require multiple tool calls — single-tool "
        "questions do not test agent reasoning\n"
        "\n"
        "A useful pattern: *\"Find patients with [condition X] and get their "
        "[medications / labs / visits].\"* This guarantees at least two tool "
        "types are needed.\n"
        "\n"
        "For finding failures, try:\n"
        "\n"
        "- **Conditions not in the code table** — ask about a disease whose "
        "SNOMED code is not listed in the tool descriptions. Will the agent "
        "guess a code, or say it does not know?\n"
        "- **Vague questions** — \"Which patients are the sickest?\" How does "
        "the agent interpret \"sickest\" without a clear definition?\n"
        "- **Multi-type reasoning** — questions that require combining data "
        "from conditions, labs, AND medications to answer properly"
    )),

    # C6: Before cell 12 — "Common Agent Failure Modes"
    (12, (
        "---\n"
        "### Common Agent Failure Modes\n"
        "\n"
        "As you run your questions, watch for these five patterns:\n"
        "\n"
        "1. **Code hallucination** — the agent invents a SNOMED or LOINC code "
        "that does not exist, gets zero results, and may draw incorrect "
        "conclusions from the empty response.\n"
        "2. **Incomplete search** — the agent checks only a few patients when "
        "there are many more matching the criteria, giving a partial picture.\n"
        "3. **Wrong tool** — the agent uses `search_conditions` (finds patients "
        "by one diagnosis code) when `search_all_conditions` (gets all diagnoses "
        "for one patient) was needed, or vice versa.\n"
        "4. **Premature answer** — the agent answers after just one or two tool "
        "calls, missing critical data that would change the conclusion.\n"
        "5. **Over-fetching** — the agent makes too many calls (e.g., fetching "
        "medications, encounters, AND observations for every patient) and hits "
        "the step limit before synthesizing an answer.\n"
        "\n"
        "Documenting these failures is the core of your deliverable. One "
        "well-analyzed failure teaches more than a dozen successful runs."
    )),

    # C7: Before cell 19 — "Understanding Your Deliverable"
    (19, (
        "---\n"
        "### Understanding Your Deliverable\n"
        "\n"
        "The cell below collects your question runs — the questions you asked, "
        "the tool call logs, and the agent's final answers — into a JSON report "
        "with a timestamp and verification hash.\n"
        "\n"
        "The **verification hash** is a SHA-256 digest of your tool call data. "
        "It ensures the report was generated by actually running the agent, not "
        "manually edited after the fact. If you modify the JSON file, the hash "
        "will no longer match the data.\n"
        "\n"
        "To submit:\n"
        "\n"
        "1. Run the deliverable cell below\n"
        "2. Enter your student ID when prompted\n"
        "3. Download the generated JSON file\n"
        "4. Submit the file through the course portal\n"
        "\n"
        "Make sure you have run at least 2 questions before generating the "
        "report. The report captures whatever runs are stored in memory, so do "
        "not restart the notebook kernel between running questions and generating "
        "the deliverable."
    )),

    # C8: Before cell 20 — "What is MCP? (Model Context Protocol)"
    (20, (
        "---\n"
        "### What is MCP? (Model Context Protocol)\n"
        "\n"
        "Throughout these three sessions, we built a tool-use system with "
        "several ad-hoc choices: tool schemas in Anthropic's native format, "
        "tools running as local Python functions, and a hardcoded list of "
        "available tools.\n"
        "\n"
        "**MCP (Model Context Protocol)** standardizes all of these:\n"
        "\n"
        "- **Schema format** — a universal way to describe tools that works "
        "across LLM providers, not just Anthropic's format\n"
        "- **Transport** — tools run as separate servers communicating via "
        "JSON-RPC over stdio or HTTP, instead of being local function calls in "
        "the same process\n"
        "- **Discovery** — the LLM can ask \"what tools are available?\" at "
        "runtime, rather than receiving a hardcoded list\n"
        "\n"
        "MCP turns our ad-hoc notebook approach into production architecture. "
        "With MCP, you could swap the FHIR tool server without changing any "
        "agent code, add new tools without restarting the agent, and use the "
        "same tools with different LLM providers. It is the difference between a "
        "prototype and a system designed for real-world deployment."
    )),
]


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    print("Creating annotated instructor notebooks...\n")

    configs = [
        ("session1_instructor.ipynb",
         "session1_instructor_annotated.ipynb",
         SESSION_1_ANNOTATIONS, 27),
        ("session2_instructor.ipynb",
         "session2_instructor_annotated.ipynb",
         SESSION_2_ANNOTATIONS, 24),
        ("session3_instructor.ipynb",
         "session3_instructor_annotated.ipynb",
         SESSION_3_ANNOTATIONS, 29),
    ]

    all_ok = True
    for src, dst, annotations, expected_count in configs:
        count = annotate_notebook(src, dst, annotations)
        if count != expected_count:
            print(f"  WARNING: Expected {expected_count} cells, got {count}")
            all_ok = False

    if all_ok:
        print("\nAll notebooks created successfully.")
    else:
        print("\nSome notebooks have unexpected cell counts — review above.")


if __name__ == "__main__":
    main()
