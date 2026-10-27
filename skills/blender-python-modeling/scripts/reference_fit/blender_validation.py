"""Fixed render channels and explicitly scoped 3D checks, for new/legacy scenes."""
from pathlib import Path
import bpy,bmesh,math,json,sys
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
from .blender_builder import OWNER,STYLE
sys.path.insert(0,str(STYLE))
from clay_common import linear_rgba,merge_config
from setup_render import setup_render


def workspace(scene,c,base):
    refs=c['reference'];owner=c['character_id']
    name=owner+'::references'
    collection=bpy.data.collections.get(name)
    if collection is None:
        collection=bpy.data.collections.new(name);scene.collection.children.link(collection)
    elif any(ob.get(OWNER)!=owner for ob in collection.objects):raise ValueError('Unowned reference collection collision')
    bases={'front':((1,0,0),(0,0,1),(0,-1,0)),
           'side':((0,1,0),(0,0,1),(1,0,0)),
           'left':((0,1,0),(0,0,1),(1,0,0)),
           'right':((0,-1,0),(0,0,1),(-1,0,0)),
           'back':((-1,0,0),(0,0,1),(0,1,0))}
    for view,item in refs.get('views',{'front':{'image':refs['image']}}).items():
        if view not in bases:raise ValueError('Reference view needs an implemented calibration basis: '+view)
        image=bpy.data.images.load(str((Path(base)/item['image']).resolve()),check_existing=True);image.pack()
        name=owner+'::reference::'+view;ob=bpy.data.objects.get(name)
        if ob is None:ob=bpy.data.objects.new(name,None);collection.objects.link(ob)
        elif ob.get(OWNER)!=owner:raise ValueError('Unowned reference object collision')
        ob.empty_display_type='IMAGE';ob.data=image;ob.empty_image_depth='FRONT';ob.empty_image_side='FRONT'
        ob.show_empty_image_only_axis_aligned=True;ob.show_empty_image_perspective=False;ob.show_empty_image_orthographic=True
        ob.use_empty_image_alpha=True;ob.color=(1,1,1,.4);ob.hide_render=True;ob.hide_select=True
        ppu=item.get('pixels_per_unit',refs['pixels_per_unit']);cx,ground=item.get('center_px',refs['center_px']);w,h=image.size
        # Blender Image Empty size denotes its largest dimension, not its width.
        ob.empty_display_size=max(w,h)/ppu;ob.empty_image_offset=(-.5,-.5)
        right,up,normal=[Vector(v) for v in bases[view]]
        ob.location=normal*.4+right*((w/2-cx)/ppu)+up*((ground-h/2)/ppu)
        ob.rotation_euler=Matrix((right,up,normal)).transposed().to_euler()
        ob.lock_location=ob.lock_rotation=ob.lock_scale=(True,True,True);ob[OWNER]=owner
        ob['fit_reference_view']=view;ob['reliability']=item.get('reliability','supplemental' if view!='front' else 'controlling')
        ob['fit_calibration']=json.dumps({'center_px':[cx,ground],'pixels_per_unit':ppu,'basis':[list(right),list(up),list(normal)],'image_size':[w,h]})
    return collection


