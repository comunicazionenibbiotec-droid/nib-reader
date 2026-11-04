"""Isolated experimental API. Does not persist images or influence /analyze."""
import base64
import cv2
import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel
from detector_v2 import detect_cassette_v2
from regional_quality_v2 import characterize_region

router=APIRouter(prefix="/detector-v2",tags=["Detector V2 experimental"])
class DetectorV2Request(BaseModel): image:str

def decode_image(value):
    try:
        payload=value.split(",",1)[1] if "," in value else value
        arr=np.frombuffer(base64.b64decode(payload),np.uint8)
        return cv2.imdecode(arr,cv2.IMREAD_COLOR)
    except Exception:return None

def jpeg_data_url(image,quality=92):
    ok,buf=cv2.imencode(".jpg",image,[int(cv2.IMWRITE_JPEG_QUALITY),int(quality)])
    return "data:image/jpeg;base64,"+base64.b64encode(buf).decode("ascii") if ok else None

@router.get("/health")
def health():return {"status":"online","version":"2.0.1-experimental","persistence":False,"clinical":False}

@router.post("/analyze")
def analyze_v2(data:DetectorV2Request):
    image=decode_image(data.image)
    if image is None:return {"ok":False,"error":"image_decode_error"}
    result=detect_cassette_v2(image); canonical=result.pop("_canonical_image",None)
    if canonical is not None:
        for name,window in result.get("windows",{}).items():
            bbox=window.get("quality",{}).get("bbox")
            if bbox:window["regional_quality"]=characterize_region(canonical,bbox)
        result["canonical_preview"]=jpeg_data_url(canonical,90)
    return {"ok":True,"detector_v2":result,"persistence":False,"used_for_clinical_result":False}
