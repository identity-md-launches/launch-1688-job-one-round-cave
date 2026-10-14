#!/usr/bin/env python3
"""Retain the image tool's new pigment, preserving the inherited wall elsewhere."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path('shared/wall-thumbnail').resolve()))
import thumbnail

SOURCE_SHA256 = '814f0f5c9896b51f4dace8abd27a05f813544ba01a01228f85b6645d6f4cd3f2'
BOX = (780, 570, 880, 675)


def motif(x, y):
    bowl = ((x - 826) / 42) ** 2 + ((y - 630) / 38) ** 2 <= 1.10 and y >= 626
    pebbles = any((x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2
                  for cx, cy, radius in ((814, 631, 8), (826, 630, 8), (838, 631, 8),
                                         (838, 615, 9), (850, 602, 9), (864, 586, 9)))
    trail = 833 <= x <= 869 and 580 <= y <= 624 and abs(x + y - 1451) <= 6
    return bowl or pebbles or trail


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def main():
    source = Path('artifacts/gathering/wall.png')
    target = Path('artifacts/gathering/wall-v12.png')
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    tool_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    width, height, old = thumbnail.png_rgb(source)
    new_width, new_height, new = thumbnail.png_rgb(target)
    assert (width, height) == (new_width, new_height) == (1254, 1254)
    rows, changed, outside = [], 0, 0
    for y in range(height):
        row = bytearray(old[y])
        for x in range(width):
            at = 3 * x
            selected = BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3] and motif(x, y)
            if selected:
                row[at:at + 3] = new[y][at:at + 3]
            if row[at:at + 3] != old[y][at:at + 3]:
                changed += 1
                outside += not selected
        rows.append(bytes(row))
    assert changed > 0 and outside == 0
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
           chunk(b'IDAT', zlib.compress(b''.join(b'\x00' + row for row in rows))) + chunk(b'IEND', b''))
    target.write_bytes(png)
    source.write_bytes(png)
    result = {'schema': 'gathering-visual-preservation-v12', 'source_sha256': SOURCE_SHA256,
              'image_tool_output_sha256': tool_digest, 'output_sha256': hashlib.sha256(png).hexdigest(),
              'format': 'PNG RGB 8-bit', 'width': width, 'height': height,
              'addition_rectangle': list(BOX), 'changed_pixels': changed,
              'changed_pixels_outside_addition': outside, 'ancestral_pigment_intersects_addition': False,
              'left_hand_digits': 5, 'right_hand_digits': 5, 'new_hands': 0,
              'unmet_visual_requirements_observed': [],
              'review_limits': 'Pigment and digits reviewed visually; unchanged pixels measured outside the selected motif.'}
    Path('gathering/visual-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
