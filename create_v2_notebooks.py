#!/usr/bin/env python3
"""
Create v2 copies of all hackathon notebooks with SBU FHIR Server auth.

Changes applied to v2 copies:
- SETUP cells: Add urllib3 import, warning suppression, FHIR credential retrieval,
  FHIR_SESSION creation, new FHIR_BASE URL
- Tool function cells: Replace requests.get → FHIR_SESSION.get
- Session 1 LLM prompt cells: Update to reference FHIR_SESSION
- Session 3 medication function: Fix parsing for medicationCodeableConcept.text fallback

Original notebooks are NOT modified.
"""

import json
import copy
import os
import re

STUDENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "student_materials", "notebooks")
INSTRUCTOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "instructor_materials", "notebooks")

OLD_FHIR_BASE = "https://launch.smarthealthit.org/v/r4/fhir"
NEW_FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"

# ──────────────────────────────────────────────────────────────
# Cell-level transformation functions
# ──────────────────────────────────────────────────────────────

def transform_session1_setup(source):
    """Transform the Session 1 SETUP cell (b8d1cbef) for auth."""
    # Replace imports
    source = source.replace(
        "import requests\nimport json\nimport pandas as pd",
        "import requests\nimport urllib3\nimport json\nimport pandas as pd"
    )

    # Add warning suppression + credentials + session after imports
    source = source.replace(
        'from IPython.display import display, HTML\n\nFHIR_BASE = "https://launch.smarthealthit.org/v/r4/fhir"',
        'from IPython.display import display, HTML\n\n'
        '# Suppress InsecureRequestWarning for self-signed SSL cert\n'
        'urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)\n\n'
        '# ---- FHIR Server (SBU IBM FHIR Server — requires Basic Auth) ----\n'
        f'FHIR_BASE = "{NEW_FHIR_BASE}"\n\n'
        '# ---- FHIR Credentials ----\n'
        'try:\n'
        '    from google.colab import userdata\n'
        '    fhir_user = userdata.get("FHIR_USERNAME")\n'
        '    fhir_pass = userdata.get("FHIR_PASSWORD")\n'
        'except (ImportError, Exception):\n'
        '    fhir_user = None\n'
        '    fhir_pass = None\n\n'
        'import os\n'
        'fhir_user = fhir_user or os.environ.get("FHIR_USERNAME", "fhiruser")\n'
        'fhir_pass = fhir_pass or os.environ.get("FHIR_PASSWORD", "BmI512@ccess")\n\n'
        'FHIR_SESSION = requests.Session()\n'
        'FHIR_SESSION.auth = (fhir_user, fhir_pass)\n'
        'FHIR_SESSION.verify = False'
    )

    # Replace metadata check
    source = source.replace(
        'resp = requests.get(f"{FHIR_BASE}/metadata", params={"_format": "json"}, timeout=10)',
        'resp = FHIR_SESSION.get(f"{FHIR_BASE}/metadata", params={"_format": "json"}, timeout=10)'
    )

    # Update success message
    source = source.replace(
        '    print(f"   This server has synthetic (Synthea) patient data. No login required.")',
        '    print(f"   Authenticated as: {fhir_user}")\n'
        '    print(f"   This server has synthetic (Synthea) patient data.")'
    )

    return source


def transform_session23_setup(source):
    """Transform Session 2/3 SETUP cells (dc03dbe9, 43fe6e11) for auth."""
    # Add urllib3 import
    source = source.replace(
        "import os, json, requests",
        "import os, json, requests, urllib3"
    )

    # Add warning suppression + credentials + session after Anthropic init
    old_fhir_section = (
        '# ---- FHIR Server ----\n'
        f'FHIR_BASE = "{OLD_FHIR_BASE}"'
    )
    new_fhir_section = (
        '# Suppress InsecureRequestWarning for self-signed SSL cert\n'
        'urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)\n\n'
        '# ---- FHIR Server (SBU IBM FHIR Server — requires Basic Auth) ----\n'
        f'FHIR_BASE = "{NEW_FHIR_BASE}"\n\n'
        '# ---- FHIR Credentials ----\n'
        'try:\n'
        '    fhir_user = userdata.get("FHIR_USERNAME")\n'
        '    fhir_pass = userdata.get("FHIR_PASSWORD")\n'
        'except (ImportError, Exception):\n'
        '    fhir_user = None\n'
        '    fhir_pass = None\n\n'
        'fhir_user = fhir_user or os.environ.get("FHIR_USERNAME", "fhiruser")\n'
        'fhir_pass = fhir_pass or os.environ.get("FHIR_PASSWORD", "BmI512@ccess")\n\n'
        'FHIR_SESSION = requests.Session()\n'
        'FHIR_SESSION.auth = (fhir_user, fhir_pass)\n'
        'FHIR_SESSION.verify = False'
    )
    source = source.replace(old_fhir_section, new_fhir_section)

    # Update status prints
    source = source.replace(
        'print(f"✅ FHIR server: {FHIR_BASE}")',
        'print(f"✅ FHIR server: {FHIR_BASE}")\n'
        'print(f"   Authenticated as: {fhir_user}")'
    )

    return source


