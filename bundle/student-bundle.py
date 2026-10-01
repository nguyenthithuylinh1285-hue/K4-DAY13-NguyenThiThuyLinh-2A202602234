#!/usr/bin/env python3
"""Pack and run the public KITTI classroom PCD with an existing native offline Docker image."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import uuid

VERSION = 1
CHECKPOINT = '/opt/PointPillars/pretrained/epoch_160.pth'
REQUIRED = {'input/demo.pcd', 'practice/preannotate.py', 'practice/pipeline-qc-cases.py',
            'student-bundle.py', 'PRE-LABEL-REPORT.md', 'TEAMMATES.md', 'README-STUDENT.md',
            'DATA-LICENSE.txt', 'ATTRIBUTION.md', 'input/provenance.json',
            'POINTPILLARS-LICENSE.txt', 'image.tar.gz'}
RUNS = [('A', '0', '0.16'), ('B', '1.73', '0.16'), ('C', '1.73', '0.32')]


def sha256(path: Path) -> str:
    """Hash a file without loading its contents into memory.

    Args:
        path: File to hash.

    Returns:
        Lowercase SHA256 digest.
    """
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def empty_output(path: Path) -> None:
    """Require an absent or empty directory and reject symbolic links.

    Args:
        path: Requested output directory.

    Raises:
        ValueError: If writing could replace existing content.
    """
    if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()))):
        raise ValueError('--out must be absent or an empty directory; refusing overwrite')


def validate_pcd(path: Path) -> int:
    """Validate the binary layout consumed by preannotate.read_xyz.

    Args:
        path: Original PCD; its bytes and coordinates are never modified.

    Returns:
        Number of finite points.

    Raises:
        ValueError: If the file is not the supported nonempty binary PCD.
    """
    if not path.is_file() or path.suffix.lower() != '.pcd':
        raise ValueError('--pcd must be an existing .pcd file')
    with path.open('rb') as source:
        header = {}
        total = 0
        while True:
            line = source.readline(8193)
            total += len(line)
            if not line or len(line) > 8192 or total > 65536:
                raise ValueError('Missing or oversized PCD DATA binary header')
            if line == b'DATA binary\n':
                break
            parts = line.decode('ascii').split()
            if parts and not parts[0].startswith('#'):
                if parts[0] in header:
                    raise ValueError('Duplicate PCD header key')
                header[parts[0]] = parts[1:]
        if header.get('FIELDS') != ['x', 'y', 'z', 'rgb']:
            raise ValueError('PCD requires FIELDS x y z rgb')
        if header.get('SIZE') != ['4'] * 4 or header.get('TYPE') not in (['F', 'F', 'F', 'F'], ['F', 'F', 'F', 'U']):
            raise ValueError('PCD requires float32 xyz and float32 or uint32 rgb')
        if header.get('COUNT', ['1'] * 4) != ['1'] * 4:
            raise ValueError('PCD requires COUNT 1 1 1 1')
        count = int(header['POINTS'][0])
        if count <= 0 or path.stat().st_size - source.tell() != count * 16:
            raise ValueError('PCD POINTS must match the nonempty 16-byte binary body')
        if int(header['WIDTH'][0]) * int(header['HEIGHT'][0]) != count:
            raise ValueError('PCD WIDTH * HEIGHT must equal POINTS')
        for _ in range(count):
            if not all(math.isfinite(x) for x in struct.unpack('<fff', source.read(16)[:12])):
                raise ValueError('PCD coordinates must be finite')
    return count


def command(argv: list[str]) -> str:
    """Run an argv command and return stdout, preserving failure diagnostics.

    Args:
        argv: Executable and arguments; never interpreted by a shell.

    Returns:
        Captured stdout.
    """
    result = subprocess.run(argv, check=True, text=True, stdout=subprocess.PIPE)
    return result.stdout


def native_arch(value: str) -> str:
    """Normalize architecture names reported by Docker.

    Args:
        value: Docker server or image architecture.

    Returns:
        OCI architecture name.
    """
    return {'x86_64': 'amd64', 'aarch64': 'arm64'}.get(value, value)


def require_native(image: dict) -> dict:
    """Compare the image against the Linux Docker server, before loading.

    Args:
        image: Manifest or inspect metadata with os and architecture.

    Returns:
        Docker server metadata.

    Raises:
        ValueError: If the image needs emulation or a different OS.
    """
    server = json.loads(command(['docker', 'info', '--format', '{{json .}}']))
    if (server.get('OSType') != 'linux' or image['os'] != 'linux'
            or native_arch(server.get('Architecture', '')) != image['architecture']):
        raise ValueError('Bundle requires a native Linux Docker server matching image architecture')
    return {'os': server['OSType'], 'architecture': native_arch(server['Architecture'])}


def container(argv: list[str], capture: bool = False) -> str | None:
    """Run a named foreground container and clean up only that owned name.

    Args:
        argv: Arguments after Docker run's resource options.
        capture: Whether to capture stdout.

    Returns:
        Stdout when requested.
    """
    name = 'student-bundle-' + uuid.uuid4().hex
    args = ['docker', 'run', '--rm', '--name', name, '--network', 'none',
            '--cpus', '4', '--memory', '4g', *argv]
    try:
        if capture:
            return command(args)
        subprocess.run(args, check=True)
        return None
    finally:
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)


def save_image(image_id: str, destination: Path) -> None:
    """Stream docker save into gzip with bounded memory and checked exit.

    Args:
        image_id: Exact image identity to save.
        destination: New archive path.
    """
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(['docker', 'save', image_id], stdout=subprocess.PIPE, stderr=errors)
        try:
            with destination.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as archive:
                shutil.copyfileobj(process.stdout, archive, 1024 * 1024)
            code = process.wait()
            if code:
                errors.seek(0)
                raise ValueError('docker save failed: ' + errors.read().decode(errors='replace'))
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            process.stdout.close()


def write_json(path: Path, payload: dict) -> None:
    """Create a UTF-8 JSON file without overwriting existing content.

    Args:
        path: New file destination.
        payload: JSON-compatible data.
    """
    with path.open('x', encoding='utf-8') as output:
        json.dump(payload, output, indent=2, allow_nan=False)
        output.write('\n')


def pack(args: argparse.Namespace) -> None:
    """Create a public Student bundle after validating all input preconditions.

    Args:
        args: CLI arguments with PCD, image, provenance, and output.
    """
    repo = Path(__file__).resolve().parents[1]
    pcd, out = args.pcd.resolve(), args.out.absolute()
    empty_output(out)
    points = validate_pcd(pcd)
    sources = {name: repo / name for name in
               ('practice/preannotate.py', 'practice/pipeline-qc-cases.py',
                'PRE-LABEL-REPORT.md', 'TEAMMATES.md', 'data/demo.pcd',
                'data/ATTRIBUTION.md', 'data/LICENSE.txt', 'data/provenance.json')}
    instructions = repo / 'README-STUDENT.md'
    if not instructions.is_file():
        instructions = repo / 'bundle' / 'README-STUDENT.md'
    sources['README-STUDENT.md'] = instructions
    for source in sources.values():
        if not source.is_file() or source.is_symlink() or source.stat().st_size == 0:
            raise ValueError(f'Missing or unsafe public bundle source: {source}')
    # An override may name a copy of the checked-in public frame, never a new dataset.
    input_hash = sha256(pcd)
    if input_hash != sha256(sources['data/demo.pcd']):
        raise ValueError('--pcd must match the checked-in public KITTI demo')
    provenance = json.loads(sources['data/provenance.json'].read_text(encoding='utf-8'),
                            object_pairs_hook=unique_object)
    if (not isinstance(provenance, dict)
            or not isinstance(provenance.get('source_ref'), str)
            or not provenance['source_ref'].strip()
            or provenance.get('license') != 'CC-BY-NC-SA-3.0'):
        raise ValueError('Public data provenance requires source_ref and CC-BY-NC-SA-3.0 license')
    inspected = json.loads(command(['docker', 'image', 'inspect', args.image]))[0]
    image = {'id': inspected['Id'], 'os': inspected['Os'],
             'architecture': inspected['Architecture'], 'source_tag': args.image}
    require_native(image)
    license_text = container(['--entrypoint', 'cat', image['id'], '/opt/PointPillars/LICENSE'], capture=True)
    if not license_text.strip():
        raise ValueError('Missing PointPillars license in image')
    checkpoint_hash = container(['--entrypoint', 'python', image['id'], '-c',
                                'import hashlib; print(hashlib.sha256(open("' + CHECKPOINT
                                + '", "rb").read()).hexdigest())'], capture=True).strip()
    if not re.fullmatch('[0-9a-f]{64}', checkpoint_hash):
        raise ValueError('Invalid checkpoint fingerprint from image')
    revision = command(['git', '-C', str(repo), 'rev-parse', 'HEAD']).strip()
    dirty = bool(command(['git', '-C', str(repo), 'status', '--porcelain']).strip())
    input_hash = sha256(pcd)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'input').mkdir()
    (out / 'practice').mkdir()
    shutil.copyfile(pcd, out / 'input/demo.pcd')
    if sha256(out / 'input/demo.pcd') != input_hash:
        raise ValueError('Input changed during packing')
    for name in ('preannotate.py', 'pipeline-qc-cases.py'):
        shutil.copyfile(sources['practice/' + name], out / 'practice' / name)
    shutil.copyfile(sources['PRE-LABEL-REPORT.md'], out / 'PRE-LABEL-REPORT.md')
    shutil.copyfile(Path(__file__), out / 'student-bundle.py')
    shutil.copyfile(instructions, out / 'README-STUDENT.md')
    for source, destination in (('TEAMMATES.md', 'TEAMMATES.md'),
                                ('data/LICENSE.txt', 'DATA-LICENSE.txt'),
                                ('data/ATTRIBUTION.md', 'ATTRIBUTION.md'),
                                ('data/provenance.json', 'input/provenance.json')):
        shutil.copyfile(sources[source], out / destination)
    with (out / 'POINTPILLARS-LICENSE.txt').open('x', encoding='utf-8') as license_file:
        license_file.write(license_text)
    save_image(image['id'], out / 'image.tar.gz')
    files = {name: {'sha256': sha256(out / name), 'bytes': (out / name).stat().st_size}
             for name in sorted(REQUIRED)}
    write_json(out / 'manifest.json', {
        'schema_version': VERSION, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'image': image, 'checkpoint': {'path': CHECKPOINT, 'sha256': checkpoint_hash},
        'input': {'path': 'input/demo.pcd', 'original_filename': pcd.name, 'points': points,
                  'source_ref': provenance['source_ref'], 'license': provenance['license'],
                  'source_provenance': provenance},
        'code': {'repo_revision': revision, 'working_tree_dirty': dirty,
                 'preannotate_sha256': files['practice/preannotate.py']['sha256'],
                 'helper_sha256': files['practice/pipeline-qc-cases.py']['sha256']},
        'files': files})
    print(f'Packed {image["architecture"]} bundle: {out}')


def unique_object(pairs: list) -> dict:
    """Reject duplicate JSON keys.

    Args:
        pairs: Decoded object entries.

    Returns:
        Unambiguous dictionary.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate manifest key: {key}')
        result[key] = value
    return result


