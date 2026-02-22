from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ServiceCheck:
    name: str
    url: str
    ok: bool
    status: int
    error: str


def _http_get(url: str, timeout_sec: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=float(timeout_sec)) as resp:
        return int(resp.status), resp.read()


def check_url_json(url: str, *, timeout_sec: float) -> ServiceCheck:
    try:
        status, body = _http_get(url, timeout_sec)
        ok = 200 <= int(status) < 300
        if not ok:
            return ServiceCheck(name="", url=url, ok=False, status=int(status), error="http_status")
        try:
            json.loads(body.decode("utf-8", errors="replace"))
        except Exception:
            return ServiceCheck(name="", url=url, ok=False, status=int(status), error="invalid_json")
        return ServiceCheck(name="", url=url, ok=True, status=int(status), error="")
    except urllib.error.HTTPError as e:
        return ServiceCheck(name="", url=url, ok=False, status=int(getattr(e, "code", 0) or 0), error="http_error")
    except Exception as e:
        return ServiceCheck(name="", url=url, ok=False, status=0, error=str(e))


def wait_ready(url: str, *, timeout_sec: float, attempts: int, sleep_sec: float) -> ServiceCheck:
    last = ServiceCheck(name="", url=url, ok=False, status=0, error="not_checked")
    for _ in range(max(1, int(attempts))):
        last = check_url_json(url, timeout_sec=float(timeout_sec))
        if last.ok:
            return last
        time.sleep(max(0.0, float(sleep_sec)))
    return last


def rag_health_url(base_url: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", "health")


def lm_models_url(base_url: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", "v1/models")


def default_lm_studio_base_url() -> str:
    return os.environ.get("LMSTUDIO_BASE_URL") or "http://127.0.0.1:1234"


def find_lm_studio_exe() -> Path | None:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA") or "") / "Programs" / "LM Studio" / "LM Studio.exe",
        Path(os.environ.get("PROGRAMFILES") or "") / "LM Studio" / "LM Studio.exe",
        Path(os.environ.get("PROGRAMFILES(X86)") or "") / "LM Studio" / "LM Studio.exe",
    ]
    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c
        except OSError:
            continue
    return None


def try_start_lm_studio() -> tuple[bool, str]:
    exe = find_lm_studio_exe()
    if exe is None:
        return False, "lm_studio_exe_missing"
    try:
        subprocess.Popen([str(exe)], cwd=str(exe.parent))
    except Exception as e:
        return False, str(e)
    return True, ""


def try_start_rag(python_cmd: str, cwd: Path, *, base_url: str) -> tuple[bool, str]:
    target = cwd / "rag_server.py"
    if not target.exists():
        return False, f"rag_server_missing: {target}"
    try:
        ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
        out_path = cwd / f"rag_server.out.{ts}"
        err_path = cwd / f"rag_server.err.{ts}"
        out_f = out_path.open("ab")
        err_f = err_path.open("ab")
        try:
            env = dict(os.environ)
            parsed = urllib.parse.urlparse(str(base_url or "").strip())
            if parsed.hostname:
                env["RAG_HOST"] = parsed.hostname
            if parsed.port:
                env["RAG_PORT"] = str(parsed.port)
            env["RAG_BASE_URL"] = str(base_url or "").strip()
            subprocess.Popen(
                [python_cmd, "rag_server.py"],
                cwd=str(cwd),
                stdout=out_f,
                stderr=err_f,
                env=env,
            )
        finally:
            out_f.close()
            err_f.close()
    except Exception as e:
        return False, str(e)
    return True, ""
