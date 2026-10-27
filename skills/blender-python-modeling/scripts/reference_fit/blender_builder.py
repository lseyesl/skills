"""Owned component builders; no scene clearing or role-specific coordinates."""
from pathlib import Path
import math,sys,random,json
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon
from .geometry import loft,path_samples,part_seed
from .config import digest,dependencies
STYLE=Path(__file__).resolve().parents[3]/'blender-styles'/'scripts'
sys.path.insert(0,str(STYLE))
from handmade_surface import material,deform

OWNER='reference_fit_owner'

def mesh_object(scene,owner,part,suffix,verts,faces,mat):
    name=f'{owner}::{part}::{suffix}'
    if bpy.data.objects.get(name):raise ValueError('Stable object name collision: '+name)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob)
    ob[OWNER]=owner;ob['fit_component']=part;ob['fit_stable_id']=name
    ob.data.materials.append(mat)
    for p in mesh.polygons:p.use_smooth=True
    return ob


def ellipsoid(scene,owner,part,suffix,center,radii,mat,direction=None):
    # Explicit ring ordering keeps localized dent seeds stable across rebuilds;
    # bmesh operator allocation/traversal order is not an object identity contract.
    n=40;m=28;unit=[Vector((0,0,-1))]
    for j in range(1,m):
        latitude=-math.pi/2+j*math.pi/m
        for i in range(n):
            angle=i*math.tau/n
            unit.append(Vector((math.cos(latitude)*math.cos(angle),math.cos(latitude)*math.sin(angle),math.sin(latitude))))
    unit.append(Vector((0,0,1)));top=len(unit)-1
    faces=[]
    for i in range(n):faces.append((0,1+(i+1)%n,1+i))
    for j in range(m-2):
        for i in range(n):
            a=1+j*n+i;b=1+j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
    for i in range(n):faces.append((top,1+(m-2)*n+i,1+(m-2)*n+(i+1)%n))
    q=Vector(direction).to_track_quat('Z','Y') if direction else None
    verts=[]
    for v in unit:
        point=Vector([v[i]*radii[i] for i in range(3)])
        verts.append(tuple((q@point if q else point)+Vector(center)))
    return mesh_object(scene,owner,part,suffix,verts,faces,mat)


def sweep(scene,owner,part,suffix,path,radii,mat,flatten=1):
    samples=path_samples(path,radii);verts=[];faces=[];n=20
    for i,row in enumerate(samples):
        c=Vector(row[:3]);t=Vector(samples[min(i+1,len(samples)-1)][:3])-Vector(samples[max(0,i-1)][:3]);t.normalize()
        axis=Vector((0,1,0)) if abs(t.y)<.9 else Vector((1,0,0))
        u=t.cross(axis).normalized();v=t.cross(u).normalized()
        for j in range(n):
            a=j*math.tau/n;verts.append(tuple(c+row[3]*(u*math.cos(a)+v*math.sin(a)*flatten)))
    for i in range(len(samples)-1):
        for j in range(n):a=i*n+j;b=i*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    faces += [tuple(range(n-1,-1,-1)),tuple((len(samples)-1)*n+j for j in range(n))]
    return mesh_object(scene,owner,part,suffix,verts,faces,mat)


def patch(scene,owner,part,p,mat,c):
    heads=[o for o in scene.objects if o.get('fit_component')==p['head'] and o.get(OWNER)==owner]
    head=heads[0];dg=bpy.context.evaluated_depsgraph_get();ev=head.evaluated_get(dg);hm=ev.to_mesh()
    bm=bmesh.new();bm.from_mesh(hm);bvh=BVHTree.FromBMesh(bm);bm.free();ev.to_mesh_clear()
    r=c['reference'];cx,ground=r['center_px'];ppu=r['pixels_per_unit']
    poly=[Vector(((x-cx)/ppu,0,(ground-y)/ppu)) for x,y in p['contour_px']]
    tris=tessellate_polygon([poly]);lookup={tuple(v):i for i,v in enumerate(poly)}
    tris=[tuple(t) if isinstance(t[0],int) else tuple(lookup[tuple(v)] for v in t) for t in tris]
    temp=bpy.data.meshes.new('fit-temp');temp.from_pydata(poly,[],tris)
    bm=bmesh.new();bm.from_mesh(temp)
    # Collinear raster contour vertices can produce zero-area tessellation
    # triangles. Clean the planar triangulation BEFORE dense subdivision.
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=9,use_grid_fill=True)
    bm.verts.ensure_lookup_table();bm.verts.index_update();n=len(bm.verts)
    boundary=[tuple(v.index for v in e.verts) for e in bm.edges if e.is_boundary]
    faces=[];verts=[]
    for offset in [-.0004,p.get('thickness',.0035)]:
        for v in bm.verts:
            hit,normal,*_=bvh.ray_cast(Vector((v.co.x,-3,v.co.z)),Vector((0,1,0)),6)
            if hit is None:raise ValueError('Facial anchor outside skull: '+part)
            if normal.y>0:normal=-normal
            verts.append(tuple(hit+normal*offset))
    for f in bm.faces:
        ids=tuple(v.index for v in f.verts);faces += [tuple(reversed(ids)),tuple(i+n for i in ids)]
    faces.extend((i,j,j+n,i+n) for i,j in boundary);bm.free();bpy.data.meshes.remove(temp)
    ob=mesh_object(scene,owner,part,'patch',verts,faces,mat)
    # The sampled outline is already smooth. A fixed-width bevel on subpixel
    # triangulated edges creates collapsed faces; retain the closed extrusion.
    ob.parent=head # coordinates remain in normalized head-local frame (head at identity)
    return [ob]


