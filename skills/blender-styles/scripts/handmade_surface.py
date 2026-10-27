"""Optional three-band handmade clay. Existing soft-clay API remains unchanged."""
import math, random
import bpy
from mathutils import Vector
from mathutils.noise import noise
from clay_common import merge_config, socket
from create_clay_material import create_material

def material(name, settings, owner):
    # Reuse strict palette/color conversion and the established shader, rather than
    # creating another incompatible material configuration entry point.
    cfg=merge_config({'palette':{name:settings['color']},'material':{
        'roughness':settings.get('roughness',.82),'color_variation':settings.get('variation',.035),
        'micro_scale':420,'bump_strength':settings.get('micro',.08),'bump_distance':.0007}})
    mat=create_material(name,settings['color'],cfg,owner)
    mat['reference_fit_base_color']=settings['color']
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    old=next(n for n in nodes if n.type=='BUMP');tex=next(n for n in nodes if n.type=='TEX_COORD')
    n=nodes.new('ShaderNodeTexNoise');n.label='Localized medium clay relief';socket(n,'Scale').default_value=75
    bump=nodes.new('ShaderNodeBump');socket(bump,'Strength').default_value=.22
    socket(bump,'Distance').default_value=settings.get('medium',.001)
    links.new(socket(tex,'Object',output=True),socket(n,'Vector'))
    links.new(socket(n,'Fac',output=True),socket(bump,'Height'))
    links.new(socket(old,'Normal',output=True),socket(bump,'Normal'))
    links.new(socket(bump,'Normal',output=True),socket(bsdf,'Normal'))
    return mat

def deform(obj, settings, seed):
    """Scale-relative low frequency plus localized medium dents, deterministic per part.

    Input mesh is freshly generated (not repeatedly displaced). Surface patches are
    projected afterwards, so facial attachment is not broken by skull deformation.
    """
    if not obj.data.vertices:return
    vertices=list(obj.data.vertices)
    mins=Vector([min(v.co[i] for v in vertices) for i in range(3)])
    maxs=Vector([max(v.co[i] for v in vertices) for i in range(3)])
    size=max(maxs-mins)
    if size<1e-8:return
    rng=random.Random(seed);shift=Vector([rng.uniform(-40,40) for _ in range(3)])
    centers=[vertices[rng.randrange(len(vertices))].co.copy() for _ in range(4)]
    low=settings.get('low',.003);medium=settings.get('medium',.001)
    obj.data.update()
    normals=[v.normal.copy() for v in vertices]
    for v,normal in zip(vertices,normals):
        delta=size*low*noise(v.co/size*4+shift)
        for center in centers:
            d=(v.co-center).length/(size*.1)
            delta-=medium*math.exp(-d*d*2)
        v.co+=normal*delta
    obj.data.update()
