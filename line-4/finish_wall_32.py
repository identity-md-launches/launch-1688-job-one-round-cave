#!/usr/bin/env python3
"""Retain only the image editor's new pigment patch and create required outputs.

One-shot artifact production: wall.png must still be the verified ancestor;
wall-v12.png must hold the full tool edit. Uses the existing stdlib thumbnail
codec, adds no painted shapes, and preserves original pixels outside the patch.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import zlib

ROOT = Path.cwd().resolve()
WALL = ROOT / 'artifacts/line-4/wall.png'
EDIT = ROOT / 'artifacts/line-4/wall-v12.png'
ANCESTOR = '50a0685d56f48b05b4a2b202ebcc92a90c038cb6cd6f05e0e20f86f81dc41ee3'
# Cut away the upper-right corner to keep the ancestor's nearby bowl untouched.
POLYGON = [(335, 925), (416, 925), (468, 962), (468, 1048), (335, 1048)]


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def png(width, height, rows):
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b''.join(b'\0' + bytes(row) for row in rows), 9))
            + chunk(b'IEND', b''))


def weight(x, y):
    distances = []
    for (ax, ay), (bx, by) in zip(POLYGON, POLYGON[1:] + POLYGON[:1]):
        distances.append(((bx-ax)*(y-ay)-(by-ay)*(x-ax)) / math.hypot(bx-ax, by-ay))
    return max(0.0, min(1.0, min(distances) / 7.0))


def main():
    original = WALL.read_bytes()
    assert hashlib.sha256(original).hexdigest() == ANCESTOR, 'requires original ancestor as wall.png'
    spec = importlib.util.spec_from_file_location('thumbnail32', ROOT / 'line-4/tools/call-rehearsal/thumbnail.py')
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    w, h, old = codec.png_rgb(WALL)
    ew, eh, edited = codec.png_rgb(EDIT)
    assert (w, h) == (ew, eh) == (1254, 1254)
    rows = [bytearray(row) for row in old]
    changed_inside = changed_outside = 0
    for y in range(h):
        for x in range(w):
            alpha = weight(x, y)
            if alpha:
                for channel in range(3):
                    i = x*3 + channel
                    rows[y][i] = round(old[y][i] * (1-alpha) + edited[y][i] * alpha)
            if rows[y][x*3:x*3+3] != old[y][x*3:x*3+3]:
                if alpha:
                    changed_inside += 1
                else:
                    changed_outside += 1
    assert changed_inside > 0 and changed_outside == 0
    finished = png(w, h, rows)
    WALL.write_bytes(finished)
    EDIT.write_bytes(finished)
    thumb = codec.jpeg(codec.resize(w, h, rows, 512))
    assert len(thumb) < 100000
    jpeg_path = ROOT / 'dist/line-4/32.jpg'
    with jpeg_path.open('xb') as f:
        f.write(thumb)
    result = {'ancestor_sha256': ANCESTOR, 'wall_sha256': hashlib.sha256(finished).hexdigest(),
              'wall': {'format': 'PNG', 'width': w, 'height': h, 'mode': 'RGB', 'bytes': len(finished)},
              'thumbnail': {'format': 'JPEG', 'width': 512, 'height': 512, 'bytes': len(thumb),
                            'sha256': hashlib.sha256(thumb).hexdigest()},
              'addition_polygon': POLYGON, 'feather_pixels': 7,
              'changed_pixels_inside': changed_inside, 'changed_pixels_outside': changed_outside,
              'named_wall_identical': WALL.read_bytes() == EDIT.read_bytes(),
              'unmet_visual_requirements': ['Inherited small three-pronged trail marks cannot be certified as five-digit handprints; preserved unchanged.']}
    (ROOT / 'line-4/delivery-checks-32.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
