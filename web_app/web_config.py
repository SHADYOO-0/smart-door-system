import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
rpi_code_path = os.path.join(project_root, "all_pc_codes")
sys.path.append(rpi_code_path)

import config as main_config

MQTT_BROKER_HOST = main_config.MQTT_BROKER_HOST
MQTT_BROKER_PORT = main_config.MQTT_BROKER_PORT
MQTT_TOPIC_DOOR_OPEN_COMMAND = main_config.MQTT_TOPIC_DOOR_OPEN_COMMAND
MQTT_TOPIC_REQUEST_PHOTO = main_config.MQTT_TOPIC_REQUEST_PHOTO

DB_HOST = main_config.DB_HOST
DB_USER = main_config.DB_USER
DB_PASSWORD = main_config.DB_PASSWORD
DB_NAME = main_config.DB_NAME

SECRET_KEY = os.urandom(24)
MQTT_CLIENT_ID_WEB = "smart_door_webapp_client"
LATEST_IMAGE_URL = "/static/latest_cam_image.jpg"