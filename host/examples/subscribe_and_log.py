from nrf_ble.client import connect_and_log

if __name__ == "__main__":
    connect_and_log(name="NRF-BLE-DEMO", save="out.jsonl", once=False)
