# 平台坑清单

每条都带**真实症状**与**为什么会这样**。这些坑大多不报"正确"的错，或者报的错指向错误方向。

---

## 1. Node 上 `process.platform === 'android'`，npm 会静默跳过平台包

**症状**：装 Node 系 CLI 时，逻辑上该装的 `*-linux-arm64` 平台包没装，
运行时报"找不到二进制"，看起来像包本身有问题。

**原因**：安卓上的 Node 报 `process.platform === 'android'`，npm 按 android 匹配
`os`/`cpu` 字段，各家平台包写的都是 `"os": ["linux"]` → 不匹配 → **静默跳过**（optional 依赖不报错）。

**解法**：显式指定。

```sh
npm install --os=linux --cpu=arm64 <包>
```

### 1b. 平台包声明了 `libc` 时，还要再给一个 `--libc=glibc`

**症状**：加了 `--os=linux --cpu=arm64` 还是装不上平台包 —— 装完只有两三个包，
运行时报 `no platform package found`。

**原因**：有的平台包（实测：`@github/copilot-linux-arm64`）声明了 `"libc": ["glibc"]`。
npm 判断本机 libc 靠 Node 的 `process.report` —— 而安卓版 Node 的 report 里**没有**
`glibcVersionRuntime` 字段，于是 npm 把它认成 **musl**，glibc 的包就被跳过了。

**解法**：

```sh
npm install --os=linux --cpu=arm64 --libc=glibc <包>
```

（反过来，要拿 musl 变体就 `--libc=musl`。）

---

## 2. Python 的兼容 tag 里没有 manylinux，PyPI 上的 aarch64 轮子基本用不了

**症状**：`pip install <包>` 去拿 sdist 现场构建，或者干脆失败。

**原因**：安卓版 Python 的 tag 只有 `cp3xx-cp3xx-android_24_arm64_v8a` 一类，
**一个 manylinux 都没有**。PyPI 上 aarch64 的轮子几乎全是 `manylinux_2_xx_aarch64`：
- `pip debug --verbose | grep -c manylinux` → `0`（实测）

而且就算硬装，manylinux 轮子是链 **glibc** 的，bionic 的 Python 进程也加载不了。

**连带**：构建后端是 maturin / setuptools-rust 的 sdist 也没戏 —— 安卓上通常也没有 Rust 工具链
（`rustup` 不支持 `aarch64-unknown-linux-android` 作为 host）。

**解法**：Python 系 CLI 优先找**官方独立二进制**（实测 Mistral Vibe 就是这样）；
纯 Python 的包可以正常装。

---

## 3. 静态二进制：没有 `/etc/resolv.conf`，DNS 解析不了

**症状**：`failed to lookup address information: Try again` / `error connecting to …`，
看着像断网；同一时刻 `curl` 一切正常。

**原因**：安卓没有 `/etc/resolv.conf`（DNS 由 netd 通过 `getaddrinfo` 提供）。
libc 的解析器（musl/glibc）读文件；Go 的纯 Go 解析器也读文件。
而 Node、Python、curl 走 `getaddrinfo`，所以没事。

**解法**：本地 DNS 桥 —— 一个只监听回环的小代理，用"能解析的那个"（Python/系统调用）替它解析：

```sh
python3 tools/dnsproxy.py &          # 监听 127.0.0.1:18080
HTTPS_PROXY=http://127.0.0.1:18080 <程序> …
```

（注意：桥只帮**支持代理**的程序。不支持 `HTTPS_PROXY` 的静态程序需要别的手段，
比如逐字节把解析调用指向自己的实现。）

---

## 4. 静态/原生程序：没有 `/etc/ssl/certs`，TLS 验不过

**症状**：`invalid peer certificate: UnknownIssuer`（rustls）或
`x509: certificate signed by unknown authority`（Go）。

**原因**：TLS 根证书在安卓上是 `/system/etc/security/cacerts`（一目录的散文件），
而 Linux 程序默认找 `/etc/ssl/certs` 或内置 Mozilla 包。

**解法**：指一个 CA 包文件。

```sh
SSL_CERT_FILE=/path/to/cert.pem <程序> …
```

---

## 5. seccomp：启动即退，只留一行 `SIGSYS: bad system call`

**症状**：程序启动即死，只打印一行 `SIGSYS: bad system call`；或"有的子命令崩、有的正常"
（用到被拦系统调用那条路径才崩）。

**原因**：安卓给应用进程装了系统调用白名单，白名单外的直接被杀。
实际会撞上的：`clone3`（glibc ≥ 2.34 的 `pthread_create` 首选）、`faccessat2`、`openat2`、`epoll_pwait2`。

**解法**：

- 动态链接（glibc）：加载器的 `--preload` 一个把被拦调用改成 `-ENOSYS` 的小库
  （让程序走它本来就有的回退路径；**不是放宽限制**）。
- 静态二进制：`enosys-run <程序> …`（ptrace 从进程外面做同一件事，不改目标程序）。

---

## 6. glibc 加载器：四个反直觉的坑

**(a) bionic 的 `LD_PRELOAD` 会被继承进来。**
症状：`libc.so: invalid ELF header`。原因：`LD_PRELOAD` 里是 bionic 的库
（如 termux-exec），它按 bionic 的名字要 `libc.so`，而 glibc 目录里 `libc.so` 是个
**链接脚本**。→ 跑 glibc 程序前 `unset LD_PRELOAD`。

**(b) 直接执行 glibc 程序报 `No such file or directory`。**
不是文件不存在，是**解释器** `/lib/ld-linux-aarch64.so.1` 不存在。

