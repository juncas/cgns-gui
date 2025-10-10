"""Utility script to produce distributable artifacts for CGNS GUI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    dist_dir = project_root / "dist"

    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    cmd = [sys.executable, "-m", "build", "--sdist", "--wheel"]
    result = subprocess.run(cmd, cwd=project_root, check=False)
    if result.returncode != 0:
        return result.returncode

    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    if not wheels or not sdists:
        print("Expected both wheel and sdist artifacts, but some are missing.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