def verify_bundle(bundle: Path) -> dict:
    """Validate manifest schema, required files, safe paths, sizes, and hashes.

    Args:
        bundle: Bundle root directory.

    Returns:
        Verified manifest.

    Raises:
        ValueError: If metadata or any bundled file is invalid.
    """
    manifest_path = bundle / 'manifest.json'
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 1024 * 1024:
        raise ValueError('Unsafe or oversized manifest')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    if not isinstance(manifest, dict) or manifest.get('schema_version') != VERSION:
        raise ValueError('Unsupported manifest schema')
    image = manifest.get('image', {})
    if (not isinstance(image, dict) or image.get('os') != 'linux'
            or image.get('architecture') not in ('amd64', 'arm64')
            or not re.fullmatch(r'sha256:[0-9a-f]{64}', image.get('id', ''))):
        raise ValueError('Invalid image metadata')
    files = manifest.get('files')
    if not isinstance(files, dict) or not REQUIRED <= files.keys():
        raise ValueError('Manifest missing required files')
    for name, record in files.items():
        rel = PurePosixPath(name)
        if (not name or '\\' in name or ':' in name or rel.is_absolute()
                or '..' in rel.parts or str(rel) != name):
            raise ValueError(f'Unsafe manifest path: {name}')
        path = bundle / name
        if any((bundle / PurePosixPath(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts) + 1)):
            raise ValueError(f'Symbolic link in bundle: {name}')
        if not path.is_file() or not path.resolve().is_relative_to(bundle.resolve()):
            raise ValueError(f'Missing or unsafe bundle file: {name}')
        if (not isinstance(record, dict) or type(record.get('bytes')) is not int
                or not re.fullmatch('[0-9a-f]{64}', record.get('sha256', ''))
                or path.stat().st_size != record['bytes'] or sha256(path) != record['sha256']):
            raise ValueError(f'Checksum or size mismatch: {name}')
    inp, code, checkpoint = (manifest.get(key, {}) for key in ('input', 'code', 'checkpoint'))
    if (not isinstance(inp, dict) or inp.get('path') != 'input/demo.pcd'
            or not all(isinstance(inp.get(key), str) and inp[key].strip()
                       for key in ('source_ref', 'original_filename'))
            or type(inp.get('points')) is not int or inp['points'] <= 0):
        raise ValueError('Invalid input provenance')
    provenance = json.loads((bundle / 'input/provenance.json').read_text(encoding='utf-8'),
                            object_pairs_hook=unique_object)
    if (not isinstance(provenance, dict) or inp.get('source_provenance') != provenance
            or provenance.get('license') != 'CC-BY-NC-SA-3.0'
            or inp.get('license') != provenance.get('license')
            or inp.get('source_ref') != provenance.get('source_ref')):
        raise ValueError('Invalid public data provenance')
    if (not isinstance(code, dict) or not re.fullmatch('[0-9a-f]{40,64}', code.get('repo_revision', ''))
            or type(code.get('working_tree_dirty')) is not bool
            or code.get('preannotate_sha256') != files['practice/preannotate.py']['sha256']
            or code.get('helper_sha256') != files['practice/pipeline-qc-cases.py']['sha256']):
        raise ValueError('Invalid code provenance')
    if (not isinstance(checkpoint, dict) or checkpoint.get('path') != CHECKPOINT
            or not re.fullmatch('[0-9a-f]{64}', checkpoint.get('sha256', ''))):
        raise ValueError('Invalid checkpoint provenance')
    if validate_pcd(bundle / 'input/demo.pcd') != inp['points']:
        raise ValueError('PCD point count differs from manifest')
    return manifest


