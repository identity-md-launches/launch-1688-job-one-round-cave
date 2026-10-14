#!/usr/bin/env python3
"""Paint one generated RGBA insert from base64 stdin; save only finished walls."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import finish_wall_26 as imageops

ROOT = Path(__file__).resolve().parents[1]
WALL = ROOT / 'artifacts/line-2/wall.png'
SOURCE_SHA256 = '388078c51619aa2812efb46d47cc30ea6b3cbf05dd0dc6f328e66944314e4778'
PLACEMENT = (615, 1065, 225, 75)


def main():
    source = WALL.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('expected the exact record-31 wall')
    width, height, channels, original = imageops.decode(source)
    assert (width, height, channels) == (1254, 1254, 3)
    chunks = []
    for line in sys.stdin.buffer:
        if line.strip() == b'END':
            break
        chunks.append(line.strip())
    else:
        raise ValueError('missing END marker')
    mw, mh, mc, markrows = imageops.decode(base64.b64decode(b''.join(chunks), validate=True))
    if mc != 4:
        raise ValueError('expected transparent RGBA pigment')
    cleaned = []
    for row in markrows:
        row = bytearray(row)
        for offset in range(3, len(row), 4):
            if row[offset] < 160:
                row[offset] = 0
        cleaned.append(bytes(row))
    imageops.PLACE_X, imageops.PLACE_Y, imageops.PLACE_W, imageops.PLACE_H = PLACEMENT
    rows, bounds = imageops.composite(original, (mw, mh, mc, cleaned))
    x, y, w, h = PLACEMENT
    for rownum, (old, new) in enumerate(zip(original, rows)):
        if not y <= rownum < y + h:
            assert old == new
        else:
            assert old[:x * 3] == new[:x * 3]
            assert old[(x + w) * 3:] == new[(x + w) * 3:]
    output = imageops.encode(width, height, rows)
    WALL.write_bytes(output)
    (WALL.parent / 'wall-v12.png').write_bytes(output)
    spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
    thumbnail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thumbnail)
    jpeg = thumbnail.jpeg(thumbnail.resize(width, height, rows, 512))
    assert len(jpeg) < 100000
    with (ROOT / 'dist/line-2/32.jpg').open('xb') as stream:
        stream.write(jpeg)
    digest = hashlib.sha256(output).hexdigest()
    meaning = 'A pale stone pinches the cord reaching a seeded pouch.'
    record = {
        'name': 'The Narrowed Cord',
        'image': 'https://api.imd.fun/artifacts/' + digest,
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Moss'},
            {'trait_type': 'Wall', 'value': 'Line 2'},
            {'trait_type': 'Number', 'value': 32},
            {'trait_type': 'Left behind', 'value': 'Allowance Caps'},
            {'trait_type': 'Meaning', 'value': meaning},
            {'trait_type': 'One thing', 'value': 'ERC-20 spending-permission audits'},
        ],
    }
    with (ROOT / 'dist/line-2/32.json').open('x') as stream:
        stream.write(json.dumps(record, indent=2) + '\n')
    checks = {
        'source_sha256': SOURCE_SHA256, 'output_sha256': digest,
        'format': 'PNG', 'dimensions': [width, height], 'placement': PLACEMENT,
        'changed_pixels': sum(old[i:i+3] != new[i:i+3] for old, new in zip(original, rows)
                              for i in range(0, len(old), 3)),
        'outside_placement_unchanged': True, 'insert_alpha_bounds': bounds,
        'preview': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
        'unmet_visual_requirements': [], 'visual_review': 'Pending complete PNG/JPEG inspection',
    }
    (ROOT / 'line-2/visual-checks-32.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
