# GLOSSARY · 术语表

> 每个术语：一句话定义 / 在哪确认（命令或文件）/ 源码位置。
> **行号会随代码漂移**：以「函数名」为准；需要精确行号时执行
> `Select-String -Path tools\dsh_flow.py -Pattern "def cmd_health"`。
> 术语与角色名一一对应；角色定义在 `roles/*.md`，命令实现在 `tools/dsh_flow.py`。

---

## 1. 角色（5 个）

| 术语 | 定义 | 在哪确认 | 源码 / 文件 |
|---|---|---|---|
| **Lead**（总线程） | 根智能体本身；拆活、派活、验凭证、推进状态 | `roles/00-lead.md`；`list_agents` 里名字是 `lead` | 无独立进程；`advance` 只由它执行 |
| **planner**（方案规划师） | 一次性角色，把模糊需求压成 `DESIGN.md`，只读代码 | `roles/01-planner.md` | 由 `subagent` 派出 |
| **executor**（执行线程） | 唯一有业务代码写权；在副本/工作树里改，冻结候选 | `roles/02-executor.md` | 同上 |
| **verifier**（验证线程） | 唯一有安装权；只读冻结包、自己重跑、写发布报告 | `roles/03-verifier.md` | 同上 |
| **inspector**（督察使） | 只读审计，只写 `evidence/inspector-<日期>.md`；可定时 | `roles/04-inspector.md` | 同上 + `schedule_create` |

> DSH 没有「总线程会话」这种实体：**Lead = 当前会话的根智能体**。子智能体之间不能通信，交接只走磁盘 + Lead 中转。

---

## 2. 状态机（阶段与阻塞）

| 术语 | 定义 | 在哪确认 |
|---|---|---|
| **DESIGN** | 需求/边界/验收标准成形阶段（planner 主导） | `status` 的 `phase` |
| **PLAN** | 四份规划（权限矩阵/任务分解/检查项/来源） | 同上；`gate --to EXECUTING` |
| **EXECUTING** | 执行线程干活、冻结候选 | 同上；`freeze` 只在此阶段 |
| **VERIFYING** | 验证线程安装/核验/写报告 | 同上；`seal` 收口 |
| **TRIAL** | 等用户试用回执 | 同上；`ACCEPTANCE.md` 的 `用户结论：通过` |
| **DONE** | 验收通过；同一 feature 下一轮用 `advance --to EXECUTING` | 同上 |
| **ROLLED_BACK** | 异常态：回滚完成 | 同上 |
| **blocked** | 阻塞标记（owner/kind/reason/since），不是阶段 | `state.blocked`；`block`/`unblock` |

状态机转移表在 `dsh_flow.py` 的 `TRANSITIONS` 常量；门禁函数是 `gate_for`。

---

## 3. 凭证与文件

| 术语 | 定义 | 谁写 | 在哪确认 |
|---|---|---|---|
| **候选 C00N** | 一次冻结的交付快照，编号递增、不可复用 | `freeze` | `releases/C00N/` |
| **manifest.json** | 候选清单：产物 sha256/bytes/role、安装顺序、回滚、证据、runtime | `freeze` | `verify --id C00N` 校验 |
| **freeze** | 把 dev 副本 `scope` 内文件复制进 `releases/<C>/files/` 并锁哈希 | executor | `manifest.json` 的 `artifacts[]` |
| **verification.json** | 封存清单：`V*` 证据 + 发布报告 + 部署台账的 sha256 | verifier（`seal`） | `gate TRIAL` 要求存在；`verify` 校验 |
| **evidence（P\*）** | 执行线程自测证据（命令原文/退出码/等级） | executor | `manifest.evidence[]` |
| **evidence（V\*）** | 验证线程核验证据 | verifier | `verification.json` + 报告引用 |
| **R1** | 运行时版本握手证据 `R1-handshake.md` | `handshake` | `state.candidates.<C>.runtime` |
| **baseline.json** | E0 基线哈希（项目内 + 外部源），越界审计参照 | `baseline` | `audit` |
| **audit** | 对比 baseline 与当前树，列「未登记/不一致/范围外」 | Lead | `audit --strict` 退出码 1 |
| **state.json** | 阶段/候选/阻塞/台账；**只有 Lead 用 `advance`/`block` 改** | `dsh_flow.py` | `status --json` |
| **ledger.md** | 人读台账（工具自动追加） | 工具 | `ledger --tail 20` |
| **handoff** | 给下一位角色的交接包（含角色说明书全文） | Lead（`next`） | `handoffs/HANDOFF-<seq>-<role>.md` |
| **health.json** | 健康快照（阶段/门禁/候选/封存/最近台账），供外部看板 | `health` | `docs/<feature>/health.json` |
| **证据等级 A/B/C/D** | A 命令原文+退出码、B 文件哈希/清单、C 截图/回执、D 自述（不能单独作通过依据） | 各角色 | `evidence/<C>/<id>.md` 头部字段 |

