#!/usr/bin/env python3
"""Reproduce the public KITTI demo adaptation without accessing private lab data."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import urllib.request

SOURCE_REF = 'https://raw.githubusercontent.com/open-mmlab/mmdetection3d/fe25f7a51d36e3702f961e198894580d83c4387b/demo/data/kitti/000008.bin'
SOURCE_SHA256 = '3b9de6cc966534900f6a1bdc93b21772e47a334eb2ef18082021956520d902d1'
Z_OFFSET = 1.73


def convert(raw):
    """Preserve xyz ordering, translate z, and write a zero RGB placeholder."""
    if not raw or len(raw) % 16:
        raise ValueError('KITTI demo requires nonempty 16-byte float32 records')
    count = len(raw) // 16
    body = bytearray()
    for x, y, z, reflectance in struct.iter_unpack('<ffff', raw):
        if not all(math.isfinite(v) for v in (x, y, z, reflectance)):
            raise ValueError('KITTI values must be finite')
        body.extend(struct.pack('<fffI', x, y, z + Z_OFFSET, 0))
    header = (f'# .PCD v0.7 - KITTI 000008 adaptation, CC BY-NC-SA 3.0\nVERSION 0.7\n'
              f'FIELDS x y z rgb\nSIZE 4 4 4 4\nTYPE F F F U\nCOUNT 1 1 1 1\n'
              f'WIDTH {count}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS {count}\nDATA binary\n').encode('ascii')
    return header + body, count


def prepare(raw, out):
    """Check the pinned source identity before writing two new dataset files."""
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source SHA256 differs from pinned KITTI demo; no files written')
    pcd, count = convert(raw)
    targets = [out / 'demo.pcd', out / 'provenance.json']
    if any(p.exists() or p.is_symlink() for p in targets):
        raise ValueError('Refusing to overwrite demo.pcd or provenance.json')
    out.mkdir(parents=True, exist_ok=True)
    provenance = {'source_ref': SOURCE_REF, 'source_sha256': SOURCE_SHA256,
                  'source_dataset': 'KITTI Vision Benchmark Suite / MMDetection3D demo 000008',
                  'source_bytes': len(raw), 'points': count,
                  'license': 'CC-BY-NC-SA-3.0',
                  'license_url': 'https://creativecommons.org/licenses/by-nc-sa/3.0/',
                  'copyright_url': 'https://www.cvlibs.net/datasets/kitti/',
                  'changes': {'x_y': 'unchanged', 'z_offset_m': Z_OFFSET,
                              'reflectance': 'discarded; constant channels in existing model adapter',
                              'rgb': 'uint32 zero placeholder'},
                  'pcd_sha256': hashlib.sha256(pcd).hexdigest()}
    targets[0].write_bytes(pcd)
    targets[1].write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(f'{count} points; PCD sha256={provenance["pcd_sha256"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Pinned original .bin; omit to download fixed public URL')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.source:
        raw = args.source.read_bytes()
    else:
        with urllib.request.urlopen(SOURCE_REF, timeout=30) as response:
            raw = response.read(1024 * 1024)
    try:
        prepare(raw, args.out)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
