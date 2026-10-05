#!/bin/bash
set -euo pipefail

echo "=== Job information ==="
hostname
date
echo "Working directory: $PWD"

export PYTHONUNBUFFERED=1
export MPLBACKEND=Agg
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4

echo
echo "=== Environment ==="
python - <<'PY'
import sys
import numpy
import casadi
import opensim

print("Python:", sys.version.split()[0])
print("NumPy:", numpy.__version__)
print("CasADi:", casadi.__version__)
print("OpenSim:", opensim.GetVersion())
PY

echo
echo "=== Unpacking STS test bundle ==="
tar -xzf sts_open_simad_test_bundle.tar.gz

cd opencap-processing-grf-sts-test

# Authentication token is transferred separately, not stored in the archive.
cp ../.env .env

echo
echo "=== Test configuration ==="
echo "Session: subject2_lab_STS_test"
echo "Trial: STS1"
echo "Motion type: sts_grf"
echo "Repetition: 0"
echo "Expected window: 0.47-1.51 s"
echo "Case: sts_grf_lab_measured_v1"

echo
echo "=== Starting OpenSimAD ==="
python Example_GRFTrack/run_subject2_lab_sts_test.py

echo
echo "=== OpenSimAD finished ==="
date

cd ..

tar -czf subject2_lab_sts_test_results.tar.gz \
    -C opencap-processing-grf-sts-test/Data \
    subject2_lab_STS_test

echo
echo "=== Result archive ==="
ls -lh subject2_lab_sts_test_results.tar.gz
