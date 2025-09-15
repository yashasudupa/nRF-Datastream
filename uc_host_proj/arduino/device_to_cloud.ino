//ESP32 doesn’t have a built‑in GSM modem — but you can connect an external GSM module (via UART)
//ESP32 talks to these modules using AT commands over UART.
//This means:

//BLE + Wi‑Fi can still work.

//GSM modem handles data session (PPP) to send to the cloud.

//Cloud Options
//MQTT broker (e.g., HiveMQ, AWS IoT, Azure IoT).

//HTTP/REST API (simpler, just POST JSON).

#include <TinyGsmClient.h>
#include <PubSubClient.h>

#define TINY_GSM_MODEM_SIM800
#define GSM_APN "your_apn"
#define GSM_USER ""
#define GSM_PASS ""

// UART for GSM
HardwareSerial SerialGSM(1);
TinyGsm modem(SerialGSM);
TinyGsmClient gsmClient;
PubSubClient mqtt(gsmClient);

const char *broker = "broker.hivemq.com";
const char *topic = "bat/sensor/data";

// Initialize GSM
void initGSM() {
    SerialGSM.begin(9600, SERIAL_8N1, 16, 17); // RX, TX
    Serial.println("Initializing modem...");
    modem.restart();
    modem.gprsConnect(GSM_APN, GSM_USER, GSM_PASS);
    if (modem.isGprsConnected()) Serial.println("GPRS connected");
    mqtt.setServer(broker, 1883);
}

// Send data to MQTT
void sendToCloud(const char* payload) {
    if (!mqtt.connected()) {
        if (mqtt.connect("BatSensorClient")) {
            Serial.println("Connected to MQTT");
        }
    }
    mqtt.publish(topic, payload);
}
