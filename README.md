# AI CLIs on Android · survey and general method

**English** · [简体中文](README.zh-CN.md)

> What happens when you take the command-line AI agents shipped by the major model vendors and run them
> **natively on an Android phone** — 13 vendors tested, plus the thin compatibility layer that makes them run.
>
> **No vendor binaries live in this repository.** Only methods, scripts and test records; install everything
> from the vendors' own channels. Names and trademarks belong to their owners.

## The one-line conclusion

An Android phone is already Linux. Once you deal with the one question — *which Linux is this program built for?* —
every vendor's CLI runs natively: no root, no container, no modified system.

Tested on: Android 14 (SDK 34) · aarch64 · non-root · ordinary app uid ·
Node 26 / Python 3.14 / a glibc runtime (`$PREFIX/glibc`).

## Results (measured 2026-10-15)

| Vendor | CLI | Distribution form | Result | Adaptation needed |
|---|---|---|---|---|
| Google | Antigravity CLI `agy` 1.3.5 | **official Android/bionic build** | ✅ runs as-is | none |
| Anthropic | Claude Code 2.1.292 | glibc, dynamic | ✅ fully working | glibc loader + seccomp shim |
| OpenAI | Codex CLI 0.162.1 | static musl (254 MB) | ✅ reached the real API | DNS bridge + CA bundle |
| xAI | Grok Build 0.1.220 | brotli-packed static ELF | ✅ reached the real API | unpack + DNS bridge + CA |
| Microsoft | GitHub Copilot CLI 1.0.98 | glibc + C++ | ✅ **real model answer** | loader + `libstdc++`/`libgcc_s` |
| Microsoft | GitHub Copilot CLI (musl) | musl, dynamic | ✅ starts | Alpine musl loader + seccomp |
| Google | Gemini CLI 0.64.0 | Node | ✅ reached the real API | `TERMUX_VERSION=1` |
| Alibaba | Qwen Code 0.25.1 | Node | ✅ up to auth | none |
| Moonshot | Kimi Code 2.2.0 | Node | ✅ up to auth | none |
| Tencent | CodeBuddy 2.167.0 | Node | ✅ up to auth | none |
| Mistral | Vibe 2.26.1 | PyInstaller / glibc | ✅ reached the real API | loader + `libz` |
| Amazon | Q Developer CLI 1.19.7 | glibc + C++ | ✅ up to auth | loader + C++ libs |
| Z.ai (Zhipu) | no standalone CLI | — | helper works | — |
| DeepSeek | **no official CLI** | — | — | point another CLI at its API |

"up to auth" = starts fully, reads config, makes the network call and is answered by the server
(with a dummy key you get 401/400 — the pipeline is complete). Per-CLI detail: [`docs/survey.md`](docs/survey.md).

## Three things to understand

**1. The distribution form decides everything.** "A Linux arm64 CLI" comes in five shapes, each needing
a different treatment:

| Form | Runs directly? | Adaptation |
|---|---|---|
| Official Android build | kernel loads it | none |
| Node / plain script | yes, with node | platform checks inside the program |
| Static binary (musl/Go) | kernel loads it | needs DNS + CA to reach the network |
| glibc, dynamic | no (no `/lib/ld-linux-aarch64.so.1`) | swap in a glibc loader |
| musl, dynamic | no (no `/lib/ld-musl-aarch64.so.1`) | swap in a musl loader |

**2. Swapping the loader is more than calling `ld.so`.** Android's seccomp allow-list, bionic's inherited
`LD_PRELOAD`, the `libc.so` that is actually a linker script, `--library-path` lost when a program re-execs
itself — each of them fails in ways that look nothing like "a loader problem".
Checklist: [`docs/pitfalls.md`](docs/pitfalls.md).

**3. "It starts" and "it reaches the network" are two different problems.** Static binaries run fine on
Android and then die on two environment facts: there is no `/etc/resolv.conf` (DNS) and no `/etc/ssl/certs`
(TLS roots). Both surface as "looks like the network is down". Fixes: [`docs/methods.md`](docs/methods.md).

## Why this matters

- **Execution moves back to the device.** Inference stays in the cloud; code, files and toolchain stay on
  your phone — no uploading a repository into somebody's ephemeral container just to let the model run it.
- **Not bound to one vendor.** The same method carries any CLI; the same holds on the model side
  (every vendor's Anthropic/OpenAI-compatible endpoint can be wired up).
- **The environment persists.** Installed tools, config and sessions stay, instead of dying with a sandbox.

## Repository layout

```
docs/survey.md     the 13 vendors, one by one: source, shortest repro command, evidence, notes
docs/matrix.md     form → adaptation matrix, and how to classify a CLI you just downloaded
docs/methods.md    the three loader methods + DNS bridge + CA + seccomp shim
docs/pitfalls.md   platform pitfalls, each with the real error message
tools/glibc-run    generic glibc launcher (--argv0, seccomp shim included)
tools/musl-run     generic musl launcher (Alpine loader + enosys)
tools/probe.sh     probe harness: one command in, verdict and log out
tools/dnsproxy.py  loopback-only DNS bridge for static binaries
tools/README.md    how to use them, and where the extra libs (libz / libstdc++ / musl) come from
recipes/           the tested CLIs packaged as cccodroid component-market recipes (launcher style, drafts)
evidence/          short excerpts of the actual runs behind the table above
```

## Reproducing (Codex as the example)

```sh
# 1. get the official linux-arm64 package (the npm platform package)
npm pack @openai/codex@<version>-linux-arm64 && tar xzf *.tgz
# 2. start the DNS bridge and point the program at a CA bundle, then run
python3 tools/dnsproxy.py &
HTTPS_PROXY=http://127.0.0.1:18080 SSL_CERT_FILE=<ca-bundle> \
  ./package/vendor/aarch64-unknown-linux-musl/bin/codex --version
```

glibc family (Copilot / Amazon Q / Vibe):

```sh
tools/glibc-run -L ./libs <program> --version
```

## Recipes (component market)

`recipes/` turns the tested CLIs into [cccodroid](https://github.com/greyoak111/cccodroid) component-market
recipes — installable from the app's Extensions page, each shipping a skill so the agent knows how to drive it.
The pattern is *launcher style*: no vendor binary is bundled or redistributed; the launcher fetches the
program from the vendor's own channel on first run (npm integrity, or pinned URL + sha256), and carries the
Android-specific fixes (DNS bridge, CA, loader, missing libs) inside itself.

## License and notices

- This repository: Apache-2.0.
- It contains methods, scripts and test records only. **No vendor binaries are packaged or mirrored** —
  install from each vendor's official channel and honour their licenses and terms.
- Vendor, product and CLI names are trademarks of their respective owners and are used here only to
  identify what was tested.