def replace_requests_get(source):
    """Replace requests.get( with FHIR_SESSION.get( in a code cell."""
    return source.replace("requests.get(", "FHIR_SESSION.get(")


def fix_medication_parsing(source):
    """Fix medication parsing to handle medicationCodeableConcept.text fallback."""
    old = '        med = r.get("medicationCodeableConcept", {}).get("coding", [{}])[0]\n        results.append({\n            "medication": med.get("display", "unknown"),\n            "code": med.get("code", ""),'
    new = '        med_concept = r.get("medicationCodeableConcept", {})\n        coding = med_concept.get("coding", [{}])[0] if med_concept.get("coding") else {}\n        med_name = coding.get("display") or med_concept.get("text", "unknown")\n        results.append({\n            "medication": med_name,\n            "code": coding.get("code", ""),'
    return source.replace(old, new)


def transform_session1_prompt_cell(source):
    """Update Session 1 LLM prompt markdown cells to reference FHIR_SESSION."""
    # Replace the old URL in prompt text
    source = source.replace(OLD_FHIR_BASE, '{FHIR_BASE}')

    # Add note about FHIR_SESSION at the end of prompt instructions
    if "Write Python code using the `requests` library" in source:
        source = source.replace(
            "Write Python code using the `requests` library to search for Condition\n> resources",
            "Write Python code using `FHIR_SESSION.get()` (a pre-configured requests Session\n> with auth) to search for Condition\n> resources"
        )
        source = source.replace(
            "on the FHIR server at\n> https://launch.smarthealthit.org/v/r4/fhir.",
            "on the FHIR server.\n> The base URL is already stored in `FHIR_BASE`."
        )
        # Add note about FHIR_SESSION
        source += (
            "\n\n**Note:** `FHIR_SESSION` is a `requests.Session()` with authentication "
            "pre-configured. Use `FHIR_SESSION.get(f\"{FHIR_BASE}/...\")` instead of "
            "`requests.get()`."
        )

    if "fetches each Patient resource\n> from `https://launch.smarthealthit.org/v/r4/fhir/Patient/{id}`" in source:
        source = source.replace(
            "fetches each Patient resource\n> from `https://launch.smarthealthit.org/v/r4/fhir/Patient/{id}`",
            "fetches each Patient resource\n> from `f\"{FHIR_BASE}/Patient/{id}\"`\n> using `FHIR_SESSION.get()`"
        )
        if "**Note:** `FHIR_SESSION`" not in source:
            source += (
                "\n\n**Note:** `FHIR_SESSION` is a `requests.Session()` with authentication "
                "pre-configured. Use `FHIR_SESSION.get(f\"{FHIR_BASE}/...\")` instead of "
                "`requests.get()`."
            )

    if "search for Observation resources at\n> `https://launch.smarthealthit.org/v/r4/fhir/Observation`" in source:
        source = source.replace(
            "search for Observation resources at\n> `https://launch.smarthealthit.org/v/r4/fhir/Observation`",
            "search for Observation resources at\n> `f\"{FHIR_BASE}/Observation\"` using `FHIR_SESSION.get()`"
        )
        if "**Note:** `FHIR_SESSION`" not in source:
            source += (
                "\n\n**Note:** `FHIR_SESSION` is a `requests.Session()` with authentication "
                "pre-configured. Use `FHIR_SESSION.get(f\"{FHIR_BASE}/...\")` instead of "
                "`requests.get()`."
            )

    return source


def update_verification_fallback(source):
    """Update fallback code in verification cell to use FHIR_SESSION."""
    return source.replace("requests.get(f'{FHIR_BASE}", "FHIR_SESSION.get(f'{FHIR_BASE}")


# ──────────────────────────────────────────────────────────────
# Notebook processing
# ──────────────────────────────────────────────────────────────

def get_cell_source(cell):
    """Get cell source as a single string."""
    src = cell.get("source", "")
    if isinstance(src, list):
        return "".join(src)
    return src


