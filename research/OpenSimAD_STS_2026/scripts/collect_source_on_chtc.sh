#!/usr/bin/env bash
# Run ON CHTC login node to assemble research source-only snapshot.
# Does not schedule or change any simulations; does not include .env or subject data.
set -euo pipefail
HOME_DIR="${HOME}"
BASE="${HOME_DIR}/opensimad_source_snapshot"
SRC="${HOME_DIR}/opencap-processing-grf-sts-test/Example_GRFTrack"
mkdir -p "${BASE}/runners" "${BASE}/batch" "${BASE}/metadata"
copy_if_exists() { local src="$1" dest="$2"; if [[ -f "$src" ]]; then cp -p "$src" "$dest"; else printf 'MISSING %s\n' "$src" >&2; fi; }
for f in run_E008.py run_E009.py run_sts_sweep.py run_walking_multi.py; do copy_if_exists "${SRC}/${f}" "${BASE}/runners/${f}"; done
for f in run_sts_sweep.sh sts_pilot.sub sts_remaining.sub monitor_sts.py collect_sts_results.py; do copy_if_exists "${HOME_DIR}/sts_sweep_v1/${f}" "${BASE}/batch/${f}"; done
for f in run_walking_multi.sh walking_multi.sub; do copy_if_exists "${HOME_DIR}/sts_walking_multi/${f}" "${BASE}/batch/${f}"; done
for f in sts_sweep_manifest.json sts_sweep_manifest.csv INDIVIDUAL_JOB_INDEX.md README_experimental_design.md sts_sweep_outcomes.csv; do copy_if_exists "${HOME_DIR}/sts_sweep_v1/${f}" "${BASE}/metadata/${f}"; done
copy_if_exists "${HOME_DIR}/sts_walking_multi/walking_multi_manifest.json" "${BASE}/metadata/walking_multi_manifest.json"
# Exact manifest/registry are the preferred source of all IDs; registry may have internal paths and needs review before publishing.
# Do NOT collect registry automatically to avoid publishing private notes accidentally.
if find "$BASE" -type f | grep -E '(^|/)(\.env|.*\.key|.*\.pem)$'; then echo 'Sensitive file found; abort' >&2; exit 1; fi
(cd "$BASE" && find . -type f -print0 | sort -z | xargs -0 sha256sum > source_file_sha256.txt)
cd "${HOME_DIR}"
tar -czf opensimad_source_snapshot.tar.gz opensimad_source_snapshot
sha256sum opensimad_source_snapshot.tar.gz
ls -lh opensimad_source_snapshot.tar.gz
