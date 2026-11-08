# OpenSimAD GRF/COP Tracking for Sit-to-Stand

**Research record | October–November 2026**  
**Current decision:** E056 is the selected **provisional** STS configuration for testing on new data.  
**Validation status:** numerical screening and qualitative motion review completed; full biomechanical validation is **not yet complete**.

## What is this project?

We want to simulate a person **rising from a chair** using OpenSimAD while reproducing the experimentally measured **ground reaction forces (GRF)** and **center of pressure (COP)**.

Our question was not simply *"Can IPOPT finish the optimization?"* It was:

> **Which OpenSimAD configuration both converges numerically and gives convincing motion, force, and COP tracking during sit-to-stand?**

We built on the GRF/COP-tracking approach developed by Emily Miller for walking, adapted it for STS, investigated solver sensitivity, and selected **E056** from 72 STS configurations for the next research stage.

**A few terms:** **STS** = sit-to-stand; **GRF** = force exchanged between the foot and ground; **COP** = effective point of application of the ground reaction force; **IK** = inverse kinematics used to estimate joint motion; **IPOPT** = the nonlinear optimizer used by OpenSimAD. *"IPOPT-optimal"* describes a solver termination status, **not** proof of accurate or physiologically realistic movement.

## The investigation at a glance

| Stage | What we investigated | Main finding |
|---|---|---|
| **1. Walking baseline** | Reproduce an Emily-style walking GRF/COP-tracking run (E009) | IPOPT reached optimal termination, but visual inspection identified an initial right-foot artifact |
| **2. Walking COP-mask test** | Eight subjects, marker-derived versus force-derived COP masks (E111–E126; 16 runs) | **0/8** marker-mask cases versus **8/8** force-mask cases reached optimal IPOPT termination |
| **3. STS formulation adaptation** | Inherited heel minimum-force and lower-limb periodicity constraints; GRF/COP tracking | Disable the 5 N heel minimum-force inequality and remove inherited periodicity for our nonperiodic STS setup |
| **4. STS parameter sweep** | 72 configurations (E015–E086), changing five numerical choices | **50/72** reached optimal IPOPT termination; COP-objective settings and tolerance interacted strongly |
| **5. Candidate selection** | Compare converged cases against measured GRF/COP and inspect simulated motion | **E056** selected as the provisional baseline for additional STS trials |

This table is an overview of **separate investigations**, not a claim that the walking tests validated the STS results.

## 1. Preliminary evaluation of the walking formulation

We first tested an adapted implementation of Emily Miller's walking GRF/COP tracking approach using laboratory walking data.

**E009: walking positive control.** It used marker-derived stance information to determine which COP frames should be tracked. IPOPT converged, but a visual inspection showed an unrealistic movement of the right foot near the start. This is why we distinguish numerical convergence from biomechanical plausibility.

**E111–E126: paired COP-mask comparison.** We tested subjects 3–10 with two COP-validity-mask methods per subject:

- **Marker-derived:** infer valid COP frames from marker-derived stance information.
- **Force-derived:** use measured per-foot vertical GRF **greater than 20 N** to identify valid COP frames.

Both variants still used **marker-derived gait-event timing and stance percentages**. Only the COP validity mask was switched.

![Walking COP-mask convergence outcomes](figures/walking_cop_mask_convergence.png)

| Walking COP mask | IPOPT-optimal | Nonoptimal |
|---|---:|---:|
| Marker-derived | **0/8** | 8 (4 restoration failures, 3 step errors, 1 iteration limit) |
| Force-derived | **8/8** | 0 |

**Interpretation:** the chosen COP mask was strongly associated with solver convergence in these walking tests. It is **not** evidence that all converged walking motions were biomechanically accurate or that we exactly reproduced Emily's published results.

**Read next:** [Walking reproduction, paired experiment design, results, and limitations](docs/walking_preliminary_numerical_evaluation.md).

## 2. Adapting the formulation for sit-to-stand

OpenSimAD's original `sit_to_stand` settings were not used unchanged. In the adapted E008 STS runner, we made two important formulation decisions before the 72-case sweep:

