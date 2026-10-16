# AI CLI 上手机 · 实测与通法

[English](README.md) · **简体中文**

> 在一台安卓手机上，把 13 家模型厂商的命令行 AI 代理原生跑起来的实测记录，以及让它们跑起来的那一层适配方法。
>
> 本仓库不含任何厂商的二进制，只放方法、脚本与实测记录；安装一律走官方渠道。各 CLI 的商标与二进制归各自厂商。

## 结论

安卓底层就是 Linux。这次试过的 CLI，在处理好「这个程序是给哪种 Linux 编的」之后，都能在手机上原生启动，
不需要 root、容器或改系统。各家走到哪一步不一样，见下表；多数只用假密钥验到了请求到达服务端，
用真实凭据跑通对话的只有 Claude Code 和 GitHub Copilot。

实测环境：一台设备，Android 14（SDK 34）· aarch64 · 未 root · 普通应用身份 ·
Node 26 / Python 3.14 / 一套 glibc 运行时（`$PREFIX/glibc`）。换设备、换版本，结果可能不同。

## 总表（2026-10-15）

| 厂商 | CLI | 分发形态 | 走到哪一步 | 需要的适配 |
|---|---|---|---|---|
| Google | Antigravity CLI `agy` 1.3.5 | 官方 Android（bionic）构建 | 启动，停在 OAuth 登录 | 无 |
| Anthropic | Claude Code 2.1.292 | glibc 动态 | 日常使用 | glibc 加载器 + seccomp 垫片 |
| OpenAI | Codex CLI 0.162.1 | 静态 musl（254 MB） | 请求到达 API（假密钥，401） | DNS 桥 + CA 包 |
| xAI | Grok Build 0.1.220 | brotli 压缩的静态 ELF | 请求到达 API（假密钥，400） | 解压 + DNS 桥 + CA |
| 微软 | GitHub Copilot CLI 1.0.98 | glibc 动态 + C++ | 用真实凭据得到模型回复 | 加载器 + `libstdc++` / `libgcc_s` |
| 微软 | GitHub Copilot CLI（musl 版） | musl 动态 | 启动（`--version`） | Alpine musl 加载器 + seccomp 垫片 |
| Google | Gemini CLI 0.64.0 | Node | 请求到达 API（假密钥，400） | `TERMUX_VERSION=1` |
| 阿里 | Qwen Code 0.25.1 | Node | 启动，停在认证 | 无 |
| Moonshot | Kimi Code 2.2.0 | Node | 启动，停在认证 | 无 |
| 腾讯 | CodeBuddy 2.167.0 | Node | 启动，停在认证 | 无 |
| Mistral | Vibe 2.26.1 | PyInstaller / glibc | 请求到达 API（假密钥） | 加载器 + 补 `libz` |
| Amazon | Q Developer CLI 1.19.7 | glibc 动态 + C++ | 启动，停在登录 | 加载器 + C++ 库 |
| 智谱 Z.ai | 无独立 CLI；官方 helper | Node | helper 可运行 | 无 |
| DeepSeek | DeepSeek Harness `dsh` 0.2.0-rc.2 | Node + 3 个原生附件 | 对本地 mock 端点跑完一个回合 | 原生附件走 JS 回退；硬链接改独占创建 |

「请求到达 API」指程序完整启动、读配置、发出请求并得到服务端的正常应答（假密钥返回 401/400，说明只差凭据）。
DeepSeek 那行没有用真实模型，而是把端点指向本地 mock，借此看到了它发出的完整请求（系统提示、文件策略、工具清单），
见 [`docs/survey.md`](docs/survey.md) 第 14 节。逐家细节也在那里。

## 三点观察

**1. 分发形态决定适配方式。** 同样标着「linux arm64」，实际有好几种形态，处理方法各不相同：

