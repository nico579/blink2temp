"""Vérifie que le tag vX.Y.Z, VERSION et le build Gradle sont d'accord."""
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def check():
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    assert re.fullmatch(r'\d+\.\d+\.\d+', version), 'VERSION must contain a semantic version'
    gradle = (ROOT / 'app/build.gradle.kts').read_text(encoding='utf-8')
    assert 'versionName = rootProject.file("VERSION").readText().trim()' in gradle
    assert 'applicationId = "com.nico.blink2temp"' in gradle
    ref = os.environ.get('GITHUB_REF', '')
    if ref.startswith('refs/tags/'):
        assert ref.removeprefix('refs/tags/') == 'v' + version, 'Tag and VERSION differ'
    print(json.dumps({'version': version, 'android': version}))
    return version


if __name__ == '__main__':
    check()
