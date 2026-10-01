import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('prepare_demo', Path(__file__).with_name('prepare-kitti-demo.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PrepareTests(unittest.TestCase):
    def test_translation_keeps_point_order_xy_and_zero_rgb(self):
        raw = struct.pack('<ffffffff', 1, 2, -1.5, .7, 4, -5, 0, .2)
        pcd, count = module.convert(raw)
        body = pcd.split(b'DATA binary\n')[1]
        rows = list(struct.iter_unpack('<fffI', body))
        self.assertEqual(count, 2)
        self.assertEqual([(r[0], r[1], r[3]) for r in rows], [(1, 2, 0), (4, -5, 0)])
        self.assertAlmostEqual(rows[0][2], .23, places=6)
        self.assertAlmostEqual(rows[1][2], 1.73, places=6)

    def test_invalid_record_or_nonfinite_is_rejected(self):
        for raw in (b'', b'bad', struct.pack('<ffff', 1, 2, float('nan'), 0)):
            with self.assertRaises(ValueError): module.convert(raw)

    def test_changed_source_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / 'data'
            with self.assertRaises(ValueError): module.prepare(b'wrong source', out)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
