"""The repository's Codex V2 sprite layout."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CELL = (192, 208)
SIZE = (1536, 2288)
STATES = (
    ('idle', 6), ('running-right', 8), ('running-left', 8),
    ('waving', 4), ('jumping', 5), ('failed', 8),
    ('waiting', 6), ('running', 6), ('review', 6),
)
NEUTRAL = (0, 6)


def pet_directory(pet_id, root=ROOT):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', pet_id):
        raise ValueError(f'Invalid pet ID: {pet_id!r}')
    path = root / 'pets' / pet_id
    if path.is_symlink() or path.resolve().parent != (root / 'pets').resolve():
        raise ValueError('Pet path escapes the pets directory')
    if not path.is_dir():
        raise ValueError(f'Unknown pet: {pet_id}')
    return path


def pet_ids(root=ROOT):
    return sorted(p.name for p in (root / 'pets').iterdir() if p.is_dir())


def frame(image, row, col):
    w, h = CELL
    return image.crop((col*w, row*h, (col+1)*w, (row+1)*h))


def used_cells():
    cells = {(row, col) for row, (_, count) in enumerate(STATES) for col in range(count)}
    cells.add(NEUTRAL)
    cells.update((row, col) for row in (9, 10) for col in range(8))
    return cells
