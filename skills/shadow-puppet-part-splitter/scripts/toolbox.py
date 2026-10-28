#!/usr/bin/env python3
"""Deterministic image/puppet utilities. All paths in configs are relative to the config file."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from puppet import load_manifest, render
from puppet_core import asset, apply, pose_transforms, require


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return str(path.resolve())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def result(artifacts=(), issues=(), **extra):
    return dict(status='ok', artifacts=[str(Path(x).resolve()) for x in artifacts], issues=list(issues), **extra)


PATH_KEYS = {'source', 'mask', 'protect_mask', 'patch', 'manifest', 'poses', 'reference',
             'frames', 'output', 'motion_plan', 'font', 'review', 'blend', 'report', 'scene_report', 'archive_root'}


def resolve_config(config, base):
    config = dict(config)
    for key in PATH_KEYS:
        if config.get(key) is not None:
            config[key] = str((base / config[key]).resolve())
    for key in ('masks', 'files', 'required'):
        if key in config:
            config[key] = [str((base / p).resolve()) for p in config[key]]
    return config


def inputs(config):
    paths = []
    for key in PATH_KEYS-{'output', 'report', 'archive_root'}:
        if config.get(key):
            p = Path(config[key])
            paths.extend(sorted(x for x in p.rglob('*') if x.is_file()) if p.is_dir() else [p])
    for key in ('masks', 'files', 'required'):
        paths.extend(Path(p) for p in config.get(key, []))
    if config.get('manifest') and Path(config['manifest']).is_file():
        data = read(config['manifest'])
        parts = data.get('parts', []) if isinstance(data, dict) else []
        for part in parts if isinstance(parts, list) else []:
            if isinstance(part, dict):
                paths.extend(Path(config['manifest']).parent / part[k] for k in ('file', 'inferred_region_mask')
                             if isinstance(part.get(k), str) and part[k])
    return paths


def safe_output(config):
    output = Path(config['output'])
    protected = {p.resolve() for p in inputs(config)}
    require(not any(p == output.resolve() or p.is_relative_to(output.resolve()) for p in protected),
            'output would overwrite or contain an input')
    require(output.with_suffix(output.suffix+'.json').resolve() not in protected, 'metadata would overwrite input')
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def save(im, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


def mask(path, size):
    with Image.open(path) as im:
        require(im.size == size, f'mask dimensions mismatch: {path}')
        return im.convert('L')


def image_info(c):
    with Image.open(c['source']) as im:
        rgba = im.convert('RGBA')
        info = dict(size=list(im.size), mode=im.mode, format=im.format,
                    alpha_extrema=rgba.getchannel('A').getextrema(), alpha_bbox=rgba.getbbox())
    return result(**info)


def extract(c):
    with Image.open(c['source']) as im:
        im = im.convert('RGBA')
    selection = mask(c['mask'], im.size)
    im.putalpha(ImageChops.multiply(im.getchannel('A'), selection))
    bbox = im.getbbox()
    if bbox is None:
        return dict(status='skipped', artifacts=[], issues=['selection is empty'])
    padding = c.get('padding', 0)
    require(isinstance(padding, int) and padding >= 0, 'padding must be a nonnegative integer')
    box = [bbox[0]-padding, bbox[1]-padding, bbox[2]+padding, bbox[3]+padding]
    out = safe_output(c)
    save(im.crop(box), out)
    meta = out.with_suffix(out.suffix+'.json')
    require(meta.resolve() not in {p.resolve() for p in inputs(c)}, 'metadata would overwrite input')
    write(meta, dict(file=out.name, crop_origin=box[:2], pixel_size=[box[2]-box[0], box[3]-box[1]], source=c['source'], mask=c['mask']))
    return result([out, meta], crop_origin=box[:2])


def combine_masks(c):
    paths = c['masks']
    require(bool(paths), 'masks must not be empty')
    with Image.open(paths[0]) as first:
        im = first.convert('L')
    methods = {'union': ImageChops.lighter, 'intersect': ImageChops.darker, 'subtract': ImageChops.subtract}
    require(c.get('method', 'union') in methods, 'unknown mask method')
    for path in paths[1:]:
        im = methods[c.get('method', 'union')](im, mask(path, im.size))
    out = safe_output(c)
    save(im, out)
    return result([out])


def register(c):
    pairs = c['anchors']
    require(len(pairs) >= 2, 'registration needs at least two anchor pairs')
    src = [complex(*p['from']) for p in pairs]
    dst = [complex(*p['to']) for p in pairs]
    sm, dm = sum(src)/len(src), sum(dst)/len(dst)
    denom = sum(abs(z-sm)**2 for z in src)
    require(denom > 1e-12, 'degenerate registration anchors')
    a = sum((z-sm).conjugate()*(w-dm) for z, w in zip(src, dst))/denom
    require(abs(a) > 1e-12, 'degenerate registration transform')
    b = dm-a*sm
    inv, shift = 1/a, -b/a
    with Image.open(c['source']) as im:
        im = im.convert('RGBA')
        size = tuple(c.get('size', im.size))
        aligned = im.transform(size, Image.Transform.AFFINE,
                               (inv.real, -inv.imag, shift.real, inv.imag, inv.real, shift.imag),
                               resample=Image.Resampling.BICUBIC)
    out = safe_output(c)
    save(aligned, out)
    return result([out], anchor_rms=math.sqrt(sum(abs(a*z+b-w)**2 for z, w in zip(src, dst))/len(src)))


def patch(c):
    with Image.open(c['source']) as im:
        im = im.convert('RGBA')
    with Image.open(c['patch']) as donor:
        donor = donor.convert('RGBA')
    require(im.size == donor.size, 'patch must be registered to source dimensions')
    selected = mask(c['mask'], im.size)
    if c.get('protect_mask'):
        # Any nonzero protection value preserves the exact source pixel.
        protect = mask(c['protect_mask'], im.size).point(lambda v: 255 if v else 0)
        selected = ImageChops.subtract(selected, protect)
    out = safe_output(c)
    save(Image.composite(donor, im, selected), out)
    return result([out])


def render_op(c):
    out = safe_output(c)
    pose = c.get('pose', {})
    save(render(c['manifest'], pose=pose, enforce_limits=c.get('enforce_limits', True)), out)
    return result([out], visual_review='pending')


def font(c):
    if c.get('font'):
        return ImageFont.truetype(c['font'], 16)
    return ImageFont.load_default(size=16)


def sheet(images, labels, output, columns=4, cell_size=None, caption_font=None):
    require(images and isinstance(columns, int) and columns > 0, 'sheet needs images and positive columns')
    w, h = cell_size or (max(i.width for i in images), max(i.height for i in images))
    cols = min(columns, len(images))
    canvas = Image.new('RGB', (cols*w, math.ceil(len(images)/cols)*(h+28)), '#e7dfce')
    draw = ImageDraw.Draw(canvas)
    for i, (im, label) in enumerate(zip(images, labels)):
        im = im.copy().convert('RGBA')
        im.thumbnail((w, h))
        x, y = i % cols*w, i//cols*(h+28)
        canvas.paste(im, (x+(w-im.width)//2, y+(h-im.height)//2), im)
        draw.text((x+4, y+h+4), str(label), fill='black', font=caption_font)
    save(canvas, output)


def preview(c):
    out = safe_output(c)
    data = load_manifest(c['manifest'])
    base = render(c['manifest'])
    artifacts = [save(base, out/'reassembled.png')]
    joints = base.copy()
    draw = ImageDraw.Draw(joints)
    for n in data['nodes']:
        x, y = n['pivot_global']
        draw.ellipse((x-4, y-4, x+4, y+4), outline='magenta', width=2)
        draw.text((x+5, y), n['id'], fill='magenta', font=font(c))
    if data['nodes']:
        artifacts.append(save(joints, out/'joints.png'))
    tiles, labels = [], []
    for part in data['parts']:
        with Image.open(asset(Path(c['manifest']).parent, part['file'])) as im:
            tiles.append(im.convert('RGBA'))
        labels.append(part['id'])
    sheet(tiles, labels, out/'parts.png', c.get('columns', 4), caption_font=font(c))
    artifacts.append(out/'parts.png')
    inferred = base.copy()
    overlay = Image.new('RGBA', base.size)
    for p in data['parts']:
        if p.get('inferred_region_mask'):
            with Image.open(asset(Path(c['manifest']).parent, p['inferred_region_mask'])) as m:
                tint = Image.new('RGBA', m.size, (255, 0, 200, 0))
                tint.putalpha(m.convert('L').point(lambda v: min(v, 160)))
                overlay.alpha_composite(tint, tuple(p['crop_origin']))
    if overlay.getbbox():
        artifacts.append(save(Image.alpha_composite(inferred, overlay), out/'inferred.png'))
    if c.get('poses'):
        poses = read(c['poses'])
        poses = poses.get('poses', []) if isinstance(poses, dict) else poses
        if poses:
            sheet([render(c['manifest'], pose=p) for p in poses],
                  [p.get('id', i) for i, p in enumerate(poses)], out/'poses.png',
                  c.get('columns', 4), c.get('cell_size'), font(c))
            artifacts.append(out/'poses.png')
    if c.get('reference'):
        with Image.open(c['reference']) as ref:
            require(ref.size == base.size, 'reference dimensions mismatch')
            artifacts.append(save(ImageChops.difference(ref.convert('RGBA'), base), out/'difference.png'))
    return result(artifacts, visual_review='pending')


def check(c):
    data = load_manifest(c['manifest'])
    metrics, bounds = [], []
    poses = read(c['poses']) if c.get('poses') else [{'id': 'rest'}]
    poses = poses.get('poses', []) if isinstance(poses, dict) else poses
    radius, threshold = c.get('radius', 12), c.get('alpha_threshold', 1)
    require(isinstance(radius, int) and radius > 0 and 0 <= threshold <= 255, 'invalid measurement window/threshold')
    for pose in poses:
        matrices = pose_transforms(data, pose)
        for p in data['parts']:
            ox, oy = p['crop_origin']; w, h = p['pixel_size']
            points = [apply(matrices[p['node']], xy) for xy in ((ox, oy), (ox+w, oy), (ox+w, oy+h), (ox, oy+h))]
            box = [min(q[0] for q in points), min(q[1] for q in points), max(q[0] for q in points), max(q[1] for q in points)]
            bounds.append(dict(pose=pose.get('id'), part=p['id'], geometry_bounds=box,
                               outside_canvas=box[0] < 0 or box[1] < 0 or box[2] > data['source_size'][0] or box[3] > data['source_size'][1]))
        grouped = {}
        for n in data['nodes']:
            subset = dict(data, parts=[p for p in data['parts'] if p['node'] == n['id']])
            if not subset['parts']:
                continue
            # Reuse validated renderer by compositing each transformed cropped layer.
            layer = Image.new('RGBA', tuple(data['source_size']))
            from puppet_core import inverse, IDENTITY
            for p in sorted(subset['parts'], key=lambda p: p['z_index']):
                with Image.open(asset(Path(c['manifest']).parent, p['file'])) as im:
                    im = im.convert('RGBA')
                inv = list(inverse(matrices[n['id']]))
                inv[2] -= p['crop_origin'][0]; inv[5] -= p['crop_origin'][1]
                layer.alpha_composite(im.transform(layer.size, Image.Transform.AFFINE, inv))
            grouped[n['id']] = layer.getchannel('A').point(lambda v: 255 if v >= threshold else 0)
        for n in data['nodes']:
            parent = n['parent']
            if n['id'] not in grouped or parent not in grouped:
                continue
            x, y = apply(matrices[n['id']], n['pivot_global'])
            box = (round(x-radius), round(y-radius), round(x+radius+1), round(y+radius+1))
            overlap = ImageChops.multiply(grouped[n['id']], grouped[parent]).crop(box)
            metrics.append(dict(pose=pose.get('id'), node=n['id'], parent=parent,
                                overlap_pixels=sum(v > 0 for v in overlap.tobytes())))
    review = read(c['review']) if c.get('review') else None
    report = result(nodes=len(data['nodes']), parts=len(data['parts']), measurements=metrics, bounds=bounds,
                    visual_review=review if review is not None else 'pending')
    if c.get('output'):
        report['artifacts'] = [write(safe_output(c), report)]
    return report


def natural(path):
    return [int(v) if v.isdigit() else v.lower() for v in re.split(r'(\d+)', str(path))]


def media(c):
    frames = sorted((p for p in Path(c['frames']).iterdir() if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}), key=natural)
    require(frames, 'no image frames')
    fps = c.get('fps', 24)
    require(isinstance(fps, (int, float)) and not isinstance(fps, bool) and math.isfinite(fps) and fps > 0, 'fps must be positive')
    out = safe_output(c); out.mkdir(parents=True, exist_ok=True)
    formats = c.get('formats', ['gif', 'mp4', 'sheet'])
    require(set(formats) <= {'gif', 'mp4', 'sheet'}, 'unknown media format')
    images = []
    for p in frames:
        with Image.open(p) as im:
            images.append(im.convert('RGBA'))
    w, h = max(i.width for i in images), max(i.height for i in images)
    issues, artifacts = [], []
    if len({i.size for i in images}) > 1:
        issues.append('mixed frame sizes padded at top-left')
    rgb = []
    for im in images:
        canvas = Image.new('RGB', (w+(w % 2), h+(h % 2)), c.get('background', '#e7dfce'))
        canvas.paste(im, (0, 0), im)
        rgb.append(canvas)
    if 'gif' in formats:
        path = out/'animation.gif'
        rgb[0].save(path, save_all=True, append_images=rgb[1:], duration=round(1000/fps), loop=0)
        artifacts.append(path)
    if 'sheet' in formats:
        stride = max(1, math.ceil(len(images)/c.get('sheet_max_frames', 24)))
        path = out/'contact-sheet.png'
        sheet(images[::stride], [p.stem for p in frames[::stride]], path,
              c.get('columns', 4), c.get('cell_size', [256, 256]), font(c))
        artifacts.append(path)
    if 'mp4' in formats:
        executable = shutil.which(c.get('ffmpeg', 'ffmpeg'))
        if executable is None:
            issues.append('ffmpeg unavailable: MP4 not produced')
        else:
            import tempfile
            with tempfile.TemporaryDirectory(prefix='puppet-media-') as temp:
                for i, im in enumerate(rgb):
                    im.save(Path(temp)/f'{i:08d}.png')
                path = out/'animation.mp4'
                proc = subprocess.run([executable, '-y', '-v', 'error', '-framerate', str(fps), '-i', str(Path(temp)/'%08d.png'),
                                       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], capture_output=True, text=True)
                if proc.returncode:
                    issues.append('MP4 failed: '+proc.stderr[-1000:])
                else:
                    artifacts.append(path)
    r = result(artifacts, issues, frame_count=len(frames), visual_review='pending')
    if issues and 'mp4' in formats and out/'animation.mp4' not in artifacts:
        r['status'] = 'partial'
    return r


def package(c):
    out = safe_output(c)
    files = list(dict.fromkeys(Path(p).resolve() for p in c.get('files', [])))
    required = [Path(p).resolve() for p in c.get('required', [])]
    missing = [str(p) for p in set(files+required) if not p.is_file()]
    files = list(dict.fromkeys(p for p in files+required if p.is_file()))
    require(files, 'no files to package')
    # Explicit archive_root preserves hierarchy; without it unique basenames are required.
    root = Path(c['archive_root']).resolve() if c.get('archive_root') else None
    entries = {}
    for p in files:
        require(p != out.resolve(), 'archive cannot include itself')
        require(root is None or p.is_relative_to(root), f'file outside archive_root: {p}')
        name = p.relative_to(root).as_posix() if root else p.name
        require(name not in entries, f'archive name collision: {name}; set archive_root')
        entries[name] = p
    reference_issues = []
    if c.get('manifest'):
        manifest = Path(c['manifest']).resolve()
        data = load_manifest(manifest)
        by_path = {p: name for name, p in entries.items()}
        if manifest not in by_path:
            reference_issues.append('manifest not included in archive')
        else:
            import posixpath
            parent = posixpath.dirname(by_path[manifest])
            for part in data['parts']:
                for field in ('file', 'inferred_region_mask'):
                    if not part.get(field):
                        continue
                    value = part[field]
                    expected = posixpath.normpath(posixpath.join(parent, value))
                    resolved = asset(manifest.parent, value)
                    if Path(value).is_absolute() or by_path.get(resolved) != expected:
                        reference_issues.append('nonportable/missing archive reference: '+value)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, p in entries.items():
            z.write(p, name)
    with zipfile.ZipFile(out) as z:
        require(z.testzip() is None, 'ZIP CRC failure')
    hashes = {name: digest(p) for name, p in entries.items()}
    meta = out.with_suffix(out.suffix+'.json')
    require(meta.resolve() not in set(files+required), 'package report would overwrite input')
    write(meta, dict(sha256=digest(out), files=hashes, missing=missing, reference_issues=reference_issues, visual_review='pending'))
    r = result([out, meta], ['missing: '+p for p in missing]+reference_issues, file_count=len(entries),
               reference_check='checked' if c.get('manifest') else 'not_requested')
    if missing or reference_issues:
        r['status'] = 'partial'
    return r


def blender(c, reopen=False):
    executable = c.get('blender') or shutil.which('blender')
    if not executable and Path('/Applications/Blender.app/Contents/MacOS/Blender').is_file():
        executable = '/Applications/Blender.app/Contents/MacOS/Blender'
    if not executable:
        return dict(status='partial', artifacts=[], issues=['Blender unavailable'])
    out = safe_output(c)
    script = Path(__file__).with_name('blender_io.py')
    command = [executable, '--background']
    if reopen:
        command.append(c['blend'])
    else:
        load_manifest(c['manifest'])
        command.append('--factory-startup')
    command += ['-t', str(c.get('threads', 2)), '--python-exit-code', '1', '--python', str(script), '--']
    if reopen:
        command += ['--reopen-report', c['scene_report'], '--out', str(out)]
    else:
        command += ['--manifest', c['manifest'], '--out', str(out)]
        if c.get('motion_plan'):
            command += ['--motion-plan', c['motion_plan']]
        if c.get('render', False):
            command += ['--render']
        if c.get('resolution'):
            command += ['--resolution', *[str(v) for v in c['resolution']]]
    proc = subprocess.run(command, capture_output=True, text=True)
    log = out.with_suffix('.log') if reopen else out/'blender.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(proc.stdout+'\n'+proc.stderr)
    if proc.returncode:
        return dict(status='failed', artifacts=[str(log)], issues=['Blender failed; see log'], exit_code=proc.returncode)
    artifacts = [out, log] if reopen else [out/'rig.blend', out/'io-report.json', log, *sorted((out/'preview').glob('*.png'))]
    return result(artifacts, visual_review='pending')


OPS = {'info': image_info, 'extract': extract, 'masks': combine_masks, 'register': register,
       'patch': patch, 'render': render_op, 'preview': preview, 'check': check, 'media': media, 'package': package,
       'blender': blender, 'reopen': lambda c: blender(c, reopen=True)}


def fingerprint(op, config):
    # Include tool source and actual input contents, rather than mtimes or filenames only.
    payload = {'op': op, 'config': config, 'inputs': {str(p): digest(p) if p.is_file() else 'missing' for p in inputs(config)},
               'code': {p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def run_pipeline(c, base, report_path, force=False):
    steps = c.get('steps', [])
    require(isinstance(steps, list) and steps, 'steps must not be empty')
    ids = [s['id'] for s in steps]
    require(len(set(ids)) == len(ids), 'duplicate step id')
    for s in steps:
        require(s['op'] in OPS, f'unknown operation: {s["op"]}')
        require(all(d in ids and d != s['id'] for d in s.get('depends_on', [])), 'unknown/self dependency')
    protected = set()
    for step in steps:
        raw = step.get('config', {})
        try:
            if isinstance(raw, str):
                path = (base/raw).resolve()
                protected.add(path)
                cfg = resolve_config(read(path), path.parent)
            else:
                cfg = resolve_config(raw, base)
            protected.update(p.resolve() for p in inputs(cfg))
        except (OSError, ValueError, TypeError, KeyError):
            continue
        if cfg.get('output'):
            require(Path(report_path).resolve() != Path(cfg['output']).resolve(), 'pipeline report collides with step output')
    require(Path(report_path).resolve() not in protected, 'pipeline report would overwrite input')
    old = read(report_path).get('steps', {}) if Path(report_path).is_file() else {}
    records, pending = {}, list(steps)
    started = time.perf_counter()
    while pending:
        ready = [s for s in pending if all(d in records for d in s.get('depends_on', []))]
        require(ready, 'dependency cycle')
        for step in ready:
            sid = step['id']; t = time.perf_counter()
            previous = old.get(sid, {})
            try:
                cfg = step.get('config', {})
                if isinstance(cfg, str):
                    path = (base/cfg).resolve(); cfg = resolve_config(read(path), path.parent)
                else:
                    cfg = resolve_config(cfg, base)
                bad = [d for d in step.get('depends_on', []) if records[d]['status'] in ('failed', 'blocked', 'skipped') or records[d]['status'] == 'partial' and not records[d].get('artifacts')]
                if bad:
                    r = dict(status='blocked', artifacts=[], issues=['dependencies unavailable: '+', '.join(bad)])
                else:
                    key = fingerprint(step['op'], cfg)
                    unchanged = previous.get('artifact_hashes') == {p: digest(p) if Path(p).is_file() else None for p in previous.get('artifacts', [])}
                    if not force and previous.get('fingerprint') == key and previous.get('status') in ('ok', 'cached') and unchanged:
                        r = dict(previous, status='cached')
                    else:
                        r = OPS[step['op']](cfg)
                    r['fingerprint'] = key
            except (ValueError, OSError, KeyError, TypeError) as exc:
                r = dict(status='failed', artifacts=[], issues=[str(exc)])
            r['duration_seconds'] = round(time.perf_counter()-t, 6)
            r['required'] = step.get('required', True)
            r['artifact_hashes'] = {p: digest(p) for p in r.get('artifacts', []) if Path(p).is_file()}
            records[sid] = r; pending.remove(step)
            write(report_path, dict(status='running', steps=records))
    unmet = [k for k, r in records.items() if r['required'] and r['status'] not in ('ok', 'cached')]
    r = dict(status='partial' if unmet else 'ok', steps=records, unmet_required_steps=unmet,
             duration_seconds=round(time.perf_counter()-started, 6), visual_review='pending')
    write(report_path, r)
    return r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=[*OPS, 'run'])
    parser.add_argument('--config', type=Path)
    for key in ('source', 'mask', 'manifest', 'poses', 'reference', 'frames', 'output', 'report'):
        parser.add_argument('--'+key.replace('_', '-'))
    parser.add_argument('--formats', help='comma-separated gif,mp4,sheet')
    parser.add_argument('--fps', type=float)
    parser.add_argument('--force', action='store_true', help='ignore successful cached steps')
    args = parser.parse_args()
    try:
        base = args.config.resolve().parent if args.config else Path.cwd()
        raw = read(args.config) if args.config else {}
        c = resolve_config(raw, base)
        for key in ('source', 'mask', 'manifest', 'poses', 'reference', 'frames', 'output', 'report'):
            if getattr(args, key) is not None:
                c[key] = str(Path(getattr(args, key)).resolve())
        if args.formats:
            c['formats'] = args.formats.split(',')
        if args.fps is not None:
            c['fps'] = args.fps
        if args.config:
            for field in ('output', 'report'):
                require(not c.get(field) or Path(c[field]).resolve() != args.config.resolve(), 'output would overwrite config')
        if args.operation == 'run':
            r = run_pipeline(raw, base, c.get('report', str(base/'run-report.json')), args.force)
        else:
            r = OPS[args.operation](c)
            if c.get('report'):
                require(Path(c['report']).resolve() not in {p.resolve() for p in inputs(c)}, 'report would overwrite input')
                write(c['report'], r)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r['status'] == 'ok' else 2
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps(dict(status='failed', issues=[str(exc)]), ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
