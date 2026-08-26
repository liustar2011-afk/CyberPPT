from pathlib import Path
import sys, tempfile
import numpy as np, cv2

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ppt_image_enhancer.auto import build_auto_config
from ppt_image_enhancer.pipeline import enhance


def main():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); src=td/'page.png'; out=td/'page_enhanced.png'; report=td/'report.json'
        img=np.full((720,1280,3),255,np.uint8)
        cv2.rectangle(img,(80,120),(1200,620),(30,60,100),2)
        cv2.putText(img,'PPT IMAGE QUALITY TEST',(120,220),cv2.FONT_HERSHEY_SIMPLEX,1.3,(30,30,30),2,cv2.LINE_AA)
        for y in range(300,540,50): cv2.line(img,(150,y),(1050,y),(18,53,91),2,cv2.LINE_AA)
        cv2.imwrite(str(src),img)
        cfg,meta=build_auto_config(src,backend='builtin',scale=1.5)
        result=enhance(src,out,cfg,report)
        assert out.exists() and out.stat().st_size>0
        assert result['super_resolution_backend']=='builtin'
        assert result['after']['width']>=result['before']['width']
        print('SMOKE OK', meta['selected_mode'], result['after']['width'], result['after']['height'])
if __name__=='__main__': main()
