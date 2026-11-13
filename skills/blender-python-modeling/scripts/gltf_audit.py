"""Local glTF/GLB format audit via an explicitly provided Khronos validator module."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def audit(asset,module,report,node=None,timeout=60):
    asset=Path(asset).resolve();module=Path(module).resolve();report=Path(report).absolute()
    if not asset.is_file():raise ValueError('Missing asset')
    if report.exists() or report.is_symlink() or report.resolve()==asset:raise ValueError('Report must be a new path separate from the input')
    report.parent.mkdir(parents=True,exist_ok=True)
    node=node or shutil.which('node')
    if not node or not module.exists():
        result={'schema_version':1,'status':'blocked','reason':'Explicit Node.js and installed validator module are required'}
        report.write_text(json.dumps(result,indent=2)+'\n');return result
    try:
        process=subprocess.run([node,str(Path(__file__).with_name('validate_gltf.mjs')),str(asset),str(report),str(module)],capture_output=True,text=True,timeout=timeout)
        result=json.loads(report.read_text()) if report.is_file() else {'schema_version':1,'status':'blocked','reason':process.stderr[-3000:] or 'No validator report'}
    except subprocess.TimeoutExpired:
        result={'schema_version':1,'status':'blocked','reason':'Validator timed out'}
    if not report.exists():report.write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('asset',type=Path);p.add_argument('--validator-module',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--node');p.add_argument('--timeout',type=float,default=60)
    a=p.parse_args()
    if a.timeout<=0:p.error('Positive timeout required')
    result=audit(a.asset,a.validator_module,a.report,a.node,a.timeout)
    print(json.dumps({'status':result['status'],'report':str(a.report)},ensure_ascii=False))
    raise SystemExit({'passed':0,'failed':1,'blocked':2}[result['status']])
if __name__=='__main__':main()
