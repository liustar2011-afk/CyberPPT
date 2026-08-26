#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from ppt_image_enhancer.auto import build_auto_config
from ppt_image_enhancer.pipeline import enhance

EXT={'.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff'}

def main():
    ap=argparse.ArgumentParser(description='Batch enhance images; each page is auto-classified')
    ap.add_argument('input_dir')
    ap.add_argument('-o','--output-dir')
    ap.add_argument('--backend', choices=['auto','builtin','realesrgan_ncnn','realesrgan','swinir'], default='auto')
    ap.add_argument('--scale', type=float, default=2.0, choices=[1.0,1.5,2.0,4.0])
    args=ap.parse_args()
    src=Path(args.input_dir).resolve(); out=Path(args.output_dir).resolve() if args.output_dir else src/'enhanced'
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for p in sorted(src.iterdir()):
        if not p.is_file() or p.suffix.lower() not in EXT: continue
        dst=out/(p.stem+'_enhanced.png'); rp=out/(p.stem+'_enhanced.png.report.json')
        cfg, decision=build_auto_config(p,None,args.backend,args.scale)
        try:
            r=enhance(p,dst,cfg,rp)
        except Exception as exc:
            if args.backend=='auto' and decision['selected_backend']!='builtin':
                cfg, decision=build_auto_config(p,None,'builtin',args.scale)
                r=enhance(p,dst,cfg,rp); r['fallback_reason']=str(exc)
            else: raise
        r['auto_decision']=decision; rp.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        rows.append({'input':str(p),'output':str(dst),'mode':decision['selected_mode'],'backend':r['super_resolution_backend'],'warnings':r['warnings']})
        print(f"{p.name} -> {dst.name} [{rows[-1]['mode']}/{rows[-1]['backend']}]")
    (out/'batch-report.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Done: {len(rows)} image(s). Output: {out}')
if __name__=='__main__': main()
