#include <ESP8266WiFi.h>
#include <PubSubClient.h>

const char* ssid = "DESKTOP-PI4QIBE 7718";///bch nbadlouh
const char* password = "V559g1{4"; ///bch nbadlouh
const char* mqtt_broker_host = "192.168.137.1";///bch nbadlouh 
const int mqtt_broker_port = 1883;
const char* mqtt_client_id_nodemcu = "nodemcu_door_sensor";

const char* mqtt_topic_door_face_detected = "door/face";
const char* mqtt_topic_door_open_command = "door/open";

#define ULTRASONIC_TRIG_PIN D5
#define ULTRASONIC_ECHO_PIN D6
#define RELAY_PIN           D7
#define LED_PIN             LED_BUILTIN

const int LED_ON_STATE = LOW;
const int LED_OFF_STATE = HIGH;

const int DETECTION_DISTANCE_CM = 80;
const unsigned long ULTRASONIC_COOLDOWN_MS = 7000;
unsigned long lastUltrasonicTriggerTime = 0;

const int RELAY_ON_STATE = LOW;
const int RELAY_OFF_STATE = HIGH;
const unsigned long LOCK_OPEN_DURATION_MS = 5000;

WiFiClient espWiFiClient;
PubSubClient mqttClient(espWiFiClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int wifi_retries = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    wifi_retries++;
    if (wifi_retries > 20) {
      Serial.println("\nFailed to connect to WiFi. Rebooting...");
      ESP.restart();
    }
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

long measure_distance_cm() {
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

  long duration = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, 25000);
  if (duration == 0) {
      return 9999;
  }

  long distance = duration * 0.0343 / 2;
  return distance;
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  if (String(topic) == mqtt_topic_door_open_command) {
    if (message == "1") {
      Serial.println("Received door open command. Activating relay...");
      digitalWrite(LED_PIN, LED_ON_STATE);
      
      digitalWrite(RELAY_PIN, RELAY_ON_STATE);
      Serial.println("Lock Opened (Relay Activated)");
      
      delay(LOCK_OPEN_DURATION_MS);
      
      digitalWrite(RELAY_PIN, RELAY_OFF_STATE);
      Serial.println("Lock Closed (Relay Deactivated)");
      
      digitalWrite(LED_PIN, LED_OFF_STATE);
    }
  }
}

void reconnect_mqtt() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect(mqtt_client_id_nodemcu)) {
      Serial.println("connected");
      mqttClient.subscribe(mqtt_topic_door_open_command);
      Serial.print("Subscribed to: ");
      Serial.println(mqtt_topic_door_open_command);
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LED_OFF_STATE);

  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, RELAY_OFF_STATE);
  Serial.println("Relay initialized and set to OFF.");

  setup_wifi();
  mqttClient.setServer(mqtt_broker_host, mqtt_broker_port);
  mqttClient.setCallback(mqtt_callback);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi Disconnected. Attempting to reconnect...");
    Serial.println("WiFi connection lost. Attempting to re-establish...");
    WiFi.begin(ssid, password);
    unsigned long wifiAttemptTime = millis();
    while(WiFi.status() != WL_CONNECTED && millis() - wifiAttemptTime < 10000) {
        delay(500);
        Serial.print("*");
    }
    if(WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi reconnection failed. Will rely on MQTT reconnect or eventual reboot.");
    } else {
        Serial.println("WiFi reconnected.");
    }
  }
  
  if (!mqttClient.connected()) {
    reconnect_mqtt();
  }
  mqttClient.loop();

  long distance = measure_distance_cm();

  if (distance >= 0 && distance < 9999 && distance < DETECTION_DISTANCE_CM) {
    if (millis() - lastUltrasonicTriggerTime > ULTRASONIC_COOLDOWN_MS) {
      Serial.print("Close presence detected at ");
      Serial.print(distance);
      Serial.println(" cm. Publishing to MQTT...");
      digitalWrite(LED_PIN, LED_ON_STATE);
      
      bool published = mqttClient.publish(mqtt_topic_door_face_detected, "1");
      if(published) {
        Serial.print("Published to: "); Serial.println(mqtt_topic_door_face_detected);
      } else {
        Serial.println("Publish FAILED!");
      }
      
      lastUltrasonicTriggerTime = millis();
      delay(100);
      digitalWrite(LED_PIN, LED_OFF_STATE);
    }
  }
  delay(250);
}