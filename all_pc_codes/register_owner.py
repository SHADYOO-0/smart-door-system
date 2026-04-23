import cv2
import numpy as np
import db_operations
import face_processing

def main():
    print("Starting webcam...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Press 'SPACE' to capture your face, or 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        cv2.imshow("Register Owner - Press SPACE to capture", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Operation cancelled.")
            break
        elif key == 32:  # SPACE bar
            print("Image captured. Processing...")
            # Save and reload to ensure a perfect 8-bit contiguous numpy array format for dlib
            cv2.imwrite("temp_webcam_face.jpg", frame)
            clean_frame = cv2.imread("temp_webcam_face.jpg")
            rgb_frame = cv2.cvtColor(clean_frame, cv2.COLOR_BGR2RGB)
            
            face_results = face_processing.get_face_descriptors_from_image(rgb_frame)
            
            if not face_results:
                print("No face detected in the image. Please try again.")
                continue
            
            if len(face_results) > 1:
                print("Multiple faces detected. Please ensure only your face is in the frame.")
                continue
            
            # We have exactly one face
            face_rect, descriptor = face_results[0]
            
            name = input("Face detected! Enter your name to register as owner: ")
            email = input("Enter your email address (optional, press Enter to skip): ")
            
            if not email.strip():
                email = None
            
            person_id = db_operations.add_person(
                name=name,
                face_descriptor=descriptor,
                status="owner",
                num_visits=0,
                email=email
            )
            
            if person_id:
                print(f"Successfully registered {name} as an owner with ID: {person_id}!")
            else:
                print("Failed to add person to the database.")
            
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
