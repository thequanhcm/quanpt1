#!/usr/bin/env python3
"""Probe Chromium kiosk qua CDP — chạy TRÊN PI (không ssh heredoc lồng)."""
import socket, base64, json, struct, os, time, sys, urllib.request

class WSClient:
    def __init__(self, host, port, path):
        self.sock = socket.create_connection((host, port), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.send(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.sock.recv(4096)
        self.buf = b""

    def _read_exact(self, n):
        while len(self.buf) < n:
            c = self.sock.recv(n - len(self.buf))
            if not c:
                raise RuntimeError("closed")
            self.buf += c
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, data):
        payload = data.encode()
        mask = os.urandom(4)
        header = b"\x81"
        ln = len(payload)
        if ln < 126:
            header += bytes([0x80 | ln])
        elif ln < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", ln)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", ln)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.send(header + mask + masked)

    def recv_message(self):
        header = self._read_exact(2)
        ln = header[1] & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", self._read_exact(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", self._read_exact(8))[0]
        return self._read_exact(ln)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass

def main():
    with urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=5) as r:
        targets = json.loads(r.read())
    page = next((t for t in targets if t["type"] == "page"), None)
    if not page:
        print("NO PAGE TARGET")
        return
    ws_path = page["webSocketDebuggerUrl"].split("9222")[1]
    ws = WSClient("127.0.0.1", 9222, ws_path)

    ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
    ws.send(json.dumps({"id": 2, "method": "Log.enable"}))
    time.sleep(0.5)
    ws.send(json.dumps({"id": 3, "method": "Runtime.evaluate", "params": {
        "expression": ("JSON.stringify({url: location.href, readyState: document.readyState, "
                       "engineType: typeof DigitalHumanAvatar, hasInstance: !!window.digitalHuman, "
                       "loaded: window.digitalHuman ? window.digitalHuman.loaded : null, "
                       "assetCount: window.digitalHuman ? Object.keys(window.digitalHuman.assets||{}).length : -1, "
                       "canvasExists: !!document.getElementById('kiosk-avatar-canvas'), "
                       "bodyClass: document.body.className, "
                       "canvasW: (c=document.getElementById('kiosk-avatar-canvas')) ? c.width : -1})"),
        "returnByValue": True,
    }}))

    console_msgs = []
    start = time.time()
    got_state = False
    while time.time() - start < 10:
        try:
            ws.sock.settimeout(1.0)
            raw = ws.recv_message()
            msg = json.loads(raw.decode())
            if msg.get("id") == 3:
                print("=== AVATAR STATE ===")
                print(msg.get("result", {}).get("result", {}).get("value"))
                got_state = True
                break
            method = msg.get("method", "")
            if method == "Runtime.consoleAPICalled":
                args = msg.get("params", {}).get("args", [])
                text = " ".join(str(a.get("value", a.get("description", "?"))) for a in args)
                console_msgs.append((msg["params"].get("type", "?"), text[:250]))
            elif method == "Runtime.exceptionThrown":
                exc = msg.get("params", {}).get("exceptionDetails", {})
                console_msgs.append(("EXCEPTION", str(exc)[:250]))
            elif method == "Log.entryAdded":
                entry = msg.get("params", {}).get("entry", {})
                console_msgs.append((entry.get("level", "?"), f"[{entry.get('source','?')}] {entry.get('text','')[:250]}"))
        except socket.timeout:
            continue
        except Exception as e:
            print("ERR:", e)
            break

    if not got_state:
        print("(no eval response in 10s)")
    print(f"\n=== CONSOLE ({len(console_msgs)}) ===")
    for tag, text in console_msgs[:25]:
        print(f"[{tag}] {text}")
    ws.close()

if __name__ == "__main__":
    main()
