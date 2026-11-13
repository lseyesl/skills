"""Reference-anchor cube teaching example. Reuses the production template.
This is blockout only; it is not a finished model or a generic asset recipe.
"""
import importlib.util
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix

_spec=importlib.util.spec_from_file_location('blockout_project',Path(__file__).resolve().parents[1]/'blender_task_template.py')
project=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(project)
project.EXECUTION_STAGE='blockout'
project.BLOCKOUT_INPUT_FILES=[__file__]
TARGET_STAGE='blockout'


def build_cube(plan,scope):
    if project.BUILD_MODE!='reference':raise RuntimeError('This teaching example requires calibrated reference anchors')
    if scope!=['body']:raise RuntimeError('The teaching example only constructs its body module')
    from reference_workspace import reference_landmark
    point=lambda name:reference_landmark(bpy.context.scene,project.TASK_ID,'front',name)
    center=point('body_center');width=(point('body_right')-point('body_left')).length;height=(point('body_top')-point('body_bottom')).length
    depth=project.BLOCKOUT_PARAMETERS.get('depth')
    if depth is None or depth<=0 or min(width,height)<=0:raise RuntimeError('Supply valid anchor dimensions and an explicitly inferred depth')
    transform=Matrix.Translation(center)@Matrix.Diagonal((width,depth,height,1))
    # Resolve geometry prerequisites before scoped replacement.
    project.remove_previous_generated_data(scope,'blockout')
    collection=bpy.data.collections.get('GEN_'+project.TASK_ID)
    if collection is None:
        collection=bpy.data.collections.new('GEN_'+project.TASK_ID);bpy.context.scene.collection.children.link(collection)
    mesh=bpy.data.meshes.new('MESH_'+project.TASK_ID+'_body');project.mark_owned(mesh,'body','blockout')
    bm=bmesh.new()
    try:
        bmesh.ops.create_cube(bm,size=1);bmesh.ops.transform(bm,matrix=transform,verts=bm.verts);bm.to_mesh(mesh)
    finally:bm.free()
    mesh.update();obj=bpy.data.objects.new('GEO_'+project.TASK_ID+'_body',mesh);collection.objects.link(obj);project.mark_owned(obj,'body','blockout')
    return [obj]

project.build_blockout=build_cube


def main():
    if TARGET_STAGE!='blockout' or project.EXECUTION_STAGE!='blockout':raise RuntimeError('Cube teaching example is blockout-only')
    result=project.main();result['sample_only']=True;return result

if __name__=='__main__':main()
