# 逐家实测（2026-10-15）

环境：Android 14 / aarch64 / 未 root / Node 26.4 / Python 3.14 / `$PREFIX/glibc`（glibc 2.44）。
「实测证据」一栏是真实输出摘要；用假密钥时得到 401/400 即为**链路全通**（只差凭据）。

---

## 1. Google · Antigravity CLI（`agy`）1.3.5 — ✅ 官方安卓构建

**来源**：`curl -fsSL https://antigravity.google/cli/install.sh | bash`
（支持 `--dir` 指定目录；平台判定见下）

**形态**：ELF aarch64，`interpreter /system/bin/linker64`，`for Android 24, built by NDK r29`
—— 官方**专门为安卓编的 bionic 版本**，176 MB。

它的安装脚本里写着：

```sh
# Termux needs the Bionic build: Android's linker rejects glibc/musl ones.
Linux) if [ "$(uname -o 2>/dev/null)" = "Android" ]; then os="android"; else os="linux"; fi ;;
```

manifest 直接给 `cli_android_arm64.tar.gz`。这次测的各家里，只有它提供了官方安卓构建。

**实测证据**：

```
$ agy --version      → 1.3.5
$ agy --help         → 39 行完整用法
$ agy -p "say hi"    → 打印 Google OAuth 登录 URL，等待授权码（无头环境 60 秒超时属正常）
```

---

## 2. Anthropic · Claude Code 2.1.292 — ✅（基线，本机日常使用）

**形态**：glibc 动态（官方 linux-arm64 原版二进制）。

**适配**：由 `$PREFIX/glibc/lib/ld-linux-aarch64.so.1` 启动，`--preload` 一个把
被 seccomp 拦截的系统调用改成 ENOSYS 的小库（否则 Android 14 上 `epoll_pwait2` 一调用就被杀）。
这套"加载器 + 垫片"正是本仓库其余方法的基础设施。

---

## 3. OpenAI · Codex CLI 0.162.1 — ✅（要过 DNS 与 CA 两关）

**来源**：`npm pack @openai/codex@0.162.1-linux-arm64`（平台包是**同包名的带后缀版本号**，不是独立包名）

**形态**：`vendor/aarch64-unknown-linux-musl/bin/codex`，**全静态**，254 MB，**直接执行**。

**适配**：静态二进制不经安卓的 linker，启动无障碍；但联网撞两堵墙：

1. musl 的解析器只读 `/etc/resolv.conf` —— 安卓没有这个文件 → `failed to lookup address information: Try again`
2. 没有 `/etc/ssl/certs` → `invalid peer certificate: UnknownIssuer`

解法：本地 DNS 桥（`tools/dnsproxy.py`，Python 走系统解析）+ `SSL_CERT_FILE`。

**实测证据**：

```
$ codex --version            → codex-cli 0.162.1
$ HTTPS_PROXY=http://127.0.0.1:18080 SSL_CERT_FILE=<cert.pem> OPENAI_API_KEY=sk-dummy \
    codex exec --skip-git-repo-check "say hi"
→ HTTP 401: Missing bearer or basic authentication  （请求真的到了 api.openai.com）
```

---

## 4. xAI · Grok Build 0.1.220 — ✅（需要先解压）

**来源**：`npm pack @xai-official/grok-linux-arm64@0.1.220`

**形态**：npm 包里只有一个 **brotli 压缩**的 `bin/grok.br`（私有格式，由它的 JS 启动器解压）。
解出来是 106 MB 的**静态 ELF**。

```sh
node -e "const z=require('zlib'),fs=require('fs');
  fs.writeFileSync('grok', z.brotliDecompressSync(fs.readFileSync('grok.br')), {mode:0o755})"
```

**适配**：同 Codex —— DNS 桥 + CA。

**实测证据**：

```
$ grok --version   → grok 0.1.220 (ae5f4af53)
$ grok -p "say hi" → HTTP 400: Incorrect API key provided（请求到了 api.x.ai）
```

---

## 5/6. 微软 · GitHub Copilot CLI 1.0.98 — ✅（glibc 版用真实凭据得到回复）

**来源**：`npm pack @github/copilot-linux-arm64@1.0.98` / `@github/copilot-linuxmusl-arm64@1.0.98`
（两种 libc 都发，罕见）

**glibc 版**：需 `libstdc++.so.6`（`$PREFIX/glibc/lib` 里没有）+ 加载器。跑通后
用本机已有的 gh 凭据完成了一次问答：

```
$ glibc-run -L ./libs copilot -p "say hi"
→ Hi!
  Changes +0 -0   AI Credits 0.18 (16s)   Tokens ↑ 14.0k ↓ 6
```

