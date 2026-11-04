"""Regional quality metrics for experimental Detector V2 canonical images."""
import cv2
import numpy as np

def characterize_region(image,bbox):
    x,y,w,h=(int(bbox[k]) for k in ("x","y","w","h")); roi=image[max(0,y):max(0,y)+max(0,h),max(0,x):max(0,x)+max(0,w)]
    if roi.size==0:return {"valid":False}
    gray=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY); b,g,r=cv2.split(roi)
    glare=(r>=245)&(g>=235)&(b>=235); valid=~glare
    return {"valid":True,"focus_laplacian":round(float(cv2.Laplacian(gray,cv2.CV_64F).var()),3),"brightness_mean":round(float(gray.mean()),3),"brightness_p05":round(float(np.percentile(gray,5)),3),"brightness_p50":round(float(np.percentile(gray,50)),3),"brightness_p95":round(float(np.percentile(gray,95)),3),"glare_fraction":round(float(glare.mean()),5),"valid_pixel_fraction":round(float(valid.mean()),5)}