**(c) 自我重执行的程序会报 `unrecognized option '--binary-version'` 之类。**
程序 re-exec 自己时 `argv[0]` 是 `ld.so`。→ 加载器加 `--argv0 <程序绝对路径>`。

**(d) PyInstaller 型程序二次启动后丢失 `--library-path`。**
缺的库要往它的 `_internal/` 里**再放一份**。

---

## 7. 应用商店/模拟器之外：安卓内核对 ELF 解释器的要求

安卓只接受两种可执行文件：**静态**的，或**解释器是 `/system/bin/linker64`** 的（bionic）。
所以 glibc / musl 的动态程序**必须**显式用它们自己的加载器启动，
不能指望 `execv` 直接跑（见坑 6b）。

---

## 8. 平台的"时灵时不灵"类坑（加载期检查）

有的库在**模块加载期**做平台判定，导致"某些子命令正常、某些直接崩"。
实测：Gemini CLI 捆绑的 clipboardy 在 `platform === 'android'` 时要求
`TERMUX_VERSION` 环境变量，否则抛 `You need to install Termux…`。
表现为 `--version` 正常、`--help` 崩（前者不导入它）。

**排查手法**：看报错栈指向哪个模块，然后 `rg` 那个模块里所有 `platform` / `android` 判断。

---

## 9. 给安卓编 C/C++：`statx` 报错其实是 API level 的锅

**症状**：编译一个 Linux 上很正常的 cmake 项目，卡在这么一行：

```
error: cannot initialize a member subobject of type '__u32' (aka 'unsigned int')
       with an lvalue of type 'const char *'
    |     if (statx(fd, pathname, stat_flags, stat_mask, &sxb) < 0) {
error: invalid operands to binary expression ('statx' and 'int')
```

看着完全不像"函数没声明"，像类型不匹配。

**原因**：C++ 里 `struct statx` 会顺带把 `statx` 变成一个**类型名**；
而 bionic 只在足够高的 API level 才声明同名**函数** `statx()`。
本机 clang 默认目标是 `aarch64-linux-android24`（`__ANDROID_MIN_SDK_VERSION__ = 24`），
函数声明被门控掉 → `statx(fd, pathname, …)` 被解析成"构造一个 statx 临时对象"，于是报出上面那堆怪话。

**别用 `-D__ANDROID_API__=NN` 去抬**：libc++ 只看 `__ANDROID_API__`，bionic 自己的头文件看
`__ANDROID_MIN_SDK_VERSION__`，两边判定不一致，会立刻冒出一批新的"未声明标识符"
（实测：`use of undeclared identifier 'pthread_cond_clockwait'`）。

**解法 —— 抬 target，让两边一致**：

```sh
CFLAGS="--target=aarch64-linux-android34" CXXFLAGS="--target=aarch64-linux-android34" <原构建命令>
```

实测：koffi 3.1.1（DeepSeek Harness 的依赖）的 cmake 构建，从 3 个 error 到 0 error。
设备是 Android 14 = API 34，抬到 34 是安全的。

---

## 10. 应用私有目录里**不能建硬链接**（SELinux）

**症状**：`EACCES: permission denied, link '…tmp' -> '…final'`，而同一目录下 `mv`（rename）一切正常。

**手工验证**：

```sh
$ echo x > a; ln a b
ln: failed to create hard link 'b' => 'a': Permission denied
```

`/data/user/0/<包名>/…` 与 `~` 下都一样；文件系统是 f2fs，**本身支持**硬链接 ——
是 Android 的 SELinux 策略不允许应用在自己的数据目录里建硬链接。

**语义陷阱**：用 `link()` 的程序往往是在做"**独占发布**"——link 在目标已存在时报 `EEXIST`，
程序据此判断"这一代已经写过了（返回 false）"。所以**不能**图省事换成 rename：
rename 会静默覆盖，把独占语义变成"后来者赢"。

**等价改法**：`open(path, "wx")`（独占创建，目标已存在时同样抛 `EEXIST`）+ 写入 + 落权限位。

实测：DeepSeek Harness 的会话持久化（`session.v4.jsonl.zstd` 的发布路径）。

---

## 11. Node 原生附件在安卓上没有产物 —— 三条替代路

**症状**：`host preparation failed: No usable native binding found for
node-addon-require-builtin-android-arm64 (auto)`。加载器按 `process.platform` 算出
`…-android-arm64` 后缀去找可选依赖，而上游只发布了 darwin / linux / win32 → 必然找不到，
且这条依赖常常是**没有 try/catch 的硬依赖**，直接致命。

三条路，代价从低到高：

1. **改 JS，用 Node 自带能力顶替。** `--expose-internals` 下 `require("internal/modules/…")`
   拿到的就是原生件要掏的那批内部模块（实测：某 agent 运行时校验的 6 个接口全在）。
   原生件只是"更快/更稳的入口"，不是唯一入口。
2. **用程序已有的 FFI 重写。** 如果程序本来就依赖 koffi 之类能调 libc 的 FFI，
   系统调用层面的原生件可以直接用 FFI 重写（实测：`flock(2)`，语义完全一致；
   顺带一个好处 —— flock 由内核在进程退出时自动释放，**不会有陈旧锁文件**）。
3. **自己编。** Node-API 附件不依赖 node-gyp：一条 clang 命令即可，
   头文件用 `$PREFIX/include/node`（Termux 的 node 自带 `node.h`）：

   ```sh
   c++ -shared -fPIC -pthread -std=c++17 -DNAPI_VERSION=9 \
       -I "$PREFIX/include/node" -I node_modules/node-addon-api \
       <sources...> -o build/napi/napi-v9-android-arm64/<名字>.node
   ```

   实测：245 KB、零警告、加载即用（源码公开、MIT 的情况下这条路最干净）。
