# 方法：让任意一个 Linux arm64 CLI 跑起来

四种工具 + 两条环境修法，覆盖全部实测样本。

## 1. `glibc-run` —— glibc 动态程序

```sh
glibc-run [-L <额外库目录>] <程序> [参数...]
```

等价于：

```sh
unset LD_PRELOAD
"$GLIBC_ROOT/lib/ld-linux-aarch64.so.1" \
  --library-path "$GLIBC_ROOT/lib[:额外库目录]" \
  --argv0 "<程序绝对路径>" \
  --preload "<seccomp-enosys.so>" \
  "<程序>" [参数...]
```

四个选项各自对应一个坑（见 `pitfalls.md` 第 6 条）：
- `unset LD_PRELOAD`：防止 bionic 的预载库被继承进来
- `--library-path`：glibc 的库目录（**绝不能混入 bionic 的目录**）
- `--argv0`：会自我重执行的 CLI 需要它
- `--preload`：seccomp 垫片

## 2. `musl-run` —— musl 动态程序

```sh
musl-run <程序> [参数...]        # 内部：env -u LD_PRELOAD enosys-run <musl>/ld-musl-aarch64.so.1 --library-path <musl> <程序>
```

musl 加载器从 Alpine 的 musl 包取（约 700 KB，见 `tools/README.md`）。

## 3. `dnsproxy.py` —— 给静态二进制的 DNS 桥

一个只监听 `127.0.0.1` 的 HTTP CONNECT 代理：**域名解析用它自己的（系统解析器），
程序只连字面 IP**。适合所有认 `HTTPS_PROXY` 的命令行程序。

```sh
python3 tools/dnsproxy.py 18080 &
HTTPS_PROXY=http://127.0.0.1:18080 HTTP_PROXY=http://127.0.0.1:18080 <程序> …
```

## 4. `probe.sh` —— 探测脚本

```sh
tools/probe.sh <标签> <命令...>
```

跑一条命令、超时兜底、stdin 接 `/dev/null`（**绝不挂在交互等待上**）、
完整输出落 `logs/probe-<标签>.log`、屏幕只回退出码与前几行。
`rc > 128` 会标注信号号（137=超时 KILL、132=SIGILL、135=SIGSYS…）。

## 两条环境修法

### CA 包

```sh
SSL_CERT_FILE=/path/to/cert.pem <程序> …
```

CA 包来源：系统自带的（Termux 系在 `$PREFIX/etc/tls/cert.pem`）、
或从发行版的 ca-certificates 包里取 Mozilla 根证书集。

### seccomp 垫片

- 动态（glibc）：由 `glibc-run` 的 `--preload` 自动带上
- 静态：`enosys-run <程序> …`

垫片做的唯一一件事：把**被安卓 seccomp 拦下的系统调用**改成返回 `ENOSYS`，
让程序走它自己本来就有的回退路径。**不放宽任何限制。**

## 一份最小检查顺序

1. `file <程序>` → 定形态（见 `matrix.md`）
2. `--version` → 能不能启动
3. 启动失败报什么：`No such file or directory` → 换加载器；`SIGSYS` → 垫片
4. 能启动后跑真实命令 → 报 DNS → 起桥；报 TLS → 指 CA
5. 还是不行 → `strace -f` 看最后一次系统调用（很多"静默"失败会现形）
