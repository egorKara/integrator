import socket
import subprocess
from datetime import datetime
from pathlib import Path
import re


def port_open(ip: str, port: int, timeout: float = 0.8) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def main() -> int:
    out = subprocess.check_output(["arp", "-a"], text=True, errors="ignore")
    ips = sorted(set(re.findall(r"192\\.168\\.31\\.\\d+", out)))
    open_22 = [ip for ip in ips if port_open(ip, 22)]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(r"C:\integrator\reports") / f"laptop_access_probe_{ts}.log"
    lines = [
        "SUBNET=192.168.31.0/24",
        "IPS_SEEN=" + (",".join(ips) if ips else "NONE"),
        "SSH_OPEN=" + (",".join(open_22) if open_22 else "NONE"),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
