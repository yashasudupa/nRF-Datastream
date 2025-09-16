from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Packet:
    op: int
    payload: bytes

def parse_packet(data: bytes) -> Optional[Packet]:
    if not data:
        return None
    op = data[0]
    return Packet(op=op, payload=data[1:])

def to_json(pkt: Packet) -> Dict[str, Any]:
    if pkt.op == 0x10 and len(pkt.payload) == 12:
        # ax, ay, az, gx, gy, gz (int16)
        import struct
        ax, ay, az, gx, gy, gz = struct.unpack("<6h", pkt.payload)
        return {"op": "imu_raw", "ax": ax, "ay": ay, "az": az, "gx": gx, "gy": gy, "gz": gz}
    elif pkt.op == 0x20 and len(pkt.payload) == 1:
        return {"op": "heartbeat", "count": pkt.payload[0]}
    else:
        return {"op": hex(pkt.op), "raw_len": len(pkt.payload)}
