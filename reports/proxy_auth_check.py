import socket
import struct
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> int:
    env_path = Path(r"C:\integrator\.env")
    if not env_path.exists():
        print("ENV=MISS")
        return 1
    env = load_env(env_path)
    host = env.get("PROXY_IP", "")
    port = int(env.get("PROXY_PORT", "0"))
    user = env.get("PROXY_USER", "")
    password = env.get("PROXY_PASS", "")
    if not (host and port and user and password):
        print("PROXY_CONFIG=MISSING")
        return 2
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(8)
    try:
        sock.connect((host, port))
        sock.sendall(b"\x05\x01\x02")
        if sock.recv(2) != b"\x05\x02":
            print("NEGOTIATION=FAIL")
            return 3
        ub = user.encode()
        pb = password.encode()
        sock.sendall(b"\x01" + bytes([len(ub)]) + ub + bytes([len(pb)]) + pb)
        auth = sock.recv(2)
        if len(auth) < 2 or auth[1] != 0:
            print("AUTH=FAIL")
            return 4
        domain = b"ifconfig.me"
        req = b"\x05\x01\x00\x03" + bytes([len(domain)]) + domain + struct.pack("!H", 80)
        sock.sendall(req)
        reply = sock.recv(4)
        if len(reply) < 4 or reply[1] != 0:
            print("CONNECT=FAIL")
            return 5
        atyp = reply[3]
        if atyp == 1:
            sock.recv(4)
        elif atyp == 3:
            sock.recv(sock.recv(1)[0])
        elif atyp == 4:
            sock.recv(16)
        sock.recv(2)
        sock.sendall(b"GET /ip HTTP/1.1\r\nHost: ifconfig.me\r\nConnection: close\r\n\r\n")
        data = b""
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
        text = data.decode(errors="ignore")
        body = text.split("\r\n\r\n", 1)[1].strip() if "\r\n\r\n" in text else ""
        ip = body.splitlines()[0].strip() if body else "UNKNOWN"
        print("AUTH=OK")
        print("CONNECT=OK")
        print(f"EGRESS_IP={ip}")
        return 0
    finally:
        sock.close()


if __name__ == "__main__":
    raise SystemExit(main())
