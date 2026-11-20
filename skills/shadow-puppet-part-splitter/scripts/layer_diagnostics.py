"""Declared draw-order and motion-parent diagnostics; no semantic inference."""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
from puppet_core import read_manifest, normalize, pose_transforms, require


def active(rule, frame):
    return 'frames' not in rule or rule['frames'][0] <= frame <= rule['frames'][1]


def cycle_at(rules, frame):
    graph={}
    for r in rules:
        if active(r,frame): graph.setdefault(r['back'],[]).append(r['front'])
    done=set()
    def visit(key,chain):
        if key in chain:return chain[chain.index(key):]+[key]
        if key in done:return None
        for other in graph.get(key,[]):
            cycle=visit(other,chain+[key])
            if cycle:return cycle
        done.add(key)
        return None
    for key in graph:
        cycle=visit(key,[])
        if cycle:return cycle
    return None


def layers(manifest, config, output):
    # Explicit diagnostic access, including blocked/stale compilations.
    from assembly_diagnostics import alpha_layer
    from puppet import render
    require(isinstance(config,dict),'layer config must be an object')
    data=read_manifest(manifest,allow_unverified=True)
    data['occlusion_rules']=config.get('occlusion_rules',data.get('occlusion_rules',[]))
    data['expected_parents']=config.get('expected_parents',data.get('expected_parents',{}))
    data=normalize(data);rules=data['occlusion_rules'];expected=data['expected_parents']
    require(rules or expected,'no declared layer or parent rules to validate')
    parts={p['id']:p for p in data['parts']};nodes={n['id']:n for n in data['nodes']}
    order=sorted(parts,key=lambda key:parts[key]['z_index']);rank={key:i for i,key in enumerate(order)}
    events={0}
    for rule in rules:
        if 'frames' in rule:events.update((rule['frames'][0],rule['frames'][1]+1))
    cycles=[]
    for frame in sorted(events):
        cycle=cycle_at(rules,frame)
        if cycle:cycles.append(dict(interval_start=frame,cycle=cycle))
    parent_errors=[dict(node=node,expected=parent,actual=nodes[node]['parent'])
                   for node,parent in expected.items() if nodes[node]['parent']!=parent]
    frames=config.get('frames',[{'frame':0,'pose':{}}]);require(isinstance(frames,list) and frames,'frames must be nonempty')
    require(len(frames)<=1000,'too many frame samples')
    require(all(isinstance(s,dict) for s in frames),'each frame sample must be an object')
    frame_ids=[s.get('frame') for s in frames]
    require(all(isinstance(f,int) and not isinstance(f,bool) and f>=0 for f in frame_ids) and len(set(frame_ids))==len(frame_ids),'invalid/duplicate frame')
    threshold=config.get('alpha_threshold',1);require(isinstance(threshold,int) and not isinstance(threshold,bool) and 1<=threshold<=255,'alpha_threshold must be 1..255')
    rows=[];count=lambda im:sum(im.histogram()[1:]);base=Path(manifest).resolve().parent
    for sample in sorted(frames,key=lambda s:s['frame']):
        frame=sample['frame'];pose=sample.get('pose',{});mats=pose_transforms(data,pose,enforce_limits=False)
        # Include every part for actual visible top-ID ownership, including third-party occluders.
        alphas={key:alpha_layer(data,p,base,mats) for key,p in parts.items()}
        supports={key:im.point(lambda v:255 if v>=threshold else 0) for key,im in alphas.items()}
        owner=Image.new('RGB',tuple(data['source_size']));colors={key:(i+1) for i,key in enumerate(order)}
        require(len(order)<16777215,'too many draw parts for RGB ID image')
        for key in order:
            n=colors[key];owner.paste((n&255,(n>>8)&255,(n>>16)&255),(0,0),supports[key])
        owner.save(output/f'frame-{frame:06d}-ids.png')
        violations=Image.new('L',owner.size);cases=[]
        for i,rule in enumerate(rules):
            if not active(rule,frame):continue
            front,back=rule['front'],rule['back'];overlap=ImageChops.multiply(supports[front],supports[back])
            if 'region' in rule:
                roi=Image.new('L',owner.size);x0,y0,x1,y1=rule['region']
                ImageDraw.Draw(roi).rectangle((x0,y0,x1-1,y1-1),fill=255);overlap=ImageChops.multiply(overlap,roi)
            correct=rank[front]>rank[back];visible=overlap.copy()
            # A later opaque part can hide the pair. Translucent covers do not erase the warning.
            for key in order[max(rank[front],rank[back])+1:]:
                visible=ImageChops.subtract(visible,alphas[key].point(lambda v:255 if v==255 else 0))
            bad=visible if not correct else Image.new('L',owner.size)
            violations=ImageChops.lighter(violations,bad)
            cases.append(dict(rule=i,front=front,back=back,order_correct=correct,
                              overlap_pixels=count(overlap),visible_violation_pixels=count(bad),
                              hidden_wrong_order_pixels=count(ImageChops.subtract(overlap,visible)) if not correct else 0))
        image=render(manifest,pose=pose,enforce_limits=False,diagnostic=True)
        tint=Image.new('RGBA',image.size,'red');tint.putalpha(violations.point(lambda v:190 if v else 0));Image.alpha_composite(image,tint).save(output/f'frame-{frame:06d}-violations.png')
        rows.append(dict(frame=frame,rules=cases,violation_pixels=count(violations)))
    unsampled=[i for i,r in enumerate(rules) if not any(active(r,f) for f in frame_ids)]
    failed=bool(cycles or parent_errors or any(row['violation_pixels'] for row in rows))
    warnings=bool(unsampled or any(not c['order_correct'] for row in rows for c in row['rules']))
    return dict(status='fail' if failed else 'warning' if warnings else 'pass-sampled',
                draw_order=order,id_colors={k:[v&255,(v>>8)&255,(v>>16)&255] for k,v in colors.items()} if rows else {},
                parent_errors=parent_errors,occlusion_cycles=cycles,frames=rows,unsampled_rules=unsampled,
                alpha_threshold=threshold,coverage='explicit samples only; no motion interpolation or continuous approval',
                limitations='RGB IDs show top alpha-support ownership, not physical material opacity. Transparent overlap and fixed z-order cannot prove anatomy or implement animated layer switching.')
