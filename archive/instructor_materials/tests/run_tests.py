#!/usr/bin/env python3
"""
Run the notebook test suite.

Usage:
    python run_tests.py                # run all tests (prompts for API key if not set)
    python run_tests.py --session 1    # session 1 only (no API key needed)
    python run_tests.py --session 2    # session 2 only (prompts for key if needed)
    python run_tests.py --session 3    # session 3 only (prompts for key if needed)
    python run_tests.py --no-api       # skip all tests requiring an API key
"""

import argparse
import getpass
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Run FHIR hackathon notebook tests")
    parser.add_argument(
        "--session", type=int, choices=[1, 2, 3],
        help="Run tests for a single session only"
    )
    parser.add_argument(
        "--no-api", action="store_true",
        help="Skip tests that require ANTHROPIC_API_KEY"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=True,
        help="Verbose output (default: on)"
    )
    args = parser.parse_args()

    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(test_dir, "test_all_notebooks.py")

    # Determine if we need an API key
    needs_api = not args.no_api and (args.session is None or args.session in (2, 3))

    if needs_api and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Sessions 2 and 3 require an Anthropic API key.")
        print("Options:")
        print("  1. Enter your API key now (used in-memory only, not stored)")
        print("  2. Skip API tests (run Session 1 only)")
        print()
        choice = input("Enter API key (or press Enter to skip API tests): ").strip()
        if choice:
            os.environ["ANTHROPIC_API_KEY"] = choice
            print("API key set for this session.\n")
        else:
            print("Skipping API-dependent tests.\n")
            args.no_api = True

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest", test_file]

    if args.verbose:
        cmd.append("-v")

    if args.session:
        cmd.append(f"-k=TestSession{args.session}")
    elif args.no_api:
        cmd.append('-k=not requires_api_key')

    # Show what we're running
    session_label = f"Session {args.session}" if args.session else "All sessions"
    api_label = "(no API tests)" if args.no_api else "(with API tests)"
    print(f"Running: {session_label} {api_label}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 70)

    result = subprocess.run(cmd, cwd=test_dir)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
