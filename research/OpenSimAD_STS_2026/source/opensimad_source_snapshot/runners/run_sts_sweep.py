"""
Torque-driven STS GRF/COP convergence sweep.

Reference implementation: Example_GRFTrack/run_E008.py
Experiment definitions: Example_GRFTrack/sts_sweep_manifest.json

Every experiment has an independent Condor working directory.
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path

baseDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(baseDir)
sys.path.append(
    os.path.join(baseDir, "UtilsDynamicSimulations", "OpenSimAD")
)

from utilsOpenSimAD import processInputsOpenSimAD
from mainOpenSimAD import run_tracking
from utilsProcessing import getCOP_masks
from utils import storage_to_numpy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_id")
    args = parser.parse_args()

    manifest_path = (
        Path(baseDir)
        / "Example_GRFTrack/sts_sweep_manifest.json"
    )

    configs = json.loads(manifest_path.read_text())
    matches = [
        c for c in configs
        if c["ID"] == args.experiment_id
    ]

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one config for {args.experiment_id}"
        )

    config = matches[0]
    exp_id = config["ID"]

    dataFolder = os.path.join(baseDir, "Data")
    session_id = "subject2_lab_STS_test"
    trial_name = "STS1"
    motion_type = "sts_grf"

    dataset = Path(dataFolder) / session_id

    force_dir = dataset / "ForceData"

    optimized = force_dir / "STS1_Optimized_forces.mot"
    original = force_dir / "STS1_forces.mot"

    grf_path = optimized if optimized.exists() else original

    if not grf_path.exists():
        raise FileNotFoundError(grf_path)

    print("=" * 70)
    print("EXPERIMENT:", exp_id)
    print(json.dumps(config, indent=2))
    print("GRF source:", grf_path)
    print("=" * 70, flush=True)

    # Preserve E008's COP validity detection.
    cop_right, cop_left = getCOP_masks(
        str(grf_path),
        threshold=10
    )

    force_data = storage_to_numpy(str(grf_path))
    input_times = force_data["time"]

    # Preserve E008's segmentation for original-window jobs.
    # Buffered jobs explicitly use the E004-style interval.
    if config["window"] == "original":
        settings = processInputsOpenSimAD(
            baseDir,
            dataFolder,
            session_id,
            trial_name,
            motion_type,
            repetition=0,
            treadmill_speed=0
        )

    elif config["window"] == "buffered":
        settings = processInputsOpenSimAD(
            baseDir,
            dataFolder,
            session_id,
            trial_name,
            motion_type,
            time_window=[0.17, 1.81],
            treadmill_speed=0
        )

    else:
        raise ValueError("Unknown window: " + config["window"])

    # Match E008's GRF/COP input preparation.
    settings["CoP_mask"] = {
        "right": cop_right,
        "left": cop_left
    }

    settings["input_times"] = input_times

    # Fixed settings across the 72 experiments.
    settings["torque_driven_model"] = True
    settings["allowPelvisResiduals"] = True
    settings["heel_vGRF_threshold"] = 0

    # Avoid the inherited lower-limb periodicity requirement.
    settings.pop("periodicConstraints", None)

    # Variable solver settings.
    settings["meshDensity"] = int(config["meshDensity"])
    settings["ipopt_tolerance"] = int(
        config["ipopt_tolerance"]
    )
    settings["maxIter"] = int(config["maxIter"])

    # Variable tracking weights.
    weight_keys = [
        "positionTrackingTerm",
        "velocityTrackingTerm",
        "accelerationTrackingTerm",
        "grfTrackingTerm",
        "copTrackingTerm",
        "copMonotonicTerm",
        "pelvisResidualsTerm",
        "coordinateExcitationTerm",
    ]

    for key in weight_keys:
        settings["weights"][key] = config[key]

    # Verify the intended COP switches.
    expected_cop = bool(config["COP_objective_enabled"])
    actual_cop = settings["weights"]["copTrackingTerm"] > 0
    actual_monotonic = (
        settings["weights"]["copMonotonicTerm"] > 0
    )

    assert actual_cop == expected_cop
    assert actual_monotonic == expected_cop
    assert settings["torque_driven_model"] is True
    assert settings["heel_vGRF_threshold"] == 0
    assert "periodicConstraints" not in settings

    # Save the actual solver parameters, not just the requested
    # manifest values. Large input arrays are documented separately.
    metadata = {
        "experiment_id": exp_id,
        "requested_config": config,
        "effective_solver_settings": {
            key: settings.get(key)
            for key in [
                "meshDensity",
                "ipopt_tolerance",
                "maxIter",
                "torque_driven_model",
                "allowPelvisResiduals",
                "heel_vGRF_threshold",
                "periodicConstraints",
                "coordinate_constraints",
            ]
        },
        "effective_weights": dict(settings["weights"]),
        "input_force_file": grf_path.name,
        "input_force_samples": len(input_times),
        "cop_mask_samples": {
            "right": len(cop_right),
            "left": len(cop_left),
        },
        "runner_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
    }

    metadata_dir = dataset / "ExperimentMetadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = metadata_dir / f"{exp_id}.json"

    metadata_path.write_text(
        json.dumps(metadata, indent=2, default=str) + "\n"
    )

    print("=== EFFECTIVE TRACKING WEIGHTS ===")
    print(json.dumps(
        metadata["effective_weights"],
        indent=2,
        default=str
    ))

    print("=== EFFECTIVE SOLVER SETTINGS ===")
    print(json.dumps(
        metadata["effective_solver_settings"],
        indent=2,
        default=str
    ))

    # Keep the case name unique for every experiment.
    case = f"{exp_id}_torqueDriven_STS"

    print("=== STARTING OPENSIMAD ===", flush=True)

    run_tracking(
        baseDir,
        dataFolder,
        session_id,
        settings,
        case=case
    )

    print("=== OPENSIMAD RETURNED ===", flush=True)


if __name__ == "__main__":
    main()
