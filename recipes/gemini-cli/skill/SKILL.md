---
name: gemini-cli
description: Google Gemini CLI（cccodroid 组件）：在终端里让 Gemini 读代码、改文件、跑命令。用户提到 Gemini、Google 的 AI、或要另跑一个模型做交叉验证时使用。
---

# Gemini CLI（Google）

本机装了 Google 官方的 `gemini`（组件启动器；程序在首次运行时从官方 npm 装进用户私有目录）。

## 用法

```sh
gemini --version
gemini -p "解释这个目录的结构"                 # 非交互（headless）
gemini --help
gemini                                       # 交互式 TUI
```

- **非交互跑之前先确认信任目录**：headless 模式需要 `--skip-trust`，或设 `GEMINI_CLI_TRUST_WORKSPACE=true`，
  否则会以 "not running in a trusted directory" 退出。
- 认证用 `GEMINI_API_KEY` 环境变量，或交互式里登录 Google 账户。

## 已知坑（本机实测）

- **别绕过启动器直接找源程序**：`gemini` 这个命令会自己处理两件事 ——
  `TERMUX_VERSION`（它捆绑的 clipboardy 在加载期检查，缺了整个 CLI 起不来）和
  首次运行的安装。直接调 `node_modules/.bin/gemini` 会撞上前者。
- 启动时会警告 `Ripgrep is not available`（它找自带的 rg）——不影响使用，
  本机的 `rg` 在 `$PREFIX/bin/rg`。
- 首次运行会联网装依赖（约一分钟），之后启动是本地调用。

## 规矩

- **不要读、不要打印任何密钥或令牌**。需要登录/换 key 时让用户自己操作。
- 会对外发布、删除文件、花钱的操作，先说清楚再动手。
