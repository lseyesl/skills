"""Independent acceptance cases discovered after initial reconstruction.
These are deterministic regression/contract tests, not an Agent success benchmark.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from knowledge import load_catalog,search
from compare_evals import compare

class AcceptanceTests(unittest.TestCase):
    def test_natural_queries_and_scope(self):
        entries=load_catalog(ROOT/'skills')
        for query,task,subject,expected in [
            ('手指弯曲后关节体积丢失','repair','hand','blender.hand-deformation'),
            ('我的车轮转动时中心绕圈','repair','wheel','blender.wheel-motion'),
            ('怎样给已有角色添加骨架','create',None,'blender.rigging-and-skinning'),
            ('给汽车添加轮子','create','wheel','blender.wheel-construction'),
            ('export animated rig to gltf','export',None,'blender.rigging-and-skinning')]:
            with self.subTest(query=query):self.assertEqual(search(entries,query,task,subject)[0]['id'],expected)
        for query in ('React wheel event handler','Blender crashes when launching','浏览器滚轮回调','Blender 安装失败'):
            with self.subTest(query=query):self.assertEqual(search(entries,query,'repair'),[])

    def test_unknown_facts_are_not_confirmed(self):
        entries=load_catalog(ROOT/'skills')
        hit=search(entries,'握拳塌陷','repair','hand',{'asset_exists':True,'intended_use':None,'rest_mesh_ok':None})[0]
        self.assertEqual(set(hit['missing_facts']),{'intended_use','rest_mesh_ok'})
        self.assertEqual(search(entries,'握拳塌陷','repair','hand',{'asset_exists':1}),[])
        with self.assertRaises(ValueError):search(entries,'hand',facts=['bad'])

    def test_check_regression_not_hidden_by_same_overall_failure(self):
        base={'kind':'tasks','evidence_validated':True,'suite_sha256':'same','missing_tasks':[],
              'metadata':{'model':'m','environment':'e','budget':'b','rubric_version':'1'},
              'records':[{'task_id':'x','repeat':1,'status':'failed','severe_error':False,
                          'elapsed_seconds':1,'context_tokens':1,'human_interventions':0,
                          'checks':{'preservation':{'status':'passed'},'appearance':{'status':'failed'}}}]}
        head=copy.deepcopy(base);head['records'][0]['checks']['preservation']['status']='failed'
        result=compare(base,head)
        self.assertEqual(result['verdict'],'negative')
        self.assertEqual(result['check_regressions'][0]['check'],'preservation')

    def test_positive_negative_tradeoff_and_insufficient(self):
        base={'kind':'tasks','evidence_validated':True,'suite_sha256':'same','missing_tasks':[],
              'metadata':{'model':'m','environment':'e','budget':'b','rubric_version':'1'},'records':[]}
        for i in range(40):
            base['records'].append(dict(task_id=str(i),repeat=1,status='failed',severe_error=False,elapsed_seconds=1,context_tokens=1,human_interventions=0))
        head=copy.deepcopy(base)
        for record in head['records']:record['status']='passed'
        self.assertEqual(compare(base,head)['verdict'],'positive')
        self.assertEqual(compare(head,base)['verdict'],'negative')
        mixed=copy.deepcopy(head);mixed['records'][0]['status']='failed'
        previous=copy.deepcopy(base);previous['records'][0]['status']='passed'
        self.assertEqual(compare(previous,mixed)['verdict'],'conditional-tradeoff')
        head['records'][0]['status']='unknown'
        self.assertEqual(compare(base,head)['verdict'],'insufficient-evidence')

    def test_committed_install_query_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp);source=temp/'source';source.mkdir();project=temp/'consumer';project.mkdir()
            shutil.copy(ROOT/'skills.json',source/'skills.json')
            for name in ('blender-python-modeling','blender-styles'):
                shutil.copytree(ROOT/'skills'/name,source/'skills'/name,ignore=shutil.ignore_patterns('__pycache__','.tmp'))
            def run(args,cwd=None,ok=True):
                result=subprocess.run([str(a) for a in args],cwd=cwd,text=True,capture_output=True)
                if ok:self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                else:self.assertNotEqual(result.returncode,0)
                return result
            run(['git','init','-q'],source);run(['git','add','.'],source)
            run(['git','-c','user.name=Acceptance Test','-c','user.email=test@example.invalid','commit','-qm','Isolated verification snapshot'],source)
            runtime=ROOT/'skills/ancient-tales-pipeline/scripts/runtime.py'
            run([sys.executable,runtime,'skills','update','--project',project,'--source',source,'--skill','blender-styles'])
            run([sys.executable,runtime,'skills','install','--project',project,'--source',source])
            lock=json.loads((project/'skills.lock.json').read_text())
            self.assertEqual({s['name'] for s in lock['skills']},{'blender-styles','blender-python-modeling'})
            for e in lock['skills']:self.assertEqual(e['source_state'],'committed')
            installed=project/'.agents/skills/blender-python-modeling'
            # Disable source path: query/check must use only the consumer installation.
            source.rename(temp/'hidden-source')
            result=run([sys.executable,installed/'scripts/knowledge_catalog.py','search','握拳塌陷','--task','repair','--subject','hand'])
            self.assertEqual(json.loads(result.stdout)[0]['id'],'blender.hand-deformation')
            run([sys.executable,installed/'scripts/knowledge_catalog.py','retrieve','blender.hand-deformation'])
            run([sys.executable,runtime,'skills','check','--project',project])
            with (installed/'knowledge.json').open('a') as stream:stream.write('\n ')
            run([sys.executable,runtime,'skills','check','--project',project],ok=False)

if __name__=='__main__':unittest.main()
