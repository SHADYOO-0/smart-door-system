Project Overview :
This document provides a comprehensive overview of the project. It is designed to be a complete guide for understanding the system's architecture, hardware, software, and logic flow, making it ideal for a college end-of-year project report or presentation.

1. High-Level Architecture
The SmartDoor project is a comprehensive Internet of Things (IoT) system designed to automate door access using facial recognition. The system is distributed across three main environments:

Hardware / Edge Devices: Microcontrollers situated at the physical door.
Central Controller (PC): A local computer acting as the "brain" for heavy processing (AI) and database management.
Web Dashboard: A user interface for remote monitoring and manual control.
These components communicate with each other in real-time using the MQTT (Message Queuing Telemetry Transport) protocol, which is lightweight and perfect for IoT devices.

2. Hardware Components (The "Eyes and Hands")
The physical door uses two separate microcontrollers to handle sensory input and physical actions.

A. NodeMCU / ESP8266 (Presence & Lock Control)
File: esp_code/ultrasonic_relay/ultrasonic_relay.ino
Ultrasonic Sensor (HC-SR04): Constantly measures the distance in front of the door. If a person stands within 80cm, the NodeMCU detects "presence" and immediately sends an MQTT message (door/face) to wake up the main system.
Relay Module: Connected to an electronic door strike or magnetic lock. When the NodeMCU receives an authorized MQTT message (door/open), it activates the relay for 5 seconds to physically unlock the door.
B. ESP32-CAM (Vision)
File: esp_code/cam/cam.ino
Camera Module: Dedicated entirely to taking photos. It sits idly until it receives an MQTT request (door/photo). Once requested, it captures a JPEG image and sends the raw image data byte-by-byte over MQTT (door/image_data) back to the main PC for analysis.
3. The Central PC Controller (The "Brain")
Because facial recognition requires significant processing power, the heavy lifting is offloaded to a local PC running Python scripts.

Main Logic Loop (smart_door_controller.py): This script constantly listens to the MQTT broker.
When it hears a "presence detected" signal from the NodeMCU, it asks the ESP32-CAM for a photo.
When it receives the photo data, it passes it to the AI module.
Facial Recognition (face_processing.py & dlib): The system uses OpenCV to read the image and the dlib machine learning library to map the face. It extracts a unique "descriptor" (a mathematical array) representing the person's facial features.
Database Management (db_operations.py & MySQL): The extracted face is compared against a MySQL database (smart_door).
Owners: If the face matches a registered "owner", the PC sends the "open door" signal (door/open) and sends an email notification.
Guests: If it matches a known "guest", the door remains locked, but the owners are notified. Intelligent Feature: If a guest visits more than 30 times, they are automatically promoted to an "owner" and the door opens for them!
Unknowns: If the face is completely new, they are automatically registered in the database as an "Unknown" guest, and the owner gets an email alert with their picture.
Email Service (email_service.py): Automatically dispatches security alerts and notifications (with the captured photo attached) to the registered owner's email address via SMTP.
4. The Web Application (The "Interface")
Files: web_app/app.py, templates/, static/
Framework: Built using Flask (Python) and styled with HTML/CSS.
Features:
Secure Login: Owners must log in to access the dashboard.
Live Monitoring: Displays the most recent photo taken by the door camera.
Manual Control: Provides buttons to manually "Take New Photo" or "Open Door", which send the respective MQTT commands to the hardware.
Visit Logs: Shows a history of who visited the door and when, reading directly from the MySQL database.
5. Step-by-Step Logic Flow (What happens when someone arrives?)
Arrival: A person walks up to the door. The Ultrasonic Sensor detects them at < 80cm.
Trigger: The NodeMCU publishes 1 to the door/face MQTT topic.
Photo Request: The PC Controller hears this and publishes 1 to the door/photo topic.
Capture: The ESP32-CAM hears the request, takes a picture, and publishes the image data to door/image_data.
Processing: The PC Controller downloads the image, finds the face, and computes its mathematical descriptor.
Lookup: The PC queries the MySQL database to find a matching descriptor.
Decision:
If Owner: PC publishes 1 to door/open. NodeMCU activates the relay. Door unlocks. Email sent.
If Guest/Unknown: Door stays locked. Visit is logged. Email sent with the photo.
6. Project Highlights for College Presentation
Decoupled Architecture: Using MQTT allows the camera, the sensor/lock, the PC, and the web app to operate independently without blocking each other.
Machine Learning Integration: Uses state-of-the-art AI (dlib ResNet) for highly accurate 128-point face encoding.
Automated Lifecycle: The system is self-sustaining (e.g., auto-registering unknowns, auto-promoting frequent guests).
Full Stack: Demonstrates knowledge of hardware (C++/Arduino), backend processing (Python/AI), database management (SQL), and frontend web development (Flask/HTML).
