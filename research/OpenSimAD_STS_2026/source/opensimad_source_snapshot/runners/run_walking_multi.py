"""E111-E126: multi-subject walking GRF/COP validation."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

baseDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(
    0, os.path.join(baseDir, "Example_GRFTrack", "E009_overrides")
)
sys.path.append(baseDir)
sys.path.append(
    os.path.join(baseDir, "UtilsDynamicSimulations", "OpenSimAD")
)

from gait_analysis import process_gait_data
from utilsProcessing import map_stance_phase
from utilsOpenSimAD import processInputsOpenSimAD
from mainOpenSimAD import run_tracking
from utils import storage_to_numpy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_id")
    args = parser.parse_args()

    manifest = json.loads(
        (Path(baseDir) / "Example_GRFTrack"
         / "walking_multi_manifest.json").read_text()
    )

    matches = [
        c for c in manifest if c["ID"] == args.experiment_id
    ]
    assert len(matches) == 1, "Invalid experiment ID"

    cfg = matches[0]
    eid = cfg["ID"]
    subject = cfg["subject"]
    method = cfg["cop_mask_method"]

    dataFolder = os.path.join(baseDir, "Data")
    session_id = f"subject{subject}_lab_walking_multi"
    trial_name = "walking1"
    data_path = Path(dataFolder) / session_id

    force_path = data_path / "ForceData/walking1_forces.mot"
    assert force_path.is_file()

    print("=== WALKING VALIDATION ===", flush=True)
    print(json.dumps(cfg, indent=2), flush=True)

    # Identical gait detection to E009.
    _, _, gait_events, _, time = process_gait_data(
        str(data_path),
        trial_name,
        "l",
        6,
        -1,
        "overground",
        0,
        0,
    )

    left_stance, right_stance = map_stance_phase(
        gait_events, time_len=len(time)
    )

    event_time = np.asarray(
        gait_events["time"], dtype=float
    )

    assert np.isfinite(event_time).all()
    assert len(event_time) == len(right_stance)
    assert len(event_time) == len(left_stance)

    marker_right = np.isfinite(right_stance).astype(int)
    marker_left = np.isfinite(left_stance).astype(int)

    # Measured vertical forces are expressed along OpenSim Y.
    force_data = storage_to_numpy(str(force_path))

    force_time = np.asarray(force_data["time"], dtype=float)

    right_vertical = np.asarray(
        force_data["R_ground_force_vy"], dtype=float
    )
    left_vertical = np.asarray(
        force_data["L_ground_force_vy"], dtype=float
    )

    assert np.isfinite(right_vertical).all()
    assert np.isfinite(left_vertical).all()
    assert np.all(np.diff(force_time) > 0)

    threshold = float(cfg["force_threshold_N"])

    force_right = (
        np.interp(
            event_time, force_time, right_vertical,
            left=0, right=0
        ) > threshold
    ).astype(int)

    force_left = (
        np.interp(
            event_time, force_time, left_vertical,
            left=0, right=0
        ) > threshold
    ).astype(int)

    assert 0 < force_right.sum() < len(force_right)
    assert 0 < force_left.sum() < len(force_left)

    if method == "marker":
        cop_right, cop_left = marker_right, marker_left
    elif method == "force":
        cop_right, cop_left = force_right, force_left
    else:
        raise ValueError(method)

    # Same input preparation as E009.
    settings = processInputsOpenSimAD(
        baseDir,
        dataFolder,
        session_id,
        trial_name,
        "walking_grf",
        time_window=[
            float(event_time.min()),
            float(event_time.max())
        ],
        treadmill_speed=0
    )

    settings["torque_driven_model"] = True

    settings["CoP_mask"]["right"] = cop_right
    settings["CoP_mask"]["left"] = cop_left

    # Keep marker-derived phase percentages in both variants.
    settings["Stance_Precentage"]["right"] = right_stance
    settings["Stance_Precentage"]["left"] = left_stance

    settings["input_times"] = gait_events["time"]

    settings["filter_Qs_toTrack"] = True
    settings["cutoff_freq_Qs"] = 6
    settings["filter_Qds_toTrack"] = True
    settings["cutoff_freq_Qds"] = 6
    settings["filter_Qdds_toTrack"] = True
    settings["cutoff_freq_Qdds"] = 6
    settings["splineQds"] = True

    settings["meshDensity"] = 50
    settings["ipopt_tolerance"] = 3
    settings["maxIter"] = 10000
    settings["weights"]["positionTrackingTerm"] = 1000
    settings["weights"]["grfTrackingTerm"] = 0.001

    # Save both the requested configuration and effective weights.
    metadata_dir = data_path / "ExperimentMetadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "ID": eid,
        "configuration": cfg,
        "effective_weights": dict(settings["weights"]),
        "meshDensity": settings["meshDensity"],
        "ipopt_tolerance": settings["ipopt_tolerance"],
        "maxIter": settings["maxIter"],
        "right_cop_valid_frames": int(cop_right.sum()),
        "left_cop_valid_frames": int(cop_left.sum()),
        "right_marker_force_disagreement": int(
            np.count_nonzero(marker_right != force_right)
        ),
        "left_marker_force_disagreement": int(
            np.count_nonzero(marker_left != force_left)
        ),
        "runner_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
    }

    (metadata_dir / f"{eid}.json").write_text(
        json.dumps(metadata, indent=2, default=str) + "\n"
    )

    print("=== EFFECTIVE CONFIGURATION ===")
    print(json.dumps(metadata, indent=2, default=str))
    print("=== STARTING IPOPT ===", flush=True)

    run_tracking(
        baseDir,
        dataFolder,
        session_id,
        settings,
        case=f"{eid}_walking_{method}"
    )

    print("=== OPENSIMAD RETURNED ===", flush=True)


if __name__ == "__main__":
    main()
