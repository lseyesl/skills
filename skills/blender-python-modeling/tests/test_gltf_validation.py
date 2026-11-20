"""Explicit integration with the real optional Khronos validator package."""
import argparse,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from gltf_audit import audit
MODULE=None
ASSET=None

class ValidatorTests(unittest.TestCase):
    def test_valid_invalid_and_external_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);asset=root/'valid.gltf'
            asset.write_text(json.dumps({'asset':{'version':'2.0'},'scenes':[{}],'scene':0}))
            valid=audit(asset,MODULE,root/'valid-report.json');self.assertEqual(valid['status'],'passed',valid)
            bad=root/'broken.gltf';bad.write_text(json.dumps({'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':99}]}))
            invalid=audit(bad,MODULE,root/'bad-report.json');self.assertEqual(invalid['status'],'failed',invalid)
            self.assertGreater(invalid['result']['issues']['numErrors'],0)
            delivery=root/'delivery';delivery.mkdir();(root/'outside.bin').write_bytes(b'\0\0\0\0')
            escaped=delivery/'external.gltf';escaped.write_text(json.dumps({'asset':{'version':'2.0'},'buffers':[{'byteLength':4,'uri':'../outside.bin'}]}))
            blocked=audit(escaped,MODULE,root/'blocked-report.json');self.assertEqual(blocked['status'],'blocked',blocked)
            (delivery/'inside.bin').write_bytes(b'\0\0\0\0');local=delivery/'local.gltf';local.write_text(json.dumps({'asset':{'version':'2.0'},'buffers':[{'byteLength':4,'uri':'inside.bin'}]}))
            accepted=audit(local,MODULE,root/'local-report.json');self.assertEqual(accepted['status'],'passed',accepted)
    def test_actual_blender_export(self):
        if ASSET is None:self.skipTest('No Blender-generated asset supplied; no export claim')
        with tempfile.TemporaryDirectory() as tmp:
            report=audit(ASSET,MODULE,Path(tmp)/'export-report.json')
            self.assertEqual(report['status'],'passed',report)
            self.assertEqual(report['result']['issues']['numErrors'],0)
            self.assertEqual(report['result']['issues']['numWarnings'],0,report['result']['issues'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--validator-module',type=Path,required=True);parser.add_argument('--asset',type=Path)
    args,remaining=parser.parse_known_args();MODULE=args.validator_module.resolve();ASSET=args.asset.resolve() if args.asset else None
    unittest.main(argv=[sys.argv[0],*remaining])
