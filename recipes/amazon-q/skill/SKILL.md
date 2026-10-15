---
name: amazon-q
description: Amazon Q Developer CLI（cccodroid 组件）：AWS 官方的终端开发助手。用户提到 AWS、Amazon Q、或要在 AWS 项目里工作、查 AWS 文档时使用。
---

# Amazon Q Developer CLI（AWS）

本机装了官方的 `q`（组件启动器；程序在首次运行时从官方 CDN 取进用户私有目录）。

## 用法

```sh
q --version
q chat "解释这个部署脚本"        # 问答
q chat --no-interactive …       # 非交互（脚本/CI 用）
q doctor                        # 自检
q login                         # 登录（浏览器/设备码）
```

- 未登录时 `q chat` 会直接返回 `You are not logged in, please log in with q login`。
  **登录由用户自己完成**，不要代填凭据。
- 包内还有 `qchat` / `qterm`，本组件只提供 `q` 一个入口。

## 已知坑（本机实测）

- 它是 glibc 动态二进制，启动器负责：glibc 加载器 + 补 `libgcc_s.so.1` / `libstdc++.so.6`
  （从 Debian 的 libgcc-s1 / libstdc++6 取，sha256 钉死）。**别绕过 `q` 直接调 app/bin/q**，
  会报 `libgcc_s.so.1: cannot open shared object file`。
- 首次运行要下载约 200 MB。

## 规矩

- **不要读、不要打印任何凭据**。
- 涉及 AWS 资源的改动（部署、删除、花钱）先说清楚再动手。
