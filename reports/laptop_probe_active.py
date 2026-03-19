import concurrent.futures
import socket
from datetime import datetime
from pathlib import Path


SUBNET = "192.168.31."
PORT = 22
TIMEOUT = 0.2


def is_open(ip: str) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    try:
        s.connect((ip, PORT))
        return True
    except Exception:
        return False
    finally:
        s.close()


def main() -> int:
    ips = [f"{SUBNET}{i}" for i in range(1, 255)]
    open_ips: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=128) as ex:
        results = ex.map(is_open, ips)
        for ip, ok in zip(ips, results):
            if ok:
                open_ips.append(ip)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(r"C:\integrator\reports") / f"laptop_access_probe_active_{ts}.log"
    out.write_text(
        "\n".join(
            [
                "SUBNET=192.168.31.0/24",
                "METHOD=active_tcp_scan",
                "PORT=22",
                "SSH_OPEN=" + (",".join(open_ips) if open_ips else "NONE"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
