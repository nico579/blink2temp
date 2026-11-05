"""Construit l'exécutable autonome Blink2Temp avec PyInstaller.

Le binaire inclut Python, blinkpy, aiohttp et certifi. Il est ensuite lancé
avec --help : un import manquant ou un démarrage cassé fait échouer la CI.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "pyinstaller"
DIST = ROOT / "dist"


def main() -> int:
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.rmtree(DIST, ignore_errors=True)

    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile",
        "--name", "blink2temp",
        "--distpath", str(DIST),
        "--workpath", str(BUILD / "work"),
        "--specpath", str(BUILD),
        "--collect-all", "blinkpy",
        "--collect-all", "certifi",
        "--add-data", f"{ROOT / 'VERSION'}{os.pathsep}.",
        str(ROOT / "blink2temp.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)

    binary = DIST / ("blink2temp.exe" if os.name == "nt" else "blink2temp")
    if not binary.is_file():
        raise SystemExit(f"Exécutable absent après PyInstaller : {binary}")

    verification = subprocess.run(
        [str(binary), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if verification.returncode != 0 or "usage" not in verification.stdout.lower():
        raise SystemExit(
            "L'exécutable ne démarre pas correctement.\n"
            f"code={verification.returncode}\n"
            f"sortie={verification.stdout}\n"
            f"erreur={verification.stderr}"
        )

    print(f"Exécutable vérifié : {binary} ({binary.stat().st_size} octets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