def setup(scene,c):
    r=c['render'];ref=c['reference'];owner=c['character_id']
    # Reuse the existing tested render compatibility/socket/config path.
    cfg=merge_config({'render':{'engine':r['engine'],'device':'CPU','width':ref['image_size'][0],
        'height':ref['image_size'][1],'samples':r['samples'],'transparent':True,'view_transform':r['view_transform'],'exposure':r['exposure']}})
    setup_render(scene,cfg)
    scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
    scene.render.resolution_percentage=100
    if not scene.world or scene.world.get(OWNER)!=owner:
        scene.world=bpy.data.worlds.new(owner+'::world');scene.world[OWNER]=owner
    scene.world.use_nodes=True
    bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(1,1,1,1);bg.inputs['Strength'].default_value=r.get('world_strength',.3)
    for ob in list(scene.objects):
        if ob.get('fit_studio')==owner:
            data=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
            group=bpy.data.cameras if isinstance(data,bpy.types.Camera) else bpy.data.lights
            if data.users==0:group.remove(data)
    for i,light in enumerate(r['lights']):
        data=bpy.data.lights.new(owner+'::light'+str(i),'AREA');data.energy=light['energy'];data.shape='DISK';data.size=light['size']
        ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob['fit_studio']=owner
        ob.location=light['position'];ob.rotation_euler=(Vector((0,0,.5))-ob.location).to_track_quat('-Z','Y').to_euler()
    w,h=ref['image_size'];ppu=ref['pixels_per_unit'];cx,ground=ref['center_px']
    x=(w/2-cx)/ppu;z=(ground-h/2)/ppu
    views={'front':((x,-3,z),(x,0,z),h/ppu),'side':((3,0,.5),(0,0,.5),1.12),'back':((0,3,.5),(0,0,.5),1.12),'three_quarter':((1.8,-3,1.15),(0,0,.5),1.15)}
    for name,(position,target,scale) in views.items():
        data=bpy.data.cameras.new(owner+'::camera::'+name);data.type='ORTHO';data.ortho_scale=scale;data.clip_start=.001
        ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob['fit_studio']=owner;ob['fit_view']=name
        ob.location=position;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    scene.camera=next(o for o in scene.objects if o.get('fit_studio')==owner and o.get('fit_view')=='front')
    return cfg


def emission(name,color):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
    out=nodes.new('ShaderNodeOutputMaterial');e=nodes.new('ShaderNodeEmission');e.inputs['Color'].default_value=color;e.inputs['Strength'].default_value=1
    mat.node_tree.links.new(e.outputs[0],out.inputs['Surface']);return mat


def render_channels(scene,c,folder,quick=False):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);owner=c['character_id']
    meshes=[o for o in scene.objects if o.type=='MESH' and o.get(OWNER)==owner and not o.hide_render]
    if not meshes:raise ValueError('No owned visible model meshes')
    cameras={o['fit_view']:o for o in scene.objects if o.get('fit_studio')==owner and o.type=='CAMERA'}
    saved={o.name:list(o.data.materials) for o in meshes};temporary=[]
    original_view=(scene.view_settings.view_transform,scene.view_settings.exposure,scene.view_settings.gamma)
    original_denoise=scene.cycles.use_denoising if scene.render.engine=='CYCLES' else None
    if scene.render.engine=='CYCLES':scene.cycles.seed=c['render'].get('seed',0)
    scene.view_settings.gamma=1
    names=sorted({o.get('fit_label',o['fit_component']) for o in meshes})
    colors={name:[40+(i*71)%190,40+(i*113)%190,40+(i*149)%190] for i,name in enumerate(names)}
    def capture(channel,view):
        path=folder/(channel+'_'+view+'.png')
        if path.exists():raise FileExistsError(path)
        scene.camera=cameras[view];scene.render.filepath=str(path);bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True,scene=scene.name)
    try:
        for view in ['front'] if quick else ['front','side','back','three_quarter']:capture('beauty',view)
        for channel in ['silhouette','labels','albedo','clay']:
            scene.view_settings.view_transform='Standard';scene.view_settings.exposure=0
            if scene.render.engine=='CYCLES':
                scene.cycles.samples=8 if channel!='clay' else min(c['render']['samples'],8)
                # Denoising discrete IDs can change a distant part boundary when
                # an unrelated limb changes. Metric passes must remain local.
                scene.cycles.use_denoising=channel=='clay'
            cache={}
            for ob in meshes:
                label=ob.get('fit_label',ob['fit_component']);source=saved[ob.name][0]
                if channel=='silhouette':key='white';color=(1,1,1,1)
                elif channel=='labels':key=label;color=linear_rgba('#'+''.join(f'{v:02x}' for v in colors[label]))
                elif channel=='albedo':key=source.name;color=source.diffuse_color[:]
                else:key='neutral';color=(.45,.45,.45,1)
                if key not in cache:
                    if channel=='clay':
                        mat=bpy.data.materials.new('fit-neutral');mat.use_nodes=True
                        p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=.82
                    else:mat=emission('fit-'+channel+'-'+key,color)
                    cache[key]=mat;temporary.append(mat)
                ob.data.materials.clear();ob.data.materials.append(cache[key])
            capture(channel,'front')
        scene.camera=cameras['front'];w,h=c['reference']['image_size'];landmarks={}
        for key,p in c['shape'].items():
            for name,anchor in p.get('landmarks',{}).items():
                obs=[o for o in meshes if o.get('fit_component')==key and o.name.endswith('::'+anchor['object_suffix'])]
                if not obs:continue
                points=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
                position=Vector([(min(v[i] for v in points)+max(v[i] for v in points))/2 for i in range(3)])
                if anchor['selector']=='min_z':position.z=min(v.z for v in points)
                if anchor['selector']=='max_z':position.z=max(v.z for v in points)
                q=world_to_camera_view(scene,scene.camera,position);landmarks[name]=[q.x*w,(1-q.y)*h]
        record={'blender':bpy.app.version_string,'engine':scene.render.engine,'resolution':[w,h],'view_transform_beauty':c['render']['view_transform'],'exposure_beauty':c['render']['exposure'],'metric_pass_transform':'Standard exposure=0 gamma=1','part_colors':colors,'landmarks_px':landmarks,'camera':{'type':'ORTHO','position':list(scene.camera.location),'ortho_scale':scene.camera.data.ortho_scale},'scope':'visible semantic parts; albedo is unlit base color, no reference relighting','quick':quick}
        (folder/'render-record.json').write_text(json.dumps(record,indent=2));return record
    finally:
        for ob in meshes:ob.data.materials.clear();[ob.data.materials.append(m) for m in saved[ob.name]]
        for mat in temporary:
            if not mat.users:bpy.data.materials.remove(mat)
        scene.view_settings.view_transform,scene.view_settings.exposure,scene.view_settings.gamma=original_view
        if scene.render.engine=='CYCLES':
            scene.cycles.samples=c['render']['samples'];scene.cycles.use_denoising=original_denoise


