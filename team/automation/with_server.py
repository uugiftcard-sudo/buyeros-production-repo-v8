#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from run import redact


def wait_for_url(url: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 500:
                    return True
        except Exception:
            time.sleep(1)
    return False


def terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a command while a temporary local server is alive")
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--ready-url", required=True)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("child", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    child = args.child[1:] if args.child[:1] == ["--"] else args.child
    if not child:
        parser.error("missing child command after --")

    cwd = Path(args.cwd)
    server = subprocess.Popen(
        ["/bin/zsh", "-lc", args.command],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    # Readiness failures are much easier to debug if we surface
    # the server's stdout/stderr (often includes a stack trace).
    server_output: list[str] = []
    assert server.stdout is not None
    try:
        deadline = time.monotonic() + args.timeout
        ready = False
        while time.monotonic() < deadline:
            # Drain any available server output for later diagnostics.
            try:
                if server.stdout is not None:
                    line = server.stdout.readline()
                    if line:
                        server_output.append(line)
            except Exception:
                pass

            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen(args.ready_url, timeout=3) as response:
                    if 200 <= response.status < 500:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)

        if not ready:
            print(f"server did not become ready: {args.ready_url}")
            if server.poll() is not None:
                print(f"server exited with code {server.returncode}")
            if server_output:
                print("--- server output (tail) ---")
                tail = "".join(server_output[-200:])
                print(redact(tail).rstrip())
            return 1

        child_proc = subprocess.run(
            child,
            cwd=Path(__file__).parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        print(redact(child_proc.stdout or "").rstrip())
        return child_proc.returncode
    finally:
        terminate_process(server)


if __name__ == "__main__":
    sys.exit(main())
