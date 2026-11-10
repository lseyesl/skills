#!/usr/bin/env python3
"""Diagnostic comparisons; measurements never approve an asset or infer anatomy."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
from compile_character import visible_diff
from puppet_core import read_manifest, pose_transforms, apply, inverse, require, asset, pair
from toolbox import sheet


def pixels(reference, candidate, output, threshold=0):
    require(isinstance(threshold,int) and 0 <= threshold <= 255, 'threshold must be 0..255')
    with Image.open(reference) as im: a=im.convert('RGBA')
    with Image.open(candidate) as im: b=im.convert('RGBA')
    require(a.size==b.size, 'pixel comparison requires identical canvas/registration')
    diff=visible_diff(a,b); values=diff.tobytes()
    selected=diff.point(lambda v:255 if v>threshold else 0)
    aa=a.getchannel('A').point(lambda v:255 if v else 0); ba=b.getchannel('A').point(lambda v:255 if v else 0)
    inter=ImageChops.multiply(aa,ba); union=ImageChops.lighter(aa,ba)
    count=lambda im:sum(im.histogram()[1:])
    heat=Image.new('RGBA',a.size,'red');heat.putalpha(selected.point(lambda v:180 if v else 0))
    Image.alpha_composite(a,heat).save(output/'pixel-overlay.png');diff.save(output/'pixel-error.png')
    return dict(changed_pixels=count(selected),max_channel_error=max(values),
                mean_max_channel_error=sum(values)/len(values),rms_max_channel_error=math.sqrt(sum(v*v for v in values)/len(values)),
                changed_bbox=selected.getbbox(),alpha_support_iou=count(inter)/count(union) if count(union) else 1,
                threshold=threshold,alignment='unchanged; no automatic registration')


def axes(reference, candidate, output, pose=None, tolerance=1):
    require(math.isfinite(tolerance) and tolerance>=0,'invalid axis tolerance')
    a=read_manifest(reference,allow_unverified=True);b=read_manifest(candidate,allow_unverified=True)
    require(a['source_size']==b['source_size'],'axis comparison requires identical coordinates/scale')
    an={n['id']:n for n in a['nodes']};bn={n['id']:n for n in b['nodes']}
    require(pose is None or set(an)==set(bn),'pose comparison requires matching node IDs')
    am=pose_transforms(a,pose);bm=pose_transforms(b,pose)
    canvas=Image.new('RGB',tuple(a['source_size']),'#e7dfce');draw=ImageDraw.Draw(canvas);rows=[]
    for key in sorted(set(an)&set(bn)):
        x=apply(am[key],an[key]['pivot_global']);y=apply(bm[key],bn[key]['pivot_global'])
        distance=math.dist(x,y)
        angle=lambda m:math.degrees(math.atan2(m[3],m[0]))
        delta=(angle(bm[key])-angle(am[key])+180)%360-180
        row=dict(node=key,reference=x,candidate=y,pivot_error_pixels=distance,world_angle_error_degrees=delta,
                 parent_changed=an[key]['parent']!=bn[key]['parent'],within_pivot_tolerance=distance<=tolerance)
        rows.append(row);draw.line([tuple(x),tuple(y)],fill='red',width=2)
        for pos,color in ((x,'green'),(y,'red')):
            px,py=pos;draw.ellipse((px-3,py-3,px+3,py+3),outline=color)
        draw.text(tuple(y),key,fill='black')
    canvas.save(output/'axis-overlay.png')
    return dict(nodes=rows,missing_nodes=sorted(set(an)-set(bn)),extra_nodes=sorted(set(bn)-set(an)),
                reference_assumption='Caller supplies a reviewed reference; matching two wrong rigs proves nothing.')


def alpha_layer(data,part,base,matrices):
    with Image.open(asset(base,part['file'])) as im: alpha=im.convert('RGBA').getchannel('A')
    inv=list(inverse(matrices[part['node']]));inv[2]-=part['crop_origin'][0];inv[5]-=part['crop_origin'][1]
    return alpha.transform(tuple(data['source_size']),Image.Transform.AFFINE,inv,resample=Image.Resampling.BILINEAR)


def sweep(manifest,config,output):
    data=read_manifest(manifest,allow_unverified=True);base=Path(manifest).resolve().parent
    parts={p['id']:p for p in data['parts']};nodes={n['id']:n for n in data['nodes']}
    node=config['node'];require(node in nodes,'unknown sweep node')
    lo,hi=config['range'];step=config.get('step',1)
    require(all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (lo,hi,step)) and lo<=hi and step>0,'invalid sweep range/step')
    require((hi-lo)/step<=720,'too many samples; maximum 721')
    angles=[lo+i*step for i in range(math.floor((hi-lo)/step)+1)]
    if angles[-1]<hi:angles.append(hi)
    pa,pb=[parts[k] for k in config['parts']];require(pa['id']!=pb['id'],'sweep needs two distinct parts')
    radius=config.get('radius',20);require(isinstance(radius,(int,float)) and math.isfinite(radius) and radius>0,'invalid radius')
    anchors=config.get('anchors');require(anchors is None or len(anchors)==2 and all(pair(p) for p in anchors),'anchors must be two reference-canvas points')
    rows=[];tiles=[]
    for i,angle in enumerate(angles):
        pose=dict(config.get('base_pose',{}));pose['angles']=dict(pose.get('angles',{}),**{node:angle})
        # Target samples may deliberately exceed delivered limits. Never approve them here.
        mats=pose_transforms(data,pose,enforce_limits=False)
        a,b=[alpha_layer(data,p,base,mats) for p in (pa,pb)]
        # Compare support, not quantized alpha products: 1*1/255 rounds to zero.
        overlap=ImageChops.multiply(a.point(lambda v:255 if v else 0),b.point(lambda v:255 if v else 0))
        center=apply(mats[node],nodes[node]['pivot_global']);roi=Image.new('L',a.size);x,y=center
        ImageDraw.Draw(roi).ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
        overlap_count=sum(ImageChops.multiply(overlap,roi).histogram()[1:])
        union=ImageChops.lighter(a,b);bbox=union.getbbox()
        row=dict(angle=angle,joint_roi_overlap_pixels=overlap_count,
                 alpha_touches_canvas=bool(bbox and (bbox[0]==0 or bbox[1]==0 or bbox[2]==a.width or bbox[3]==a.height)))
        if anchors:
            row['anchor_distance_pixels']=math.dist(apply(mats[pa['node']],anchors[0]),apply(mats[pb['node']],anchors[1]))
        rows.append(row)
        tile=Image.new('RGB',a.size,'#e7dfce');red=Image.new('RGB',a.size,'#cf5c42');blue=Image.new('RGB',a.size,'#327cb3')
        tile.paste(red,(0,0),a);tile.paste(blue,(0,0),b);draw=ImageDraw.Draw(tile);draw.ellipse((x-radius,y-radius,x+radius,y+radius),outline='black')
        if anchors:
            draw.line([tuple(apply(mats[p['node']],point)) for p,point in zip((pa,pb),anchors)],fill='yellow',width=2)
        tile.save(output/f'sweep-{i:04d}.png')
        if i in {0,len(angles)//2,len(angles)-1}:tiles.append((tile,str(angle)))
    sheet([t[0] for t in tiles],[t[1] for t in tiles],output/'sweep-summary.png',columns=3)
    return dict(samples=rows,zero_overlap_angles=[r['angle'] for r in rows if r['joint_roi_overlap_pixels']==0],
                limitations='Overlap near pivot cannot certify an entire sleeve seam. Anchor positions are supplied evidence, not automatically detected. Canvas contact is a warning, not proof of clipping.')


def fit_pivot(config, output):
    """Fit a fixed-parent planar pivot from independently measured landmark pairs."""
    size=config['source_size'];require(pair(size,integer=True) and min(size)>0,'invalid source_size')
    observations=config['observations'];require(len(observations)>=2,'at least two independent landmark observations required')
    numerator=[0.0,0.0];denominator=0;prepared=[]
    for o in observations:
        angle=o['angle'];x=o['before'];q=o['after']
        require(pair(x) and pair(q) and isinstance(angle,(int,float)) and not isinstance(angle,bool) and math.isfinite(angle),'invalid observation')
        theta=math.radians(angle);c=math.cos(theta);sn=math.sin(theta);u=1-c
        bx=q[0]-c*x[0]+sn*x[1];by=q[1]-sn*x[0]-c*x[1]
        numerator[0]+=u*bx-sn*by;numerator[1]+=sn*bx+u*by;denominator+=u*u+sn*sn
        prepared.append((x,q,c,sn))
    require(math.isfinite(denominator) and all(math.isfinite(v) for v in numerator),'pivot fit overflow')
    require(denominator>1e-8,'degenerate pivot fit: meaningful rotation required')
    pivot=[v/denominator for v in numerator];residuals=[]
    canvas=Image.new('RGB',tuple(size),'#e7dfce');draw=ImageDraw.Draw(canvas)
    for x,q,c,sn in prepared:
        predicted=[pivot[0]+c*(x[0]-pivot[0])-sn*(x[1]-pivot[1]),pivot[1]+sn*(x[0]-pivot[0])+c*(x[1]-pivot[1])]
        require(all(math.isfinite(v) for v in predicted),'pivot prediction overflow')
        residuals.append(math.dist(predicted,q));require(math.isfinite(residuals[-1]),'pivot residual overflow');draw.line([tuple(predicted),tuple(q)],fill='red',width=2)
    px,py=pivot;draw.ellipse((px-5,py-5,px+5,py+5),outline='green',width=2)
    canvas.save(output/'fitted-pivot.png')
    return dict(suggested_pivot=pivot,suggested_pivot_inside_canvas=0<=px<size[0] and 0<=py<size[1],landmark_residual_pixels=residuals,rms_residual_pixels=math.sqrt(sum(v*v for v in residuals)/len(residuals)),
                conditioning_denominator=denominator,assumptions='Fixed parent, rigid part, known clockwise angle, same source coordinates; no camera movement or scale change. Suggestions do not modify the rig.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('pixels','axes','sweep','fit-pivot','layers'):
        p=sub.add_parser(name);p.add_argument('--output',required=True,type=Path)
        if name in ('sweep','fit-pivot','layers'):
            p.add_argument('--config',required=True,type=Path)
            if name in ('sweep','layers'):p.add_argument('--manifest',required=True,type=Path)
        else:p.add_argument('--reference',required=True,type=Path);p.add_argument('--candidate',required=True,type=Path)
        if name=='pixels':p.add_argument('--threshold',type=int,default=0)
        if name=='axes':p.add_argument('--pose',type=Path);p.add_argument('--tolerance',type=float,default=1)
    args=parser.parse_args()
    try:
        require(not args.output.exists(),'diagnostic output already exists; choose a new directory');args.output.mkdir(parents=True)
        if args.command=='pixels':report=pixels(args.reference,args.candidate,args.output,args.threshold)
        elif args.command=='axes':report=axes(args.reference,args.candidate,args.output,json.loads(args.pose.read_text()) if args.pose else None,args.tolerance)
        elif args.command=='sweep':report=sweep(args.manifest,json.loads(args.config.read_text()),args.output)
        elif args.command=='layers':
            from layer_diagnostics import layers
            report=layers(args.manifest,json.loads(args.config.read_text()),args.output)
        else:report=fit_pivot(json.loads(args.config.read_text()),args.output)
        report.update(purpose='diagnostic-only',visual_review='pending')
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
        if args.command=='layers' and report['status']=='fail':parser.exit(2,'layer constraint violation; inspect report and overlays\n')
    except (ValueError,KeyError,TypeError,OSError) as exc:parser.exit(1,f'error: {exc}\n')

if __name__=='__main__':main()
