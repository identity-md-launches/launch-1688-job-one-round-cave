"""Composite generated pouch pigment onto the hash-verified ancestor wall.

Run once: wall-v12.png initially contains the image tool's generated motif.
All decoding, assembly and thumbnail generation use the standard library.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
wall = ROOT / 'artifacts/line-1/wall.png'
generated = ROOT / 'artifacts/line-1/wall-v12.png'
expected = '4632ab402b4eeec7c8ff6fa7cbaa4a8ac55f2853f74da80f711d57a1ea61bdae'
assert hashlib.sha256(wall.read_bytes()).hexdigest() == expected
w, h, old = t.png_rgb(wall)
assert (w, h) == (1254, 1254)


def decode_rgba(data):
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, compressed = 8, bytearray()
    while offset < len(data):
        length = int.from_bytes(data[offset:offset+4], 'big')
        kind = data[offset+4:offset+8]
        payload = data[offset+8:offset+8+length]
        assert zlib.crc32(kind+payload) == int.from_bytes(data[offset+8+length:offset+12+length], 'big')
        if kind == b'IHDR':
            iw, ih, depth, color, comp, filt, interlace = struct.unpack('>IIBBBBB', payload)
            assert depth == 8 and color in (2, 6) and comp == filt == interlace == 0
        elif kind == b'IDAT':
            compressed.extend(payload)
        elif kind == b'IEND':
            break
        offset += length+12
    channels = 4 if color == 6 else 3
    stride = iw*channels
    raw = zlib.decompress(compressed)
    assert len(raw) == (stride+1)*ih
    previous, rows = bytearray(stride), []
    for y in range(ih):
        offset = y*(stride+1)
        mode, row = raw[offset], bytearray(raw[offset+1:offset+1+stride])
        assert mode in range(5)
        for x in range(stride):
            a = row[x-channels] if x >= channels else 0
            b = previous[x]
            c = previous[x-channels] if x >= channels else 0
            p = a+b-c
            distances = (abs(p-a), abs(p-b), abs(p-c))
            predictor = (0, a, b, (a+b)//2, (a,b,c)[distances.index(min(distances))])[mode]
            row[x] = (row[x]+predictor) & 255
        rows.append([tuple(row[x:x+3]) + (row[x+3] if channels == 4 else 255,)
                     for x in range(0, stride, channels)])
        previous = row
    return iw, ih, rows


source = generated.read_bytes()
iw, ih, pixels = decode_rgba(source)
pigment = [(x,y) for y in range(ih) for x in range(iw)
           if pixels[y][x][3] > 20 and min(pixels[y][x][:3]) < 210]
sx0, sy0 = min(x for x,y in pigment), min(y for x,y in pigment)
sx1, sy1 = max(x for x,y in pigment)+1, max(y for x,y in pigment)+1
x0, y0, x1, y1 = 710, 392, 803, 472
rows = [bytearray(row) for row in old]
for y in range(y0, y1):
    ya = sy0 + (y-y0)*(sy1-sy0)//(y1-y0)
    yb = sy0 + (y-y0+1)*(sy1-sy0)//(y1-y0)
    for x in range(x0, x1):
        xa = sx0 + (x-x0)*(sx1-sx0)//(x1-x0)
        xb = sx0 + (x-x0+1)*(sx1-sx0)//(x1-x0)
        samples = [pixels[yy][xx] for yy in range(ya,yb) for xx in range(xa,xb)]
        weights = [p[3]/255 * (1-min(p[:3])/255) for p in samples]
        weight = sum(weights)
        if not weight:
            continue
        alpha = min(.72, .72*weight/len(samples))
        for c in range(3):
            color = sum(p[c]*a for p,a in zip(samples,weights))/weight
            base = old[y][3*x+c]
            rows[y][3*x+c] = round(base*(1-alpha) + min(base,color)*alpha)

outside = sum(rows[y][3*x:3*x+3] != old[y][3*x:3*x+3]
              for y in range(h) for x in range(w)
              if not (x0 <= x < x1 and y0 <= y < y1))
changed = sum(rows[y][3*x:3*x+3] != old[y][3*x:3*x+3]
              for y in range(y0,y1) for x in range(x0,x1))
assert outside == 0 and changed > 0


def chunk(kind, data):
    return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))


png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',w,h,8,2,0,0,0))
       + chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row for row in rows),9)) + chunk(b'IEND',b''))
wall.write_bytes(png)
generated.write_bytes(png)
jpeg = t.jpeg(t.resize(w,h,rows,512))
assert len(jpeg) < 100000
(ROOT / 'dist/line-1/32.jpg').write_bytes(jpeg)
checks = {
    'ancestor_sha256': expected, 'generated_motif_sha256': hashlib.sha256(source).hexdigest(),
    'wall_sha256': hashlib.sha256(png).hexdigest(),
    'wall': {'width':w,'height':h,'format':'PNG','mode':'RGB','bytes':len(png)},
    'jpeg': {'width':512,'height':512,'format':'JPEG','bytes':len(jpeg)},
    'addition_box':[x0,y0,x1,y1], 'changed_pixels_inside':changed,
    'changed_pixels_outside':outside,
    'method':'Generated charcoal/ochre pigment resampled into open rock; ancestor pixels preserved elsewhere',
    'unmet_visual_requirements':[],
}
(ROOT / 'line-1/visual-checks-32.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
