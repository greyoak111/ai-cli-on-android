# AI CLI 上手机 · 实测与通法

[English](README.md) · **简体中文**

> 各大模型厂商的命令行 AI 代理，在安卓手机上**原生运行**的实测记录，以及让它们跑起来的那一层适配方法。
>
> 本仓库**不含任何厂商的二进制**：只放方法、脚本与实测记录；安装一律走官方渠道。各 CLI 的商标与二进制归各自厂商。

## 一句话结论

安卓手机本来就是 Linux。只要把「这程序是给谁的 Linux 写的」这件事处理掉，
各家厂商的 AI 命令行代理都能原生跑在手机上 —— **不用 root、不用容器、不用改系统**。

实测环境：Android 14（SDK 34）· aarch64 · 未 root · 普通应用 uid ·
Node 26 / Python 3.14 / 一套 glibc 运行时（`$PREFIX/glibc`）。

## 总表（2026-10-15 实测）

| 厂商 | CLI | 分发形态 | 结果 | 需要的适配 |
|---|---|---|---|---|
| Google | Antigravity CLI `agy` 1.3.5 | **官方 Android/bionic 构建** | ✅ 直接跑 | 无 |
| Anthropic | Claude Code 2.1.292 | glibc 动态 | ✅ 完整可用 | glibc 加载器 + seccomp 垫片 |
| OpenAI | Codex CLI 0.162.1 | 静态 musl（254 MB） | ✅ 打到真实 API | DNS 桥 + CA 包 |
| xAI | Grok Build 0.1.220 | brotli 压缩的静态 ELF | ✅ 打到真实 API | 解压 + DNS 桥 + CA |
| 微软 | GitHub Copilot CLI 1.0.98 | glibc 动态 + C++ | ✅ **真实模型回复** | 加载器 + `libstdc++/libgcc_s` |
| 微软 | GitHub Copilot CLI（musl 版） | musl 动态 | ✅ 启动成功 | Alpine musl 加载器 + seccomp |
| Google | Gemini CLI 0.64.0 | Node | ✅ 打到真实 API | `TERMUX_VERSION=1` |
| 阿里 | Qwen Code 0.25.1 | Node | ✅ 到认证步骤 | 无 |
| Moonshot | Kimi Code 2.2.0 | Node | ✅ 到认证步骤 | 无 |
| 腾讯 | CodeBuddy 2.167.0 | Node | ✅ 到认证步骤 | 无 |
| Mistral | Vibe 2.26.1 | PyInstaller / glibc | ✅ 打到真实 API | 加载器 + 补 `libz` |
| Amazon | Q Developer CLI 1.19.7 | glibc 动态 + C++ | ✅ 到认证步骤 | 加载器 + C++ 库 |
| 智谱 Z.ai | 无独立 CLI；官方 helper | Node | ✅ helper 可跑 | 无 |
| DeepSeek | **DeepSeek Harness `dsh` 0.2.0-rc.2** | Node + 3 个原生附件 | ✅ **跑完整回合**（本地 mock 端点） | 原生附件走 JS 回退；硬链接改独占创建 |

「到认证步骤 / 打到真实 API」= 程序完整启动、读配置、发起网络请求并被服务端正常应答
（用假密钥时得到 401/400，即链路全通）。DeepSeek 那行更进一步：拿本地 mock 端点
**跑完了一整个 agent 回合**（含系统提示、文件策略、工具清单，见 survey 第 14 节）。
逐家细节见 [`docs/survey.md`](docs/survey.md)。

## 三条主线索

**1. 形态决定一切。** 同是「linux arm64 CLI」，分发形态有五种，适配方式完全不同：

| 形态 | 谁能直接跑 | 适配 |
|---|---|---|
| 官方安卓构建 | 内核直接加载 | 无 |
| Node / 纯脚本 | 有 node 就行 | 平台判定的环境变量 |
| Node/Python + 原生附件 | 主程序直接跑 | 附件多半没有 android 产物：JS 回退 / FFI 顶替 / 自己编 |
| 静态二进制（musl/Go） | 内核直接加载 | 联网要过 DNS 与 CA 两关 |
| glibc 动态 | 不行（安卓没有 `/lib/ld-linux-aarch64.so.1`） | 换 glibc 加载器 |
| musl 动态 | 不行（没有 `/lib/ld-musl-aarch64.so.1`） | 换 musl 加载器 |

**2. 换加载器不是"跑个 ld.so"那么简单。** 安卓的 seccomp 白名单、bionic 的 `LD_PRELOAD`、
被当作链接脚本的 `libc.so`、自我重执行时丢失的 `--library-path`……每一个都能让程序以
完全不像"加载器问题"的方式失败。清单见 [`docs/pitfalls.md`](docs/pitfalls.md)。

**3.「能启动」与「能联网」是两件事。** 静态二进制在安卓上畅通无阻，却常死在两处：
没有 `/etc/resolv.conf`（DNS 解析不了）和没有 `/etc/ssl/certs`（TLS 验不过）。
两条都以"看起来像断网"的形式出现。解法见 [`docs/methods.md`](docs/methods.md)。

## 为什么值得做

- **执行回到端侧**：模型推理在云端，代码、文件、工具链留在自己的手机上，
  不为了"让 AI 跑一下"把仓库传进别人的临时容器。
- **不绑定厂商**：同一套方法换任何一家 CLI；模型侧同理，各家的 Anthropic/OpenAI 兼容端点都能接。
- **环境是持久的**：装过的工具、配置、会话都在，不是随会话销毁的沙箱。

## 仓库结构

```
docs/survey.md     13 家逐家实测：来源、最短复现命令、实测证据、注意事项
docs/matrix.md     形态 × 适配 矩阵（含"怎么先判断一个 CLI 属于哪类"）
docs/methods.md    三种加载器方法 + DNS 桥 + CA + seccomp 垫片
docs/pitfalls.md   平台坑清单：每个都带症状与真实报错
tools/glibc-run    通用 glibc 启动器（含 --argv0、seccomp 垫片）
tools/musl-run     通用 musl 启动器（Alpine 加载器 + enosys）
tools/probe.sh     探测脚本：一条命令出结果，输出落日志
tools/dnsproxy.py  给静态二进制用的本地 DNS 桥（仅监听回环）
tools/README.md    工具用法 + 额外库（libz / libstdc++ / musl）从哪来
recipes/           把这批 CLI 做成组件的示范（启动器型，10 个）——**方法论，不是路线图**，不计划上架
evidence/          上面那张表背后的真实运行片段（原话摘录，可复核）
```

## 复现

最小路径（以 Codex 为例）：

```sh
# 1. 官方渠道拿到 linux-arm64 包（npm 平台包）
npm pack @openai/codex@<版本>-linux-arm64 && tar xzf *.tgz
# 2. 起 DNS 桥 + 指定 CA，然后跑
python3 tools/dnsproxy.py &
HTTPS_PROXY=http://127.0.0.1:18080 SSL_CERT_FILE=<系统 CA 包> \
  ./package/vendor/aarch64-unknown-linux-musl/bin/codex --version
```

glibc 系（Copilot / Amazon Q / Vibe 等）：

```sh
tools/glibc-run -L ./libs <程序> --version
```

## 许可与声明

- 本仓库：Apache-2.0。
- 只含方法、脚本与实测记录，**不打包、不镜像任何厂商的二进制**；
  安装请走各厂商官方渠道，并遵守各自的许可与条款。
- 各厂商名称、CLI 名称与商标归各自权利人所有，此处仅为指明兼容对象。
