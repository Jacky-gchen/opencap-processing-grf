#!/usr/bin/env python3
"""Read-only post-processing of saved IPOPT iteration traces and STS72 outcome CSV.

Requires output from STS72_Parameter_Importance_Convergence.py:
~/sts72_validation_review/factor_and_convergence/traces/E###_ipopt_iterations.csv
and the 72-run metrics table:
~/sts72_validation_review/qa_72_common_147/all_72_metrics.csv

The printed per-iteration inf_pr and inf_du are NOT the overall scaled NLP
optimality error tested against `tol`. Thus only the archived *terminal*
ScaledNLPError is compared to `tol`. Plots of inf_pr and inf_du are diagnostic.
"""
from __future__ import annotations
import argparse
import csv
import html
import math
from pathlib import Path

PAIRS = [('E017','E021'),('E056','E060'),('E058','E062'),('E018','E022'),('E032','E036'),('E080','E084')]
COLORS=('#2563eb','#ea580c')
EPS=1e-16

def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def fnum(val):
    try:
        f=float(val)
        return f if math.isfinite(f) else None
    except (ValueError,TypeError):return None

def esc(s):return html.escape(str(s))

def draw_poly(rows, name, xmap, ymap):
    pts=[]
    for r in rows:
        x,y=r.get('iteration'),r.get(name)
        if x is not None and y is not None:
            pts.append(f'{xmap(x):.2f},{ymap(max(y,EPS)):.2f}')
    return ' '.join(pts)

