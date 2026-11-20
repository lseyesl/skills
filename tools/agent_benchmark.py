"""Linux Codex CLI benchmark with hidden repo/grader and recorded task/skill fingerprints.
Run explicitly; never called by lightweight CI. No API key provisioning or model override.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tarfile
import time
from run_evals import digest, validate_run
from compare_evals import validate_policy

ROOT=Path(__file__).resolve().parents[1]
PRIVATE_PARTS={'tests','evals','history','__pycache__','.tmp','.venv'}


def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def execute(command,cwd,logs,timeout,prompt=None,environment=None):
    started=time.monotonic()
    with Path(str(logs)+'.stdout').open('w') as stdout, Path(str(logs)+'.stderr').open('w') as stderr:
        proc=subprocess.Popen(list(map(str,command)),cwd=cwd,stdin=subprocess.PIPE if prompt is not None else subprocess.DEVNULL,
                              stdout=stdout,stderr=stderr,env=environment,start_new_session=True)
        try:proc.communicate(prompt.encode() if prompt is not None else None,timeout=timeout);state='completed'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();state='timeout'
    return {'state':state,'returncode':proc.returncode,'elapsed_seconds':time.monotonic()-started}


def archive_skills(destination,ref,skill):
    registry=json.loads(subprocess.check_output(['git','show',ref+':skills.json'],cwd=ROOT)) if ref!='working-tree' else json.loads((ROOT/'skills.json').read_text())
    ordered=[]
    def visit(name):
        if name in ordered:return
        for dep in registry['skills'][name].get('requires',[]):visit(dep)
        ordered.append(name)
    visit(skill)
    for name in ordered:
        target=destination/name
        if ref=='working-tree':
            shutil.copytree(ROOT/'skills'/name,target,ignore=shutil.ignore_patterns(*PRIVATE_PARTS,'test_*.py'))
        else:
            data=subprocess.check_output(['git','archive',ref,'skills/'+name],cwd=ROOT)
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                for member in archive.getmembers():
                    relative=Path(member.name).relative_to('skills')
                    if any(part in PRIVATE_PARTS for part in relative.parts) or relative.name.startswith('test_'):continue
                    path=(destination/relative).resolve()
                    if not path.is_relative_to(destination.resolve()):raise ValueError('Escaping archive entry')
                    if member.isdir():path.mkdir(parents=True,exist_ok=True)
                    elif member.isfile():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.extractfile(member).read())
                    else:raise ValueError('Unsupported archive member')
    files={p.relative_to(destination).as_posix():digest(p) for p in destination.rglob('*') if p.is_file()}
    return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()


def sandbox_command(task,agent_home,command,hidden_paths=()):
    home=Path.home();codex_home=Path(os.environ.get('CODEX_HOME',str(home/'.codex')))
    prefix=['bwrap','--unshare-pid','--die-with-parent','--ro-bind','/','/','--tmpfs','/workspace','--tmpfs','/tmp','--tmpfs',str(home)]
    for path in dict.fromkeys([str(ROOT), *map(str,hidden_paths)]):prefix+=['--tmpfs',path]
    return prefix+['--dir',str(codex_home),'--bind',str(agent_home),str(codex_home),
            '--bind',str(task),'/workspace/task','--ro-bind',str(task/'inputs'),'/workspace/task/inputs',
            '--ro-bind',str(task/'.agents/skills'),'/workspace/task/.agents/skills',
            '--proc','/proc','--dev','/dev','--chdir','/workspace/task','--',*command]


def clean_environment():
    allowed={'PATH','HOME','LANG','LC_ALL','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE'}
    return {k:v for k,v in os.environ.items() if (k in allowed or k.startswith('CODEX_') or k == 'OPENAI_CLUSTER') and not k.startswith(('CODEX_EXEC_SERVER_', 'CODEX_PRIMARY_RUNTIME_'))}


def failure_class(stderr, execution):
    text=Path(stderr).read_text(errors='replace')
    if '401 Unauthorized' in text: return 'authentication'
    if '451' in text: return 'service-access'
    if execution['state']=='timeout': return 'timeout'
    if execution['returncode']!=0: return 'agent-process'
    return None


def usage_and_model(log,stderr):
    total=0;found=False;model=None;events=[]
    for line in log.read_text(errors='replace').splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        events.append(event.get('type','unknown'))
        if isinstance(event.get('model'),str):model=event['model']
        if event.get('type')=='turn.completed':
            usage=event.get('usage',{});total+=usage.get('input_tokens',0)+usage.get('output_tokens',0);found=True
    if model is None:
        match=re.search(r'^model:\s*(\S+)',stderr.read_text(errors='replace'),re.M)
        if match:model=match.group(1)
    return total if found else None,model,events


def run(args):
    if os.name!='posix' or not shutil.which('bwrap'):raise RuntimeError('Linux bubblewrap isolation is required')
    output=args.output.resolve()
    if output.exists():raise ValueError('Output directory must be new; never overwrite attempts')
    capsule_dir=args.capsule.resolve()
    if not capsule_dir.is_relative_to(ROOT):raise ValueError('Capsule must be inside the hidden repository')
    capsule=json.loads((capsule_dir/'capsule.json').read_text())
    if capsule.get('schema_version')!=1:raise ValueError('Unsupported capsule')
    for field in ('prompt','prepare','grader'):
        path=(capsule_dir/capsule[field]).resolve()
        if not path.is_relative_to(capsule_dir) or not path.is_file():raise ValueError('Invalid capsule file: '+field)
    if args.calibration is None: raise ValueError('A fresh calibrated grader report is required (--calibration)')
    from calibrate_capsule import validate_calibration
    validate_calibration(capsule_dir,args.calibration,subprocess.check_output([args.blender,'--version'],text=True).splitlines()[0])
    auth_source=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'auth.json'
    if not auth_source.is_file():raise RuntimeError('Existing Codex CLI login is required; no credential values are inspected')
    policy=json.loads(args.policy.read_text());validate_policy(policy)
    policy_hash=hashlib.sha256(json.dumps(policy,sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True)
    preflight=execute(['bwrap','--ro-bind','/','/','--tmpfs',str(ROOT),'--','/usr/bin/true'],ROOT,output/'isolation',10)
    if preflight['returncode']!=0:
        write(output/'blocked.json',{'stage':'isolation','reason':'Cannot hide repository; refusing unisolated Agent evaluation','execution':preflight});return 2
    version=subprocess.check_output([args.agent,'--version'],text=True).strip()
    prepared=output/'private-inputs';prepared.mkdir()
    setup=execute([args.blender,'--background','--factory-startup','--python-exit-code','1','--python',capsule_dir/capsule['prepare'],'--',prepared],ROOT,output/'prepare',90)
    if setup['returncode']!=0:write(output/'blocked.json',{'stage':'prepare','execution':setup});return 2
    source_hash=digest(prepared/'source.blend')
    frozen={}
    for label,ref in [('base',args.base),('head',args.head)]:
        folder=output/'frozen'/label
        folder.mkdir(parents=True)
        frozen[label]=(folder,archive_skills(folder,ref,capsule['skill']))
    reports=[]
    for label,ref in [('base',args.base),('head',args.head)]:
        records=[];models=set();skill_hashes=set();failures=[]
        for repeat in range(1,args.repeats+1):
            attempt=output/label/str(repeat);task=attempt/'task';task.mkdir(parents=True)
            shutil.copytree(prepared,task/'inputs')
            snapshot,fingerprint=frozen[label];shutil.copytree(snapshot,task/'.agents/skills');skill_hashes.add(fingerprint)
            prompt=(capsule_dir/capsule['prompt']).read_text();(task/'task.md').write_text(prompt)
            agent_home=attempt/'agent-home';agent_home.mkdir()
            try:
                shutil.copyfile(auth_source,agent_home/'auth.json');(agent_home/'auth.json').chmod(0o600)
                isolation=execute(sandbox_command(task,agent_home,['/bin/sh','-c','test -d /workspace/task/inputs && test ! -e /workspace/skills/skills.json'],[output]),ROOT,attempt/'isolation',10,environment=clean_environment())
                if isolation['returncode']!=0:
                    write(output/'blocked.json',{'stage':'task-isolation','execution':isolation})
                    return 2
                command=[args.agent,'exec','--json','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--sandbox','workspace-write','-C','/workspace/task','-o','/workspace/task/agent-final.md','-']
                execution=execute(sandbox_command(task,agent_home,command,[output]),ROOT,attempt/'trajectory',args.timeout,prompt,clean_environment())
            finally:
                shutil.rmtree(agent_home)
            tokens,model,event_types=usage_and_model(attempt/'trajectory.stdout',attempt/'trajectory.stderr')
            models.add(model or 'unobserved')
            runtime_failure=failure_class(attempt/'trajectory.stderr',execution)
            if runtime_failure:failures.append({'repeat':repeat,'stage':'agent','class':runtime_failure})
            grade_path=attempt/'grade.json'
            grading=execute([args.blender,'--background','--factory-startup','--python-exit-code','1','--python',capsule_dir/capsule['grader'],'--',prepared/'source.blend',task/capsule['output'],grade_path],ROOT,attempt/'grading',90)
            grade=json.loads(grade_path.read_text()) if grade_path.is_file() and grading['returncode']==0 else {'checks':{c:False for c in capsule['checks']},'error':'grader failed'}
            unchanged=digest(task/'inputs/source.blend')==source_hash
            grade['checks']['preservation']=grade['checks'].get('preservation',False) and unchanged
            write(grade_path,grade)
            passed=execution['returncode']==0 and execution['state']=='completed' and all(grade['checks'].values())
            status='unknown' if tokens is None else ('passed' if passed else 'failed')
            evidence={'path':str(grade_path.relative_to(output)),'sha256':digest(grade_path)}
            record={'task_id':capsule['id'],'repeat':repeat,'status':status,'severe_error':tokens is not None and not grade['checks'].get('preservation',False),
                    'elapsed_seconds':execution['elapsed_seconds'],'context_tokens':tokens,'human_interventions':0,
                    'checks':{c:{'status':'passed' if grade['checks'].get(c) else 'failed','evidence':[evidence]} for c in capsule['checks']}}
            if tokens is None:
                record['checks']={c:{'status':'unknown','reason':'Agent execution did not expose completed-turn usage; inspect raw trajectory'} for c in capsule['checks']}
            records.append(record)
            write(attempt/'execution.json',{'execution':execution,'grading':grading,'source_sha256':source_hash,'skill_sha256':fingerprint,'model':model,'events':event_types,'failure_class':failure_class(attempt/'trajectory.stderr',execution),'scope':capsule['scope']})
            if runtime_failure == 'authentication':break
        suite={'schema_version':1,'tasks':[{'id':capsule['id'],'prompt':prompt,'split':'test','checks':[{'id':c,'kind':'behavior','required':True,'criterion':c} for c in capsule['checks']]}]}
        suite_path=output/'suite.json';write(suite_path,suite)
        report={'schema_version':1,'metadata':{'revision':ref,'model':','.join(sorted(models)),'environment':version+'; '+subprocess.check_output([args.blender,'--version'],text=True).splitlines()[0],
                    'budget':str(args.timeout)+' seconds','rubric_version':digest(capsule_dir/capsule['grader']),
                    'comparison_policy_sha256':policy_hash,'calibration_sha256':digest(args.calibration),'source_sha256':source_hash,'skill_sha256':','.join(sorted(skill_hashes))},'records':records,
                    'kind':'tasks','suite_sha256':digest(suite_path),'missing_tasks':[],'scope':capsule['scope'],'origin':'live-codex-cli','execution_failures':failures}
        if all(r['context_tokens'] is not None for r in records):validate_run(suite,report,output);report['evidence_validated']=True
        else:report['evidence_validated']=False;report['reason']='CLI did not expose measured token usage'
        write(output/(label+'-report.json'),report);reports.append(report)
        if any(f['class']=='authentication' for f in failures):
            blocked={'verdict':'insufficient-evidence','reason':'Agent authentication failed; remaining attempts were not run','stage':'agent-authentication'}
            write(output/'blocked.json',blocked);write(output/'comparison.json',blocked);return 2
    from compare_evals import compare
    if all(r['evidence_validated'] for r in reports):
        comparison=compare(*reports,policy=policy)
    else:comparison={'verdict':'insufficient-evidence','reason':'Incomplete execution metadata'}
    write(output/'comparison.json',comparison)
    print(json.dumps({'output':str(output),'comparison':comparison},ensure_ascii=False))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capsule',type=Path,default=ROOT/'evals/capsules/wheel-origin')
    p.add_argument('--base',default='bdf36e5');p.add_argument('--head',default='working-tree');p.add_argument('--policy',type=Path,required=True)
    p.add_argument('--calibration',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--agent',default=shutil.which('codex') or 'codex');p.add_argument('--blender',default=shutil.which('blender') or 'blender')
    p.add_argument('--repeats',type=int,default=1);p.add_argument('--timeout',type=int,default=300)
    args=p.parse_args()
    if args.repeats<1 or args.timeout<1:p.error('Positive repeats/timeout required')
    raise SystemExit(run(args))
if __name__=='__main__':main()
