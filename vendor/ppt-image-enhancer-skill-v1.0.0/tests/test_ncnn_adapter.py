from pathlib import Path
import sys, tempfile, os
import cv2, numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ppt_image_enhancer.pipeline import enhance
from ppt_image_enhancer.config import load_config, deep_merge

FAKE='''#!/usr/bin/env python3\nimport sys, cv2\na=sys.argv\ninput=a[a.index("-i")+1]; output=a[a.index("-o")+1]; scale=int(a[a.index("-s")+1])\nim=cv2.imread(input); out=cv2.resize(im,(im.shape[1]*scale,im.shape[0]*scale),interpolation=cv2.INTER_CUBIC); cv2.imwrite(output,out)\n'''

def main():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); src=td/'in.png'; dst=td/'out.png'; fake=td/'realesrgan-ncnn-vulkan'
        fake.write_text(FAKE,encoding='utf-8'); fake.chmod(0o755)
        img=np.full((200,320,3),255,np.uint8); cv2.putText(img,'TEST',(20,100),cv2.FONT_HERSHEY_SIMPLEX,1.5,(0,0,0),2); cv2.imwrite(str(src),img)
        cfg=load_config('scene_plus_text')
        cfg=deep_merge(cfg,{'output':{'upscale_factor':2.0,'max_width':1000,'max_height':1000},'super_resolution':{'backend':'realesrgan_ncnn','realesrgan_ncnn':{'executable':str(fake),'scale':2,'model_name':'realesrgan-x4plus','tile':0,'model_dir':''}}})
        r=enhance(src,dst,cfg)
        assert dst.exists(); assert r['super_resolution_backend']=='realesrgan_ncnn'; assert r['ai_super_resolution_used'] is True
        print('NCNN ADAPTER OK')
if __name__=='__main__': main()
