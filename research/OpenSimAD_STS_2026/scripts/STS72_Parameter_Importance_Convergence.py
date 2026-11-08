#!/usr/bin/env python3
"""Read-only STS72 factorial parameter analysis + IPOPT iteration-log screening.

Inputs: ~/sts72_validation_review/qa_72_common_147/all_72_metrics.csv,
        original ~/sts_sweep_v1/results/E###_results.tar.gz (optional for logs),
        stdout logs named with experiment IDs in ~/sts_sweep_v1 or --log-dir.
Outputs: CSV, SVG and notes only in --out; no simulation or archive is altered.

CAUTION: An IPOPT iteration trace is available only if original per-iteration
stdout is preserved. Final result MOT files/solver summaries cannot recover it.
"""
from __future__ import annotations
import argparse, csv, math, re, tarfile, statistics, html, gzip
from pathlib import Path
from collections import defaultdict

F = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
ROW = re.compile(r'^\s*(\d+)(r?)\s+('+F+r')\s+('+F+r')\s+('+F+r')(?:\s+|$)')
HEADER = re.compile(r'\biter\s+objective\s+inf_pr\s+inf_du\b', re.I)
LEVELS = {
    'COPObjectiveON': ['False','True'],
    'IPOPTTolerance': ['0.01','0.001'],
    'TimeWindow': ['original','buffered'],
    'MeshDensity': ['25','50','100'],
    'Profile': ['emily','intermediate','sts_inspired'],
}
LABELS = {'COPObjectiveON':'COP objective', 'IPOPTTolerance':'IPOPT tolerance',
          'TimeWindow':'Window', 'MeshDensity':'Mesh density', 'Profile':'Tracking profile'}
KEYS = list(LEVELS)
M = ['BilateralGRF_VectorRMSE_N','BilateralCOP_2D_RMSE_mm',
     'BilateralFreeMomentY_RMSE_Nm']
MATCH_PAIRS = {
    'COPObjectiveON':[('False','True')],
    'IPOPTTolerance':[('0.01','0.001')],
    'TimeWindow':[('original','buffered')],
    'MeshDensity':[('25','50'),('50','100'),('25','100')],
    'Profile':[('emily','sts_inspired'),('emily','intermediate'),('intermediate','sts_inspired')],
}
FEATURED = [('E017','E021'),('E018','E022'),('E056','E060'),
            ('E058','E062'),('E032','E036'),('E080','E084')]

def load_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))
def write_csv(path, items, keys=None):
    if keys is None:
        keys = list(dict.fromkeys(k for d in items for k in d))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(items)
def num(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError): return None
def fmt(v,precision=3):
    return f'{v:.{precision}f}' if v is not None else 'NA'
def median(xs):
    xs=[x for x in xs if x is not None]
    return statistics.median(xs) if xs else None
def norm(key,v):
    v=str(v).strip()
    if key=='COPObjectiveON': return 'True' if v.lower() in ('true','1','yes') else 'False'
    if key=='IPOPTTolerance': return '0.01' if num(v) is not None and abs(float(v)-.01)<1e-8 else ('0.001' if num(v) is not None and abs(float(v)-.001)<1e-8 else v)
    return v

