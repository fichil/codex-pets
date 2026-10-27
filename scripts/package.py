"""Build reproducible, self-contained single-pet ZIPs with licenses and checksums."""
import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

from pet_format import ROOT, pet_directory, pet_ids
from validate import validate


def build(pet_id, version, output):
    pet = pet_directory(pet_id)
    result = validate(pet_id)
    if not result['ok']:
        raise ValueError(f'{pet_id}: {result["errors"]}')
    # Include all provenance and upstream notices, so the asset license travels with it.
    files = [p for p in pet.rglob('*') if p.is_file()]
    files += [ROOT / p for p in ('LICENSE', 'LICENSE-ASSETS', 'NOTICE.md',
              'scripts/install.ps1', 'scripts/uninstall.ps1', 'scripts/common.ps1',
              'docs/安装与使用.md')]
    archive_path = output / f'{pet_id}-{version}.zip'
    if archive_path.exists():
        raise FileExistsError(f'Refusing to overwrite {archive_path}')
    entries = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files}
    entries['INSTALL.txt'] = (
        f'Codex Pets / {pet_id} / {version}\n\n'
        f'From this extracted folder, run:\n'
        f'powershell -ExecutionPolicy Bypass -File .\\scripts\\install.ps1 -PetId {pet_id}\n\n'
        f'Or copy pets/{pet_id}/pet/ into <CodexHome>/pets/{pet_id}/.\n'
        f'Read pets/{pet_id}/README.md and all included licenses before redistributing.\n'
        f'Source: https://github.com/fichil/codex-pets\n'
    ).encode('utf-8')
    entries['SHA256SUMS.txt'] = ''.join(
        f'{hashlib.sha256(data).hexdigest()}  {name}\n'
        for name, data in sorted(entries.items())
    ).encode('utf-8')
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 27, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC validation failed')
        for name, data in entries.items():
            if archive.read(name) != data:
                raise ValueError(f'ZIP readback mismatch: {name}')
    return archive_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--pet-id')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/releases')
    args = parser.parse_args()
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[a-z0-9.]+)?', args.version):
        parser.error('Use a version such as v2.0.0')
    ids = [args.pet_id] if args.pet_id else pet_ids()
    # Preflight every package before creating any release artifact.
    for pet_id in ids:
        result = validate(pet_id)
        if not result['ok']:
            raise ValueError(f'{pet_id}: {result["errors"]}')
    output = args.output.resolve()
    if (output / 'SHA256SUMS.txt').exists() or any((output / f'{i}-{args.version}.zip').exists() for i in ids):
        raise FileExistsError('Release output exists; choose a new output directory')
    output.mkdir(parents=True, exist_ok=True)
    archives = [build(pet_id, args.version, output) for pet_id in ids]
    checksums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in archives)
    (output / 'SHA256SUMS.txt').write_text(checksums, encoding='utf-8')
    print(checksums, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
