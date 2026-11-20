import shutil
import subprocess
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from compile_character import compile_character

class CharacterCompileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.r=Path(self.tmp.name)
        im=Image.new('RGBA',(8,8),(80,120,160,255))
        for y in range(8): im.putpixel((0,y),(20,40,60,[0,1,64,128,192,254,255,255][y]))
        im.save(self.r/'source.png')
        self.data={'schema_version':'character-annotation-1','source':'source.png','source_size':[8,8],'hidden_policy':'concept-covered','ownership':'exclusive','subject':self.region(0,7),'nodes':[{'id':'root','pivot_global':[4,4]}], 'parts':[{'id':'a','node':'root','z_index':0,'visible':self.region(0,3)},{'id':'b','node':'root','z_index':1,'visible':self.region(4,7)}]}
    def region(self,x1,x2): return {'polygons':[[[x1,0],[x2,0],[x2,7],[x1,7]]]}
    def run_case(self):
        (self.r/'a.json').write_text(json.dumps(self.data))
        return compile_character(self.r/'a.json',self.r/'out')
    def test_preserves_soft_alpha_and_source(self):
        original=(self.r/'source.png').read_bytes(); report=self.run_case()
        self.assertEqual(report['rest_changed_pixels'],0)
        self.assertEqual((self.r/'source.png').read_bytes(),original)
        with Image.open(self.r/'out/preview/reassembled.png') as result,Image.open(self.r/'source.png') as source:
            for y in range(1,8): self.assertEqual(result.getpixel((0,y)),source.getpixel((0,y)))
    def test_missing_pixels_rejected(self):
        self.data['parts'].pop()
        with self.assertRaisesRegex(ValueError,'unassigned'):self.run_case()
        self.assertFalse((self.r/'out').exists())
    def test_overlap_requires_explicit_priority(self):
        self.data['parts'][0]['visible']=self.region(0,7)
        with self.assertRaisesRegex(ValueError,'overlapping'):self.run_case()
        self.data['ownership']='ordered-last-wins'
        self.assertEqual(self.run_case()['rest_changed_pixels'],0)
    def test_invalid_hierarchy_before_writes(self):
        self.data['nodes'][0]['parent']='root'
        with self.assertRaisesRegex(ValueError,'cycle'):self.run_case()
        self.assertFalse((self.r/'out').exists())
    def test_existing_output_protected(self):
        self.run_case(); saved=(self.r/'out/manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'already exists'):self.run_case()
        self.assertEqual((self.r/'out/manifest.json').read_bytes(),saved)
    def add_repair(self):
        self.data['hidden_policy']='inferred-repair'
        Image.new('RGBA',(8,8),(220,0,0,255)).save(self.r/'repair.png')
        self.data['parts'][0]['repair']={'file':'repair.png','region':self.region(4,7),'reason':'test hidden extension'}
    def test_covered_repair_preserves_rest(self):
        self.add_repair();self.assertEqual(self.run_case()['rest_changed_pixels'],0)
        manifest=json.loads((self.r/'out/manifest.json').read_text());self.assertTrue(manifest['parts'][0]['inferred'])
    def test_exposed_repair_blocks(self):
        self.add_repair();self.data['parts'][0]['z_index']=2
        report=self.run_case();self.assertEqual(report['status'],'blocked');self.assertEqual(report['rest_changed_pixels'],32)
    def test_concept_policy_rejects_repair(self):
        self.add_repair();self.data['hidden_policy']='concept-covered'
        with self.assertRaisesRegex(ValueError,'forbidden'):self.run_case()
    def test_paths_cannot_escape_output(self):
        self.data['parts'][0]['id']='../escape'
        with self.assertRaisesRegex(ValueError,'invalid/duplicate'):self.run_case()
    def test_unknown_node_rejected(self):
        self.data['parts'][0]['node']='missing'
        with self.assertRaisesRegex(ValueError,'unknown node'):self.run_case()

    def test_blocked_asset_cannot_enter_normal_loader(self):
        from puppet import load_manifest, render
        self.add_repair(); self.data['parts'][0]['z_index']=2
        self.assertEqual(self.run_case()['status'],'blocked')
        with self.assertRaisesRegex(ValueError,'blocked'):load_manifest(self.r/'out/manifest.json')
        self.assertIsNotNone(render(self.r/'out/manifest.json',diagnostic=True))
    def test_source_binding_rejects_same_size_replacement(self):
        self.data['source_sha256']=hashlib.sha256((self.r/'source.png').read_bytes()).hexdigest()
        Image.new('RGBA',(8,8),'green').save(self.r/'source.png')
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):self.run_case()
    def test_output_changes_invalidate_compilation(self):
        from puppet import load_manifest
        self.run_case(); Image.new('RGBA',(4,8),'red').save(self.r/'out/parts/a.png')
        with self.assertRaisesRegex(ValueError,'changed since validation'):load_manifest(self.r/'out/manifest.json')
    def test_records_repair_dependencies(self):
        self.add_repair(); report=self.run_case()
        self.assertIn(str(self.r/'repair.png'),report['input_sha256'])
        self.assertIn('manifest.json',report['output_sha256'])

    @unittest.skipUnless(shutil.which('node'), 'optional Node editor contract check')
    def test_editor_identity_and_reserved_ids(self):
        subprocess.run(['node',str(Path(__file__).with_name('editor_contract.js'))],check=True,capture_output=True,text=True)

    def test_compiler_preserves_and_checks_parent_intent(self):
        self.data['expected_parents']={'root':'root'}
        report=self.run_case();self.assertEqual(report['status'],'blocked')
        manifest=json.loads((self.r/'out/manifest.json').read_text())
        self.assertEqual(manifest['expected_parents'],self.data['expected_parents'])
    def test_compiler_preserves_occlusion_rules(self):
        self.data['occlusion_rules']=[{'front':'b','back':'a'}]
        report=self.run_case();self.assertEqual(report['status'],'pass')
        self.assertEqual(report['layer_constraints'],'pass-sampled')

    def test_wrong_layer_blocks_even_if_pixel_colors_match(self):
        self.add_repair();Image.new('RGBA',(8,8),(80,120,160,255)).save(self.r/'repair.png')
        self.data['parts'][0]['z_index']=2
        self.data['occlusion_rules']=[{'front':'b','back':'a'}]
        report=self.run_case();self.assertEqual(report['rest_changed_pixels'],0)
        self.assertEqual(report['status'],'blocked');self.assertEqual(report['layer_constraints'],'fail')

if __name__=='__main__':unittest.main()
