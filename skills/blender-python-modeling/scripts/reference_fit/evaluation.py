"""Visible-region 2D evidence. No per-part registration, no 3D similarity claims."""
from pathlib import Path
import json, math, hashlib
import cv2
import numpy as np
from analyze_reference_images import foreground_mask, iou


def read(path):
    a=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
    if a is None: raise FileNotFoundError(path)
    return a


def annotations(path,image):
    a=json.loads(Path(path).read_text())
    if a.get('schema_version')!=1: raise ValueError('Unsupported annotation version')
    if a.get('image_size')!=[image.shape[1],image.shape[0]]: raise ValueError('Annotation/image dimensions differ')
    if not a.get('components'): raise ValueError('No trusted annotations; manual masks or polygons required')
    return a


def reference_masks(image,a,base):
    h,w=image.shape[:2]
    fg,_=foreground_mask(image[:,:,:3],image[:,:,3] if image.shape[2]==4 else None)
    if not .005<np.count_nonzero(fg)/fg.size<.95: raise ValueError('Unreliable foreground segmentation; supply alpha')
    masks={};evidence={}
    for name,item in a['components'].items():
        confidence=item.get('confidence',0)
        if not isinstance(confidence,(int,float)) or not 0<=confidence<=1: raise ValueError('Invalid annotation confidence')
        if confidence<.7 or item.get('status')=='not_evaluable':
            evidence[name]={'status':'not_evaluable','reason':item.get('reason','confidence below 0.7')};continue
        if 'mask' in item:
            m=read(Path(base)/item['mask'])
            if m.ndim==3:m=m[:,:,0]
            if m.shape!=(h,w): raise ValueError('Component mask size mismatch')
            m=(m>127).astype('uint8')*255
        elif 'polygon' in item:
            poly=np.asarray(item['polygon'])
            if poly.ndim!=2 or poly.shape[1]!=2 or len(poly)<3 or not np.isfinite(poly).all(): raise ValueError('Invalid annotation polygon')
            m=np.zeros((h,w),np.uint8);cv2.fillPoly(m,[poly.astype(np.int32)],255)
            m=cv2.bitwise_and(m,fg)
        else: raise ValueError('Trusted component needs explicit mask/polygon: '+name)
        if not np.any(m):raise ValueError('Empty trusted mask: '+name)
        masks[name]=m;evidence[name]={'status':'measured','confidence':confidence,'source':item.get('source','supplied annotation'),'scope':'visible pixels only'}
    return fg,masks,evidence


def boundary_distance(a,b,height):
    if not np.any(a) or not np.any(b):return None
    kernel=np.ones((3,3),np.uint8)
    aa=(a>0).astype(np.uint8);bb=(b>0).astype(np.uint8)
    ea=aa-cv2.erode(aa,kernel);eb=bb-cv2.erode(bb,kernel)
    da=cv2.distanceTransform(1-ea,cv2.DIST_L2,5);db=cv2.distanceTransform(1-eb,cv2.DIST_L2,5)
    return float((db[ea>0].mean()+da[eb>0].mean())/(2*height))


def align(reference,render,mode='none'):
    """One recorded global isotropic scale + translation; never deform parts."""
    if mode not in ['none','bbox_similarity']:raise ValueError('Only none/bbox_similarity alignment permitted')
    if reference.shape!=render.shape: raise ValueError('Alignment inputs must share canvas dimensions')
    if not np.any(reference) or not np.any(render):raise ValueError('Cannot align empty silhouettes')
    matrix=np.array([[1.,0.,0.],[0.,1.,0.]])
    before=iou(reference,render)
    if mode=='bbox_similarity':
        rx,ry,rw,rh=cv2.boundingRect(reference);x,y,w,h=cv2.boundingRect(render)
        scale=rh/h
        matrix=np.array([[scale,0,rx+(rw-1)/2-scale*(x+(w-1)/2)],[0,scale,ry-scale*y+(scale-1)/2]])
    transformed=cv2.warpAffine(render,matrix,(reference.shape[1],reference.shape[0]),flags=cv2.INTER_NEAREST)
    return matrix,{'mode':mode,'before':{'scale':1,'translation_px':[0,0]},'after':{'scale':float(matrix[0,0]),'translation_px':matrix[:,2].tolist()},'iou_before':before,'iou_after':iou(reference,transformed),'part_warps':False}


def color_delta(a,b,ma,mb):
    if not np.any(ma) or not np.any(mb):return None
    # Float OpenCV Lab yields CIE L*a*b* units; median is robust to small highlights.
    la=cv2.cvtColor(a[:,:,:3].astype(np.float32)/255,cv2.COLOR_BGR2LAB)
    lb=cv2.cvtColor(b[:,:,:3].astype(np.float32)/255,cv2.COLOR_BGR2LAB)
    ca=np.median(la[ma>0],axis=0);cb=np.median(lb[mb>0],axis=0)
    return {'delta_e76':float(np.linalg.norm(ca-cb)),'reference_lab':ca.tolist(),'render_lab':cb.tolist(),'status':'descriptive','reason':'Reference illumination is unknown; albedo comparison is not intrinsic reflectance recovery.'}


def sampled_colors(image,masks):
    """Robust observed sRGB, not intrinsic material/lighting decomposition."""
    out={}
    for name,mask in masks.items():
        pixels=image[:,:,:3][mask>0]
        if not len(pixels):continue
        bgr=np.median(pixels,axis=0).round().astype(int)
        out[name]={'hex':'#'+''.join(f'{v:02X}' for v in bgr[::-1]),'sample_count':len(pixels),'scope':'observed reference color; illumination unknown'}
    return out


