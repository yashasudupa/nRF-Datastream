# Protocol

All notifications are **binary**. First byte is **op code**.

- `0x10` IMU raw sample: 12 bytes payload (6 * int16 LE): ax, ay, az, gx, gy, gz.
- `0x20` Heartbeat: 1 byte payload (counter).

Host commands (Write to RX char):

- `0x01` Request one IMU sample (device responds with `0x10` packet).
