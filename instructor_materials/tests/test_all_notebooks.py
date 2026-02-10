"""
Unified test suite for all 3 student notebooks.

- TestSession1: FHIR server queries only (no API key needed)
- TestSession2: Tool-use agent with 3 tools (requires ANTHROPIC_API_KEY)
- TestSession3: Extended agent with 6 tools (requires ANTHROPIC_API_KEY)

Run:
    pytest test_all_notebooks.py -v                     # all tests
    pytest test_all_notebooks.py::TestSession1 -v       # session 1 only
    pytest test_all_notebooks.py -k "not requires_api_key" -v  # skip API tests
"""

import json
import pytest
import pandas as pd

from conftest import (
    FHIR_BASE, MODEL, fhir_get,
    search_conditions, get_patient, search_observations,
    search_medications, search_encounters, search_all_conditions,
    SESSION2_TOOLS, SESSION2_FUNCTIONS,
    SESSION3_TOOLS, SESSION3_FUNCTIONS,
    SYSTEM_PROMPT, run_agent,
)


# ======================================================================
# Session 1: FHIR Fundamentals (no API key needed)
# ======================================================================

class TestSession1:
    """Tests mirroring every code cell in session1_student.ipynb."""

    def test_fhir_server_connection(self):
        """Setup cell: verify FHIR server is reachable."""
        resp = fhir_get(
            f"{FHIR_BASE}/metadata",
            params={"_format": "json"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("fhirVersion"), "No FHIR version in metadata"

    def test_patient_fetch(self):
        """Step 0: fetch Patient resources from the server."""
        resp = fhir_get(
            f"{FHIR_BASE}/Patient",
            params={"_count": 3, "_format": "json"}
        )
        resp.raise_for_status()
        bundle = resp.json()
        assert bundle["resourceType"] == "Bundle"
        entries = bundle.get("entry", [])
        assert len(entries) > 0, "No patients returned"
        first = entries[0]["resource"]
        assert "id" in first, "Patient resource missing 'id'"
        assert "name" in first, "Patient resource missing 'name'"

    def test_condition_search(self):
        """Step 1 (student cell): search Conditions for SNOMED 44054006."""
        resp = fhir_get(
            f"{FHIR_BASE}/Condition",
            params={"code": "44054006", "_count": 20, "_format": "json"}
        )
        resp.raise_for_status()
        bundle = resp.json()
        entries = bundle.get("entry", [])
        assert len(entries) > 0, "No Type 2 Diabetes conditions found"

        patient_refs = set()
        for entry in entries:
            ref = entry["resource"].get("subject", {}).get("reference", "")
            if ref:
                patient_refs.add(ref)
        assert len(patient_refs) > 0, "No patient references extracted"

        # Verify IDs can be extracted
        patient_ids = [ref.split("/")[-1] for ref in patient_refs if "/" in ref]
        assert len(patient_ids) > 0

    def test_patient_demographics(self):
        """Step 2 (student cell): follow references to get patient demographics."""
        # Get a patient ID from condition search
        conds = search_conditions("44054006", max_results=5)
        pid = conds["results"][0]["patient_reference"].split("/")[-1]

        patient = get_patient(pid)
        assert patient["id"] == pid
        assert patient["name"], "Patient name is empty"
        assert patient["birthDate"] != "unknown"
        assert patient["gender"] in ("male", "female", "other", "unknown")

    def test_hba1c_observations(self):
        """Step 3 (student cell): search HbA1c observations for diabetic patients."""
        conds = search_conditions("44054006", max_results=20)
        patient_ids = list({
            r["patient_reference"].split("/")[-1]
            for r in conds["results"]
            if "/" in r["patient_reference"]
        })

        found_hba1c = False
        for pid in patient_ids[:10]:
            obs = search_observations(pid, "4548-4", max_results=1)
            if obs["results"]:
                found_hba1c = True
                result = obs["results"][0]
                assert "date" in result
                assert "value" in result
                break

        assert found_hba1c, "No HbA1c observations found for any diabetic patient"

    def test_combined_analysis(self):
        """Verification cell: merge data and flag glycemic control."""
        # Replicate the full pipeline
        conds = search_conditions("44054006", max_results=20)
        patient_ids = list({
            r["patient_reference"].split("/")[-1]
            for r in conds["results"]
            if "/" in r["patient_reference"]
        })

        patients = []
        for pid in patient_ids[:5]:
            patients.append(get_patient(pid))

        observations = []
        for p in patients:
            obs = search_observations(p["id"], "4548-4", max_results=1)
            if obs["results"]:
                r = obs["results"][0]
                observations.append({
                    "patient_id": p["id"],
                    "date": r["date"],
                    "value": r["value"],
                    "unit": r.get("unit", "")
                })
            else:
                observations.append({
                    "patient_id": p["id"],
                    "date": "N/A",
                    "value": "N/A",
                    "unit": ""
                })

        df_patients = pd.DataFrame(patients)
        df_obs = pd.DataFrame(observations)
        df_patients["id"] = df_patients["id"].astype(str)
        df_obs["patient_id"] = df_obs["patient_id"].astype(str)

        df_merged = df_obs.merge(df_patients, left_on="patient_id", right_on="id", how="left")
        df_merged["hba1c_numeric"] = pd.to_numeric(df_merged["value"], errors="coerce")

        assert len(df_merged) > 0, "Merged dataframe is empty"
        assert "hba1c_numeric" in df_merged.columns
        # At least some patients should have data
        has_data = df_merged["hba1c_numeric"].notna().sum()
        assert has_data > 0, "No patients have numeric HbA1c values"


# ======================================================================
# Session 2: Tool Use Agent with 3 Tools
# ======================================================================

@pytest.mark.requires_api_key
class TestSession2:
    """Tests for session2_student.ipynb (Anthropic tool-use agent)."""

    def test_fhir_tools_smoke(self):
        """Smoke test: all 3 Session 2 FHIR tool functions work."""
        conds = search_conditions("44054006", max_results=3)
        assert conds["results"], "search_conditions returned no results"

        pid = conds["results"][0]["patient_reference"].split("/")[-1]

        patient = get_patient(pid)
        assert patient["name"], "get_patient returned empty name"

        obs = search_observations(pid, "4548-4", max_results=1)
        assert isinstance(obs["results"], list), "search_observations didn't return a list"

    def test_tool_schemas_valid(self):
        """Tool schemas have matching function entries."""
        for schema in SESSION2_TOOLS:
            name = schema["name"]
            assert name in SESSION2_FUNCTIONS, f"No function for tool '{name}'"
            assert "input_schema" in schema, f"Tool '{name}' missing input_schema"
            required = schema["input_schema"].get("required", [])
            assert len(required) > 0, f"Tool '{name}' has no required params"

    def test_agent_loop(self, anthropic_client):
        """Full agent run: diabetes + HbA1c question with 3 tools."""
        question = (
            "Find patients with Type 2 diabetes and their most recent HbA1c values. "
            "Which patients have poor glycemic control (HbA1c > 7.5%)?"
        )

        answer, tool_calls = run_agent(
            client=anthropic_client,
            question=question,
            tools=SESSION2_TOOLS,
            available_functions=SESSION2_FUNCTIONS,
        )

        # Agent should have made tool calls
        assert len(tool_calls) > 0, "Agent made no tool calls"

        # Agent should have used all 3 tools
        tools_used = {tc["function"] for tc in tool_calls}
        assert "search_conditions" in tools_used, "Agent never searched conditions"
        assert "get_patient" in tools_used, "Agent never fetched patients"
        assert "search_observations" in tools_used, "Agent never searched observations"

        # Agent should produce a non-empty final answer
        assert len(answer) > 50, f"Agent answer too short: {answer[:100]}"
        assert answer != "Max steps reached without final answer"


# ======================================================================
# Session 3: Extended Agent with 6 Tools
# ======================================================================

@pytest.mark.requires_api_key
class TestSession3:
    """Tests for session3_student.ipynb (6-tool agent)."""

    def test_extended_tools_smoke(self):
        """Smoke test: all 6 Session 3 FHIR tool functions work."""
        conds = search_conditions("44054006", max_results=3)
        pid = conds["results"][0]["patient_reference"].split("/")[-1]

        # Session 2 tools
        patient = get_patient(pid)
        assert patient["name"]
        obs = search_observations(pid, "4548-4", max_results=1)
        assert isinstance(obs["results"], list)

        # Session 3 new tools
        meds = search_medications(pid, max_results=3)
        assert isinstance(meds["results"], list), "search_medications didn't return a list"

        encs = search_encounters(pid, max_results=3)
        assert isinstance(encs["results"], list), "search_encounters didn't return a list"

        all_conds = search_all_conditions(pid, max_results=5)
        assert isinstance(all_conds["results"], list), "search_all_conditions didn't return a list"

    def test_extended_tool_schemas_valid(self):
        """All 6 tool schemas have matching function entries."""
        assert len(SESSION3_TOOLS) == 6, f"Expected 6 tools, got {len(SESSION3_TOOLS)}"
        for schema in SESSION3_TOOLS:
            name = schema["name"]
            assert name in SESSION3_FUNCTIONS, f"No function for tool '{name}'"
            assert "input_schema" in schema, f"Tool '{name}' missing input_schema"

    def test_agent_loop_extended(self, anthropic_client):
        """Agent with 6 tools answers a multi-resource question."""
        question = (
            "Find one patient with Type 2 diabetes. "
            "Tell me their demographics, all conditions, and current medications."
        )

        answer, tool_calls = run_agent(
            client=anthropic_client,
            question=question,
            tools=SESSION3_TOOLS,
            available_functions=SESSION3_FUNCTIONS,
        )

        assert len(tool_calls) > 0, "Agent made no tool calls"

        tools_used = {tc["function"] for tc in tool_calls}
        # Agent must search conditions and get patient at minimum
        assert "search_conditions" in tools_used, "Agent never searched conditions"
        assert "get_patient" in tools_used, "Agent never fetched patient"

        # Agent should use at least one of the new Session 3 tools
        session3_new_tools = {"search_medications", "search_encounters", "search_all_conditions"}
        used_new = tools_used & session3_new_tools
        assert len(used_new) > 0, (
            f"Agent didn't use any Session 3 tools. Used: {tools_used}"
        )

        assert len(answer) > 50, f"Agent answer too short: {answer[:100]}"
        assert answer != "Max steps reached without final answer"