def summary_and_pairs(rows,out):
    factor_rows=[];pair_rows=[];effect_rows=[]
    for factor,levels in LEVELS.items():
        for level in levels:
            rs=[r for r in rows if r[factor]==level]
            optimal=[r for r in rs if r['is_optimal']]
            rec={'Factor':LABELS[factor], 'Level':level,'N':len(rs),
                 'Optimal':len(optimal),'OptimalRate_percent':round(100*len(optimal)/len(rs),3) if rs else '',
                 'MedianIterations_successes':fmt(median([num(r.get('Iterations')) for r in optimal]),1)}
            for m in M:
                rec['Median_'+m+'_successes']=fmt(median([num(r.get(m)) for r in optimal]))
            factor_rows.append(rec)
        other=[k for k in KEYS if k!=factor]
        ix={tuple(r[k] for k in KEYS):r for r in rows}
        for a,b in MATCH_PAIRS[factor]:
            pairs=[]
            # Enforce one-to-one exactly matched combinations of other four factors.
            for r in rows:
                if r[factor]!=a:continue
                vals={k:r[k] for k in KEYS};vals[factor]=b
                r2=ix.get(tuple(vals[k] for k in KEYS))
                if r2 is None:continue
                rec={'Factor':LABELS[factor], 'A_Level':a, 'B_Level':b,
                     'A_ID':r['ID'],'B_ID':r2['ID'],'A_Optimal':r['is_optimal'],
                     'B_Optimal':r2['is_optimal'],'BothOptimal':r['is_optimal'] and r2['is_optimal']}
                for k in other:rec[k]=r[k]
                for m in M:
                    av,bv=num(r.get(m)),num(r2.get(m))
                    rec['A_'+m]=av if av is not None else ''
                    rec['B_'+m]=bv if bv is not None else ''
                    rec['Delta_B_minus_A_'+m]=(round(bv-av,6) if rec['BothOptimal'] and av is not None and bv is not None else '')
                ai,bi=num(r.get('Iterations')),num(r2.get('Iterations'))
                rec['A_Iterations']=ai if ai is not None else ''
                rec['B_Iterations']=bi if bi is not None else ''
                rec['DeltaIterations_B_minus_A']=(bi-ai if rec['BothOptimal'] and ai is not None and bi is not None else '')
                rec['IdenticalExportedMotion']=(r.get('MotionSHA256','')==r2.get('MotionSHA256','') and bool(r.get('MotionSHA256')))
                pairs.append(rec)
                pair_rows.append(rec)
            both=[p for p in pairs if p['BothOptimal']]
            e={'Factor':LABELS[factor],'Comparison':f'{a} -> {b}', 'MatchedPairs':len(pairs),
               'BothOptimal':len(both),
               'AOnlyOptimal':sum(p['A_Optimal'] and not p['B_Optimal'] for p in pairs),
               'BOnlyOptimal':sum(p['B_Optimal'] and not p['A_Optimal'] for p in pairs),
               'IdenticalMotion_BothOptimal':sum(p['IdenticalExportedMotion'] for p in both)}
            for m in M:
                deltas=[num(p['Delta_B_minus_A_'+m]) for p in both]
                e['MedianDelta_B_minus_A_'+m]=fmt(median(deltas))
                e['MedianAbsDelta_'+m]=fmt(median([abs(v) if v is not None else None for v in deltas]))
            e['MedianIterationDelta_B_minus_A']=fmt(median([num(p['DeltaIterations_B_minus_A']) for p in both]),1)
            effect_rows.append(e)
    write_csv(out/'factor_levels.csv',factor_rows)
    write_csv(out/'controlled_parameter_pairs.csv',pair_rows)
    write_csv(out/'matched_effects.csv',effect_rows)
    return factor_rows,effect_rows,pair_rows

def parse_ipopt(text):
    """Parse only text with a canonical IPOPT header; split repeated solves at reset."""
    if not HEADER.search(text): return []
    blocks=[];block=[]
    armed=False
    for line in text.splitlines():
        if HEADER.search(line):
            armed=True
            continue
        if not armed:continue
        m=ROW.match(line)
        if not m:continue
        it=int(m.group(1));obj=num(m.group(3));pr=num(m.group(4));du=num(m.group(5))
        if obj is None or pr is None or du is None:continue
        if block and it < block[-1]['iteration']:
            if len(block)>=5:blocks.append(block)
            block=[]
        if block and it==block[-1]['iteration']:
            block[-1]={'iteration':it,'objective':obj,'inf_pr':pr,'inf_du':du,'restoration':bool(m.group(2))}
        else:
            block.append({'iteration':it,'objective':obj,'inf_pr':pr,'inf_du':du,'restoration':bool(m.group(2))})
    if len(block)>=5:blocks.append(block)
    return blocks

def scan_external(log_root, eid):
    """Scan bounded folders; never walk large participant data trees."""
    if not log_root.exists():return []
    candidates=[]
    roots=[log_root] + [log_root/d for d in ('logs','log','stdout','output','outputs','condor_logs','batch','results')]
    for d in roots:
        if not d.is_dir():continue
        for pattern in (f'*{eid}*.out',f'*{eid}*.log',f'*{eid}*.txt',f'*{eid}*.stdout',f'*{eid}*.out.gz',f'*{eid}*.log.gz'):
            try:candidates.extend(d.glob(pattern))
            except OSError:pass
    return sorted(set(x for x in candidates if x.is_file() and x.stat().st_size<60_000_000))

def load_text(path):
    if path.suffix=='.gz':
        with gzip.open(path,'rb') as f:data=f.read(60_000_001)
    else:
        with path.open('rb') as f:data=f.read(60_000_001)
    return data.decode('utf-8','replace') if len(data)<=60_000_000 else ''

