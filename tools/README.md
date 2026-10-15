# 工具与取材

## 用法

```sh
# glibc 动态程序
tools/glibc-run -L ./libs <程序> --version

# musl 动态程序（先准备 ./musl，见下）
MUSL_ROOT=./musl tools/musl-run <程序> --version

# 静态程序联网：起 DNS 桥 + 指 CA
python3 tools/dnsproxy.py 18080 &
HTTPS_PROXY=http://127.0.0.1:18080 SSL_CERT_FILE=<CA 包> <程序> …

# 通用探测（输出落 logs/）
tools/probe.sh <标签> <命令...>
```

`glibc-run` 依赖：一个 glibc 运行时目录（含 `lib/ld-linux-aarch64.so.1`）、
可选的 seccomp 垫片（`ENOSYS_SO`，没有也能跑，只是可能被 SIGSYS 打死）。
`musl-run` 依赖：Alpine 的 musl 包、可选的 `enosys-run`。

## 额外库从哪来

`$PREFIX/glibc/lib` 里常常缺这三样，而很多 CLI 需要它们：

| 库 | 谁要 | 从哪取 |
|---|---|---|
| `libz.so.1` | Mistral Vibe（PyInstaller） | Debian `zlib1g` 的 arm64 deb 里 `usr/lib/aarch64-linux-gnu/libz.so.1*` |
| `libstdc++.so.6` | GitHub Copilot（glibc 版） | Debian `libstdc++6` 的 arm64 deb |
| `libgcc_s.so.1` | Amazon Q、Copilot | Debian `libgcc-s1` 的 arm64 deb |
| musl 加载器 | Copilot（musl 版）等 musl 动态程序 | Alpine `musl` 的 aarch64 apk：`https://dl-cdn.alpinelinux.org/alpine/<版本>/main/aarch64/musl-<版本>.apk`（`tar xzf` 解开即得 `lib/ld-musl-aarch64.so.1`） |

`.deb` / `.apk` 都是归档，解开后从里面取文件即可（`.deb` 是 ar 归档，内层 `data.tar.*`；
`.apk` 直接是 gzip 的 tar）。**从上游发行版取，比从别人的包里拷干净**。

放在一个目录里（比如 `./libs`），用 `glibc-run -L ./libs` 指过去；
PyInstaller 型程序还要把这个目录里的缺库**再拷一份进它的 `_internal/`**（原因见 `docs/pitfalls.md` 第 6d 条）。

## CA 包

系统里通常已有：Termux 系在 `$PREFIX/etc/tls/cert.pem`；
否则从发行版的 `ca-certificates` 包里取 Mozilla 根证书集（`.crt`/`.pem` 均可），
用 `SSL_CERT_FILE=<文件>` 指给程序。

## seccomp 垫片

- **动态链接**：一个小 `.so`，用加载器的 `--preload` 挂上（`glibc-run` 默认带上，
  路径用 `ENOSYS_SO` 指定）。
- **静态二进制**：需要从进程外面做（ptrace），即 `enosys-run` 一类的工具
  （本仓库不附带；思路与实现见 `docs/methods.md`，文末有参考实现的名字）。

垫片只把**被拦下的系统调用**改成返回 `ENOSYS`，不放宽任何限制。
