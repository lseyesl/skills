#!/usr/bin/env python3
"""Create a standalone, editable mechanical-hinge example; no character assumptions."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw


def create(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    def write(name, data):
        (out/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    Image.new('RGB', (60, 42), '#bb4433').save(out/'panel.png')
    flap = Image.new('RGBA', (68, 24))
    ImageDraw.Draw(flap).rounded_rectangle((0, 2, 66, 22), radius=5, fill='#287db5')
    flap.save(out/'flap.png')
    write('static.json', dict(schema_version='1.0', coordinate_system='image-pixels-y-down', source_size=[160, 120],
                             parts=[dict(id='opaque panel', file='panel.png', crop_origin=[24, 40], pixel_size=[60, 42])]))
    data = dict(schema_version='1.0', coordinate_system='image-pixels-y-down', source_size=[160, 120],
                nodes=[dict(id='base/control', pivot_global=[48, 60]),
                       dict(id='hinge:任意名称', parent='base/control', pivot_global=[68, 60])],
                parts=[dict(id='panel', node='base/control', file='panel.png', crop_origin=[24, 40], pixel_size=[60, 42]),
                       dict(id='flap', node='hinge:任意名称', file='flap.png', crop_origin=[68, 48], pixel_size=[68, 24])])
    write('manifest.json', data)
    poses = [dict(id='rest', frame=1), dict(id='tilt', frame=9, angles={'hinge:任意名称': 45}, translations={'base/control': [5, -3]}),
             dict(id='scale', frame=17, angles={'base/control': -10, 'hinge:任意名称': -20}, scales={'hinge:任意名称': [1.1, .9]})]
    write('poses.json', dict(poses=poses))
    write('motion.json', dict(fps=24, clips=[dict(id='mechanical hinge', frames=poses),
                                           dict(id='second take', frames=[dict(frame=1), dict(frame=5, angles={'hinge:任意名称': -30})])]))
    write('pipeline.json', dict(steps=[
        dict(id='inspect', op='check', config=dict(manifest='manifest.json', poses='poses.json', output='results/check.json')),
        dict(id='rest', op='render', config=dict(manifest='manifest.json', output='results/rest.png')),
        dict(id='preview', op='preview', config=dict(manifest='manifest.json', poses='poses.json', output='results/preview')),
        dict(id='archive', op='package', depends_on=['rest', 'inspect'], config=dict(manifest='manifest.json', files=['manifest.json', 'panel.png', 'flap.png', 'results/rest.png', 'results/check.json'], output='results/assets.zip'))]))
    write('blender.json', dict(manifest='manifest.json', motion_plan='motion.json', output='blender', render=True))
    print(out/'pipeline.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    create(parser.parse_args().output)
