# 辅助工具评估：把外部工具接到多角色流程上

> 2026-11-20 复核（feature `toolchain-fixups`，C003 再修正一次判据）。目的：判断这 5 个工具值不值得接、接到哪个角色、有什么代价。
> 结论一句话：**Graphify 已可用（已接到角色）；Mnemon 三件套（CLI + Space + Documents 检索）实测已闭环，`providers: []` 是设计如此不是故障、检索是纯词法（无向量）；Stop That Shit 已装上且宿主半已热加载（`include:sts-bridge` → `enabled=true` / `fiberPhase=active`，**不需要重启**），真拦截仍要用户以 `$stop-that-shit review --` 首行武装；GitNexus 图查询、FTS 与 `detect_changes` 均可用（**必须走 wrapper**，实测 `bm25=170.4`、无 FTS 警告）；agentmem 与 Mnemon 重叠。**

> **2026-11-22 A-20 迁移**：`graphify` / `mnemon` / `agentmem` / `gitnexus` / `sts` 五个工具目录已统一搬到 `D:\Tools`（本文所有路径均为迁移后现值）；原根目录下只留 `graphify` 的 Junction 兜底 15 个 exe 内嵌的旧 shebang。顺序与坑见 `ops/lessons.md` L025。

## 1. 现状与落点

| 工具 | 是什么 | 本机状态 | 接到哪个角色 / 环节 | 许可 / 风险 | 建议 |
|---|---|---|---|---|---|
| **Graphify** 0.9.112 | 代码/文档知识图谱；tree-sitter AST（免费本地）+ 可选模型做语义 | ✅ 已装：`<graphify-tools>`，MCP 已挂（14 个工具），当前图谱 2742 节点 / 5424 边 | planner 读现状与影响面；executor 改前查调用链；verifier 定回归范围；Lead 做架构导航 | MIT；本地，代码不出机；文档/图片语义提取要模型 key | **已接线**（见第 2 节） |
| **Mnemon** 0.5.50 | 分层记忆：运行时常驻 USER/MEMORY、项目文档、Memory Spaces（本地 SQLite 或 8 种 Provider） | ✅ 插件 `dsh-mnemon@0.5.50` 已装（**版本口径**：本文档说 mnemon 版本一律指 profile 实装版本 `0.5.50`，读 `<profile>\node_modules\dsh-mnemon\package.json`；`D:\Tools\mnemon\mnemon.exe --version` 自报 `0.2.13` 是 **CLI 自身**版本，不同层，不要拿两者对比）；宿主能找到 CLI（`commandFound=true`）；1 个 Memory Space `default`（Provider `mnemon-native`）`active+healthy`；Documents 词法检索实测命中（`total=1`、`score=28`） | 跨会话记忆：需求约束、用户偏好、项目决策；Lead/planner 起草前先 recall | MIT；本地。**`providers: []` 不是故障**：该数组只列「非 native 的外部 Provider」，只用 Mnemon Native 时恒为空（判据见 §5） | **已可用**（判据已更正，别再拿 `providers≥1` 当门槛） |
| **Stop That Shit** 0.2.6 | 任务边界 Guard：`review` 只读、`files=` 锁范围、`deps/hash` 审批、`agents=N` 子代理预算；附 Skill 做工程判断 | ✅ 已装且**已热加载**：直装被 `engines.dsh=0.2.2-rc.3` 拒装 → **用户 2026-11-20 批准版本豁免** → `set_version_exemption` + `dsh plugin --profile desktop add` → 宿主 loader 里 `include:sts-bridge`（`stop-that-shit-dsh`）`enabled=true` / `fiberPhase=active`，**没有重启也已经加载**（典型：本会话已在收到它的 watch-only 注入） | **executor 越界硬拦**（补 `write_scopes` 只是建议的洞）；verifier 只读复核；Lead 用 `agents=N` 控子代理数 | MIT；**preview**：默认 OBSERVING，收到 `$stop-that-shit` 指令才 ARMED；review 模式会真的拒写，可能误伤 | **已加载但未武装**：要真拦截得由用户在会话首行写 `$stop-that-shit review -- …`；武装后被拒的命令形态见 §3.1 |
| **GitNexus** 1.6.12 | 符号/调用/执行流知识图 + MCP（impact / trace / detect_changes / rename） | ✅ 已装 `<gitnexus-tools>`；`weekly-report-dev` 索引 590 节点 / 1751 边，`impact -u` 可用；**FTS 已修复**：`analyze --repair-fts --skip-git` 成功 → `query` 不再报 `FTS indexes missing`／`FTS extension failed`，实测 `bm25=170.4`（须走 wrapper `<gitnexus-tools>\gitnexus.cmd`，裸命令会退回 `FTS extension failed`）；`detect_changes` 在 git 仓库里实测出受影响符号（C003 E14） | executor 改前 `impact`、verifier 用 `detect_changes` 看 diff 影响面 | **PolyForm Noncommercial**：个人/研究可用，商用需授权；索引/向量可配远程 | **可用**；前置条件与命令形态见 §5.2 |
| **agentmem** | 全机 Agent 会话历史的只读 MCP：跨 Codex/Claude/DSH 检索、insights | ⬜ 未装；Python 3.12 + pip 可用，需 `pip install zstandard` | Lead 查「上次是怎么解决的」；跨 CLI 记忆 | MIT；本地、写入时脱敏、只读查询；但**会索引全机会话**（隐私自查）、`connect` 会改 MCP 配置（有备份） | **可选**；与 Mnemon 重叠，除非确实要跨 CLI 记忆 |

