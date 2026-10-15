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

## 这个目录里已写的配方

| id | 命令 | 形态 | 特殊处理 |
|---|---|---|---|
| `gemini-cli` | `gemini` | Node | `TERMUX_VERSION=1`（clipboardy 加载期检查） |
| `qwen-code` | `qwen` | Node | 无 |
| `kimi-code` | `kimi` | Node | 无 |
| `codebuddy-code` | `codebuddy` | Node | 无 |
| `codex-cli` | `codex` | 静态 musl | 组件自带 DNS 桥 `dnsproxy.py` + 指 CA 包 |

## 尚未覆盖

- **copilot / vibe / amazon-q**：glibc 动态或 PyInstaller 形态，要配 glibc 加载器与额外库
  （`libstdc++` / `libgcc_s` / `libz`），打包形态与这里不同，见 `../docs/matrix.md` D/F 节。
- **antigravity**：Google 官方就有安卓构建，组件只需薄薄一层（或让用户跑官方安装脚本）。
- **各家交互式 TUI 的完整体验**：尚未在真机上逐项验证。
