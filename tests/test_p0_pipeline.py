"""P0 mechanism tests; no model calls or credentials."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from knowledge import load_catalog,search,validate_catalog
from compare_evals import compare,validate_policy
from agent_benchmark import execute,usage_and_model,sandbox_command,archive_skills,clean_environment,failure_class

class PipelineTests(unittest.TestCase):
    def policy(self):
        return {'schema_version':1,'objective':{'metric':'success_rate','min_improvement':0},'minimum_distinct_tasks':10,
                'max_mean_increase':dict(elapsed_seconds=5,context_tokens=100,human_interventions=0),
                'max_per_run':dict(elapsed_seconds=100,context_tokens=1000,human_interventions=0),'protected_checks':['preservation']}
    def reports(self,policy):
        metadata=dict(source_sha256='same-fixture',model='observed-model',environment='same',budget='same',rubric_version='same',comparison_policy_sha256=hashlib.sha256(json.dumps(policy,sort_keys=True).encode()).hexdigest())
        base=dict(kind='tasks',evidence_validated=True,suite_sha256='s',missing_tasks=[],metadata=metadata,records=[])
        for i in range(40):base['records'].append(dict(task_id=str(i),repeat=1,status='failed',severe_error=False,elapsed_seconds=10,context_tokens=100,human_interventions=0,checks={'preservation':{'status':'passed'}}))
        head=copy.deepcopy(base)
        for r in head['records']:r['status']='passed'
        return base,head
    def test_full_coverage_and_existing_topics(self):
        data=validate_catalog(ROOT);self.assertGreater(data['entries'],80)
        entries=load_catalog(ROOT/'skills')
        for query,expected in [('UV 接缝','blender.uv-and-texture-baking'),('cloth simulation','blender.physics-and-simulation'),('布料穿透','blender.cloth-collision-repair'),('为 React 展示页面导出 Blender 角色 GLB','blender.export-and-packaging')]:
            with self.subTest(query=query):self.assertEqual(search(entries,query)[0]['id'],expected)
        self.assertEqual(search(entries,'React wheel event handler'),[])
        self.assertEqual(search(entries,'Blender crashes when launching'),[])
    def test_integrated_shadow_puppet_topics(self):
        entries=load_catalog(ROOT/'skills')
        for query,expected in [
            ('皮影动画','shadow-puppet-animation.overview'),
            ('皮影接触量测','shadow-puppet-animation.contact-audit'),
            ('角色标注编译','shadow-puppet-part-splitter.character-intake'),
            ('装配诊断','shadow-puppet-part-splitter.assembly-diagnostics')]:
            with self.subTest(query=query):self.assertEqual(search(entries,query)[0]['id'],expected)
    def test_policy_prevents_false_positive(self):
        policy=self.policy();base,head=self.reports(policy)
        self.assertEqual(compare(base,head,policy=policy)['verdict'],'positive')
        for r in head['records']:r.update(elapsed_seconds=1000,context_tokens=100000,human_interventions=10)
        result=compare(base,head,policy=policy)
        self.assertEqual(result['verdict'],'negative');self.assertIn('mean-increase:elapsed_seconds',result['policy_result']['violations'])
    def test_policy_cannot_be_selected_after_results(self):
        policy=self.policy();base,head=self.reports(policy)
        del base['metadata']['comparison_policy_sha256']
        self.assertEqual(compare(base,head,policy=policy)['verdict'],'insufficient-evidence')
        with self.assertRaises(ValueError):validate_policy({'schema_version':1})
    def test_unknown_model_is_not_comparable(self):
        policy=self.policy();base,head=self.reports(policy)
        for r in (base,head):r['metadata']['model']='unobserved'
        self.assertEqual(compare(base,head,policy=policy)['verdict'],'insufficient-evidence')
    def test_bounded_cost_objective(self):
        policy=self.policy();policy['objective']={'metric':'elapsed_seconds','min_improvement':1}
        policy['max_per_run']['elapsed_seconds']=100
        base,head=self.reports(policy)
        for r in base['records']:r.update(status='passed',elapsed_seconds=100)
        for r in head['records']:r.update(status='passed',elapsed_seconds=1)
        self.assertEqual(compare(base,head,policy=policy)['verdict'],'positive')
    def test_command_timeout_and_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            result=execute([sys.executable,'-c','import time; time.sleep(5)'],root,root/'timeout',0.05)
            self.assertEqual(result['state'],'timeout')
            (root/'events').write_text(json.dumps({'type':'turn.completed','usage':{'input_tokens':3,'output_tokens':2}})+'\n')
            (root/'err').write_text('model: actual-model\n')
            count,model,_=usage_and_model(root/'events',root/'err');self.assertEqual((count,model),(5,'actual-model'))
    def test_authentication_failure_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'stderr';path.write_text('401 Unauthorized: token parse failure')
            self.assertEqual(failure_class(path,{'state':'completed','returncode':1}),'authentication')

    def test_snapshot_and_isolation_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'snapshot';target.mkdir()
            fingerprint=archive_skills(target,'bdf36e5','blender-styles')
            self.assertEqual(len(fingerprint),64)
            self.assertTrue((target/'blender-python-modeling/SKILL.md').exists())
            self.assertFalse((target/'blender-python-modeling/tests').exists())
            self.assertFalse((target/'blender-python-modeling/evals').exists())
        command=sandbox_command(Path('/task-source'),Path('/private-auth'),['true'])
        self.assertIn('--unshare-pid',command);self.assertIn('--tmpfs',command)
        self.assertNotIn('GH_TOKEN',clean_environment());self.assertNotIn('HF_TOKEN',clean_environment())

if __name__=='__main__':unittest.main()
