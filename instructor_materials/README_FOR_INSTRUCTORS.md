# FHIR + AI Hackathon - Instructor Materials

This folder contains all testing, validation, and instructor resources.

## 📁 What's in This Folder

### Tests Directory (`tests/`)
- `test_session1.py` - Validates Session 1 notebook functionality
- `test_session2_simplified.py` - Tests Session 2 agent (3 tools)
- `test_session3_simplified.py` - Tests Session 3 agent (6 tools)
- `test_session2.py` - Alternative Session 2 test

### Validation Files
- `validate_fhir_server.py` - Comprehensive FHIR server validation
- `validation_results.json` - Latest validation results
- `TESTING_SUMMARY.md` - Complete test results and known issues

## 🚀 Quick Start

### 1. Set Up Your API Key

```bash
# Option 1: Environment variable
export ANTHROPIC_API_KEY=your_api_key_here

# Option 2: .env file (copy from root .env.example)
cp ../.env.example ../.env
# Edit .env and add your key
```

### 2. Validate FHIR Server

```bash
python validate_fhir_server.py
```

**Expected:** 8/10 checks pass
- ✅ Server reachable
- ✅ Type 2 Diabetes patients found
- ✅ HbA1c data available
- ✅ HbA1c > 7.0% patients found
- ⚠️ Hypertension code returns 0 (known issue)
- ⚠️ Creatinine sparse in dataset (known issue)

### 3. Run All Tests

```bash
# Session 1: Manual FHIR queries
python tests/test_session1.py

# Session 2: Agent with 3 tools
python tests/test_session2_simplified.py

# Session 3: Agent with 6 tools
python tests/test_session3_simplified.py
```

**All tests should PASS** ✅

## 📖 Pre-Hackathon Checklist

### One Week Before
- [ ] Test all notebooks with your API key
- [ ] Run validation script - confirm 8/10 checks pass
- [ ] Review orientation PDFs
- [ ] Prepare student API keys (or guide them to get their own)
- [ ] Set up Colab or Jupyter environment
- [ ] Print/share orientation PDFs with students

### Day Before
- [ ] Re-test all notebooks (in case FHIR server changed)
- [ ] Verify Colab access works
- [ ] Test student API keys
- [ ] Prepare example outputs to show students
- [ ] Review session timing

### Day Of
- [ ] Share student materials folder
- [ ] Explain Colab Secrets setup
- [ ] Have `session1_backup.ipynb` ready in case SMART server is down
- [ ] Monitor for FHIR server issues

## 🎓 Session Guidelines

### Session 1 (1 hour) - FHIR Fundamentals
**Timing:**
- 5 min: Overview and FHIR introduction
- 10 min: Explain clinical scenario and codes
- 40 min: Students work through notebook
- 5 min: Debrief and Q&A

**What to Monitor:**
- Students understanding FHIR resource structure
- Successful FHIR server queries
- Proper use of SNOMED CT codes (not ICD-10)
- Understanding of multi-step query workflow

**Common Issues:**
- Forgetting to use SNOMED CT codes
- Not extracting patient IDs from references
- Confusion about Bundle vs Resource
- Empty HbA1c results for some patients (expected)
- FHIR server returning 500/502 errors (switch to `session1_backup.ipynb`)

### Session 2 (1 hour) - AI Agents
**Timing:**
- 5 min: Recap Session 1
- 10 min: Explain tool use concept
- 35 min: Students run agent and analyze
- 10 min: Discussion of observations

**What to Monitor:**
- API key properly configured
- Agent making ~20-30 tool calls
- Students analyzing tool call trace
- Comparing to their Session 1 manual workflow

**Common Issues:**
- API key not in Colab Secrets
- Agent taking longer than expected (normal)
- Confusion about tool schemas
- Not understanding agent decision process

### Session 3 (1 hour) - Open Exploration
**Timing:**
- 5 min: Introduction to open-ended exploration
- 40 min: Students design and test questions
- 10 min: Share failure modes discovered
- 5 min: MCP introduction and wrap-up

