#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.json"
STATE_START = "<!-- AUTOMATION_STATUS_START -->"
STATE_END = "<!-- AUTOMATION_STATUS_END -->"
MAX_OUTPUT_CHARS = 6000
REDACTION_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"sbp_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE),
]


@dataclasses.dataclass
class StepResult:
    name: str
    ok: bool
    command: str
    skipped: bool = False
    returncode: int | None = None
    output: str = ""


@dataclasses.dataclass
class RepoResult:
    key: str
    label: str
    mode: str
    ok: bool
    deploy_allowed: bool
    dirty: bool
    secret_hits: list[str]
    blockers: list[str]
    steps: list[StepResult]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def redact(text: str) -> str:
    redacted = text
    for pattern in REDACTION_PATTERNS:
        redacted = pattern.sub(lambda match: (match.group(1) if match.groups() else "") + "[REDACTED]", redacted)
    return redacted


def render_cmd(cmd: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def run_command(step: dict[str, Any], dry_run: bool) -> StepResult:
    cmd = [str(part) for part in step["cmd"]]
    command = render_cmd(cmd)
    if dry_run:
        return StepResult(name=step["name"], ok=True, command=command, skipped=True, output="dry-run")

    try:
        proc = subprocess.run(
            ["/bin/zsh", "-lc", command],
            cwd=step.get("cwd"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except FileNotFoundError as exc:
        return StepResult(
            name=step["name"],
            ok=False,
            command=command,
            returncode=127,
            output=redact(str(exc)),
        )
    output = redact(proc.stdout or "")
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[-MAX_OUTPUT_CHARS:]
    return StepResult(
        name=step["name"],
        ok=proc.returncode == 0,
        command=command,
        returncode=proc.returncode,
        output=output.strip(),
    )


def git_output(repo_path: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git_status(repo_path: str) -> str:
    proc = git_output(repo_path, ["status", "--short"])
    return proc.stdout.strip()


def git_pr_hygiene(repo_path: str) -> StepResult:
    lines: list[str] = []
    ok = True

    def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
        return git_output(repo_path, args)

    branch = run_git(["branch", "--show-current"])
    if branch.returncode == 0 and branch.stdout.strip():
        lines.append(f"branch: {branch.stdout.strip()}")
    else:
        ok = False
        lines.append("branch: unavailable")

    upstream = run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if upstream.returncode == 0 and upstream.stdout.strip():
        upstream_name = upstream.stdout.strip()
        lines.append(f"upstream: {upstream_name}")
        ahead_behind = run_git(["rev-list", "--left-right", "--count", f"{upstream_name}...HEAD"])
        if ahead_behind.returncode == 0 and ahead_behind.stdout.strip():
            behind, ahead = ahead_behind.stdout.strip().split()[:2]
            lines.append(f"ahead: {ahead}; behind: {behind}")
    else:
        lines.append("upstream: none")

    if shutil.which("gh"):
        pr = subprocess.run(
            ["gh", "pr", "status", "--json", "currentBranch"],
            cwd=repo_path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if pr.returncode == 0 and pr.stdout.strip():
            lines.append("github pr status: available")
        else:
            lines.append("github pr status: unavailable")
    else:
        lines.append("github pr status: gh not installed")

    return StepResult(
        name="PR hygiene",
        ok=ok,
        command="git branch/upstream/ahead-behind + gh pr status",
        output="\n".join(lines),
    )


def secret_scan(repo_path: str, patterns: list[str]) -> list[str]:
    combined = ""
    for args in (["diff", "--no-ext-diff"], ["diff", "--cached", "--no-ext-diff"]):
        proc = git_output(repo_path, args)
        combined += "\n" + (proc.stdout or "")
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, combined, flags=re.IGNORECASE):
            hits.append(pattern)
    return sorted(set(hits))


def repo_selection(config: dict[str, Any], selected: str) -> list[str]:
    if selected == "all":
        return list(config["repos"].keys())
    if selected not in config["repos"]:
        raise SystemExit(f"Unknown repo: {selected}")
    return [selected]


def run_repo(config: dict[str, Any], repo_key: str, mode: str, dry_run: bool) -> RepoResult:
    repo = config["repos"][repo_key]
    path = repo["path"]
    label = repo["label"]
    status = git_status(path)
    dirty = bool(status)
    secret_hits = secret_scan(path, config["secret_patterns"])
    blockers: list[str] = []
    steps: list[StepResult] = []

    if dirty:
        blockers.append("dirty working tree blocks deploy")
    if secret_hits:
        blockers.append("secret-like pattern found in git diff")

    if mode in {"check", "deploy"}:
        steps.append(git_pr_hygiene(path))
        for step in repo.get("check_commands", []):
            steps.append(run_command(step, dry_run=dry_run))

    check_ok = all(step.ok for step in steps)
    deploy_allowed = not dirty and not secret_hits and check_ok

    if mode == "deploy":
        deploy_commands = repo.get("deploy_commands", [])
        if not deploy_commands:
            blockers.append(f"no deploy target configured: {repo.get('deploy_policy', 'unknown')}")
            deploy_allowed = False
        if deploy_allowed:
            deployed = False
            for step in deploy_commands:
                result = run_command(step, dry_run=dry_run)
                steps.append(result)
                deployed = deployed or (not result.skipped)
                if not result.ok:
                    blockers.append(f"deploy failed at step: {step['name']}")
                    if deployed and repo.get("rollback_commands"):
                        for rollback in repo["rollback_commands"]:
                            steps.append(run_command(rollback, dry_run=dry_run))
                    break
        else:
            steps.append(
                StepResult(
                    name="deploy gate",
                    ok=False,
                    command="deploy",
                    skipped=True,
                    output="blocked by safety gate",
                )
            )

    ok = not blockers and all(step.ok for step in steps)
    return RepoResult(
        key=repo_key,
        label=label,
        mode=mode,
        ok=ok,
        deploy_allowed=deploy_allowed,
        dirty=dirty,
        secret_hits=secret_hits,
        blockers=blockers,
        steps=steps,
    )


def render_report(results: list[RepoResult], dry_run: bool) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Automation Report",
        "",
        f"- Generated: {now}",
        f"- Dry run: {'yes' if dry_run else 'no'}",
        "",
        "| Repo | Status | Dirty | Secret diff | Deploy gate | Blockers |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for result in results:
        blockers = "; ".join(result.blockers) if result.blockers else "-"
        lines.append(
            f"| {result.label} | {'PASS' if result.ok else 'FAIL'} | "
            f"{'yes' if result.dirty else 'no'} | "
            f"{'yes' if result.secret_hits else 'no'} | "
            f"{'open' if result.deploy_allowed else 'blocked'} | {blockers} |"
        )
    lines.append("")
    for result in results:
        lines.extend([f"## {result.label}", ""])
        for step in result.steps:
            suffix = " (skipped)" if step.skipped else ""
            status = "PASS" if step.ok else "FAIL"
            lines.append(f"- {status}{suffix} `{step.name}`: `{step.command}`")
            if step.output and not step.skipped:
                lines.append("")
                lines.append("```text")
                lines.append(step.output)
                lines.append("```")
                lines.append("")
        if result.secret_hits:
            lines.append(f"- Secret scan hits: {', '.join(result.secret_hits)}")
        if result.blockers:
            lines.append(f"- Blockers: {'; '.join(result.blockers)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def update_state_file(state_file: Path, report: str) -> None:
    summary = report.split("\n## ", 1)[0].rstrip() + "\n"
    block = f"{STATE_START}\n{summary}{STATE_END}"
    current = state_file.read_text(encoding="utf-8") if state_file.exists() else ""
    if STATE_START in current and STATE_END in current:
        start = current.index(STATE_START)
        end = current.index(STATE_END) + len(STATE_END)
        updated = current[:start].rstrip() + "\n\n" + block + "\n" + current[end:].lstrip()
    else:
        updated = current.rstrip() + "\n\n" + block + "\n"
    state_file.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Three-repo automation controller")
    parser.add_argument("mode", choices=["check", "deploy", "report"])
    parser.add_argument("--repo", default="all", choices=["all", "buyeros", "xau", "cloth"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict-exit", action="store_true", help="Return non-zero on blockers even during dry-run")
    parser.add_argument("--write-state", action="store_true", help="Update team/state.md with report summary")
    parser.add_argument("--no-report-file", action="store_true", help="Do not write latest-report.md")
    args = parser.parse_args()

    config = load_config()
    mode = "check" if args.mode == "report" else args.mode
    results = [run_repo(config, key, mode, args.dry_run) for key in repo_selection(config, args.repo)]
    report = render_report(results, dry_run=args.dry_run)
    print(report)

    if not args.no_report_file and not args.dry_run:
        Path(config["report_file"]).write_text(report, encoding="utf-8")
    if args.write_state and not args.dry_run:
        update_state_file(Path(config["state_file"]), report)

    if args.dry_run and not args.strict_exit:
        return 0
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
