#!/usr/bin/env python3
"""Generate a comprehensive Session 1 Orientation PDF for the FHIR + AI Hackathon.

Uses fpdf2 to produce a slide-style document with one concept per page.
Run:  python generate_session1_orientation.py
Output: ../student_materials/orientation_pdfs/pre_session1_orientation.pdf
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os

# ── Colour palette ────────────────────────────────────────────────────────
DARK   = (30, 30, 30)
ACCENT = (0, 102, 178)      # blue
LIGHT  = (245, 245, 245)
WHITE  = (255, 255, 255)
GREEN  = (34, 139, 34)
RED    = (200, 50, 50)
ORANGE = (210, 120, 20)
GRAY   = (120, 120, 120)

class SlidePDF(FPDF):
    """Letter-landscape PDF with slide-like formatting helpers."""

    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="Letter")
        self.set_auto_page_break(auto=False)
        # Use built-in fonts only (no TTF needed)

    # ── helpers ────────────────────────────────────────────────────────
    def slide_title(self, text):
        """Large bold title at the top of a slide."""
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*DARK)
        self.set_xy(20, 18)
        self.cell(0, 14, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # accent rule
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.8)
        self.line(20, 35, 255, 35)
        self.set_y(40)

    def subtitle(self, text, size=18):
        self.set_font("Helvetica", "B", size)
        self.set_text_color(*ACCENT)
        self.multi_cell(0, 9, text)
        self.ln(2)

    def body(self, text, size=13, bold=False):
        style = "B" if bold else ""
        self.set_font("Helvetica", style, size)
        self.set_text_color(*DARK)
        self.set_x(20)
        self.multi_cell(230, 7, text)
        self.ln(2)

    def bullet(self, text, size=13, indent=25):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        self.set_x(indent)
        self.cell(5, 7, "-")
        self.multi_cell(220, 7, text)
        self.ln(1)

    def code_block(self, text, size=11):
        self.set_font("Courier", "", size)
        self.set_text_color(50, 50, 50)
        # light gray background box
        x0, y0 = 25, self.get_y()
        lines = text.split("\n")
        h = len(lines) * 6 + 6
        self.set_fill_color(*LIGHT)
        self.rect(x0 - 3, y0 - 1, 224, h, "F")
        for line in lines:
            self.set_x(x0)
            self.cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def note_box(self, text, colour=ACCENT):
        y = self.get_y()
        self.set_draw_color(*colour)
        self.set_line_width(0.6)
        self.rect(25, y, 220, 20)
        self.set_xy(28, y + 2)
        self.set_font("Helvetica", "I", 11)
        self.set_text_color(*colour)
        self.multi_cell(214, 5.5, text)
        self.set_y(y + 22)

    def table_row(self, cols, widths, bold=False, fill=False):
        style = "B" if bold else ""
        self.set_font("Helvetica", style, 11)
        if fill:
            self.set_fill_color(220, 235, 250)
        self.set_text_color(*DARK)
        x = 25
        for i, (col, w) in enumerate(zip(cols, widths)):
            self.set_xy(x, self.get_y())
            self.cell(w, 8, col, border=1, fill=fill)
            x += w
        self.ln(8)

    def new_slide(self):
        self.add_page()


# ══════════════════════════════════════════════════════════════════════════
#  BUILD THE SLIDES
# ══════════════════════════════════════════════════════════════════════════
pdf = SlidePDF()

# ── Slide 1: Title ────────────────────────────────────────────────────
pdf.new_slide()
pdf.set_font("Helvetica", "B", 38)
pdf.set_text_color(*DARK)
pdf.set_xy(20, 50)
pdf.cell(0, 18, "FHIR + AI Hackathon")
pdf.set_xy(20, 72)
pdf.set_font("Helvetica", "", 26)
pdf.set_text_color(*ACCENT)
pdf.cell(0, 14, "Session 1 Orientation")
pdf.set_xy(20, 95)
pdf.set_font("Helvetica", "", 18)
pdf.set_text_color(*GRAY)
pdf.cell(0, 10, "FHIR Fundamentals with LLM-Assisted Code Generation")
pdf.set_xy(20, 115)
pdf.cell(0, 10, "Duration: 1 hour")
pdf.set_xy(20, 140)
pdf.set_font("Helvetica", "I", 14)
pdf.set_text_color(*GRAY)
pdf.cell(0, 8, "BMI 512 - Clinical Informatics and AI  |  Stony Brook University")

# ── Slide 2: The Big Picture ──────────────────────────────────────────
pdf.new_slide()
pdf.slide_title("The Big Picture")
pdf.body(
    "In this hackathon you will build a clinical data pipeline that turns a plain-English "
    "question into an evidence-based answer.  The three sessions walk you through this "
    "pipeline step by step:"
)
pdf.ln(2)
pdf.set_font("Courier", "B", 13)
pdf.set_text_color(*DARK)
pdf.set_x(30)
pdf.cell(0, 8, "English Question", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(40)
pdf.cell(0, 8, '|  (you prompt an LLM)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(40)
pdf.cell(0, 8, "v", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(30)
pdf.cell(0, 8, "Python / FHIR Code", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(40)
pdf.cell(0, 8, "|  (your code queries a FHIR server)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(40)
pdf.cell(0, 8, "v", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(30)
pdf.cell(0, 8, "Structured Clinical Data  (JSON)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(40)
pdf.cell(0, 8, "|  (you prompt an LLM again)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(40)
pdf.cell(0, 8, "v", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(30)
pdf.cell(0, 8, "Clinical Summary  (narrative text)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(4)
pdf.note_box(
    "Key insight: The LLM never touches the FHIR server directly.  YOUR CODE does the "
    "querying.  The LLM helps you write the code and interpret the results."
)

# ── Slide 3: Three-Session Arc ────────────────────────────────────────
pdf.new_slide()
pdf.slide_title("Three-Session Arc")
pdf.subtitle("Session 1  -  Manual Pipeline  (today)")
pdf.bullet("You write the queries (with LLM help) and decide the order of steps.")
pdf.bullet("Goal: understand FHIR resources, references, and multi-step queries.")
pdf.ln(3)
pdf.subtitle("Session 2  -  Observe an Agent")
pdf.bullet("An AI agent executes the same pipeline autonomously using tool use.")
pdf.bullet("You predict its behaviour, then compare to reality.")
pdf.ln(3)
pdf.subtitle("Session 3  -  Open Exploration")
pdf.bullet("You design your own clinical questions with an expanded 6-tool agent.")
pdf.bullet("Goal: find failure modes and document them.  Finding failures = success.")
pdf.ln(5)
pdf.note_box(
    "Each session builds on the last.  Save your Session 1 notebook -- you will reference "
    "it in Sessions 2 and 3.", GRAY
)

# ── Slide 4: Today's Clinical Scenario ────────────────────────────────
pdf.new_slide()
pdf.slide_title("Today's Clinical Scenario")
pdf.set_font("Helvetica", "B", 16)
pdf.set_text_color(*DARK)
pdf.set_x(20)
pdf.multi_cell(230, 9,
    '"Find patients with Type 2 diabetes, retrieve their most recent HbA1c values, '
    'and identify those with poor glycemic control (HbA1c > 7.0%)."'
)
pdf.ln(4)
pdf.body("This is a real clinical informatics task.  To answer it you need to:")
pdf.bullet("Search a FHIR server for Condition resources (diabetes diagnosis)")
pdf.bullet("Follow references to retrieve Patient demographics (name, DOB, gender)")
pdf.bullet("Search for Observation resources (HbA1c lab results) per patient")
pdf.bullet("Combine and analyse the results to flag patients with poor control")
pdf.bullet("Generate a narrative clinical summary from the structured data")
pdf.ln(3)
pdf.note_box(
    "Note on threshold: In clinical practice 'poor control' varies by guideline (commonly "
    "7.0-9.0%).  We use > 7.0% because the Synthea synthetic data on this server skews "
    "toward lower HbA1c values.  This is a data artifact, not a clinical recommendation.",
    ORANGE
)

# ── Slide 5: What is FHIR? ───────────────────────────────────────────
pdf.new_slide()
pdf.slide_title("What is FHIR?")
pdf.body(
    "FHIR (Fast Healthcare Interoperability Resources) is an HL7 standard for exchanging "
    "healthcare information electronically.  Think of it as a RESTful API for clinical data."
)
pdf.ln(2)
pdf.subtitle("Key ideas", 15)
pdf.bullet("All clinical data is organised into Resources (Patient, Condition, Observation, ...)")
pdf.bullet("Each resource has a unique ID and a standard JSON structure")
pdf.bullet("Resources reference each other (e.g. a Condition points to a Patient)")
pdf.bullet("You query the server with simple HTTP GET requests and URL parameters")
pdf.ln(4)
pdf.subtitle("The server we are using", 15)
pdf.bullet("URL:  https://launch.smarthealthit.org/v/r4/fhir")
pdf.bullet("Public sandbox -- no login, no API key needed for Session 1")
pdf.bullet("Populated with synthetic patients generated by Synthea")
pdf.bullet("FHIR version R4  (the current widely-adopted release)")

# ── Slide 6: What is an API / JSON ────────────────────────────────────
pdf.new_slide()
pdf.slide_title("APIs and JSON in 3 Minutes")
pdf.subtitle("What is an API?", 15)
pdf.body(
    "An API (Application Programming Interface) lets programs talk to servers.  "
    "A FHIR server is an API: you send it a URL, it sends back JSON."
)
pdf.ln(1)
pdf.code_block(
    "GET https://launch.smarthealthit.org/v/r4/fhir/Patient?_count=1\n"
    "\n"
    "Response (JSON):\n"
    '{\n'
    '  "resourceType": "Bundle",\n'
    '  "total": 1243,\n'
    '  "entry": [\n'
    '    {\n'
    '      "resource": {\n'
    '        "resourceType": "Patient",\n'
    '        "id": "abc123",\n'
    '        "name": [{"given": ["Jane"], "family": "Doe"}],\n'
    '        "birthDate": "1965-04-12",\n'
    '        "gender": "female"\n'
    '      }\n'
    '    }\n'
    '  ]\n'
    '}'
)

# ── Slide 7: FHIR Resources ──────────────────────────────────────────
pdf.new_slide()
pdf.slide_title("FHIR Resources You Will Use Today")
pdf.ln(2)
pdf.subtitle("Condition", 16)
pdf.body("Records a diagnosis.  Contains the SNOMED CT code, onset date, and a reference to the Patient.")
pdf.code_block('GET /Condition?code=44054006&_count=30   -->  Bundle of Conditions')
pdf.ln(1)
pdf.subtitle("Patient", 16)
pdf.body("Demographics: name, birth date, gender, address.  Other resources point here via subject.reference.")
pdf.code_block('GET /Patient/{id}                        -->  Single Patient resource')
pdf.ln(1)
pdf.subtitle("Observation", 16)
pdf.body("A lab result or vital sign.  Contains the LOINC code, numeric value, unit, and date.")
pdf.code_block('GET /Observation?subject=Patient/{id}&code=4548-4&_sort=-date&_count=1')

# ── Slide 8: How Resources Link Together ──────────────────────────────
pdf.new_slide()
pdf.slide_title("How FHIR Resources Link Together")
pdf.body(
    "Our clinical question requires THREE types of FHIR resources linked by references:"
)
pdf.ln(2)
pdf.code_block(
    "Condition  (code: 44054006 -- Type 2 Diabetes, SNOMED CT)\n"
    "  |-- subject.reference ---->  Patient/{id}\n"
    "                                    ^\n"
    "Observation  (code: 4548-4 -- HbA1c, LOINC)\n"
    "  |-- subject ----------------------+\n"
)
pdf.ln(2)
pdf.body("To answer our question we must:", bold=True)
pdf.bullet("1.  Search Conditions  -->  find patients with diabetes")
pdf.bullet("2.  Follow references  -->  get Patient demographics (name, DOB, gender)")
pdf.bullet("3.  Search Observations -->  get each patient's most recent HbA1c value")
pdf.bullet("4.  Combine and analyse -->  flag patients with HbA1c > 7.0%")
pdf.ln(3)
pdf.note_box(
    "This multi-step pattern is fundamental to FHIR: clinical facts are stored in "
    "separate, linked resources.  No single query gives you the full answer."
)

# ── Slide 9: Clinical Codes Reference ─────────────────────────────────
pdf.new_slide()
pdf.slide_title("Clinical Codes Reference")
pdf.ln(2)
widths = [30, 30, 65, 40, 30]
pdf.table_row(["Code", "System", "Meaning", "Used In", "ICD-10"], widths, bold=True, fill=True)
pdf.table_row(["44054006", "SNOMED", "Type 2 Diabetes Mellitus", "Condition search", "E11"], widths)
pdf.table_row(["59621000", "SNOMED", "Essential Hypertension", "(Session 3)", "I10"], widths)
pdf.table_row(["4548-4", "LOINC", "Hemoglobin A1c (HbA1c)", "Observation search", "-"], widths)
pdf.table_row(["85354-9", "LOINC", "Blood Pressure panel", "(Session 3)", "-"], widths)
pdf.table_row(["2160-0", "LOINC", "Creatinine", "(Session 3)", "-"], widths)
pdf.ln(4)
pdf.subtitle("HbA1c Interpretation", 15)
pdf.bullet("< 5.7%   Normal")
pdf.bullet("5.7 - 6.4%   Prediabetes")
pdf.bullet(">= 6.5%   Diabetes")
pdf.bullet("> 7.0%   Poor glycemic control -- needs intervention  (our threshold)")
pdf.ln(3)
pdf.note_box(
    "IMPORTANT: This FHIR server uses SNOMED CT codes for conditions, NOT ICD-10.  "
    "Always use SNOMED codes (e.g. 44054006) when searching for conditions.",
    RED
)

# ── Slide 10: Your Workflow Today ─────────────────────────────────────
pdf.new_slide()
pdf.slide_title("Your Workflow Today")
pdf.body("You will work through the notebook step by step.  For each step:")
pdf.bullet("Read the instruction cell (markdown)")
pdf.bullet("Ask Claude to generate the Python code")
pdf.bullet("Paste the code into the empty cell and run it")
pdf.bullet("Run the verification cell to check your results")
pdf.ln(3)
pdf.subtitle("The 5 Steps", 15)
pdf.set_font("Helvetica", "B", 13)
pdf.set_text_color(*DARK)
steps = [
    ("Step 0:", "Run the setup cell and see your first FHIR query (pre-built)"),
    ("Step 1:", "Search for Condition resources with Type 2 Diabetes (SNOMED 44054006)"),
    ("Step 2:", "Follow patient references to get demographics (name, DOB, gender)"),
    ("Step 3:", "Search for each patient's most recent HbA1c Observation (LOINC 4548-4)"),
    ("Step 4:", "Generate a clinical summary by prompting Claude with your table"),
]
for label, desc in steps:
    pdf.set_x(25)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(22, 8, label)
    pdf.set_font("Helvetica", "", 13)
    pdf.cell(0, 8, desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

# ── Slide 11: Using Claude as Your Code Generator ─────────────────────
pdf.new_slide()
pdf.slide_title("Using Claude as Your Code Generator")
pdf.body(
    "In Session 1, you use the Claude web interface (claude.ai) to generate Python code.  "
    "The notebook tells you exactly what to ask.  Here is the workflow:"
)
pdf.ln(2)
pdf.code_block(
    "1. Read the prompt in the notebook  (e.g. 'Ask Claude: ...')\n"
    "2. Copy-paste the prompt into claude.ai\n"
    "3. Claude generates Python code using the requests library\n"
    "4. Copy Claude's code into the empty Colab cell\n"
    "5. Run the cell (Shift+Enter)\n"
    "6. Run the verification cell to confirm correctness"
)
pdf.ln(3)
pdf.subtitle("Good Prompt vs Poor Prompt", 15)
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(*GREEN)
pdf.set_x(25)
pdf.multi_cell(220, 6,
    'GOOD: "Write Python code using requests to search for Condition resources '
    'with SNOMED CT code 44054006 on the FHIR server at '
    'https://launch.smarthealthit.org/v/r4/fhir.  Limit to 30 results."'
)
pdf.ln(2)
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(*RED)
pdf.set_x(25)
pdf.multi_cell(220, 6,
    'POOR: "Get me diabetes patients from FHIR."'
)
pdf.ln(2)
pdf.set_text_color(*DARK)
pdf.set_font("Helvetica", "", 12)
pdf.set_x(25)
pdf.multi_cell(220, 6,
    "Be specific: include the exact code system, codes, server URL, and desired output format."
)

# ── Slide 12: FHIR Bundles Explained ──────────────────────────────────
pdf.new_slide()
pdf.slide_title("Understanding FHIR Bundles")
pdf.body(
    "Every FHIR search returns a Bundle -- a container that wraps the results:"
)
pdf.ln(1)
pdf.code_block(
    '{\n'
    '  "resourceType": "Bundle",\n'
    '  "total": 30,                    <-- total matches on server\n'
    '  "entry": [                      <-- array of results\n'
    '    {\n'
    '      "resource": {               <-- the actual clinical resource\n'
    '        "resourceType": "Condition",\n'
    '        "id": "cond-001",\n'
    '        "subject": {\n'
    '          "reference": "Patient/abc123"   <-- LINK to a Patient\n'
    '        },\n'
    '        "code": {\n'
    '          "coding": [{"code": "44054006", ...}]\n'
    '        }\n'
    '      }\n'
    '    },\n'
    '    ...                            <-- more entries\n'
    '  ]\n'
    '}'
)
pdf.ln(2)
pdf.bullet("bundle['total']  tells you how many matched on the entire server")
pdf.bullet("bundle['entry']  is the list of results (may be paginated)")
pdf.bullet("entry['resource']  is the actual FHIR resource (Condition, Observation, etc.)")

# ── Slide 13: Google Colab Refresher ──────────────────────────────────
pdf.new_slide()
pdf.slide_title("Google Colab Quick Reference")
pdf.body(
    "The notebooks run in Google Colab -- a free cloud Jupyter environment."
)
pdf.ln(2)
pdf.subtitle("Key actions", 15)
pdf.bullet("Shift+Enter  --  run the current cell and advance to the next")
pdf.bullet("Cells run in order.  Variables persist between cells.")
pdf.bullet("Code cells (gray background) contain Python.  Markdown cells contain instructions.")
pdf.bullet("If you see a play button on the left of a cell, click it to run.")
pdf.ln(3)
pdf.subtitle("Colab Secrets  (for Session 2 and 3 only)", 15)
pdf.bullet("Click the key icon in the left sidebar to open Secrets")
pdf.bullet("Store your ANTHROPIC_API_KEY there -- not in your code!")
pdf.bullet("Session 1 does NOT need any API keys -- just the FHIR server")
pdf.ln(3)
pdf.note_box(
    "If you lose your work: Colab autosaves to Google Drive.  You can also "
    "File > Download .ipynb to save a local copy."
)

# ── Slide 14: Key Learning Points ─────────────────────────────────────
pdf.new_slide()
pdf.slide_title("Key Learning Points")
pdf.ln(2)
pdf.subtitle("1. LLM as Code Generator", 16)
pdf.body(
    "You describe what you want in plain English, Claude writes the Python.  "
    "You inspect the code, paste it in, and run it.  The LLM is your assistant, not the pilot."
)
pdf.ln(2)
pdf.subtitle("2. Multi-Step Clinical Queries", 16)
pdf.body(
    "No single FHIR query answers our clinical question.  You must chain "
    "Condition -> Patient -> Observation queries and combine the results.  This is "
    "how real clinical informatics works."
)
pdf.ln(2)
pdf.subtitle("3. Separation of Concerns", 16)
pdf.body(
    "The LLM generates code and interprets results.  YOUR CODE queries the FHIR server.  "
    "This separation is critical for safety: the LLM never has direct database access.  "
    "In Session 2, the LLM will request tool calls, but your code still executes them."
)

# ── Slide 15: What to Expect ──────────────────────────────────────────
pdf.new_slide()
pdf.slide_title("What to Expect")
pdf.ln(2)
pdf.set_font("Helvetica", "B", 15)
pdf.set_text_color(*GREEN)
pdf.set_x(20)
pdf.cell(0, 8, "Success looks like:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_text_color(*DARK)
pdf.set_font("Helvetica", "", 13)
pdf.bullet("~30 patients with Type 2 Diabetes found (from Condition search)")
pdf.bullet("Demographics retrieved for all patients")
pdf.bullet("HbA1c values for most patients (some may have no lab data -- that's normal)")
pdf.bullet("A few patients flagged with poor control (HbA1c > 7.0%)")
pdf.bullet("A clinical summary paragraph generated by Claude")
pdf.ln(4)
pdf.set_font("Helvetica", "B", 15)
pdf.set_text_color(*ORANGE)
pdf.set_x(20)
pdf.cell(0, 8, "Common issues:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_text_color(*DARK)
pdf.set_font("Helvetica", "", 13)
pdf.bullet("Claude's code uses a different variable name than expected -- "
           "the verification cell will tell you what to rename")
pdf.bullet("Using ICD-10 codes instead of SNOMED CT -- use 44054006, not E11")
pdf.bullet("FHIR server returns 500/502 errors -- ask the instructor for the backup notebook")
pdf.bullet("Some patients have no HbA1c data -- expected, the verification cell handles it")

# ── Slide 16: Session 2 Preview ───────────────────────────────────────
pdf.new_slide()
pdf.slide_title("Next Session Preview")
pdf.subtitle("Session 2: Tool Use & AI Agents", 18)
pdf.ln(3)
pdf.body("Today you are the orchestrator:", bold=True)
pdf.bullet("You decide which query to run next")
pdf.bullet("You paste code, run it, inspect results, decide the next step")
pdf.bullet("The LLM only helps write code when you ask")
pdf.ln(3)
pdf.body("In Session 2 the LLM takes over orchestration:", bold=True)
pdf.bullet("You give the LLM a question and a set of tools (functions it can call)")
pdf.bullet("The LLM decides which tool to call, with what arguments, and in what order")
pdf.bullet("Your code executes the tool calls and feeds results back to the LLM")
pdf.bullet("The LLM synthesises a final answer from all the data it gathered")
pdf.ln(3)
pdf.note_box(
    'This is called "tool use" or "function calling."  The manual steps you do today '
    "become the tools the agent uses autonomously in Session 2."
)

# ── Slide 17: Questions & Getting Started ─────────────────────────────
pdf.new_slide()
pdf.slide_title("Questions?")
pdf.ln(6)
pdf.subtitle("Before you start:", 18)
pdf.ln(2)
pdf.bullet("Open the Session 1 notebook in Google Colab", size=15)
pdf.bullet("Run the first (Setup) cell to verify the FHIR server is reachable", size=15)
pdf.bullet("Have the Claude web interface (claude.ai) open in another tab", size=15)
pdf.bullet("Keep this orientation handy for the clinical codes reference", size=15)
pdf.ln(8)
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(*ACCENT)
pdf.set_x(20)
pdf.cell(0, 12, "Let's begin!")

# ── Slide 18: Resources ──────────────────────────────────────────────
pdf.new_slide()
pdf.slide_title("Resources")
pdf.ln(2)
pdf.subtitle("FHIR Server", 15)
pdf.body("https://launch.smarthealthit.org/v/r4/fhir")
pdf.ln(1)
pdf.subtitle("Claude Web Interface", 15)
pdf.body("https://claude.ai   (free tier is sufficient for Session 1)")
pdf.ln(1)
pdf.subtitle("FHIR Documentation", 15)
pdf.body("https://hl7.org/fhir/R4/")
pdf.ln(1)
pdf.subtitle("Key Codes to Remember", 15)
pdf.bullet("Type 2 Diabetes  (SNOMED CT):  44054006")
pdf.bullet("HbA1c  (LOINC):  4548-4")
pdf.bullet("Poor glycemic control threshold:  > 7.0%")
pdf.ln(4)
pdf.note_box(
    "REMEMBER:  Use SNOMED CT codes (not ICD-10) for all condition searches on this "
    "server!  The most common mistake is searching with ICD-10 code E11 instead of "
    "SNOMED 44054006.",
    RED
)

# ══════════════════════════════════════════════════════════════════════════
#  WRITE OUTPUT
# ══════════════════════════════════════════════════════════════════════════
out_dir = os.path.join(os.path.dirname(__file__), "..", "student_materials", "orientation_pdfs")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "pre_session1_orientation.pdf")
pdf.output(out_path)
print(f"Wrote {os.path.getsize(out_path):,} bytes -> {out_path}")