## 2. Graphify 接线（已生效）

MCP 工具：`query_graph` / `get_node` / `get_neighbors` / `god_nodes` / `shortest_path` / `get_community` / `graph_stats`。
建图（每个仓库一次，代码部分免费本地）：

```powershell
graphify .                 # 默认输出 graphify-out/
graphify . --update        # 只处理改动文件
graphify . --mcp           # 需要时自起 MCP stdio
```

用法约定（已写进角色说明书）：

- **planner**：先 `query_graph "<模块名>"` 看现状，别逐个文件读；`shortest_path A B` 找两个模块的依赖路径。
- **executor**：改前 `get_neighbors <符号>` 看调用方；改后把受影响文件写进候选清单。
- **verifier**：用 `god_nodes` / `get_neighbors` 定回归范围，避免「只测了改的那一个」。
- **Lead**：评审时用 `shortest_path` 解释「为什么改 A 会连到 B」。
- 图谱是**旁证**，不是凭证：候选真相仍以 `manifest.json` 的 sha256 为准。

## 3. Stop That Shit 试用方案（已装上、已加载、**未武装**）

**现状先说清**（2026-11-20 C003 复核，别再照旧写「待重启生效」）：`dsh plugin --profile desktop add` 之后宿主 loader 里已有 `include:sts-bridge`（`stop-that-shit-dsh`），`enabled=true`、`fiberPhase=active`——**宿主半已经加载，不需要重启**。装完没重启也能用，原因见 `ops/host-restart-sop.md`：这个包走的是 bundle 补丁层，热加载即可。`fiberPhase=active` 只说明「适配器在跑」，**不等于「已经在拦」**：默认 OBSERVING，要真拦截得由用户武装。

1. 装件（已完成，留档）：下载 release 资产 `stop-that-shit-dsh-0.2.6.tgz`（80KB）→ `dsh plugin --profile desktop add <tgz>`。**不要为它重启 DSH**，除非 `plugin_manager list_plugins` 里 `include:sts-bridge` 不是 `active`。
2. 武装（**只有用户能做**）：在会话**首行**写
   ```
   $stop-that-shit review lock files=src/** -- 只读审查本次候选，不要改任何文件。
   ```
   验证：写 `src/` 之外被拒（拿到宿主 denial 原文）；再 `$stop-that-shit change -- ...` 切回可写。
3. 观察一周：误伤率（正常改动被拒）、与 `subagent`/`workflow` 的兼容（`agents=N`）、与我们的 `audit` 是否重复。
4. 不满意：见 §6 的正确回滚（**不要整份还原 `package.json`**）。

**不建议**直接装到主力 profile 后立刻在所有项目启用：Guard 是 preview，且 review 模式的拒写会打断执行线程。

### 3.1 武装后哪些命令形态会被拒（2026-11-20 实测踩坑）

`review` 契约下判定走 `stop-that-shit-dsh/src/shell-analysis.cjs` 的**静态**分析。只读白名单**不在本文档维护**——它的唯一来源是那个文件里的两个常量，本文档只给提取命令，不再抄条目（抄一份就会漂一份）：

| 常量 | 含义 |
|---|---|
| `READ_POWERSHELL_COMMANDS` | PowerShell 只读 cmdlet 白名单 |
| `READ_SHELL_COMMANDS` | 上面那组 **+** 若干 unix 只读命令（`...READ_POWERSHELL_COMMANDS` 展开后追加） |

```powershell
Get-Content "~/.dsh\profiles\desktop\node_modules\stop-that-shit-dsh\src\shell-analysis.cjs" |
  Select-String -Pattern 'READ_(POWERSHELL|SHELL)_COMMANDS\s*=' -Context 0,4
```

**`READ_SHELL_COMMANDS` 实际追加的 11 条命令**（2026-11-20 用上面那条命令从 `stop-that-shit-dsh@0.2.6` 源码 `shell-analysis.cjs` 提取，不是手抄记忆）：

| # | 命令 | # | 命令 | # | 命令 |
|---|---|---|---|---|---|
| 1 | `rg` | 5 | `ls` | 9 | `tail` |
| 2 | `grep` | 6 | `dir` | 10 | `wc` |
| 3 | `findstr` | 7 | `pwd` | 11 | `type` |
| 4 | `cat` | 8 | `head` | | |

