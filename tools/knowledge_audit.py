"""Inspect validation freshness or create an unreviewed receipt draft."""
import argparse
import json
from pathlib import Path
from knowledge import load_catalog
from knowledge_evidence import snapshot,receipt_state
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--skills-dir',type=Path,default=ROOT/'skills');p.add_argument('--id');p.add_argument('--suite');p.add_argument('--tool',action='append',default=[]);p.add_argument('--output',type=Path)
    args=p.parse_args();entries=load_catalog(args.skills_dir)
    if args.id:
        if not args.suite or not args.output:p.error('--id requires --suite and --output')
        report=snapshot(entries,args.id,args.suite,args.tool)
        if args.output.exists():p.error('Refusing to overwrite an existing receipt')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    else:
        report={ident:receipt_state(entries,ident) for ident in entries if entries[ident]['status']=='validated'}
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if any(value!='fresh' for value in report.values()):raise SystemExit(1)