def build_component(scene,c,part,mats):
    owner=c['character_id'];p=c['shape'][part];mat=mats[p['material']];kind=p['kind'];objects=[]
    if kind in ['head','loft']:
        verts,faces=loft(p);ob=mesh_object(scene,owner,part,'body',verts,faces,mat);objects.append(ob)
        if p.get('open'):
            solid=ob.modifiers.new('physical clay shell','SOLIDIFY');solid.thickness=p.get('thickness',.005);solid.offset=-1
        for i,path in enumerate(p.get('straps',[])):
            objects.append(sweep(scene,owner,part,'strap_'+str(i),path,[p.get('strap_radius',.012)]*len(path),mat,flatten=.55))
    elif kind=='sweep':
        radius=[r*p.get('radius_scale',1) for r in p['radii']]
        path=[list(v) for v in p['path']]
        if 'length_scale' in p:
            origin=Vector(path[0]);path=[tuple(origin+(Vector(v)-origin)*p['length_scale']) for v in path]
        objects.append(sweep(scene,owner,part,'limb',path,radius,mat))
        if 'palm' in p:
            palm=p['palm'];r=[v*p.get('palm_scale',1) for v in palm['radii']]
            direction=Vector(path[-1])-Vector(path[-2])
            shift=Vector(path[-1])-Vector(p['path'][-1])
            objects.append(ellipsoid(scene,owner,part,'palm',Vector(palm['center'])+shift,r,mat,direction))
            objects.append(ellipsoid(scene,owner,part,'thumb',Vector(palm['thumb_center'])+shift,palm['thumb_radii'],mat,direction))
    elif kind=='ellipsoid':
        center=p['center']
        if p.get('surface_anchor_px'):
            head=next(o for o in scene.objects if o.get(OWNER)==owner and o.get('fit_component')==p['head'])
            bm=bmesh.new();bm.from_mesh(head.data);bvh=BVHTree.FromBMesh(bm);bm.free()
            x,z=p['surface_anchor_px'];r=c['reference'];x=(x-r['center_px'][0])/r['pixels_per_unit'];z=(r['center_px'][1]-z)/r['pixels_per_unit']
            hit,normal,*_=bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)),6)
            if hit is None:raise ValueError('Raised facial anchor outside head: '+part)
            if normal.y>0:normal=-normal
            center=hit+normal*p.get('surface_offset',.008)
        objects.append(ellipsoid(scene,owner,part,'body',center,p['radii'],mat,p.get('direction')))
    elif kind=='shoe':
        x,y,z=p['center'];rx,ry,rz=p['radii'];scale=p.get('width_scale',1);rx*=scale
        objects.append(ellipsoid(scene,owner,part,'toe',(x,y-ry*.22,z),(rx,ry,rz),mat))
        # Closed volumetric upper + annular cuff/opening + flattened sole.
        objects.append(ellipsoid(scene,owner,part,'upper',(x,y+ry*.25,z+rz*.3),(rx*.82,ry*.65,rz*.8),mat))
        n=48;verts=[];faces=[]
        for zz,r in [(z+rz*.75,1),(z+rz*.95,1),(z+rz*.95,.7),(z+rz*.75,.7)]:
            for i in range(n):a=i*math.tau/n;verts.append((x+rx*.65*r*math.cos(a),y+ry*.4+ry*.35*r*math.sin(a),zz))
        for j in range(4):
            for i in range(n):a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,(j+1)%4*n+(i+1)%n,(j+1)%4*n+i))
        objects.append(mesh_object(scene,owner,part,'opening_rim',verts,faces,mat))
        sole=ellipsoid(scene,owner,part,'sole',(x,y,z-rz*.7),(rx*1.02,ry*1.03,rz*.25),mat)
        objects.append(sole)
    elif kind=='hair':
        cx,cy,cz=p['center'];rx,ry,rz=p['radii'];n=64;m=28;verts=[];faces=[]
        for j in range(m+1):
            for i in range(n):
                t=i*math.tau/n
                end=p['cap_extent'][0]+p['cap_extent'][1]*max(0,-math.sin(t))+p['cap_extent'][2]*max(0,math.sin(t))
                a=.008+(end-.008)*j/m
                verts.append((cx+rx*math.sin(a)*math.cos(t),cy+ry*math.sin(a)*math.sin(t),cz+rz*math.cos(a)))
        for j in range(m):
            for i in range(n):a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
        faces.append(tuple(range(n-1,-1,-1)))
        ob=mesh_object(scene,owner,part,'cap',verts,faces,mat);solid=ob.modifiers.new('clay cap thickness','SOLIDIFY');solid.thickness=.004;objects.append(ob)
        for i,guide in enumerate(p['flow_guides']):
            radii=[p.get('lock_radius',.014)*(.5+.5*math.sin(math.pi*j/(len(guide)-1))) for j in range(len(guide))]
            objects.append(sweep(scene,owner,part,'directed_lock_'+str(i),guide,radii,mat,flatten=.45))
        rng=random.Random(part_seed(c['materials'][p['material']]['seed'],part))
        for i,bun in enumerate(p.get('buns',[])):
            center=bun['center'];rad=bun['radii']
            objects.append(ellipsoid(scene,owner,part,'bun_'+str(i),center,rad,mat))
            # A small number of elongated, tangential arcs over a continuous mass.
            for k in range(5):
                phase=k*math.tau/5;guide=[]
                for j in range(9):
                    a=-1.2+j*.3;guide.append((center[0]+rad[0]*math.sin(a)*math.cos(phase),center[1]-rad[1]*math.cos(a),center[2]+rad[2]*math.sin(a)*math.sin(phase)))
                rr=.010*rng.uniform(.85,1.2)
                objects.append(sweep(scene,owner,part,f'bun_{i}_fold_{k}',guide,[rr]*len(guide),mat,flatten=.65))
    elif kind=='surface_patch':return patch(scene,owner,part,p,mat,c)
    else:raise ValueError(kind)
    settings=c['materials'][p['material']]
    for ob in objects:deform(ob,settings,part_seed(settings['seed'],ob['fit_stable_id']))
    return objects