即：`READ_SHELL_COMMANDS = READ_POWERSHELL_COMMANDS ∪ {rg, grep, findstr, cat, ls, dir, pwd, head, tail, wc, type}`。这 11 条**只**在命令名这一层被放行（`classifyCommandArguments` 命中 `READ_SHELL_COMMANDS.has(name)` 就返回 `read`）；`rg` 另走 `classifyRipgrepArguments` 逐参数校验，`npm/pnpm/yarn add|install|remove|uninstall|publish`、`pip install`、`git add|commit|push|…` 等先被判 `write`。

**管道规则（显式写清，别再靠猜）**：**管道的每个段落都必须在白名单内**——`analyzeShell` 用 `staticShellCommands` 把一条命令切成多段，再交给 `combineClassifications` 合并：任一段是 `write` → 整条 `write`；**所有**段都是 `read` 才 `read`；**只要有一段不在白名单（`unknown`），整条就是 `unknown` → 被拒**。所以 `Get-Content a.json | Select-String x` 通过，而 `Get-Content a.json | python -` 或 `cat x | mytool` 必被拒——不是「第一段在白名单就行」。

**两个拒绝码**（宿主回执里的 `analysisReason`，看到就知道该怎么改命令）：

| 拒绝码 | 触发 | 含义 / 怎么改 |
|---|---|---|
| `shell_syntax_unproven` | `staticShellCommands` 返回 `null`（含未加引号的 `\ $ { } ( ) < @ % * ? [ ] #`、`&` 调用运算符、智能引号等动态语法） | 「语法没能静态解析」→ 判 `unknown` 拒。把命令改成白名单里的静态形态，或先 `$stop-that-shit change -- …` 切回可写 |
| `shell_command_unproven` | 静态解析成功，但命令名既不在 `READ_SHELL_COMMANDS` 也不在 `WRITE_SHELL_COMMANDS` | 「命令未证明只读」→ 判 `unknown` 拒。换成白名单内的只读命令（如用 `Get-Content` 代替自定义脚本） |

（升级 `stop-that-shit-dsh` 后白名单可能变：上表 11 条是快照，**以源码常量为准**，漂移了就用上面的提取命令重跑；本文档与 `ops/inspector-schedule.md` 都只引用常量名。）

其余一律按下面几条判「unknown → 拒」：

| 形态 | 判定 | 后果 |
|---|---|---|
| `& <cmd>` 调用运算符 | `&` 直接判 unknown | `& $PY tools\dsh_flow.py …` 这类 python 调用**必被拒** |
| 未加引号的 `\ $ { } ( ) < @ % * ? [ ] #` | 判 unknown（见 `staticShellCommands` 的字符黑名单） | 未加引号的 Windows 绝对路径（含 `\`）**必被拒** |
| `Get-FileHash` / `Get-Process` 等不在白名单的 cmdlet | 不在白名单 | 幂等只读也会被拒 |
| `>` 重定向、`&&`、单个 `\|` 之外的复合 | 判 write / unknown | 拒 |

**所以武装状态下做「只读审计」要给白名单里的形态**，例如：

```powershell
# 合规：两段都在白名单，路径用引号也好、用引号外没有反斜杠的形态也好，关键是不出现黑名单字符
Get-Content "D:\...\docs\<feature>\state.json" | Select-String '"phase"'
Get-ChildItem "D:\...\releases\C003" | Select-Object Name,Length
Get-Content "D:\...\ops\aux-tools.md" | Select-String "回滚材料"
```

要跑 `$PY … dsh_flow.py audit`、`Get-FileHash` 这类命令，**先在首行用 `$stop-that-shit change -- …` 切回可写**，或让 Lead 在未武装的会话里跑——不要为了让命令通过而去改 Guard 的白名单。

## 4. 建议顺序

```
Graphify（已可用）→ Mnemon（已可用，判据见 §5.1）→ Stop That Shit（已加载，武装后试用）
→ GitNexus（已可用，必须走 wrapper，见 §5.2）→ agentmem（确认需要跨 CLI 记忆再装）
```

优先级理由：前两个是**只读/记忆增强**，零拦截风险；STS 是唯一能**事前拦截越界**的，但也是唯一可能打断工作的；GitNexus/agentmem 与已装能力重叠最多。

## 5. 2026-11-20 判据更正（`toolchain-fixups` C001 实测，别再照旧文档走）

### 5.1 mnemon 就绪判据：`providers ≥ 1` 是错的

`mnemon_status.providers` 的取值来自 `dsh-mnemon-source-memory-spaces` 的 `providerServices()`，该函数**明确排除 native Provider**：

```js
const providers = this.providerCatalog.providers.filter((provider) => !isNativeProvider(provider));
```

再用 `enabled || configured || memoryBodyCount > 0 || status === 'unhealthy'` 过滤。只用 Mnemon Native（本机就是这种配置，`persistenceStrategy.allowedProviderIds = ['mnemon-native']`）时，**这个数组恒为 `[]`**，与「记忆能不能用」无关。

**正确判据（三条同时满足即可用）**：

| 判据 | 实测值（2026-11-20） |
|---|---|
| `commandFound === true`（宿主找到 mnemon CLI） | `true` |
| `memorySpaces.total ≥ 1` 且 `unhealthy === 0` | `total=1, active=1, healthy=1, unhealthy=0` |
| `mnemon_memory_bodies` 能列出 Space 且带 `capabilities` | `default` / `mnemon-native` / `remember+link+forget+search+graph` 全 true |

反过来说：**只有 `providers: []` 而没有前三条，才叫故障。**

### 5.2 GitNexus FTS 前置条件：OpenSSL 3 与 wrapper

LadybugDB 的 `fts` 扩展（`libfts.lbug_extension`）在 Windows 上依赖 **OpenSSL 3**（`libcrypto-3-x64.dll` / `libssl-3-x64.dll`），不是 VC++。缺它时 `gitnexus doctor` 报：

```
Full-text search: unavailable
  IO exception: Failed to load library: C:\Users\<user>/.lbdb/extension/<ver>/win_amd64/fts/libfts.lbug_extension
  ... Error: 找不到指定的模块。
