"""Persistent rig construction from explicit reviewed 3D joints and vertex weights.
No automatic anatomy inference, existing-rig replacement, or deformation certification.
"""
import math
import bpy
from mathutils import Vector
from domain_checks import weight_issues,inspect_weights


def build_rig(scene, name, bones, bindings, *, influence_limit=4, preserve_volume=False):
    """bones: ordered dictionaries (name/head/tail/parent); bindings: mesh -> per-vertex weight dicts."""
    if bpy.context.scene is not scene or bpy.context.mode!='OBJECT':raise ValueError('Active source scene in Object Mode required')
    if not bones or not bindings or bpy.data.objects.get(name):raise ValueError('New rig name, explicit bones and bindings required')
    names=set()
    for bone in bones:
        if not isinstance(bone.get('name'),str) or not bone['name'] or bone['name'] in names:raise ValueError('Unique bone names required')
        for key in ('head','tail'):
            if len(bone[key])!=3 or not all(math.isfinite(v) for v in bone[key]):raise ValueError('Finite world-space joints required')
        if (Vector(bone['tail'])-Vector(bone['head'])).length<=1e-8:raise ValueError('Zero-length bone')
        if type(bone.get('roll',0.0)) not in (int,float) or not math.isfinite(bone.get('roll',0.0)):raise ValueError('Finite explicit bone roll required')
        if bone.get('parent') is not None and bone['parent'] not in names:raise ValueError('Parent must precede child')
        names.add(bone['name'])
    for obj,rows in bindings.items():
        if scene.objects.get(obj.name) is not obj or obj.type!='MESH' or not obj.data.vertices or any(m.type=='ARMATURE' for m in obj.modifiers):raise ValueError('Explicit nonempty unrigged scene mesh required; existing rigs use repair workflow')
        if set(obj.vertex_groups.keys())&names:raise ValueError('Refuse to overwrite existing vertex groups')
        if len(rows)!=len(obj.data.vertices) or any(not isinstance(row,dict) or set(row)-names for row in rows):raise ValueError('Exact per-vertex deform weights required')
        if any(weight_issues([list(row.values()) for row in rows],influence_limit).values()):raise ValueError('Invalid/unweighted/excess-influence binding')
    active=bpy.context.view_layer.objects.active;selected=list(bpy.context.selected_objects)
    arm=bpy.data.armatures.new(name);rig=bpy.data.objects.new(name,arm);scene.collection.objects.link(rig)
    try:
        for obj in selected:obj.select_set(False)
        rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
        for bone in bones:
            edit=arm.edit_bones.new(bone['name']);edit.head=bone['head'];edit.tail=bone['tail']
            edit.roll=bone.get('roll',0.0)
            if bone.get('parent'):edit.parent=arm.edit_bones[bone['parent']]
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj,rows in bindings.items():
            groups={key:obj.vertex_groups.new(name=key) for key in names}
            for index,row in enumerate(rows):
                for key,value in row.items():
                    if value>0:groups[key].add([index],value,'REPLACE')
            mod=obj.modifiers.new('PersistentSkin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=preserve_volume
        return rig
    finally:
        if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
        rig.select_set(False)
        for obj in selected:obj.select_set(True)
        bpy.context.view_layer.objects.active=active


def rig_inventory(meshes, rig, *, influence_limit=4):
    if rig.type!='ARMATURE' or not meshes:raise ValueError('Persistent armature and target meshes required')
    records=[inspect_weights(obj,influence_limit) for obj in meshes]
    return {'rig':rig.name,'bones':{b.name:b.parent.name if b.parent else None for b in rig.data.bones},
        'meshes':records,'weights_valid':all(r['armature']==rig.name and not any(r['issues'].values()) for r in records),
        'scope':'persistent structure and weight numbers only; shoulder/elbow/knee surface inspection and export motion remain required'}
