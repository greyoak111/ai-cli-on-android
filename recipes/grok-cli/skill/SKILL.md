---
name: grok-cli
description: Grok Build（cccodroid 组件）：xAI 官方的终端编程代理。用户提到 Grok、xAI、或要用 Grok 写代码时使用。
---

# Grok Build（xAI）

本机装了官方的 `grok`（组件启动器；程序在首次运行时从官方 npm 取进用户私有目录，
启动器还负责两处安卓特有的联网修复）。

## 用法

```sh
grok --version
grok -p "解释这个模块"           # 单条非交互
grok                            # 交互式 TUI（plan / code / ask 三种模式）
grok --help                     # 148 行完整选项
```

- 认证：`XAI_API_KEY` 环境变量，或交互式里登录（SuperGrok / X Premium+ 订阅）。
  **密钥让用户自己填**。

## 启动器替你做的事（别绕过它直接调源程序）

它的二进制是**全静态**的，在安卓上启动没问题，但联网会撞两堵墙：

1. **DNS**：静态 musl 只读 `/etc/resolv.conf`，安卓没有 → 启动器起本地桥（`dnsproxy.py`）
   并导出 `HTTPS_PROXY`/`HTTP_PROXY`；
2. **CA**：安卓没有 `/etc/ssl/certs` → 启动器导出 `SSL_CERT_FILE`。

所以不要 `unset HTTPS_PROXY` 之后再跑，也不要绕过 `grok` 直接执行 pack 里的二进制。
排查联网问题看 `~/.local/share/cccodroid/ai-cli/grok-cli/dnsproxy.log`。

## 规矩

- **不要读、不要打印任何密钥或令牌**。
- 会对外发布、删除文件、花钱（按 token 计费）的操作，先说清楚再动手。