def trace_plot(path, pair, traces, rows, window='all'):
    # Two independent log-scaled panels for the diagnostic quantities in IPOPT stdout.
    W,H=1180,720
    top=76; bottom=105; panel_h=216; gap=93
    xleft=114; xright=W-55
    selected=[]
    alltr=[traces.get(e,[]) for e in pair]
    endpoints=[tr[-1]['iteration'] for tr in alltr if tr]
    if not endpoints:return False
    right=max(endpoints)
    left=max(0,right-250) if window=='tail' else 0
    # In tail plots with substantially different lengths, include each run's
    # 250 terminal iterations in a normalized 'iterations before finish' axis.
    normalized=window=='tail'
    for tr in alltr:
        if normalized:
            maxit=tr[-1]['iteration'] if tr else 0
            selected.append([dict(r,iteration=r['iteration']-maxit) for r in tr if r['iteration']>=maxit-250])
        else:
            selected.append(tr)
    if normalized:
        left,right=-250,0
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{xleft}" y="37" font-family="Arial" font-weight="bold" font-size="24" fill="#111827">{esc(pair[0])} vs {esc(pair[1])}: IPOPT feasibility diagnostics</text>',
         f'<text x="{xleft}" y="62" font-family="Arial" font-size="15" fill="#475569">{("Last 250 iterations of each run, aligned at termination" if normalized else "Full histories, actual iteration index")}. Logarithmic Y axes.</text>']
    for i,(field,label) in enumerate([('inf_pr','inf_pr — primal constraint violation (unscaled)'),('inf_du','inf_du — dual infeasibility (scaled internal)')]):
        ytop=top+i*(panel_h+gap)
        ybottom=ytop+panel_h
        vals=[max(r[field],EPS) for group in selected for r in group if field in r and r[field] is not None]
        if not vals:continue
        low=math.floor(math.log10(min(vals)))-.25
        high=math.ceil(math.log10(max(vals)))+.25
        if high-low<1: high=low+1
        xx=lambda x: xleft+(x-left)/(right-left)*(xright-xleft)
        yy=lambda y: ybottom-(math.log10(max(y,EPS))-low)/(high-low)*(panel_h)
        out.append(f'<text x="{xleft}" y="{ytop-13}" font-family="Arial" font-size="19" font-weight="bold" fill="#334155">{esc(label)}</text>')
        for k in range(5):
            v=low+(high-low)*k/4
            yp=ybottom-(v-low)/(high-low)*panel_h
            out.append(f'<line x1="{xleft}" y1="{yp:.1f}" x2="{xright}" y2="{yp:.1f}" stroke="#e2e8f0"/>')
            out.append(f'<text x="{xleft-13}" y="{yp+4:.1f}" font-family="Arial" text-anchor="end" font-size="12" fill="#64748b">10^{v:.1f}</text>')
        for k in range(6):
            x=left+(right-left)*k/5; xp=xx(x)
            out.append(f'<line x1="{xp:.1f}" y1="{ytop}" x2="{xp:.1f}" y2="{ybottom}" stroke="#f1f5f9"/>')
            out.append(f'<text x="{xp:.1f}" y="{ybottom+19}" text-anchor="middle" font-family="Arial" font-size="12" fill="#64748b">{x:.0f}</text>')
        out.append(f'<rect x="{xleft}" y="{ytop}" width="{xright-xleft}" height="{panel_h}" stroke="#cbd5e1" fill="none"/>')
        for c,exp,trace,series in zip(COLORS,pair,alltr,selected):
            if not series:continue
            points=draw_poly(series,field,xx,yy)
            if points:
                out.append(f'<polyline points="{points}" fill="none" stroke="{c}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
                v=series[-1][field]
                if v is not None:
                    out.append(f'<circle cx="{xx(series[-1]["iteration"]):.1f}" cy="{yy(v):.1f}" r="4" fill="{c}"/>')
        out.append(f'<text x="{W/2}" y="{ybottom+40}" font-family="Arial" text-anchor="middle" font-size="14" fill="#475569">{("Iterations relative to each run’s final iteration" if normalized else "IPOPT iteration")}</text>')
    legendy=H-60
    for i,(c,exp) in enumerate(zip(COLORS,pair)):
        info=rows[exp]
        it=info.get('Iterations','?'); tol=info.get('IPOPTTolerance','?')
        status='optimal' if info.get('IPOPTOptimal','').strip().lower() in ('true','1','yes') else 'nonoptimal'
        x=115+i*480
        out.append(f'<line x1="{x}" y1="{legendy}" x2="{x+40}" y2="{legendy}" stroke="{c}" stroke-width="3"/>')
        out.append(f'<text x="{x+49}" y="{legendy+5}" font-family="Arial" font-size="16" fill="#1f2937">{esc(exp)} | tol={esc(tol)} | {esc(it)} iter | {status}</text>')
    out.append(f'<text x="{xleft}" y="{H-19}" font-family="Arial" font-size="12" fill="#a04c0b">IMPORTANT: Neither IPOPT stdout column is the overall scaled NLP error tested against tol. See terminal-error threshold chart.</text>')
    out.append('</svg>')
    path.write_text('\n'.join(out)+'\n',encoding='utf-8')
    return True

def final_chart(path,pairs,rows):
    W,H=1300,650;L,R,T,B=135,70,100,130
    # Plot final *scaled* overall NLP error only; do not reconstruct per iteration.
    data=[(e,rows[e],fnum(rows[e].get('ScaledNLPError'))) for p in pairs for e in p if e in rows]
    hi=1.0;lo=1e-6
    X=lambda i:L+(i+.5)/len(data)*(W-L-R)
    Y=lambda v:T+(math.log10(hi)-math.log10(max(v,lo)))/(math.log10(hi)-math.log10(lo))*(H-T-B)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{L}" y="35" font-family="Arial" font-size="24" font-weight="bold" fill="#111827">Final scaled NLP error versus requested IPOPT tolerance</text>',
         f'<text x="{L}" y="62" font-family="Arial" font-size="15" fill="#475569">Terminal values only. Missing values are shown as NA; these are actual tol thresholds, but other stop checks also apply.</text>']
    for k in range(7):
        v=10**(-k);yp=Y(v)
        out.append(f'<line x1="{L}" y1="{yp:.1f}" x2="{W-R}" y2="{yp:.1f}" stroke="#e2e8f0"/>')
        out.append(f'<text x="{L-15}" y="{yp+5:.1f}" text-anchor="end" font-family="Arial" font-size="14" fill="#475569">1e-{k}</text>')
    for tol,color,name in [(1e-2,'#0f766e','tol = 1e-2'),(1e-3,'#be123c','tol = 1e-3')]:
        yp=Y(tol)
        out.append(f'<line x1="{L}" y1="{yp:.1f}" x2="{W-R}" y2="{yp:.1f}" stroke="{color}" stroke-dasharray="8 7" stroke-width="3"/>')
        out.append(f'<text x="{W-R-4}" y="{yp-8:.1f}" text-anchor="end" font-family="Arial" font-size="15" font-weight="bold" fill="{color}">{name}</text>')
    for i,(eid,r,value) in enumerate(data):
        x=X(i); group=i//2
        if group%2:
            mid=(X(2*group)+X(min(2*group+1,len(data)-1)))/2
        status=r.get('IPOPTOptimal','').strip().lower() in ('true','1','yes')
        color='#2563eb' if status else '#f97316'
        if value is not None and value>0:
            yp=Y(value)
            out.append(f'<circle cx="{x:.1f}" cy="{yp:.1f}" r="7" fill="{color}" stroke="white" stroke-width="1.5"/>')
            out.append(f'<text x="{x:.1f}" y="{yp-12:.1f}" text-anchor="middle" font-family="Arial" font-size="12" fill="#1f2937">{value:.2g}</text>')
        else:
            out.append(f'<text x="{x:.1f}" y="{H-B-17}" font-family="Arial" text-anchor="middle" font-size="13" fill="#a16207">NA</text>')
        out.append(f'<text x="{x:.1f}" y="{H-B+25}" text-anchor="middle" font-family="Arial" font-size="13" fill="#1f2937">{eid}</text>')
        out.append(f'<text x="{x:.1f}" y="{H-B+44}" text-anchor="middle" font-family="Arial" font-size="11" fill="#64748b">tol {r.get("IPOPTTolerance","?")}</text>')
        if i%2==1 and i<len(data)-1:
            xx=(x+X(i+1))/2
            out.append(f'<line x1="{xx:.1f}" y1="{T}" x2="{xx:.1f}" y2="{H-B+54}" stroke="#e2e8f0" stroke-dasharray="4 6"/>')
    out.extend([f'<text x="{L}" y="{H-48}" font-family="Arial" font-size="14" fill="#2563eb">● optimal</text>',
                f'<text x="{L+124}" y="{H-48}" font-family="Arial" font-size="14" fill="#f97316">● nonoptimal</text>',
                f'<text x="{L}" y="{H-21}" font-family="Arial" font-size="12" fill="#64748b">Values from all_72_metrics.csv (ScaledNLPError). Each run also needs absolute dual/constraint/complementarity checks.</text>','</svg>'])
    path.write_text('\n'.join(out)+'\n', encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    home=Path.home()
    ap.add_argument('--analysis-dir',type=Path,default=home/'sts72_validation_review/factor_and_convergence')
    ap.add_argument('--metrics',type=Path,default=home/'sts72_validation_review/qa_72_common_147/all_72_metrics.csv')
    ap.add_argument('--out',type=Path,default=home/'sts72_validation_review/tolerance_diagnostics')
    args=ap.parse_args()
    out=args.out.expanduser();out.mkdir(parents=True,exist_ok=True)
    rows={r['ID']:r for r in read_csv(args.metrics.expanduser())}
    root=args.analysis_dir.expanduser()/'traces'
    traces={}
    for pair in PAIRS:
        for e in pair:
            p=root/f'{e}_ipopt_iterations.csv'
            if e in traces or not p.exists():continue
            records=[]
            for r in read_csv(p):
                it=fnum(r.get('iteration'));pr=fnum(r.get('inf_pr'));du=fnum(r.get('inf_du'))
                if it is not None and pr is not None and du is not None:
                    records.append({'iteration':int(it),'inf_pr':pr,'inf_du':du})
            if records:traces[e]=sorted(records,key=lambda v:v['iteration'])
    final_chart(out/'FINAL_scaled_NLP_error_vs_tol.svg',PAIRS,rows)
    for pair in PAIRS:
        for window in ('all','tail'):
            filename=f'{pair[0]}_vs_{pair[1]}_{"full" if window=="all" else "final_250"}_feasibility.svg'
            did=trace_plot(out/filename,pair,traces,rows,window)
            if not did:print(f'{pair[0]}/{pair[1]}: no trace for either; {filename} skipped')
    summary=[]
    summary.append('IPOPT TOLERANCE COMPARISON — source: all_72_metrics.csv and preserved iteration traces')
    summary.append('NOTE: final ScaledNLPError is the quantity compared to tol; inf_pr and inf_du are separately scaled/defined diagnostics.')
    summary.append('A final error below tol alone does not guarantee optimal termination: absolute criteria also apply.')
    summary.append('A temporary dip below a reference line during iterations does not indicate successful final convergence.')
    summary.append('')
    for a,b in PAIRS:
        summary.append(f'{a} vs {b}:')
        for e in (a,b):
            r=rows[e];v=fnum(r.get('ScaledNLPError'));tol=fnum(r.get('IPOPTTolerance'))
            optimal=r.get('IPOPTOptimal','').strip().lower() in ('true','1','yes')
            ratio=v/tol if v is not None and tol is not None and tol else None
            summary.append(f'  {e} tol={tol:g} optimal={optimal} iterations={r.get("Iterations","NA")} final scaled NLP error={f"{v:.8g}" if v is not None else "not recorded"} error/tol={f"{ratio:.3g}" if ratio is not None else "NA"} trace={"yes" if e in traces else "NO"} status={r.get("IPOPTStatus","")}')
        summary.append('')
    (out/'README_TOLERANCE.txt').write_text('\n'.join(summary),encoding='utf-8')
    print('\n'.join(summary))
    print('Plots and README written to:',out)

if __name__=='__main__':main()
