import cv2
import numpy as np
import dlib

detector = dlib.get_frontal_face_detector()

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    print(f"Frame shape: {frame.shape}, dtype: {frame.dtype}")
    
    # Try raw frame
    try:
        detector(frame)
        print("Raw frame worked")
    except Exception as e:
        print("Raw frame failed:", type(e).__name__, "-", str(e))

    # Try RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    print(f"RGB shape: {rgb.shape}, dtype: {rgb.dtype}, C_CONTIGUOUS: {rgb.flags['C_CONTIGUOUS']}")
    try:
        detector(rgb)
        print("RGB worked")
    except Exception as e:
        print("RGB failed:", type(e).__name__, "-", str(e))

    # Try Grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    print(f"Gray shape: {gray.shape}, dtype: {gray.dtype}, C_CONTIGUOUS: {gray.flags['C_CONTIGUOUS']}")
    try:
        detector(gray)
        print("Gray worked")
    except Exception as e:
        print("Gray failed:", type(e).__name__, "-", str(e))

cap.release()
