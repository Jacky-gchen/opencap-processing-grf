#!/usr/bin/env python3
"""Read-only force/COP screening for completed E015..E086 STS CHTC jobs.

Requires the original ~/sts_sweep_v1 manifests/results and the previous
~/prepare_sts72.py parser. Writes ONLY into a new analysis output folder.

This is a target-tracking QA screen, NOT independent biomechanics validation.
Input force files must be checked for synchronization, axes, signs, and units.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import tarfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from prepare_sts72 import read_mot, interp
except ImportError as e:
    raise SystemExit('Missing ~/prepare_sts72.py: copy the previous toolkit script into the same folder as this script') from e

EPS = 1e-7
STEPS = 52  # 0.47 to 1.51, inclusive, at exactly 0.02 s (53 samples)


def csvrows(p):
    with p.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv(p, rows, keys=None):
    if keys is None:
        keys = list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def one_blob(tf, members, predicate, desc):
    found = [x for x in members if x.isfile() and predicate(x.name)]
    if len(found) != 1:
        raise ValueError(f'{desc}: expected one matching file, found {len(found)}')
    fp = tf.extractfile(found[0])
    if fp is None:
        raise ValueError(f'{desc}: cannot extract {found[0].name}')
    return fp.read()


def finite(x):
    return isinstance(x, (int,float)) and math.isfinite(x)


def mean(x):
    return sum(x)/len(x) if x else math.nan


def rms(x):
    return math.sqrt(sum(v*v for v in x)/len(x)) if x else math.nan


def stdev_population(x):
    b = mean(x)
    return rms([v-b for v in x]) if x else math.nan


def sample(d, col, times):
    if col not in d:
        raise ValueError(f'Missing force column {col!r}; available: {", ".join(d.keys())}')
    t, y = d['time'], d[col]
    if len(t) != len(y) or any(t[i] >= t[i+1] for i in range(len(t)-1)):
        raise ValueError(f'Nonmonotonic or invalid times for column {col}')
    if t[0] > times[0] + EPS or t[-1] < times[-1] - EPS:
        raise ValueError(f'Incomplete time coverage {t[0]:.5f}..{t[-1]:.5f} for {times[0]:.5f}..{times[-1]:.5f}')
    # Snap tiny (1e-7) endpoint rounding differences before interpolation.
    q = [max(t[0], min(t[-1], x)) for x in times]
    out = [interp(t,y,x) for x in q]
    if not all(finite(v) for v in out):
        raise ValueError(f'Nonfinite interpolated data in column {col}')
    return out


def metrics(pred, measured):
    err = [x-y for x,y in zip(pred,measured)]
    return {'rmse': rms(err), 'bias':mean(err), 'maxabs':max(map(abs,err))}


def screen_one(p, r, times, threshold):
    """Keep all comparisons on same fixed time grid; do not cherry-pick times."""
    P, R = {}, {}
    for side, label in [('right','R'),('left','L')]:
        P[side] = {}
        R[side] = {}
        for axis in 'xyz':
            P[side][f'f{axis}'] = sample(p,f'ground_force_{side}_v{axis}',times)
            R[side][f'f{axis}'] = sample(r,f'{label}_ground_force_v{axis}',times)
        for axis in 'xz':
            P[side][f'p{axis}'] = sample(p,f'ground_force_{side}_p{axis}',times)
            R[side][f'p{axis}'] = sample(r,f'{label}_ground_force_p{axis}',times)
        P[side]['ty'] = sample(p,f'ground_torque_{side}_y',times)
        R[side]['ty'] = sample(r,f'{label}_ground_torque_y',times)
    result = {}
    result['ComparisonSamples'] = len(times)
    result['PredTimeStart'] = p['time'][0]
    result['PredTimeEnd'] = p['time'][-1]
    side_vector = {}
    for side in ('right','left'):
        prefix = 'R' if side == 'right' else 'L'
        errors = []
        for axis in 'xyz':
            v = metrics(P[side][f'f{axis}'],R[side][f'f{axis}'])
            result[f'{prefix}_F{axis.upper()}_RMSE_N'] = round(v['rmse'],6)
            result[f'{prefix}_F{axis.upper()}_Bias_N'] = round(v['bias'],6)
            errors += [(x-y)**2 for x,y in zip(P[side][f'f{axis}'],R[side][f'f{axis}'])]
        # Vector RMSE: sqrt(mean_t [dx²+dy²+dz²]), not per-component RMS.
        side_vector[side] = math.sqrt(sum(errors)/len(times))
        result[f'{prefix}_GRF_VectorRMSE_N'] = round(side_vector[side],6)
        measured_loaded = [y > threshold for y in R[side]['fy']]
        valid = [m and p > threshold for m,p in zip(measured_loaded,P[side]['fy'])]
        nload, nvalid = sum(measured_loaded),sum(valid)
        result[f'{prefix}_MeasuredLoadedSamples'] = nload
        result[f'{prefix}_COPValidSamples'] = nvalid
        result[f'{prefix}_COPCoverageFraction'] = round(nvalid/nload,5) if nload else None
        for axis in 'xz':
            err = [(x-y)*1000 for x,y,keep in zip(P[side][f'p{axis}'],R[side][f'p{axis}'],valid) if keep]
            result[f'{prefix}_COP{axis.upper()}_RMSE_mm'] = round(rms(err),6) if err else None
            result[f'{prefix}_COP{axis.upper()}_Bias_mm'] = round(mean(err),6) if err else None
            result[f'{prefix}_COP{axis.upper()}_DemeanedRMSE_mm'] = round(stdev_population(err),6) if err else None
        free_torque_err = [x-y for x,y,keep in zip(P[side]['ty'],R[side]['ty'],valid) if keep]
        result[f'{prefix}_FreeMomentY_RMSE_Nm'] = round(rms(free_torque_err),6) if free_torque_err else None
    # Bilateral vector error preserves errors that would cancel when summing feet.
    result['BilateralGRF_VectorRMSE_N'] = round(math.sqrt((side_vector['right']**2+side_vector['left']**2)/2),6)
    for axis in 'xyz':
        pred = [x+y for x,y in zip(P['right'][f'f{axis}'],P['left'][f'f{axis}'])]
        ref = [x+y for x,y in zip(R['right'][f'f{axis}'],R['left'][f'f{axis}'])]
        v = metrics(pred,ref)
        result[f'TotalF{axis.upper()}_RMSE_N'] = round(v['rmse'],6)
        result[f'TotalF{axis.upper()}_Bias_N'] = round(v['bias'],6)
    result['TotalGRF_VectorRMSE_N'] = round(math.sqrt(sum(result[f'TotalF{a}_RMSE_N']**2 for a in 'XYZ')),6)
    total_ref_y = [x+y for x,y in zip(R['right']['fy'],R['left']['fy'])]
    total_pred_y = [x+y for x,y in zip(P['right']['fy'],P['left']['fy'])]
    force_ref_peak = max(total_ref_y)
    result['MeasuredPeakTotalVertical_N'] = round(force_ref_peak,6)
    result['BilateralGRF_RMSE_PctPeak'] = round(100*result['BilateralGRF_VectorRMSE_N']/force_ref_peak,6) if force_ref_peak>0 else None
    def impulse(x):
        return sum((times[i+1]-times[i])*(x[i]+x[i+1])/2 for i in range(len(times)-1))
    result['TotalVerticalImpulseError_Ns'] = round(impulse(total_pred_y)-impulse(total_ref_y),6)
    # COP scalar is bilateral, 2D position vector error over valid frames per foot.
    squared=[]
    for side in ('right','left'):
        valid = [ry > threshold and py > threshold for ry,py in zip(R[side]['fy'],P[side]['fy'])]
        for x,z,rx,rz,keep in zip(P[side]['px'],P[side]['pz'],R[side]['px'],R[side]['pz'],valid):
            if keep: squared.append((1000*(x-rx))**2+(1000*(z-rz))**2)
    result['BilateralCOP_2D_RMSE_mm'] = round(math.sqrt(mean(squared)),6) if squared else None
    torque_sq=[]
    for side in ('right','left'):
        valid = [ry > threshold and py > threshold for ry,py in zip(R[side]['fy'],P[side]['fy'])]
        torque_sq += [(x-y)**2 for x,y,keep in zip(P[side]['ty'],R[side]['ty'],valid) if keep]
    result['BilateralFreeMomentY_RMSE_Nm'] = round(math.sqrt(mean(torque_sq)),6) if torque_sq else None
    if '3_ground_force_vy' in r:
        third = sample(r,'3_ground_force_vy',times)
        result['ThirdPlateMaxAbsFy_N'] = round(max(map(abs,third)),6)
    return result


def pctranks(rows, metric):
    """Compute rank percentiles only among eligible optimal candidates; 0 is best."""
    good=sorted([(float(row[metric]),i) for i,row in enumerate(rows) if finite(row.get(metric))])
    if len(good)<2:
        return {i:0.0 for _,i in good}
    # Tie-aware: equal values share their average rank.
    ans={}
    j=0
    while j<len(good):
        k=j+1
        while k<len(good) and abs(good[k][0]-good[j][0])<1e-10:
            k+=1
        rank = (((j+k-1)/2)/(len(good)-1))
        for _,i in good[j:k]:ans[i]=rank
        j=k
    return ans


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path.home()/'sts_sweep_v1')
    ap.add_argument('--out',type=Path,default=Path.home()/'sts72_validation_review'/'qa_72_all')
    ap.add_argument('--start',type=float,default=0.47)
    ap.add_argument('--end',type=float,default=1.51)
    ap.add_argument('--load-threshold',type=float,default=20.0)
    ap.add_argument('--min-cop-coverage',type=float,default=0.90)
    args=ap.parse_args()
    if not (args.end>args.start and 0<=args.min_cop_coverage<=1):
        ap.error('Invalid analysis interval or COP coverage fraction')
    root,out=args.root.expanduser(),args.out.expanduser()
    manifest_path=root/'sts_sweep_manifest.csv'
    outcome_path=root/'sts_sweep_outcomes.csv'
    for p in (manifest_path,outcome_path):
        if not p.is_file(): raise SystemExit(f'Missing {p}')
    manifest=csvrows(manifest_path)
    outcomes=csvrows(outcome_path)
    byid={r['ID']:r for r in manifest}
    status={r['ID']:r for r in outcomes}
    expected={f'E{i:03d}' for i in range(15,87)}
    if not expected.issubset(byid):raise SystemExit(f'Manifest missing IDs: {sorted(expected-set(byid))}')
    if not expected.issubset(status):raise SystemExit(f'Outcomes missing IDs: {sorted(expected-set(status))}')
    if any(sum(r['ID']==eid for r in manifest) != 1 for eid in expected):
        raise SystemExit('Manifest has duplicate or missing experiment IDs')
    if any(sum(r['ID']==eid for r in outcomes) != 1 for eid in expected):
        raise SystemExit('Outcomes CSV has duplicate or missing experiment IDs')
    times=[round(args.start+(args.end-args.start)*i/STEPS,10) for i in range(STEPS+1)]
    out.mkdir(parents=True, exist_ok=True)
    rows=[]
    ref_hashes=Counter()
    for j in range(15,87):
        eid=f'E{j:03d}'
        c=byid[eid]; o=status[eid]
        optimal='Optimal Solution Found' in o.get('Status','') and 'Converged' in o.get('Status','')
        rec={
            'ID':eid,'Profile':c.get('profile',''),'MeshDensity':c.get('meshDensity',''),
            'IPOPTTolerance':c.get('ipopt_tolerance_value',''),'COPObjectiveON':c.get('COP_objective_enabled',''),
            'TimeWindow':c.get('window',''),'PositionWeight':c.get('positionTrackingTerm',''),
            'VelocityWeight':c.get('velocityTrackingTerm',''),'AccelerationWeight':c.get('accelerationTrackingTerm',''),
            'GRFWeight':c.get('grfTrackingTerm',''),'COPWeight':c.get('copTrackingTerm',''),
            'IPOPTStatus':o.get('Status',''),'IPOPTOptimal':optimal,'Iterations':o.get('Iterations',''),
            'ScaledNLPError':o.get('ScaledNLPError',''),'HTCondorJob':o.get('Cluster',''),
            'Archive':str(root/'results'/f'{eid}_results.tar.gz'),
            'MetricStatus':'NOT_CALCULATED','Issue':'','BestCandidateRank':'',
            'CompositeScreenScore':'','ViewerModel':f'groups/profile-{c.get("profile")}_mesh-{c.get("meshDensity")}/viewer/{eid}_model.osim',
            'ViewerMotion':f'groups/profile-{c.get("profile")}_mesh-{c.get("meshDensity")}/viewer/{eid}_motion.mot'
        }
        archive=root/'results'/f'{eid}_results.tar.gz'
        try:
            with tarfile.open(archive,'r:gz') as tf:
                mem=tf.getmembers()
                predbytes=one_blob(tf,mem,lambda n:n.endswith(f'GRF_resultant_STS1_{eid}_torqueDriven_STS.mot'),'predicted resultant GRF')
                refbytes=one_blob(tf,mem,lambda n:n.endswith('/ForceData/STS1_forces.mot'),'measured GRF')
                motions=[m for m in mem if m.isfile() and m.name.endswith(f'kinematics_activations_STS1_{eid}_torqueDriven_STS.mot')]
                rec['MotionSHA256'] = sha(tf.extractfile(motions[0]).read()) if len(motions)==1 else ''
                rec['MotionPresent'] = len(motions)==1
                rec['PredGRFSHA256']=sha(predbytes)
                rec['MeasuredRefSHA256']=sha(refbytes)
                ref_hashes[rec['MeasuredRefSHA256']]+=1
                pred=read_mot(predbytes)
                ref=read_mot(refbytes)
                rec.update(screen_one(pred,ref,times,args.load_threshold))
                rec['MetricStatus']='OK'
        except Exception as exc:
            rec['MetricStatus']='ERROR'
            rec['Issue']=str(exc)[:450]
        rows.append(rec)
        print(f'{eid}: {"OPT" if optimal else "NONOPT"} | {rec["MetricStatus"]} | '
              f'GRF={rec.get("BilateralGRF_VectorRMSE_N", "n/a")} N | '
              f'COP={rec.get("BilateralCOP_2D_RMSE_mm","n/a")} mm')
    # Identify exact duplicate exported motions, including distinct tolerances.
    by_motion = defaultdict(list)
    for row in rows:
        if row.get('MotionSHA256'):
            by_motion[row['MotionSHA256']].append(row['ID'])
    duplicates = []
    for digest, ids in sorted(by_motion.items()):
        if len(ids)>1:
            duplicates.append({'MotionSHA256':digest, 'ExperimentIDs':';'.join(ids), 'Count':len(ids)})
            for row in rows:
                if row['ID'] in ids:
                    row['IdenticalMotionIDs'] = ';'.join(x for x in ids if x != row['ID'])
    write_csv(out/'exact_duplicate_motions.csv',duplicates,
              ['MotionSHA256','ExperimentIDs','Count'])
    # Never rank across non-identical reference-force data.
    consistent_reference=len(ref_hashes)==1
    eligible=[]
    for row in rows:
        if row['MetricStatus']!='OK' or not row['IPOPTOptimal'] or not consistent_reference:
            continue
        if row.get('MotionPresent') is not True:
            continue
        if any(not finite(row.get(x)) for x in (
            'BilateralGRF_VectorRMSE_N','BilateralCOP_2D_RMSE_mm',
            'BilateralFreeMomentY_RMSE_Nm','R_COPCoverageFraction','L_COPCoverageFraction')):
            continue
        if min(row['R_COPCoverageFraction'],row['L_COPCoverageFraction']) < args.min_cop_coverage:
            continue
        if row.get('ThirdPlateMaxAbsFy_N',0)>20:
            continue
        eligible.append(row)
    # SCREEN-ONLY, rank percentiles: force 60%, COP 30%, free moment 10%.
    # Do NOT interpret this as a validated physics objective or clinical score.
    ranks={m:pctranks(eligible,m) for m in (
        'BilateralGRF_VectorRMSE_N','BilateralCOP_2D_RMSE_mm','BilateralFreeMomentY_RMSE_Nm')}
    for idx,row in enumerate(eligible):
        val=(0.60*ranks['BilateralGRF_VectorRMSE_N'][idx]
             +0.30*ranks['BilateralCOP_2D_RMSE_mm'][idx]
             +0.10*ranks['BilateralFreeMomentY_RMSE_Nm'][idx])
        row['CompositeScreenScore']=round(val,6)
    eligible.sort(key=lambda x:(x['CompositeScreenScore'],x['BilateralGRF_VectorRMSE_N']))
    for i,row in enumerate(eligible,1):row['BestCandidateRank']=i
    data_out=out/'all_72_metrics.csv'
    write_csv(data_out,rows)
    write_csv(out/'eligible_ranked.csv',eligible)
    write_csv(out/'nonoptimal_or_incomplete.csv',[x for x in rows if x not in eligible])
    # Baseline top 10 and ensure every weight profile has a representative if possible.
    chosen=[]
    seen_motion=set()
    for row in eligible:
        hashval=row.get('MotionSHA256')
        if hashval and hashval in seen_motion:
            continue
        chosen.append(row)
        if hashval: seen_motion.add(hashval)
        if len(chosen)>=10: break
    for profile in sorted(set(r['Profile'] for r in eligible)):
        profile_winners=[r for r in eligible if r['Profile']==profile]
        if profile_winners and all(r['Profile']!=profile for r in chosen):
            chosen.append(profile_winners[0])
    write_csv(out/'visualization_shortlist.csv',chosen)
    pairs=[]
    # Like-for-like COP ON/OFF and tolerance comparisons; do not conflate factor changes.
    index={(r['Profile'],r['MeshDensity'],r['IPOPTTolerance'],r['TimeWindow'],str(r['COPObjectiveON']).lower()):r for r in rows}
    for r in rows:
        if str(r['COPObjectiveON']).lower() in ('true','1','yes'):
            s=index.get((r['Profile'],r['MeshDensity'],r['IPOPTTolerance'],r['TimeWindow'],'false'))
            if s:
                pairs.append({'PairType':'COP ON vs OFF','A':r['ID'],'B':s['ID'],
                              'Profile':r['Profile'],'Mesh':r['MeshDensity'],'Tolerance':r['IPOPTTolerance'],'Window':r['TimeWindow'],
                              'AOptimal':r['IPOPTOptimal'],'BOptimal':s['IPOPTOptimal'],
                              'A_ForceRMSE_N':r.get('BilateralGRF_VectorRMSE_N',''),
                              'B_ForceRMSE_N':s.get('BilateralGRF_VectorRMSE_N',''),
                              'A_COP_RMSE_mm':r.get('BilateralCOP_2D_RMSE_mm',''),
                              'B_COP_RMSE_mm':s.get('BilateralCOP_2D_RMSE_mm','')})
    for r in rows:
        if abs(float(r['IPOPTTolerance'])-0.01)<1e-8:
            target=index.get((r['Profile'],r['MeshDensity'],'0.001',r['TimeWindow'],str(r['COPObjectiveON']).lower()))
            if target:
                pairs.append({'PairType':'1e-2 vs 1e-3','A':r['ID'],'B':target['ID'],
                              'Profile':r['Profile'],'Mesh':r['MeshDensity'],'Tolerance':'pair','Window':r['TimeWindow'],
                              'AOptimal':r['IPOPTOptimal'],'BOptimal':target['IPOPTOptimal'],
                              'A_ForceRMSE_N':r.get('BilateralGRF_VectorRMSE_N',''),
                              'B_ForceRMSE_N':target.get('BilateralGRF_VectorRMSE_N',''),
                              'A_COP_RMSE_mm':r.get('BilateralCOP_2D_RMSE_mm',''),
                              'B_COP_RMSE_mm':target.get('BilateralCOP_2D_RMSE_mm','')})
    write_csv(out/'controlled_pairs.csv',pairs)
    # Convergence per factor, no suggestion of causal main effects from marginal counts.
    stats=[]
    for factor in ('Profile','MeshDensity','IPOPTTolerance','COPObjectiveON','TimeWindow'):
        for value in sorted(set(str(r[factor]) for r in rows)):
            rs=[r for r in rows if str(r[factor])==value]
            stats.append({'Factor':factor,'Level':value,'N':len(rs),
                          'Optimal':sum(r['IPOPTOptimal'] for r in rs),
                          'OptimalPercent':round(100*sum(r['IPOPTOptimal'] for r in rs)/len(rs),2),
                          'MetricsOK':sum(r['MetricStatus']=='OK' for r in rs)})
    write_csv(out/'factor_summary.csv',stats)
    metadata={
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'input_manifest_sha256':sha(manifest_path.read_bytes()),
        'input_outcomes_sha256':sha(outcome_path.read_bytes()),
        'input_root':str(root),
        'window_start_s':args.start,'window_end_s':args.end,'samples':len(times),
        'sampling_dt_s':(args.end-args.start)/STEPS,
        'vertical_direction':'Y assumed','horizontal_directions':['X','Z'],
        'measured_vertical_threshold_N':args.load_threshold,
        'cop_coverage_requirement':args.min_cop_coverage,
        'measured_reference_hashes':dict(ref_hashes),
        'same_measured_reference_for_all_readable_archives':consistent_reference,
        'total_experiments':len(rows),
        'solver_optimal':sum(r['IPOPTOptimal'] for r in rows),
        'force_metrics_OK':sum(r['MetricStatus']=='OK' for r in rows),
        'eligible_for_preliminary_ranking':len(eligible),
        'exact_duplicate_motion_groups':len(duplicates),
        'screen_weighting':'rank percentile: 60% bilateral 3D GRF RMSE; 30% bilateral 2D COP RMSE; 10% bilateral vertical free moment RMSE; lower better',
        'scope':'Tracking-target agreement in one trial, not independent validation; excludes foot sliding and pelvis residual assessment',
        'limitations':['Force axes, coordinate frame, sign, units and synchronization require verification',
                       'COP/free moment terms are part of optimized target; not out-of-sample validation',
                       'Nonoptimal simulations are never eligible for candidate rank',
                       'Force error alone does not validate pelvis residuals, foot contact or muscle static optimization',
                       'Time-window comparisons use common 0.47-1.51s only; buffered behavior outside is not evaluated']}
    (out/'method_and_provenance.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    lines=[
        'OpenSimAD E015-E086: ALL 72 force/COP screening',
        '=============================================',
        f'IPOPT optimal: {metadata["solver_optimal"]}/72',
        f'Force/COP metrics available: {metadata["force_metrics_OK"]}/72',
        f'Measured force identical across readable archives: {consistent_reference}',
        f'Eligible converged candidates (>= {100*args.min_cop_coverage:.0f}% COP valid frames/foot): {len(eligible)}',
        f'Groups of byte-identical exported motions: {len(duplicates)}',
        f'Fixed grid: {args.start} to {args.end} s, {len(times)} points, dt={(args.end-args.start)/STEPS:.4f} s',
        '',
        'Top preliminary candidates (NOT independently biomechanically validated):',
    ]
    if not eligible:
        lines.append('  NONE: inspect all_72_metrics.csv Issue, MetricStatus, and reference SHA flags.')
    else:
        lines.append('Rank   ID     Profile        Mesh  Tol    COP    Window      Bilat 3D GRF N   Bilat COP mm  Free M Nm')
        for r in eligible[:12]:
            lines.append(f'{r["BestCandidateRank"]:>4}   {r["ID"]:5}  {r["Profile"][:13]:13} {r["MeshDensity"]:>4}  '
                         f'{r["IPOPTTolerance"]:>5}  {str(r["COPObjectiveON"]):>5}  {r["TimeWindow"]:9} '
                         f'{r["BilateralGRF_VectorRMSE_N"]:>14.2f}  {r["BilateralCOP_2D_RMSE_mm"]:>12.2f}  '
                         f'{r["BilateralFreeMomentY_RMSE_Nm"]:>9.2f}')
    lines += ['', 'REQUIRED BEFORE STATIC OPTIMIZATION:',
              'Verify force frames and signs, inspect animations, quantify stance-foot drift,',
              'check residual pelvis forces/moments and resulting inverse-dynamics moments.',
              'The ranking only reflects fit to the same measured tracking targets.',
              '',f'Output folder: {out}']
    (out/'README_RESULTS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'+'\n'.join(lines))


if __name__=='__main__':
    main()
