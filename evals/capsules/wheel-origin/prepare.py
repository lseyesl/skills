"""Create a reproducible defect; hidden from the evaluated Agent."""
import bpy
from mathutils import Matrix
from pathlib import Path
import sys
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_torus_add(major_radius=0.8,minor_radius=0.18,major_segments=32,minor_segments=12)
wheel=bpy.context.object;wheel.name='Wheel';wheel.data.transform(Matrix.Translation((0.25,0,0)))
bpy.ops.mesh.primitive_cube_add(size=0.2,location=(-2,0,0));bpy.context.object.name='PreserveMe'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'source.blend'))
