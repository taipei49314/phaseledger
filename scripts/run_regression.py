#!/usr/bin/env python3
"""Local regression harness for phaseledger (no network, no other repos).

Runs the full unittest suite via the same discover entry operators use.
Exit 0 only if all tests pass.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    print("regression:", " ".join(cmd))
    print("root:", root)
    proc = subprocess.run(cmd, cwd=str(root), env=env)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
