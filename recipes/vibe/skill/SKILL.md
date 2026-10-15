---
name: vibe
description: Mistral Vibe（cccodroid 组件）：Mistral 官方的终端编程代理。用户提到 Mistral、Vibe、或用 Mistral 的模型写代码时使用。
---

# Mistral Vibe（Mistral AI）

本机装了官方的 `vibe`（组件启动器；程序在首次运行时从官方 GitHub Release 取进用户私有目录，
启动器还补了它缺的一个库）。

## 用法

```sh
vibe --version
vibe -p "总结这个仓库"              # 单条非交互
vibe --output json                 # 结构化输出
vibe                               # 交互式 TUI
```

- 认证：`MISTRAL_API_KEY` 环境变量（假值会得到 `Invalid API key (from env var MISTRAL_API_KEY)`）。
  **密钥让用户自己填**。
- 它的自动化档位（`--auto-approve` / `--smart-approve`）会让代理不经确认就改文件、跑命令 ——
  **除非用户明确要求，不要替他们开**。
- 有额度护栏：`--max-turns` / `--max-price` / `--max-tokens` / `--time-limit`。

## 已知坑（本机实测）

- 它是 PyInstaller 打的 glibc 程序，启动器负责：glibc 加载器 + 补 `libz.so.1`；
  而且因为 PyInstaller **二次启动**时会丢 `--library-path`，那个 `libz.so.1` 还要放进它的
  `_internal/`（启动器里自动做）。**别绕过 `vibe` 直接跑 app/vibe**，会报缺 libz。
- 首次运行要下载约 74 MB。

## 规矩

- **不要读、不要打印任何密钥或令牌**。
- 会对外发布、删除文件、花钱（按 token 计费）的操作，先说清楚再动手。