def structure(scene,c):
    owner=c['character_id'];report={'meshes':{},'errors':[],'warnings':[],'intersection_scope':'Connection endpoints and AABB broad phase only; arbitrary mesh self/intersections not certified.','rig_status':'not_requested'}
    for ob in scene.objects:
        if ob.get(OWNER)!=owner or ob.type!='MESH':continue
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();bm=bmesh.new();bm.from_mesh(mesh)
        bad=sum(not e.is_manifold for e in bm.edges);degenerate=sum(f.calc_area()<1e-12 for f in bm.faces)
        winding=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        volume=bm.calc_volume(signed=True)
        finite=all(math.isfinite(v) for p in mesh.vertices for v in p.co)
        report['meshes'][ob.name]={'non_manifold_edges':bad,'inconsistent_winding_edges':winding,'degenerate_faces':degenerate,'signed_volume':volume,'finite':finite,'dimensions':list(ob.dimensions)}
        if not finite or bad or winding or degenerate or volume<=0:report['errors'].append(ob.name+': invalid topology/normals')
        bm.free();ev.to_mesh_clear()
    # Minimum depth floor protects against a front-view optimizer flattening the head.
    for key,p in c['shape'].items():
        if p['kind']=='head':
            obs=[o for o in scene.objects if o.get('fit_component')==key and o.get(OWNER)==owner]
            if not obs or obs[0].dimensions.y<p.get('min_depth',.2):report['errors'].append(key+': insufficient depth')
        if p['kind']=='sweep' and 'palm' in p:
            distance=(Vector(p['path'][-1])-Vector(p['palm']['center'])).length
            if distance>max(p['palm']['radii'])*p.get('palm_scale',1)+p['radii'][-1]*p.get('radius_scale',1):report['errors'].append(key+': disconnected palm')
    for link in c.get('validation',{}).get('connections',[]):
        a,b=[next((o for o in scene.objects if o.get('fit_component')==part and o.get(OWNER)==owner),None) for part in link['components']]
        if a is None or b is None:report['errors'].append('Missing connection component');continue
        if link.get('mode')=='endpoint_surface':
            from mathutils.bvhtree import BVHTree
            p=c['shape'][link['components'][0]]
            position=Vector(p['path'][0 if link.get('endpoint','start')=='start' else -1])
            radius=p['radii'][0 if link.get('endpoint','start')=='start' else -1]*p.get('radius_scale',1)
            ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
            bm=bmesh.new();bm.from_mesh(mesh);tree=BVHTree.FromBMesh(bm);bm.free();ev.to_mesh_clear()
            hit,normal,_,distance=tree.find_nearest(position)
            # Nearest outward normal supports these convex socket targets; this
            # is explicitly narrower than an arbitrary concave collision solver.
            if hit is None or ((position-hit).dot(normal)>0 and distance>radius+link.get('tolerance',.004)):
                report['errors'].append('Disconnected limb socket: '+str(link['components']))
            continue
        aa=[a.matrix_world@Vector(v) for v in a.bound_box];bb=[b.matrix_world@Vector(v) for v in b.bound_box]
        overlap=all(max(v[i] for v in aa)>=min(v[i] for v in bb)-link.get('tolerance',.005) and max(v[i] for v in bb)>=min(v[i] for v in aa)-link.get('tolerance',.005) for i in range(3))
        if not overlap:report['errors'].append('Connection AABBs separate: '+str(link['components']))
    report['ok']=not report['errors'];return report