| Setting | Inherited STS behavior | Our STS behavior | Why |
|---|---|---|---|
| **Heel vertical GRF threshold** | A **5 N minimum** on selected *modeled heel contact-sphere forces* | Set `heel_vGRF_threshold = 0`, disabling that inequality | Permit heel unloading during forward weight transfer without imposing a heel-specific minimum |
| **Lower-limb periodicity** | Force selected initial and final lower-limb coordinates to agree | Remove `periodicConstraints` | A full STS rise begins and ends in different postures |

**Important distinction:** `heel_vGRF_threshold = 0` **does not force heel GRF to zero**. In the optimization source, the inequality is imposed only when the threshold is **greater than zero**. The heel contact model still generates forces according to its dynamics.

We also used a **separate COP-validity mask** derived from **measured** vertical GRF with a **10 N** threshold in the STS runs. That 10 N criterion tells the objective *when to track measured COP*; it is **not** the modeled heel minimum-force constraint.

These formulation adaptations were **held fixed in all 72 STS runs**. Our sweep therefore does **not** isolate whether removing the heel constraint or periodicity individually improved convergence.

**Read next:** [STS formulation decisions and code evidence](docs/STS_formulation_decisions.md).

## 3. The 72-case STS parameter investigation

We used the subject 2 laboratory STS trial, OpenCap-derived kinematics and measured laboratory force/COP targets. Across experiments **E015–E086**, we varied five factors:

| Factor | Tested values |
|---|---|
| **Kinematic tracking profile** | Emily-style: **1000 / 100 / 0.1**; STS-inspired: **50 / 10 / 50**; intermediate: **200 / 30 / 2** (position / velocity / acceleration weights) |
| **Mesh density** | 25, 50, 100 |
| **IPOPT tolerance** | `1e-2`, `1e-3` |
| **COP objective** | ON or OFF (switching **both** `copTrackingTerm` and `copMonotonicTerm`) |
| **Time window** | Original or buffered |

The setup was **torque-driven**, with laboratory GRF inputs, allowed pelvis residuals, a measured-force-derived COP mask, **heel minimum = 0**, and **no inherited periodicity**.

### Numerical convergence results

**50/72 (69.4%)** STS cases reached optimal IPOPT termination. The remaining 22 terminated nonoptimally (15 iteration-limit, 7 step-computation errors). All 72 HTCondor jobs completed and transferred result archives; **HTCondor completion is not the same as IPOPT convergence**.

![STS COP objective and tolerance convergence](figures/sts_cop_tolerance_convergence.png)

| COP objective | Tolerance `1e-2` | Tolerance `1e-3` | Total |
|---|---:|---:|---:|
| **ON** | **14/18** optimal | **0/18** optimal | 14/36 |
| **OFF** | **18/18** optimal | **18/18** optimal | 36/36 |

**What this means:** disabling the combined COP objective made optimal solver termination more reliable in **this** experiment. But an easier-to-solve problem does not necessarily yield better COP tracking. And because the COP switch changes two objective terms together, these results cannot identify which individual term produced the effect.

**Tolerance example:** E056 (`1e-2`, COP ON) reached optimal termination after **541 iterations**; otherwise matched E060 (`1e-3`, COP ON) continued to **8,144 iterations** and terminated nonoptimally. Their plotted primal/dual infeasibility histories overlap through iteration 541. These traces illustrate sensitivity to the stopping tolerance; they do not prove a particular underlying numerical failure mechanism.

## 4. Why we selected E056

We compared force/COP predictions against laboratory measurements on a **common 0.47–1.47 s interval** (53 points) and visually compared selected motion trajectories with laboratory MoCap-derived IK. This is the **screening interval**, not the full E056 simulation window.

E056 ranked first under our provisional combined screening criterion (GRF 60%, COP 30%, vertical free moment 10%). That weighting is a **research heuristic**, not an independently validated biomechanical standard.

| E056 setting | Value |
|---|---|
| Tracking profile (position / velocity / acceleration) | **50 / 10 / 50** |
| Mesh density | **100** |
| IPOPT tolerance | **`1e-2`** |
| Maximum iterations | **10,000** |
| COP tracking / COP monotonic weights | **300 / 0.001** (ON) |
| GRF tracking weight | **0.001** |
| Heel minimum-force constraint | **Disabled (`heel_vGRF_threshold = 0`)** |
| COP validity mask | **Measured-force-derived, 10 N** |
| Periodicity | **Disabled** |
| Original E056 buffered time window | **0.17–1.81 s** |

