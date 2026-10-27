"""Connected alpha components for reproducible sprite extraction (no redraw)."""
import numpy as np


def components(image, threshold=32):
    mask = np.asarray(image.getchannel('A')) > threshold
    parent, runs, previous = [], [], []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for y, row in enumerate(mask):
        edges = np.diff(np.pad(row.astype(np.int8), (1, 1)))
        current = []
        for x0, x1 in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
            index = len(parent)
            parent.append(index)
            runs.append((y, int(x0), int(x1), index))
            for p0, p1, pi in previous:
                if p0 > x1:
                    break
                if p1 >= x0:
                    parent[find(pi)] = find(index)
            current.append((x0, x1, index))
        previous = current
    groups = {}
    for y, x0, x1, i in runs:
        groups.setdefault(find(i), []).append((y, x0, x1))
    result = []
    for group in groups.values():
        area = sum(x1 - x0 for _, x0, x1 in group)
        if area < 100:
            continue
        box = (min(x0 for _, x0, _ in group), group[0][0], max(x1 for _, _, x1 in group), group[-1][0] + 1)
        result.append({'area': area, 'box': box, 'runs': group})
    return sorted(result, key=lambda c: c['area'], reverse=True)