def rig_probe(scene,c):
    """Actually skin disposable limb copies and bend joints. Not production rig approval."""
    owner=c['character_id'];results=[]
    for key,p in c['shape'].items():
        if p['kind']!='sweep':continue
        src=next(o for o in scene.objects if o.get(OWNER)==owner and o.get('fit_component')==key and o.name.endswith('::limb'))
        ob=src.copy();ob.data=src.data.copy();scene.collection.objects.link(ob)
        arm=bpy.data.armatures.new('fit-rig-probe');rig=bpy.data.objects.new(arm.name,arm);scene.collection.objects.link(rig)
        bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
        path=p['path'];a=Vector(path[0]);b=Vector(path[len(path)//2]);d=Vector(path[-1])
        first=arm.edit_bones.new('upper');first.head=a;first.tail=b
        second=arm.edit_bones.new('lower');second.head=b;second.tail=d;second.parent=first;second.use_connect=True
        bpy.ops.object.mode_set(mode='OBJECT')
        upper=ob.vertex_groups.new(name='upper');lower=ob.vertex_groups.new(name='lower')
        axis=(d-a);length=axis.length_squared
        for v in ob.data.vertices:
            t=max(0,min(1,(v.co-a).dot(axis)/length));weight=max(0,min(1,(t-.35)/.3))
            upper.add([v.index],1-weight,'REPLACE');lower.add([v.index],weight,'REPLACE')
        mod=ob.modifiers.new('probe','ARMATURE');mod.object=rig
        rig.pose.bones['lower'].rotation_mode='XYZ';rig.pose.bones['lower'].rotation_euler[1]=.45;bpy.context.view_layer.update()
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
        displacement=max((v.co-ob.data.vertices[i].co).length for i,v in enumerate(me.vertices))
        ok=displacement>.0001 and all(math.isfinite(x) for v in me.vertices for x in v.co)
        results.append({'component':key,'ok':ok,'max_displacement':displacement,'angle_radians':.45});ev.to_mesh_clear()
        data=ob.data;bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(data)
        bpy.data.objects.remove(rig,do_unlink=True);bpy.data.armatures.remove(arm)
    return {'ok':bool(results) and all(r['ok'] for r in results),'limbs':results,'scope':'Disposable two-bone skinning/bend smoke test only. Production rig, shoulder/cloth deformation and all poses unvalidated.'}