**What to Monitor:**
- Students asking diverse questions
- Finding and documenting failures
- Critical thinking about trustworthiness
- JSON deliverable generated

**Common Issues:**
- Questions too vague (expected - learning moment!)
- Not finding failures (encourage edge cases)
- Forgetting to save JSON deliverable
- Running out of time (have example questions ready)

## 📊 Expected Test Results

### Session 1
- Finds 30 patients with Type 2 diabetes
- Retrieves demographics for all
- Gets HbA1c for most patients
- Some patients have HbA1c > 7.0%

### Session 2
- Agent makes 20-30 tool calls
- Finds patients with poor control
- May identify historical data (HbA1c > 7.0% in past)
- No hallucinations in final answer

### Session 3
- Agent uses 4+ tools depending on question
- Successfully handles multi-condition queries
- May fail on vague questions (expected)
- Generates detailed patient profiles

## 🐛 Known Issues & Workarounds

### FHIR Server
- **Hypertension code 59621000 returns 0**: Use different code or skip
- **Creatinine sparse**: Expected, students can try other LOINC codes
- **Some patient IDs return 410**: Server cleanup, normal behavior

### Agent Behavior
- **No patients with HbA1c > 9%**: Why we use 7.0% threshold (Synthea data skews low)
- **Agent may be verbose**: Expected with detailed queries
- **Tool call order varies**: Non-deterministic, all valid

### Notebooks
- **Colab Secrets not working**: Use environment variables instead
- **Long execution time**: Agent thinking, not stuck
- **API rate limits**: Rare, wait 60 seconds

## 📝 Grading (Optional)

If collecting Session 3 deliverables:

```bash
# Collect submissions
mkdir submissions
# Students upload hackathon_session3_*.json files

# Manual review criteria:
# ✅ 2+ different questions (check questions array)
# ✅ 1+ failure mode documented (check observations)
# ✅ Clear documentation (read final answer quality)
# ✅ Thoughtful reflection (check reflection section)
```

**Grading rubric:**
- **Participation (40%)**: Ran 2+ questions with tool calls
- **Observation (30%)**: Found and documented failures/surprises
- **Analysis (20%)**: Clear explanation of what happened
- **Reflection (10%)**: Thoughtful discussion of trustworthiness

## 🔧 Troubleshooting

### Student Can't Connect to FHIR Server
```bash
# Test manually:
curl https://launch.smarthealthit.org/v/r4/fhir/metadata

# If down, use alternate:
curl https://r4.smarthealthit.org/metadata
```

**If the SMART server is completely down:** Have students switch to
`session1_backup.ipynb`. This notebook runs a local Flask-based FHIR server
inside the notebook with 30 cached Synthea patients (Type 2 Diabetes cohort).
Students write identical `requests.get()` code — the only difference is
`FHIR_BASE` points to `http://localhost:5050`. No internet required for the
FHIR queries. The backup produces the same 5 patients with poor glycemic
control (>7.0% HbA1c).

### API Key Not Working
```bash
# Verify key format (should start with sk-ant-api03-)
# Test with simple API call
python -c "from anthropic import Anthropic; print(Anthropic(api_key='YOUR_KEY').messages.create(model='claude-sonnet-4-20250514', max_tokens=10, messages=[{'role':'user','content':'hi'}]))"
```

### Tests Failing
```bash
# Re-run validation
python validate_fhir_server.py

# Check API key is set
echo $ANTHROPIC_API_KEY

# Run tests individually to isolate issue
```

## 📚 Additional Resources

- `TESTING_SUMMARY.md` - Complete test results
- `../docs/fhir_hackathon_claude_code_spec.md` - Full build spec
- Main repository README - Student-facing information

## 🤝 Support

- **Repository issues:** [GitHub Issues](https://github.com/joelhsaltz/AI-FHIR-HACKATHON/issues)
- **Anthropic support:** https://support.anthropic.com/
- **FHIR server:** https://docs.smarthealthit.org/

---

**Good luck with your hackathon!** 🎓

If you make improvements, please commit and push them back to GitHub!
