import json, threading

class JSONLinesWriter:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        open(self.path, "a").close()

    def append(self, obj: dict):
        line = json.dumps(obj, separators=(",", ":"))
        with self.lock:
            with open(self.path, "a", buffering=1) as f:
                f.write(line + "\n")
