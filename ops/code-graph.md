# 代码知识图谱：每个项目建图与多项目切换契约

> 适用：本机 `desktop` profile，graphify 0.9.112（`<graphify-tools>`），MCP 服务名 `graphify`
> （14 个 `mcp__graphify__*` 工具）。本文只讲「图在哪、怎么建、怎么切、什么时候别信它」。

## 0. 一句话

**每个项目各建一张图，存在该项目自己的 `graphify-out\graph.json`；MCP 服务的默认图是
`default-workspace` 那张，查别的项目时给工具传 `project_path`，不要去改 MCP 配置。**

## 1. 本机事实（2026-11-20 实测；含 2026-11-21 追补，各行时点见文内标注）

| 项 | 值 |
|---|---|
| CLI | `<graphify-tools>\Scripts\graphify.exe` → `graphify 0.9.112` |
| MCP 服务 | `dsh-graphify` 插件注册 `@deepseek-ai/dsh-mcp-client`，stdio 起 `graphify-mcp.exe` |
| MCP 默认图 | `<default-workspace>\graphify-out\graph.json`（2742 节点 / 5424 边 / 107 社区） |
| 其他已建图项目（2026-11-20 时点） | `<workspace>\weekly-report-dev` → 240 节点 / 468 边 / 9 社区（**该目录现已不存在**，2026-11-21 实测 `Test-Path=False`，图随之失效）；继任项目 `<weekly-report-project>` 有自己的图：**63 节点 / 70 边 / 6 社区**（2026-11-21 实测 `graph_stats`） |
| 本项目图（`dsh-多角色协作流程`） | **397 节点 / 919 边 / 24 社区**（**C005 时点现值**，2026-11-21 16:48 重建后实测 `graphify-out/graph.json`；副本污染 0）；C003 时点为 395 节点 / 908 边 / 18 社区，其后 C004 又改过 `tools/dsh_flow.py`，以最近一次实测为准 |
| 未建图项目 | 其余项目目录（查图前先看图在不在，见 §4） |

`default-workspace` 那张图是**工作区级**的（文档 + 代码混合），不是某个业务仓库的调用图；
业务仓库的影响面判断要用该仓库自己那张图。

## 2. 建图（代码部分本地、免费、不外发）

```powershell
$g = "<graphify-tools>\Scripts\graphify.exe"

# 首次建图：只解析代码（tree-sitter AST，不调模型、不需要 key）
& $g extract "<workspace>\<项目>" --code-only

# 代码改动后增量更新（不新增/不删除节点时最快）
& $g update "<workspace>\<项目>"

# 大重构后节点变少会被安全阀拦住，确认要覆盖再加 --force
& $g update "<workspace>\<项目>" --force
```

