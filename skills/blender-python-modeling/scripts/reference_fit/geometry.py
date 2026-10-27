"""Pure cross-section and sweep sampling. Coordinates are normalized height units."""
import math

def lerp(a,b,t): return a+(b-a)*t

def sample(rows,t):
    if t<=rows[0][0]: return rows[0][1:]
    if t>=rows[-1][0]: return rows[-1][1:]
    for a,b in zip(rows,rows[1:]):
        if a[0]<=t<=b[0]:
            i=rows.index(a);span=b[0]-a[0];u=(t-a[0])/span
            out=[]
            for col in range(1,len(a)):
                slope=(b[col]-a[col])/span
                def tangent(index):
                    if index==0:return (rows[1][col]-rows[0][col])/(rows[1][0]-rows[0][0])
                    if index==len(rows)-1:return (rows[-1][col]-rows[-2][col])/(rows[-1][0]-rows[-2][0])
                    left=(rows[index][col]-rows[index-1][col])/(rows[index][0]-rows[index-1][0])
                    right=(rows[index+1][col]-rows[index][col])/(rows[index+1][0]-rows[index][0])
                    return 2*left*right/(left+right) if left*right>0 else 0
                m0=tangent(i);m1=tangent(i+1)
                value=(2*u**3-3*u*u+1)*a[col]+(u**3-2*u*u+u)*span*m0+(-2*u**3+3*u*u)*b[col]+(u**3-u*u)*span*m1
                out.append(max(min(a[col],b[col]),min(max(a[col],b[col]),value)))
            return out

def loft(p,rings=40,sides=64):
    rows=p['sections'];verts=[];faces=[]
    for j in range(rings+1):
        z=lerp(rows[0][0],rows[-1][0],j/rings)
        rx,ry,cx,cy,rot=sample(rows,z)
        if p['kind']=='head':
            u=j/rings
            rx*=1+p.get('cheek_fullness',0)*math.exp(-((u-.36)/.18)**2)*.18
            rx*=1-p.get('chin_taper',0)*math.exp(-((u-.08)/.14)**2)*.3
        rx*=p.get('width_scale',1);ry*=p.get('depth_scale',1)
        for i in range(sides):
            a=i*math.tau/sides
            x=rx*math.cos(a);y=ry*math.sin(a)
            wave=p.get('hem_wave',0)*(math.sin(a*5+.4)+.4*math.sin(a*9))*(1-j/rings)**6
            asym=1+p.get('asymmetry',0)*.1*math.sin(a*3+z*8)
            verts.append((cx+(x*math.cos(rot)-y*math.sin(rot))*asym,cy+(x*math.sin(rot)+y*math.cos(rot))*asym,z+wave))
    for j in range(rings):
        for i in range(sides):
            a=j*sides+i;b=j*sides+(i+1)%sides;faces.append((a,b,b+sides,a+sides))
    if p['kind']=='head' or not p.get('open',False):
        faces += [tuple(range(sides-1,-1,-1)),tuple(rings*sides+i for i in range(sides))]
    return verts,faces

def path_samples(path,radii,steps=48):
    rows=[[i/(len(path)-1),*p,radii[i]] for i,p in enumerate(path)]
    return [sample(rows,i/steps) for i in range(steps+1)]

def part_seed(seed,name):
    import hashlib
    return seed+int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
