"""Check installable packages and their hash-bound evidence; never rewrite them."""
import argparse
import hashlib
import json
import sys

import numpy as np
from PIL import Image

from pet_format import ROOT, SIZE, STATES, frame, pet_directory, pet_ids, used_cells


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(pet_id, root=ROOT, require_visual=True):
    pet = pet_directory(pet_id, root)
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    for path in pet.rglob('*'):
        check(not path.is_symlink() and not path.is_junction(), f'Linked path: {path.relative_to(pet)}')
    manifest = json.loads((pet / 'pet/pet.json').read_text(encoding='utf-8-sig'))
    check(manifest.get('id') == pet_id, 'Manifest ID does not match folder')
    check(manifest.get('spriteVersionNumber') == 2, 'Expected spriteVersionNumber=2')
    check(manifest.get('spritesheetPath') == 'spritesheet.webp', 'Invalid sprite path')
    check(isinstance(manifest.get('displayName'), str) and bool(manifest['displayName'].strip()), 'Missing display name')
    image_path = pet / 'pet/spritesheet.webp'
    with Image.open(image_path) as source:
        check(source.format == 'WEBP', 'Expected WebP')
        check(source.size == SIZE, f'Expected size {SIZE}, got {source.size}')
        check(source.mode == 'RGBA', 'Expected RGBA transparency')
        image = source.convert('RGBA')
    pixels = np.asarray(image)
    check(bool((pixels[:, :, 3] == 0).any()), 'No fully transparent pixels')
    check(not bool((pixels[pixels[:, :, 3] == 0, :3] != 0).any()), 'Hidden RGB in transparent pixels')
    used = used_cells()
    occupied = 0
    if image.size == SIZE:
        for row in range(11):
            for col in range(8):
                tile = np.asarray(frame(image, row, col))[:, :, 3]
                if (row, col) in used:
                    check(int((tile > 32).sum()) > 500, f'Empty or incomplete used cell {row},{col}')
                    occupied += 1
                    check(not bool((tile[[0, -1], :] > 32).any() or (tile[:, [0, -1]] > 32).any()),
                          f'Artwork touches cell edge {row},{col}')
                else:
                    check(not bool(tile.any()), f'Unused cell {row},{col} is not transparent')
    digest = sha256(image_path)
    provenance = json.loads((pet / 'source/qa/generation-provenance.json').read_text(encoding='utf-8-sig'))
    check(provenance.get('spritesheetSha256', '').lower() == digest, 'Stale provenance hash')
    for entry in provenance.values():
        if isinstance(entry, dict) and 'sourceSha256' in entry:
            source = pet / entry['source']
            check(source.is_file() and sha256(source) == entry['sourceSha256'].lower(), 'Source hash mismatch')
    if require_visual:
        visual = json.loads((pet / 'source/qa/visual-qa.json').read_text(encoding='utf-8-sig'))
        check(visual.get('reviewed_spritesheet_sha256', '').lower() == digest, 'Stale visual QA hash')
        check(visual.get('visual_qa') == 'pass', 'Visual QA not passed')
    for name, count in (*STATES, ('look-directions', 16)):
        with Image.open(pet / 'previews' / f'{name}.gif') as gif:
            check(gif.size == (192, 208), f'Wrong preview size: {name}')
            check(gif.n_frames == count, f'Wrong preview frame count: {name}')
    for relative in ('README.md', 'LICENSE', 'previews/index.html', 'assets/contact-sheet-extended.png', 'assets/look-directions.png'):
        check((pet / relative).is_file(), f'Missing {relative}')
    if pet_id == 'dafeiyu':
        chain = json.loads((pet / 'source/qa/generation-chain.json').read_text(encoding='utf-8'))
        for job in chain['jobs']:
            source = pet / job['source']
            check(source.is_file() and sha256(source) == job['sourceSha256'], 'Generation-chain source mismatch')
            check((pet / job['prompt']).is_file(), 'Missing generation prompt')
            for reference in job['references']:
                check((pet / reference).is_file(), 'Missing generation input')
        references = json.loads((pet / 'source/references/SOURCES.json').read_text(encoding='utf-8'))
        for reference in references['references']:
            check(sha256(pet / 'source/references' / reference['file']) == reference['sha256'], 'Upstream reference mismatch')
        for relative in ('NOTICE.md', 'source/licenses/YunYueSama-ATTRIBUTION-1.0.txt',
                         'source/licenses/YunYueSama-ASSET_LICENSE.md', 'source/licenses/xiaoweigen-NOTICE.md'):
            check((pet / relative).is_file(), f'Missing attribution: {relative}')
    return {'petId': pet_id, 'ok': not errors, 'spritesheetSha256': digest,
            'usedCells': occupied, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pet-id')
    parser.add_argument('--structural-only', action='store_true', help='Skip visual verdict while authoring; not for releases')
    args = parser.parse_args()
    results = []
    for pet_id in [args.pet_id] if args.pet_id else pet_ids():
        try:
            results.append(validate(pet_id, require_visual=not args.structural_only))
        except (OSError, ValueError, KeyError) as exc:
            results.append({'petId': pet_id, 'ok': False, 'errors': [str(exc)]})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results and all(r['ok'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
