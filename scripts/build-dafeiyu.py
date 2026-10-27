"""Extract and register generated alpha components, preserving per-animation scale."""
import json, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from sprite_components import components
ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / 'pets/dafeiyu'
REF = PET / 'source/references'
STATES = [('idle', 6), ('running-right', 8), ('running-left', 8), ('waving', 4), ('jumping', 5), ('failed', 8), ('waiting', 6), ('running', 6), ('review', 6), ('look-row-9', 8), ('look-row-10', 8)]

def extract(name, count):
    selected = {'jumping': 'jumping-revised', 'look-row-9': 'look-row-9-upward-fix', 'look-row-10': 'look-row-10-revised'}.get(name, name)
    im = Image.open(REF / f'{selected}.png').convert('RGBA')
    groups = components(im)
    n = 8 if name == 'jumping' else count
    assert len(groups) == n, (name, 'unexpected component count', len(groups), n)
    groups.sort(key=lambda c: (c['box'][1] + c['box'][3]) / 2)
    groups = sorted(groups[:4], key=lambda c: c['box'][0]) + sorted(groups[4:], key=lambda c: c['box'][0]) if n > 4 else sorted(groups, key=lambda c: c['box'][0])
    result = []
    for i, c in enumerate(groups):
        x0, y0, x1, y1 = c['box']
        assert 0 < x0 < x1 < im.width and 0 < y0 < y1 < im.height, (name, i, 'source edge clipping', c['box'])
        support = Image.new('L', im.size)
        d = ImageDraw.Draw(support)
        for y, a, b in c['runs']:
            d.line((a, y, b - 1, y), fill=255)
        support = support.filter(ImageFilter.MaxFilter(5))
        rgba = np.asarray(im).copy()
        rgba[np.asarray(support) == 0] = 0
        rgba[rgba[:, :, 3] <= 4] = 0
        tile = Image.fromarray(rgba).crop((max(0, x0 - 2), max(0, y0 - 2), min(im.width, x1 + 2), min(im.height, y1 + 2)))
        ys, xs = np.where(np.asarray(tile.getchannel('A')) > 32)
        bottom = int(ys.max() + 1)
        anchor = float(np.median(xs[ys > bottom - (ys.max() - ys.min()) * 0.08]))
        result.append({'image': tile, 'anchor': anchor, 'height': bottom, 'sourceBottom': y1 - (im.height // 2 if n > 4 and i >= 4 else 0), 'box': list(c['box'])})
    if name == 'jumping':
        result = [result[i] for i in (1, 2, 3, 5, 6)]
    return (result, selected)

def register(frames, jumping=False):
    left = max((f['anchor'] for f in frames))
    right = max((f['image'].width - f['anchor'] for f in frames))
    scale = min(182 / (left + right), (167 if jumping else 190) / max((f['height'] for f in frames)))
    center = (192 + scale * (left - right)) / 2
    floor = max((f['sourceBottom'] for f in frames))
    result = []
    positions = []
    for f in frames:
        im = f['image']
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
        lift = round((floor - f['sourceBottom']) * scale) if jumping else 0
        x = round(center - f['anchor'] * scale)
        y = round(201 - f['height'] * scale - lift)
        assert x >= 0 and y >= 0 and (x + im.width <= 192) and (y + im.height <= 208), ('frame overflow', x, y, im.size)
        tile = Image.new('RGBA', (192, 208))
        tile.alpha_composite(im, (x, y))
        a = np.asarray(tile).copy()
        a[a[:, :, 3] == 0] = 0
        result.append(Image.fromarray(a))
        positions.append({'x': x, 'y': y, 'jumpLift': lift})
    return (result, {'scale': scale, 'bodyAnchorX': center, 'feetBaseline': 201, 'positions': positions})

def save_gif(frames, path, duration):
    out = []
    for f in frames:
        p = f.convert('RGB').quantize(colors=255)
        p.paste(255, mask=f.getchannel('A').point(lambda a: 255 if a < 128 else 0))
        out.append(p)
    out[0].save(path, save_all=True, append_images=out[1:], duration=duration, loop=0, transparency=255, disposal=2, optimize=False)

def main():
    atlas = Image.new('RGBA', (1536, 2288))
    extracted = {}
    sources = {}
    evidence = {}
    for name, count in STATES:
        extracted[name], sources[name] = extract(name, count)
    looks, lt = register(extracted['look-row-9'] + extracted['look-row-10'])
    for row, (name, count) in enumerate(STATES):
        if row >= 9:
            frames = looks[:8] if row == 9 else looks[8:]
            transform = lt
        else:
            frames, transform = register(extracted[name], jumping=name == 'jumping')
        for col, f in enumerate(frames):
            atlas.paste(f, (col * 192, row * 208))
        evidence[name] = {'source': f'source/references/{sources[name]}.png', 'sourceSha256': hashlib.sha256((REF / f'{sources[name]}.png').read_bytes()).hexdigest(), 'sourceBoxes': [f['box'] for f in extracted[name]], 'registration': transform}
        if row < 9:
            save_gif(frames, PET / 'previews' / f'{name}.gif', 140 if name.startswith('running-') else 180)
    neutral = atlas.crop((0, 0, 192, 208))
    atlas.paste(neutral, (1152, 0))
    neutral.save(PET / 'assets/dafeiyu-base-transparent.png')
    evidence['neutralPose'] = {'source': 'idle frame 0', 'reason': 'identical open-eye resting pose avoids a scale jump'}
    atlas.save(PET / 'pet/spritesheet.webp', lossless=True, exact=True, method=6)
    save_gif(looks, PET / 'previews/look-directions.gif', 180)
    sheet = Image.new('RGB', (1536, 2596), '#f1f5fa')
    d = ImageDraw.Draw(sheet)
    for row, (name, _) in enumerate(STATES):
        d.text((8, row * 236 + 4), name, fill='#243552')
        for col in range(8):
            tile = atlas.crop((col * 192, row * 208, (col + 1) * 192, (row + 1) * 208))
            sheet.paste(tile, (col * 192, row * 236 + 24), tile)
    sheet.save(PET / 'assets/contact-sheet-extended.png')
    sheet = Image.new('RGB', (1536, 472), '#eef4fa')
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(looks):
        x, y = (i % 8 * 192, i // 8 * 236)
        d.text((x + 8, y + 4), f'{i * 22.5:g} deg', fill='#243552')
        sheet.paste(f, (x, y + 24), f)
    sheet.save(PET / 'assets/look-directions.png')
    evidence.update(spritesheetSha256=hashlib.sha256((PET / 'pet/spritesheet.webp').read_bytes()).hexdigest(), tool='OpenAI built-in image_gen', postprocessing='connected alpha support; shared scale per animation; shoe registration; no redraw or mirror')
    (PET / 'source/qa/generation-provenance.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Built', evidence['spritesheetSha256'])
if __name__ == '__main__':
    main()
