import dlib
import numpy as np
import cv2
import config

try:
    detector = dlib.get_frontal_face_detector()
    sp = dlib.shape_predictor("shape_predictor_5_face_landmarks.dat") #how it was : sp = dlib.shape_predictor(config."shape_predictor_5_face_landmarks.dat")
    facerec = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat") #how it was : facerec = dlib.face_recognition_model_v1(config."dlib_face_recognition_resnet_model_v1.dat")
    print("Dlib models loaded successfully.")
except Exception as e:
    print(f"Error loading Dlib models: {e}. Ensure model files are in the correct path.")
    exit()

def get_face_descriptors_from_image(image_rgb):
    if image_rgb is None:
        print("Cannot process None image.")
        return []
        
    faces = detector(image_rgb)
    descriptors = []
    if not faces:
        print("No faces detected in the image.")
        return []

    for face_rect in faces:
        shape = sp(image_rgb, face_rect)
        descriptor = facerec.compute_face_descriptor(image_rgb, shape)
        descriptors.append((face_rect, np.array(descriptor)))
    
    print(f"Detected {len(descriptors)} face(s).")
    return descriptors