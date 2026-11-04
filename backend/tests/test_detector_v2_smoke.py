import cv2
import numpy as np
from detector_v2 import detect_cassette_v2

def synthetic():
    im=np.zeros((1600,1200,3),np.uint8);pts=np.array([[340,130],[850,160],[820,1480],[300,1450]],np.int32);cv2.fillConvexPoly(im,pts,(235,235,235));cv2.circle(im,(475,430),80,(40,40,40),-1);cv2.rectangle(im,(640,300),(760,570),(40,40,40),-1);cv2.rectangle(im,(625,760),(760,1110),(40,40,40),-1);return im
if __name__=='__main__':
    result=detect_cassette_v2(synthetic());assert ('geometry_score' in result) or (result.get('detected') is False);print(result.get('detected'),result.get('geometry_score'),result.get('reason'))
