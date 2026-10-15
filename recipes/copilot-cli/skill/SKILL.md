---
name: copilot-cli
description: GitHub Copilot CLI（cccodroid 组件）：GitHub 官方的终端编程代理。用户提到 Copilot、GitHub 的 AI、或要在 GitHub 仓库里用 AI 改代码时使用。
---

# GitHub Copilot CLI（微软）

本机装了官方的 `copilot`（组件启动器；程序在首次运行时从官方 npm 装进用户私有目录，
并已处理好它的三处安卓适配）。

## 用法

```sh
copilot --version
copilot -p "给这个函数补测试"        # 非交互（脚本/自动化）
copilot --help                       # 完整选项（含权限/沙箱相关）
copilot                              # 交互式
```

- 认证：**优先复用本机 gh 的登录**（`gh auth status` 看有没有）。没有 gh 登录时，
  在交互式里 `/login` 走 GitHub 授权。**不要让 Claude 代填或转述令牌**。
- 会话可以 `copilot --resume=<id>` 接着跑。

## 已知坑（本机实测）

- **别绕过 `copilot` 启动器**直接调 `node_modules/.bin/copilot`：那是它的 JS 壳，
  在安卓上按 `process.platform` 拼包名（会拼出不存在的 `@github/copilot-android`）→
  报 `no platform package found`。启动器直接跑平台二进制。
- 平台二进制是 glibc 动态链接的，启动器负责加载器 + `libstdc++.so.6` / `libgcc_s.so.1`
  （从 Debian 的 deb 取，sha256 钉死）。
- 首次运行要下载约 120 MB。

## 规矩

- **不要读、不要打印任何密钥或令牌**。
- 会对外发布、删除文件、花钱（AI Credits）的操作，先说清楚再动手。
