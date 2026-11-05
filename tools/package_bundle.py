"""Archive l'exécutable construit et écrit son empreinte SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "android" / "VERSION").read_text(encoding="utf-8").strip()

LISEZ_MOI = """Blink2Temp {version} — {artifact}

Exécutable autonome : Python et toutes les dépendances sont inclus.
Aucune installation de Python n'est nécessaire.

Utilisation
-----------
  Tableau de bord web :
    {binary} --web --loop 60
    puis ouvrir http://localhost:8770
    Le bouton « Vérifier la mise à jour » y installe la dernière release
    GitHub (archive vérifiée par empreinte SHA-256, redémarrage automatique).

  Relevé unique :
    {binary} --once

  Aide complète :
    {binary} --help

Les données (config.json, temperatures.db, blink2temp.log) sont écrites dans
le dossier de données de l'utilisateur, jamais dans le dossier temporaire du
programme :
  Windows : %APPDATA%\\Blink2Temp
  Linux   : ~/.local/share/Blink2Temp
  macOS   : ~/Library/Application Support/Blink2Temp

La connexion Blink se fait dans la console au premier relevé (2FA comprise).
Sous macOS, si le système bloque l'exécutable téléchargé, ouvrir le menu
contextuel puis « Ouvrir », ou retirer la quarantaine :
  xattr -d com.apple.quarantine blink2temp
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args()

    binary = ROOT / "dist" / ("blink2temp.exe" if os.name == "nt" else "blink2temp")
    if not binary.is_file():
        raise SystemExit(f"Exécutable absent : {binary}")

    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    binary_name = "blink2temp.exe" if os.name == "nt" else "blink2temp"
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary) / "blink2temp"
        stage.mkdir()
        shutil.copy2(binary, stage / binary_name)
        (stage / "LISEZ-MOI.txt").write_text(
            LISEZ_MOI.format(version=VERSION, artifact=args.artifact, binary=binary_name),
            encoding="utf-8",
            newline="\n",
        )

        if os.name == "nt":
            archive = output / f"blink2temp-{VERSION}-{args.artifact}.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for path in sorted(stage.iterdir()):
                    bundle.write(path, arcname=path.name)
        else:
            archive = output / f"blink2temp-{VERSION}-{args.artifact}.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(stage, arcname="blink2temp")

    digest = sha256(archive)
    (output / f"SHA256SUMS-{args.artifact}.txt").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n"
    )
    print(f"{archive.name}  {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