| 形态 | 能否直接跑 | 适配 |
|---|---|---|
| 官方安卓构建 | 内核直接加载 | 无 |
| Node / 纯脚本 | 有 node 就行 | 注意程序里的平台判定 |
| Node/Python + 原生附件 | 主程序能跑 | 附件多半没有 android 产物：JS 回退 / FFI 顶替 / 自己编 |
| 静态二进制（musl/Go） | 内核直接加载 | 联网要过 DNS 与 CA 两关 |
| glibc 动态 | 不行（安卓没有 `/lib/ld-linux-aarch64.so.1`） | 换 glibc 加载器 |
| musl 动态 | 不行（没有 `/lib/ld-musl-aarch64.so.1`） | 换 musl 加载器 |

完整的分类和判断方法见 [`docs/matrix.md`](docs/matrix.md)。

**2. 换加载器不只是调用一下 `ld.so`。** 安卓的 seccomp 白名单、继承下来的 bionic `LD_PRELOAD`、
其实是链接脚本的 `libc.so`、程序自我重执行时丢掉的 `--library-path`，都会让程序以不像「加载器问题」的方式失败。
清单见 [`docs/pitfalls.md`](docs/pitfalls.md)。

**3. 能启动和能联网是两回事。** 静态二进制在安卓上启动没问题，但常卡在两处：
没有 `/etc/resolv.conf`（DNS 解析不了）和没有 `/etc/ssl/certs`（TLS 验不过）。两种情况看起来都像断网。
解法见 [`docs/methods.md`](docs/methods.md)。

## 为什么做这件事

想知道「让 AI 代理在手机本地干活」这条路是不是只对某一家成立。结果看，方法是通用的：
模型推理在云端，代码、文件和工具链留在自己的设备上，环境也不会随会话销毁。

## 范围与局限

- 只在一台设备上测过；各家的分发形态随版本变化，结论都标了日期。
- 多数 CLI 只用假密钥验到链路连通，没有用真实账号做完整使用。
- 各家的交互式 TUI 没有逐项验证。

## 仓库结构

```
docs/survey.md     逐家实测：来源、最短复现命令、实测输出、注意事项
docs/matrix.md     形态 × 适配矩阵（含"怎么先判断一个 CLI 属于哪类"）
docs/methods.md    加载器方法 + DNS 桥 + CA + seccomp 垫片
docs/pitfalls.md   平台坑清单，每条带症状与真实报错
tools/glibc-run    通用 glibc 启动器（含 --argv0、seccomp 垫片）
tools/musl-run     通用 musl 启动器（Alpine 加载器 + enosys）
tools/probe.sh     探测脚本：跑一条命令，输出落日志
tools/dnsproxy.py  给静态二进制用的本地 DNS 桥（只监听回环）
tools/README.md    工具用法，以及额外的库（libz / libstdc++ / musl）从哪来
recipes/           把这些 CLI 做成 cccodroid 组件的示范配方（启动器型，10 个），只作方法存档，不计划上架
evidence/          总表背后的运行输出摘录，可复核
```

## 复现

以 Codex 为例：

```sh
# 1. 从官方渠道拿 linux-arm64 包（npm 平台包）
npm pack @openai/codex@<版本>-linux-arm64 && tar xzf *.tgz
# 2. 起 DNS 桥、指定 CA，然后运行
python3 tools/dnsproxy.py &
HTTPS_PROXY=http://127.0.0.1:18080 SSL_CERT_FILE=<CA 包> \
  ./package/vendor/aarch64-unknown-linux-musl/bin/codex --version
```

glibc 系（Copilot / Amazon Q / Vibe 等）：

```sh
tools/glibc-run -L ./libs <程序> --version
```

## 许可与声明

- 本仓库：Apache-2.0。
- 只含方法、脚本与实测记录，不打包、不镜像任何厂商的二进制；请从各厂商官方渠道安装，并遵守各自的许可与条款。
- 各厂商名称、CLI 名称与商标归各自权利人所有，此处仅用于指明测试对象。