```

（Windows 错误 126 同时覆盖「文件不存在」和「依赖 DLL 缺失」，所以别按字面理解成「扩展没装」。）

**本机方案（零系统级改动）**：把 DSH python 运行时自带的同版本 DLL 目录前置到本次调用的 PATH，已固化成 wrapper：

```powershell
# 前置 ~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\DLLs
# 再原样转发参数给 node_modules\.bin\gitnexus.CMD
& "<gitnexus-tools>\gitnexus.cmd" doctor     # → Full-text search: available
& "<gitnexus-tools>\gitnexus.cmd" query "manifest"
```

**两条纪律**：

1. **不要**把 wrapper 写成含中文注释的 `.cmd`：cmd.exe 按 OEM 代码页读批处理，UTF-8 中文会把 `rem` 行拆坏成随机命令（实测报过 `'bug_extension' is not recognized`）。脚本保持 ASCII。
2. **目标目录不是 git 仓库时必须加 `--skip-git`**，否则 `analyze` 会报 `Not inside a git repository.` 并退出（`status` 同样报 `Not a git repository.`）。

**已完成（2026-11-20 C003 复核，不再是欠账）**：`fts` 扩展能加载 ≠ FTS 索引已建，而本机索引已建好：

```powershell
& "<gitnexus-tools>\gitnexus.cmd" analyze --repair-fts --skip-git   # 657 s，输出 FTS indexes repaired successfully
& "<gitnexus-tools>\gitnexus.cmd" query "manifest"                  # 无 FTS 警告，timing.bm25 = 170.4
```

**判据（三条同时满足才算「关键字检索可用」）**：① `doctor` 报 `Full-text search: available`；② `query <关键词>` 输出**不含** `FTS indexes missing` / `FTS extension failed`；③ 输出里 `timing.bm25 > 0`。

**三条纪律**：

1. **必须走 wrapper，不要直接敲 `gitnexus`**：裸命令拿不到 OpenSSL 3，FTS 会退回 `FTS extension failed`，看起来像「索引又坏了」；同样不要为了这条去动 `System32`（不变量：零系统级改动）。
2. `analyze --repair-fts` 在本机会长时间无输出（`--verbose` 也不打印进度，只在结束时输出），**不要当它卡死就杀掉**——按 15–25 分钟预留（实测 657 s）。
3. `detect_changes` 要求**目标目录是 git 仓库且已有初始提交**；非 git 目录只能 `--skip-git` 做图查询，拿不到变更影响面。

## 6. 回滚材料已被污染（2026-11-20，装 STS 之后必读）

**结论：`package.json.bak-20261120-fixups` 已不是「干净的前装状态」，整份还原会误删别人的插件。**

| 事实 | 值 |
|---|---|
| 备份文件 | `~/.dsh\profiles\desktop\package.json.bak-20261120-fixups` |
| 备份时间 | 2026-11-20 **11:09:56**（装 `stop-that-shit-dsh` 之前） |
| 备份之后、本轮之外的写入 | 2026-11-20 **11:21:14** 有**流程外来源**（不是执行线程、不是验证线程）往同一个 `package.json` 里加了 `dsh-token-total` 一行，现在 loader 里能看到 `include:token-total` → `enabled=true` / `fiberPhase=active` |
| 后果 | 把备份整份覆盖回去 = 连 `dsh-token-total` 一起回滚，**用户会以为「token 统计坏了」，而根因是回滚** |
| 正确回滚 | ① 只删 `package.json` 里 `stop-that-shit-dsh` 那一行（`dependencies` 与 `bundles` 里各一处，实测是 `"stop-that-shit-dsh": "file:C:/…/stop-that-shit-dsh-0.2.6.tgz"` 与 bundles 数组里的 `"stop-that-shit-dsh"`）；② 删状态目录 `~/.dsh\stop-that-shit`；③ `dsh plugin --profile desktop list` 复核 `sts-bridge` 不再 active |
| 不要做 | 不要用 `Copy-Item package.json.bak-… package.json` 整份还原；不要顺手把 `cordis.patch.yml` 也还原（本轮没改它，`sts-bridge` 来自包内 bundle 层） |

**教训（写进纪律）**：任何「备份 → 改 → 回滚」的素材，只要备份与回滚之间还有别的写者，备份就退化成「某一时刻的快照」而不是「安全基线」。回滚必须按**增量**做（只撤自己加的那几行），不能按**快照**做。

---

## 9. 2026-11-21 09:58 实测更正（Lead）

> 本节**覆盖**上文第 3–14 行里已过期的判据。上文作为历史记录保留，不回改；以本节为准。

### 9.1 五件工具最终状态（09:50 实测）

| 工具 | 版本 | 状态 | 与上文的差异 |
|---|---|---|---|
| Graphify | 0.9.112 | ✅ MCP 2742 节点 / 5424 边 / 107 社区 | 无差异 |
| Mnemon | 插件 0.5.50 / CLI **0.2.14** | ⚠️ **1 个健康 Space + 2 条记忆可召回**；但 **Documents 检索不可用** | 上文说「Documents 词法检索实测命中（total=1、score=28）」**已失效**；CLI 从 0.2.13 升到 0.2.14 |
| Stop That Shit | 0.2.6 | ✅ `sts-bridge` active；**review 契约下真拦截**（宿主 denial 原文已取证） | 一致；补 §9.3 的 tgz 新路径 |
| GitNexus | 1.6.12 | ✅ `native ✓ lbugjs.node loaded`；FTS `bm25=950.1` | 上文 `bm25=170.4` 是旧索引；根因不是 OpenSSL 3 而是缺 `vcruntime140*.dll` |
| agentmem | — | ✅ **已装**：`D:\Tools\agentmem` + `agentmem.db`（7 会话 / 2293 事件）；MCP `search_events` 可命中 | 上文写「⬜ 未装」**已过期** |

### 9.2 Mnemon Documents 检索：**可用**（2026-11-22 01:19 更正，原判「不可用」是查错目录）

**实测矛盾**：

| 观察点 | 值 |
|---|---|
| `mnemon_document_create` 返回 | `documents.active=1`、`activeBytes=4910`、`status=active` |
| `~/.mnemon\documents\index.json` | `{"version":1,"documents":[]}`，**38 B，2026-11-19 21:48 后未再更新** |
| `~/.mnemon\documents\active\` | **空目录** |
| `mnemon_document_search` | `total=0` |
| CLI `mnemon status` | `total_insights=0`、`edge_count=0` |
| MCP `mnemon_status` | `totalInsights=2`、`edgeCount=4` |

**原判（2026-11-21，已推翻）**：曾据此表判定「写入没有落盘、Documents 不可用」。该判断**错误**——原因是查错了目录。

**2026-11-22 01:19 更正**：上述矛盾**不代表功能坏了**。两次独立验证证明「写入 → 索引 → 检索」是闭环的：

| 验证 | 命令 | 结果 |
|---|---|---|
| 跨重启存活 | `mnemon_document_search("代码图谱使用契约 graphify GitNexus")` | 命中 `e5b1e7c4`，`score=30`；该文档创建于 11-21 08:45，当前 DSH 进程 11-21 19:25 启动 |
| 写入即检索 | `mnemon_document_search("zebra-quasar-2201 探针 Documents 闭环")` | 命中探针 `2f793cf1`（01:16 创建），`score=13` |

**真相**：真实数据**不在** `~\.mnemon\documents\` 下（那目录只是遗留结构，`index.json` 38 B 空数组是历史残留），具体 `storageRoot` 未公开。

**处置（更正后）**：**可以用**，但 **备份时不能只拷 `~\.mnemon\documents\`**，否则会漏真实数据。完整取证与上游 issue 草稿见 [`ops/mnemon-documents-issue.md`](mnemon-documents-issue.md)。**仍然不要**去改 `index.json`（那是伪造状态，且改它也不会影响真实存储）。

### 9.3 Stop That Shit 的 tgz 已迁出 %TEMP%

- 旧：`file:C:/Users/81901/AppData/Local/Temp/sts-probe/stop-that-shit-dsh-0.2.6.tgz`（**Temp 被清理后会失效**，任何 `pnpm install`/`dsh plugin` 修复都会因找不到 tgz 失败）
- 新：`file:D:/Tools/sts/stop-that-shit-dsh-0.2.6.tgz`（80115 B，sha256 `B98A3085D90078AAF8013203BFADF1D1BAC5B4C863D45ADCA53194AFF6597103`；**这一版 2026-11-21 落在当时的工具根目录，2026-11-22 A-20 迁移时随目录整体搬到 `D:\Tools\sts`**，字节未变）
- 备份：`~/.dsh\profiles\desktop\package.json.bak-20261121-sts-relocate`
- **版本豁免**：`stop-that-shit-dsh@0.2.6` → 运行时 `0.2.2-rc.5`（`plugin_manager list_version_exemptions` 可查）。**DSH 升级后必须重验此豁免**；不兼容就卸载，不要本地改 `engines.dsh`。

### 9.4 周报项目根 `pack` 已回灌

`<weekly-report-project>\pack` 曾是 **0.1.0 / 7 文件**的残骸，与 `-dev` 副本（0.1.2 / 17 文件）和冻结包（0.1.2 / 17 文件）都不一致。已用 `releases/C004/files/pack` 回灌，**17 文件逐字节与 C004 全等**，备份在 `<root>\_backup-103pack-20261121-0958`。

> 判据：项目根 `pack/package.json` 的 `version` 必须与「最近一个已封存候选」的 `files/pack/package.json` 一致；不一致时以冻结包为准回灌，不要手改版本号。

## 10. 安装面清单（18 依赖 / 35 bundles，2026-11-22 实测）

> **数据源唯一**：`~/.dsh\profiles\desktop\package.json`（`[IO.File]::ReadAllText($p,[Text.Encoding]::UTF8) | ConvertFrom-Json` 读出：`dependencies` **18** 条、`dsh.profile.bundles` **35** 条）。
> **本节目的**：让「这个 profile 装了什么都从哪来的、谁装的」可追溯，不是安装说明。条目数必须与数据源逐条对齐；查不到归属就写「流程外来源 + 依据」，**不留空、不标「来路不明」而不给依据**。
> **措辞纪律**：任何没有真正解决的项写「未修复 / 待重建 / 上游缺陷」；**禁止**写「已修复」。
> **来源类型**取值只有五种：host 内置 / link / file / github / npm。

### 10.1 依赖（`dependencies`，18 条）

| # | 包名 | 来源类型 | 版本 / 规格 | 是否本项目流程安装 | 依据 |
|---|---|---|---|---|---|
| 01 | `@deepseek-ai/dsh-subagent-codex` | npm（官方） | `0.2.2-rc.5` | 否（宿主自带） | `@deepseek-ai` 官方发布，与宿主 rc.5 同版本；活文档无本流程安装记录 |
| 02 | `@local/dsh-graphify` | link | `link:packs/dsh-graphify` | 是（流程接线） | `ops/aux-tools.md` §2「Graphify 接线（已生效）」；`ops/code-graph.md` 记接线与提取命令 |
| 03 | `@local/dsh-ms-dev-preset` | link | `link:dsh-plugins/dsh-ms-dev-preset` | 是（本流程配套 preset） | `ops/schedules.md`；其 `flow/` 镜像由 `sync-flow.ps1` 从本仓库同步（本流程资产） |
| 04 | `@local/dsh-weekly-report` | link | `link:103-周报/docs/weekly-report/releases/C004/files/pack` | 否（另一项目冻结包） | 直链 `103-周报` 项目 `releases/C004/files/pack`；`ops/dsh-plugin-dev.md` 记回灌 |
| 05 | `@local/dsh-workbench` | file | `workbench/bundles/dsh-workbench-2.8.0.tgz` | 否（工作台安装） | 来自 `profiles/desktop/workbench/bundles/`；`ops/dsh-plugin-dev.md` 记录 |
| 06 | `@local/dsh-workbench-bot` | file | `workbench/bundles/工作台机器人.tgz` | 否（工作台安装） | 同上目录；活文档无本流程安装记录 |
| 07 | `@local/huiwen-ppt` | file | `workbench/bundles/汇文-ppt.tgz` | 否（工作台安装） | 同上目录；`ops/dsh-plugin-dev.md` 记录 |
| 08 | `@xmanrui/dsh-im` | npm | `^5.10.0` | 否 | npm 源；`docs/toolchain-fixups` 记为流程外来源新增的 bundle 登记之一 |
| 09 | `ds-harness-remote` | npm | `0.6.7` | 否 | npm 源；活文档无本流程安装记录 |
| 10 | `dsh-ask-panel` | github | `github:mouse985/dsh-ask-panel` | 否 | GitHub 直链；活文档无本流程安装记录 |
| 11 | `dsh-meetai` | file | `workbench/bundles/会议助手.tgz`（装后 0.4.0） | 否（工作台安装；**已就地打补丁**） | 见 §10.3 第 1 条；上游缺陷**未修复** |
| 12 | `dsh-memory-evolve` | npm | `0.1.0` | 否 | npm 源；`ops/memory-split.md` 只有记忆定位/运维记录 |
| 13 | `dsh-mnemon` | npm | `0.5.50` | 否 | npm 源；`ops/aux-tools.md` §5.1 / §9.2 是运维结论，无安装记录 |
| 14 | `dsh-multi-role-flow` | link | `link:dsh-多角色协作流程/dsh-bundle-dist` | 是（本流程自身） | 即 `dsh-bundle-dist/` 的 bundle 产物，由 `tools/build_bundle.py` 生成 |
| 15 | `dsh-raganything-kb` | file | `workbench/bundles/知识库.tgz` | 否（工作台安装） | 同上目录；活文档无本流程安装记录 |
| 16 | `dsh-super-kanban` | npm | `^0.10.5` | 否 | npm 源；`docs/toolchain-fixups/DEPLOYMENT-PLAN.md` 记为流程外来源 |
| 17 | `dsh-token-total` | npm | `^1.1.6` | 否（流程外来源） | `ops/aux-tools.md` §6 明确「11:21:14 流程外加进来」 |
| 18 | `stop-that-shit-dsh` | file | `file:D:/Tools/sts/stop-that-shit-dsh-0.2.6.tgz` | 是 | `toolchain-fixups` C001/C002 按候选安装 + 版本豁免；`ops/aux-tools.md` §3 / §9.3 |

**计数自检**：上表数据行 01–18 共 **18** 条；类型分布 npm 7 / link 4 / file 6 / github 1。

### 10.2 bundles（`dsh.profile.bundles`，35 条）

| # | bundle | 来源类型 | 版本 / 规格 | 是否本项目流程安装 | 依据 |
|---|---|---|---|---|---|
| 01 | `@deepseek-ai/dsh-base` | host 内置 | 宿主 rc.5 | 否（宿主自带） | `@deepseek-ai` 内置 bundle |
| 02 | `@deepseek-ai/dsh-web-app` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 03 | `@deepseek-ai/dsh-experimental-voice-input-bundle` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 04 | `@deepseek-ai/dsh-experimental-plugin-market-bundle` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 05 | `@deepseek-ai/dsh-experimental-auto-review` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 06 | `@deepseek-ai/dsh-experimental-forge-bundle` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 07 | `@deepseek-ai/dsh-personalized-recommendations` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 08 | `@deepseek-ai/dsh-experimental-inspector-profile` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 09 | `@deepseek-ai/dsh-experimental-cot-translation-bundle` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 10 | `@deepseek-ai/dsh-experimental-session-titles-bundle` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 11 | `@deepseek-ai/dsh-experimental-badge-skill-bundle` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 12 | `@deepseek-ai/dsh-deepseek-chat-import` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 13 | `dsh-raganything-kb` | file | `workbench/bundles/知识库.tgz` | 否（工作台安装） | 同 §10.1-15 |
| 14 | `@local/dsh-workbench-bot` | file | `workbench/bundles/工作台机器人.tgz` | 否（工作台安装） | 同 §10.1-06 |
| 15 | `dsh-meetai` | file | `workbench/bundles/会议助手.tgz`（装后 0.4.0） | 否（工作台安装；**已就地打补丁**） | 见 §10.3 第 1 条；上游缺陷**未修复** |
| 16 | `@local/huiwen-ppt` | file | `workbench/bundles/汇文-ppt.tgz` | 否（工作台安装） | 同 §10.1-07 |
| 17 | `dsh-ask-panel` | github | `github:mouse985/dsh-ask-panel` | 否 | 同 §10.1-10 |
| 18 | `@deepseek-ai/dsh-experimental-ralph-bundle` | host 内置 | 宿主 rc.5 | 否（宿主自带） | `@deepseek-ai` 内置 bundle |
| 19 | `@deepseek-ai/dsh-experimental-session-search` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 20 | `@deepseek-ai/dsh-experimental-terminal-bundle` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 21 | `@deepseek-ai/dsh-experimental-liveshare` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 22 | `@deepseek-ai/dsh-experimental-tool-worktree` | host 内置 | 宿主 rc.5 | 否（宿主自带） | 同上 |
| 23 | `@local/dsh-ms-dev-preset` | link | `link:dsh-plugins/dsh-ms-dev-preset` | 是（本流程配套 preset） | 同 §10.1-03 |
| 24 | `@local/dsh-graphify` | link | `link:packs/dsh-graphify` | 是（流程接线） | 同 §10.1-02 |
| 25 | `dsh-memory-evolve` | npm | `0.1.0` | 否 | 同 §10.1-12 |
| 26 | `@deepseek-ai/dsh-subagent-codex` | host 内置 | `0.2.2-rc.5` | 否（宿主自带） | 官方包，与宿主 rc.5 同版本 |
| 27 | `dsh-mnemon` | npm | `0.5.50` | 否 | 同 §10.1-13 |
| 28 | `@xmanrui/dsh-im` | npm | `^5.10.0` | 否 | 同 §10.1-08 |
| 29 | `dsh-super-kanban` | npm | `^0.10.5` | 否 | 同 §10.1-16 |
| 30 | `stop-that-shit-dsh` | file | `file:D:/Tools/sts/stop-that-shit-dsh-0.2.6.tgz` | 是 | 同 §10.1-18 |
| 31 | `dsh-token-total` | npm | `^1.1.6` | 否（流程外来源） | 同 §10.1-17 |
| 32 | `@local/dsh-weekly-report` | link | `link:103-周报/.../releases/C004/files/pack` | 否（另一项目冻结包） | 同 §10.1-04 |
| 33 | `dsh-multi-role-flow` | link | `link:dsh-多角色协作流程/dsh-bundle-dist` | 是（本流程自身） | 同 §10.1-14 |
| 34 | `@local/dsh-workbench` | file | `workbench/bundles/dsh-workbench-2.8.0.tgz` | 否（工作台安装） | 同 §10.1-05 |
| 35 | `ds-harness-remote` | npm | `0.6.7` | 否 | 同 §10.1-09 |

**计数自检**：上表数据行 01–35 共 **35** 条；类型分布 host 内置 18（`@deepseek-ai/*`，含 `dsh-subagent-codex`）/ file 6 / link 4 / npm 6 / github 1。
**与依赖的关系**：18 条依赖全部出现在本节 35 条中；多出的 17 条均为 `@deepseek-ai/*` 宿主内置项。

### 10.3 两条必须单独登记的特别项（都不许写「已修复」）

#### ① `dsh-meetai`：**已就地打补丁，但上游缺陷未修复**

| 项 | 事实 |
|---|---|
| 缺陷 | `scripts/native-unified/grant-store.mjs` 上游无条件要求 `O_NOFOLLOW`；Windows 上该常量为 `undefined` → 整模块 import 即抛 `NOFOLLOW_CAPABILITY_REQUIRED`，DSH 里 `include:meetai` 的 fiber 起不来 |
| 本机处置 | **已就地打补丁**：`noFollow = typeof constants.O_NOFOLLOW === 'number' ? constants.O_NOFOLLOW : 0`（退化后符号链接/硬链接防护仍由 `lstat` + `nlink` + `realpath` 校验承担）。**这是本机适配，不是上游修复** |
| 补丁件位置 | `<workspace>\_vendor-patches\dsh-meetai\scripts\native-unified\grant-store.mjs`（15135 B，2026-11-22 13:02:33）；原件 `.orig`（14598 B，2026-11-19 10:33:42） |
| 装机状态 | 补丁打在 pnpm 硬链接**之外**的独立 inode（`nlink=1`），因此不会被同 inode 的其它链接覆盖 |
| 已知残留 | native 授权存储仍 **Linux-only**；本补丁只消除 import 抛错，**不能**证明 Windows 上授权存储可用 |
| 重装风险 | **重装后需重打**（`pnpm install` / 插件升级会覆盖）。重打时把 `_vendor-patches` 里的 `grant-store.mjs` 覆盖回 `node_modules\dsh-meetai\scripts\native-unified\` |
| 措辞 | 上游缺陷**未修复**；本机为「适配补丁」，待上游发布 Windows 兼容版本 |

#### ② preset 的 GitHub 发布 `imasonhk-spec/dsh-ms-dev-preset`：**发布渠道失效，待重建**

| 项 | 事实（2026-11-22 实测） |
|---|---|
| repos | `https://api.github.com/repos/imasonhk-spec/dsh-ms-dev-preset` → **HTTP 404** |
| releases | `.../releases` → **HTTP 404** |
| tags | `.../tags` → **HTTP 404** |
| 网页端点 | `https://github.com/imasonhk-spec/dsh-ms-dev-preset` 请求被中断（连接被意外关闭）——既不构成可见证据，也不构成可用发布 |
| 本机是否依赖 | **不依赖**：`@local/dsh-ms-dev-preset` 走 `link:` 指向本地 `<plugins-home>\dsh-ms-dev-preset`，运行不需要 GitHub |
| 结论 | **发布渠道失效，待重建**（公开不可见）。不许写「已修复」或「已重新发布」 |

### 10.4 维护约定

- 任何加装/卸载后必须重跑本节口径：`dependencies` 应为 **18**、`dsh.profile.bundles` 应为 **35**；数字变了就同时更新小节标题与本表。
- profile 目录下的 `*.bak*` 备份文件**不登记**为依赖。
- 本节不写安装步骤（步骤在 §3 / §9.3 与 `ops/dsh-plugin-dev.md`），只写归属。
