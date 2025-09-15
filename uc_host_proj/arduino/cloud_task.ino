void taskDeviceToCloud(void *pvParameters) {
    initGSM();
    for (;;) {
        char payload[128];
        snprintf(payload, sizeof(payload), "{\"ax\":%.2f,\"ay\":%.2f,\"impact\":%d}", 0.0, 0.0, 1);
        sendToCloud(payload);
        mqtt.loop();
        vTaskDelay(1000 / portTICK_PERIOD_MS); // 1Hz
    }
}

xTaskCreatePinnedToCore(taskDeviceToCloud, "CloudTask", 10000, NULL, 1, NULL, 1);
