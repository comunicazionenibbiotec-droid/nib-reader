"""Experimental ZenPSA cassette detector. No clinical decisions or persistence."""
from __future__ import annotations
import cv2
import numpy as np

CANONICAL_WIDTH = 1200
CANONICAL_HEIGHT = 2340
EXPECTED_ASPECT = 1.95
WINDOWS = {
    "A": {"x": .285, "y": .135, "w": .215, "h": .175, "shape": "circle", "analysis": True},
    "B": {"x": .545, "y": .120, "w": .205, "h": .205, "shape": "rounded_rect", "analysis": False},
    "C": {"x": .555, "y": .385, "w": .175, "h": .265, "shape": "rounded_rect", "analysis": True},
}

def _order_points(points):
    pts=np.asarray(points,dtype=np.float32).reshape(4,2)
    s=pts.sum(axis=1); d=np.diff(pts,axis=1).ravel()
    return np.array([pts[np.argmin(s)],pts[np.argmin(d)],pts[np.argmax(s)],pts[np.argmax(d)]],dtype=np.float32)

def _angle_deg(p1,p2):
    return float(np.degrees(np.arctan2(p2[1]-p1[1],p2[0]-p1[0])))

def _warp(image,corners):
    src=_order_points(corners)
    dst=np.array([[0,0],[CANONICAL_WIDTH-1,0],[CANONICAL_WIDTH-1,CANONICAL_HEIGHT-1],[0,CANONICAL_HEIGHT-1]],dtype=np.float32)
    matrix=cv2.getPerspectiveTransform(src,dst)
    return cv2.warpPerspective(image,matrix,(CANONICAL_WIDTH,CANONICAL_HEIGHT),flags=cv2.INTER_CUBIC),matrix

def _candidate_contours(image):
    h,w=image.shape[:2]; scale=min(1.0,1100/max(h,w)); small=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale<1 else image.copy()
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    blur=cv2.GaussianBlur(gray,(5,5),0)
    edges=cv2.Canny(blur,35,120)
    edges=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(9,9)),iterations=2)
    contours,_=cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    return contours,scale,edges

def _score_quad(quad,frame_shape):
    h,w=frame_shape[:2]; q=_order_points(quad)
    top=np.linalg.norm(q[1]-q[0]); bottom=np.linalg.norm(q[2]-q[3]); left=np.linalg.norm(q[3]-q[0]); right=np.linalg.norm(q[2]-q[1])
    width=max(1,(top+bottom)/2); height=max(1,(left+right)/2); aspect=height/width
    area=abs(cv2.contourArea(q)); area_ratio=area/(w*h)
    cx=float(q[:,0].mean()/w); cy=float(q[:,1].mean()/h); center_distance=((cx-.5)**2+(cy-.5)**2)**.5
    aspect_score=max(0,1-abs(aspect-EXPECTED_ASPECT)/EXPECTED_ASPECT)
    area_score=min(1,max(0,(area_ratio-.05)/.35)); center_score=max(0,1-center_distance/.5)
    opposite_score=max(0,1-(abs(top-bottom)/width+abs(left-right)/height)/2)
    score=.42*aspect_score+.25*area_score+.20*center_score+.13*opposite_score
    return score,{"aspect_ratio":aspect,"area_ratio":area_ratio,"center_x":cx,"center_y":cy,"opposite_sides_score":opposite_score}

def _find_best_quad(image):
    contours,scale,edges=_candidate_contours(image); candidates=[]
    min_area=edges.shape[0]*edges.shape[1]*.035
    for c in contours:
        area=cv2.contourArea(c)
        if area<min_area: continue
        peri=cv2.arcLength(c,True)
        approx=cv2.approxPolyDP(c,.022*peri,True)
        if len(approx)==4 and cv2.isContourConvex(approx): quad=approx.reshape(4,2).astype(np.float32)/scale
        else:
            rect=cv2.minAreaRect(c); quad=cv2.boxPoints(rect).astype(np.float32)/scale
        score,metrics=_score_quad(quad,image.shape); candidates.append((score,quad,metrics))
    candidates.sort(key=lambda x:x[0],reverse=True)
    return candidates[0] if candidates else None