**musl 版**：需要 `/lib/ld-musl-aarch64.so.1`（安卓没有）。补 Alpine 的 musl 包后：

```sh
env -u LD_PRELOAD enosys-run <musl>/ld-musl-aarch64.so.1 --library-path <musl> ./copilot --version
→ GitHub Copilot CLI 1.0.98.
```

两个要点：必须清 `LD_PRELOAD`（bionic 的 termux-exec 预载会让 musl 加载器报一串
`symbol not found`）；musl 直启会 SIGSYS（rc=159），套 seccomp 垫片即过。

---

## 7. Google · Gemini CLI 0.64.0 — ✅（加一个环境变量）

**来源**：`npm install @google/gemini-cli`（纯 Node）

**适配**：启动即抛

```
Error: You need to install Termux for this module to work on Android: https://termux.com
```

出处是它捆绑的 **clipboardy**（剪贴板库）在**模块加载期**检查 `process.platform === 'android'`
且要求 `process.env.TERMUX_VERSION` 存在。`--version` 不导入它，`--help` 导入 —— 所以症状"时灵时不灵"。

```sh
TERMUX_VERSION=1 gemini --help          # 正常
TERMUX_VERSION=1 GEMINI_API_KEY=x gemini --skip-trust -p "hi"
→ 400 API key not valid（generativelanguage.googleapis.com）  ✅
```

（`--skip-trust` 是它自己的非交互确认开关；headless 场景会需要。）

---

## 8. 阿里 · Qwen Code 0.25.1 — ✅ 开箱

**来源**：`npm install @qwen-code/qwen-code`（纯 Node）

```
$ qwen --version → 0.25.1
$ qwen -p "say hi" → No auth type is selected. Please configure an auth type …
```

`--help`、参数解析、配置读取全部正常，只差选认证方式。

## 9. Moonshot · Kimi Code 2.2.0 — ✅ 开箱

```
$ kimi --version → 2.2.0
$ kimi -p "say hi" → No model configured. Run `kimi` and use /login …
```

## 10. 腾讯 · CodeBuddy Code 2.167.0 — ✅ 开箱

```
$ cbc --version → 2.167.0
$ cbc -p "say hi" → Authentication required. Please use /login …
```

> Node 这四家（Gemini/Qwen/Kimi/CodeBuddy）装的时候必须带 `--os=linux --cpu=arm64`，
> 原因见 `docs/pitfalls.md` 第 1 条。

---

## 11. Mistral · Vibe 2.26.1 — ✅（pip 装不上，改用官方二进制）

**来源**：PyPI 上下不到 —— 本机 Python 的兼容 tag 里**一个 manylinux 都没有**，
而它的 sdist 构建后端是 maturin（Rust），本机也没有 Rust。
改走 GitHub Release：`vibe-linux-aarch64-2.26.1.zip`（PyInstaller onedir）。

**适配**：glibc 加载器 + 补 `libz.so.1`；且因为 PyInstaller 会**二次启动**（那一刻
`--library-path` 丢失），`libz.so.1` 还必须**再拷一份进它的 `_internal/`**。

**实测证据**：

```
$ glibc-run -L ./libs vibe --version → vibe 2.26.1
$ MISTRAL_API_KEY=dummy vibe -p "hi" → Error: Invalid API key (from env var MISTRAL_API_KEY)
```

## 12. Amazon · Q Developer CLI 1.19.7 — ✅

**来源**：`https://desktop-release.q.us-east-1.amazonaws.com/latest/q-aarch64-linux.zip`
（包里有 `q` / `qchat` / `qterm` 三个 glibc 程序）

**适配**：加载器 + `libgcc_s.so.1`。

```
$ glibc-run -L ./libs q --version → q 1.19.7
$ grep… q chat "say hi" → error: You are not logged in, please log in with `q login`
```

---

## 13. 智谱 Z.ai — ➖

没有独立 CLI。官方定位是"配到别人的 CLI 里用"；官方 helper
`npx @z_ai/coding-helper` 本机可跑（`--help` 正常）。

---

## 14. DeepSeek · DeepSeek Harness（`dsh`）0.2.0-rc.2 — ✅ 对本地 mock 端点跑完一个回合

**来源**：npm `@deepseek-ai/dsh`（MIT；源码 `github.com/deepseek-ai/deepseek-harness`，口号
"Everything is a Plugin"）。纯 Node 程序，**没有 linux-arm64 预编译主程序**。

**形态**：Node 程序 + 三个 **Node-API 原生附件**。主程序本身完全跨平台，
卡点全在附件上 —— 它们只发布 darwin / linux-x64 / linux-arm64 / win32 的产物，**没有 android**。

