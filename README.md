# FHIR + AI Hackathon 🏥🤖

> **Learn clinical informatics and AI agent patterns through hands-on FHIR data exploration**

A comprehensive three-session educational hackathon teaching students how to query healthcare data using FHIR (Fast Healthcare Interoperability Resources) and build autonomous AI agents with Claude.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FHIR R4](https://img.shields.io/badge/FHIR-R4-green.svg)](https://www.hl7.org/fhir/)
[![Claude Sonnet 4.5](https://img.shields.io/badge/Claude-Sonnet%204.5-purple.svg)](https://www.anthropic.com/claude)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📚 Table of Contents

- [Overview](#overview)
- [Learning Objectives](#learning-objectives)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Session Structure](#session-structure)
- [Clinical Scenario](#clinical-scenario)
- [Repository Structure](#repository-structure)
- [Setup Instructions](#setup-instructions)
- [Testing](#testing)
- [For Instructors](#for-instructors)
- [Technical Details](#technical-details)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## 🎯 Overview

This hackathon was designed for **BMI 512 (Clinical Informatics and AI)** at Stony Brook University. It teaches students with mixed backgrounds (MDs, PhD students, MS students from CS and biology) how to:

1. **Understand FHIR** - The modern standard for healthcare data exchange
2. **Query clinical data** - Using REST APIs and standardized terminologies (SNOMED CT, LOINC)
3. **Build AI agents** - That autonomously orchestrate multi-step clinical data queries
4. **Evaluate AI systems** - Recognize failure modes and design safeguards

### Why This Matters

Healthcare data is fragmented across systems. FHIR provides a standardized way to access it. AI agents can help clinicians answer complex questions by autonomously chaining together the right queries. But they must be trustworthy. This hackathon teaches both the potential and the pitfalls.

---

## 🎓 Learning Objectives

By completing this hackathon, students will:

### Session 1: FHIR Fundamentals
- ✅ Understand FHIR resource types (Patient, Condition, Observation)
- ✅ Query a FHIR server using REST APIs
- ✅ Use standardized clinical terminologies (SNOMED CT, LOINC)
- ✅ Chain multiple queries to answer clinical questions
- ✅ Use LLMs for code generation

### Session 2: AI Agent Basics
- ✅ Understand tool use (function calling) in LLMs
- ✅ Observe an agent autonomously orchestrating FHIR queries
- ✅ Analyze tool call traces and decision-making
- ✅ Compare manual vs. agentic workflows

### Session 3: Agent Evaluation
- ✅ Design custom clinical questions
- ✅ Identify agent failure modes (hallucination, wrong tool choice, etc.)
- ✅ Understand when to trust AI agents with clinical data
- ✅ Learn about MCP (Model Context Protocol) for tool standardization

---

## 📋 Prerequisites

### For Students

**Required:**
- Basic Python knowledge (variables, functions, loops)
- Google account (for Colab)
- Internet connection

**Helpful but not required:**
- Healthcare/clinical background
- Understanding of APIs
- Familiarity with pandas

### For Instructors

**Required:**
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Python 3.10+
- Git

---

## 🚀 Quick Start

### For Students

1. **Download the notebooks** from the `notebooks/` folder
2. **Upload to Google Colab**: [colab.research.google.com](https://colab.research.google.com/)
3. **Session 1**: No setup needed! Just run the cells
4. **Sessions 2 & 3**:
   - Get an Anthropic API key from your instructor
   - Add it to Colab Secrets (🔑 icon in left sidebar)
   - Name: `ANTHROPIC_API_KEY`
   - Value: Your API key

### For Instructors

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fhir-hackathon.git
cd fhir-hackathon

# Set your API key
export ANTHROPIC_API_KEY=your_api_key_here

# Validate the FHIR server
python validate_fhir_server.py

# Run the tests
python test_session1.py
python test_session2_simplified.py
python test_session3_simplified.py
```

---

## 📖 Session Structure

### Session 1: FHIR Fundamentals (1 hour)
**Materials:** `session1_student.ipynb`, `pre_session1_orientation.pdf`
**Backup:** `session1_backup.ipynb` (if SMART FHIR server is down)

**What students do:**
- Learn FHIR resource structure
- Query a public FHIR server (`https://launch.smarthealthit.org/v/r4/fhir`)
- Use Claude web UI to generate Python code
- Execute a multi-step clinical query manually

**Deliverable:** None (learning session)

### Session 2: Tool Use & Agents (1 hour)
**Materials:** `session2_student.ipynb`, `pre_session2_orientation.pdf`

**What students do:**
- Watch an AI agent autonomously execute the same pipeline from Session 1
- Analyze the tool call trace
- Understand how LLMs use function calling
- Compare manual vs. agentic approaches

**Deliverable:** None (observation session)

### Session 3: Open-Ended Exploration (1 hour)
**Materials:** `session3_student.ipynb`, `pre_session3_orientation.pdf`

**What students do:**
- Design 2+ custom clinical questions
- Run them through an agent with 6 tools
- Find and document agent failures or surprises
- Reflect on trustworthiness

**Deliverable:** JSON file (`hackathon_session3_*.json`)

---

## 🏥 Clinical Scenario

**Primary Question:**
> "Find patients with Type 2 diabetes, retrieve their most recent HbA1c values, and identify those with poor glycemic control (HbA1c > 7.0%)."

### Clinical Codes Used

| Code | System | Meaning | ICD-10 Ref |
|------|--------|---------|------------|
| **44054006** | SNOMED CT | Type 2 Diabetes Mellitus | E11 |
| **59621000** | SNOMED CT | Essential Hypertension | I10 |
| **4548-4** | LOINC | Hemoglobin A1c (HbA1c) | - |
| 85354-9 | LOINC | Blood Pressure panel | - |
| 2160-0 | LOINC | Creatinine | - |

### HbA1c Interpretation
- **< 5.7%**: Normal
- **5.7% – 6.4%**: Prediabetes
- **≥ 6.5%**: Diabetes
- **> 7.0%**: Poor glycemic control (needs intervention)

**Note:** We use > 7.0% because the Synthea-generated data on this server skews toward lower HbA1c values. In clinical practice, thresholds vary by guideline (commonly 7.0%–9.0%).

**Note:** The FHIR server uses **SNOMED CT** for conditions, not ICD-10.

---

## 📁 Repository Structure

```
fhir-hackathon/
├── README.md                          # This file
├── .gitignore                         # Excludes API keys, system files
├── .env.example                       # Template for API keys
│
├── notebooks/                         # Student materials
│   ├── session1_student.ipynb         # Session 1: Manual FHIR queries
│   ├── session1_backup.ipynb          # Session 1: Backup (local FHIR server)
│   ├── session2_student.ipynb         # Session 2: Agent observation
│   └── session3_student.ipynb         # Session 3: Open-ended exploration
│
├── pre_session1_orientation.pdf       # Session 1 slides
├── pre_session2_orientation.pdf       # Session 2 slides
├── pre_session3_orientation.pdf       # Session 3 slides
│
├── test_session1.py                   # Test Session 1 functionality
├── test_session2_simplified.py        # Test Session 2 agent
├── test_session3_simplified.py        # Test Session 3 agent
├── validate_fhir_server.py            # Validate FHIR data availability
│
├── fhir_hackathon_claude_code_spec.md # Complete build specification
├── TESTING_SUMMARY.md                 # Test results and validation
└── SIMPLIFICATION_SUMMARY.md          # Architecture decisions
```

---

## ⚙️ Setup Instructions

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fhir-hackathon.git
cd fhir-hackathon

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install anthropic requests pandas jupyter
```

### 2. API Key Configuration

**Option A: Environment Variable**
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

**Option B: .env File**
```bash
# Copy the template
cp .env.example .env

# Edit .env and add your key
ANTHROPIC_API_KEY=your_api_key_here
```

**Option C: Google Colab Secrets** (recommended for students)
1. Open a notebook in Colab
2. Click the 🔑 icon in the left sidebar
3. Add: `ANTHROPIC_API_KEY` = `your_api_key`

### 3. Validate Setup

```bash
# Check FHIR server connectivity
python validate_fhir_server.py

# Should output:
# ✅ 8/10 checks passed
```

---

## 🧪 Testing

All three sessions have been tested against the live FHIR server.

### Run All Tests

```bash
# Session 1: Manual FHIR queries
python test_session1.py

# Session 2: Agent with 3 tools
python test_session2_simplified.py

# Session 3: Agent with 6 tools
python test_session3_simplified.py
```

### Expected Results

- **Session 1**: Finds 30 patients with Type 2 diabetes
- **Session 2**: Agent makes ~26 tool calls, identifies patients with poor control
- **Session 3**: Agent makes 4+ tool calls, generates comprehensive patient profiles

### Validation Results

```bash
python validate_fhir_server.py
```

**Passing checks (8/10):**
- ✅ Server reachable (FHIR 4.0.0)
- ✅ Type 2 Diabetes patients found (20+)
- ✅ Patient demographics fetchable
- ✅ HbA1c observations available
- ✅ HbA1c > 7.0% found (1+ patients)
- ✅ Medications available
- ✅ Encounters available
- ✅ Multiple conditions per patient

**Known limitations:**
- ⚠️ Hypertension SNOMED code returns 0 results
- ⚠️ Creatinine observations sparse in dataset

---

## 👨‍🏫 For Instructors

### Before the Hackathon

1. **Test all notebooks** with your API key
2. **Review orientation PDFs** with students
3. **Set up Colab access** or local Jupyter environment
4. **Prepare API keys** for students (or have them get their own)

### Session Guidelines

**Session 1 (1 hour):**
- 5 min: Overview and FHIR intro
- 10 min: Explain clinical scenario
- 40 min: Students work through notebook
- 5 min: Debrief and questions

**Session 2 (1 hour):**
- 5 min: Recap Session 1
- 10 min: Explain tool use concept
- 35 min: Students run agent and analyze
- 10 min: Discussion of observations

**Session 3 (1 hour):**
- 5 min: Intro to open-ended exploration
- 40 min: Students design and test questions
- 10 min: Share failure modes discovered
- 5 min: MCP introduction and wrap-up

### Grading (Optional)

Session 3 generates a JSON deliverable:

```bash
# Collect all student submissions
mkdir submissions
# Students upload their hackathon_session3_*.json files

# Grade (requires implementation of grade_session3.py)
python grading/grade_session3.py submissions/
```

**Grading criteria:**
- ✅ Ran 2+ different questions
- ✅ Found at least 1 failure mode or surprise
- ✅ Documented observations clearly
- ✅ Reflected on trustworthiness

---

## 🔧 Technical Details

### FHIR Server

**URL:** `https://launch.smarthealthit.org/v/r4/fhir`

**Characteristics:**
- Public sandbox (no authentication)
- FHIR R4 compliant
- Synthea-generated synthetic data
- ~100+ patients with various conditions

**Backup:** If the SMART server is unavailable, use `session1_backup.ipynb` which runs a local Flask-based FHIR server with 30 cached Synthea patients embedded directly in the notebook. Students write identical code — only `FHIR_BASE` changes to `localhost:5050`.

**API Examples:**

```bash
# Get metadata
curl https://launch.smarthealthit.org/v/r4/fhir/metadata

# Search conditions
curl "https://launch.smarthealthit.org/v/r4/fhir/Condition?code=44054006&_count=10"

# Get patient
curl https://launch.smarthealthit.org/v/r4/fhir/Patient/abc123
```

### AI Model

**Provider:** Anthropic
**Model:** Claude Sonnet 4.5 (`claude-sonnet-4-20250514`)
**Tool Use:** Native Anthropic format

**Why Anthropic-only?**
- Simplified from dual-provider architecture
- Better educational clarity
- Native tool use support
- Consistent behavior

### Architecture

**Session 1:** Manual orchestration
```
Student → Claude Web UI → Python Code → FHIR Server
```

**Sessions 2 & 3:** Agentic orchestration
```
Student Question → Agent Loop → Tool Calls → FHIR Server
                      ↑            ↓
                      └── Results ─┘
```

**Tool Schema Format:** Anthropic native
```python
{
    "name": "search_conditions",
    "description": "Search for Condition resources...",
    "input_schema": {
        "type": "object",
        "properties": {...},
        "required": [...]
    }
}
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/improvement`)
3. **Make your changes**
4. **Test thoroughly**
5. **Commit** (`git commit -m 'Add some improvement'`)
6. **Push** (`git push origin feature/improvement`)
7. **Open a Pull Request**

### Areas for Improvement

- 🎯 Additional clinical scenarios
- 🧪 More test coverage
- 📚 Additional FHIR resources (Procedures, DiagnosticReports)
- 🌐 Multi-language support
- 🎨 Better visualizations
- 🤖 Additional LLM providers

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **SMART Health IT** for providing the public FHIR sandbox
- **Anthropic** for Claude and tool use capabilities
- **HL7** for the FHIR specification
- **Synthea** for synthetic patient data
- **BMI 512 students** for feedback and testing

---

## 📞 Support

**For students:**
- Review the orientation PDFs in this repository
- Check the notebook comments and instructions
- Ask your instructor

**For instructors:**
- Open an issue in this repository
- Review `fhir_hackathon_claude_code_spec.md` for detailed documentation
- Check `TESTING_SUMMARY.md` for validation results

---

## 🔗 Useful Links

- [FHIR Documentation](https://www.hl7.org/fhir/)
- [SMART on FHIR](https://docs.smarthealthit.org/)
- [Anthropic Claude Docs](https://docs.anthropic.com/)
- [SNOMED CT Browser](https://browser.ihtsdotools.org/)
- [LOINC Search](https://loinc.org/)
- [Synthea Patient Generator](https://synthetichealth.github.io/synthea/)

---

<div align="center">

**Built with ❤️ for clinical informatics education**

⭐ Star this repo if you find it helpful!

</div>
