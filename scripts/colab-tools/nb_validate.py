#!/usr/bin/env python3
"""
Standalone CLI for validating Jupyter notebook structure and code syntax.

Usage:
    python nb_validate.py <path.ipynb> [--strict]

Checks:
    - nbformat parse + validate
    - ast.parse() each code cell for syntax errors
    - Common Colab issues: missing pip installs, input() without @param
    - Kernel metadata exists

Outputs structured JSON report to stdout. Exit code 0 if all pass, 1 if errors.
"""

import argparse
import ast
import json
import re
import sys

import nbformat


def extract_imports(source: str) -> list[str]:
    """Extract top-level module names from import statements."""
    modules = []
    for line in source.splitlines():
        line = line.strip()
        m = re.match(r"^import\s+([\w.]+)", line)
        if m:
            modules.append(m.group(1).split(".")[0])
        m = re.match(r"^from\s+([\w.]+)\s+import", line)
        if m:
            modules.append(m.group(1).split(".")[0])
    return modules


def find_pip_installs(source: str) -> set[str]:
    """Extract package names from !pip install or %pip install lines."""
    packages = set()
    for line in source.splitlines():
        line = line.strip()
        m = re.match(r"^[!%]pip\s+install\s+(.+)", line)
        if m:
            for token in m.group(1).split():
                if token.startswith("-"):
                    continue
                # Strip version specifiers
                pkg = re.split(r"[><=!~]", token)[0].strip()
                if pkg:
                    packages.add(pkg.lower())
    return packages


# Standard library modules (common subset) that don't need pip install
STDLIB_MODULES = {
    "abc", "argparse", "ast", "asyncio", "base64", "bisect", "builtins",
    "calendar", "cgi", "cgitb", "cmd", "code", "codecs", "collections",
    "colorsys", "compileall", "concurrent", "configparser", "contextlib",
    "contextvars", "copy", "copyreg", "cProfile", "csv", "ctypes",
    "dataclasses", "datetime", "decimal", "difflib", "dis", "distutils",
    "doctest", "email", "encodings", "enum", "errno", "faulthandler",
    "filecmp", "fileinput", "fnmatch", "fractions", "ftplib", "functools",
    "gc", "getopt", "getpass", "gettext", "glob", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "idlelib", "imaplib", "importlib",
    "inspect", "io", "ipaddress", "itertools", "json", "keyword",
    "lib2to3", "linecache", "locale", "logging", "lzma", "mailbox",
    "math", "mimetypes", "mmap", "multiprocessing", "netrc", "numbers",
    "operator", "optparse", "os", "pathlib", "pdb", "pickle", "pickletools",
    "pipes", "pkgutil", "platform", "plistlib", "poplib", "posixpath",
    "pprint", "profile", "pstats", "pty", "py_compile", "pyclbr",
    "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtpd",
    "smtplib", "sndhdr", "socket", "socketserver", "sqlite3", "ssl",
    "stat", "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
    "tarfile", "tempfile", "termios", "test", "textwrap", "threading",
    "time", "timeit", "tkinter", "token", "tokenize", "trace",
    "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types",
    "typing", "unicodedata", "unittest", "urllib", "uu", "uuid",
    "venv", "warnings", "wave", "weakref", "webbrowser", "winreg",
    "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp",
    "zipfile", "zipimport", "zlib", "_thread",
}

# Modules commonly available in Colab without pip install
COLAB_BUILTINS = {
    "google", "IPython", "ipython", "ipywidgets", "matplotlib", "numpy",
    "pandas", "PIL", "scipy", "sklearn", "seaborn", "cv2", "tensorflow",
    "keras", "torch", "tqdm",
}


def validate_notebook(path: str, strict: bool = False) -> dict:
    """Validate a notebook and return a structured report."""
    report = {
        "valid": True,
        "notebook": path,
        "cells_checked": 0,
        "errors": [],
        "warnings": [],
        "per_cell": [],
    }

    # 1. Parse and validate with nbformat
    try:
        with open(path) as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        report["valid"] = False
        report["errors"].append(f"Failed to parse notebook: {e}")
        return report

    try:
        nbformat.validate(nb)
    except nbformat.ValidationError as e:
        report["valid"] = False
        report["errors"].append(f"nbformat validation failed: {e.message}")
        return report

    # 2. Check kernel metadata
    kernelspec = nb.get("metadata", {}).get("kernelspec")
    if not kernelspec:
        report["warnings"].append("No kernelspec metadata found")

    # 3. Collect all pip installs and imports across cells
    all_pip_packages: set[str] = set()
    all_imports: list[str] = []

    code_cells = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "code":
            src = cell.source
            all_pip_packages |= find_pip_installs(src)
            all_imports.extend(extract_imports(src))
            code_cells.append((i, src))

    report["cells_checked"] = len(code_cells)

    # 4. Per-cell validation
    for cell_idx, src in code_cells:
        cell_report = {"index": cell_idx, "type": "code", "status": "ok"}

        # Syntax check
        # Strip lines starting with ! or % (shell/magic commands) for ast parsing
        parseable_lines = []
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("!") or stripped.startswith("%"):
                parseable_lines.append("pass  # magic/shell line stripped")
            else:
                parseable_lines.append(line)
        parseable_src = "\n".join(parseable_lines)

        try:
            ast.parse(parseable_src)
        except SyntaxError as e:
            cell_report["status"] = "error"
            cell_report["message"] = f"SyntaxError line {e.lineno}: {e.msg}"
            report["errors"].append(
                f"Cell {cell_idx}: SyntaxError line {e.lineno}: {e.msg}"
            )
            report["valid"] = False

        # Check for input() without @param
        if "input(" in src and "#@param" not in src:
            msg = f"Cell {cell_idx}: input() call without #@param annotation (will block in Colab)"
            if cell_report["status"] == "ok":
                cell_report["status"] = "warning"
            cell_report.setdefault("message", msg)
            report["warnings"].append(msg)

        report["per_cell"].append(cell_report)

    # 5. Check for missing pip installs
    for mod in all_imports:
        mod_lower = mod.lower()
        if mod in STDLIB_MODULES:
            continue
        if mod in COLAB_BUILTINS or mod_lower in COLAB_BUILTINS:
            continue
        # Check if a matching pip package was installed
        # Common mapping: module name often matches package name (lowercase)
        if mod_lower not in all_pip_packages:
            # Some common mismatches
            known_mappings = {
                "cv2": "opencv-python",
                "PIL": "Pillow",
                "sklearn": "scikit-learn",
                "yaml": "pyyaml",
                "bs4": "beautifulsoup4",
                "dotenv": "python-dotenv",
                "attr": "attrs",
                "dateutil": "python-dateutil",
            }
            mapped = known_mappings.get(mod, "").lower()
            if mapped and mapped in all_pip_packages:
                continue
            msg = (
                f"Module '{mod}' is imported but no matching pip install found "
                f"(not in stdlib or Colab builtins)"
            )
            report["warnings"].append(msg)

    # 6. Apply strict mode
    if strict and report["warnings"]:
        report["valid"] = False
        report["errors"].extend(
            [f"[strict] {w}" for w in report["warnings"]]
        )

    # If any per-cell errors exist, mark invalid
    if any(c["status"] == "error" for c in report["per_cell"]):
        report["valid"] = False

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate Jupyter notebook structure and code syntax."
    )
    parser.add_argument("notebook", help="Path to .ipynb file")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    args = parser.parse_args()

    report = validate_notebook(args.notebook, strict=args.strict)
    json.dump(report, sys.stdout, indent=2)
    print()  # trailing newline
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