**适配集中在原生附件上**：不换加载器（不碰 bionic/glibc 之争）、不要 seccomp 垫片、
不要 DNS 桥、不要 CA 包 —— 前面几家遇到的那几类问题它都没有。适配只落在"安卓没有的那几个原生附件"上，
每一处都找到了不需要编译的替代路径：

| 上游原生件 | 用途 | Android 上的症状 | 不编译的替代 |
|---|---|---|---|
| `node-addon-require-builtin` | 打开 Node 内部模块（插件加载器要用） | `dsh: host preparation failed: No usable native binding found for node-addon-require-builtin-android-arm64 (auto)` —— **连 web profile 都起不来** | 启动 node 时加 `--expose-internals`，`require("internal/modules/…")` 直接可用；在 JS 里做一层回退即可（上游源码公开且 MIT，也能自己编：一条 clang 命令） |
| `@deepseek-ai/node-addon-system`（flock） | 会话文件的非阻塞互斥锁 | 先 `flock is not supported on android-arm64`（纯 JS 平台判定）；放行后仍加载不了：glibc 版要 `libc.so.6`、musl 版要 `__errno_location`，bionic 都没有 | `flock(2)` 在 bionic 里**是有的** → 改 JS 用 FFI 调它，或退化为空锁 |
| `koffi`（FFI） | 只在 win32 路径用到 | `npm install` 时编译失败（`base.cc:2967` 的 `statx`，见 pitfalls 第 9 条） | `npm install --ignore-scripts` 就行 —— 安卓路径根本不需要它 |

另有两处不是"加载"，是**安卓的内核/SELinux 行为**：

| 症状 | 原因 | 改法 |
|---|---|---|
| `EACCES: permission denied, link '…tmp' -> '…session.v4.jsonl.zstd'` | 安卓 SELinux 禁止应用私有目录里建硬链接（详见 pitfalls 第 10 条） | 上游用 `link()` 做"独占发布"（靠 EEXIST 判断目标已存在），**不能**简单换 rename（会静默覆盖）→ 改成 `open(path, "wx")` 独占创建 + 写入，语义等价 |
| 目录 fsync 返回 `EINVAL` / `ENOTSUP` | 部分挂载点不支持目录 fsync | 视为尽力而为，不因此判定"会话发布失败" |

**实测证据**（Android 14 / Node 26.4）：

```
$ npm install --ignore-scripts --os=linux --cpu=arm64 @deepseek-ai/dsh
$ dsh --version                        → 0.2.0-rc.2
$ dsh web                              → dsh web: http://127.0.0.1:3080/?token=…
$ curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3080/   → 401（无 token）
$ curl … "http://127.0.0.1:3080/?token=…"                          → 303（会话建立）
$ dsh --profile headless "reply with the word ok"     # DEEPSEEK_BASE_URL 指向本地 mock
                                       → OK-FROM-LOCAL-MOCK      （rc=0，stderr 为空）
```

这次没有用真实模型，而是让本地 mock 端点接住请求，好看清它发出了什么。收到的请求是
`POST /v1/messages`、`user-agent: deepseek-harness/0.2.0-rc.2`、`model: deepseek-flash`、
请求体 53 KB，system 里是完整的 agent 提示词，运行上下文里的文件策略已经落到会话工作区
（`workspace-write` + 实际目录）、工具清单齐备 —— 说明插件树、内部模块加载、沙箱策略、
会话持久化在安卓上都能工作。（与 Claude Code、Copilot 不同，这里没有接真实模型。）

**社区已有适配补丁集**：`woaiys3/deepseek-harness-android-app` 的
`dsh-patches/overlay-020/`（12 个文件，覆盖上面全部四处，**零原生编译**）。本机是把这套补丁
原样应用（外加 `node --expose-internals` 启动）后跑通的；该项目的归纳是"4 处需要适配 Android 的
源码改动"：subprocess（node-pty 编不了）、attachment（sharp + 硬链接）、bash 沙箱、
会话持久化（硬链接）。

**对照实验**：不用补丁集、改走"自己编原生件"也能通 —— 编出
`node-addon-require-builtin` 的 android-arm64 产物（公开源码，一条 clang 命令）+
用 koffi 的**真 flock** 替掉空锁，headless 同样得到 `OK-FROM-LOCAL-MOCK`。
两条路都验过；差别只是"要不要在本机编译"。

---

## 未测

- 各家的**交互式 TUI** 完整使用（需要真实凭据/登录；本报告只验到"链路全通"）。
- 各家在自己的更新节奏里随时可能改变分发形态；本报告的版本号与结论都标注了实测日期。