**双清单口径**：`manifest.evidence`（冻结时 P\*）与 `verification.json`（封存时 V\*/报告/部署台账）职责不重叠，详见 `MIGRATION.md` 第三节第 7 条。

---

## 4. 命令（`tools/dsh_flow.py`，24 个子命令）

| 命令 | 一句话 | 实现函数 |
|---|---|---|
| `init` | 初始化 feature 骨架；`--kind plugin` 同时生成能力包四件套；**默认**维护项目根 `.graphifyignore` 并自动建图（失败只打 ⚠ + 手工命令、退出码 0；`--no-graph` 关闭、`--graph-timeout` 改超时） | `cmd_init` |
| `baseline` | 记 E0 基线（自动发现 `*-dev`/`package.json` link 外部源） | `cmd_baseline` |
| `freeze` | 冻结候选、生成 manifest、校验式告警；`--reused "检查号:具体理由"`（可多次保序）登记复用检查项到 `manifest.checks.reused` | `cmd_freeze` |
| `verify` | 校验 manifest（+ 已封存时的 verification.json） | `cmd_verify` |
| `drop` | 作废候选清理：`releases/<C>` 与 `evidence/<C>` **移动**到 `archive/<C>-<时间戳>/`，从 `state.candidates` 移除（只移动不删除；已 seal 需 `--force`） | `cmd_drop` |
| `audit` | 越界审计（项目内 + 外部源） | `cmd_audit` |
| `evidence` | 生成统一格式证据文件 | `cmd_evidence` |
| `status` | 阶段/候选/阻塞/门禁/台账 | `cmd_status` |
| `next` | 生成交接包（Lead 专用，会改 `next_seq`）；默认带「已知上下文」四子块（图谱/上一候选的坑/同类坑/项目关键事实，含 `KEY.md` 直读）与按阶段裁剪的角色要点；`--key-note`、`--memories-dir`、`--no-context`、`--max-context-chars` | `cmd_next` |
| `lesson` | 跨 feature 教训库：`add` 追加一条（自动编号）、`list` 只读（可按角色）；只写 `ops/lessons.md`，不写 `state.json`、不进 `gate` | `cmd_lesson` |
| `scope` | 补正声明写范围：`--add <相对路径>`（可多次）只追加 `state.scope`，**不动 `baseline.json`**；用于存量 feature 把 `.graphifyignore` 补进 scope | `cmd_scope` |
| `advance` | 推进阶段（门禁强校验，`--force` 需 `--reason`） | `cmd_advance` |
| `gate` | 汇总当前/指定目标的门禁 | `cmd_gate` |
| `drive` | **只读合成**：一次给出 `phase` / 候选 / 下一角色 / 门禁（硬 `N/M` + 软 `⚠`）/ 阻塞 / 能否推进 / 建议命令；不写 `state.json`/`ledger.md`/`health.json`，不生成交接包；退出码与 `gate` 对齐（未过 1 / 全过 0 / 无 state 2）；`--json` 顶层 12 键（`schema=dsh-flow/drive@1`） | `cmd_drive` |
| `ledger` | 追加/查看台账 | `cmd_ledger` |
| `doctor` | 环境自检（git/node/模板/角色/基线） | `cmd_doctor` |
| `health` | 写 `health.json` | `cmd_health` |
| `dashboard` | 多 feature 看板 | `cmd_dashboard` |
| `inspector` | 生成可粘进 `schedule_create` 的巡检 prompt | `cmd_inspector` |
| `block` | 标记阻塞（owner/kind/reason/since 四要素，只写 `state.blocked`，不改 `phase`） | `cmd_block` |
| `unblock` | 解除阻塞（记台账，可带 `--note` 说明解封依据） | `cmd_unblock` |
| `amend` | DESIGN 升版：归档旧版、置待确认、记台账 | `cmd_amend` |
| `handshake` | 运行时版本握手（写 R1） | `cmd_handshake` |
| `seal` | 封存 V\*/报告/部署台账 | `cmd_seal` |

