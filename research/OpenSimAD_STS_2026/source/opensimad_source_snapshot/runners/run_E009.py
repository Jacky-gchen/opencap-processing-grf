"""
E009: Emily Miller walking GRF/COP tracking positive control.

Dataset: OpenCap validation, subject2, walking1, HRNet 2-camera IK.
External loads: measured laboratory GRF/COP.
Model: scaled LaiArnoldModified2017.
Formulation: original walking_grf settings and walking example overrides.
"""

import os
import sys
import numpy as np

baseDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# E009-specific model selection; does not modify shared source files.
overrideDir = os.path.join(
    baseDir, "Example_GRFTrack", "E009_overrides"
)
sys.path.insert(0, overrideDir)
sys.path.append(baseDir)

opensimADDir = os.path.join(
    baseDir, "UtilsDynamicSimulations", "OpenSimAD"
)
sys.path.append(opensimADDir)

from gait_analysis import process_gait_data
from utilsProcessing import map_stance_phase
from utilsOpenSimAD import processInputsOpenSimAD
from mainOpenSimAD import run_tracking

dataFolder = os.path.join(baseDir, "Data")
session_id = "subject2_lab_walking_E009"
trial_name = "walking1"
motion_type = "walking_grf"

case = "E009_emily_walking_measured_grf_v1"

# Original walking example: gait detection and COP masks.
_, _, gait_events, foot_positions, time = process_gait_data(
    os.path.join(dataFolder, session_id),
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

print("=== E009 walking inputs ===")
print("Simulation interval:",
      min(gait_events["time"]),
      max(gait_events["time"]))
print("Left COP mask frames:",
      np.isfinite(left_stance).sum())
print("Right COP mask frames:",
      np.isfinite(right_stance).sum())

# Prepare contact model and OpenSimAD external dynamics function.
settings = processInputsOpenSimAD(
    baseDir,
    dataFolder,
    session_id,
    trial_name,
    motion_type,
    time_window=[
        min(gait_events["time"]),
        max(gait_events["time"])
    ],
    treadmill_speed=0,
)

# Preserve Emily's torque-driven walking example settings.
settings["torque_driven_model"] = True

settings["CoP_mask"]["right"] = (
    np.isfinite(right_stance).astype(int)
)
settings["CoP_mask"]["left"] = (
    np.isfinite(left_stance).astype(int)
)

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
settings["weights"]["positionTrackingTerm"] = 1000
settings["weights"]["grfTrackingTerm"] = 0.001

print("=== Starting E009 OpenSimAD optimization ===")

run_tracking(
    baseDir,
    dataFolder,
    session_id,
    settings,
    case=case
)
