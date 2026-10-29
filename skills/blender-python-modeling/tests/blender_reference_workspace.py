"""Synthetic Blender integration checks; NOT visual/reference fidelity approval.

Run with Blender --background --factory-startup --python-exit-code 1 --python ...
"""
from pathlib import Path
import importlib.util
import json
import hashlib
import sys
import tempfile

import bpy
from mathutils import Vector

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from reference_workspace import (OWNER, setup_references, workspace_signature,
                                 reference_landmark, require_reference_review, model_signature, appearance_signature)

checks = []


def rejects(label, fn):
    try:
        fn()
    except (RuntimeError, ValueError, FileNotFoundError):
        checks.append(label)
        return
    raise AssertionError('Expected rejection: ' + label)


def main():
    scene = bpy.data.scenes.new('ReferenceWorkspaceSyntheticTest')
    bpy.context.window.scene = scene
    task = 'reference-workspace-test'
    with tempfile.TemporaryDirectory(prefix='reference-workspace-') as tmp:
        root = Path(tmp)
        image = bpy.data.images.new('synthetic-calibration', width=100, height=200)
        image.filepath_raw = str(root / 'reference.png')
        image.file_format = 'PNG'
        image.save()
        rejects('packed image alone is not a workspace', lambda: workspace_signature(scene, task))
        landmarks = {'body_center': [50, 80], 'body_left': [10, 80], 'body_right': [90, 80],
                     'body_top': [50, 10], 'body_bottom': [50, 180], 'probe': [75, 80]}
        config = {'views': {v: {'image': 'reference.png', 'pixels_per_unit': 200,
                               'origin_px': [50, 180], 'landmarks': landmarks}
                            for v in ['front', 'back', 'right', 'left', 'top', 'bottom']}}
        # Synthetic pre-model evidence tests declarations, never image agreement.
        rejects('multiple guides without design review', lambda: setup_references(scene, task, config, root))
        assert not any(o.get(OWNER) == task for o in scene.objects)
        from reference_review import CHECKS
        design = {'schema_version': 1, 'purpose': 'synthetic rigid prop', 'pose': 'fixed rest cube',
                  'readiness': 'passed', 'allowed_regions': ['body'], 'blocked_regions': [],
                  'conflicts': [], 'checks': {k: {'status': 'passed', 'finding': 'Synthetic test only'} for k in CHECKS},
                  'views': {v: {'image': 'reference.png', 'sha256': hashlib.sha256((root/'reference.png').read_bytes()).hexdigest(),
                                'role': 'controlling', 'controls': ['body'], 'finding': 'Synthetic test only'} for v in config['views']},
                  'review_artifacts': ['reference.png']}
        design_path = root/'design-review.json';design_path.write_text(json.dumps(design))
        config['multiview_review'] = 'design-review.json'
        record = setup_references(scene, task, config, root)
        sig = workspace_signature(scene, task)
        counts = (len(scene.objects), len(bpy.data.images))
        setup_references(scene, task, config, root)
        assert counts == (len(scene.objects), len(bpy.data.images))
        checks.append('owned references and images reused on rerun')
        expected = {'front': [.125, 0, .5], 'back': [-.125, 0, .5],
                    'right': [0, .125, .5], 'left': [0, -.125, .5],
                    'top': [.125, .5, 0], 'bottom': [.125, -.5, 0]}
        for view, point in expected.items():
            assert (reference_landmark(scene, task, view, 'probe') - Vector(point)).length < 1e-6, view
        checks.append('six axis pixel-to-world mappings')
        front = bpy.data.objects[record['front']['object']]
        assert front.empty_image_depth == 'FRONT' and abs(front.color[3] - .4) < 1e-6
        assert front.hide_select and all(front.lock_location)
        checks.append('front depth, alpha, transform protection')
        front.empty_image_depth = 'BACK'
        rejects('wrong depth', lambda: workspace_signature(scene, task))
        front.empty_image_depth = 'FRONT'
        front.color[3] = 1
        rejects('opaque guide', lambda: workspace_signature(scene, task))
        front.color[3] = .4
        front.location.x += .1
        bpy.context.view_layer.update()
        rejects('moved guide', lambda: workspace_signature(scene, task))
        front.location.x -= .1
        bpy.context.view_layer.update()
        front.hide_set(True)
        rejects('hidden guide', lambda: workspace_signature(scene, task))
        front.hide_set(False)
        front.empty_display_size *= 2
        rejects('rescaled guide', lambda: workspace_signature(scene, task))
        front.empty_display_size /= 2
        assert workspace_signature(scene, task) == sig

        # Synthetic captures test file/state gates, not an actual human visual review.
        review = {'workspace_signature': sig, 'phase': 'calibration', 'status': 'passed',
                  'views': {v: {'artifact': 'reference.png', 'finding': 'Synthetic test receipt, not art signoff'}
                            for v in config['views']}}
        review_path = root / 'review.json'
        review_path.write_text(json.dumps(review))
        require_reference_review(scene, task, review_path)
        missing = json.loads(json.dumps(review));missing['views']['front']['artifact'] = 'missing.png'
        review_path.write_text(json.dumps(missing))
        rejects('missing viewport artifact', lambda: require_reference_review(scene, task, review_path))
        stale = json.loads(json.dumps(review));stale['workspace_signature'] = 'old-state'
        review_path.write_text(json.dumps(stale))
        rejects('stale calibration review', lambda: require_reference_review(scene, task, review_path))
        review_path.write_text(json.dumps(review))

        template = SCRIPTS.parent / 'assets/blender_task_template.py'
        spec = importlib.util.spec_from_file_location('task_template', template)
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.TASK_ID = task;module.COLLECTION_NAME = 'GEN_reference-workspace-test'
        sentinel = bpy.data.objects.new('owned-prior-geometry', None)
        scene.collection.objects.link(sentinel);sentinel[module.OWNER_KEY] = task
        rejects('template mode must be explicit', module.main)
        module.BUILD_MODE = 'reference'
        rejects('template prerequisite before deleting prior geometry', module.main)
        assert scene.objects.get(sentinel.name) == sentinel
        config_path = root / 'reference-setup.json';config_path.write_text(json.dumps(config))
        module.REFERENCE_HELPER_DIR = SCRIPTS;module.REFERENCE_CONFIG = config_path
        module.CALIBRATION_REVIEW = review_path
        module.BUILD_RECEIPT = root / 'build-state.json'
        rejects('missing inferred depth before deleting geometry', module.main)
        assert scene.objects.get(sentinel.name) == sentinel
        assert json.loads(module.BUILD_RECEIPT.read_text())['status']=='failed'
        checks.append('template records failed prerequisite attempt before preserving old geometry')
        module.INFERRED_DEPTH = .2
        module.main()
        cube = bpy.data.objects['GEO_' + task + '_body']
        assert (cube.dimensions - Vector((.4, .2, .85))).length < 1e-6
        checks.append('sample builder dimensions actually derived from imported guide anchors')
        from stage_guard import require_stage
        require_stage(module.BUILD_RECEIPT,'build',module.stage_inputs)
        checks.append('template successful build has fresh guarded receipt')

        comparison = dict(review, phase='comparison', model_signature=model_signature([cube]),
                          appearance_signature=appearance_signature(scene, [cube]))
        review_path.write_text(json.dumps(comparison))
        require_reference_review(scene, task, review_path, phase='comparison', objects=[cube])
        # Material, light, world, camera, attribute and image changes invalidate visual receipts.
        mat=bpy.data.materials.new('synthetic-visual');mat.use_nodes=True;cube.data.materials.append(mat)
        bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        def current_comparison():
            comparison['appearance_signature']=appearance_signature(scene,[cube]);review_path.write_text(json.dumps(comparison))
        def stale_visual(label):
            rejects(label,lambda:require_reference_review(scene,task,review_path,phase='comparison',objects=[cube]))
        current_comparison();bs.inputs['Base Color'].default_value=(.2,.5,.8,1);stale_visual('base colour invalidates comparison')
        current_comparison();bs.inputs['Roughness'].default_value=.12;stale_visual('roughness invalidates comparison')
        texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
        current_comparison();image.colorspace_settings.name='Non-Color';stale_visual('image colours change invalidates comparison')
        texcoord=mat.node_tree.nodes.new('ShaderNodeAttribute');texcoord.attribute_name='RestUV'
        attr=cube.data.attributes.new('RestUV','FLOAT_VECTOR','POINT')
        current_comparison();cube.data.attributes['RestUV'].data[0].vector=(.2,.3,.4);stale_visual('material attribute invalidates comparison')
        light_data=bpy.data.lights.new('synthetic-light','AREA');light=bpy.data.objects.new('synthetic-light',light_data);scene.collection.objects.link(light)
        current_comparison();light.data.energy+=10;stale_visual('light energy invalidates comparison')
        current_comparison();light.location.x+=.2;bpy.context.view_layer.update();stale_visual('light placement invalidates comparison')
        camera_data=bpy.data.cameras.new('synthetic-camera');camera=bpy.data.objects.new('synthetic-camera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
        current_comparison();camera.data.lens+=5;stale_visual('camera lens invalidates comparison')
        world=bpy.data.worlds.new('synthetic-world');world.use_nodes=True;scene.world=world
        current_comparison();next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.2;stale_visual('world invalidates comparison')
        group=bpy.data.node_groups.new('synthetic-group','ShaderNodeTree');node=mat.node_tree.nodes.new('ShaderNodeGroup');node.node_tree=group
        value=group.nodes.new('ShaderNodeValue')
        current_comparison();value.outputs[0].default_value=.7
        # Output default sockets also matter for Value/RGB nodes.
        stale_visual('nested group output invalidates comparison')
        brick=mat.node_tree.nodes.new('ShaderNodeTexBrick')
        current_comparison();brick.offset_frequency=3;stale_visual('stock node RNA settings invalidate comparison')
        stable=appearance_signature(scene,[cube]);brick.location.x+=50
        assert stable==appearance_signature(scene,[cube]);checks.append('editor node layout does not invalidate visual evidence')
        current_comparison();scene.view_settings.exposure+=.3;stale_visual('exposure invalidates comparison')
        uv=cube.data.uv_layers.new(name='ShaderUV')
        current_comparison();cube.data.uv_layers['ShaderUV'].data[0].uv=(.3,.5);stale_visual('UV change invalidates comparison')
        attr=cube.data.attributes.new('RegionId','INT','FACE')
        current_comparison();cube.data.attributes['RegionId'].data[0].value=3;stale_visual('region ids invalidate comparison')
        separate=bpy.data.images.new('synthetic-texture',width=8,height=8);separate.filepath_raw=str(root/'texture.png');separate.file_format='PNG';separate.save();separate.pack();texture.image=separate
        current_comparison();p=root/'texture.png';p.write_bytes(p.read_bytes()+b'changed');stale_visual('external texture content invalidates comparison')
        current_comparison();scene.render.resolution_x+=1;stale_visual('resolution invalidates comparison')
        current_comparison();mat.node_tree.nodes.get(texture.name).image=None;stale_visual('texture binding invalidates comparison')
        current_comparison()
        cube.data.vertices[0].co.x += .01;cube.data.update();bpy.context.view_layer.update()
        rejects('model edit invalidates prior overlay comparison',
                lambda: require_reference_review(scene, task, review_path, phase='comparison', objects=[cube]))

        original_design=design_path.read_text();design['pose']='changed pose after calibration';design_path.write_text(json.dumps(design))
        rejects('changed design review invalidates workspace',lambda:workspace_signature(scene,task))
        design_path.write_text(original_design)
        # A packed guide remains usable after moving the blend away from source files.
        (root / 'reference.png').unlink()
        workspace_signature(scene, task)
        checks.append('packed source fallback retains calibration')
        design_path.unlink();workspace_signature(scene,task)
        checks.append('embedded design receipt keeps packed scene inspectable offline')
    print(json.dumps({'ok': True, 'blender': bpy.app.version_string, 'checks': checks,
                      'scope': 'Synthetic integration checks; no real viewport review or artistic fidelity certified'}))


if __name__ == '__main__':
    main()
