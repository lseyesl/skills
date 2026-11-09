import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from planar_ik import solve_two_link

class IK(unittest.TestCase):
    def test_body_height_changes_keep_same_foot(self):
        # Root bobs and advances while this planted target stays in world space.
        foot=(30,60)
        for root in [(0,5),(8,10),(15,6),(20,4)]:
            dx,dy=foot[0]-root[0],foot[1]-root[1]
            a,b=solve_two_link(dx,dy,35,30)
            a=math.radians(a+90);b=a+math.radians(b)
            self.assertAlmostEqual(root[0]+35*math.cos(a)+30*math.cos(b),foot[0])
            self.assertAlmostEqual(root[1]+35*math.sin(a)+30*math.sin(b),foot[1])
    def test_unreachable_not_clamped(self):
        for target in [(0,61),(0,0),(1,0)]:
            with self.assertRaises(ValueError):solve_two_link(*target,35,25)
    def test_bend_branches(self):
        for sign in (-1,1):
            a,b=solve_two_link(12,45,30,25,sign)
            self.assertEqual(1 if b>0 else -1,sign)
    def test_nonfinite_rejected(self):
        for val in (float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):solve_two_link(val,20,30,30)
    def test_scale_invariance_without_overflow(self):
        expected=solve_two_link(1,1,1,1)
        actual=solve_two_link(1e200,1e200,1e200,1e200)
        for a,b in zip(expected,actual):self.assertAlmostEqual(a,b)

if __name__=='__main__':unittest.main()
