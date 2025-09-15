# ---------------- BLE device names ----------------
LEFT_NAME  = "Insole_Left"    # <-- put your actual left device name
RIGHT_NAME = "Insole_Right"   # <-- put your actual right device name

# ---------------- BLE UUIDs ----------------
SERVICE_UUID   = "12345678-1234-5678-1234-56789abcdef0"     # <-- replace
CMD_CHAR_UUID  = "12345678-1234-5678-1234-56789abcdef1"     # <-- replace
DATA_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef2"     # <-- replace

# ---------------- Smart Ball BLE ----------------
BALL_NAME      = "SmartBall"   # <-- replace with your actual advertised name
ADDRESS = "AAA91506-414F-7AC5-7B39-53AE12DAFDBC"
CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
BALL_CMD_CHAR = "19B10002-E8F2-537E-4F6C-D104768A1214"

# ---------------- Commands (bytes/strings as your FW expects) ----------------
CMD_START = b"start_r"
CMD_STOP  = b"stop_r"
CMD_PULL  = b"get_data10_bin"

# ---------------- Channel labeling & areas ----------------
# Order here must match the order your firmware sends channels
CHANNEL_LABELS = [
    "Toe R", "Ball R", "Heel R", "Heel L", "Mid", "Ball L", "Toe L", "Ball Mid"
]

# Contact area of each sensor (cm^2). Tune with your insole layout.
AREA_CM2 = {
    "Toe R":  3.0,
    "Ball R": 3.0,
    "Heel R": 3.5,
    "Heel L": 3.5,
    "Mid":    3.0,
    "Ball L": 3.0,
    "Toe L":  3.0,
    "Ball Mid": 3.0,
}

# ---------------- Timing ----------------
# device timestamp ticks per second (edit if device uses different units)
DEV_TS_UNITS_PER_S = 1000.0

# ---------------- Biomechanics thresholds & groupings ----------------
# If you know body weight in Newtons, set it; else leave None and compute a heuristic threshold
BODY_WEIGHT_N = None
FORCE_THRESHOLD_RATIO = 0.05  # 5% BW for HS/TO

# Sensor XY positions in meters (set for COP to be meaningful)
SENSOR_POS_M = {
    "Toe R":    (+0.07, +0.18),
    "Ball R":   (+0.04, +0.10),
    "Heel R":   (+0.02, -0.03),
    "Heel L":   (-0.02, -0.03),
    "Mid":      ( 0.00, +0.05),
    "Ball L":   (-0.04, +0.10),
    "Toe L":    (-0.07, +0.18),
    "Ball Mid": ( 0.00, +0.11),
}

HEEL_LABELS = {"Heel L", "Heel R"}
TOE_LABELS  = {"Toe L", "Toe R"}
MID_LABELS  = {"Mid"}
BALL_LABELS = {"Ball L", "Ball Mid", "Ball R"}