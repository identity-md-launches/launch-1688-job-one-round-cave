"""Assemble only the image editor's addition and preserve ancestor pixels elsewhere.

One-time artifact production helper, not a Code Routes dependency.
Inputs: recovered record-31 wall.png and image-tool output wall-v12.png.
Outputs: identical final wall PNGs, numbered JPEG, record and preservation report.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)
ancestor_path = ROOT / 'artifacts/line-3/wall.png'
generated_path = ROOT / 'artifacts/line-3/wall-v12.png'
ancestor_bytes = ancestor_path.read_bytes()
generated_bytes = generated_path.read_bytes()
assert hashlib.sha256(ancestor_bytes).hexdigest() == 'fb03d5101c2d4a196268a027421a3982381f95fdc6545f7f83f0638b8a0590b6'
width, height, ancestor = thumbnail.png_rgb(ancestor_path)
gw, gh, generated = thumbnail.png_rgb(generated_path)
assert (width, height) == (gw, gh) == (1254, 1254)
x, y, w, h = 580, 35, 255, 135
rows = [bytearray(row) for row in ancestor]
for py in range(y, y+h):
    for px in range(x, x+w):
        feather = min(8, px-x, x+w-1-px, py-y, y+h-1-py)
        for channel in range(3):
            index = 3*px+channel
            rows[py][index] = (ancestor[py][index]*(8-feather)
                               + generated[py][index]*feather + 4)//8

def chunk(kind, payload):
    return (struct.pack('>I', len(payload)) + kind + payload
            + struct.pack('>I', zlib.crc32(kind+payload)))

png = (b'\x89PNG\r\n\x1a\n'
       + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(b''.join(b'\0'+row for row in rows), 9))
       + chunk(b'IEND', b''))
assert png.startswith(b'\x89PNG\r\n\x1a\n')
generated_path.write_bytes(png)
fw, fh, final = thumbnail.png_rgb(generated_path)
assert (fw, fh) == (width, height)
inside = outside = 0
for py in range(height):
    for px in range(width):
        if final[py][3*px:3*px+3] != ancestor[py][3*px:3*px+3]:
            if x <= px < x+w and y <= py < y+h:
                inside += 1
            else:
                outside += 1
assert inside > 0 and outside == 0
ancestor_path.write_bytes(png)
jpeg = thumbnail.jpeg(thumbnail.resize(width, height, final, 512))
assert len(jpeg) < 100000
with (ROOT / 'dist/line-3/32.jpg').open('xb') as stream:
    stream.write(jpeg)
report = {
    'ancestor_sha256': hashlib.sha256(ancestor_bytes).hexdigest(),
    'generated_before_assembly_sha256': hashlib.sha256(generated_bytes).hexdigest(),
    'wall_sha256': hashlib.sha256(png).hexdigest(), 'format': 'PNG',
    'dimensions': [width, height], 'mode': 'RGB', 'wall_bytes': len(png),
    'addition_boxes_xyxy': [[x, y, x+w, y+h]],
    'changed_pixels_inside_boxes': inside, 'changed_pixels_outside_boxes': outside,
    'thumbnail': {'path': 'dist/line-3/32.jpg', 'format': 'JPEG', 'dimensions': [512, 512],
                  'bytes': len(jpeg), 'sha256': hashlib.sha256(jpeg).hexdigest()},
    'manual_review_pending': True,
}
(ROOT / 'line-3/visual-checks-32.json').write_text(json.dumps(report, indent=2) + '\n')
record = {'name': 'The Branching Trail',
          'image': 'https://api.imd.fun/artifacts/' + report['wall_sha256'],
          'attributes': [
              {'trait_type': 'Cave', 'value': 'Moss'},
              {'trait_type': 'Wall', 'value': 'Line 3'},
              {'trait_type': 'Number', 'value': 32},
              {'trait_type': 'Left behind', 'value': 'Code Routes'},
              {'trait_type': 'Meaning', 'value': 'Pepe follows a forked trail and marks where a path ends.'},
              {'trait_type': 'One thing', 'value': 'Ethereum executable code identity'}]}
with (ROOT / 'dist/line-3/32.json').open('x') as stream:
    stream.write(json.dumps(record, indent=2) + '\n')
print(json.dumps(report, indent=2))
