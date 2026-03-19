import argparse
import asyncio
import os
import socket
from datetime import datetime


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def write_log(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{ts()} {line}\n")


async def read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    data = await reader.readexactly(n)
    return data


async def relay(a_reader: asyncio.StreamReader, a_writer: asyncio.StreamWriter, b_reader: asyncio.StreamReader, b_writer: asyncio.StreamWriter) -> None:
    async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    await asyncio.gather(pipe(a_reader, b_writer), pipe(b_reader, a_writer))


async def handle_client(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter, upstream_host: str, upstream_port: int, upstream_user: str, upstream_pass: str, log_file: str) -> None:
    peer = client_writer.get_extra_info("peername")
    try:
        head = await read_exact(client_reader, 2)
        ver, nmethods = head[0], head[1]
        if ver != 5:
            client_writer.close()
            return
        _methods = await read_exact(client_reader, nmethods)
        client_writer.write(b"\x05\x00")
        await client_writer.drain()

        req_head = await read_exact(client_reader, 4)
        ver, cmd, _rsv, atyp = req_head
        if ver != 5 or cmd != 1:
            client_writer.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_writer.drain()
            client_writer.close()
            return

        if atyp == 1:
            addr_raw = await read_exact(client_reader, 4)
            target_host = socket.inet_ntoa(addr_raw)
            dst_addr_wire = addr_raw
            atyp_wire = b"\x01"
        elif atyp == 3:
            ln = (await read_exact(client_reader, 1))[0]
            host_raw = await read_exact(client_reader, ln)
            target_host = host_raw.decode("utf-8", errors="ignore")
            dst_addr_wire = bytes([ln]) + host_raw
            atyp_wire = b"\x03"
        elif atyp == 4:
            addr_raw = await read_exact(client_reader, 16)
            target_host = socket.inet_ntop(socket.AF_INET6, addr_raw)
            dst_addr_wire = addr_raw
            atyp_wire = b"\x04"
        else:
            client_writer.write(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_writer.drain()
            client_writer.close()
            return

        dst_port_raw = await read_exact(client_reader, 2)
        target_port = int.from_bytes(dst_port_raw, "big")

        up_reader, up_writer = await asyncio.open_connection(upstream_host, upstream_port)
        up_writer.write(b"\x05\x01\x02")
        await up_writer.drain()
        up_method = await read_exact(up_reader, 2)
        if up_method != b"\x05\x02":
            write_log(log_file, f"UP_NEGOTIATION_FAIL peer={peer} method={up_method.hex()}")
            client_writer.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_writer.drain()
            client_writer.close()
            up_writer.close()
            return

        ub = upstream_user.encode("utf-8")
        pb = upstream_pass.encode("utf-8")
        if len(ub) > 255 or len(pb) > 255:
            write_log(log_file, "UP_CRED_LENGTH_INVALID")
            client_writer.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_writer.drain()
            client_writer.close()
            up_writer.close()
            return

        up_writer.write(b"\x01" + bytes([len(ub)]) + ub + bytes([len(pb)]) + pb)
        await up_writer.drain()
        up_auth = await read_exact(up_reader, 2)
        if len(up_auth) < 2 or up_auth[1] != 0:
            write_log(log_file, f"UP_AUTH_FAIL peer={peer} code={up_auth.hex()}")
            client_writer.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_writer.drain()
            client_writer.close()
            up_writer.close()
            return

        up_req = b"\x05\x01\x00" + atyp_wire + dst_addr_wire + dst_port_raw
        up_writer.write(up_req)
        await up_writer.drain()

        up_resp_head = await read_exact(up_reader, 4)
        rep = up_resp_head[1]
        bnd_atyp = up_resp_head[3]
        if bnd_atyp == 1:
            _ = await read_exact(up_reader, 4)
        elif bnd_atyp == 3:
            ln = (await read_exact(up_reader, 1))[0]
            _ = await read_exact(up_reader, ln)
        elif bnd_atyp == 4:
            _ = await read_exact(up_reader, 16)
        _ = await read_exact(up_reader, 2)

        if rep != 0:
            write_log(log_file, f"UP_CONNECT_FAIL peer={peer} target={target_host}:{target_port} rep={rep}")
            client_writer.write(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_writer.drain()
            client_writer.close()
            up_writer.close()
            return

        client_writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await client_writer.drain()
        write_log(log_file, f"CONNECT_OK peer={peer} target={target_host}:{target_port}")
        await relay(client_reader, client_writer, up_reader, up_writer)
    except asyncio.IncompleteReadError:
        pass
    except Exception as e:
        write_log(log_file, f"HANDLE_ERROR peer={peer} err={type(e).__name__}:{e}")
    finally:
        try:
            client_writer.close()
        except Exception:
            pass


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=19080)
    parser.add_argument("--upstream-host", required=True)
    parser.add_argument("--upstream-port", type=int, required=True)
    parser.add_argument("--log-file", required=True)
    args = parser.parse_args()

    upstream_user = os.environ.get("BRIDGE_UP_USER", "")
    upstream_pass = os.environ.get("BRIDGE_UP_PASS", "")
    if not upstream_user or not upstream_pass:
        write_log(args.log_file, "START_FAIL_MISSING_UPSTREAM_CREDENTIALS")
        return 2

    write_log(args.log_file, f"START listen={args.listen_host}:{args.listen_port} upstream={args.upstream_host}:{args.upstream_port} user={upstream_user}")
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, args.upstream_host, args.upstream_port, upstream_user, upstream_pass, args.log_file),
        host=args.listen_host,
        port=args.listen_port,
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
