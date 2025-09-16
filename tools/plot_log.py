import json, sys
import matplotlib.pyplot as plt

xs, ax, ay, az = [], [], [], []
for line in sys.stdin:
    try:
        j = json.loads(line)
        if j.get("op") == "imu_raw":
            xs.append(j["ts"]); ax.append(j["ax"]); ay.append(j["ay"]); az.append(j["az"])
    except: pass

plt.plot(xs, ax, label="ax")
plt.plot(xs, ay, label="ay")
plt.plot(xs, az, label="az")
plt.legend()
plt.title("IMU acc (raw)")
plt.xlabel("time (s)")
plt.ylabel("counts")
plt.show()
