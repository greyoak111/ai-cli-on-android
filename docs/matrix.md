# 形态矩阵：拿到一个 CLI，先判断它属于哪类

## 第一步：看它是什么

```sh
file <二进制>
readelf -d <二进制> | grep NEEDED      # 动态的看依赖
head -1 <脚本>                          # 脚本的看 shebang
```

| `file` 说 | 说明 | 去哪一节 |
|---|---|---|
| `for Android … /system/bin/linker64` | 官方 bionic 构建 | A |
| 文本 / shebang 是 node、python | 脚本 | B |
| `statically linked` | 静态 | C |
| `interpreter /lib/ld-linux-aarch64.so.1` | glibc 动态 | D |
| `interpreter /lib/ld-musl-aarch64.so.1` | musl 动态 | E |
| 非 ELF（`.br`、`.gz`、`.zip` 里的东西） | 先解压再回到第一步 | — |

## A. 官方安卓构建 —— 直接跑

内核直接加载，什么都不用。实测：Google Antigravity CLI。
（判断依据：`built by NDK` / `for Android NN` / interpreter 是 `/system/bin/linker64`。）

## B. Node / Python 脚本 —— 看两个平台判定

能跑 node/python 就能跑。例外都在"程序里写死的平台判定"：

- **npm 装的时候**：必须 `npm install --os=linux --cpu=arm64`（见 pitfalls 第 1 条）。
- **运行时**：有的库会在加载期检查平台。实测：Gemini CLI 捆绑的 clipboardy 要求
  `TERMUX_VERSION` 存在（`TERMUX_VERSION=1 gemini …` 即过）。
- **Python**：只装纯 Python 包；带 C 扩展的现场编译；**PyPI 的 manylinux wheel 一律装不上**
  （见 pitfalls 第 2 条），所以 Python 系 CLI 优先找官方独立二进制。

## C. 静态二进制 —— 直接跑，但联网要过两关

启动没问题（内核直接加载，不经 linker，也不受 bionic/glibc 之争影响）。
撞的是**运行环境**，不是加载：

1. **DNS**：musl / Go 的自带解析器只读 `/etc/resolv.conf`，安卓没有 → 起本地 DNS 桥
2. **CA**：安卓没有 `/etc/ssl/certs` → `SSL_CERT_FILE=<系统里的 CA 包>`

实测：Codex、Grok（两者都是静态）。

若出现 `SIGSYS: bad system call`：套 `enosys-run <程序> …`。

## D. glibc 动态 —— 换加载器

安卓没有 `/lib/ld-linux-aarch64.so.1`，直接执行会报
`No such file or directory`（**注意：这个报错说的是解释器不存在，不是文件不存在**）。

```sh
tools/glibc-run -L ./libs <程序> [参数...]
```

`glibc-run` 做了四件事：清 bionic 的 `LD_PRELOAD`、指定 `--library-path`、
`--preload` seccomp 垫片、给 `--argv0`（防自我重执行时 argv[0] 变成 ld.so）。

常见缺库（`$PREFIX/glibc/lib` 里没有的）：`libz.so.1`、`libstdc++.so.6`、`libgcc_s.so.1`
—— 见 `tools/README.md` 的"额外库从哪来"。

## E. musl 动态 —— 补一个 musl 加载器

安卓没有 `/lib/ld-musl-aarch64.so.1`。拿 Alpine 的 musl 包即可（约 700 KB）：

```sh
tools/musl-run <程序> [参数...]
```

注意两点：**必须清 `LD_PRELOAD`**（bionic 的预载会让 musl 加载器报一串
`…: symbol not found`）；musl 直启在安卓上会 SIGSYS，**套 `enosys-run`**。

## F. 特殊打包（PyInstaller 等）—— 注意"二次启动"

PyInstaller 的 onedir 程序在启动时会**再启动一次**自己，那一刻命令行上的
`--library-path` **不在**了，只会搜索自己 `_internal/` 和加载器的默认路径。
所以：缺的库除了 `-L` 给一份，**还要往它的 `_internal/` 里拷贝一份**。

实测：Mistral Vibe 的 `libz.so.1`。

## 一页速查

| 形态 | 启动 | 联网 | 一句话 |
|---|---|---|---|
| A 官方安卓 | 直接 | 正常 | 白送 |
| B 脚本 | 直接 | 正常 | 注意平台判定与 npm 参数 |
| C 静态 | 直接 | 要修 | DNS 桥 + CA；SIGSYS 用 enosys |
| D glibc | 加载器 | 正常 | 常缺 C++/zlib |
| E musl | 加载器 | 要修 | Alpine musl + enosys |
| F PyInstaller | 加载器 | 正常 | 缺库要塞 `_internal/` |
