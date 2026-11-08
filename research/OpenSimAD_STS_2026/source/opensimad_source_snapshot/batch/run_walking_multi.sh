#!/bin/bash
set -euo pipefail

EXPERIMENT_ID="$1"
NUMBER="${EXPERIMENT_ID#E}"
SUBJECT=$((3 + (10#$NUMBER - 111) / 2))
DATASET="subject${SUBJECT}_lab_walking_multi"

export PYTHONUNBUFFERED=1
export MPLBACKEND=Agg
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4

echo "Experiment=$EXPERIMENT_ID"
echo "Subject=$SUBJECT"
hostname
date

tar -xzf walking_multi_bundle.tar.gz
cd opencap-processing-grf-sts-test

cp ../.env .env
chmod 600 .env

sha256sum Example_GRFTrack/run_walking_multi.py

if python Example_GRFTrack/run_walking_multi.py "$EXPERIMENT_ID"; then
    STATUS=0
else
    STATUS=$?
fi

echo "Python exit code: $STATUS"

printf "Experiment=%s\nSubject=%s\nExitCode=%s\n" \
    "$EXPERIMENT_ID" "$SUBJECT" "$STATUS" \
    > "Data/$DATASET/${EXPERIMENT_ID}_job_status.txt"

cd ..

tar -czf "${EXPERIMENT_ID}_results.tar.gz" \
    -C opencap-processing-grf-sts-test/Data \
    "$DATASET"

ls -lh "${EXPERIMENT_ID}_results.tar.gz"
date

exit "$STATUS"