> `--help` 是唯一权威。`selftest` 的 I 套会做「文档命令 ↔ `--help`」双向对照，文档写了不存在的命令或漏写命令都会失败。

---

## 5. DSH 概念

| 术语 | 定义 |
|---|---|
| **subagent** | 派生一个独立上下文的子智能体；完成自动通知父；可用 `send_message` 续聊 |
| **subagent_fork** | 带父会话已完成轮次上下文的子智能体（适合「接着刚才复核」） |
| **write_scopes** | 任务板上的**建议性**写范围，可被 PowerShell 绕过 → 靠「不做清单」+ `audit` 兜底 |
| **blocked_by** | 任务依赖（验证依赖冻结、修复依赖报告），由任务板强制顺序 |
| **workflow** | 脚本化编排：`agent()`/`pipeline()`/`parallel()`/`phase()`；见 `workflow/review-candidate.workflow.js` |
| **schedule_create** | 定时投递 prompt（督察使日审计）；DSH 未运行期间不投递、恢复后只补最近一次 |
| **create_worktree** | 原生工具：建 `<仓库>/.agents/worktrees/<name>` 并切换调用者 cwd；已实测可用（`ops/worktree-isolation.md`） |

**外部工具与记忆归属**（定义同 §5，第三列是「在哪确认」）

