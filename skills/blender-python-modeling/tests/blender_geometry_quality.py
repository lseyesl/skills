"""Synthetic real-Blender controls: geometry layers, aggregate budgets, delivery rejection.
These fixtures do not establish image-reconstruction or general Skill gains.
"""
import bpy,json,sys,uuid,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from production_checks import inspect_mesh,inspect_asset,require_asset_geometry,GeometryRejected
from asset_delivery import export_glb
from isolated_delivery import sample
from blockout_gate import resource_limits
out=Path(sys.argv[sys.argv.index('--')+1]).resolve()/('run-'+uuid.uuid4().hex[:10]);out.mkdir(parents=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
checks={}
def check(name,value):assert value,name;checks[name]=True
def rejected(name,fn):
 try:fn()
 except (ValueError,RuntimeError) as exc:checks[name]=True;return exc
 raise AssertionError('Accepted invalid control: '+name)
def mesh(name,points,faces):
 data=bpy.data.meshes.new(name);data.from_pydata(points,[],faces);data.update();obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
 mat=bpy.data.materials.new(name+'PBR');mat.use_nodes=True;data.materials.append(mat);return obj
plane=mesh('LegalOpenSheet',[(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[(0,1,2,3)])
check('intentional_open_sheet_allowed',not inspect_mesh(plane)['structural_issues'])
rejected('closed_surface_contract_rejects_open_sheet',lambda:require_asset_geometry([plane],stage='delivery',require_closed=True))
solid=plane.modifiers.new('Intentional thickness','SOLIDIFY');solid.thickness=.1
report=inspect_mesh(plane,True)
check('open_control_cage_with_closed_evaluated_shell_allowed',report['source_geometry']['boundary_edges']>0 and not report['structural_issues'])
plane.modifiers.remove(solid)
rejected('position_weld_does_not_fill_real_opening',lambda:require_asset_geometry([plane],stage='reimport',require_closed=True,seam_weld_distance=1e-5))
# A positive-area polygon whose tessellation has a zero-area triangle.
bad=mesh('PositiveAreaBadTessellation',[(0,0,0),(1,0,0),(1,1,0),(1,1,0),(0,1,0)],[(0,1,2,3,4)])
report=inspect_mesh(bad)
check('polygon_area_alone_misses_bad_triangle',report['degenerate_faces']==0 and report['degenerate_triangles']>0)
check('triangle_failure_names_polygon',bool(report['triangle_examples']) and report['triangle_examples'][0]['polygon']==0)
rejected('bad_tessellation_blocks_stage',lambda:require_asset_geometry([bad],stage='refine'))
baseline_checks={}
if '--baseline-checker' in sys.argv:
 path=Path(sys.argv[sys.argv.index('--baseline-checker')+1]);spec=importlib.util.spec_from_file_location('baseline_geometry_checker',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 previous=old.inspect_mesh(bad)
 baseline_checks['same_bad_ngon']={'baseline_polygon_degenerate_faces':previous['degenerate_faces'],
     'baseline_accepted':not previous['structural_issues'],'candidate_rejected':bool(report['structural_issues']),
     'scope':'same synthetic input, expanded triangulation coverage; not an Agent modeling success'}
 baseline_checks['same_legal_open_sheet']={'baseline_accepted':not old.inspect_mesh(plane)['structural_issues'],
     'candidate_accepted':not inspect_mesh(plane)['structural_issues']}
before=[tuple(v.co) for v in bad.data.vertices];inspect_mesh(bad)
check('inspection_never_repairs_source',before==[tuple(v.co) for v in bad.data.vertices])
plane.scale=(1e-7,1e-7,1)
check('world_scale_included_in_area',inspect_mesh(plane)['degenerate_triangles']==2)
check('explicit_world_area_tolerance_respected',inspect_mesh(plane,min_triangle_area=1e-16)['degenerate_triangles']==0)
plane.scale=(1,1,1)
sub=plane.modifiers.new('Subdivide','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=2
report=inspect_mesh(plane)
check('source_and_evaluated_cost_separate',report['source_geometry']['triangles']==2 and report['evaluated_triangles']==32)
rejected('modifier_cost_blocks_refinement',lambda:require_asset_geometry([plane],stage='refine',max_triangles=10))
plane.modifiers.remove(sub)
bpy.ops.mesh.primitive_cube_add();a=bpy.context.object;a.name='BudgetA'
bpy.ops.mesh.primitive_cube_add(location=(3,0,0));b=bpy.context.object;b.name='BudgetB'
from reference_fit.blender_validation import structure as fitter_structure
from reference_fit.blender_builder import OWNER as FITTER_OWNER
a[FITTER_OWNER]='quality-fitter-control'
cfg={'character_id':'quality-fitter-control','shape':{},'validation':{'max_triangles':12}}
check('fitter_legal_control_stays_accepted',fitter_structure(bpy.context.scene,cfg)['ok'])
del a[FITTER_OWNER];bad[FITTER_OWNER]='quality-fitter-control'
fit_report=fitter_structure(bpy.context.scene,cfg)
check('fitter_inspects_actual_triangles',not fit_report['ok'] and fit_report['geometry_audit']['objects'][bad.name]['degenerate_triangles']>0)
del bad[FITTER_OWNER]
check('exact_aggregate_budget_passes',inspect_asset([a,b],stage='refine',max_triangles=24)['passed'])
rejected('aggregate_budget_not_per_object',lambda:require_asset_geometry([a,b],stage='refine',max_triangles=12))
check('undeclared_budget_stays_unknown',inspect_asset([a],stage='blockout')['budget_passed'] is None)
# Template local refinement includes unaffected same-phase owned modules.
spec=importlib.util.spec_from_file_location('task_template',ROOT/'assets/blender_task_template.py');template=importlib.util.module_from_spec(spec);spec.loader.exec_module(template);template.TASK_ID='budget-fixture'
for obj in [a,b]:obj[template.OWNER_KEY]=template.TASK_ID;obj[template.PHASE_KEY]='refine'
rejected('template_counts_unaffected_modules',lambda:template._geometry_check([a],'refine',{'resource_budget':{'max_triangles':12,'reason':'shared synthetic budget'}}))
for obj in [a,b]:obj.data.materials.append(plane.data.materials[0])
rejected('bad_geometry_stops_export',lambda:export_glb([bad],out/'bad.glb'))
check('rejected_preflight_has_report_no_glb',not (out/'bad.glb').exists() and json.loads((out/'bad.glb.report.json').read_text())['phase']=='source-preflight')
rejected('delivery_aggregate_budget_enforced',lambda:export_glb([a,b],out/'over.glb',max_triangles=12))
check('budget_rejection_precedes_export',not (out/'over.glb').exists())
record=export_glb([a],out/'valid.glb',max_triangles=12,require_closed=True)
check('valid_closed_alternative_roundtrips',record['status']=='passed' and record['imported']['1']['BudgetA']['geometry']['degenerate_triangles']==0)
raw_import=record['imported']['1']['BudgetA']['geometry']
check('normal_seams_retained_and_geometric_closure_distinguished',raw_import['nonmanifold_edges']>0 and raw_import['position_welded_topology']['nonmanifold_edges']==0)
# Imported damaged GLB is checked independently even when the external exporter ran.
bpy.ops.object.select_all(action='DESELECT');bad.select_set(True);bpy.context.view_layer.objects.active=bad
bpy.ops.export_scene.gltf(filepath=str(out/'external-bad.glb'),export_format='GLB',use_selection=True)
scene=bpy.data.scenes.new('ExternalImport');bpy.context.window.scene=scene;bpy.ops.import_scene.gltf(filepath=str(out/'external-bad.glb'))
rejected('actual_imported_tessellation_checked',lambda:sample(scene,{'max_triangles':100}))
# A valid rest mesh collapses at an explicit animation sample; parent process is unchanged.
scene=bpy.data.scenes.new('AnimatedValidation');bpy.context.window.scene=scene
anim=a.copy();anim.data=a.data.copy();anim.name='CollapsingMesh';scene.collection.objects.link(anim);scene.frame_start=1;scene.frame_end=17
for frame,scale in [(1,1),(9,0),(17,1)]:anim.scale=(scale,scale,scale);anim.keyframe_insert('scale',frame=frame)
anim.animation_data.action.name='Collapse';scene.frame_set(1)
rejected('animated_later_invalid_frame_blocks_export',lambda:export_glb([anim],out/'collapse.glb',mode='animated',frames=(1,9,17),clip='Collapse',max_triangles=12))
failure=json.loads((out/'collapse.glb.report.json').read_text())
check('animation_failure_retains_geometry_evidence','geometry_failure' in failure and not (out/'collapse.glb').exists())
report={'passed':all(checks.values()),'checks':checks,'blender':bpy.app.version_string,'baseline_controls':baseline_checks,'scope':'synthetic geometry/budget/delivery coverage, not modeling quality or Skill effect'}
(out/'geometry-quality.json').write_text(json.dumps(report,indent=2));print('GEOMETRY_QUALITY_OK',json.dumps(report))