def set_cell_source(cell, source):
    """Set cell source (always as a single string for consistency)."""
    cell["source"] = source


def process_notebook(src_path, dst_path, cell_transforms):
    """Read notebook, apply cell transforms, write output.

    cell_transforms: dict mapping cell_id -> transform function(source) -> source
    """
    with open(src_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    nb = copy.deepcopy(nb)

    for cell in nb["cells"]:
        cell_id = cell.get("id", "")
        source = get_cell_source(cell)

        if cell_id in cell_transforms:
            new_source = cell_transforms[cell_id](source)
            set_cell_source(cell, new_source)

    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(f"  Created: {os.path.basename(dst_path)} ({len(nb['cells'])} cells)")


# ──────────────────────────────────────────────────────────────
# Session 1 v2
# ──────────────────────────────────────────────────────────────

def create_session1_student_v2():
    src = os.path.join(STUDENT_DIR, "session1_student.ipynb")
    dst = os.path.join(STUDENT_DIR, "session1_student_v2.ipynb")
    transforms = {
        "b8d1cbef": transform_session1_setup,
        "c82eb0b2": replace_requests_get,
        "13314576": transform_session1_prompt_cell,
        "9f70bdd3": transform_session1_prompt_cell,
        "108ca158": transform_session1_prompt_cell,
        "e7688276": update_verification_fallback,
    }
    process_notebook(src, dst, transforms)


def create_session1_instructor_v2():
    src = os.path.join(INSTRUCTOR_DIR, "session1_instructor.ipynb")
    dst = os.path.join(INSTRUCTOR_DIR, "session1_instructor_v2.ipynb")
    transforms = {
        "b8d1cbef": transform_session1_setup,
        "c82eb0b2": replace_requests_get,
        "13314576": transform_session1_prompt_cell,
        "fb369eb3": replace_requests_get,      # Reference impl Step 1
        "9f70bdd3": transform_session1_prompt_cell,
        "d43e5687": replace_requests_get,      # Reference impl Step 2
        "108ca158": transform_session1_prompt_cell,
        "7984510c": replace_requests_get,      # Reference impl Step 3
        "e7688276": update_verification_fallback,
    }
    process_notebook(src, dst, transforms)


# ──────────────────────────────────────────────────────────────
# Session 2 v2
# ──────────────────────────────────────────────────────────────

def create_session2_student_v2():
    src = os.path.join(STUDENT_DIR, "session2_student.ipynb")
    dst = os.path.join(STUDENT_DIR, "session2_student_v2.ipynb")
    transforms = {
        "dc03dbe9": transform_session23_setup,
        "98ac9f52": replace_requests_get,
    }
    process_notebook(src, dst, transforms)


def create_session2_instructor_v2():
    src = os.path.join(INSTRUCTOR_DIR, "session2_instructor.ipynb")
    dst = os.path.join(INSTRUCTOR_DIR, "session2_instructor_v2.ipynb")
    transforms = {
        "dc03dbe9": transform_session23_setup,
        "98ac9f52": replace_requests_get,
    }
    process_notebook(src, dst, transforms)


# ──────────────────────────────────────────────────────────────
# Session 3 v2
# ──────────────────────────────────────────────────────────────

def create_session3_v2(src_path, dst_path):
    """Common logic for Session 3 student and instructor v2."""
    transforms = {
        "43fe6e11": transform_session23_setup,
        "960c2965": replace_requests_get,
        "ee22ddcd": lambda s: fix_medication_parsing(replace_requests_get(s)),
    }
    process_notebook(src_path, dst_path, transforms)


def create_session3_student_v2():
    src = os.path.join(STUDENT_DIR, "session3_student.ipynb")
    dst = os.path.join(STUDENT_DIR, "session3_student_v2.ipynb")
    create_session3_v2(src, dst)


def create_session3_instructor_v2():
    src = os.path.join(INSTRUCTOR_DIR, "session3_instructor.ipynb")
    dst = os.path.join(INSTRUCTOR_DIR, "session3_instructor_v2.ipynb")
    create_session3_v2(src, dst)


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    print("Creating v2 notebooks with SBU FHIR Server auth...\n")

    print("Session 1:")
    create_session1_student_v2()
    create_session1_instructor_v2()

    print("\nSession 2:")
    create_session2_student_v2()
    create_session2_instructor_v2()

    print("\nSession 3:")
    create_session3_student_v2()
    create_session3_instructor_v2()

    print("\nAll v2 notebooks created successfully.")


if __name__ == "__main__":
    main()