def fingerprints(scene,owner):
    out={}
    for ob in scene.objects:
        if ob.get(OWNER)!=owner or ob.type!='MESH':continue
        # Includes topology, transforms, modifiers, material identity and node data.
        mats=[]
        for m in ob.data.materials:
            mats.append((m.name,[(n.bl_idname,[(s.name,str(s.default_value)) for s in n.inputs if hasattr(s,'default_value')]) for n in m.node_tree.nodes],[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links]))
        out[ob['fit_stable_id']]=digest({'v':[list(v.co) for v in ob.data.vertices],'f':[list(p.vertices) for p in ob.data.polygons],'matrix':[list(r) for r in ob.matrix_world],'materials':mats,'modifiers':[(m.type,getattr(m,'thickness',None),getattr(m,'width',None)) for m in ob.modifiers]})
    return out


def build(c,scene=None,only=None):
    scene=scene or bpy.data.scenes.new('Fit_'+c['character_id']);bpy.context.window.scene=scene
    owner=c['character_id'];scene[OWNER]=owner
    requested=set(only or c['shape']);affected=dependencies(c,requested)
    for key in affected:
        if c['shape'][key].get('state') in ['locked','approved'] and only:raise ValueError('Cannot rebuild locked component/dependency '+key)
    # Material tree reuse is essential for locks: constructing one component must
    # never recreate a shared shader used by an unchanged component.
    mats={}
    for key,settings in c['materials'].items():
        role=owner+'::'+key
        existing=next((m for m in bpy.data.materials if m.get('fit_material_id')==role),None)
        if existing and existing.get('fit_settings_hash')!=digest(settings):
            if only:raise ValueError('Shared material changed during local geometry update')
            existing=None
        mat=existing or material(key,settings,owner)
        mat['fit_material_id']=role;mat['fit_settings_hash']=digest(settings);mats[key]=mat
    for ob in list(scene.objects):
        if ob.get(OWNER)==owner and ob.get('fit_component') in affected:
            data=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
            if data.users==0:bpy.data.meshes.remove(data)
    order=[k for k in c['shape'] if k in affected and not c['shape'][k].get('head')]+[k for k in c['shape'] if k in affected and c['shape'][k].get('head')]
    for key in order:build_component(scene,c,key,mats)
    bpy.context.view_layer.update();scene['fit_config']=json.dumps(c,sort_keys=True)
    return scene,sorted(affected)
