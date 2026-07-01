"""[LEGACY/DEV] LAN proxy for Monster AI — Call Guard v1.2+ uses Cloudflare Tunnel only."""
from __future__ import annotations

import http.server
import socket
import socketserver
import sys
import threading
import urllib.error
import urllib.request

UPSTREAM = "http://127.0.0.1:7860"
PORT = 7860
DISCOVER_PORT = 47890
DISCOVER_MAGIC = b"MONSTER_CALLGUARD_V1"


def discover_bind_addrs() -> list[str]:
    addrs: set[str] = set()
    try:
        import subprocess

        out = subprocess.check_output(["ipconfig"], text=True, errors="ignore")
        for line in out.splitlines():
            if "IPv4" in line and ":" in line:
                ip = line.split(":")[-1].strip()
                if ip.startswith(("192.168.", "10.")):
                    addrs.add(ip)
    except Exception:
        pass
    if not addrs:
        addrs.add("0.0.0.0")
    return sorted(addrs)


class BridgeHandler(http.server.BaseHTTPRequestHandler):
    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else None
        url = f"{UPSTREAM}{self.path}"
        req = urllib.request.Request(url, data=body, method=self.command)
        for key, value in self.headers.items():
            if key.lower() in {"host", "connection", "transfer-encoding"}:
                continue
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = resp.read()
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    if key.lower() in {"connection", "transfer-encoding"}:
                        continue
                    self.send_header(key, value)
                self.end_headers()
                if payload:
                    self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            for key, value in exc.headers.items():
                if key.lower() in {"connection", "transfer-encoding"}:
                    continue
                self.send_header(key, value)
            self.end_headers()
            if payload:
                self.wfile.write(payload)
        except Exception as exc:
            msg = f'{{"error":"bridge_failed","detail":"{exc}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self) -> None:
        self._proxy()

    def do_POST(self) -> None:
        self._proxy()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[lan-bridge] {self.address_string()} {fmt % args}\n")


class ReuseServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def serve_on(bind_addr: str) -> None:
    try:
        with ReuseServer((bind_addr, PORT), BridgeHandler) as httpd:
            print(f"MonsterCallGuard bridge on http://{bind_addr}:{PORT} -> {UPSTREAM}")
            httpd.serve_forever()
    except OSError as exc:
        print(f"Skip {bind_addr}:{PORT} ({exc})", file=sys.stderr)


def pick_lan_ip(addrs: list[str]) -> str:
    private = [a for a in addrs if a.startswith(("192.168.", "10."))]
    return private[0] if private else (addrs[0] if addrs else "127.0.0.1")


def udp_discovery_loop(advertise_ip: str) -> None:
    import json

    payload = json.dumps(
        {"service": "monster-callguard", "host": advertise_ip, "port": PORT},
    ).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", DISCOVER_PORT))
    except OSError as exc:
        print(f"UDP discovery disabled ({exc})", file=sys.stderr)
        return
    print(f"UDP discovery on :{DISCOVER_PORT} -> {advertise_ip}")
    while True:
        try:
            data, addr = sock.recvfrom(512)
            if data.strip() != DISCOVER_MAGIC:
                continue
            sock.sendto(payload, addr)
        except Exception:
            continue


def main() -> None:
    addrs = discover_bind_addrs()
    print(f"Binding: {', '.join(addrs)}")
    threading.Thread(
        target=udp_discovery_loop,
        args=(pick_lan_ip(addrs),),
        daemon=True,
    ).start()
    threads = []
    for addr in addrs:
        t = threading.Thread(target=serve_on, args=(addr,), daemon=True)
        t.start()
        threads.append(t)
    print("Press Ctrl+C to stop.")
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()