def mounts(bundle: Path, out: Path) -> list[str]:
    """Construct portable read-only input/code and writable output mounts.

    Args:
        bundle: Absolute bundle directory.
        out: Absolute output directory.

    Returns:
        Docker bind-mount argv entries.
    """
    result = []
    for source, target, readonly in ((bundle / 'input', '/data', True),
                                     (bundle / 'practice', '/practice', True), (out, '/out', False)):
        # Docker --mount uses CSV syntax; quoting handles commas in host paths.
        import io
        stream = io.StringIO()
        csv.writer(stream, lineterminator='').writerow(
            ['type=bind', f'source={source}', f'target={target}'] + (['readonly'] if readonly else []))
        result.extend(['--mount', stream.getvalue()])
    return result


def validate_outputs(out: Path, label: str, delta: str, voxel: str) -> dict:
    """Check the actual prediction identity and required artifacts for one run.

    Args:
        out: Results root.
        label: A, B, or C.
        delta: Expected sensor height.
        voxel: Expected pillar edge.

    Returns:
        Prediction identity and measured box count.
    """
    stem = f'demo-delta-{delta}-voxel-{voxel}'
    root = out / f'run-{label}'
    for name in (f'boxes-{stem}.json', f'side-{stem}.png', 'summary.csv'):
        if not (root / name).is_file() or (root / name).stat().st_size == 0:
            raise ValueError(f'Missing output: run-{label}/{name}')
    prediction = json.loads((root / f'boxes-{stem}.json').read_text())
    if (prediction.get('frame_id') != 'demo' or prediction.get('dataset') != 'KITTI'
            or prediction.get('delta') != float(delta) or prediction.get('voxel_size') != float(voxel)
            or not isinstance(prediction.get('boxes'), list)):
        raise ValueError(f'Unexpected prediction identity in run-{label}')
    return {'boxes': len(prediction['boxes']), 'prediction_sha256': sha256(root / f'boxes-{stem}.json')}


