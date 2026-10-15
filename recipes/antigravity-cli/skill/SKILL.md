---
name: antigravity-cli
description: Antigravity CLI（cccodroid 组件）：Google 官方的终端代理 agy。用户提到 Antigravity、Google 的终端代理、或要换一个模型家的 CLI 试试时使用。
---

# Antigravity CLI（Google）

本机装了 Google 官方的 `agy`（组件启动器；首次运行时按官方 manifest 取安卓构建，sha512 核对）。

## 用法

```sh
agy --version
agy -p "解释这个目录"            # 单条非交互
agy                              # 交互式 TUI（可 --continue 接上次会话）
agy --help                       # 39 行用法
```

- 认证：首次运行会打印 Google 账户的 OAuth 授权链接，等你在浏览器里授权后把码贴回来。
  **不要替用户进行登录**；引导用户自己完成。
- headless/CI 场景可用 `GEMINI_API_KEY`，但需要在它的 settings.json 里把 `modelProvider`
  设为 `gemini`（只设环境变量不生效）。

## 本机情况

- 这是候选里唯一官方发**安卓构建**的 CLI，所以没有任何加载器/补库/联网适配，
  启动器只做「按 manifest 取件 + 核 sha512」。
- 二进制约 176 MB，首次运行会下载。

## 规矩

- **不要读、不要打印任何凭据或授权码**。
- 会对外发布、删除文件、花钱的操作，先说清楚再动手。
