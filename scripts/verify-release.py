"""Verify downloaded ZIP hashes, all payloads and isolated package installation."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from pet_format import ROOT


def checksums(text):
    entries = {}
    for line in text.splitlines():
        digest, name = line.split('  ', 1)
        path = PurePosixPath(name)
        if (not re.fullmatch(r'[a-f0-9]{64}', digest) or path.is_absolute()
                or '..' in path.parts or '\\' in name or ':' in name or name in entries):
            raise ValueError(f'Unsafe checksum entry: {name}')
        entries[name] = digest
    if not entries:
        raise ValueError('Empty checksum file')
    return entries


def verify(directory):
    archives = checksums((directory / 'SHA256SUMS.txt').read_text(encoding='utf-8'))
    results = []
    for name, digest in archives.items():
        if '/' in name or not name.endswith('.zip'):
            raise ValueError('Expected a ZIP filename')
        path = directory / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Archive hash mismatch: {name}')
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(set(names)) != len(names) or archive.testzip() is not None:
                raise ValueError('Duplicate entries or corrupt archive')
            payloads = checksums(archive.read('SHA256SUMS.txt').decode('utf-8'))
            if set(names) != set(payloads) | {'SHA256SUMS.txt'}:
                raise ValueError('Unlisted ZIP payload')
            for member, expected in payloads.items():
                if hashlib.sha256(archive.read(member)).hexdigest() != expected:
                    raise ValueError(f'Payload mismatch: {member}')
            manifests = [n for n in names if re.fullmatch(r'pets/[a-z0-9-]+/pet/pet.json', n)]
            if len(manifests) != 1:
                raise ValueError('Each ZIP must contain exactly one pet')
            manifest = json.loads(archive.read(manifests[0]).decode('utf-8-sig'))
            pet_id = PurePosixPath(manifests[0]).parts[1]
            if manifest['id'] != pet_id or manifest['spritesheetPath'] != 'spritesheet.webp':
                raise ValueError('Invalid manifest ownership')
            other_pets = {PurePosixPath(n).parts[1] for n in names if n.startswith('pets/')}
            if other_pets != {pet_id}:
                raise ValueError('Package contains unrelated pets')
            installed = False
            if os.name == 'nt':
                # Temp directories are created and removed only inside this workspace output.
                output = (ROOT / 'output').resolve()
                output.mkdir(exist_ok=True)
                with tempfile.TemporaryDirectory(prefix='package-test-', dir=output) as temporary:
                    target = Path(temporary).resolve()
                    if target.parent != output:
                        raise ValueError('Unsafe test directory')
                    archive.extractall(target / 'package')
                    package = target / 'package'
                    command = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                               '-File', str(package / 'scripts/install.ps1')]
                    # Python launched from PowerShell 7 inherits its incompatible module paths.
                    # Let Windows PowerShell initialize its own defaults in this child only.
                    child_env = {k: v for k, v in os.environ.items() if k.lower() != 'psmodulepath'}
                    subprocess.run([*command, '-List'], check=True, env=child_env)
                    subprocess.run([*command, '-PetId', pet_id, '-CodexHome', str(target / 'home')], check=True, env=child_env)
                    for file in ('pet.json', 'spritesheet.webp'):
                        original = package / f'pets/{pet_id}/pet/{file}'
                        copy = target / f'home/pets/{pet_id}/{file}'
                        if copy.read_bytes() != original.read_bytes():
                            raise ValueError(f'Installed package differs: {file}')
                    installed = True
        results.append({'archive': name, 'sha256': digest, 'payloads': len(payloads),
                        'petId': pet_id, 'isolatedWindowsInstallVerified': installed})
    print(json.dumps(results, indent=2))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    verify(parser.parse_args().directory.resolve())
