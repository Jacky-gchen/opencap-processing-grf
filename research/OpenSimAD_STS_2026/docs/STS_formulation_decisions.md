# STS formulation adaptations made before the 72-case sweep

**Purpose:** document the modeling/constraint decisions that preceded the E015–E086 parameter sweep. These were *fixed assumptions* during the sweep, not additional factorial variables.

## 1. Inherited heel vertical-force minimum

The `sit_to_stand` preset in `UtilsDynamicSimulations/OpenSimAD/settingsOpenSimAD.py` sets:

```python
'heel_vGRF_threshold': 5
```

The `sts_grf` preset is initialized by deep-copying `sit_to_stand`, so this setting is inherited unless explicitly overridden. In `mainOpenSimAD.py`, a **strictly positive** threshold triggers an inequality constraint on the model's selected heel-contact-sphere vertical reaction force(s) at the relevant collocation points:

```python
if heel_vGRF_threshold > 0:
    vGRFk = Tk[idx_vGRF_heel]
    opti.subject_to(vGRFk > heel_vGRF_threshold)
```

Thus, the 5 N setting is a **hard numerical constraint on selected heel-sphere forces**, not a penalty weight and not a threshold on the total foot GRF. It was intended to encourage heel-ground contact. During an STS rise, forward weight transfer may temporarily reduce heel loading without implying that the entire foot has lost ground contact. Enforcing this minimum continuously may therefore be unnecessarily restrictive, although we have not isolated its effect in a controlled experiment.

The E008 adapted STS runner explicitly changed:

```python
settings['heel_vGRF_threshold'] = 0
```

**Code-level consequence:** when set to zero, the `if heel_vGRF_threshold > 0` branch is skipped; this *disables the inherited heel minimum-force inequality*. It **does not** impose `F_heel = 0`, guarantee a planted foot, or turn off the modeled contact forces. It also does not automatically disable any separate nonpenetration/contact geometry requirements.

The E015–E086 sweep preserved `heel_vGRF_threshold = 0` for all 72 experiments, including selected E056. Accordingly, the sweep **cannot estimate the isolated effect** of changing 5 N to 0 N on IPOPT convergence, GRF/COP accuracy, or foot drift.

## 2. Remove inherited STS periodicity

The original `sit_to_stand` preset includes `periodicConstraints: {'coordinateValues': ['lowerLimbJoints']}`. E008 removed the inherited setting with `settings.pop('periodicConstraints', None)`; this removal was also fixed for all 72 experiments.

For a full sit-to-stand rise, starting and ending limb postures are different, so equality of initial and final lower-limb coordinates is not generally a defensible boundary condition. Disabling this inherited periodicity is therefore a formulation decision—not proof, from the 72-case sweep, that it independently caused convergence improvement.

## 3. Keep the heel constraint distinct from COP validity masking

The E008/E056 COP mask is constructed by `getCOP_masks(measured_force_file, threshold=10)`. It uses **measured vertical GRF** to decide which frames have a reliable COP tracking target.

| Setting | Uses | Numerical role | E056 value |
|---|---|---|---|
| `heel_vGRF_threshold` | **Predicted** selected heel-sphere vertical contact force | If > 0, impose a hard lower-bound constraint | **0 N (constraint disabled)** |
| `getCOP_masks(..., threshold=10)` | **Measured** per-foot vertical GRF | Gate whether COP tracking contributes to the objective | **10 N** |
| `copTrackingTerm` | Difference between predicted and measured COP during valid frames | Weighted tracking objective | **300** |

Do **not** conflate the two thresholds, and do not call the 0 N setting a COP masking method.

## 4. What changed, and when?

1. **Original `sit_to_stand` preset:** heel minimum 5 N; inherited lower-limb periodicity.
2. **STS hybrid E008 adaptation:** combine GRF/COP tracking with the torque-driven STS formulation; override heel minimum to zero; remove inherited periodicity; use a measured-force-derived COP mask at 10 N.
3. **STS sweep E015–E086:** hold the above adaptation fixed while varying (a) kinematic tracking profile, (b) mesh density, (c) IPOPT tolerance, (d) combined COP tracking/monotonic objective enabled or disabled, and (e) time window.
4. **E056 selected:** STS-inspired 50/10/50 tracking weights, mesh 100, tolerance 0.01, COP tracking enabled, buffered STS window. See [the E056 configuration](../configs/E056_selected_config.json).

## 5. What our study supports, and does not support

**Supported:** the original `sit_to_stand` code contains a 5 N heel constraint; the adapted runner explicitly disables it; the effective E056 metadata confirms 0 N; the selected E056 tracks the supplied force/COP targets well in our short-window screening.

**Not established:** that the 5 N heel constraint was the primary cause of early failures, that removal alone improves convergence, or that 0 N is always the best choice for a new subject. Those claims require a controlled `heel_vGRF_threshold = 5` versus `0` comparison with other settings held constant and inspection of resulting contact mechanics.

## Source traceability

- `UtilsDynamicSimulations/OpenSimAD/settingsOpenSimAD.py`: original heel=5 and `periodicConstraints`, followed by `sts_grf = copy.deepcopy(setups['sit_to_stand'])`.
- `UtilsDynamicSimulations/OpenSimAD/mainOpenSimAD.py`: conditionally imposed heel reaction constraint (`if heel_vGRF_threshold > 0`).
- [Archived E008 runner](../source/opensimad_source_snapshot/runners/run_E008.py): explicit heel=0 and periodicity removal.
- [Archived 72-case runner](../source/opensimad_source_snapshot/runners/run_sts_sweep.py): fixes the same decisions in the sweep.
- [Selected E056 effective configuration](../configs/E056_selected_config.json): confirms the carried-forward settings.

**Data policy:** this note contains no subject-level time series, markers, or proprietary recordings. Preserve original CHTC results separately in approved institutional storage.
