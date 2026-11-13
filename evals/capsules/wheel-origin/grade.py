"""Independent numeric acceptance; no golden repair implementation is exposed."""
import bpy
import math,json,sys
from pathlib import Path
from mathutils import Vector
source,target,report=map(Path,sys.argv[sys.argv.index('--')+1:])
def sample():
    wheel=bpy.data.objects.get('Wheel');other=bpy.data.objects.get('PreserveMe')
    if not wheel or wheel.type!='MESH' or not other:raise ValueError('Required objects missing')
    graph=bpy.context.evaluated_depsgraph_get()
    geometry=[tuple(wheel.matrix_world@v.co) for v in wheel.evaluated_get(graph).data.vertices]
    preserved={'matrix':[list(row) for row in other.matrix_world],'vertices':[list(v.co) for v in other.data.vertices]}
    return geometry,preserved
bpy.ops.wm.open_mainfile(filepath=str(source));original,preserved=sample()
checks={};details={}
try:
    bpy.ops.wm.open_mainfile(filepath=str(target));actual,current=sample();wheel=bpy.data.objects['Wheel']
    # Bidirectional nearest distances allow equivalent reordered topology.
    def distance(a,b):return max(min((Vector(v)-Vector(w)).length for w in b) for v in a)
    difference=max(distance(original,actual),distance(actual,original))
    checks['rest_geometry']=difference<1e-5;checks['preservation']=preserved==current
    centers=[]
    for i in range(9):
        wheel.rotation_euler.z=math.tau*i/8;bpy.context.view_layer.update()
        evaluated=wheel.evaluated_get(bpy.context.evaluated_depsgraph_get())
        centers.append(sum((evaluated.matrix_world@v.co for v in evaluated.data.vertices),Vector())/len(evaluated.data.vertices))
    excursion=max((v-centers[0]).length for v in centers)
    checks['rotation']=excursion<1e-5
    details={'rest_max_distance':difference,'center_excursion':excursion}
except Exception as exc:
    checks={'rest_geometry':False,'preservation':False,'rotation':False};details={'error':str(exc)}
report.write_text(json.dumps({'checks':checks,'details':details,'scope':'wheel-origin numeric repair only; no visual certification'},indent=2))
