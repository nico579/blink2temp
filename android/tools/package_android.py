"""Vérifie et empaquette l'APK construit par GitHub Actions."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from check_versions import check, ROOT

APPLICATION_ID = 'com.nico.blink2temp'
CERTIFICATE = '2e1c7200c865dd127c22d2233feba41d5b9e9d1a81fbd2030a106e6d32c8e7ec'
MINIMUM_TESTS = 20


def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Release APKs must be built by GitHub Actions'
    metadata_file = ROOT / 'app/build/outputs/apk/release/output-metadata.json'
    version = json.loads(metadata_file.read_text())['elements'][0]['versionName']
    assert version == check()

    results = [
        ET.parse(path).getroot()
        for path in (ROOT / 'app/build/test-results/testDebugUnitTest').glob('TEST-*.xml')
    ]
    counts = {
        key: sum(int(result.get(key, '0')) for result in results)
        for key in ('tests', 'failures', 'errors', 'skipped')
    }
    assert counts['tests'] >= MINIMUM_TESTS, counts
    assert counts['failures'] == counts['errors'] == 0, counts
    assert counts['skipped'] == 0, counts

    lint = ET.parse(ROOT / 'app/build/reports/lint-results-release.xml').getroot().findall('issue')
    assert not any(issue.get('severity') in ('Error', 'Fatal') for issue in lint), lint

    apk = ROOT / 'app/build/outputs/apk/release/app-release.apk'
    sdk = Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT'])
    tools = sdk / 'build-tools/34.0.0'
    aapt = tools / ('aapt.exe' if os.name == 'nt' else 'aapt')
    signer = tools / ('apksigner.bat' if os.name == 'nt' else 'apksigner')

    badging = subprocess.check_output([str(aapt), 'dump', 'badging', str(apk)], text=True)
    package = re.search(
        r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging
    )
    assert package and package[1] == APPLICATION_ID and package[3] == version, badging.splitlines()[0]

    signed = subprocess.check_output([str(signer), 'verify', '--print-certs', str(apk)], text=True)
    fingerprint = re.search(r'certificate SHA-256 digest: ([0-9a-f]+)', signed)
    assert fingerprint and fingerprint[1] == CERTIFICATE, 'Unexpected Android signing certificate'

    output = ROOT / 'release'
    output.mkdir(exist_ok=True)
    target = output / f'blink2temp-{version}.apk'
    shutil.copy2(apk, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    checksums = [f'{digest}  {target.name}']

    bundle = ROOT / 'app/build/outputs/bundle/release/app-release.aab'
    bundle_digest = None
    if bundle.is_file():
        bundle_target = output / f'blink2temp-{version}.aab'
        shutil.copy2(bundle, bundle_target)
        bundle_digest = hashlib.sha256(bundle_target.read_bytes()).hexdigest()
        checksums.append(f'{bundle_digest}  {bundle_target.name}')

    report = {
        'application': 'blink2temp',
        'version': version,
        'application_id': package[1],
        'versionCode': int(package[2]),
        'sha256': digest,
        'sha256_aab': bundle_digest,
        'certificat_signataire_sha256': fingerprint[1],
        'tests': counts,
        'lint_erreurs': 0,
        'lint_avertissements': len(lint),
        'validation': 'GitHub Actions, tests JVM, aucun téléphone physique',
        'commit': os.environ['GITHUB_SHA'],
        'run_url': (
            f"https://github.com/{os.environ['GITHUB_REPOSITORY']}"
            f"/actions/runs/{os.environ['GITHUB_RUN_ID']}"
        ),
    }
    (output / 'verification-android.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n'
    )
    (output / 'SHA256SUMS-android.txt').write_text(
        '\n'.join(checksums) + '\n', encoding='utf-8', newline='\n'
    )
    print(json.dumps({
        'apk': target.name,
        'aab': f'blink2temp-{version}.aab' if bundle_digest else None,
        'version': version,
        'application_id': package[1],
        'tests': counts,
        'sha256': digest,
        'sha256_aab': bundle_digest,
    }))


if __name__ == '__main__':
    main()
