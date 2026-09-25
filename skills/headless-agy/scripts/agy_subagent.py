#!/usr/bin/env python3
"""
Headless agy Subagent Dispatcher & Verification Wrapper

Executes tasks through the Antigravity CLI (agy) non-interactively,
audits git blast-radius, scans for careless edits (stubs, TODOs, scope violations),
and runs independent verification commands before reporting to the orchestrator.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


CARELESSNESS_PATTERNS = [
    (re.compile(r"^\+[ \t]*(#|//)?[ \t]*(TODO|FIXME)\b", re.MULTILINE | re.IGNORECASE), "Unfinished TODO/FIXME marker"),
    (re.compile(r"^\+[ \t]*pass[ \t]*(#.*)?$", re.MULTILINE), "Stubbed 'pass' statement"),
    (re.compile(r"^\+[ \t]*throw new Error\(['\"](Not implemented|TODO)['\"]\)", re.MULTILINE | re.IGNORECASE), "Stubbed exception"),
    (re.compile(r"^\+[ \t]*(except\s+\w+:\s*pass|catch\s*\([^)]*\)\s*\{\s*\})", re.MULTILINE), "Silent exception suppression"),
    (re.compile(r"^\+[ \t]*(@ts-ignore|as any|# type: ignore)", re.MULTILINE), "Type system escape"),
    (re.compile(r"^\+[ \t]*\.(skip|only)\(", re.MULTILINE), "Skipped or solo test run"),
]


def run_cmd(cmd: List[str], cwd: Optional[str] = None, timeout: Optional[int] = None) -> Tuple[int, str, str]:
    """Execute a subprocess command returning exit_code, stdout, stderr."""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def get_git_status(cwd: str) -> List[Tuple[str, str]]:
    """Return list of (status_code, filepath) from git status --porcelain."""
    code, out, _ = run_cmd(["git", "status", "--porcelain"], cwd=cwd)
    if code != 0:
        return []
    results = []
    for line in out.splitlines():
        if len(line) >= 4:
            status = line[:2].strip()
            path = line[3:].strip()
            results.append((status, path))
    return results


def get_git_diff(cwd: str) -> str:
    """Return unstaged and staged git diff."""
    code, out, _ = run_cmd(["git", "diff", "HEAD"], cwd=cwd)
    if code != 0:
        _, out, _ = run_cmd(["git", "diff"], cwd=cwd)
    return out


def audit_diff_for_carelessness(diff_text: str) -> List[str]:
    """Scan diff additions for common careless patterns."""
    findings = []
    for pattern, description in CARELESSNESS_PATTERNS:
        matches = pattern.findall(diff_text)
        if matches:
            findings.append(f"{description} (detected {len(matches)} occurrence(s))")
    return findings


def build_contract_prompt(base_prompt: str, target_files: Optional[List[str]]) -> str:
    """Wrap raw prompt with explicit boundary constraints if target files specified."""
    if not target_files:
        return base_prompt

    targets_str = "\n".join(f"- {f}" for f in target_files)
    return (
        f"{base_prompt}\n\n"
        "STRICT BOUNDARIES:\n"
        f"You are authorized to modify ONLY these target files:\n{targets_str}\n"
        "Do NOT modify or reformat any other files in the repository.\n"
        "Do NOT leave stubbed functions, pass statements, or TODO comments.\n"
        "Implement complete, working logic."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run agy headlessly as a subagent with automated git auditing and verification."
    )
    parser.add_argument("prompt", help="Prompt describing the task to delegate.")
    parser.add_argument("--model", default="gemini-3.8-flash-high", help="LLM model (default: gemini-3.8-flash-high).")
    parser.add_argument("--effort", choices=["low", "medium", "high"], default=None, help="Reasoning effort.")
    parser.add_argument("--mode", choices=["accept-edits", "plan"], default="accept-edits", help="agy execution mode.")
    parser.add_argument("--timeout", default="300s", help="Turn timeout limit (default: 300s).")
    parser.add_argument("--conversation", default=None, help="Resume previous conversation ID.")
    parser.add_argument("--target-files", nargs="*", default=None, help="Allowed files to modify.")
    parser.add_argument("--verify-cmd", default=None, help="Verification command to execute after agy finishes.")
    parser.add_argument("--auto-revert-on-fail", action="store_true", help="Revert git working tree if verification fails.")
    parser.add_argument("--json-out", action="store_true", help="Output summary report as JSON.")

    args = parser.parse_args()

    if not shutil.which("agy"):
        sys.stderr.write("Error: 'agy' CLI executable not found in PATH.\n")
        return 1

    cwd = os.getcwd()
    status_before = get_git_status(cwd)

    contract_prompt = build_contract_prompt(args.prompt, args.target_files)

    cmd = [
        "agy",
        "-p", contract_prompt,
        "--output-format", "json",
        "--dangerously-skip-permissions",
        "--print-timeout", args.timeout,
        "--mode", args.mode,
    ]
    if args.model:
        cmd.extend(["--model", args.model])
    if args.effort:
        cmd.extend(["--effort", args.effort])
    if args.conversation:
        cmd.extend(["--conversation", args.conversation])

    # Convert timeout to seconds for python subprocess timeout guard
    timeout_secs = 360
    if args.timeout.endswith("s"):
        timeout_secs = int(args.timeout[:-1]) + 30
    elif args.timeout.endswith("m"):
        timeout_secs = int(args.timeout[:-1]) * 60 + 30

    agy_code, agy_stdout, agy_stderr = run_cmd(cmd, cwd=cwd, timeout=timeout_secs)

    parsed_agy: Dict[str, Any] = {}
    if agy_code == 0 and agy_stdout.strip():
        try:
            parsed_agy = json.loads(agy_stdout)
        except json.JSONDecodeError:
            parsed_agy = {"raw_output": agy_stdout}
    else:
        parsed_agy = {"error": agy_stderr, "raw_stdout": agy_stdout, "exit_code": agy_code}

    status_after = get_git_status(cwd)
    diff_text = get_git_diff(cwd)

    # Calculate files changed
    files_before = {p for _, p in status_before}
    changed_files = [p for _, p in status_after if p not in files_before or any(p == p_orig and s != s_orig for s, p in status_after for s_orig, p_orig in status_before)]
    if not changed_files:
        changed_files = [p for _, p in status_after]

    # Check for scope violations
    scope_violations = []
    if args.target_files:
        target_set = set(args.target_files)
        for f in changed_files:
            if f not in target_set:
                scope_violations.append(f)

    # Audit diff for carelessness
    carelessness_warnings = audit_diff_for_carelessness(diff_text)
    if scope_violations:
        carelessness_warnings.append(f"Scope violation: Modified unauthorized files {scope_violations}")

    # Run independent verification command if specified
    verify_code = 0
    verify_stdout = ""
    verify_stderr = ""
    if args.verify_cmd:
        verify_code, verify_stdout, verify_stderr = run_cmd(args.verify_cmd.split(), cwd=cwd)

    conv_id = parsed_agy.get("conversation_id", "")
    transcript_path = ""
    if conv_id:
        transcript_path = str(Path.home() / ".gemini" / "antigravity-cli" / "brain" / conv_id / ".system_generated" / "logs" / "transcript.jsonl")

    is_success = (
        agy_code == 0
        and parsed_agy.get("status") == "SUCCESS"
        and verify_code == 0
        and len(scope_violations) == 0
    )

    if not is_success and args.auto_revert_on_fail:
        # Revert changes
        run_cmd(["git", "restore", "."], cwd=cwd)
        run_cmd(["git", "clean", "-fd"], cwd=cwd)
        reverted = True
    else:
        reverted = False

    report = {
        "status": "PASS" if is_success else "FAIL",
        "conversation_id": conv_id,
        "transcript_path": transcript_path if os.path.exists(transcript_path) else None,
        "duration_seconds": parsed_agy.get("duration_seconds"),
        "agy_status": parsed_agy.get("status"),
        "files_changed": changed_files,
        "carelessness_warnings": carelessness_warnings,
        "verify_command": args.verify_cmd,
        "verify_passed": (verify_code == 0) if args.verify_cmd else None,
        "verify_output": (verify_stdout + verify_stderr).strip() if args.verify_cmd else None,
        "reverted": reverted,
        "agy_summary": parsed_agy.get("response", "").strip(),
    }

    if args.json_out:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print(f"HEADLESS AGY SUBAGENT REPORT: {report['status']}")
        print("=" * 60)
        print(f"Conversation ID : {conv_id}")
        if transcript_path:
            print(f"Transcript Log  : {transcript_path}")
        print(f"Files Changed   : {', '.join(changed_files) if changed_files else 'None'}")
        if carelessness_warnings:
            print("\n[!] CARELESSNESS WARNINGS:")
            for w in carelessness_warnings:
                print(f"  - {w}")
        if args.verify_cmd:
            print(f"\nVerification Command: {args.verify_cmd}")
            print(f"Verification Result : {'PASSED' if verify_code == 0 else 'FAILED'}")
            if verify_code != 0:
                print(f"Verification Error  :\n{verify_stderr or verify_stdout}")
        print("\n--- Subagent Narrative Response ---")
        print(report["agy_summary"] or "No response.")
        print("=" * 60)

    return 0 if is_success else 1


if __name__ == "__main__":
    sys.exit(main())
