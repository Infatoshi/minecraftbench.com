# Clean container for the eval-time candidate dump: no network at run time, no JVM,
# filesystem = this image + the candidate repo mounted read-only + an output dir.
# Build once:  docker build -t mcbench-eval benchmarks/rewrite/eval
# Dump:        see eval/dump.sh
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04
RUN apt-get update && apt-get install -y --no-install-recommends make cmake g++ && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /work
