#!/usr/bin/env python3
"""Optional real Blender regression; uses a fresh temporary directory, never the open UI."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('create_demo', ROOT/'examples/create_demo.py')
demo = importlib.util.module_from_spec(spec); spec.loader.exec_module(demo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='puppet-blender-smoke-') as temp:
        out = Path(temp); demo.create(out)
        # Exercise explicit external/absolute input paths in the Blender adapter too.
        static = json.loads((out/'static.json').read_text())
        static['parts'][0]['file'] = str(out/'panel.png')
        (out/'static.json').write_text(json.dumps(static))
        def run(argv):
            proc = subprocess.run([args.blender, '--background', *argv], capture_output=True, text=True)
            if proc.returncode:
                print(proc.stdout[-3000:]+proc.stderr[-3000:], file=sys.stderr)
                raise RuntimeError(f'Blender exited {proc.returncode}')
        reports = {}
        for label, manifest, motion in [('static', 'static.json', None), ('hierarchy', 'manifest.json', 'motion.json')]:
            target = out/label
            cmd = ['--factory-startup', '-t', '2', '--python-exit-code', '1', '--python', str(ROOT/'scripts/blender_io.py'),
                   '--', '--manifest', str(out/manifest), '--out', str(target), '--render']
            if motion:
                cmd += ['--motion-plan', str(out/motion)]
            run(cmd)
            report = json.loads((target/'io-report.json').read_text())
            assert report['visual_review'] == 'pending'
            assert bool(report['rig_name']) == bool(motion)
            run([str(target/'rig.blend'), '-t', '2', '--python-exit-code', '1', '--python', str(ROOT/'scripts/blender_io.py'),
                 '--', '--reopen-report', str(target/'io-report.json'), '--out', str(target/'reopen.json')])
            reports[label] = json.loads((target/'reopen.json').read_text())
        print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
