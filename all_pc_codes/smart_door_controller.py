import paho.mqtt.client as mqtt
import base64
import cv2
import numpy as np
import time
import datetime
import threading
import os
import config
import db_operations
import email_service
import face_processing

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="smart_door_controller_pi", protocol=mqtt.MQTTv311)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully to MQTT Broker.")
        client.subscribe(config.MQTT_TOPIC_DOOR_FACE_DETECTED)
        print(f"Subscribed to: {config.MQTT_TOPIC_DOOR_FACE_DETECTED}")
        client.subscribe(config.MQTT_TOPIC_PHOTO_DATA)
        print(f"Subscribed to: {config.MQTT_TOPIC_PHOTO_DATA}")
    else:
        print(f"Failed to connect to MQTT Broker, return code {rc}")

def send_mqtt_message(topic, payload):
    try:
        client.publish(topic, payload, qos=1)
        print(f"MQTT Published: Topic='{topic}', Payload='{payload}'")
    except Exception as e:
        print(f"MQTT Publish Error: {e}")

def on_message(client, userdata, msg):
    payload_str = str(msg.payload)[:50] if msg.topic != config.MQTT_TOPIC_PHOTO_DATA else "<binary jpeg data>"
    print(f"MQTT Message Received: Topic='{msg.topic}', Payload='{payload_str}...'")

    if msg.topic == config.MQTT_TOPIC_DOOR_FACE_DETECTED:
        print("Face detected at door (from ESP32). Requesting photo from ESP32-CAM...")
        send_mqtt_message(config.MQTT_TOPIC_REQUEST_PHOTO, "1")

    elif msg.topic == config.MQTT_TOPIC_PHOTO_DATA:
        print("Photo data received from ESP32-CAM. Processing...")
        
        if not msg.payload:
            print("Ignored empty photo payload (likely an old retained MQTT message).")
            return
            
        owner_emails = db_operations.get_owner_emails()

        try:
            nparr = np.frombuffer(msg.payload, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                print("Failed to decode image from ESP32-CAM.")
                return

            try:
                base_dir = os.path.dirname(os.path.abspath(__file__)) 
                web_image_path = os.path.join(base_dir, config.WEB_APP_LAST_IMAGE_PATH) 
                os.makedirs(os.path.dirname(web_image_path), exist_ok=True) 
                
                cv2.imwrite(web_image_path, frame) 
                print(f"Saved latest image for web app at {web_image_path}") 
            except Exception as e_save: 
                print(f"Error saving image for web app: {e_save}")
                

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = face_processing.get_face_descriptors_from_image(rgb_frame)

            if not face_results:
                print("No faces found in the captured image.")
                email_subject = "Smart Door: Motion Detected (No Face)"
                email_body = "Motion was detected at the door, but no clear face was captured in the image."
                email_service.send_notification_email(email_subject, email_body, owner_emails, frame)
                return

            _face_rect, descriptor = face_results[0] 
            person_id, name, status, num_visits = db_operations.find_person_by_descriptor(descriptor)

            if person_id:
                print(f"Known person detected: ID={person_id}, Name='{name}', Status='{status}', Visits={num_visits}")
                db_operations.log_visit(person_id)

                if status == 'owner':
                    print("Owner detected. Opening door...")
                    send_mqtt_message(config.MQTT_TOPIC_DOOR_OPEN_COMMAND, "1")
                    email_subject = f"Smart Door: Owner ({name}) Access Granted"
                    email_body = f"Owner '{name}' accessed the door at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
                    email_service.send_notification_email(email_subject, email_body, owner_emails, frame)

                else:
                    num_visits += 1
                    if num_visits >= config.VISIT_PROMOTION_THRESHOLD:
                        print(f"Guest '{name}' reached {num_visits} visits. Promoting to owner.")
                        db_operations.update_person_visits_and_status(person_id, 0, 'owner')
                        
                        email_subject = f"Smart Door: Guest '{name}' Promoted to Owner"
                        email_body = (f"Guest '{name}' has been automatically promoted to 'owner' status after {num_visits} visits.\n"
                                      f"The door has been opened for them.\n"
                                      f"'{name}' can now set their email via the mobile app for future notifications directly to them.")
                        email_service.send_notification_email(email_subject, email_body, owner_emails, frame)
                        send_mqtt_message(config.MQTT_TOPIC_DOOR_OPEN_COMMAND, "1")
                    else:
                        db_operations.update_person_visits_and_status(person_id, num_visits)
                        print(f"Guest '{name}' detected. Notifying owners. Visit count: {num_visits}")
                        email_subject = f"Smart Door: Known Guest '{name}' at Door"
                        email_body = (f"Known guest '{name}' is at the door.\n"
                                      f"Total visits this period: {num_visits}.\n"
                                      f"Owners can open door via mobile app if desired.")
                        email_service.send_notification_email(email_subject, email_body, owner_emails, frame)
            
            else:
                print("Unknown person detected. Adding to database and notifying owner(s).")
                unknown_person_name = f"Unknown_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                new_person_id = db_operations.add_person(
                    name=unknown_person_name,
                    face_descriptor=descriptor,
                    status="guest",
                    num_visits=1,
                    email=None
                )
                if new_person_id:
                    db_operations.log_visit(new_person_id)
                    email_subject = "Smart Door: Unknown Person Detected"
                    email_body = (f"An unknown person (now registered as '{unknown_person_name}') "
                                  f"was detected at the door at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                                  f"Their face has been added to the database. "
                                  f"Owners can open door via mobile app and update details if recognized.")
                    email_service.send_notification_email(email_subject, email_body, owner_emails, frame)
                else:
                    print("Failed to add unknown person to the database.")
                    email_subject = "Smart Door: Unknown Person (DB Error)"
                    email_body = "An unknown person was detected, but there was an error adding them to the database."
                    email_service.send_notification_email(email_subject, email_body, owner_emails, frame)

        except cv2.error as e:
            print(f"OpenCV error processing image: {e}")
        except Exception as e:
            print(f"Error processing photo data: {e}")

def monthly_visit_reset_scheduler():
    """ Periodically checks if it's a new month to reset guest visit counts. """
    global last_reset_month
    while True:
        time.sleep(3600 * 6)
        current_month = datetime.datetime.now().month
        if current_month != last_reset_month:
            print(f"New month detected ({current_month}). Performing monthly reset of guest visits...")
            db_operations.reset_monthly_guest_visits()
            last_reset_month = current_month
            print("Monthly guest visit reset complete.")

def main():
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"Attempting to connect to MQTT broker at {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT}")
        client.connect(config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT, 60)
    except Exception as e:
        print(f"Could not connect to MQTT Broker: {e}")
        return 

    reset_thread = threading.Thread(target=monthly_visit_reset_scheduler, daemon=True)
    reset_thread.start()
    print("Monthly visit reset scheduler started.")

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Disconnecting from MQTT broker...")
    finally:
        client.disconnect()
        print("Disconnected.")

if __name__ == "__main__":
    time.sleep(1) 
    main()