def _regional_quality(image,region):
    h,w=image.shape[:2]; x0=max(0,int(region["x"]*w)); y0=max(0,int(region["y"]*h)); x1=min(w,int((region["x"]+region["w"])*w)); y1=min(h,int((region["y"]+region["h"])*h)); roi=image[y0:y1,x0:x1]
    if roi.size==0:return {"valid":False}
    gray=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY); focus=float(cv2.Laplacian(gray,cv2.CV_64F).var()); brightness=float(np.mean(gray))
    b,g,r=cv2.split(roi); glare=((r>=245)&(g>=235)&(b>=235)); near=((r>=235)&(g>=225)&(b>=225))
    return {"valid":True,"bbox":{"x":x0,"y":y0,"w":x1-x0,"h":y1-y0},"focus_laplacian":round(focus,3),"brightness":round(brightness,3),"glare_fraction":round(float(glare.mean()),5),"near_glare_fraction":round(float(near.mean()),5)}

def _window_geometry_score(canonical,region):
    q=_regional_quality(canonical,region)
    if not q.get("valid"):return 0.0,q
    b=q["bbox"]; roi=canonical[b["y"]:b["y"]+b["h"],b["x"]:b["x"]+b["w"]]
    gray=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY); edge=cv2.Canny(cv2.GaussianBlur(gray,(5,5),0),30,100)
    density=float(np.mean(edge>0)); score=min(1.0,density/.12)
    q["edge_density"]=round(density,5); q["geometry_score"]=round(score,3)
    return score,q

def detect_cassette_v2(image):
    if image is None or image.size==0:return {"detected":False,"reason":"empty_image","version":"2.0.0-experimental"}
    best=_find_best_quad(image)
    if best is None:return {"detected":False,"reason":"no_quadrilateral_candidate","version":"2.0.0-experimental","source":{"width":int(image.shape[1]),"height":int(image.shape[0])}}
    outer_score,corners,outer_metrics=best; canonical,matrix=_warp(image,corners)
    window_data={}; window_scores=[]
    for name,region in WINDOWS.items():
        score,quality=_window_geometry_score(canonical,region);window_scores.append(score);window_data[name]={"role":"analysis" if region["analysis"] else "alignment_only","expected":region,"quality":quality}
    internal=float(np.mean(window_scores)); geometry_score=.70*outer_score+.30*internal
    q=_order_points(corners); rotation=_angle_deg(q[0],q[1])
    top=float(np.linalg.norm(q[1]-q[0])); bottom=float(np.linalg.norm(q[2]-q[3])); left=float(np.linalg.norm(q[3]-q[0])); right=float(np.linalg.norm(q[2]-q[1]))
    source_w=(top+bottom)/2.0; source_h=(left+right)/2.0; source_aspect=source_h/max(source_w,1e-6)
    stretch_ratio=EXPECTED_ASPECT/max(source_aspect,1e-6)
    return {"detected":bool(geometry_score>=.35),"version":"2.0.1-experimental","used_for_clinical_result":False,"source":{"width":int(image.shape[1]),"height":int(image.shape[0])},"corners":[{"x":round(float(x),2),"y":round(float(y),2)} for x,y in q],"rotation_deg":round(rotation,3),"source_quad":{"width_px":round(source_w,2),"height_px":round(source_h,2),"aspect_ratio":round(source_aspect,5),"canonical_aspect_ratio":EXPECTED_ASPECT,"vertical_stretch_ratio":round(stretch_ratio,5)},"outer_geometry_score":round(float(outer_score),3),"internal_geometry_score":round(internal,3),"geometry_score":round(float(geometry_score),3),"metrics":{k:round(float(v),5) for k,v in outer_metrics.items()},"canonical":{"width":CANONICAL_WIDTH,"height":CANONICAL_HEIGHT},"windows":window_data,"perspective_matrix":np.round(matrix,6).tolist(),"_canonical_image":canonical}
