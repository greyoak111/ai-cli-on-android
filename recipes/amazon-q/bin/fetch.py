#!/usr/bin/env python3
"""fetch.py — 按钉死的 URL + SHA256 取件并落地（纯 Python，无外部命令）。

    fetch.py <spec.json> <dest-root>

spec 形如：

    {"items": [
      {"url": "https://…/vibe.zip", "sha256": "…",
       "extract": {"kind": "zip", "member": "vibe", "to": "vibe"}, "mode": "755"},

      {"url": "https://…/libstdc++6_….deb", "sha256": "…",
       "extract": {"kind": "deb", "member": "usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.33",
                   "to": "libs/libstdc++.so.6"}},

      {"url": "https://…/q-aarch64-linux.zip", "sha256": "…",
       "extract": {"kind": "zip", "prefix": "q/bin/", "to": "q/"},

      {"url": "https://…/plain-binary", "sha256": "…", "to": "bin/tool", "mode": "755"}
    ]}

- `extract.kind`：`zip` / `tar`（含 .tar.gz/.xz/.zst）/ `deb`（ar 归档，抽 data.tar.* 里的成员）
- `member`：精确成员名（不含前导 `./`）；`prefix`：按前缀整目录抽出（保留相对路径）
- `to`：相对 dest-root 的目标文件/目录
- **sha256 必须写全**（64 位小写十六进制）；对不上就失败退出，不落地、不动已有文件
- 已存在目标就跳过（幂等）

为什么要有它：安卓上没有 /etc/ld.so.conf、也没有发行版的多架构库目录，
而各家 CLI 的官方构件又散在 npm / GitHub Releases / 厂商 CDN 上 ——
用它把「取件 + 校验 + 解包」收敛成一件可复查的事。
"""

import gzip
import hashlib
import io
import json
import lzma
import os
import sys
import tarfile
import urllib.request
import zipfile

try:                                        # Python 3.14 起在标准库里
    from compression import zstd as _zstd
except ImportError:
    _zstd = None

ALLOWED_SCHEMES = ("https://", "file://")   # 明文 http 一律拒绝（file:// 只为本地测试）


def _download(url: str) -> bytes:
    if not url.startswith(ALLOWED_SCHEMES):
        raise ValueError(f"只接受 https（或本地测试的 file://）：{url}")
    with urllib.request.urlopen(url, timeout=180) as resp:   # noqa: S310 —— 上面已限 scheme
        return resp.read()


def _decompress(data: bytes) -> bytes:
    if data[:6] == b"\xfd7zXZ\x00":
        return lzma.decompress(data)
    if data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    if data[:4] == b"\x28\xb5\x2f\xfd":
        if _zstd is not None:
            return _zstd.decompress(data)
        import subprocess
        return subprocess.run(["zstd", "-d", "-q", "-c"], input=data,
                              capture_output=True, check=True).stdout
    return data


def _ar_members(blob: bytes):
    """极简 ar 解析：.deb 就是 ar 归档（!<arch>\\n + 60 字节头 + 数据）。"""
    if not blob.startswith(b"!<arch>\n"):
        raise ValueError("不是 ar 归档（.deb 应以此开头）")
    off, end = 8, len(blob)
    while off + 60 <= end:
        header = blob[off:off + 60]
        name = header[0:16].decode("ascii", "replace").strip().rstrip("/")
        size = int(header[48:58].decode("ascii").strip() or "0")
        start = off + 60
        yield name, blob[start:start + size]
        off = start + size + (size & 1)          # 偶数对齐


def _tar_bytes_from_deb(deb: bytes) -> bytes:
    for name, data in _ar_members(deb):
        if name.startswith("data.tar"):
            return _decompress(data)
    raise ValueError("这个 .deb 里没有 data.tar.*")


def _normalize(path: str) -> str:
    return path.lstrip("./").rstrip("/")


def _extract_tar(tar_bytes: bytes, member: str | None, prefix: str | None):
    """返回 [(相对路径, 内容)]。"""
    out = []
    want = _normalize(member) if member else None
    pre = _normalize(prefix) if prefix else None
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tf:
        for entry in tf:
            if not entry.isfile():
                continue
            name = _normalize(entry.name)
            if want and name != want:
                continue
            if pre and not name.startswith(pre + "/"):
                continue
            rel = name[len(pre) + 1:] if pre else name
            fh = tf.extractfile(entry)
            if fh is not None:
                out.append((rel, fh.read()))
    if not out:
        raise ValueError(f"tar 里找不到成员：member={member} prefix={prefix}")
    return out


def _extract_zip(blob: bytes, member: str | None, prefix: str | None):
    out = []
    want = _normalize(member) if member else None
    pre = _normalize(prefix) if prefix else None
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = _normalize(info.filename)
            if want and name != want:
                continue
            if pre and not name.startswith(pre + "/"):
                continue
            rel = name[len(pre) + 1:] if pre else name
            out.append((rel, zf.read(info)))
    if not out:
        raise ValueError(f"zip 里找不到成员：member={member} prefix={prefix}")
    return out


def _write(dest_root: str, rel: str, data: bytes, mode: int):
    target = os.path.join(dest_root, rel)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.chmod(tmp, mode)
    os.replace(tmp, target)                 # 原子改名：中断不留半个文件


def _target_exists(dest_root: str, item: dict) -> bool:
    spec = item.get("extract")
    if spec and spec.get("kind") == "zip" and spec.get("prefix"):
        return os.path.isdir(os.path.join(dest_root, _normalize(item["to"])))
    return os.path.exists(os.path.join(dest_root, _normalize(item["to"])))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: fetch.py <spec.json> <dest-root>", file=sys.stderr)
        return 2
    spec_path, dest_root = sys.argv[1], sys.argv[2]

    with open(spec_path, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    for item in spec["items"]:
        label = os.path.basename(item["url"])

        if _target_exists(dest_root, item):
            print(f"[skip]    {label} → {item['to']}（已存在）", flush=True)
            continue

        print(f"[fetch]   {label}", flush=True)
        blob = _download(item["url"])

        digest = hashlib.sha256(blob).hexdigest()
        if digest != item["sha256"]:
            print(f"[FAIL]    sha256 不匹配：\n  期望 {item['sha256']}\n  实际 {digest}",
                  file=sys.stderr, flush=True)
            return 1

        mode = int(item.get("mode", "644"), 8)
        spec_ex = item.get("extract")

        if not spec_ex:                                   # 整个下载物就是一个文件
            _write(dest_root, item["to"], blob, mode)
            print(f"[ok]      {item['to']}（{len(blob)} 字节）", flush=True)
            continue

        kind = spec_ex["kind"]
        has_prefix = "prefix" in spec_ex            # 空串也是合法前缀 = 整包
        if kind == "deb":
            members = _extract_tar(_tar_bytes_from_deb(blob),
                                   spec_ex.get("member"), spec_ex.get("prefix"))
        elif kind == "tar":
            members = _extract_tar(_decompress(blob),
                                   spec_ex.get("member"), spec_ex.get("prefix"))
        elif kind == "zip":
            members = _extract_zip(blob, spec_ex.get("member"), spec_ex.get("prefix"))
        else:
            raise ValueError(f"不认识的 extract.kind：{kind}")

        base = _normalize(item["to"])
        for rel, data in members:
            _write(dest_root, os.path.join(base, rel) if has_prefix else base, data, mode)
        print(f"[ok]      {item['to']}（{len(members)} 个成员，sha256 已核对）", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
