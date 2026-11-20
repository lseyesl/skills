import json
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from production_checks import correspondence_status,padding_pixels,optimization_result
from gltf_audit import audit
from knowledge_catalog import load_catalog,search

class ProductionChecks(unittest.TestCase):
    def test_correspondence_requires_identity_and_order(self):
        self.assertEqual(correspondence_status(4,4),'unknown-order')
        self.assertEqual(correspondence_status(4,3),'incompatible-count')
        self.assertEqual(correspondence_status(3,3,['a','b','c'],['c','b','a']),'incompatible-order')
        self.assertEqual(correspondence_status(3,3,['a','b','c'],['a','b','c']),'compatible')
        self.assertEqual(correspondence_status(3,3,['a','a','c'],['a','b','c']),'invalid-identity')
    def test_padding_uses_measured_gap(self):
        self.assertAlmostEqual(padding_pixels(4/1024,1024),4)
        self.assertAlmostEqual(padding_pixels(4/1024,4096),16)
        with self.assertRaises(ValueError):padding_pixels(-0.1,1024)
    def test_cost_reduction_does_not_override_preservation(self):
        before={'bytes':100};after={'bytes':50}
        self.assertEqual(optimization_result(before,after,'bytes',20,{'nodes':True,'visual':True})['status'],'positive')
        self.assertEqual(optimization_result(before,after,'bytes',20,{'nodes':False})['status'],'negative')
        self.assertEqual(optimization_result(before,after,'bytes',20,{'visual':None})['status'],'unknown')
        self.assertEqual(optimization_result(before,after,'bytes',60,{'nodes':True})['status'],'not-demonstrated')
        with self.assertRaises(ValueError):optimization_result(before,after,'bytes',20,{})
    def test_missing_validator_is_blocked_and_input_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);asset=root/'test.gltf';content='{"asset":{"version":"2.0"}}';asset.write_text(content)
            result=audit(asset,root/'absent',root/'report.json')
            self.assertEqual(result['status'],'blocked');self.assertEqual(asset.read_text(),content)
            with self.assertRaises(ValueError):audit(asset,root/'absent',asset)
            with self.assertRaises(ValueError):audit(asset,root/'absent',root/'report.json')
    def test_sources_and_verification_are_traceable(self):
        entries=load_catalog(ROOT.parent)
        source_text=(ROOT/'references/sources/production-sources.md').read_text()
        for entry in entries.values():
            for ident in entry.get('source_ids',[]):
                self.assertIn('| '+ident+' |',source_text)
                self.assertTrue(entry['verification'])

    def test_specific_symptoms_find_workflows(self):
        entries=load_catalog(ROOT.parent)
        for query,task,expected in [
            ('生成模型重拓扑','repair','blender.mesh-recovery'),('权重迁移','repair','blender.data-transfer-repair'),
            ('修正形态键','repair','blender.joint-correctives'),('法线贴图接缝','repair','blender.normal-bake-repair'),
            ('布料穿透','repair','blender.cloth-collision-repair'),('GLB规范验证','inspect','blender.gltf-validation'),
            ('保留节点优化','optimize','blender.realtime-optimization')]:
            with self.subTest(query=query):self.assertEqual(search(entries,query,task)[0]['id'],expected)

    def test_source_then_optimization_routes(self):
        entries=load_catalog(ROOT.parent)
        for query,task,expected in [('先还原再减面','optimize','blender.realtime-optimization'),
                                    ('源模型与交付副本','create','blender.blockout-and-refinement')]:
            with self.subTest(query=query):self.assertEqual(search(entries,query,task)[0]['id'],expected)

    def test_modeling_method_and_acceptance_routes(self):
        entries=load_catalog(ROOT.parent)
        for query,task,expected in [
            ('盒式建模','create','blender.blockout-and-refinement'),
            ('Cube 细分','create','blender.blockout-and-refinement'),
            ('已有基础网格复用','repair','blender.blockout-and-refinement'),
            ('基础形体验收','inspect','blender.acceptance.blockout')]:
            with self.subTest(query=query):self.assertEqual(search(entries,query,task)[0]['id'],expected)

    def test_usable_asset_failure_routes(self):
        entries=load_catalog(ROOT.parent)
        for query,task,expected in [
            ('默认 Cube 混入','repair','blender.production-workspace'),
            ('降噪器不可用','repair','blender.production-workspace'),
            ('杯底漏孔','repair','blender.containers-and-connections'),
            ('把手浮空','repair','blender.containers-and-connections'),
            ('辐条断开','repair','blender.containers-and-connections'),
            ('可用资产验收','inspect','blender.acceptance.usable-asset')]:
            with self.subTest(query=query):self.assertEqual(search(entries,query,task)[0]['id'],expected)

    def test_reference_preparation_and_source_fidelity_routes(self):
        entries=load_catalog(ROOT.parent)
        for query,expected in [('参考准备','blender.reference-preparation'),('原图对照','concept.source-fidelity'),('Blender MCP安装','blender.mcp-workflow'),('遮挡误判','blender.reference-image-analysis'),('退化三角形','blender.verification'),('面数超预算','blender.verification')]:
            with self.subTest(query=query):
                self.assertEqual(search(entries,query,'inspect')[0]['id'],expected)

    def test_resource_contract_validation(self):
        from blockout_gate import resource_limits
        for value in (0,-1,True,40000.5,'40000'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                resource_limits({'resource_budget':{'max_triangles':value,'reason':'test'}},'refine')
        with self.assertRaises(ValueError):resource_limits({'resource_budget':{'required':True,'reason':'delivery unresolved'}},'delivery')
        with self.assertRaises(ValueError):resource_limits({'resource_budget':{'max_triangles':100}},'blockout')
        plan={'resource_budget':{'required':True,'max_triangles':40000,'blockout_max_triangles':2000,'reason':'test target','require_closed':True}}
        self.assertEqual(resource_limits(plan,'blockout')['max_triangles'],2000)
        self.assertIsNone(resource_limits(plan,'refine')['max_triangles'])
        self.assertEqual(resource_limits(plan,'delivery')['max_triangles'],40000)
        self.assertFalse(resource_limits(plan,'blockout')['require_closed'])
        self.assertTrue(resource_limits(plan,'delivery')['require_closed'])

    def test_delivery_budget_never_leaks_into_source_construction(self):
        from blockout_gate import resource_limits
        plan={'resource_budget':{'required':True,'max_triangles':100,'reason':'consumer cap'}}
        for stage in ['blockout','refine']:
            self.assertIsNone(resource_limits(plan,stage)['max_triangles'])
        for stage in ['delivery','reimport']:
            self.assertEqual(resource_limits(plan,stage)['max_triangles'],100)
        plan['resource_budget']['working_max_triangles']=100000
        self.assertEqual(resource_limits(plan,'refine')['max_triangles'],100000)
        self.assertIsNone(resource_limits(plan,'blockout')['max_triangles'])
        for value in (True,0,-1,float('nan')):
            plan['resource_budget']['working_max_triangles']=value
            with self.subTest(value=value),self.assertRaises(ValueError):resource_limits(plan,'refine')

    def test_source_may_precede_resolved_delivery_budget(self):
        from blockout_gate import resource_limits
        plan={'resource_budget':{'required':True,'reason':'target budget pending; source reconstruction first'}}
        self.assertIsNone(resource_limits(plan,'refine')['max_triangles'])
        with self.assertRaises(ValueError):resource_limits(plan,'reimport')

    def test_fitter_task_budget_validation(self):
        import copy
        from reference_fit.config import validate
        config=json.loads((ROOT/'examples/clay-girl-fit/character.json').read_text())
        for budget in (0,-1,True,80000.5):
            candidate=copy.deepcopy(config);candidate['validation']['max_triangles']=budget
            with self.subTest(budget=budget),self.assertRaises(ValueError):validate(candidate)
        config['validation']['max_triangles']=80000;validate(config)
        config['validation']['working_max_triangles']=160000;validate(config)
        config['validation']['working_max_triangles']=True
        with self.assertRaises(ValueError):validate(config)
        del config['validation']['working_max_triangles']
        for value in (-1,True,float('nan')):
            candidate=copy.deepcopy(config);candidate['validation']['min_triangle_area']=value
            with self.subTest(area=value),self.assertRaises(ValueError):validate(candidate)

if __name__=='__main__':unittest.main()
