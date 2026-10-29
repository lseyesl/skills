"""Synthetic Blender integration checks; NOT visual/reference fidelity approval.

Run with Blender --background --factory-startup --python-exit-code 1 --python ...
"""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile

import bpy
from mathutils import Vector

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from reference_workspace import (OWNER, setup_references, workspace_signature,
                                 reference_landmark, require_reference_review, model_signature)

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
        rejects('missing inferred depth before deleting geometry', module.main)
        assert scene.objects.get(sentinel.name) == sentinel
        module.INFERRED_DEPTH = .2
        module.main()
        cube = bpy.data.objects['GEO_' + task + '_body']
        assert (cube.dimensions - Vector((.4, .2, .85))).length < 1e-6
        checks.append('sample builder dimensions actually derived from imported guide anchors')

        comparison = dict(review, phase='comparison', model_signature=model_signature([cube]))
        review_path.write_text(json.dumps(comparison))
        require_reference_review(scene, task, review_path, phase='comparison', objects=[cube])
        cube.data.vertices[0].co.x += .01;cube.data.update();bpy.context.view_layer.update()
        rejects('model edit invalidates prior overlay comparison',
                lambda: require_reference_review(scene, task, review_path, phase='comparison', objects=[cube]))

        # A packed guide remains usable after moving the blend away from source files.
        (root / 'reference.png').unlink()
        workspace_signature(scene, task)
        checks.append('packed source fallback retains calibration')
    print(json.dumps({'ok': True, 'blender': bpy.app.version_string, 'checks': checks,
                      'scope': 'Synthetic integration checks; no real viewport review or artistic fidelity certified'}))


if __name__ == '__main__':
    main()
