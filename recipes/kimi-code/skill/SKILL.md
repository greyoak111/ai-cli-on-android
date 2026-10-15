---
name: kimi-code
description: Kimi Code（cccodroid 组件）：月之暗面的终端编程代理，可切换多家 provider。用户提到 Kimi、月之暗面、Moonshot 时使用。
---

# Kimi Code（Moonshot）

本机装了官方的 `kimi`（组件启动器；程序在首次运行时从官方 npm 装进用户私有目录）。

## 用法

```sh
kimi --version
kimi -p "总结这个项目的结构"        # 单条非交互
kimi                              # 交互式（首次要 /login）
kimi provider list                # 看已配置的 provider
```

- 没登录/没配模型时非交互会退出并提示
  `No model configured. Run `kimi` and use /login …, or set default_model in config.toml`。
- 支持把 DeepSeek / Qwen / GLM 等作为 provider 加进来（`kimi provider catalog add …`）——
  **加 provider 要密钥，让用户自己填**。

## 已知坑（本机实测）

- 别绕过 `kimi` 启动器直接调 `node_modules/.bin/kimi`（首次安装与 npm 平台参数在启动器里）。
- 官方 install.sh 发的原生二进制是 glibc 版，在安卓上不能用；本组件走 npm 的 Node 版，开箱即用。

## 规矩

- **不要读、不要打印任何密钥或令牌**。
- 会对外发布、删除文件、花钱的操作，先说清楚再动手。