**Screening errors for E056** (common 0.47–1.47 s interval):

| Metric | Result |
|---|---:|
| Bilateral 3D GRF RMSE | **10.01 N** |
| Bilateral 2D COP RMSE | **19.18 mm** |
| Vertical free-moment RMSE | **2.51 N·m** |

The visual inspection of E056, E032, and E058 suggested all three were close to the reference IK motion; E058 had a small end-frame artifact. **These tracking-error metrics use measured targets that were also involved in optimization.** They are not independent validation or proof that E056 is the best choice for all participants.

**Read next:** [E056 selection, paired comparisons, tolerance findings, and remaining limitations](docs/E056_selection_2026-11-08.md).

## 5. What is complete—and what is not?

| Evaluation | Current status |
|---|---|
| Experiment submission and solver-status audit | **Complete:** 72 STS and 16 paired walking jobs checked |
| STS force/COP screening | **Complete for all 72** on the documented common interval |
| E056 configuration selection and archival | **Complete:** provisional baseline selected |
| Visual review of shortlisted STS motions | **Preliminary qualitative review completed** |
| Full-window quantitative IK validation | **Not complete** |
| Contact/foot-drift checks and pelvis residual assessment | **Not complete** |
| Independent biomechanics and muscle-force validation | **Not complete** |
| Demonstrated transfer of E056 to a new STS dataset | **Not yet established** |

An *optimal* IPOPT exit is only one requirement. Before downstream inverse dynamics and muscle-force estimation, we still need credible joint motion, contact mechanics, residual loads, and time/coordinate alignment.

## 6. Reusing E056 for a new STS trial

Our next step is to use E056 as a **starting configuration**, not as a universally validated preset. Retain the numerical baseline initially, but regenerate each new trial's subject-specific model, kinematics, measured force inputs, COP mask, time window, and initial conditions.

Start with the [new-trial adaptation and validation checklist](docs/apply_E056_to_new_STS.md). The [E056 JSON configuration](configs/E056_selected_config.json) stores requested and effective settings, but **is a reference snapshot, not an executable config loader by itself**. Confirm that the actual runner applies each setting.

## Where to find the files

| Location | Contents |
|---|---|
| [`docs/`](docs/) | Explanations, walking study, heel/periodicity decisions, E056 selection and validation checklist |
| [`configs/E056_selected_config.json`](configs/E056_selected_config.json) | Selected E056 numerical configuration and source provenance |
| [`data/`](data/) | Summary CSVs for the original October audit (including transcribed walking outcomes) |
| [`scripts/`](scripts/) | 72-run GRF/COP screening, parameter-importance analysis, IPOPT tolerance diagnostics, and summary tools |
| [`source/opensimad_source_snapshot/`](source/opensimad_source_snapshot/) | Preserved example runners, batch files, and original experiment manifests/outcome records |
| [`figures/`](figures/) | Summary plots of STS convergence and walking COP-mask convergence |
| [`docs/provenance.md`](docs/provenance.md) | CHTC job identifiers, archive/source records, and historical audit scope |

**For the original October audit only**, run from this directory:

```bash
python3 scripts/rebuild_summary.py
```

The historical `data/` summaries reflect an October 12 transcription and reconstructed design; the later screening and detailed source manifests are preserved separately. Do not confuse historical audit scope with later analysis completion. Source runner versions and CHTC result archives remain the authority for exact reproduction.

## Reproducibility and data boundaries

This is a **research record**, not a self-contained package that can reproduce every simulation without the corresponding inputs, OpenSimAD environment, and dependencies. The original trial data and full result archives are **not** committed here; they remain in institutional storage or the research workspace and need an approved backup independent of CHTC.

The repository is public. **Do not commit** raw participant videos/markers/force recordings, identifiable subject files, full research archives, credentials or `.env` files, or licensed papers. Preserve redistribution permissions for third-party source code.

**Historical note:** proposed E010–E014 and E087–E110 were not submitted in the documented closeout.
