"""Read-only round-trip checks of the actual saved delivery, not a rebuilt proxy."""
from pathlib import Path
import argparse,json,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from reference_fit.blender_builder import fingerprints
from reference_fit.blender_validation import structure
p=argparse.ArgumentParser();p.add_argument('--expected',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);s=bpy.context.scene;c=json.loads(s['fit_config']);owner=c['character_id']
refs=[o for o in s.objects if o.get('fit_reference_view')]
checks={'active_orthographic_camera':bool(s.camera and s.camera.data.type=='ORTHO'),
 'saved_geometry_materials_match_last_selected':fingerprints(s,owner)==json.loads(a.expected.read_text()),
 'references_packed':len(refs)==len(c['reference']['views']) and all(o.data.packed_file for o in refs),
 'reference_upright_and_pixel_scale':all(abs((o.rotation_euler.to_matrix()@Vector((0,1,0))).z-1)<1e-5 and abs(o.empty_display_size-max(o.data.size)/json.loads(o['fit_calibration'])['pixels_per_unit'])<1e-5 for o in refs),
 'evaluated_structural_checks':structure(s,c)['ok']}
report={'ok':all(checks.values()),'checks':checks,'blender':bpy.app.version_string,'actual_file':bpy.data.filepath,'file_not_modified':True}
a.output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if not report['ok']:raise SystemExit(1)