def archive_logs(archive):
    if not archive.is_file():return []
    out=[]
    try:
        with tarfile.open(archive,'r:gz') as tf:
            for member in tf:
                if not member.isfile() or member.size>50_000_000:continue
                if not re.search(r'\.(?:out|log|txt|stdout|stderr)$',member.name,re.I): continue
                # Skip large generic metadata/data files; explicit header check below.
                fh=tf.extractfile(member)
                if fh is None:continue
                data=fh.read(50_000_001)
                if len(data)>50_000_000:continue
                s=data.decode('utf-8','replace')
                if HEADER.search(s):out.append((f'{archive.name}!{member.name}',s))
    except (OSError,tarfile.TarError) as e:
        return [(f'{archive.name}:ERROR {e}','')]
    return out

def collect_trace(eid,expected_iters,root,log_roots):
    candidates=[]
    for directory in log_roots:
        for file in scan_external(directory,eid):
            try:s=load_text(file)
            except (OSError,EOFError):continue
            if HEADER.search(s):candidates.append((str(file),s))
    # Preserve login-node I/O: inspect compressed archive only if no external IPOPT stdout was found.
    if not candidates:
        candidates+=archive_logs(root/'results'/f'{eid}_results.tar.gz')
    choices=[]
    for path,s in candidates:
        for block in parse_ipopt(s):
            n=block[-1]['iteration']
            # Prefer a block that actually ends at the archived solver iteration.
            closeness=abs(n-expected_iters) if expected_iters is not None else 0
            # When equal, favor more actual recorded iterations, not copied summaries.
            choices.append((closeness,-len(block),path,block))
    if not choices:
        return None, '', len(candidates)
    choices.sort(key=lambda t:(t[0],t[1]))
    _,__,path,block=choices[0]
    return block,path,len(candidates)

def svg_plot(path,title,curve1,label1,curve2,label2,field,logscale=False):
    W,H=1020,580;L,R,T,B=104,45,66,91
    a,b=curve1,curve2
    values=[r[field] for rows in (a,b) for r in rows if math.isfinite(r[field])]
    if not values:return
    if logscale:
        values=[math.log10(max(v,1e-14)) for v in values]
    lo,hi=min(values),max(values)
    if hi<=lo:hi=lo+1
    pad=.06*(hi-lo);lo-=pad;hi+=pad
    maxit=max(r['iteration'] for rows in (a,b) for r in rows)
    maxit=max(maxit,1)
    X=lambda k:L+k/maxit*(W-L-R)
    Y=lambda y:T+(hi-y)/(hi-lo)*(H-T-B)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{L}" y="32" font-size="22" fill="#222" font-family="Arial">{html.escape(title)}</text>']
    for j in range(6):
        y=lo+(hi-lo)*j/5;py=Y(y)
        lab=f'{y:.2f}' if logscale else f'{y:.5g}'
        out.append(f'<line x1="{L}" y1="{py:.1f}" x2="{W-R}" y2="{py:.1f}" stroke="#e5e8eb"/>')
        out.append(f'<text x="{L-12}" y="{py+5:.1f}" text-anchor="end" font-family="Arial" font-size="13" fill="#666">{lab}</text>')
    for j in range(6):
        x=j*maxit/5;px=X(x)
        out.append(f'<text x="{px:.1f}" y="{H-B+24}" text-anchor="middle" font-family="Arial" font-size="13" fill="#666">{x:.0f}</text>')
    out.append(f'<line x1="{L}" x2="{W-R}" y1="{H-B}" y2="{H-B}" stroke="#444"/>')
    for color,rows,name in [('#2469b5',a,label1),('#dc7625',b,label2)]:
        pts=[]
        for r in rows:
            v=math.log10(max(r[field],1e-14)) if logscale else r[field]
            pts.append(f'{X(r["iteration"]):.2f},{Y(v):.2f}')
        out.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.3" points="{" ".join(pts)}"/>')
    out.extend([f'<text x="{W/2}" y="{H-19}" font-size="16" font-family="Arial" text-anchor="middle" fill="#333">IPOPT iteration</text>',
               f'<text x="20" y="{H/2}" transform="rotate(-90 20 {H/2})" text-anchor="middle" font-family="Arial" font-size="15" fill="#333">{"log10("+field+")" if logscale else field}</text>'])
    for j,(color,label) in enumerate([('#2469b5',label1),('#dc7625',label2)]):
        yy=H-B+44+j*20
        out.append(f'<line x1="{L}" y1="{yy}" x2="{L+35}" y2="{yy}" stroke="{color}" stroke-width="3"/>')
        out.append(f'<text x="{L+42}" y="{yy+5}" font-family="Arial" font-size="14" fill="#333">{html.escape(label)}</text>')
    out.append('</svg>')
    path.write_text('\n'.join(out)+'\n',encoding='utf-8')

