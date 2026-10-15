#!/usr/bin/env python3
"""install.py — 按官方 manifest 安装 Antigravity CLI 的安卓构建。

    install.py <dest-dir>

流程：取 manifest（android_arm64）→ 下载构件 → **核对 manifest 里的 sha512** →
从 tar.gz 里取出 antigravity 成员 → 落地为 <dest-dir>/agy（755）。

manifest 地址可用 CCODROID_AGY_MANIFEST 覆盖（本地测试时指向 file:// 即可）。
"""

import hashlib
import io
import json
import os
import sys
import tarfile
import urllib.request

DEFAULT_MANIFEST = (
    "https://antigravity-cli-auto-updater-974169037036.us-central1.run.app"
    "/manifests/android_arm64.json"
)
ALLOWED_SCHEMES = ("https://", "file://")


def _download(url: str) -> bytes:
    if not url.startswith(ALLOWED_SCHEMES):
        raise ValueError(f"只接受 https（或本地测试的 file://）：{url}")
    with urllib.request.urlopen(url, timeout=600) as resp:
        return resp.read()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: install.py <dest-dir>", file=sys.stderr)
        return 2
    dest = sys.argv[1]
    manifest_url = os.environ.get("CCODROID_AGY_MANIFEST", DEFAULT_MANIFEST)

    print(f"[manifest] {manifest_url}", flush=True)
    meta = json.loads(_download(manifest_url))
    version, url, want = meta["version"], meta["url"], meta["sha512"]
    print(f"[fetch]    CLI {version} ← {url.split('/')[-1]}", flush=True)

    blob = _download(url)
    digest = hashlib.sha512(blob).hexdigest()
    if digest != want:
        print(f"[FAIL]     sha512 不匹配：\n  期望 {want}\n  实际 {digest}",
              file=sys.stderr, flush=True)
        return 1

    print("[extract]  解开 tar.gz，取 antigravity 成员", flush=True)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        member = None
        for entry in tf:
            if entry.isfile() and entry.name.rstrip("/").endswith("antigravity"):
                member = entry
                break
        if member is None:
            print("[FAIL]     包里没有 antigravity 成员", file=sys.stderr, flush=True)
            return 1
        fh = tf.extractfile(member)
        assert fh is not None
        data = fh.read()

    os.makedirs(dest, exist_ok=True)
    target = os.path.join(dest, "agy")
    tmp = target + ".part"
    with open(tmp, "wb") as out:
        out.write(data)
    os.chmod(tmp, 0o755)
    os.replace(tmp, target)               # 原子改名：中断不会留下半个二进制
    print(f"[ok]       agy {version}（{len(data)} 字节，sha512 已核对）", flush=True)

    # 顺手把版本记下来，便于排查
    with open(os.path.join(dest, "VERSION"), "w", encoding="utf-8") as out:
        out.write(version + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
