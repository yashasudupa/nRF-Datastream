from nrf_ble.parser import parse_packet, to_json

def test_parse_imu():
    data = bytes([0x10]) + (1).to_bytes(2,"little")*6
    pkt = parse_packet(data)
    j = to_json(pkt)
    assert j["op"] == "imu_raw"
    assert j["ax"] == 1 and j["gz"] == 1
