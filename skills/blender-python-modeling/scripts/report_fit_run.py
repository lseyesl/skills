#!/usr/bin/env python3
"""Create paired measurement tables and visual evidence from actual fitter outputs."""
from pathlib import Path
import argparse,json,cv2,numpy as np


def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--delivery',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 load=lambda f:json.loads(f.read_text())
 old=load(a.baseline/'evaluation/metrics.json');initial=load(a.run/'initial/evaluation/metrics.json');new=load(a.delivery/'evaluation/metrics.json');opt=load(a.run/'iterations/optimization.json')
 if old['input_hashes']!=new['input_hashes']:raise ValueError('Cannot compare different reference/annotation evidence')
 def tile(path):
  image=cv2.imread(str(path),-1)
  if image is None:raise FileNotFoundError(path)
  if image.shape[2]==4:
   alpha=image[:,:,3:4]/255;image=(image[:,:,:3]*alpha+240*(1-alpha)).astype('uint8')
  return cv2.resize(image,(512,536),interpolation=cv2.INTER_AREA)
 def board(name,items):
  sheet=np.full((576,512*len(items),3),240,np.uint8)
  for i,(label,path) in enumerate(items):
   sheet[40:,i*512:(i+1)*512]=tile(path);cv2.putText(sheet,label,(i*512+12,27),cv2.FONT_HERSHEY_SIMPLEX,.65,(40,40,40),1,cv2.LINE_AA)
  cv2.imwrite(str(out/name),sheet)
 board('model-comparison.png',[('REFERENCE',Path(new['reference'])),('ORIGINAL V5 / FIXED ENV',a.baseline/'beauty_front.png'),('PARAMETRIC + LOCAL FIT',a.delivery/'beauty_front.png')])
 board('iteration-comparison.png',[('PARAMETRIC INITIAL',a.run/'initial/beauty_front.png'),('AFTER 4 LOCAL UPDATES',a.delivery/'beauty_front.png'),('FINAL DIFFERENCE',a.delivery/'evaluation/difference_heatmap.png')])
 board('multiview.png',[(v.upper(),a.delivery/('beauty_'+v+'.png')) for v in ['front','side','back','three_quarter']])
 board('material-diagnostics.png',[('REFERENCE',Path(new['reference'])),('UNLIT BASE COLOR',a.delivery/'albedo_front.png'),('NEUTRAL CLAY',a.delivery/'clay_front.png'),('FIXED BEAUTY',a.delivery/'beauty_front.png')])
 metrics={'global':{'old':old['global'],'initial':initial['global'],'final':new['global']},'components':{},'landmarks':{'old':old['landmarks'],'initial':initial['landmarks'],'final':new['landmarks']},'accepted_iterations':opt['accepted_iterations'],'stop_reason':opt['stop_reason'],'scope':'2D visible evidence only; no overall model accuracy percent'}
 rows=[];colors=[]
 for key,value in new['components'].items():
  o=old['components'].get(key,{});i=initial['components'].get(key,{})
  metrics['components'][key]={'old':o,'initial':i,'final':value}
  number=lambda item:f"{item['iou']:.4f}" if 'iou'in item else 'N/A'
  delta=f"{value['iou']-o['iou']:+.4f}" if 'iou'in value and 'iou'in o else 'N/A'
  rows.append(f'| {key} | {number(o)} | {number(i)} | {number(value)} | {delta} |')
  if value.get('color'):
   colors.append(f"| {key} | {o.get('color',{}).get('delta_e76',float('nan')):.2f} | {value['color']['delta_e76']:.2f} |")
 (out/'comparison-metrics.json').write_text(json.dumps(metrics,indent=2))
 (out/'metrics-table.md').write_text('## 可见部位 IoU（同相机、同版标注）\n\n| 部位 | 旧 v5 | 参数化初版 | 自动修正后 | 相对旧版变化 |\n|---|---:|---:|---:|---:|\n'+'\n'.join(rows)+'\n\n## 无光照颜色诊断\n\n参考光照未知，以下 Lab ΔE76 仅描述观察颜色差异，不能当作固有材质质量评分。\n\n| 部位 | 旧版 ΔE76 | 新版 ΔE76 |\n|---|---:|---:|\n'+'\n'.join(colors)+'\n')
 print(json.dumps({'ok':True,'output':str(out),'global_iou':metrics['global'],'accepted_iterations':opt['accepted_iterations']}))

if __name__=='__main__':main()
