# STS OpenSimAD Convergence Sweep — v1

## Research objective

Identify torque-driven STS configurations that achieve genuine
IPOPT convergence and produce biomechanically plausible motion.

## Reference configurations

E003: Original STS interval, heel 0 N, periodic.
E004: Buffered STS interval, heel 0 N, nonperiodic.
E008: Original STS interval, heel 0 N, nonperiodic.
E009: Walking positive control, converged in 505 iterations,
      but visual inspection raised concerns about foot motion.

## Sweep: E015–E086

All 72 experiments use:
- motion_type = sts_grf
- torque-driven actuation
- measured subject2 laboratory GRF/COP
- original HRNet 2-camera STS IK
- heel_vGRF_threshold = 0
- periodic constraints disabled
- GRF tracking weight = 0.001
- pelvis residual weight = 0.001
- maxIter = 10000

Five experimental variables:

1. Kinematic tracking weights

   Emily:
       position 1000, velocity 100, acceleration 0.1

   STS-inspired:
       position 50, velocity 10, acceleration 50

   Intermediate:
       position 200, velocity 30, acceleration 2

2. meshDensity: 25, 50, 100

3. ipopt_tolerance: 2 or 3
   Corresponding to 1e-2 or 1e-3.

4. COP objective:
   Enabled: COP weight 300, monotonic weight 0.001
   Disabled: both weights zero
   Code-level behavior must be verified before submission.

5. Simulation window:
   Original: repetition 0 from segment_STS
   Buffered: explicit [0.17, 1.81] seconds

## Controlled comparisons

To isolate one variable, compare experiments with all
other manifest columns identical except that variable.

Profile effect:
    Fix mesh, tolerance, COP and window.
    Compare Emily, STS-inspired and intermediate.

Mesh effect:
    Fix profile, tolerance, COP and window.
    Compare 25, 50 and 100.

Tolerance effect:
    Fix profile, mesh, COP and window.
    Compare tolerance settings 2 and 3.

COP effect:
    Fix profile, mesh, tolerance and window.
    Compare COP on and off.

Window effect:
    Fix profile, mesh, tolerance and COP.
    Compare original and buffered.

## Comparison with E008

E008 used:
- Emily-like tracking weights
- meshDensity 50
- IPOPT tolerance setting 3
- COP tracking enabled
- original STS window
- heel minimum 0
- no periodicity
- maxIter 5000

The corresponding sweep configuration uses 10000 iterations,
so comparison to E008 additionally tests the iteration budget.

## Evaluation rules

IPOPT status:
    Use actual solver termination message.
    HTCondor exit code alone is insufficient.

Accuracy:
    Evaluate vertical GRF RMSE for both feet over
    the common STS interval [0.47, 1.51] seconds.

Mechanical assessment:
    Inspect pelvis residual forces/moments,
    coordinate tracking errors, and contact behavior.

Visualization:
    Inspect plausible foot-floor interaction,
    joint motion, and absence of gross compensation.

A numerically converged solution is not automatically
a biomechanically valid solution.

## Reproducibility

Retain each job's:
- Manifest row and full configuration
- Runner SHA256 and code revision
- Input bundle SHA256
- HTCondor ClusterId and ProcId
- IPOPT termination and diagnostics
- Objective components
- GRF/COP errors
- Results archive and status
