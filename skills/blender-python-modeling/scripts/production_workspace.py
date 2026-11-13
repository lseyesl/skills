"""Owned empty creation scenes and executable render preflight, for Blender 4.x/5.x."""
import bpy

OWNER = 'modeling_task_id'
ROLES = ('Asset', 'Coarse', 'References', 'Studio')


def task_scene(task_id, *, mode='create', name=None, existing=None):
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError('Explicit task identity required')
    if mode == 'edit':
        if existing is None or bpy.data.scenes.get(existing.name) is not existing:
            raise ValueError('Edit requires an explicit existing scene')
        bpy.context.window.scene = existing
        return existing
    if mode != 'create':
        raise ValueError('Scene mode must be create or edit')
    name = name or 'MODEL_' + task_id
    scene = bpy.data.scenes.get(name)
    if scene is not None and scene.get(OWNER) != task_id:
        raise RuntimeError('Refuse to clear an unowned scene: ' + name)
    if scene is None:
        # scenes.new creates no startup Cube/Camera/Light. Never copy the default scene.
        scene = bpy.data.scenes.new(name)
        scene[OWNER] = task_id
        if scene.objects:
            raise RuntimeError('Creation scene was not empty')
        for role in ROLES:
            collection = bpy.data.collections.new(name + '::' + role)
            collection[OWNER] = task_id
            collection['modeling_role'] = role
            scene.collection.children.link(collection)
    bpy.context.window.scene = scene
    return scene


def role_collection(scene, role):
    if role not in ROLES:
        raise ValueError('Unknown modeling role')
    matches = [c for c in scene.collection.children if c.get('modeling_role') == role and c.get(OWNER) == scene.get(OWNER)]
    if len(matches) != 1:
        raise RuntimeError('Missing/ambiguous owned role collection: ' + role)
    return matches[0]


def probe_render(scene, *, prefer_denoise=True, allow_fallback=True, render_probe=None):
    """Execute a 16px probe without touching the user's geometry or render setup.

    Only recognized unavailable-denoiser errors permit fallback. Other errors propagate.
    Returns measured support, not a version-derived assumption or artistic acceptance.
    """
    probe = bpy.data.scenes.new('RenderCapabilityProbe')
    meshes = []; cameras = []; objects = []
    try:
        probe.render.engine = scene.render.engine
        probe.render.resolution_x = probe.render.resolution_y = 16
        probe.render.resolution_percentage = 100
        probe.render.image_settings.file_format = 'PNG'
        mesh = bpy.data.meshes.new('ProbeTriangle'); meshes.append(mesh)
        mesh.from_pydata([(-1,-1,0),(1,-1,0),(0,1,0)], [], [(0,1,2)])
        obj = bpy.data.objects.new('ProbeTriangle', mesh); objects.append(obj); probe.collection.objects.link(obj)
        data = bpy.data.cameras.new('ProbeCamera'); cameras.append(data)
        camera = bpy.data.objects.new('ProbeCamera', data); objects.append(camera); probe.collection.objects.link(camera)
        camera.location = (0,0,3); probe.camera = camera
        if probe.render.engine == 'CYCLES':
            probe.cycles.device = 'CPU'; probe.cycles.samples = 1
            probe.cycles.use_denoising = bool(prefer_denoise)
        execute = render_probe or (lambda s: bpy.ops.render.render(scene=s.name))
        fallback = None
        try:
            execute(probe)
        except RuntimeError as exc:
            message = str(exc).lower()
            denoiser_error = any(x in message for x in ('openimagedenoise', 'failed to denoise', 'denoiser not available', 'no available denoiser'))
            if not (allow_fallback and probe.render.engine == 'CYCLES' and prefer_denoise and denoiser_error):
                raise
            fallback = str(exc)
            probe.cycles.use_denoising = False
            execute(probe)
        return {'engine':probe.render.engine, 'blender':bpy.app.version_string,
                'requested_denoise':bool(prefer_denoise),
                'use_denoising':bool(prefer_denoise and fallback is None and probe.render.engine == 'CYCLES'),
                'fallback_reason':fallback, 'probe_passed':True,
                'scope':'16px CPU preflight only; production device, caches and final render remain separate checks'}
    finally:
        bpy.data.scenes.remove(probe)
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for data in meshes: bpy.data.meshes.remove(data)
        for data in cameras: bpy.data.cameras.remove(data)


def apply_render_preflight(scene, *, prefer_denoise=True):
    result = probe_render(scene, prefer_denoise=prefer_denoise)
    if scene.render.engine == 'CYCLES':
        scene.cycles.use_denoising = result['use_denoising']
    return result
