"""Fail clearly when a matrix worker has the wrong Blender version."""
import argparse
import re
import subprocess
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--blender',required=True);p.add_argument('--expected-major-minor',required=True);args=p.parse_args()
    version=subprocess.check_output([args.blender,'--version'],text=True).splitlines()[0]
    match=re.match(r'Blender (\d+\.\d+)\.',version)
    if not match or match.group(1)!=args.expected_major_minor:p.error('Expected Blender '+args.expected_major_minor+', observed '+version)
    print(version)
