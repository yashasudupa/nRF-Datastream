#include <Arduino.h>
#include <Wire.h>
#include "SparkFun_ICM-20948_ArduinoLibrary.h"
#include <Adafruit_ADS1X15.h>

// ==== Global objects ====
ICM_20948_I2C myICM;           // 9-DOF IMU
Adafruit_ADS1115 ads;          // For ADXL377

// ==== Sensor init functions ====
void initICM20948() {
    Wire.begin();
    if (myICM.begin(Wire, 0x68) != ICM_20948_Stat_Ok) {
        Serial.println("ICM-20948 init failed!");
        while (1);
    }
    Serial.println("ICM-20948 ready");
}

void initADXL377() {
    if (!ads.begin()) {
        Serial.println("ADS1115 init failed!");
        while (1);
    }
    Serial.println("ADS1115 ready (for ADXL377)");
}

// ==== Sensor read functions ====
void readIMU() {
    if (myICM.dataReady()) {
        myICM.getAGMT();
        float ax = myICM.accX();
        float ay = myICM.accY();
        float az = myICM.accZ();
        float gx = myICM.gyrX();
        float gy = myICM.gyrY();
        float gz = myICM.gyrZ();
        float mx = myICM.magX();
        float my = myICM.magY();
        float mz = myICM.magZ();
        // Store or process these values
    }
}

void readHighGAccel() {
    int16_t x = ads.readADC_SingleEnded(0);
    int16_t y = ads.readADC_SingleEnded(1);
    int16_t z = ads.readADC_SingleEnded(2);
    // Convert to G: G = ((raw * 3.3 / 32768) - bias) / sensitivity
    // Sensitivity ≈ 0.229 mV/g for ADXL377
}

// ==== Piezo read (placeholder) ====
void readPiezo() {
    // Implement ADC read for piezo sensors
}

// ==== Filtering & buffering ====
void filterSignals() {
    // Your RC/digital filtering
}
void bufferData() {
    // Store readings in a buffer
}

// ==== Madgwick, BLE, logging (placeholders) ====
void runMadgwick() { /* Sensor fusion */ }
void detectImpacts() { /* Impact detection */ }
void sendDataBLE() { /* BLE transmission */ }
void logDataToFlash() { /* Data logging */ }

// ==== FreeRTOS tasks ====
void taskSensorAcquisition(void *pvParameters) {
    initICM20948();
    initADXL377();
    for (;;) {
        readIMU();
        readHighGAccel();
        readPiezo();
        filterSignals();
        bufferData();
        vTaskDelay(5 / portTICK_PERIOD_MS);  // ~200Hz
    }
}

void taskFusionAndBLE(void *pvParameters) {
    for (;;) {
        runMadgwick();
        detectImpacts();
        sendDataBLE();
        logDataToFlash();
        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}

// ==== Arduino setup & loop ====
void setup() {
    Serial.begin(115200);
    xTaskCreatePinnedToCore(taskSensorAcquisition, "SensorTask", 10000, NULL, 2, NULL, 0);
    xTaskCreatePinnedToCore(taskFusionAndBLE, "FusionTask", 10000, NULL, 1, NULL, 1);
}
void loop() { /* Idle */ }
