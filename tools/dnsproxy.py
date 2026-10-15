#!/usr/bin/env python3
"""dnsproxy.py — 给"自己解析域名"的程序用的本地 DNS 桥（只监听回环）。

背景
    安卓没有 /etc/resolv.conf：DNS 由系统服务经 getaddrinfo 提供，没有全局配置文件。
    musl / Go 这类自带解析器、只读 /etc/resolv.conf 的静态程序因此解析不了任何域名，
    报 "failed to lookup address information" 或 "error connecting to ..."，
    看起来像断网，其实是解析不到。

原理
    起一个只监听 127.0.0.1 的 HTTP 代理；域名由**本进程**解析（Python 的
    socket.getaddrinfo 走系统解析器，安卓上正常），目标程序只连字面 IP。
    支持 CONNECT（https/wss）与普通 http 转发。

用法
    python3 dnsproxy.py [端口]            # 默认 18080
    HTTPS_PROXY=http://127.0.0.1:18080 HTTP_PROXY=http://127.0.0.1:18080 <程序> ...

注意
    - 只绑 127.0.0.1，不接受外部连接。
    - 自己不缓存、不解密（CONNECT 只是转发字节），日志只记主机名与端口。
"""

import select
import socket
import sys
import threading

BUF = 65536
IDLE = 300          # 空闲多久断开（秒）
CONNECT_TIMEOUT = 20


def _resolve(host: str, port: int):
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return infos[0][4]


def _pump(a: socket.socket, b: socket.socket):
    """双向转发，任一方向 EOF 或空闲超时就结束。"""
    try:
        while True:
            readable, _, _ = select.select([a, b], [], [], IDLE)
            if not readable:
                return
            for src in readable:
                data = src.recv(BUF)
                if not data:
                    return
                (b if src is a else a).sendall(data)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.close()
            except OSError:
                pass


def _read_head(conn: socket.socket) -> bytes:
    """读到请求头结束（\\r\\n\\r\\n），上限 32 KiB。"""
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(BUF)
        if not chunk:
            return buf
        buf += chunk
        if len(buf) > 32768:
            raise ValueError("request head too large")
    return buf


def _handle(conn: socket.socket, addr):
    try:
        head = _read_head(conn)
        if not head:
            return
        line = head.split(b"\r\n", 1)[0].decode("latin-1")
        parts = line.split()
        if len(parts) < 2:
            return
        method, target = parts[0].upper(), parts[1]

        if method == "CONNECT":
            host, _, port_s = target.partition(":")
            port = int(port_s or 443)
            peer = socket.create_connection(_resolve(host, port), CONNECT_TIMEOUT)
            conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            print(f"[connect] {host}:{port}", flush=True)
            _pump(conn, peer)
            return

        # 普通 http：target 形如 http://host:port/path
        if target.startswith("http://"):
            rest = target[len("http://"):]
            hostport, _, path = rest.partition("/")
            host, _, port_s = hostport.partition(":")
            port = int(port_s or 80)
            peer = socket.create_connection(_resolve(host, port), CONNECT_TIMEOUT)
            newline = head.find(b"\r\n")
            rebuilt = b" ".join([method.encode(), b"/" + path.encode(), b"HTTP/1.1"]) + head[newline:]
            peer.sendall(rebuilt)
            print(f"[http]    {host}:{port}", flush=True)
            _pump(conn, peer)
            return

        conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
    except Exception as exc:                       # noqa: BLE001 —— 代理不该因单个连接退出
        print(f"[error]   {addr[0]}: {exc}", file=sys.stderr, flush=True)
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18080
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))                  # 只监听回环
    srv.listen(64)
    print(f"dnsproxy 监听 127.0.0.1:{port}（只解析 + 转发，不缓存不记录内容）", flush=True)
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=_handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
