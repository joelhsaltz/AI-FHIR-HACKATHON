# FHIR + AI Hackathon - Student Materials

Welcome! This folder contains everything you need for the three-session hackathon.

## 📁 What's in This Folder

### Notebooks
- `session1_student.ipynb` - FHIR Fundamentals (manual queries)
- `session1_backup.ipynb` - Session 1 Backup (uses local FHIR server — use this if the SMART server is down)
- `session2_student.ipynb` - AI Agent Basics (observe tool use)
- `session3_student.ipynb` - Open-Ended Exploration (your turn!)

### Orientation PDFs
- `pre_session1_orientation.pdf` - Introduction to FHIR
- `pre_session2_orientation.pdf` - Introduction to AI Agents
- `pre_session3_orientation.pdf` - Agent Evaluation & MCP

## 🚀 Quick Start

### For Session 1 (No API Key Needed!)
1. Download `notebooks/session1_student.ipynb`
2. Upload to [Google Colab](https://colab.research.google.com/)
3. Follow the instructions in the notebook
4. Use Claude web UI to generate code

> **FHIR server not responding?** Use `session1_backup.ipynb` instead. It runs
> a local FHIR server inside the notebook with cached patient data. Your code
> will be identical — the only difference is `FHIR_BASE` points to `localhost`.

### For Sessions 2 & 3 (API Key Required)
1. Download the session notebook
2. Upload to Google Colab
3. Get your API key from your instructor
4. Add it to Colab Secrets:
   - Click the 🔑 icon in the left sidebar
   - Add new secret:
     - **Name:** `ANTHROPIC_API_KEY`
     - **Value:** Your API key
5. Run the notebook!

## 📖 Session Overview

| Session | What You'll Do | Time | Deliverable |
|---------|----------------|------|-------------|
| 1 | Learn FHIR, write queries manually with LLM help | 1 hour | None |
| 2 | Watch AI agent execute same queries autonomously | 1 hour | None |
| 3 | Design custom questions, find agent failures | 1 hour | JSON file |

## 🏥 Clinical Scenario

**Main Question:**
> "Find patients with Type 2 diabetes, retrieve their most recent HbA1c values, and identify those with poor glycemic control (HbA1c > 7.0%)."

**Important Codes:**
- **Type 2 Diabetes:** SNOMED CT `44054006` (not ICD-10 E11!)
- **HbA1c:** LOINC `4548-4`
- **Poor Control:** HbA1c > 7.0%

**FHIR Server:** `https://launch.smarthealthit.org/v/r4/fhir`

## ❓ Need Help?

1. **Read the orientation PDFs** - They explain everything step-by-step
2. **Check notebook comments** - Detailed instructions in each cell
3. **Ask your instructor** - They're here to help!
4. **Review error messages** - They usually tell you what's wrong

## 🎯 Learning Goals

By the end of this hackathon, you'll understand:
- ✅ How FHIR structures healthcare data
- ✅ How to query clinical data with standardized codes
- ✅ How LLMs can generate and execute code
- ✅ How AI agents autonomously orchestrate queries
- ✅ When to trust (and not trust) AI in healthcare

## 💡 Tips for Success

**Session 1:**
- Take your time understanding FHIR resources
- Read the example outputs carefully
- Copy/paste prompts exactly to Claude web UI
- Verify each step before moving on

**Session 2:**
- Compare agent behavior to what you did manually
- Count the tool calls - does it match your steps?
- Look for any mistakes or inefficiencies

**Session 3:**
- Start with simple questions, then get creative
- Try to break the agent - find edge cases!
- Document everything for your deliverable
- Reflect on trustworthiness and safety

## 📦 Deliverables

**Session 3 Only:**
- The notebook auto-generates `hackathon_session3_YOURID.json`
- Download this file
- Submit to your instructor

**What's graded:**
- ✅ Ran 2+ different clinical questions
- ✅ Found at least 1 agent failure or surprise
- ✅ Clear documentation of observations
- ✅ Thoughtful reflection on trustworthiness

## 🔗 Useful Resources

- [FHIR Documentation](https://www.hl7.org/fhir/)
- [SNOMED CT Browser](https://browser.ihtsdotools.org/)
- [LOINC Search](https://loinc.org/)
- [Claude Documentation](https://docs.anthropic.com/)

---

**Questions?** Ask your instructor!

**Good luck and have fun!** 🎓
