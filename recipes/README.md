# AI CLI 组件配方（草稿）

把 [`ai-cli-on-android`](../) 里实测过的各家 CLI，做成 cccodroid 组件市场的形态：
装完就有命令可用，并带一条 skill 告诉 Claude 怎么用它。

> 状态：**草稿**，尚未提交到 `cccodroid-components`。进市场前需要 CI 审计 + 真机验证。

## 形态：启动器型（launcher），不打包二进制

市场现有组件（gh、llama-cpp……）的做法是「把 Termux 的包改前缀后打进市场包」。
**这批 AI CLI 不能照做**：

1. **许可**：多数 CLI 即使源码开源（Apache-2.0），其 npm 分发件也常带自己的条款；
   把二进制塞进市场 Release 等于再分发。实测中还有 npm 包明写 `Proprietary` 的。
2. **体积与节奏**：codex 单个二进制 254 MB；各家迭代以周计，打进包就立刻过时。

所以这里的配方是**启动器型**：

- 组件只装两样东西：一个薄启动脚本（`usr/bin/<命令>`）+ 一条 skill（`skill/SKILL.md`）；
- 真正的程序由脚本在**用户机器上首次运行时**从官方渠道（npm）取，
  装进用户私有目录 `~/.local/share/cccodroid/ai-cli/<id>/`，之后直接复用；
- 版本在配方里**钉死**（可用环境变量覆盖），升级 = 改版本号重发一版。

市场 schema 的硬性要求照样满足：`roots` 非空（填底座已有的 `nodejs`，不会被重复打包）、
`bin` 至少一个、`selftest` 一条；版本由 `version` 字段自己指定（不跟 `roots[0]` 走）。
`kind` 仍是 `termux`（产物落在 `$PREFIX` 下）。

## 许可对照（2026-10-15 查证）

| CLI | 分发渠道 | 许可 | 结论 |
|---|---|---|---|
| Gemini CLI | npm `@google/gemini-cli` | Apache-2.0 | 可打包，但仍走启动器（更新快） |
| Qwen Code | npm `@qwen-code/qwen-code` | Apache-2.0（仓库） | 同上 |
| Kimi Code | npm `@moonshot-ai/kimi-code` | MIT | 同上 |
| CodeBuddy Code | npm `@tencent-ai/codebuddy-code` | `SEE LICENSE IN README.md`（专有） | **只能启动器** |
| Codex CLI | npm `@openai/codex` | Apache-2.0 | 启动器（二进制 254 MB，不值得打包） |
| GitHub Copilot CLI | npm `@github/copilot` | `NOASSERTION`（专有） | 启动器 |
| Grok Build | npm `@xai-official/grok-linux-arm64` | 包内声明 `Proprietary` | 启动器 |
| Mistral Vibe | GitHub Releases | Apache-2.0 | 启动器（PyInstaller 包，74 MB） |
| Amazon Q CLI | 官方 zip | Apache-2.0 | 启动器 |
| Antigravity CLI | 官方安装脚本 | 专有 | 直接跑官方安装器（它自己有安卓构建） |

## 这个目录里已写的配方（10 个）

| id | 命令 | 形态 | 特殊处理 |
|---|---|---|---|
| `gemini-cli` | `gemini` | Node | `TERMUX_VERSION=1`（clipboardy 加载期检查） |
| `qwen-code` | `qwen` | Node | 无 |
| `kimi-code` | `kimi` | Node | 无 |
| `codebuddy-code` | `codebuddy` | Node | 无 |
| `codex-cli` | `codex` | 静态 musl | 自带 DNS 桥 + CA 包 |
| `grok-cli` | `grok` | brotli → 静态 ELF | npm pack 后就地解 brotli；DNS 桥 + CA |
| `copilot-cli` | `copilot` | glibc + C++ | npm 要 `--libc=glibc`；绕过 JS 壳直调平台二进制；补 libstdc++/libgcc_s |
| `vibe` | `vibe` | PyInstaller | 取官方 Release zip（sha256）；补 libz，并再拷一份进 `_internal/` |
| `amazon-q` | `q` | glibc + C++ | 版本化 URL（sha256）；补 libgcc_s/libstdc++ |
| `antigravity-cli` | `agy` | **官方安卓构建** | 只做「按 manifest 取件 + 核 sha512」 |

共同点：**都不打包厂商二进制**；取件要么走 npm（自带完整性校验），要么走钉死 URL+sha256；
缺的 glibc 库从 Debian 的 deb 里按成员抽出（sha256 钉死）。

## 验证状态（2026-10-15，真机 Android 14 / aarch64）

- **格式**：10 个配方全部通过 `cccodroid-components` 的 `tools/check-recipes.mjs`。
- **端到端**（预置/真实路径都跑过）：
  - `codex`：启动器 → `codex-cli 0.162.1`；再跑 `exec` → **打到 api.openai.com 得 401**（假密钥）
  - `grok`：启动器 → `grok 0.1.220`
  - `copilot`：npm `--libc=glibc` + 直调平台二进制 → `GitHub Copilot CLI 1.0.98`（此前用同一二进制跑出过真实回复）
  - `gemini`：首装 → `0.64.0`；二次调用 `--help` 正常；**对照组**（绕过启动器）复现 clipboardy 的 Termux 报错
  - `vibe` → `vibe 2.26.1`；`q` → `q 1.19.7`；`qwen` → `0.25.1`；`kimi` → `2.2.0`；`codebuddy` → `2.167.0`
  - `agy`：安装器用**真实 176 MB 官方包**跑通（sha512 核对），改动一个字节即失败且零落地
- 取件器 `fetch.py`：zip 整包/成员、deb 成员、幂等、**篡改即失败** 都单独测过。

## 已知取舍

- `fetch.py` 在 copilot / vibe / amazon-q 三个配方里各有一份副本（配方设计上要自包含）。
  如果这个形态被接受，值得抽成一个公共的 `ai-cli-runtime` 组件，其它配方 `requires` 它。
- 各家的**交互式 TUI 完整体验**尚未逐项验证（本仓库只验到"链路全通/命令能跑"）。
