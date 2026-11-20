"""Cross-scenario tests for explicit-input tooling, including partial results and resume."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from PIL import Image, ImageChops, ImageDraw
import toolbox as t
from puppet import load_manifest, render
from puppet_core import apply, pose_transforms


class ToolboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def path(self, name):
        return str(self.root/name)

    def put(self, name, data):
        p = self.root/name
        t.write(p, data)
        return str(p)

    def static(self):
        Image.new('RGB', (20, 12), 'red').save(self.path('prop.png'))
        return self.put('manifest.json', dict(schema_version='1.0', coordinate_system='image-pixels-y-down', source_size=[40, 30],
                          parts=[dict(id='prop', file='prop.png', crop_origin=[4, 5], pixel_size=[20, 12])]))

    def test_static_rgb_without_nodes_or_motion_and_stable_ties(self):
        manifest = self.static()
        data = t.read(manifest)
        Image.new('RGB', (20, 12), 'blue').save(self.path('overlay.png'))
        data['parts'].append(dict(id='overlay', file='overlay.png', crop_origin=[4, 5], pixel_size=[20, 12]))
        t.write(manifest, data)
        self.assertEqual(render(manifest).getpixel((5, 6)), (0, 0, 255, 255))
        self.assertEqual(t.check(dict(manifest=manifest))['visual_review'], 'pending')
        data['parts'][0]['file'] = self.path('prop.png')
        t.write(manifest, data)
        self.assertEqual(len(load_manifest(manifest)['parts']), 2)

    def test_arbitrary_partial_hierarchy_translation_and_scale(self):
        manifest = self.static()
        data = t.read(manifest)
        data['nodes'] = [dict(id='axis/任意', parent=None, pivot_global=[4, 5]),
                         dict(id='hinge', parent='axis/任意', pivot_global=[14, 5])]
        data['parts'][0]['node'] = 'hinge'
        t.write(manifest, data)
        normalized = load_manifest(manifest)
        matrices = pose_transforms(normalized, dict(angles={'axis/任意': 90}, translations={'axis/任意': [2, 3]}, scales={'hinge': [2, 1]}))
        self.assertEqual([round(v) for v in apply(matrices['hinge'], [16, 5])], [6, 22])
        self.assertEqual(render(manifest, pose=dict(translations={'hinge': [2, 0]})).getpixel((6, 5)), (255, 0, 0, 255))

    def test_masked_crop_records_source_coordinates_and_empty_is_skipped(self):
        self.static()
        m = Image.new('L', (20, 12)); ImageDraw.Draw(m).rectangle((3, 4, 8, 9), fill=255)
        m.save(self.path('mask.png'))
        r = t.extract(dict(source=self.path('prop.png'), mask=self.path('mask.png'), output=self.path('part.png'), padding=2))
        self.assertEqual(r['crop_origin'], [1, 2])
        with Image.open(self.path('part.png')) as im:
            self.assertEqual(im.size, (10, 10))
            self.assertEqual(im.getpixel((0, 0))[3], 0)
        Image.new('L', (20, 12)).save(self.path('mask.png'))
        self.assertEqual(t.extract(dict(source=self.path('prop.png'), mask=self.path('mask.png'), output=self.path('empty.png')))['status'], 'skipped')
        self.assertFalse(Path(self.path('empty.png')).exists())

    def test_anchor_registration_and_exact_protection(self):
        im = Image.new('RGBA', (24, 24)); ImageDraw.Draw(im).rectangle((2, 3, 8, 9), fill='red'); im.save(self.path('source.png'))
        r = t.register(dict(source=self.path('source.png'), output=self.path('aligned.png'),
                            anchors=[{'from': [0, 0], 'to': [4, 5]}, {'from': [10, 0], 'to': [14, 5]}]))
        self.assertEqual(r['anchor_rms'], 0)
        with Image.open(self.path('aligned.png')) as aligned:
            self.assertEqual(aligned.getpixel((6, 8)), (255, 0, 0, 255))
        Image.new('RGBA', im.size, 'blue').save(self.path('patch.png'))
        Image.new('L', im.size, 255).save(self.path('mask.png'))
        protect = Image.new('L', im.size); ImageDraw.Draw(protect).rectangle((0, 0, 10, 10), fill=1); protect.save(self.path('protect.png'))
        t.patch(dict(source=self.path('source.png'), patch=self.path('patch.png'), mask=self.path('mask.png'), protect_mask=self.path('protect.png'), output=self.path('fixed.png')))
        with Image.open(self.path('fixed.png')) as fixed:
            self.assertEqual(fixed.crop((0, 0, 11, 11)).tobytes(), im.crop((0, 0, 11, 11)).tobytes())
            self.assertEqual(fixed.getpixel((20, 20)), (0, 0, 255, 255))

    def test_media_only_no_manifest_and_unavailable_encoder(self):
        frames = self.root/'frames'; frames.mkdir()
        for i, size in enumerate(((21, 23), (23, 21), (21, 23))):
            Image.new('RGBA', size, (i*80, 20, 30, 255)).save(frames/f'{i}.png')
        r = t.media(dict(frames=str(frames), output=self.path('media'), ffmpeg='__missing_encoder__'))
        self.assertEqual(r['status'], 'partial')
        self.assertEqual(r['frame_count'], 3)
        self.assertTrue(Path(self.path('media/animation.gif')).is_file())
        self.assertTrue(Path(self.path('media/contact-sheet.png')).is_file())
        with Image.open(self.path('media/animation.gif')) as im:
            self.assertEqual(im.n_frames, 3)

    def test_package_has_no_fixed_inventory_and_missing_is_explicit(self):
        self.static()
        r = t.package(dict(files=[self.path('prop.png')], required=[self.path('missing.png')], output=self.path('delivery.zip')))
        self.assertEqual(r['status'], 'partial')
        self.assertEqual(r['file_count'], 1)
        self.assertTrue(t.read(self.path('delivery.zip.json'))['missing'])
        self.assertEqual(t.read(self.path('delivery.zip.json'))['visual_review'], 'pending')

    def test_package_checks_portable_manifest_references(self):
        manifest = self.static()
        cfg = dict(manifest=manifest, files=[manifest], output=self.path('incomplete.zip'))
        self.assertEqual(t.package(cfg)['status'], 'partial')
        cfg.update(files=[manifest, self.path('prop.png')], output=self.path('complete.zip'))
        self.assertEqual(t.package(cfg)['status'], 'ok')
        data = t.read(manifest); data['parts'][0]['file'] = self.path('prop.png'); t.write(manifest, data)
        cfg['output'] = self.path('nonportable.zip')
        self.assertEqual(t.package(cfg)['status'], 'partial')

    def test_pipeline_failures_are_local_and_cache_tracks_real_inputs(self):
        self.static()
        config = dict(steps=[
            dict(id='bad', op='info', config=dict(source='missing.png')),
            dict(id='dependent', op='info', depends_on=['bad'], config=dict(source='prop.png')),
            dict(id='good', op='render', config=dict(manifest='manifest.json', output='rest.png'))])
        report = self.path('run.json')
        first = t.run_pipeline(config, self.root, report)
        self.assertEqual(first['status'], 'partial')
        self.assertEqual(first['steps']['dependent']['status'], 'blocked')
        self.assertEqual(first['steps']['good']['status'], 'ok')
        second = t.run_pipeline(config, self.root, report)
        self.assertEqual(second['steps']['good']['status'], 'cached')
        Image.new('RGB', (20, 12), 'green').save(self.path('prop.png'))
        third = t.run_pipeline(config, self.root, report)
        self.assertEqual(third['steps']['good']['status'], 'ok')
        with Image.open(self.path('rest.png')) as im:
            self.assertEqual(im.getpixel((5, 6)), (0, 128, 0, 255))
        Path(self.path('rest.png')).write_bytes(b'corrupt')
        self.assertEqual(t.run_pipeline(config, self.root, report)['steps']['good']['status'], 'ok')

    def test_missing_step_config_does_not_cancel_independent_steps(self):
        self.static()
        c = dict(steps=[dict(id='bad', op='info', config='absent.json'),
                        dict(id='good', op='info', config=dict(source='prop.png'))])
        r = t.run_pipeline(c, self.root, self.path('run.json'))
        self.assertEqual(r['steps']['bad']['status'], 'failed')
        self.assertEqual(r['steps']['good']['status'], 'ok')

    def test_corrupt_manifest_only_fails_its_step(self):
        self.static()
        for invalid in ([], {'parts': [None]}, 'not-a-manifest'):
            self.put('corrupt.json', invalid)
            c = dict(steps=[dict(id='bad', op='render', config=dict(manifest='corrupt.json', output='bad.png')),
                            dict(id='good', op='info', config=dict(source='prop.png'))])
            r = t.run_pipeline(c, self.root, self.path('run.json'))
            self.assertEqual(r['steps']['bad']['status'], 'failed')
            self.assertIn(r['steps']['good']['status'], ('ok', 'cached'))
        with self.assertRaisesRegex(ValueError, 'overwrite input'):
            t.run_pipeline(c, self.root, self.path('prop.png'))

    def test_partial_media_can_feed_existing_outputs_without_hiding_failure(self):
        frames = self.root/'frames'; frames.mkdir(); Image.new('RGB', (20, 20), 'red').save(frames/'1.png')
        c = dict(steps=[dict(id='media', op='media', config=dict(frames='frames', output='media', ffmpeg='__missing__')),
                        dict(id='zip', op='package', depends_on=['media'], config=dict(files=['media/animation.gif'], output='gif.zip'))])
        r = t.run_pipeline(c, self.root, self.path('run.json'))
        self.assertEqual(r['steps']['zip']['status'], 'ok')
        self.assertEqual(r['unmet_required_steps'], ['media'])

    def test_outputs_cannot_overwrite_inputs_or_metadata(self):
        self.static()
        with self.assertRaises(ValueError):
            t.safe_output(dict(source=self.path('prop.png'), output=str(self.root)))
        with self.assertRaises(ValueError):
            t.safe_output(dict(source=self.path('prop.png'), output=self.path('prop.png')))
        with self.assertRaises(ValueError):
            t.safe_output(dict(files=[self.path('delivery.zip.json')], output=self.path('delivery.zip')))

    def moving(self):
        manifest = self.static()
        data = t.read(manifest)
        data['nodes'] = [dict(id='root', pivot_global=[4, 5], rotation_range=[-30, 30])]
        data['parts'][0]['node'] = 'root'
        t.write(manifest, data)
        motion = self.put('motion.json', dict(fps=24, clips=[dict(id='move', frames=[
            dict(frame=10), dict(frame=14, translations={'root': [12, 0]})])]))
        return dict(manifest=manifest, motion_plan=motion, output=self.path('take-1'))

    def test_animation_renders_every_frame_with_timing_and_stage(self):
        c = self.moving()
        Image.new('RGB', (40, 30), 'blue').save(self.path('stage.png'))
        r = t.animate(dict(c, stage=self.path('stage.png')))
        self.assertEqual(r['frame_count'], 5)
        self.assertEqual(r['visual_review'], 'pending')
        self.assertEqual(r['clips'][0]['start_frame'], 10)
        self.assertEqual(r['clips'][0]['duration_seconds'], 5/24)
        # Real image positions, including an interpolated frame rather than just the keys.
        for index, x in ((0, 4), (2, 10), (4, 16)):
            with Image.open(self.path(f'take-1/clip-000/frames/{index:08d}.png')) as im:
                self.assertEqual(im.getpixel((x, 5)), (255, 0, 0, 255))
                self.assertEqual(im.getpixel((x-1, 5)), (0, 0, 255, 255))
        with Image.open(self.path('take-1/clip-000/media/animation.gif')) as im:
            self.assertEqual(im.n_frames, 5)
        self.assertTrue(Path(self.path('take-1/preview.json')).is_file())

    def test_animation_uses_default_pose_at_each_key_and_separates_clips(self):
        c = self.moving()
        motion = t.read(c['motion_plan'])
        motion['clips'][0]['frames'] = [dict(frame=1, translations={'root': [12, 0]}), dict(frame=5)]
        motion['clips'].append(dict(id='../untrusted-name', frames=[dict(frame=1), dict(frame=2)]))
        t.write(c['motion_plan'], motion)
        r = t.animate(c)
        self.assertEqual([v['frame_count'] for v in r['clips']], [5, 2])
        with Image.open(self.path('take-1/clip-000/frames/00000004.png')) as im:
            self.assertEqual(im.getbbox(), (4, 5, 24, 17))
        self.assertTrue(Path(self.path('take-1/clip-001/media/animation.gif')).exists())

    def test_animation_rejects_bad_motion_before_writing(self):
        c = self.moving()
        original = t.read(c['motion_plan'])
        for changes in (
            dict(frames=[dict(frame=1), dict(frame=1)]),
            dict(frames=[dict(frame=1, angles={'root': 31})]),
            dict(frames=[dict(frame=1, translations={'unknown': [0, 0]})]),
            dict(frames=[dict(frame=True)]),
            dict(frames=[dict(frame=1, visibility={'prop': False})]),
        ):
            motion = copy.deepcopy(original)
            motion['clips'][0].update(changes)
            t.write(c['motion_plan'], motion)
            with self.assertRaises(ValueError):
                t.animate(c)
            self.assertFalse(Path(c['output']).exists())
        t.write(c['motion_plan'], original)
        for extra in (dict(max_frames=4), dict(fps=12), dict(clip_id='missing'), dict(formats=['sheet'])):
            with self.assertRaises(ValueError):
                t.animate(dict(c, **extra))

    def test_animation_interpolates_rotation_scale_and_parent_follow(self):
        c = self.moving()
        data = t.read(c['manifest'])
        del data['nodes'][0]['rotation_range']
        data['nodes'].append(dict(id='child', parent='root', pivot_global=[14, 5]))
        data['parts'][0]['node'] = 'child'
        t.write(c['manifest'], data)
        motion = t.read(c['motion_plan'])
        motion['clips'][0]['frames'] = [dict(frame=1), dict(frame=5, angles={'root': 90, 'child': -30},
            translations={'root': [4, 6]}, scales={'root': [2, 1]})]
        t.write(c['motion_plan'], motion)
        t.animate(c)
        expected = render(c['manifest'], pose=dict(angles={'root': 45, 'child': -15},
            translations={'root': [2, 3]}, scales={'root': [1.5, 1]}))
        with Image.open(self.path('take-1/clip-000/frames/00000002.png')) as actual:
            self.assertEqual(actual.tobytes(), expected.tobytes())

    def test_animation_revision_keeps_source_and_previous_preview(self):
        c = self.moving()
        t.animate(c)
        with self.assertRaisesRegex(ValueError, 'new preview'):
            t.animate(c)
        source_hash = t.digest(c['manifest'])
        motion = t.read(c['motion_plan'])
        motion['clips'][0]['frames'][-1]['translations']['root'] = [6, 0]
        t.write(c['motion_plan'], motion)
        t.animate(dict(c, output=self.path('take-2')))
        self.assertEqual(t.digest(c['manifest']), source_hash)
        with Image.open(self.path('take-1/clip-000/frames/00000004.png')) as a, Image.open(self.path('take-2/clip-000/frames/00000004.png')) as b:
            self.assertNotEqual(a.tobytes(), b.tobytes())

    def test_selected_animation_does_not_wait_for_unfinished_clips(self):
        c = self.moving()
        motion = t.read(c['motion_plan'])
        motion['clips'].append(dict(id='unfinished', frames=[]))
        t.write(c['motion_plan'], motion)
        r = t.animate(dict(c, clip_id='move'))
        self.assertEqual([clip['id'] for clip in r['clips']], ['move'])

    def test_animation_missing_encoder_retains_playable_preview_and_failure(self):
        c = self.moving()
        r = t.animate(dict(c, formats=['gif', 'mp4'], ffmpeg='__missing_encoder__'))
        self.assertEqual(r['status'], 'partial')
        self.assertTrue(Path(self.path('take-1/clip-000/media/animation.gif')).exists())


if __name__ == '__main__':
    unittest.main()