def evaluate(reference,annotation,render_dir,output,alignment='none'):
    ref=read(reference);a=annotations(annotation,ref)
    fg,parts,evidence=reference_masks(ref,a,Path(annotation).parent)
    folder=Path(render_dir);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((folder/'render-record.json').read_text())
    model=read(folder/'silhouette_front.png')
    mm=(model[:,:,3]>127).astype(np.uint8)*255 if model.shape[2]==4 else (model[:,:,0]>127).astype(np.uint8)*255
    h,w=fg.shape
    if mm.shape!=fg.shape: raise ValueError('Render/reference canvas differs; fix camera/render configuration')
    transform,reg=align(fg,mm,alignment)
    warp=lambda im,nearest=False:cv2.warpAffine(im,transform,(w,h),flags=cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR)
    mm=warp(mm,True);height=cv2.boundingRect(fg)[3]
    beauty=warp(read(folder/'beauty_front.png'));albedo=warp(read(folder/'albedo_front.png'))
    labels=warp(read(folder/'labels_front.png'),True)
    results={}
    for name,item in evidence.items():
        if name not in parts:results[name]=item;continue
        ids=manifest.get('part_colors',{}).get(name)
        if ids is None:results[name]={'status':'not_evaluable','reason':'No render part ID','confidence':item['confidence']};continue
        bgr=np.asarray(ids[::-1],np.float32)
        m=(np.linalg.norm(labels[:,:,:3].astype(np.float32)-bgr,axis=2)<20).astype(np.uint8)*255
        if labels.shape[2]==4:m[labels[:,:,3]<127]=0
        cv2.imwrite(str(out/(name+'-reference-mask.png')),parts[name]);cv2.imwrite(str(out/(name+'-model-mask.png')),m)
        box1=cv2.boundingRect(parts[name]);box2=cv2.boundingRect(m) if np.any(m) else None
        results[name]={**item,'iou':iou(parts[name],m),'boundary_distance':boundary_distance(parts[name],m,height),'reference_bbox':list(box1),'model_bbox':list(box2) if box2 else None,'color':color_delta(ref,albedo,parts[name],m)}
    landmarks=[]
    for name,p in a.get('landmarks',{}).items():
        q=manifest.get('landmarks_px',{}).get(name)
        if p.get('confidence',0)<.7 or q is None:
            landmarks.append({'name':name,'status':'not_evaluable'});continue
        xy=np.asarray(p['xy'],float);q=transform[:,:2]@np.asarray(q)+transform[:,2]
        landmarks.append({'name':name,'status':'measured','reference_px':xy.tolist(),'render_px':q.tolist(),'error_normalized':float(np.linalg.norm(xy-q)/height),'confidence':p['confidence']})
    errors=[p['error_normalized'] for p in landmarks if p['status']=='measured']
    report={'schema_version':1,'global':{'iou':iou(fg,mm),'boundary_distance':boundary_distance(fg,mm,height)},'alignment':reg,'components':results,'landmarks':{'items':landmarks,'mean':float(np.mean(errors)) if errors else None,'max':max(errors) if errors else None,'status':'measured' if errors else 'not_evaluable'},'normalization_height_px':height,'reference':str(Path(reference).resolve()),'render_record':manifest,'unmeasured':['3D shape accuracy from front image','hidden geometry fidelity','intrinsic reference material reflectance'],'confidence_policy':'Only supplied masks/polygons >=0.7; no inferred component score.'}
    base=ref[:,:,:3].copy()
    if ref.shape[2]==4:base=np.where(ref[:,:,3:4]>127,base,240).astype('uint8')
    shown=beauty[:,:,:3].copy()
    if beauty.shape[2]==4:shown=np.where(beauty[:,:,3:4]>127,shown,240).astype('uint8')
    overlay=cv2.addWeighted(base,.5,shown,.5,0)
    cv2.drawContours(overlay,cv2.findContours(fg,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(255,200,0),1)
    cv2.drawContours(overlay,cv2.findContours(mm,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(180,0,255),1)
    for p in landmarks:
        if p['status']=='measured':cv2.line(overlay,tuple(np.rint(p['reference_px']).astype(int)),tuple(np.rint(p['render_px']).astype(int)),(0,0,255),1)
    heat=np.full((h,w,3),240,np.uint8);heat[(fg>0)&(mm==0)]=(40,40,235);heat[(fg==0)&(mm>0)]=(230,120,25);heat[(fg>0)&(mm>0)]=(165,195,165)
    for name,im in [('overlay_front.png',overlay),('difference_heatmap.png',heat),('reference.png',base)]:cv2.imwrite(str(out/name),im)
    report['input_hashes']={'reference_sha256':hashlib.sha256(Path(reference).read_bytes()).hexdigest(),'annotation_sha256':hashlib.sha256(Path(annotation).read_bytes()).hexdigest(),'part_masks_sha256':{name:hashlib.sha256(mask.tobytes()).hexdigest() for name,mask in parts.items()}}
    (out/'metrics.json').write_text(json.dumps(report,indent=2));return report


def compare(before,after):
    out={'global_iou':after['global']['iou']-before['global']['iou'],'components':{}}
    for name,p in after['components'].items():
        q=before['components'].get(name,{})
        if 'iou' in p and 'iou' in q:out['components'][name]=p['iou']-q['iou']
    return out
