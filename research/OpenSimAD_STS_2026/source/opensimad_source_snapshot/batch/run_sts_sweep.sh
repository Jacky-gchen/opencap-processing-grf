#!/bin/bash
set -euo pipefail

EXPERIMENT_ID="$1"

export PYTHONUNBUFFERED=1
export MPLBACKEND=Agg
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4

echo "======================================="
echo "STS experiment: $EXPERIMENT_ID"
hostname
date
echo "======================================="

tar -xzf sts_sweep_v1_bundle.tar.gz

cd opencap-processing-grf-sts-test

cp ../.env .env
chmod 600 .env

echo "=== RUNNER SHA256 ==="
sha256sum Example_GRFTrack/run_sts_sweep.py

echo "=== BEGIN OPTIMIZATION ==="

if python Example_GRFTrack/run_sts_sweep.py "$EXPERIMENT_ID"; then
    STATUS=0
else
    STATUS=$?
fi

echo "=== PYTHON EXIT CODE: $STATUS ==="

DATASET="Data/subject2_lab_STS_test"

printf "Experiment=%s\nPythonExitCode=%s\n" \
    "$EXPERIMENT_ID" "$STATUS" \
    > "$DATASET/${EXPERIMENT_ID}_job_status.txt"

cd ..

tar -czf "${EXPERIMENT_ID}_results.tar.gz" \
    -C opencap-processing-grf-sts-test/Data \
    subject2_lab_STS_test

echo "=== RESULT ARCHIVE ==="
ls -lh "${EXPERIMENT_ID}_results.tar.gz"

date
exit "$STATUS"
