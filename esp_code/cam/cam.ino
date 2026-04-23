#include <WiFi.h>
#include <PubSubClient.h>
#include "esp_camera.h"
#include "img_converters.h"
#include "base64.h"

const char* ssid = "DESKTOP-PI4QIBE 7718";///bch nbadlouh
const char* password = "V559g1{4"; ///bch nbadlouh
const char* mqtt_broker_host = "192.168.137.1";///bch nbadlouh
const int mqtt_broker_port = 1883;
const char* mqtt_client_id_esp32_cam = "esp32_cam_photo_service";

const char* mqtt_topic_request_photo = "door/photo";
const char* mqtt_topic_photo_data = "door/image_data";

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1 
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

const int STATUS_LED_PIN = 33;

WiFiClient espWiFiClientCam;
PubSubClient mqttClientCam(espWiFiClientCam);

const uint16_t MQTT_MESSAGE_BUFFER_SIZE = 40000;

bool init_camera() {
  camera_config_t config;

config.ledc_channel = LEDC_CHANNEL_0;

config.ledc_timer = LEDC_TIMER_0;

config.pin_d0 = Y2_GPIO_NUM;

config.pin_d1 = Y3_GPIO_NUM;

config.pin_d2 = Y4_GPIO_NUM;

config.pin_d3 = Y5_GPIO_NUM;

config.pin_d4 = Y6_GPIO_NUM;

config.pin_d5 = Y7_GPIO_NUM;

config.pin_d6 = Y8_GPIO_NUM;

config.pin_d7 = Y9_GPIO_NUM;

config.pin_xclk = XCLK_GPIO_NUM;

config.pin_pclk = PCLK_GPIO_NUM;

config.pin_vsync = VSYNC_GPIO_NUM;

config.pin_href = HREF_GPIO_NUM;

config.pin_sccb_sda = SIOD_GPIO_NUM;

config.pin_sccb_scl = SIOC_GPIO_NUM;

config.pin_pwdn = PWDN_GPIO_NUM;

config.pin_reset = RESET_GPIO_NUM;

//config.xclk_freq_hz = 20000000; high

config.xclk_freq_hz = 10000000; // Try reducing the clock frequency to reduce frame rate

config.pixel_format = PIXFORMAT_RGB565;

config.frame_size = FRAMESIZE_QQVGA; // Lower resolution to reduce lag

//config.frame_size = FRAMESIZE_QVGA; //this is lower than VGA but higher than QQVGA

//config.frame_size = FRAMESIZE_VGA; //higher frame rate //buffers a little

config.jpeg_quality = 10;

config.fb_count = 2;

config.grab_mode = CAMERA_GRAB_LATEST;

config.fb_location = CAMERA_FB_IN_PSRAM;
  

  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return false;
  }
  Serial.println("Camera initialized successfully.");
  return true;
}

void setup_wifi_cam() {
  delay(10);
  Serial.println();
  Serial.print("ESP32-CAM: Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int wifi_retries = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    wifi_retries++;
    if (wifi_retries > 20) {
      Serial.println("\nESP32-CAM: Failed to connect to WiFi. Rebooting...");
      ESP.restart();
    }
  }
  Serial.println("");
  Serial.println("ESP32-CAM: WiFi connected");
  Serial.print("ESP32-CAM IP address: ");
  Serial.println(WiFi.localIP());
}


void capture_and_send_photo() {
  Serial.println("Photo request received. Capturing image...");
  if (STATUS_LED_PIN >= 0) digitalWrite(STATUS_LED_PIN, HIGH);

  camera_fb_t * fb = NULL;
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed!");
    if (STATUS_LED_PIN >= 0) digitalWrite(STATUS_LED_PIN, LOW);
    return;
  }

  Serial.printf("Picture taken! Size: %u bytes, Format: %d\n", fb->len, fb->format);

  uint8_t * out_jpg = NULL;
  size_t out_jpg_len = 0;
  bool jpeg_converted = false;

  if (fb->format != PIXFORMAT_JPEG) {
    Serial.println("Image format is not JPEG. Converting to JPEG...");
    jpeg_converted = frame2jpg(fb, 50, &out_jpg, &out_jpg_len);
    if (!jpeg_converted) {
      Serial.println("JPEG conversion failed!");
      esp_camera_fb_return(fb);
      if (STATUS_LED_PIN >= 0) digitalWrite(STATUS_LED_PIN, LOW);
      return;
    }
  } else {
    out_jpg = fb->buf;
    out_jpg_len = fb->len;
  }

  Serial.print("Raw JPEG Image Length: ");
  Serial.println(out_jpg_len);

  bool published = false;
  if (mqttClientCam.beginPublish(mqtt_topic_photo_data, out_jpg_len, false)) {
    const uint8_t* payloadPtr = out_jpg;
    size_t remaining = out_jpg_len;
    size_t offset = 0;
    while (remaining > 0) {
      size_t chunkSize = (remaining > 1024) ? 1024 : remaining;
      mqttClientCam.write(payloadPtr + offset, chunkSize);
      offset += chunkSize;
      remaining -= chunkSize;
      delay(2); // Yield to prevent Watchdog Timeout (WDT) crash
    }
    published = mqttClientCam.endPublish();
  }
  
  if (jpeg_converted) free(out_jpg);
  esp_camera_fb_return(fb);
  
  if (published) {
    Serial.println("Photo data published successfully.");
  } else {
    Serial.println("Photo data PUBLISH FAILED. Check connection or buffer size.");
    Serial.print("MQTT Client State: "); Serial.println(mqttClientCam.state());
  }
  
  if (STATUS_LED_PIN >= 0) digitalWrite(STATUS_LED_PIN, LOW);
}

void mqtt_callback_cam(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived on CAM [");
  Serial.print(topic);
  Serial.print("] ");
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  if (String(topic) == mqtt_topic_request_photo) {
    if (message == "1") {
      capture_and_send_photo();
    }
  }
}

void reconnect_mqtt_cam() {
  while (!mqttClientCam.connected()) {
    Serial.print("ESP32-CAM: Attempting MQTT connection...");
    if (mqttClientCam.connect(mqtt_client_id_esp32_cam)) {
      Serial.println("connected");
      mqttClientCam.subscribe(mqtt_topic_request_photo);
      Serial.print("ESP32-CAM: Subscribed to: ");
      Serial.println(mqtt_topic_request_photo);
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClientCam.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println("\nESP32-CAM Photo Service Starting...");

  if(STATUS_LED_PIN >=0){
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);
  }

  if(!init_camera()){
    Serial.println("CRITICAL: Failed to initialize camera! Halting or Restarting.");
    delay(5000);
    ESP.restart();
    return;
  }

  setup_wifi_cam();
  mqttClientCam.setServer(mqtt_broker_host, mqtt_broker_port);
  mqttClientCam.setCallback(mqtt_callback_cam);
  
  if (!mqttClientCam.setBufferSize(MQTT_MESSAGE_BUFFER_SIZE)) {
    Serial.printf("Warning: Failed to set MQTT buffer size to %u via setBufferSize(). Check PubSubClient.h for MQTT_MAX_PACKET_SIZE.\n", MQTT_MESSAGE_BUFFER_SIZE);
  } else {
     Serial.printf("MQTT client buffer size set to %u.\n", MQTT_MESSAGE_BUFFER_SIZE);
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("ESP32-CAM: WiFi Disconnected. Attempting to reconnect...");
    setup_wifi_cam();
  }

  if (!mqttClientCam.connected()) {
    reconnect_mqtt_cam();
  }
  mqttClientCam.loop();
}