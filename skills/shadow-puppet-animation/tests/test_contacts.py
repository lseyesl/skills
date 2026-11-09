import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_contacts import audit

class Contacts(unittest.TestCase):
    def setUp(self):
        self.manifest=dict(schema_version='1.0',coordinate_system='image-pixels-y-down',source_size=[100,100],
            nodes=[dict(id='root',pivot_global=[0,0]),dict(id='foot',parent='root',pivot_global=[0,20])],
            parts=[dict(id='unused',file='not-read.png',pixel_size=[1,1])])
        self.contact=dict(id='support',node='foot',point=[0,20],target=dict(point=[0,20]),frames=[1,3],tolerance_px=.01)
    def test_root_compensation(self):
        poses=[dict(frame=f,translations={'root':[f*4,0],'foot':[-f*4,0]}) for f in range(1,4)]
        self.assertEqual(audit(self.manifest,poses,[self.contact])['status'],'pass')
    def test_sliding_rejected(self):
        poses=[dict(frame=f,translations={'root':[f*4,0]}) for f in range(1,4)]
        r=audit(self.manifest,poses,[self.contact]); self.assertEqual(r['status'],'fail')
        self.assertEqual(r['contacts'][0]['worst']['error_px'],12)
    def test_sparse_not_accepted(self):
        with self.assertRaisesRegex(ValueError,'Missing frame'):
            audit(self.manifest,[dict(frame=1),dict(frame=3)],[self.contact])
    def test_moving_parent_target(self):
        self.contact['target']=dict(node='root',point=[0,20])
        poses=[dict(frame=f,translations={'root':[f,2*f]},angles={'root':f*10}) for f in range(1,4)]
        self.assertEqual(audit(self.manifest,poses,[self.contact])['status'],'pass')
    def test_empty_not_accepted(self):
        with self.assertRaises(ValueError): audit(self.manifest,[],[])
    def test_nonfinite_tolerance(self):
        self.contact['tolerance_px']=float('nan')
        with self.assertRaises(ValueError):audit(self.manifest,[dict(frame=1)],[self.contact])
    def test_overflow_rejected(self):
        poses=[dict(frame=1),dict(frame=2,scales={'root':[1e308,1],'foot':[1e308,1]}),dict(frame=3)]
        with self.assertRaisesRegex(ValueError,'Nonfinite'):audit(self.manifest,poses,[self.contact])
    def test_null_actor_rejected(self):
        self.contact['node']=None
        with self.assertRaises(ValueError):audit(self.manifest,[dict(frame=1)],[self.contact])
    def test_invalid_target_rejected(self):
        for invalid in (None,False,'',0,'missing'):
            with self.subTest(invalid=invalid):
                self.contact['target']['node']=invalid
                with self.assertRaises(ValueError):audit(self.manifest,[dict(frame=1)],[self.contact])
    def test_invalid_structure_rejected(self):
        for motion,contacts in (([None],[self.contact]),({},[self.contact]),([],[None])):
            with self.assertRaises(ValueError):audit(self.manifest,motion,contacts)
    def test_duplicate_contacts_rejected(self):
        poses=[dict(frame=f) for f in range(1,4)]
        with self.assertRaises(ValueError):audit(self.manifest,poses,[self.contact,self.contact])

if __name__=='__main__': unittest.main()
