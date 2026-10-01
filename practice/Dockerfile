# CPU image for the day-13 PointPillars pre-label.
# Same checkpoint and architecture as zhulf0804/PointPillars.
# The voxel op is the upstream C++ CPU path. NMS is a CPU stand-in.
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir "numpy<2" matplotlib "numba<0.61" pyyaml

ARG POINTPILLARS_COMMIT=620e6b0d07e4cb37b7b0114f26b934e8be92a0ba
RUN git clone https://github.com/zhulf0804/PointPillars.git /opt/PointPillars \
    && git -C /opt/PointPillars checkout ${POINTPILLARS_COMMIT}

COPY patches/setup_cpu.py /opt/PointPillars/setup.py
COPY patches/iou3d_module.py /opt/PointPillars/pointpillars/ops/iou3d_module.py
COPY patches/utils_init.py /opt/PointPillars/pointpillars/utils/__init__.py

WORKDIR /opt/PointPillars
RUN python setup.py build_ext --inplace

COPY preannotate.py /opt/preannotate.py
ENV PYTHONPATH=/opt/PointPillars
ENV MPLBACKEND=Agg
WORKDIR /opt
ENTRYPOINT ["python", "/opt/preannotate.py"]
