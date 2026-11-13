import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from knowledge import load_catalog,search,validate_catalog
from run_evals import retrieval,validate_suite,validate_run
from compare_evals import compare
sys.path.insert(0,str(ROOT/'skills/blender-python-modeling/scripts'))
from domain_checks import weight_issues,rolling_error
from knowledge_catalog import impacts

class KnowledgeTests(unittest.TestCase):
    def test_catalog_and_retrieval(self):
        self.assertGreater(validate_catalog(ROOT)['entries'],12)
        for split in ('dev','test'):self.assertTrue(retrieval(ROOT,split)['passed'])
    def test_missing_facts_and_hard_exclusion(self):
        entries=load_catalog(ROOT/'skills')
        hit=search(entries,'握拳塌陷','repair','hand')[0]
        self.assertIn('rest_mesh_ok',hit['missing_facts'])
        self.assertEqual(search(entries,'握拳塌陷','repair','hand',{'asset_exists':False}),[])
    def test_locked_copy_works_without_root(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            dst=Path(tmp)/'blender-python-modeling'
            shutil.copytree(ROOT/'skills/blender-python-modeling',dst)
            self.assertEqual(search(load_catalog(Path(tmp)),'finger collapse','repair','hand')[0]['id'],'blender.hand-deformation')
    def test_bad_paths_ids_refs_and_cycles(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'lib';shutil.copytree(ROOT/'catalog',root/'catalog')
            (root/'skills.json').parent.mkdir(exist_ok=True);shutil.copy(ROOT/'skills.json',root/'skills.json')
            # All manifests and their referenced files, no binary assets needed.
            for path in (ROOT/'skills').glob('*/knowledge.json'):
                folder=root/'skills'/path.parent.name;folder.mkdir(parents=True)
                shutil.copy(path,folder/'knowledge.json')
                for e in json.loads(path.read_text())['entries']:
                    dest=folder/e['entry'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(path.parent/e['entry'],dest)
            p=root/'skills/blender-python-modeling/knowledge.json';original=json.loads(p.read_text())
            for mutate in (lambda d:d['entries'][0].update(entry='../../skills.json'),
                           lambda d:d['entries'][0].update(requires=['unknown']),
                           lambda d:d['entries'][0].update(requires=[d['entries'][0]['id']]),
                           lambda d:d['entries'][0].update(requires=['style.soft-clay']),
                           lambda d:d['entries'][0].update(status='validated')):
                data=copy.deepcopy(original);mutate(data);p.write_text(json.dumps(data))
                with self.assertRaises(ValueError):validate_catalog(root)
    def test_reverse_impact(self):
        affected=impacts(load_catalog(ROOT/'skills'),'blender.acceptance.hand-poses')
        self.assertIn('blender.hand-deformation',affected)
        self.assertNotIn('blender.wheel-motion',affected)

    def test_domain_defects(self):
        self.assertEqual(weight_issues([[],[0.5],[0.5,0.5],[float('nan')]],1)['unweighted'],[0])
        self.assertEqual(weight_issues([[0.5,0.5]],1)['excess_influences'],[0])
        self.assertFalse(rolling_error(1,1,2,0.01)['passed'])
        with self.assertRaises(ValueError):rolling_error(1,0,1,0)

class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.suite={'schema_version':1,'tasks':[{'id':'x','prompt':'do','split':'test','checks':[{'id':'visual','kind':'visual','required':True,'criterion':'inspect'}]}]}
        self.run={'schema_version':1,'metadata':dict(revision='a',model='m',environment='e',budget='b',rubric_version='1'),'records':[dict(task_id='x',repeat=1,status='unknown',severe_error=False,elapsed_seconds=1,context_tokens=2,human_interventions=0,checks={'visual':{'status':'unknown','reason':'not inspected'}})]}
    def test_suite(self):validate_suite(json.loads((ROOT/'skills/blender-python-modeling/evals/task-suite.json').read_text()))
    def test_false_pass_and_stale_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            validate_run(self.suite,self.run,tmp)
            self.run['records'][0]['status']='passed'
            with self.assertRaises(ValueError):validate_run(self.suite,self.run,tmp)
            path=Path(tmp)/'image.txt';path.write_text('evidence')
            check={'status':'passed','reviewer':'test-reviewer','evidence':[{'path':'image.txt','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]}
            self.run['records'][0]['checks']['visual']=check
            validate_run(self.suite,self.run,tmp)
            path.write_text('changed')
            with self.assertRaises(ValueError):validate_run(self.suite,self.run,tmp)
    def test_pass_needs_visual_reviewer_and_cannot_hide_severe_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'evidence';path.write_text('actual')
            self.run['records'][0].update(status='passed')
            check={'status':'passed','evidence':[{'path':'evidence','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]}
            self.run['records'][0]['checks']['visual']=check
            with self.assertRaisesRegex(ValueError,'reviewer'):validate_run(self.suite,self.run,tmp)
            check['reviewer']='human'
            self.run['records'][0]['severe_error']=True
            with self.assertRaisesRegex(ValueError,'False pass'):validate_run(self.suite,self.run,tmp)

    def test_comparison_rejects_confounds_and_missing_pairs(self):
        report={**copy.deepcopy(self.run),'kind':'tasks','evidence_validated':True,'suite_sha256':'s','missing_tasks':[]}
        self.assertEqual(compare(report,report)['verdict'],'insufficient-evidence')
        head=copy.deepcopy(report);head['metadata']['model']='other'
        with self.assertRaises(ValueError):compare(report,head)
        head=copy.deepcopy(report);head['records'][0]['repeat']=2
        self.assertEqual(compare(report,head)['verdict'],'insufficient-evidence')
    def test_modeling_comparison_rejects_extra_revision_allowance(self):
        report={**copy.deepcopy(self.run),'kind':'tasks','evidence_validated':True,'suite_sha256':'s','missing_tasks':[]}
        budget={'candidate_builds':1,'quality_revision_rounds':0,'image_generation_calls':2}
        report['metadata']['budget']=json.dumps(budget,sort_keys=True)
        head=copy.deepcopy(report);budget['quality_revision_rounds']=2
        head['metadata']['budget']=json.dumps(budget,sort_keys=True)
        with self.assertRaisesRegex(ValueError,'budget'):compare(report,head)

    def test_repeats_do_not_inflate_independent_sample_count(self):
        a={**copy.deepcopy(self.run),'kind':'tasks','evidence_validated':True,'suite_sha256':'s','missing_tasks':[]}
        a['records']=[dict(copy.deepcopy(a['records'][0]),repeat=i,status='failed') for i in range(1,101)]
        b=copy.deepcopy(a)
        for r in b['records']:r['status']='passed'
        result=compare(a,b)
        self.assertEqual(result['distinct_tasks'],1)
        self.assertEqual(result['verdict'],'insufficient-evidence')

    def test_comparison_severe_and_tradeoff(self):
        a={**copy.deepcopy(self.run),'kind':'tasks','evidence_validated':True,'suite_sha256':'s','missing_tasks':[]}
        a['records'][0]['status']='passed';b=copy.deepcopy(a);b['records'][0].update(status='failed',severe_error=True)
        self.assertEqual(compare(a,b)['verdict'],'negative')
        b['records'][0]['severe_error']=False
        a['records'].append(dict(copy.deepcopy(a['records'][0]),task_id='y',status='failed'))
        b['records'].append(dict(copy.deepcopy(b['records'][0]),task_id='y',status='passed'))
        self.assertEqual(compare(a,b)['verdict'],'conditional-tradeoff')

if __name__=='__main__':unittest.main()
