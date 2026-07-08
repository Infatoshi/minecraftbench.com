# Clean container for the eval-time candidate dump: no network at run time, no JVM,
# filesystem = this image + the candidate repo mounted read-only + an output dir.
# Build once:  docker build -t mcbench-eval benchmarks/rewrite/eval
# Dump:        see eval/dump.sh
# ubuntu24.04 + cuda 12.8 = the dev sandbox host (glibc 2.39); candidates may carry
# artifacts built there, so the eval base must match or honest builds fail to link
FROM nvidia/cuda:12.8.1-devel-ubuntu24.04
RUN apt-get update && apt-get install -y --no-install-recommends make cmake g++ \
    zlib1g-dev libpng-dev && \
    rm -rf /var/lib/apt/lists/*
# dev-sandbox parity: the host exposes CUDA headers/libs on default search paths
# (symlinks in /usr/local/include), so candidates legitimately build without -I flags
ENV CPATH=/usr/local/cuda/include \
    LIBRARY_PATH=/usr/local/cuda/lib64
WORKDIR /work
