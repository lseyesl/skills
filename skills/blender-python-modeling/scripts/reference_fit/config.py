"""Versioned character configuration, independent of bpy/OpenCV."""
from __future__ import annotations
import copy, hashlib, json, math
from pathlib import Path

STATES = {'needs_refinement', 'locked', 'approved', 'not_evaluable'}
KINDS = {'head', 'loft', 'sweep', 'ellipsoid', 'shoe', 'hair', 'surface_patch'}

def check_runtime(version):
    if tuple(version[:2])<(4,0) or tuple(version[:2])>=(6,0):
        raise RuntimeError('Reference fitter requires Blender 4.x/5.x capabilities; validated on 4.5.12 LTS only')

def finite(value, label, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: expected finite number')
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f'{label}: outside [{low}, {high}]')
    return value

def vector(value, n, label):
    if not isinstance(value, list) or len(value) != n: raise ValueError(f'{label}: expected {n} values')
    for v in value: finite(v, label)

def _validate(c):
    if not isinstance(c, dict) or type(c.get('schema_version'))!=int or c.get('schema_version') != 1: raise ValueError('Unsupported schema_version')
    allowed={'schema_version','character_id','reference','shape','materials','render','validation','rig','assumptions'}
    if set(c)-allowed: raise ValueError(f'Unknown config fields: {set(c)-allowed}')
    if not isinstance(c.get('character_id'), str) or not c['character_id'].replace('-','').replace('_','').isalnum(): raise ValueError('Invalid character_id')
    for required in ['reference','shape','materials','render','validation']:
        if not isinstance(c.get(required),dict):raise ValueError('Missing/invalid section: '+required)
    r=c['reference'];vector(r['image_size'],2,'image_size')
    if any(type(v)!=int or v<16 for v in r['image_size']): raise ValueError('Invalid image size')
    for key in ['image','annotation']:
        if not isinstance(r.get(key), str) or not r[key]: raise ValueError('Missing reference '+key)
    vector(r['center_px'],2,'center_px');finite(r['pixels_per_unit'],'pixels_per_unit',1)
    if r.get('units')!='normalized_character_height': raise ValueError('Explicit normalized_character_height units required')
    if not isinstance(c.get('shape'),dict) or not c['shape']: raise ValueError('No components')
    for name,p in c['shape'].items():
        if not isinstance(p,dict):raise ValueError('Component must be object: '+name)
        if not name.replace('_','').isalnum() or p.get('kind') not in KINDS: raise ValueError('Invalid component '+name)
        if p.get('state','needs_refinement') not in STATES: raise ValueError('Invalid component state')
        if p.get('material') not in c['materials']: raise ValueError('Unknown material for '+name)
        supported={'kind','material','state','label','priority','landmarks','head'}
        supported.update({
            'head':{'sections','width_scale','depth_scale','cheek_fullness','chin_taper','asymmetry','min_depth'},
            'loft':{'sections','width_scale','depth_scale','asymmetry','open','thickness','hem_wave','straps','strap_radius'},
            'sweep':{'path','radii','radius_scale','palm_scale','palm','length_scale'},
            'ellipsoid':{'center','radii','direction','surface_anchor_px','surface_offset'},
            'shoe':{'center','radii','width_scale'},
            'hair':{'center','radii','cap_extent','flow_guides','lock_radius','buns'},
            'surface_patch':{'contour_px','thickness'},
        }[p['kind']])
        if set(p)-supported:raise ValueError('Unsupported component fields: '+str(set(p)-supported))
        for key in ['width_scale','depth_scale','radius_scale','palm_scale','length_scale']:
            if key in p: finite(p[key],name+'.'+key,.1,4)
        for key in ['cheek_fullness','chin_taper','asymmetry']:
            if key in p: finite(p[key],key,0,1)
        if p['kind'] in ['head','loft']:
            rows=p['sections']
            if len(rows)<3: raise ValueError('At least 3 cross sections required')
            for row in rows:
                if len(row)!=6: raise ValueError('Section = [z, half_width, half_depth, cx, cy, rotation]')
                vector(row,6,'section');finite(row[1],'section width',1e-6);finite(row[2],'section depth',1e-6)
            if any(a[0]>=b[0] for a,b in zip(rows,rows[1:])): raise ValueError('Sections must increase in z')
            finite(p.get('thickness',.003),'thickness',0,.05)
        for key in ['hem_wave','strap_radius','surface_offset','lock_radius']:
            if key in p:finite(p[key],name+'.'+key,0,.1)
        if 'min_depth' in p:finite(p['min_depth'],name+'.min_depth',.05,1)
        if p['kind']=='surface_patch':finite(p.get('thickness',.0035),name+'.thickness',.0001,.05)
        for anchor in p.get('landmarks',{}).values():
            if anchor.get('selector') not in ['min_z','max_z','center'] or not isinstance(anchor.get('object_suffix'),str):raise ValueError('Invalid landmark anchor')
        if p.get('head') and (p['head'] not in c['shape'] or c['shape'][p['head']]['kind']!='head'):raise ValueError('Invalid head dependency')
        if p['kind']=='sweep':
            if len(p['path'])<2 or len(p['path'])!=len(p['radii']): raise ValueError('Sweep path/radii mismatch')
            for point in p['path']: vector(point,3,'path')
            if any(a==b for a,b in zip(p['path'],p['path'][1:])): raise ValueError('Degenerate sweep path')
            for radius in p['radii']: finite(radius,'radius',.0001,.5)
        if p.get('palm'):
            for key in ['center','radii','thumb_center','thumb_radii']:vector(p['palm'][key],3,'palm.'+key)
            for key in ['radii','thumb_radii']:
                for value in p['palm'][key]:finite(value,'palm radius',.0001,.5)
        if p['kind'] in ['ellipsoid','shoe']:
            vector(p['center'],3,'center');vector(p['radii'],3,'radii')
            for v in p['radii']: finite(v,'radius',.0001,1)
        if p['kind']=='hair':
            vector(p['center'],3,'hair center');vector(p['radii'],3,'hair radii')
            for v in p['radii']:finite(v,'hair radius',.0001,1)
            vector(p['cap_extent'],3,'cap_extent')
            if not p.get('flow_guides'): raise ValueError('Hair needs explicit flow_guides')
            for guide in p['flow_guides']:
                if len(guide)<2: raise ValueError('Hair guide needs >=2 points')
                for point in guide: vector(point,3,'guide')
        for path in p.get('straps',[]):
            if len(path)<2:raise ValueError('Strap path too short')
            for point in path:vector(point,3,'strap')
        if p.get('surface_anchor_px'):
            vector(p['surface_anchor_px'],2,'surface_anchor_px')
            if not p.get('head'):raise ValueError('Raised patch must attach to head')
        if p['kind']=='surface_patch':
            if p.get('head') not in c['shape'] or c['shape'][p['head']]['kind']!='head': raise ValueError('Patch needs head component')
            if len(p['contour_px'])<3: raise ValueError('Patch needs polygon')
            for point in p['contour_px']: vector(point,2,'patch point')
    for name,m in c['materials'].items():
        if set(m)-{'color','roughness','low','medium','micro','variation','seed','color_source'}:raise ValueError('Unknown material parameters')
        if not isinstance(m.get('color'),str) or len(m['color'])!=7 or not m['color'].startswith('#'): raise ValueError('Expected hex material color')
        int(m['color'][1:],16)
        for key,default,hi in [('roughness',.82,1),('low',.004,.05),('medium',.001,.02),('micro',.08,1),('variation',.035,.3)]: finite(m.get(key,default),name+'.'+key,0,hi)
        if type(m.get('seed',0))!=int: raise ValueError('Seed must be integer')
    rend=c['render']
    if rend['engine'] not in ['CYCLES','BLENDER_EEVEE_NEXT']: raise ValueError('Unsupported render engine')
    if rend.get('view_transform') not in ['Standard','AgX']: raise ValueError('Explicit color management required')
    if type(rend.get('samples'))!=int or not 1<=rend['samples']<=1024: raise ValueError('Invalid samples')
    finite(rend['exposure'],'exposure',-10,10)
    finite(rend.get('world_strength',.3),'world_strength',0,10)
    if not isinstance(rend.get('lights'),list) or not rend['lights']:raise ValueError('Fixed lights required')
    for light in rend['lights']:
        vector(light['position'],3,'light position');finite(light['energy'],'light energy',0,100000);finite(light['size'],'light size',.0001,100)
    if type(rend.get('seed',0))!=int:raise ValueError('Render seed must be integer')
    v=c['validation']
    for key in ['global_iou_target','component_iou_target','regression_tolerance','min_improvement']: finite(v[key],key,0,1)
    if type(v['max_iterations'])!=int or not 0<=v['max_iterations']<=50: raise ValueError('Invalid iteration limit')
    if v.get('alignment','none') not in ['none','bbox_similarity']:raise ValueError('Invalid alignment mode')
    for item in v.get('parameters',[]):
        part,key=item['path'].split('.',1)
        if part not in c['shape'] or key not in c['shape'][part]: raise ValueError('Unknown refinement path')
        if key not in ['width_scale','depth_scale','radius_scale','cheek_fullness','chin_taper','palm_scale','hem_wave']:raise ValueError('Parameter is not locally refinable: '+key)
        finite(c['shape'][part][key],item['path']);finite(item['step'],'step',.0001,1)
        finite(item['min'],'min');finite(item['max'],'max')
        if item['min']>=item['max'] or not item['min']<=c['shape'][part][key]<=item['max']: raise ValueError('Invalid parameter bounds')
    return c

def validate(c):
    try:return _validate(c)
    except (KeyError,TypeError,AttributeError,IndexError) as exc:
        raise ValueError('Missing or invalid configuration field: '+str(exc)) from exc

def load(path):
    path=Path(path).resolve();c=validate(json.loads(path.read_text()))
    return c,path.parent

def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def changed(a,b): return [k for k in a['shape'] if digest(a['shape'][k])!=digest(b['shape'][k])]
def dependencies(c, names):
    names=set(names)
    # Face surface and hair anchors are dependencies, not unrelated components.
    for k,p in c['shape'].items():
        if p.get('head') in names: names.add(k)
    return names

def candidate(c,path,delta):
    d=copy.deepcopy(c);part,key=path.split('.',1)
    if d['shape'][part].get('state') in ['locked','approved']: raise ValueError('Locked component')
    spec=next(v for v in c['validation']['parameters'] if v['path']==path)
    d['shape'][part][key]=max(spec['min'],min(spec['max'],d['shape'][part][key]+delta))
    return validate(d)
