"""Small positive/negative/alternative controls for technical measurements only."""
import hashlib,importlib.util,json,sys
from pathlib import Path
import bpy
from mathutils import Matrix

p=Path(__file__).parent/'check_assets.py';spec=importlib.util.spec_from_file_location('checker',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=Path(sys.argv[sys.argv.index('--')+1]).resolve();out.mkdir(parents=True,exist_ok=True)
scene=bpy.data.scenes.new('Control');bpy.context.window.scene=scene
def triangle(name,vertices):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],[(0,1,2)]);mesh.update();ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob);return ob
good=triangle('LegalOpenSurface',[(0,0,0),(1,0,0),(0,1,0)])
bad=triangle('DegenerateFace',[(0,0,0),(1,0,0),(2,0,0)])
source=m.snapshot([good]);defect=m.snapshot([bad]);good.name='LegalRenamedAlternative';renamed=m.snapshot([good])
for ob in scene.objects:ob.select_set(False)
good.select_set(True);bpy.context.view_layer.objects.active=good
kwargs={'filepath':str(out/'control.glb'),'export_format':'GLB','use_selection':True}
if 'use_active_scene' in bpy.ops.export_scene.gltf.get_rna_type().properties:kwargs['use_active_scene']=True
bpy.ops.export_scene.gltf(**kwargs)
document=m.glb_json(out/'control.glb')
other=bpy.data.scenes.new('ControlReimport');bpy.context.window.scene=other;bpy.ops.import_scene.gltf(filepath=str(out/'control.glb'))
restored=m.snapshot(list(other.objects));bounds_error=max(abs(source['bounds'][i][j]-restored['bounds'][i][j]) for i in range(2) for j in range(3))
good.matrix_world=Matrix.Translation((5,0,0));bpy.context.window.scene=scene;bpy.context.view_layer.update();shifted=m.snapshot([good]);shift_error=max(abs(source['bounds'][i][j]-shifted['bounds'][i][j]) for i in range(2) for j in range(3))
checks={'valid_open_surface_allowed':source['triangles']==1 and source['degenerate_triangles']==0,'degenerate_face_detected':defect['degenerate_triangles']==1,'renaming_does_not_change_geometry':source['bounds']==renamed['bounds'] and source['triangles']==renamed['triangles'],'positive_bounds_roundtrip':bounds_error<1e-4,'positive_triangle_roundtrip':source['triangles']==restored['triangles'],'shift_detected':shift_error>1,'static_glb_not_mistaken_for_rig':not document.get('skins') and not document.get('animations')}
report={'passed':all(checks.values()),'checks':checks,'blender':bpy.app.version_string,'checker_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'technical helper calibration only; visual grader and real use-case functionality remain uncalibrated'}
(out/'calibration.json').write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']:raise RuntimeError(report)