| 术语 | 定义 | 在哪确认 |
|---|---|---|
| **Mnemon** | 分层记忆插件 + CLI（`D:\Tools\mnemon`）：运行时常驻 / 项目文档 / Memory Spaces | `dsh-mnemon` 插件页 |
| **记忆分工** | 流程事实进 memory-evolve、代码库知识进 mnemon；冲突按事实类型裁决（不按时间） | `ops/memory-split.md` |
| **agentmem** | 只读 MCP：把本机各 agent（含 DSH）的会话历史索引进本地 SQLite 供跨端检索；`connect` 才写 MCP 配置 | `D:\Tools\agentmem`；`agentmem.py detect/init/sync/status/search` |
| **GitNexus** | 符号级调用图 + `impact`/`context`/`trace`（PolyForm Noncommercial） | `<gitnexus-tools>`；索引在 `<仓库>\.gitnexus\` |
| **stop-that-shit（STS）** | 两层：Skill = advisory 纪律（Stop Ladder 五步）；Guard = 宿主侧模式/文件锁/子代理预算硬拦 | `skills/stop-that-shit/SKILL.md`；Guard 版本门禁见 `ops/aux-tools.md` §3 |
| **代码图谱契约** | 每个项目各建一张图（`<项目>\graphify-out\graph.json`），MCP 查询必须显式传 `project_path` | `ops/code-graph.md` |

---

## 6. 能力包概念（插件项目）

| 术语 | 定义 | 检查点 |
|---|---|---|
| **capabilityPack** | `package.json` 的 `dsh.capabilityPack`：id/title/description/entryKey/order/icon/category/version/tags | `init --kind plugin` 生成；`smoke.mjs` 断言 |
| **bundle / patch** | `dsh.bundle.patch` 指向 `cordis.patch.yml`，向 Loader roster 插入本包行 | 短 id 与包名分离 |
| **entryKey** | 能力入口键，固定 `cap:<短id>` | 与 `client.js` 的 `ENTRY_KEY` 一致 |
| **openEvent** | 打开面板的事件名，固定 `cappacks:open-<短id>` | 前端监听同名 |
| **`__ModuleLoader__`** | 浏览器半加载契约；`id` 必须是**包名**（不是短 id） | `smoke.mjs` 断言 |
| **smoke.mjs** | 零依赖自检（33 条断言） | `node scripts/smoke.mjs` |
| **runtime / handshake** | 宿主半改动需重启 DSH；「新版是否在跑」只认握手 | `ops/host-restart-sop.md` |
| **requires_restart** | `manifest.runtime.requires_restart`：装完未重启 → 结论只能「待用户试用」 | `gate TRIAL` |

---

## 7. 原协议 → DSH 的术语对照

| 原协议（Codex 版） | DSH 版 | 变化 |
|---|---|---|
| threadId 登记表 | `handoffs/` + 任务板 | 没有可核验地址，改为磁盘交接 |
| 人肉粘贴启动指令 | `next` 生成的交接包全文 | 工具生成，占位符填实 |
| 压缩计数 / 递归交接 | `state.json` + `ledger.md` | 阶段级交接，压缩后一条命令恢复 |
| SENT / QUEUED / ACKNOWLEDGED | 磁盘回执 + 任务板 `complete` | 不存在输入框投递 |
| STS Guard（工具层写保护） | `audit` + `block` + Lead 复核 | 降为流程纪律 |
| 独立副本 + 独立会话 | git worktree / `<项目根>-dev` | 物理隔离仍在，但需 Lead 复核 |
| 候选 C00N / manifest | 同左 + `verification.json` | 证据分冻结/封存两份清单 |

---

## 8. 源码索引（按符号名查，**不写行号**）

> **行号随代码漂移，不要写死。** 本节曾经是一张 29 条 `L####` 的行号表，2026-11-22 复核时**全部 29 条都已漂移**（偏差 +4 到 +1398 行，因为 `dsh_flow.py` 一直在长）——所以表撤掉，只留符号名与现查命令。

一条命令列出下面 29 个符号的**当前**行号（在项目根执行；正则按 `cmd_` 前缀兜住全部子命令实现，所以还会多出一条 `cmd_drive`——`drive` 是只读合成子命令，未纳入索引表）：

```powershell
Select-String -Path 'tools\dsh_flow.py' -Pattern '^(def (cmd_|build_health|build_parser|verify_manifest|gate_for|main)|TRANSITIONS\s*=)' | Select-Object LineNumber, Line
```

Git Bash / WSL 等价写法：

```bash
grep -nE '^(def (cmd_|build_health|build_parser|verify_manifest|gate_for|main)|TRANSITIONS[[:space:]]*=)' tools/dsh_flow.py
```

只查一个符号（把 `cmd_freeze` 换成下表的任一名字）：

```powershell
Select-String -Path 'tools\dsh_flow.py' -Pattern '^def cmd_freeze\b'
```

同理，**文件总行数也不要抄**（现读：`(Get-Content 'tools\dsh_flow.py').Count`）——它每天都在变。

### 8.1 符号清单（只给名字，不给行号）

| 分组 | 符号 |
|---|---|
| 状态机与解析 | `TRANSITIONS`、`build_parser`、`main` |
| 门禁与候选校验 | `gate_for`、`verify_manifest` |
| 生命周期子命令 | `cmd_init`、`cmd_scope`、`cmd_baseline`、`cmd_freeze`、`cmd_verify`、`cmd_drop`、`cmd_seal`、`cmd_advance` |
| 审计与证据 | `cmd_audit`、`cmd_evidence`、`cmd_lesson`、`cmd_ledger` |
| 状态与交接 | `cmd_status`、`cmd_next` |
| 阻塞与变更 | `cmd_block`、`cmd_unblock`、`cmd_amend` |
| 运行时与服务 | `cmd_handshake`、`cmd_gate`、`cmd_doctor`、`build_health`、`cmd_health` |
| 看板与巡检 | `cmd_inspector`、`cmd_dashboard` |
