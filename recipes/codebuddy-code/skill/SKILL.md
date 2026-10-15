---
name: codebuddy-code
description: CodeBuddy Code（cccodroid 组件）：腾讯云 CodeBuddy 的终端编程代理。用户提到 CodeBuddy、腾讯、或国内云端编程助手时使用。
---

# CodeBuddy Code（腾讯）

本机装了官方的 `codebuddy`（组件启动器；程序在首次运行时从官方 npm 装进用户私有目录）。

## 用法

```sh
codebuddy --version
codebuddy -p "总结这个项目"       # 非交互（--print）
codebuddy                        # 交互式
```

- 未登录时非交互会直接返回 `Authentication required. Please use /login command to sign in`。
  **登录由用户在交互式里做**，不要代填账号或密钥。
- 同包还提供短命令 `cbc`（本组件只装 `codebuddy` 一个入口，需要 `cbc` 可自己 `ln -s`）。

## 已知坑（本机实测）

- 别绕过启动器直接调源程序：首次安装与 npm 平台参数（`--os=linux --cpu=arm64`）在启动器里。
- 首次运行会联网装依赖（约一分钟）。

## 规矩

- **不要读、不要打印任何密钥或令牌**。
- 它的账号可能是团队/企业席位，涉及用量与账单的操作先问用户。
