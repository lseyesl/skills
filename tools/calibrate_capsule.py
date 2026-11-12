"""Calibrate the wheel-origin grader on golden, unchanged, and damaged fixtures.
Golden construction remains outside Agent-visible workspaces.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from agent_benchmark import execute,write
from run_evals import digest


def calibrate(capsule_dir,output,blender):
    capsule_dir=Path(capsule_dir).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Calibration output must be new')
    output.mkdir(parents=True)
    prepare=execute([blender,'--background','--factory-startup','--python-exit-code','1','--python',capsule_dir/'prepare.py','--',output/'inputs'],output,output/'prepare',90)
    if prepare['returncode']!=0:raise RuntimeError('Fixture preparation failed')
    generator=output/'golden.py'
    generator.write_text('''import bpy,sys
from pathlib import Path
from mathutils import Vector,Matrix
root=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.wm.open_mainfile(filepath=str(root/'inputs/source.blend'))
wheel=bpy.data.objects['Wheel']
center=sum((v.co for v in wheel.data.vertices),Vector())/len(wheel.data.vertices)
wheel.data.transform(Matrix.Translation(-center));wheel.matrix_world=wheel.matrix_world@Matrix.Translation(center)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(root/'golden.blend'))
# Equivalent correct solution with reordered vertices: grader must not require golden ordering.
old=wheel.data
vertices=[tuple(v.co) for v in reversed(old.vertices)]
faces=[tuple(len(vertices)-1-i for i in polygon.vertices) for polygon in old.polygons]
mesh=bpy.data.meshes.new('reordered-mesh');mesh.from_pydata(vertices,[],faces);mesh.update();wheel.data=mesh
bpy.ops.wm.save_as_mainfile(filepath=str(root/'reordered.blend'))
bpy.data.objects['PreserveMe'].location.x+=1
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(root/'damaged.blend'))
''')
    generation=execute([blender,'--background','--factory-startup','--python-exit-code','1','--python',generator,'--',output],output,output/'generate',90)
    if generation['returncode']!=0:raise RuntimeError('Golden generation failed')
    expected={'golden':{'rest_geometry':True,'preservation':True,'rotation':True},
              'reordered':{'rest_geometry':True,'preservation':True,'rotation':True},
              'unchanged':{'rest_geometry':True,'preservation':True,'rotation':False},
              'damaged':{'rest_geometry':True,'preservation':False,'rotation':True}}
    reports={}
    for name in expected:
        target=output/'inputs/source.blend' if name=='unchanged' else output/(name+'.blend')
        report=output/(name+'.json')
        execution=execute([blender,'--background','--factory-startup','--python-exit-code','1','--python',capsule_dir/'grade.py','--',output/'inputs/source.blend',target,report],output,output/name,90)
        observed=json.loads(report.read_text()) if report.is_file() else {}
        reports[name]={'expected':expected[name],'observed':observed,'passed':execution['returncode']==0 and observed.get('checks')==expected[name]}
    result={'schema_version':1,'passed':all(v['passed'] for v in reports.values()),'cases':reports,
            'fingerprints':{name:digest(capsule_dir/name) for name in ('capsule.json','prepare.py','grade.py','task.md')},
            'blender':subprocess.check_output([blender,'--version'],text=True).splitlines()[0],
            'scope':'Numeric wheel-origin grader only; no Agent or visual quality certification'}
    write(output/'calibration.json',result);return result


def validate_calibration(capsule_dir,path,blender_version=None):
    capsule_dir=Path(capsule_dir);data=json.loads(Path(path).read_text())
    if data.get('passed') is not True or data.get('schema_version')!=1:raise ValueError('Grader calibration failed')
    if blender_version is not None and data.get('blender') != blender_version:raise ValueError('Calibration environment changed')
    if set(data.get('cases',{})) != {'golden','reordered','unchanged','damaged'} or not all(case.get('passed') is True and case.get('observed',{}).get('checks')==case.get('expected') for case in data['cases'].values()):raise ValueError('Missing/failed calibration controls')
    required={'capsule.json','prepare.py','grade.py','task.md'}
    if set(data.get('fingerprints',{}))!=required or any(data['fingerprints'][name]!=digest(capsule_dir/name) for name in required):
        raise ValueError('Stale calibration; capsule changed')
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capsule',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--blender',default=shutil.which('blender') or 'blender')
    args=p.parse_args();result=calibrate(args.capsule,args.output,args.blender);print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
