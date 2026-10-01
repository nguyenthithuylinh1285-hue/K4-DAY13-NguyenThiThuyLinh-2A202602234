"""CPU-only build of the PointPillars voxel op.

The upstream setup.py asks for a CUDA extension. This lab image has no GPU.
The same voxelization sources already dispatch to ``hard_voxelize_cpu`` when
the tensor is on CPU, so the extension is built from the C++ files only.
"""

from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CppExtension

setup(
    name="pointpillars",
    version="0.1",
    packages=["pointpillars"],
    ext_modules=[
        CppExtension(
            name="pointpillars.ops.voxel_op",
            sources=[
                "pointpillars/ops/voxelization/voxelization.cpp",
                "pointpillars/ops/voxelization/voxelization_cpu.cpp",
            ],
        ),
    ],
    cmdclass={"build_ext": BuildExtension},
    zip_safe=False,
)