def convergence(rows,out,root,log_roots):
    index={r['ID']:r for r in rows}
    result=[];traces={}
    all_ids=sorted(index)
    for eid in all_ids:
        target=num(index[eid].get('Iterations'))
        block,path,candidates=collect_trace(eid,int(target) if target is not None else None,root,log_roots)
        if block:
            traces[eid]=block
            write_csv(out/'traces'/f'{eid}_ipopt_iterations.csv',block)
        rec={'ID':eid,'IPOPTOptimal':index[eid]['is_optimal'],
             'ReportedIterations':target if target is not None else '',
             'TraceFound':bool(block),'LogSource':path,
             'CandidateLogFilesWithHeader':candidates,
             'ParsedRows':len(block) if block else 0,
             'LastTraceIteration':block[-1]['iteration'] if block else '',
             'IterationCountMatches':(abs(block[-1]['iteration']-target)<1.1 if block and target is not None else ''),
             'FirstObjective':block[0]['objective'] if block else '',
             'FinalObjective':block[-1]['objective'] if block else ''}
        result.append(rec)
        if block:print(f'  {eid}: trace found, {len(block)} rows, final iter {block[-1]["iteration"]}; {path}')
    write_csv(out/'ipopt_log_inventory.csv',result)
    pair_table=[]
    for a,b in FEATURED:
        ra,rb=index[a],index[b];ta,tb=traces.get(a),traces.get(b)
        rec={'A':a,'B':b,'A_Tolerance':ra['IPOPTTolerance'],'B_Tolerance':rb['IPOPTTolerance'],
             'A_Optimal':ra['is_optimal'],'B_Optimal':rb['is_optimal'],
             'A_Iterations':ra.get('Iterations',''), 'B_Iterations':rb.get('Iterations',''),
             'IdenticalExportedMotion': bool(ra.get('MotionSHA256')) and ra.get('MotionSHA256')==rb.get('MotionSHA256'),
             'BothTracesFound':bool(ta and tb)}
        if ta and tb:
            da={r['iteration']:r for r in ta};db={r['iteration']:r for r in tb}
            common=sorted(set(da)&set(db))
            rec['CommonIterations']=len(common)
            rec['MaxAbsObjectiveDifference_CommonIterations']=max(abs(da[k]['objective']-db[k]['objective']) for k in common) if common else ''
            rec['MaxAbsPrimalInfeasibilityDifference_CommonIterations']=max(abs(da[k]['inf_pr']-db[k]['inf_pr']) for k in common) if common else ''
            for name,field,lg in [('objective','objective',False),('primal_infeasibility','inf_pr',True),('dual_infeasibility','inf_du',True)]:
                svg_plot(out/'plots'/f'{a}_vs_{b}_{name}.svg',f'{a} vs {b}: {name.replace("_"," ")}',
                         ta,f'{a} | tol {ra["IPOPTTolerance"]}',tb,f'{b} | tol {rb["IPOPTTolerance"]}',field,lg)
        pair_table.append(rec)
    write_csv(out/'featured_tolerance_pairs.csv',pair_table)
    return result,pair_table

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    home=Path.home()
    ap.add_argument('--metrics',type=Path,default=home/'sts72_validation_review'/'qa_72_common_147'/'all_72_metrics.csv')
    ap.add_argument('--root',type=Path,default=home/'sts_sweep_v1')
    ap.add_argument('--log-dir',type=Path,action='append',default=[],help='Additional directory of preserved IPOPT stdout logs; repeat if needed.')
    ap.add_argument('--out',type=Path,default=home/'sts72_validation_review'/'factor_and_convergence')
    ap.add_argument('--skip-logs',action='store_true',help='Only calculate parameter effects; do not scan 72 archives.')
    args=ap.parse_args();out=args.out.expanduser();out.mkdir(parents=True,exist_ok=True)
    rows=load_csv(args.metrics.expanduser())
    if len(rows)!=72 or set(r['ID'] for r in rows)!={f'E{x:03d}' for x in range(15,87)}:
        raise SystemExit('Input must contain one row for every E015..E086. Verify metrics CSV.')
    for r in rows:
        for k in KEYS:r[k]=norm(k,r[k])
        r['is_optimal']=str(r['IPOPTOptimal']).lower() in ('true','1','yes')
    if any(r.get('MetricStatus')!='OK' for r in rows):
        raise SystemExit('One or more metric rows are ERROR. Use corrected --end 1.47 sweep result.')
    level,eff,pair=summary_and_pairs(rows,out)
    print('\n=== PARAMETERS: CONVERGENCE RATES ===')
    for r in level:
        print(f'{r["Factor"]:<20} {r["Level"]:<14} {r["Optimal"]:>2}/{r["N"]:<2} ({r["OptimalRate_percent"]:>5.1f}%)  '
              f'median GRF {r["Median_"+M[0]+"_successes"]} N, COP {r["Median_"+M[1]+"_successes"]} mm')
    print('\n=== CONTROLLED MATCHED-PAIR EFFECTS (B-A; negative RMSE delta is better) ===')
    for r in eff:
        print(f'{r["Factor"]:<20} {r["Comparison"]:<29} pairs={r["MatchedPairs"]:2} both_opt={r["BothOptimal"]:2} '
              f'A-only={r["AOnlyOptimal"]:2} B-only={r["BOnlyOptimal"]:2} '
              f'GRF delta {r["MedianDelta_B_minus_A_"+M[0]]} N  '
              f'COP delta {r["MedianDelta_B_minus_A_"+M[1]]} mm')
    if not args.skip_logs:
        (out/'traces').mkdir(exist_ok=True);(out/'plots').mkdir(exist_ok=True)
        roots=[args.root.expanduser()]+[d.expanduser() for d in args.log_dir]
        inv,featured=convergence(rows,out,args.root.expanduser(),roots)
        count=sum(r['TraceFound'] for r in inv)
        print(f'\nIPOPT iteration traces found for {count}/72 experiments.')
        for r in featured:
            print(f'  {r["A"]}/{r["B"]}: both traces={r["BothTracesFound"]}, same motion={r["IdenticalExportedMotion"]}')
    notes=[
        '# STS72 parameter importance and convergence screening',
        '',
        'Files: factor_levels.csv, matched_effects.csv, controlled_parameter_pairs.csv.',
        'For iteration logs: ipopt_log_inventory.csv, featured_tolerance_pairs.csv, plots/*.svg, traces/*.csv.',
        '',
        '## Interpretation',
        '- The 72 runs constitute a balanced 3x3x2x2x2 factorial design.',
        '- Factor levels give descriptive marginal OPTIMAL rates, plus medians across *successful* runs.',
        '- Matched pairs compare settings differing in exactly ONE factor, using same central validation window.',
        '- AOnlyOptimal/BOnlyOptimal are discordant paired outcomes. For objective/COP effects, compare only pairs where both converged.',
        '- Missing/nonoptimal cases are not simply dropped when reporting convergence. RMSE among converged cases has selection bias.',
        '- A lower COP error for COP-ON is target fit, NOT independent validation.',
        '- Objective value vs iteration is the IPOPT printed objective; nonmonotonicity and restoration iterations are possible.',
        '- inf_pr and inf_du are plotted on log10 scale with a display floor of 1e-14.',
        '- Identical final motion file hashes do NOT prove identical iteration traces.',
        '- A printed 1e-3 vs 1e-2 tolerance is termination precision, not simulation accuracy or physical error bound.',
        '- Overall parameter ranking based on several objectives is NOT unique: prioritize criterion (solver robustness vs tracking fit vs runtime).',
        '',
        '## If no IPOPT curves are found',
        'The original per-iteration stdout may not have been preserved. MOT files, final objectives, and iteration counts cannot reconstruct it.',
        'Inspect ~/sts_sweep_v1/ and the old HTCondor .out files for the text header "iter objective inf_pr inf_du".',
        'Rerun this script with --log-dir /path/to/old/job/stdout if found. Do not rerun full optimization solely for an objective curve.',
        '',
    ]
    (out/'README_ANALYSIS.txt').write_text('\n'.join(notes),encoding='utf-8')
    print('\nFiles written under:',out)

if __name__=='__main__':main()