- 输出固定落在 `<项目>\graphify-out\graph.json`（另有 `.graphify_analysis.json`、`manifest.json`、`cache\`）。
- **不要**加 `--code-only` 之外的语义提取（文档/PDF/图片）除非确实要，且要配模型 key——那是外发内容。
- 建图只读项目文件、只写 `graphify-out\`，不碰源码；`graphify-out\` 不需要进候选包，也不该进 git
  （若项目是 git 仓库，把它加进 `.gitignore`）。
- 不要把 `graphify install` / `claude install` / `codex install` / `opencode install` 这类命令用在本流程的
  项目里：它们会写 `AGENTS.md` / `CLAUDE.md` / `.cursor` 等宿主约定文件，与「不新增宿主约定文件」冲突。

## 3. 查询：三种入口，按场景选

| 场景 | 用什么 | 关键参数 |
|---|---|---|
| 会话内（智能体） | MCP 工具 `mcp__graphify__*` | **`project_path` = 项目根绝对路径**，指向含 `graphify-out\graph.json` 的目录 |
| 一次性提问（人/脚本） | `graphify query "<问题>" --graph <项目>\graphify-out\graph.json` | `--depth`、`--budget` |
| 结构定位（人） | `graphify explain <节点>` / `graphify path A B` / `graphify affected X` | `--graph <路径>` |

MCP 侧最常用的四个：

```
graph_stats(project_path=...)      # 先确认图存在、节点数 > 0
query_graph(question, project_path=..., depth=3)
get_neighbors(label, project_path=...)   # 改前看调用方
god_nodes(project_path=..., top_n=10)    # 架构枢纽，定回归范围
```

**切换契约**：`project_path` 缺省时工具读 MCP 配置里那张默认图（`default-workspace`）。
跨项目就在每次调用时显式传 `project_path`，**每个调用都要传**——这是建议性参数，传错不报错，
只会拿另一张图回答，看起来「有结果」但答的是别的项目。

## 4. 图不存在的表现（别把「查不到」当「没依赖」）

- MCP 工具在 `project_path` 下找不到 `graphify-out\graph.json` 时会报错或返回空；
  **空结果先查图在不在**（`Test-Path <项目>\graphify-out\graph.json`），不要据此判断「无调用方」。
- `failOnStartupError: false` 是故意的：图缺失不能让 DSH 起不来，所以症状是「工具在、查不到」，
  而不是启动失败。
- 结论：**没有图就不算查过影响面**，要么建图，要么在证据里写「未建图，改用文件列举 + 哈希差集」。

## 5. 什么要改 MCP 配置（不归执行线程）

需要「不传 `project_path` 就默认查某个业务仓库」时，才要改 `dsh-graphify` 的
`cordis.patch.yml` 里 `graphify-mcp` 的 `args[0]`（现在写死 default-workspace 的 graph.json）。
这属于改 profile 配置 + 宿主半，必须重启 DSH 才生效，**由 Lead 决定、验证线程执行**；
执行线程不自行改、也不在候选里夹带。

## 6. 图谱是旁证，不是凭证

- 候选真相仍以 `releases/<候选>/manifest.json` 的 `sha256` + `tools/dsh_flow.py verify` 为准。
- 图谱用于**缩小范围**（改前看调用方、定回归集），不能用于证明「没影响」——INFERRED 边是推断，
  EXTRACTED 也覆盖不到配置文件、字符串拼接的间接调用与运行时注册。
- 证据里引用图谱结论时写清：哪张图（项目 + 节点/边数）、哪个工具、什么参数、结论是
  「EXTRACTED 边显示 X」还是「推断」。

## 7. GitNexus 关键字检索（FTS）前置条件

> 2026-11-20（feature `toolchain-fixups` C001）实测补入。graphify 与 GitNexus 是两套图，本节只管 GitNexus 的**关键字检索**这一路。

**前置条件 1：PATH 里要有 OpenSSL 3。** LadybugDB 的 `fts` 扩展（`libfts.lbug_extension`）依赖
`libcrypto-3-x64.dll` / `libssl-3-x64.dll`；缺它时 `gitnexus doctor` 报
`Full-text search: unavailable` + `Failed to load library ... Error: 找不到指定的模块`（Windows 错误 126 同时
表示「文件不存在」和「依赖 DLL 缺失」，别照字面理解）。本机**不装系统级运行库**，改由 wrapper 前置
DSH python 运行时的 `python\DLLs` 目录：

```powershell
& "<gitnexus-tools>\gitnexus.cmd" doctor      # → Full-text search: available
& "<gitnexus-tools>\gitnexus.cmd" query "关键字"
```

wrapper 本体在 `<gitnexus-tools>\gitnexus.cmd`（ASCII-only，改动前先读它的注释）。

**前置条件 2：目标目录不是 git 仓库时加 `--skip-git`。** 否则 `analyze` 直接报
`Not inside a git repository.` 退出（`gitnexus status` 同样报 `Not a git repository.`）。

**前置条件 3：FTS 索引要建过。** 扩展能加载 ≠ 索引存在。缺索引时 `query` 仍带
`warning: FTS indexes missing — keyword search degraded`，且 `timing.bm25` 只反映退化查询耗时，
不代表命中了关键字。建索引：

```powershell
& "<gitnexus-tools>\gitnexus.cmd" analyze --repair-fts --skip-git
```

该命令在本机**长时间不打印进度**（`--verbose` 也只输出结束时的结果），10 分钟没动静不等于卡死，
按 15–25 分钟预留；后台跑就用 `Test-Path`/mtime 观察 `<项目>\.gitnexus\lbug` 是否被写。

**排障口径**：`query` 没有 `FTS extension failed` 与 `FTS indexes missing` 两条 warning，且
`timing.bm25 > 0`，才能说「关键字检索可用」。只满足前半条只能说「扩展加载成功、索引未建」。graphify 那条链路（§2–§4）与本节无关，不受影响。

## 8. 默认步骤与失败降级（`init` 自动建图）

> 2026-11-20（feature `flow-context-boost` C001）起，建图不再是「可选的手工动作」，而是 `dsh_flow.py init` 的**默认步骤**（`next` 生成的交接包也会自动带图谱摘要）。它就是「默认步骤」——**不进 `advance` 硬门禁**，失败只降级。

| 场景 | `init` 行为 | 失败时 |
|---|---|---|
| 项目根没有 `graphify-out/graph.json` | 执行 `graphify extract "<项目>" --code-only` | 打 `⚠ 建图失败（原因）+ 手工命令`，**退出码仍 0** |
| 已有 `graphify-out/graph.json` | 执行 `graphify update "<项目>"`（增量，不新增/删除节点时最快） | 同上；安全阀拦住（节点变少）时**不自动加 `--force`** |
| `init --no-graph` | 两步都不做（也不维护 `.graphifyignore`），回到旧行为 | — |
| `init --graph-timeout <秒>` | 建图超时（默认 300s）即放弃 | 打 `⚠ 建图失败（超时 Ns）+ 手工命令`，退出码 0 |
| 兜底 | — | 手工命令一律打印在 `⚠` 那行下面，可直接复制粘贴执行 |

**失败降级纪律（沿用 §4）**：没有图就不算查过影响面 → 证据里写「未建图，改用文件列举 + 哈希差集」；
不要把「查不到」当「没依赖」，也不要因为建图失败去堵 `advance`/`freeze`。

## 9. `.graphifyignore` 排除规则（不加排除 = 图里 89% 是封存副本）

项目根的 `.graphifyignore` 由 `dsh_flow.py init` 维护：不存在就创建，存在则**只追加缺失的排除行**
（不重写、不删用户自定义行、不改顺序，连续两次 `init` 字节一致）。graphify 按 gitignore 语义逐目录 + 祖先链读取，
只能排除、不能反包含。

```text
# 由 dsh_flow.py init 维护；只排除封存副本与工具产物
docs/**/releases/
docs/**/archive/
docs/**/files/
docs/**/evidence/
examples/
dsh-bundle/
dsh-bundle-live/
dsh-bundle-dist/
graphify-out/
```

> **分发产物目录会有多个历史名字**（`dsh-bundle/` → 事故后 `dsh-bundle-live/` → 现在
> `dsh-bundle-dist/`），所以清单里三个名字都要列。C003 之前只排了 `dsh-bundle/`，
> 结果图里 322/675 个节点是 `dsh-bundle-live/**` 的旧副本（C001 时点，见下表第二行）。
> 这里**故意不用通配** `dsh-bundle*/`：那会连 `dsh-bundleable/` 这类同前缀目录一起排除，
> 且 `init` 的契约是「只追加缺失行」——写进去的通配行以后再想改就得重写文件。
> 代价是改名要再补一行（`selftest` 的 `Q: F1` 会校验已知三类都在清单里）。

**本项目实测对照（graphify 0.9.112；各行标的是「该行时点」的实测值，历史行不追改成现值）**：

| 条件 | 耗时 | 节点 | 边 | 说明 |
|---|---|---|---|---|
| 不加 `.graphifyignore`（2026-11-20，97 个文件） | 26.8 s | **2378** | 5343 | 约 89% 节点是 `docs/*/releases/*/files/` 的封存副本，`god_nodes` 全指向重复副本 |
| 加 7 行排除（2026-11-20，同上 97 个文件） | 6.5 s | **269** | 685 | 来源分布全部是真实源码 |
| **加 7 行排除、但排除清单漏了 `dsh-bundle-live/`**（**C001 时点**，2026-11-21 实测） | — | **675** | 1701 | 该时点 `graph_stats` = **675 节点 / 1701 边 / 36 社区**（社区数引自 C002 台账，见 `docs/flow-quality-boost/evidence/C003/P24-graph-rebuilt-clean.md`）；其中 **322 个**节点在 `dsh-bundle-live/**`；`_qc_static`/`warn_for` 等新符号**查不到**，`get_neighbors` 报 ambiguous（两份 `dsh_flow.py`） |
| **9 行排除 + `graphify update --force`**（**C003 时点**，2026-11-21 15:43） | **7.56 s** | **395** | 908 | 污染 0（同刻 `graph_stats` = **395 节点 / 908 边 / 18 社区**）；`_qc_static`/`warn_for`/`cmd_drive` 均命中且 `source_file` 均为 `tools/dsh_flow.py` |

> **C005 时点现值（2026-11-21 实测）**：**397 节点 / 919 边 / 24 社区**，副本污染 0。出处：`graphify-out/graph.json` 的 `nodes`/`links` 计数 + `GRAPH_REPORT.md` 摘要行（`397 nodes · 919 edges · 24 communities`）；相对 C003 的 395/908/18 是 **+2 节点 / +11 边**，增量来自本轮新增的 `suite_r()` 函数与其 docstring 节点（见 `docs/flow-quality-boost/EXECUTION-PLAN.md`）。

判断图被污染：`graphify-out/graph.json` 的 `nodes[].source_file` 里出现
`releases/` / `archive/` / `evidence/` / `files/` / `dsh-bundle` / `dsh-bundle-<后缀>`
（`dsh_flow.py` 里由同一个 `RE_GRAPH_COPY_SOURCE` 判据负责，两处检测共用）。
此时**只提示**（`init` 与 `next` 都会打
`⚠ 检测到图中含封存副本 … 建议 graphify update --force 重建`），**绝不自动 `--force`**：它会覆盖更大的图，
是破坏性操作。`graphify-out/` 本身也在 `SKIP_DIR_NAMES` 里——不进基线、不进候选、不被 `audit` 记越界。
**别拿 graphify 自己的 `pruned N node(s)` 当「图已干净」的判据**：C003 实测它只报
`pruned 10 node(s) from 1 newly-ignored file(s)`，而实际从图里消失的副本节点是 322 个；
判据只能是重建后对 `nodes[].source_file` 的实测。

**换盘不影响排除行为（2026-11-21）**：D 卷由 **2026-11-21 换盘前**的 exFAT（当时 `HealthStatus=Warning` / `OperationalStatus=Full Repair Needed`，**历史状态，现已不存在**）整块换成 SSD，现为 **NTFS / Healthy / OK**（2026-11-21 `Get-Volume -DriveLetter D` 实测）；`.graphifyignore` 的语义不变（graphify 仍按 gitignore 规则逐目录 + 祖先链读取），`dsh-bundle-live/`、`dsh-bundle-dist/` 从 C003 起就在排除清单里。换盘后本项目实测（**C005 时点**）**397 节点 / 919 边 / 24 社区，副本污染 0**（判据见上：`nodes[].source_file` 实测，不认 graphify 的 `pruned` 行）。`dsh-bundle-live` 残骸已归档到项目外 `<workspace>\_attic-dsh-bundle-live-20261121`（7 个根级文件），即使没有排除行也不会再进图。
