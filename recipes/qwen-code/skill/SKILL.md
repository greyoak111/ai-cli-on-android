---
name: qwen-code
description: Qwen Code（cccodroid 组件）：阿里通义千问的终端编程代理。用户提到 Qwen、通义千问、或用国产模型写代码时使用。
---

# Qwen Code（阿里通义千问）

本机装了官方的 `qwen`（组件启动器；程序在首次运行时从官方 npm 装进用户私有目录）。

## 用法

```sh
qwen --version
qwen -p "总结这个项目的结构"      # 非交互
qwen                             # 交互式
```

- **非交互模式要先配认证方式**，否则直接退出并提示
  `No auth type is selected. Please configure an auth type (e.g. via settings or --auth-type)`。
  认证方式由用户在交互式里选，或写进它的配置文件；**不要让 Claude 代填密钥**。
- 它也可以指向 OpenAI / Anthropic / Gemini 兼容端点（`--auth-type` 与设置里配）。

## 已知坑（本机实测）

- 别绕过 `qwen` 启动器直接调 `node_modules/.bin/qwen`：启动器负责首次安装，
  以及 npm 的平台参数（安卓上不加 `--os=linux --cpu=arm64` 会装不全）。
- 首次运行会联网装依赖（约一分钟）。

## 规矩

- **不要读、不要打印任何密钥或令牌**。
- 会对外发布、删除文件、花钱的操作，先说清楚再动手。
