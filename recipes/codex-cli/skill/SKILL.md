---
name: codex-cli
description: Codex CLI（cccodroid 组件）：OpenAI 官方的终端编程代理，可 headless 跑。用户提到 Codex、OpenAI 的命令行、或要用 GPT 写代码时使用。
---

# Codex CLI（OpenAI）

本机装了官方的 `codex`（组件启动器；程序在首次运行时从官方 npm 装进用户私有目录，
**启动器还负责两件安卓特有的联网修复**，见下）。

## 用法

```sh
codex --version
codex exec "给这个函数补测试"          # 非交互
codex                                # 交互式
```

- 非交互跑先注意工作目录：不在 git 仓库里时要加 `--skip-git-repo-check`，
  否则它退出并提示 `Not inside a trusted directory …`。
- 认证：`codex login`（浏览器/设备码）或 `OPENAI_API_KEY`。**密钥让用户自己填**。

## 启动器替你做的事（别绕过它直接调源程序）

它的二进制是**全静态 musl**，在安卓上启动没问题，但联网会撞两堵墙——启动器都补好了：

1. **DNS**：静态 musl 只读 `/etc/resolv.conf`，安卓没有这个文件 →
   启动器起一个只监听 127.0.0.1 的本地桥（`dnsproxy.py`），导出 `HTTPS_PROXY`/`HTTP_PROXY`；
2. **CA**：安卓没有 `/etc/ssl/certs` → 启动器导出 `SSL_CERT_FILE` 指向工具包自带的 CA 包。

所以：**不要** `unset HTTPS_PROXY` 之后再跑 codex，也不要绕过 `codex` 直接执行
`node_modules/.bin/codex`（那样会退化成"解析不了域名/证书验不过"）。

排查这类问题时看 `~/.local/share/cccodroid/ai-cli/codex-cli/dnsproxy.log`。

## 规矩

- **不要读、不要打印任何密钥或令牌**。
- 会对外发布、删除文件、花钱的操作，先说清楚再动手。