def run_bundle(args: argparse.Namespace) -> None:
    """Verify and load a bundle, then run A/B/C and controlled QC sequentially.

    Args:
        args: Bundle and new output directory CLI arguments.
    """
    bundle, out = args.bundle.resolve(), args.out.absolute()
    empty_output(out)
    manifest = verify_bundle(bundle)
    if out.resolve().is_relative_to(bundle) or bundle.is_relative_to(out.resolve()):
        raise ValueError('Output must be outside the bundle')
    runtime = require_native(manifest['image'])
    out.mkdir(parents=True, exist_ok=True)
    smoke = {'schema_version': VERSION, 'status': 'running', 'image': manifest['image'],
             'checkpoint': manifest['checkpoint'], 'code': manifest['code'],
             'input_sha256': manifest['files']['input/demo.pcd']['sha256'],
             'runtime': runtime, 'limits': {'cpus': 4, 'memory': '4g'}, 'steps': []}
    def step(name, action):
        """Record wall elapsed time and UTC boundaries for one operation.

        Args:
            name: Step name.
            action: Callable operation.

        Returns:
            Operation result.
        """
        item = {'name': name, 'started_utc': datetime.now(timezone.utc).isoformat()}
        smoke['steps'].append(item)
        start = time.monotonic()
        try:
            result = action()
            item['status'] = 'passed'
            return result
        except BaseException:
            item['status'] = 'failed'
            raise
        finally:
            item['ended_utc'] = datetime.now(timezone.utc).isoformat()
            item['elapsed_seconds'] = time.monotonic() - start
    try:
        step('docker-load', lambda: command(['docker', 'load', '-i', str(bundle / 'image.tar.gz')]))
        image_id = manifest['image']['id']
        loaded = json.loads(command(['docker', 'image', 'inspect', image_id]))[0]
        if (loaded['Id'] != image_id or loaded['Os'] != manifest['image']['os']
                or loaded['Architecture'] != manifest['image']['architecture']):
            raise ValueError('Loaded image differs from manifest')
        for label, delta, voxel in RUNS:
            step('run-' + label, lambda label=label, delta=delta, voxel=voxel: container([
                '--entrypoint', 'python', *mounts(bundle, out), image_id,
                '/practice/preannotate.py', '--data', '/data/demo.pcd', '--out', '/out/run-' + label,
                '--from', 'KITTI', '--deltas', delta, '--voxel-size', voxel, '--score-thresh', '0.3']))
            smoke['steps'][-1].update(validate_outputs(out, label, delta, voxel))
        step('qc-cases', lambda: container(['--entrypoint', 'python', *mounts(bundle, out), image_id,
            '/practice/pipeline-qc-cases.py', '--prediction',
            '/out/run-B/boxes-demo-delta-1.73-voxel-0.16.json', '--out', '/out/qc-cases',
            '--pcd', '/data/demo.pcd']))
        for name in ('correct', 'batch-z', 'one-box-z'):
            for file in (f'case-{name}.json', f'side-{name}.png'):
                if not (out / 'qc-cases' / file).is_file() or (out / 'qc-cases' / file).stat().st_size == 0:
                    raise ValueError(f'Missing QC output: {file}')
        qc = json.loads((out / 'qc-cases/manifest.json').read_text())
        for name in ('correct', 'batch-z', 'one-box-z'):
            case = json.loads((out / 'qc-cases' / f'case-{name}.json').read_text())
            if (case.get('training_only') is not True
                    or case.get('source_prediction_sha256') != smoke['steps'][2]['prediction_sha256']):
                raise ValueError('QC case must be training_only and reference original B prediction')
        if (qc.get('training_only') is not True
                or qc.get('source_prediction_sha256') != smoke['steps'][2]['prediction_sha256']):
            raise ValueError('QC cases do not reference original B prediction')
        smoke['status'] = 'passed'
    except BaseException as error:
        smoke['status'] = 'failed'
        smoke['error'] = str(error) or type(error).__name__
        raise
    finally:
        write_json(out / 'smoke.json', smoke)
    print(f'Offline A/B/C and QC completed: {out}')


def main() -> None:
    """Parse the portable host CLI and report actionable failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    pack_parser = sub.add_parser('pack', help='Package an existing native image and permitted PCD')
    pack_parser.add_argument('--pcd', type=Path, default=Path(__file__).resolve().parents[1] / 'data/demo.pcd')
    pack_parser.add_argument('--image', required=True)
    pack_parser.add_argument('--out', type=Path, required=True)
    run_parser = sub.add_parser('run', help='Verify then execute a bundle offline')
    run_parser.add_argument('--bundle', type=Path, required=True)
    run_parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        (pack if args.operation == 'pack' else run_bundle)(args)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Error: {error}\n')
    except KeyboardInterrupt:
        parser.exit(130, 'Interrupted; owned foreground container cleaned up.\n')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    main()
