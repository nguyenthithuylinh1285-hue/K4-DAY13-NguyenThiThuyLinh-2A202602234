"""Offline stdlib tests; Docker is mocked only at the process boundary."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import gzip
import sys

SPEC = importlib.util.spec_from_file_location('student_bundle', Path(__file__).with_name('student-bundle.py'))
student = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = student
SPEC.loader.exec_module(student)
IMAGE = 'sha256:' + 'a' * 64


def pcd_bytes():
    return (b'FIELDS x y z rgb\nSIZE 4 4 4 4\nTYPE F F F F\nCOUNT 1 1 1 1\n'
            b'WIDTH 2\nHEIGHT 1\nPOINTS 2\nDATA binary\n' + struct.pack('<ffffffff', 1, 2, 3, 0, 4, 5, 6, 0))


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pcd = self.root / 'original frame.pcd'
        self.pcd.write_bytes(pcd_bytes())
        self.bundle = self.root / 'bundle'
        self.out = self.root / 'results'
        self.repo = self.root / 'public-repo'
        (self.repo / 'bundle').mkdir(parents=True)
        (self.repo / 'practice').mkdir()
        (self.repo / 'data').mkdir()
        (self.repo / 'data/demo.pcd').write_bytes(pcd_bytes())
        for name in ('practice/preannotate.py', 'practice/pipeline-qc-cases.py',
                     'PRE-LABEL-REPORT.md', 'TEAMMATES.md', 'bundle/README-STUDENT.md',
                     'data/ATTRIBUTION.md', 'data/LICENSE.txt'):
            (self.repo / name).write_text('Public fixture ' + name)
        self.provenance = {'source_ref': 'https://example.org/public-kitti-frame',
                           'license': 'CC-BY-NC-SA-3.0', 'adaptation': 'z + 1.73'}
        (self.repo / 'data/provenance.json').write_text(json.dumps(self.provenance))
        self.runner = self.repo / 'bundle/student-bundle.py'
        self.runner.write_bytes(Path(student.__file__).read_bytes())

    def docker(self, argv, **kwargs):
        if argv[:3] == ['docker', 'image', 'inspect']:
            stdout = json.dumps([{'Id': IMAGE, 'Os': 'linux', 'Architecture': 'arm64'}])
        elif argv[:2] == ['docker', 'info']:
            stdout = json.dumps({'OSType': 'linux', 'Architecture': 'aarch64'})
        elif argv[:2] == ['docker', 'run']:
            if '/opt/PointPillars/LICENSE' in argv:
                stdout = 'MIT License\nUnit test attribution fixture'
            elif '-c' in argv:
                stdout = 'b' * 64 + '\n'
            elif '/practice/preannotate.py' in argv:
                self.prediction(argv[argv.index('--out') + 1].split('/')[-1],
                                argv[argv.index('--deltas') + 1], argv[argv.index('--voxel-size') + 1])
                stdout = ''
            else:
                root = self.out / 'qc-cases'
                root.mkdir()
                for name in ('correct', 'batch-z', 'one-box-z'):
                    (root / f'case-{name}.json').write_text(json.dumps({
                        'training_only': True, 'source_prediction_sha256': student.sha256(
                            self.out / 'run-B/boxes-demo-delta-1.73-voxel-0.16.json')}))
                    (root / f'side-{name}.png').write_bytes(b'png')
                (root / 'manifest.json').write_text(json.dumps({'training_only': True, 'source_prediction_sha256':
                    student.sha256(self.out / 'run-B/boxes-demo-delta-1.73-voxel-0.16.json')}))
                stdout = ''
        elif argv[0] == 'git':
            stdout = 'c' * 40 + '\n' if 'rev-parse' in argv else ''
        else:
            stdout = ''
        return subprocess.CompletedProcess(argv, 0, stdout)

    def pack(self):
        args = argparse.Namespace(pcd=self.pcd, image='test:local', out=self.bundle)
        process = unittest.mock.Mock()
        process.stdout = io.BytesIO(b'exact exported Docker archive')
        process.wait.return_value = 0
        process.poll.return_value = 0
        with patch.object(student, '__file__', str(self.runner)), \
                patch.object(student.subprocess, 'run', side_effect=self.docker), \
                patch.object(student.subprocess, 'Popen', return_value=process):
            student.pack(args)
        return args

    def prediction(self, name, delta, voxel):
        root = self.out / name
        root.mkdir()
        stem = f'demo-delta-{delta}-voxel-{voxel}'
        (root / f'boxes-{stem}.json').write_text(json.dumps({
            'frame_id': 'demo', 'dataset': 'KITTI', 'delta': float(delta),
            'voxel_size': float(voxel), 'boxes': [{}, {}]}))
        (root / f'side-{stem}.png').write_bytes(b'png')
        (root / 'summary.csv').write_text('frame_id,dataset,delta,voxel_size,n_boxes,mean_z\n')

    def test_pack_preserves_input_and_provenance(self):
        self.pack()
        manifest = student.verify_bundle(self.bundle)
        self.assertEqual((self.bundle / 'input/demo.pcd').read_bytes(), self.pcd.read_bytes())
        self.assertEqual(manifest['input']['original_filename'], 'original frame.pcd')
        self.assertEqual(manifest['image']['id'], IMAGE)
        self.assertEqual(manifest['input']['source_provenance'], self.provenance)
        self.assertEqual(manifest['code']['repo_revision'], 'c' * 40)
        self.assertFalse(manifest['code']['working_tree_dirty'])
        for name in ('DATA-LICENSE.txt', 'ATTRIBUTION.md', 'TEAMMATES.md', 'input/provenance.json'):
            self.assertIn(name, manifest['files'])
        self.assertEqual(manifest['checkpoint']['sha256'], 'b' * 64)
        with gzip.open(self.bundle / 'image.tar.gz', 'rb') as archive:
            self.assertEqual(archive.read(), b'exact exported Docker archive')

    def test_invalid_pcd_does_not_mutate_output_or_call_docker(self):
        self.pcd.write_bytes(b'not a PCD')
        args = argparse.Namespace(pcd=self.pcd, image='test', out=self.bundle)
        with patch.object(student.subprocess, 'run') as docker, self.assertRaises(ValueError):
            student.pack(args)
        docker.assert_not_called()
        self.assertFalse(self.bundle.exists())

    def test_pack_requires_public_licenses_before_docker(self):
        for name in ('data/LICENSE.txt', 'data/ATTRIBUTION.md', 'data/provenance.json'):
            path = self.repo / name
            original = path.read_bytes()
            path.unlink()
            with patch.object(student.subprocess, 'run') as calls, self.assertRaises(ValueError):
                self.pack()
            calls.assert_not_called()
            self.assertFalse(self.bundle.exists())
            path.write_bytes(original)

    def test_pack_rejects_any_other_dataset(self):
        self.pcd.write_bytes(pcd_bytes().replace(struct.pack('<f', 1.0), struct.pack('<f', 9.0)))
        with patch.object(student.subprocess, 'run') as calls, self.assertRaisesRegex(ValueError, 'public KITTI'):
            self.pack()
        calls.assert_not_called()
        self.assertFalse(self.bundle.exists())

    def test_refuses_output_file_nonempty_directory_and_symlink(self):
        for kind in ('file', 'directory', 'symlink'):
            path = self.root / kind
            if kind == 'file':
                path.write_text('keep')
            elif kind == 'directory':
                path.mkdir()
                (path / 'keep').touch()
            else:
                path.symlink_to(self.root, target_is_directory=True)
            with self.assertRaises(ValueError):
                student.empty_output(path)
        empty = self.root / 'empty'
        empty.mkdir()
        student.empty_output(empty)

    def test_nonempty_run_output_is_rejected_before_docker(self):
        self.out.mkdir()
        (self.out / 'keep').write_text('unchanged')
        with patch.object(student.subprocess, 'run') as docker, self.assertRaises(ValueError):
            student.run_bundle(argparse.Namespace(bundle=self.bundle, out=self.out))
        docker.assert_not_called()
        self.assertEqual((self.out / 'keep').read_text(), 'unchanged')

    def test_duplicate_manifest_keys_rejected(self):
        self.bundle.mkdir()
        (self.bundle / 'manifest.json').write_text('{"schema_version": 1, "schema_version": 1}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            student.verify_bundle(self.bundle)

    def test_tampered_checksum_rejected(self):
        self.pack()
        (self.bundle / 'practice/preannotate.py').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'Checksum'):
            student.verify_bundle(self.bundle)

    def test_required_file_missing_rejected(self):
        self.pack()
        (self.bundle / 'input/demo.pcd').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            student.verify_bundle(self.bundle)

    def test_traversal_and_windows_paths_rejected(self):
        self.pack()
        path = self.bundle / 'manifest.json'
        original = path.read_text()
        for unsafe in ('../outside', '/absolute', 'C:/outside', r'input\demo.pcd', 'input/../demo.pcd'):
            manifest = json.loads(original)
            manifest['files'][unsafe] = {'sha256': 'a' * 64, 'bytes': 0}
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Unsafe manifest path'):
                student.verify_bundle(self.bundle)

    def test_symlink_rejected_even_with_matching_bytes(self):
        self.pack()
        path = self.bundle / 'input/demo.pcd'
        path.unlink()
        path.symlink_to(self.pcd)
        with self.assertRaisesRegex(ValueError, 'Symbolic link'):
            student.verify_bundle(self.bundle)

    def test_wrong_architecture_prevents_load_and_output(self):
        self.pack()
        with patch.object(student.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0,
                   json.dumps({'OSType': 'linux', 'Architecture': 'x86_64'}))) as calls:
            with self.assertRaisesRegex(ValueError, 'native Linux'):
                student.run_bundle(argparse.Namespace(bundle=self.bundle, out=self.out))
        self.assertFalse(self.out.exists())
        self.assertEqual(len(calls.call_args_list), 1)
        self.assertNotIn('load', calls.call_args.args[0])

    def test_run_uses_sequential_exact_offline_contract(self):
        self.pack()
        with patch.object(student.subprocess, 'run', side_effect=self.docker) as calls:
            student.run_bundle(argparse.Namespace(bundle=self.bundle, out=self.out))
        runs = [call.args[0] for call in calls.call_args_list if call.args[0][:2] == ['docker', 'run']]
        self.assertEqual(len(runs), 4)
        for argv in runs:
            self.assertEqual(argv[argv.index('--network') + 1], 'none')
            self.assertEqual(argv[argv.index('--cpus') + 1], '4')
            self.assertEqual(argv[argv.index('--memory') + 1], '4g')
            self.assertIn(IMAGE, argv)
            self.assertIn('--rm', argv)
            self.assertTrue(argv[argv.index('--name') + 1].startswith('student-bundle-'))
            self.assertEqual(sum('readonly' in value for value in argv), 2)
        self.assertEqual([argv[argv.index('--deltas') + 1] for argv in runs[:3]], ['0', '1.73', '1.73'])
        self.assertEqual([argv[argv.index('--voxel-size') + 1] for argv in runs[:3]], ['0.16', '0.16', '0.32'])
        self.assertIn('/practice/preannotate.py', runs[0])
        self.assertIn('/out/run-B/boxes-demo-delta-1.73-voxel-0.16.json', runs[3])
        smoke = json.loads((self.out / 'smoke.json').read_text())
        self.assertEqual(smoke['status'], 'passed')
        self.assertEqual([step['name'] for step in smoke['steps']], ['docker-load', 'run-A', 'run-B', 'run-C', 'qc-cases'])
        self.assertTrue(all(step['elapsed_seconds'] >= 0 for step in smoke['steps']))
        self.assertNotIn('ram_measured', smoke)

    def test_owned_container_cleanup_on_interruption(self):
        def interrupted(argv, **kwargs):
            if argv[:2] == ['docker', 'run']:
                raise KeyboardInterrupt
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(student.subprocess, 'run', side_effect=interrupted) as calls:
            with self.assertRaises(KeyboardInterrupt):
                student.container([IMAGE])
        first, last = (call.args[0] for call in calls.call_args_list)
        self.assertEqual(last, ['docker', 'rm', '-f', first[first.index('--name') + 1]])

    def test_b_helper_failure_is_preserved_in_smoke(self):
        self.pack()
        def failure(argv, **kwargs):
            if '/practice/pipeline-qc-cases.py' in argv:
                raise subprocess.CalledProcessError(1, argv)
            return self.docker(argv, **kwargs)
        with patch.object(student.subprocess, 'run', side_effect=failure):
            with self.assertRaises(subprocess.CalledProcessError):
                student.run_bundle(argparse.Namespace(bundle=self.bundle, out=self.out))
        smoke = json.loads((self.out / 'smoke.json').read_text())
        self.assertEqual(smoke['status'], 'failed')
        self.assertEqual(smoke['steps'][-1]['status'], 'failed')

    def test_all_required_manifest_entries_are_enforced(self):
        self.pack()
        path = self.bundle / 'manifest.json'
        original = json.loads(path.read_text())
        for name in student.REQUIRED:
            with self.subTest(name=name):
                manifest = json.loads(json.dumps(original))
                del manifest['files'][name]
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'required files'):
                    student.verify_bundle(self.bundle)
        path.write_text(json.dumps(original))

    def test_pack_records_actual_repository_and_dirty_state(self):
        def dirty(argv, **kwargs):
            if argv[0] == 'git':
                self.assertEqual(argv[2], str(self.repo.resolve()))
                return subprocess.CompletedProcess(argv, 0,
                    'd' * 40 if 'rev-parse' in argv else ' M README.md')
            return self.docker(argv, **kwargs)
        args = argparse.Namespace(pcd=self.pcd, image='test', out=self.bundle)
        with patch.object(student, '__file__', str(self.runner)), \
                patch.object(student.subprocess, 'run', side_effect=dirty), \
                patch.object(student, 'save_image', side_effect=lambda _, path: path.write_bytes(b'image')):
            student.pack(args)
        manifest = student.verify_bundle(self.bundle)
        self.assertEqual(manifest['code']['repo_revision'], 'd' * 40)
        self.assertTrue(manifest['code']['working_tree_dirty'])

    def test_output_inside_bundle_is_rejected_before_docker(self):
        self.pack()
        with patch.object(student.subprocess, 'run') as calls, self.assertRaisesRegex(ValueError, 'outside'):
            student.run_bundle(argparse.Namespace(bundle=self.bundle, out=self.bundle / 'results'))
        calls.assert_not_called()

    def test_loaded_image_identity_mismatch_prevents_inference(self):
        self.pack()
        def mismatch(argv, **kwargs):
            if argv[:3] == ['docker', 'image', 'inspect']:
                return subprocess.CompletedProcess(argv, 0, json.dumps([
                    {'Id': 'sha256:' + 'e' * 64, 'Os': 'linux', 'Architecture': 'arm64'}]))
            return self.docker(argv, **kwargs)
        with patch.object(student.subprocess, 'run', side_effect=mismatch) as calls:
            with self.assertRaisesRegex(ValueError, 'Loaded image differs'):
                student.run_bundle(argparse.Namespace(bundle=self.bundle, out=self.out))
        self.assertFalse(any(call.args[0][:2] == ['docker', 'run'] for call in calls.call_args_list))
        self.assertEqual(json.loads((self.out / 'smoke.json').read_text())['status'], 'failed')

    def test_qc_requires_training_only_cases(self):
        self.pack()
        def invalid_case(argv, **kwargs):
            result = self.docker(argv, **kwargs)
            if '/practice/pipeline-qc-cases.py' in argv:
                path = self.out / 'qc-cases/case-correct.json'
                case = json.loads(path.read_text())
                case['training_only'] = False
                path.write_text(json.dumps(case))
            return result
        with patch.object(student.subprocess, 'run', side_effect=invalid_case):
            with self.assertRaisesRegex(ValueError, 'training_only'):
                student.run_bundle(argparse.Namespace(bundle=self.bundle, out=self.out))
        self.assertEqual(json.loads((self.out / 'smoke.json').read_text())['status'], 'failed')

    def test_packed_uint32_rgb_is_supported_without_coordinate_changes(self):
        self.pcd.write_bytes(pcd_bytes().replace(b'TYPE F F F F', b'TYPE F F F U'))
        self.assertEqual(student.validate_pcd(self.pcd), 2)

    def test_pcd_bad_body_and_nonfinite_coordinates_rejected(self):
        for raw in (pcd_bytes()[:-1], pcd_bytes() + b'extra', pcd_bytes().replace(
                struct.pack('<f', 1.0), struct.pack('<f', float('nan')))):
            self.pcd.write_bytes(raw)
            with self.assertRaises(ValueError):
                student.validate_pcd(self.pcd)


if __name__ == '__main__':
    unittest.main()
