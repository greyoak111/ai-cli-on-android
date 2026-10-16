# AI CLIs on Android · survey and general method

**English** · [简体中文](README.zh-CN.md)

> Notes from running the command-line AI agents of 13 model vendors natively on one Android phone,
> and the compatibility layer that got them running.
>
> No vendor binaries live in this repository: only methods, scripts and test records. Install everything
> from the vendors' own channels. Names and trademarks belong to their owners.

## Summary

Android is Linux underneath. Every CLI we tried started natively on the phone once we dealt with one question,
*which Linux was this program built for?*, with no root, container or modified system. How far each one got
differs (see the table). Most were only checked with a dummy key up to the point where the server answers;
only Claude Code and GitHub Copilot were used with real credentials.

Tested on one device: Android 14 (SDK 34) · aarch64 · non-root · ordinary app uid ·
Node 26 / Python 3.14 / a glibc runtime (`$PREFIX/glibc`). Other devices and versions may behave differently.

## Results (2026-10-15)

| Vendor | CLI | Distribution form | How far it got | Adaptation needed |
|---|---|---|---|---|
| Google | Antigravity CLI `agy` 1.3.5 | official Android (bionic) build | starts, stops at OAuth sign-in | none |
| Anthropic | Claude Code 2.1.292 | glibc, dynamic | in daily use | glibc loader + seccomp shim |
| OpenAI | Codex CLI 0.162.1 | static musl (254 MB) | request reached the API (dummy key, 401) | DNS bridge + CA bundle |
| xAI | Grok Build 0.1.220 | brotli-packed static ELF | request reached the API (dummy key, 400) | unpack + DNS bridge + CA |
| Microsoft | GitHub Copilot CLI 1.0.98 | glibc + C++ | model reply with real credentials | loader + `libstdc++`/`libgcc_s` |
| Microsoft | GitHub Copilot CLI (musl) | musl, dynamic | starts (`--version`) | Alpine musl loader + seccomp shim |
| Google | Gemini CLI 0.64.0 | Node | request reached the API (dummy key, 400) | `TERMUX_VERSION=1` |
| Alibaba | Qwen Code 0.25.1 | Node | starts, stops at auth | none |
| Moonshot | Kimi Code 2.2.0 | Node | starts, stops at auth | none |
| Tencent | CodeBuddy 2.167.0 | Node | starts, stops at auth | none |
| Mistral | Vibe 2.26.1 | PyInstaller / glibc | request reached the API (dummy key) | loader + `libz` |
| Amazon | Q Developer CLI 1.19.7 | glibc + C++ | starts, stops at sign-in | loader + C++ libs |
| Z.ai (Zhipu) | no standalone CLI; official helper | Node | helper runs | none |
| DeepSeek | DeepSeek Harness `dsh` 0.2.0-rc.2 | Node + 3 native addons | one full turn against a local mock endpoint | JS fallbacks for the addons; hard link → exclusive create |

"Request reached the API" means the program started, read its config, sent the request and got a normal
answer from the server (a dummy key gets 401/400, so only the credential is missing). The DeepSeek row used no
real model: the endpoint pointed at a local mock, which showed the complete request it sends (system prompt,
file policy, tool list). See section 14 of [`docs/survey.md`](docs/survey.md), which has the per-vendor details.

## Three observations

**1. The distribution form decides the adaptation.** "Linux arm64" covers several different shapes,
each handled differently:

| Form | Runs directly? | Adaptation |
|---|---|---|
| Official Android build | kernel loads it | none |
| Node / plain script | yes, with node | watch for platform checks inside the program |
| Node/Python + native addons | the main program does | the addons ship no android build: JS fallback / FFI / build it yourself |
| Static binary (musl/Go) | kernel loads it | needs DNS + CA to reach the network |
| glibc, dynamic | no (no `/lib/ld-linux-aarch64.so.1`) | swap in a glibc loader |
| musl, dynamic | no (no `/lib/ld-musl-aarch64.so.1`) | swap in a musl loader |

The full classification and how to tell which one you have: [`docs/matrix.md`](docs/matrix.md).

**2. Swapping the loader is more than calling `ld.so`.** Android's seccomp allow-list, bionic's inherited
`LD_PRELOAD`, a `libc.so` that is actually a linker script, `--library-path` lost when a program re-execs
itself: each of these fails in ways that don't look like a loader problem.
Checklist: [`docs/pitfalls.md`](docs/pitfalls.md).

**3. Starting and reaching the network are separate problems.** Static binaries start fine on Android and
then often stop at two environment gaps: there is no `/etc/resolv.conf` (DNS) and no `/etc/ssl/certs`
(TLS roots). Both look like the network is down. Fixes: [`docs/methods.md`](docs/methods.md).

## Why

We wanted to know whether letting an AI agent work locally on a phone only works for one vendor.
It doesn't: the method carries over. Inference stays in the cloud; code, files and toolchain stay on your
own device, and the environment persists between sessions.

## Scope and limits

- Tested on one device only. Distribution forms change between versions; every result is dated.
- Most CLIs were only checked with a dummy key up to a working connection, not used with a real account.
- Interactive TUIs were not exercised in detail.

## Repository layout

```
docs/survey.md     the vendors one by one: source, shortest repro command, output, notes
docs/matrix.md     form → adaptation matrix, and how to classify a CLI you just downloaded
docs/methods.md    loader methods + DNS bridge + CA + seccomp shim
docs/pitfalls.md   platform pitfalls, each with the real error message
tools/glibc-run    generic glibc launcher (--argv0, seccomp shim included)
tools/musl-run     generic musl launcher (Alpine loader + enosys)
tools/probe.sh     probe harness: runs one command, logs the output
tools/dnsproxy.py  loopback-only DNS bridge for static binaries
tools/README.md    how to use them, and where the extra libs (libz / libstdc++ / musl) come from
recipes/           example cccodroid component recipes for these CLIs (launcher style, 10); kept as methodology, not planned for release
evidence/          excerpts of the actual runs behind the table, for checking
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

## Recipes

`recipes/` shows what it would take to package each tested CLI as a
[cccodroid](https://github.com/greyoak111/cccodroid) component recipe. They are launcher style: nothing is
redistributed; the launcher fetches from the vendor's own channel on first run and carries the
Android-specific fixes. They are kept as a worked example of the pattern and its pitfalls, not as a plan to
ship them.

## License and notices

- This repository: Apache-2.0.
- It contains methods, scripts and test records only. No vendor binaries are packaged or mirrored;
  install from each vendor's official channel and follow their licenses and terms.
- Vendor, product and CLI names are trademarks of their respective owners and are used here only to
  identify what was tested.
