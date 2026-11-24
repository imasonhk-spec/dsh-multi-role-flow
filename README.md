# DSH 多角色协作开发流程

> 把 Codex 桌面版那套「方案规划师 / 执行线程 / 验证线程 / 督察使」协议，改写成 **DSH 原生**的一套开发流程：
> 一个根智能体（Lead）编排，用 `subagent` 把活派给不同角色，**角色完成自动回到 Lead，再由 Lead 按门禁派下一个**。
> 文档层（角色职责、模板、证据标准）基本原样保留；传输层（怎么开会话、怎么交接、怎么防越界）按 DSH 重写。

**第一次用，直接看「三、5 分钟上手」**。原理和边界在「五」「六」，出问题看「八」。

---

## 一、这套流程解决什么

单会话做完整项目有三个硬伤，DSH 上一个都没消失：

| 硬伤 | 在 DSH 上的表现 | 这里的解法 |
|---|---|---|
| 上下文会压缩 | 长任务压缩后忘掉授权边界、「重复问已确认的问题」 | 状态落盘：`state.json` + `handoffs/` + `ledger.md`，压缩后一条命令恢复 |
| 开发与部署必须分离 | 子智能体共享同一文件系统，开发者能顺手装东西 | 候选冻结包 + sha256 + 验证线程只读冻结包；Lead 亲自 `audit` |
| 会越界 | `write_scopes` 只是建议，PowerShell 能绕过 | 「不做清单」+ 候选清单只登记声明范围 + `audit` 三类告警 |

核心原则不变：**把「信任」换成「可核验的凭证」**。任何角色说「完成」，都要有别处可复核的东西（哈希、命令原文、文件路径）。

---

## 二、包内清单

```
dsh-多角色协作流程/
├── README.md                       ← 本文件
├── ROADMAP.md                      ← 后续任务（P0/P1/P2 + 待用户拍板）
├── MIGRATION.md                    ← 原协议 → DSH 的差异、降级与补偿（含工具名更正）
├── roles/                          ← 角色说明书（直接当 subagent prompt 用）
│   ├── 00-lead.md                  总线程 = 根智能体，编排手册
│   ├── 01-planner.md               方案规划师（一次性，只读 + 写 DESIGN）
│   ├── 02-executor.md              执行线程（唯一有代码写权）
│   ├── 03-verifier.md              验证线程（唯一有安装权，只信哈希）
│   └── 04-inspector.md             督察使（只读审计，可选）
├── templates/                      ← 目标项目里的文档模板
│   ├── AGENTS.md                   项目级自动注入（安装时写入目标项目根）
│   ├── DESIGN.md / SOURCE-PLAN.md
│   ├── COORDINATION-PLAN.md / EXECUTION-WORKPLAN.md / VALIDATION-WORKPLAN.md
│   ├── EXECUTION-PLAN.md / DEPLOYMENT-PLAN.md / ACCEPTANCE.md
│   └── manifest.json / RELEASE-REPORT.md / HANDOFF.md
├── dsh-bundle-dist/                ← 可分发 DSH bundle（由 tools/build_bundle.py 生成，勿手改）—— 目录名由项目根 `.dsh-flow-bundle-dir` 决定（2026-11-21 换盘后为 `dsh-bundle-dist`；历史 `dsh-bundle/` 已废弃、现存 0 文件）—— **仅源仓库存在，preset 内置副本 `flow/` 不含本目录**
├── tools/
│   ├── build_bundle.py             重建 dsh-bundle-dist/（含 --check）（生成的 dsh-bundle-dist/ 仅源仓库存在）
│   ├── dsh_flow.py                 状态机 + 候选凭证工具（24 个子命令的唯一实现，以 `--help` 的 choices 为准）
│   ├── selftest.py                 无模型端到端自测（**2026-11-22 实测 473 用例 / 0 失败**，步数一律以现跑末尾 `total=`/`failed=` 为准；**23 套 A–Y（无 F/O）**——纯文件、带运行时插件、只有 docs/、未声明 runtime 告警、看板、能力包骨架、health、文档命令漂移、bundle 完整性、docs 元数据留痕、工具缓存排除、drop 作废、门禁加固、交接包上下文、质量提升、交叉 seal、文档类候选免证据、封存异地快照、备份缺陷回归 C002、备份缺陷回归 C003、audit 时间线误报、audit 只报真问题、`.ps1` 编码与删除守卫）
│   ├── install.ps1                 一键装到目标项目（AGENTS.md + .dsh/skills）
│   └── install-git.ps1             补装 git（MinGit，免管理员），让 create_worktree 可用
├── skills/dsh-multi-role-flow/SKILL.md   DSH 技能（项目级安装后自动出现在技能目录）
├── workflow/review-candidate.workflow.js  多角度独立复核的 workflow 脚本模板
├── ops/                            ← 运维与硬事实手册（10 份 .md）
│   ├── aux-tools.md                辅助工具评估：graphify / GitNexus / agentmem 等接不接、凭什么接
│   ├── code-graph.md               代码知识图谱：每项目建图与多项目切换契约
│   ├── dsh-plugin-dev.md           DSH 能力包/插件开发硬规则（模块 id、宿主半重启、握手、错误格式）
│   ├── host-restart-sop.md         宿主重启 SOP（插件/能力包/服务类）
│   ├── inspector-schedule.md       督察使定时审计操作手册（Lead 专用）
│   ├── lessons.md                  跨 feature 教训库（`lesson add` 沉淀，下个交接包自动带出）
│   ├── memory-split.md             记忆分工：memory-evolve 与 mnemon 各记什么、冲突以谁为准
│   ├── schedules.md                定时任务台账（id、频率、暂停/删除命令）
│   ├── workflow-verification.md    workflow 多角度复核：实测记录
│   └── worktree-isolation.md       工作树隔离：开法与实测结论
└── examples/                       演示（真实跑过一遍）—— **仅源仓库存在，preset 内置副本 `flow/` 不含本目录**
    ├── setup_demo.py               一键搭 demo 项目并推进到 EXECUTING
    ├── README.md                   演示时间线与结果
    └── demo-wordstat/              演示项目（执行 → 验证 → 用户试用）
```

**「文档层」与「传输层」**：`roles/`、`templates/`、证据标准都是文档层（换平台也能用）；`tools/dsh_flow.py`、`AGENTS.md`、`skills/`、`workflow/`、`ops/` 是 DSH 传输层。

---

## 三、5 分钟上手

### 1. 装到目标项目（幂等，可重复跑）

```powershell
# 方式 A（推荐，全局一次）：装 bundle，技能在所有会话可见
#   plugin_manager install_bundle target="<flow-home>\dsh-bundle-dist"   ← 目录名以项目根 .dsh-flow-bundle-dir 为准（现为 dsh-bundle-dist）；该路径仅源仓库存在，preset 内置副本 flow/ 不含 dsh-bundle-dist/；在 preset 里跳过方式 A 用方式 B
# 方式 B（按项目）：项目级 AGENTS.md + .dsh/skills
powershell -NoProfile -ExecutionPolicy Bypass -File "<flow-home>\tools\install.ps1" -Project "<your-project>"
```

它做两件事：
- 复制技能到 `<your-project>\.dsh\skills\dsh-multi-role-flow\SKILL.md`（DSH 自动发现并热加载，不用重启）；
- 在 `<your-project>\AGENTS.md` 写入流程约定（已有内容不覆盖，装过就跳过）。

> 在 DSH 里把这个项目作为会话工作目录打开。无 `.git` 时 DSH 用当前目录识别项目根；会话开在子目录会找不到 `.dsh/skills`。

### 2. 初始化一个 feature

```powershell
$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$FLOW = "<flow-home>\tools\dsh_flow.py"

& $PY $FLOW init     -p "<your-project>" -f export-report --scope src
& $PY $FLOW baseline -p "<your-project>" -f export-report
& $PY $FLOW status   -p "<your-project>" -f export-report
```

- `--scope` 是**执行线程允许改的目录**（可多次给）。
- `baseline` 默认覆盖整个项目（排除 `docs/`、依赖与缓存），用来发现「范围外悄悄改了」。
- 这时 `status` 会告诉你当前阶段、缺什么门禁、下一位角色。

### 3. 让 Lead 自己跑起来

先一条命令看清全局（**只读**，不写 `state.json`、不生成交接包、不写 `health.json`）：

```powershell
& $PY $FLOW drive -p "<your-project>" -f export-report          # 8 行：phase / 候选 / 下一角色 / 门禁 / 软告警 / 阻塞 / 能否推进 / 建议命令
& $PY $FLOW drive -p "<your-project>" -f export-report --json   # 给看板/脚本：顶层 12 键（schema=dsh-flow/drive@1）
```

`门禁` 给「N/M 通过」与未过项名，`软告警` 给 `⚠` 计数与首条明细（静态检查 / 图谱证据），
`建议命令` 可直接复制。退出码与 `gate` 对齐：硬门禁未过 `1`、全过 `0`、`state.json` 缺失 `2`。

在 DSH 里说一句：

> 按 `docs/export-report/state.json` 的当前阶段推进，用 subagent 派对应角色，完成一个阶段就校验凭证再推进。

Lead 的动作是固定的：

```
status → next（生成交接包）→ team_task_create（带 blocked_by）
       → subagent(prompt=交接包全文) → 完成通知自动回到 Lead
       → Lead 亲自 verify / audit → advance → 下一个角色
```

### 4. 你只需要在四个时刻出现

需求确认、试用回执、范围变更、不可逆操作（装服务/删数据/动生产/花钱）。

---

## 四、角色与 DSH 能力映射

| 角色 | DSH 里是什么 | 关键工具 | 生命周期 |
|---|---|---|---|
| Lead（总线程） | **根智能体本身**（不存在独立会话） | `subagent`、`team_task_*`、`advance` | 全程 |
| planner 方案规划师 | `subagent` | 只读 + `write`（只写 docs） | 一次性 |
| executor 执行线程 | `subagent`，可 `send_message` 续聊 | `pwsh`、`read/write`、`freeze` | 一个批次 |
| verifier 验证线程 | **另一个独立** `subagent`，不看 exec 上下文 | `verify`、`pwsh`、`write`（只写报告/证据） | 一个批次 |
| inspector 督察使 | `subagent` + `schedule_create` | `audit`、`gate`、`ledger` | 只读、可选 |
| 用户 | 人 | `ask_user_question` | 关键时刻 |

**自动交接的四个机制**（缺一条就退化成人肉）：

| 机制 | 替代原协议里的什么 |
|---|---|
| 子智能体完成**自动通知 Lead** | 替代「执行线程发消息给验证线程」 |
| `next` 生成带完整事实的**交接包** | 替代「人肉粘贴启动指令 + threadId 登记」 |
| `team_task_*` 的 `blocked_by` | 替代「靠 Markdown 台账记得顺序」 |
| `state.json` + `ledger.md` | 替代「靠压缩计数判断要不要换代」 |

**交接包默认带上下文（2026-11-20 `flow-context-boost` 起）**：`next` 生成的交接包 §1「已知上下文」自动汇总四块——
图谱摘要（`graphify-out/graph.json` 的节点/边数与 top5 分布）、上一候选已报的坑（`RELEASE-REPORT.md` 的两个固定小节）、
同类坑（`ops/lessons.md` 按角色过滤）、项目关键事实（直读 memory-evolve 的 `projects/<id>/KEY.md`，可叠加
`docs/<feature>/CONTEXT-NOTES.md` 与 `--key-note`）。§2 角色要点按阶段裁剪（必保五节 + 指针，交接包 ≤12000 字节），
`--no-context` / `--max-context-chars` / `--memories-dir` 可调。**全部离线采集**（不调 MCP/LLM/网络），缺数据只写
「未提供（原因 + 怎么补）」，`next` 退出码仍为 0。

**建图与教训库也变成默认供给**：`init` 默认维护项目根 `.graphifyignore` 并自动建图（失败只降级、退出码 0，`--no-graph` 关闭）；
角色说明书里的图谱查询从「可选」改成「默认步骤（本阶段必做、不进硬门禁）」；踩坑用 `lesson add` 沉淀进跨 feature 教训库
`ops/lessons.md`，下一个 feature 的交接包自动带出来。**新增动作一律不进 `advance` 硬门禁**（用户拍板「轻量」）。

---

## 五、状态机与门禁

```
DESIGN ──planner──► PLAN ──Lead──► EXECUTING ──executor──►
VERIFYING ──verifier──► TRIAL ──用户──► DONE
异常态：ROLLED_BACK；任何阶段可标 blocked
```

`advance` 每次都会重跑门禁并拒绝不合格的推进：

| 转换 | 必须存在的东西 |
|---|---|
| `DESIGN→PLAN` | `DESIGN.md`：`## 验收标准`、`## 不改什么（边界）`、独占一行 `状态：已确认`、无 `{{占位符}}` |
| `PLAN→EXECUTING` | `planning/` 四份：`## 权限矩阵`、`## 任务分解`、`## 检查项`、来源登记 |
| `EXECUTING→VERIFYING` | 已冻结候选，且 `verify --id C00X` 通过（哈希、证据、安装顺序、回滚字段） |
| `VERIFYING→TRIAL` | `RELEASE-REPORT.md`：`## 待用户试用清单` + 独占一行 `结论：已上线可试用/待用户试用/完整业务验收通过` |
| `TRIAL→DONE` | `ACCEPTANCE.md`：独占一行 `用户结论：通过` |

> 三态里只有用户能说「完整业务验收通过」。`待用户试用` 是合法状态，不是失败。

### 运行时、重启与变更（第一轮真实项目后新增）

插件/能力包/服务类项目，**装上 ≠ 生效**——宿主半常不热替换。门禁现在把这些变成硬检查：

| 动作 | 命令 | 什么时候用 |
|---|---|---|
| 运行时握手 | `flow.py handshake --id C007 --expect 0.4.1 --url http://127.0.0.1:61081/api/<id>/health` | 装完/重启后核对运行时真实版本；写 `evidence/<C>/R1-handshake.md`，FAIL 退出码 1 |
| 封存验证证据 | `flow.py seal --id C007` | 验证线程写完报告、收口前 |
| 标记阻塞 | `flow.py block --reason "等用户重启 DSH" --owner user --kind env` | 等用户/环境时；阻塞期间 `advance` 会被拒绝 |
| 解除阻塞 | `flow.py unblock --note "已重启，握手通过"` | 用户处理完 |
| 设计变更 | `flow.py amend --reason "格式改为纯文本编号版"` | 需求/验收变化：归档旧 DESIGN、置「待用户确认」、DESIGN 版本 +1 |

- `freeze` 新增 `--runtime-kind/--runtime-version/--health-url/--requires-restart`。声明 `runtime` 后，`gate TRIAL` 要求握手通过（实际版本 == manifest 声明版本）。
- `seal` 把 `V*` 证据、发布报告、部署台账的 sha256 封进 `releases/<C>/verification.json`；之后任何改动或新增证据都会被 `verify` 查出（补掉了原来「`V*` 不在哈希清单」的缺口）。
- **别用新候选掩盖旧宿主**：装完行为没变 → 先 `handshake`；FAIL 就重启 DSH，重启后重跑握手，不要连出 C003/C004。

**DSH 中途重启、子智能体消失**：`status` 看 phase/阻塞/最近交接 → `next` 重新生成同一交接包（或直接用 `handoffs/` 最新那份）→ 重派；磁盘产物与证据**不重做**。卡在「等用户重启」时用 `block --owner user` 记录，别硬出候选。

**需求/格式变更**：`amend` → 改 `DESIGN.md` 与「变更历史」→ 用户确认后把状态行改回 `状态：已确认` → `unblock` → `advance --to EXECUTING` 开新候选（不继承旧候选结论）。

**TRIAL 后发现要补验**（例如用户重启后要确认运行时、或环境变化）：`advance --to VERIFYING` 回补验同一候选，不重装、不新开候选；补验完再 `advance --to TRIAL`。

---

## 六、目标项目里的目录约定

```
<项目根>/
├── AGENTS.md                       流程约定（DSH 每次会话自动读）
├── .dsh/skills/dsh-multi-role-flow/SKILL.md
└── docs/<feature>/
    ├── DESIGN.md
    ├── planning/{SOURCE,COORDINATION,EXECUTION-WORKPLAN,VALIDATION-WORKPLAN}.md
    ├── EXECUTION-PLAN.md           执行线程台账
    ├── DEPLOYMENT-PLAN.md          验证线程台账
    ├── ACCEPTANCE.md               验收台账（用户结论）
    ├── state.json                  阶段/候选/台账（只有 Lead 用 advance 改）
    ├── baseline.json               E0 基线哈希（越界审计参照）
    ├── ledger.md                   人读台账（工具自动追加）
    ├── evidence/<C00N>/<check>.md  证据（A/B/C/D）
    ├── releases/<C00N>/manifest.json + RELEASE-REPORT.md + files/
    └── handoffs/HANDOFF-<seq>-<role>.md   Lead 生成的交接包
```

---

## 七、可靠性边界（诚实说明）

本机**没有 bash**（`git` 2.56.1 与 node 24.21.0 已在 PATH，`doctor` 实测），但 `create_worktree` 是否可用**以 `doctor` 输出为准**、未验证前按不可用算。这带来三个必须接受的降级，以及补偿手段：

| 降级 | 后果 | 补偿 |
|---|---|---|
| `create_worktree` 未验证 / 无 `git diff` 基线（整包未 `git init`） | 执行与验证共享文件系统，验证线程可能看到改了一半的代码 | 执行线程在 `<项目根>-dev` 副本工作；验证线程**只读** `releases/<C>/files/`；`freeze` 生成哈希、`verify` 复核 |
| `write_scopes` 仅建议性 | PowerShell 能绕过写范围 | 任务「不做清单」+ 候选只登记声明范围 + `audit` 的「未登记 / 与候选不一致 / 范围外」三类告警 + Lead 亲自看 |
| 子智能体不能互相通信 | 无法复刻「执行 ↔ 验证」直接对话 | 一切经磁盘 + Lead 中转；完成通知自动回 Lead 就是交接触发 |

**结论**：DSH 上「开发者不能自证」从「物理隔离」降为「冻结包 + 哈希 + 流程纪律」。跑数据工程、内容改动、内部工具足够；碰生产数据、出过事故的项目，把开发/部署放回 Codex 桌面版，DSH 只做需求与审计。

补充一个已知缺口：`manifest.json` 只登记**冻结时**存在的证据（执行线程的 `P*`）；验证线程后写的 `V*` 与 `RELEASE-REPORT.md` 不在哈希清单里，靠报告的引用关系与督察使抽查兜底。要把 `V*` 也纳入凭证，可让验证线程在安装后追加一个「验证候选」或由 Lead 在 `advance --to TRIAL` 前手工算一次哈希并记进台账。

---

## 八、故障排查

| 现象 | 先查 |
|---|---|
| `advance` 说门禁不过 | 直接看输出里 `✗` 那几行；按提示补内容，别用 `--force` |
| `verify` 报「未登记文件」 | 有人往 `releases/C00X/files/` 里塞了东西，或冻结时漏登记 |
| `verify` 报「哈希不一致」 | 冻结后文件被改过，重新冻结新编号 |
| `audit` 报「未登记」 | 执行线程超出声明范围，或候选清单漏登记 |
| 子智能体「不知道上游做了什么」 | 派活时没给交接包全文；用 `next` 重新生成 |
| 状态与磁盘对不上 | 有人手改了 `state.json` 或 `ledger.md`；用 `status`/`ledger` 对齐 |
| 装完技能没出现 | 会话工作目录不是项目根（无 `.git` 时按 cwd 识别） |
| 命令找不到 `python` | 用绝对路径 `$PY`（见上手第 2 步） |
| 装完行为没变 / 面板打不开 | 先 `handshake` 核运行时版本；插件宿主半要重启 DSH；客户端模块 id 必须是包名（见 [ops/dsh-plugin-dev.md](ops/dsh-plugin-dev.md)） |
| 报错只有 `NOT FOUND` | 前端错误必须带 `HTTP <status> <METHOD> <path>`；按 `ops/dsh-plugin-dev.md` 的错误格式修，并在验收里加检查项 |
| DSH 重启后角色不见了 | `next` 重派同一交接包；磁盘产物与证据不重做（`status` 会显示最近交接） |
| 卡在等用户重启/确认 | `block --owner user` 记录，`advance` 会被拒绝；别靠出新候选掩盖 |

**裁剪建议**（别一律上五角色）：

| 任务 | 角色 | 流程深度 |
|---|---|---|
| typo、单文件小改 | 0 | 直接做，不要用本流程 |
| 多文件、要交付 | executor + verifier | 从 `EXECUTING` 起 |
| 需求模糊 | + planner | 从 `DESIGN` 起 |
| 周期长、范围会变 | Lead 亲自写规划 | 完整 `PLAN` |
| 生产数据、出过事故 | + inspector | 加定时审计（`ops/inspector-schedule.md`） |

---

## 九、与原协议的关系

- 原协议：`<legacy-protocol>`（Codex 桌面版，未改动）。
- 本包：文档层沿用（角色职责、模板骨架、证据 A/B/C/D、候选不继承、三态结论），传输层重写。
- 差异与逐条理由见 [MIGRATION.md](MIGRATION.md)；工具名更正（`spawn_teammate`→`subagent` 等）也在那里。

## 十、事实来源

- DSH 版本：见 `dsh_flow.py doctor` 输出的 python 路径与安装目录；本机 `git` **2.56.1**（`git.exe`）与 node **v24.21.0** 已在 PATH，`doctor` 不再报缺 git——`create_worktree` 是否可用仍**以 `doctor` 结论为准**。
- 工具能力：依据当前会话实际可见的工具（`subagent`、`subagent_fork`、`send_message`、`list_agents`、`wait_agent`、`team_task_*`、`create_worktree`、`workflow`、`schedule_*`）。
- 技能自动发现：`@deepseek-ai/dsh-skill-filesystem` 的默认根（项目 `.dsh/skills`、用户 `~/.dsh/skills`）。**实测**：把本包的 `SKILL.md` 放进工作区 `.dsh/skills/` 后，当前会话的技能目录**立刻出现** `dsh-multi-role-flow`，无需重启。
- 项目级自动注入：`@deepseek-ai/dsh-agent-instructions` 读取 `AGENTS.md`。**实测**：在本包 `templates/AGENTS.md` 存在期间，DSH 已把它作为该目录的会话指令自动加载。
- 原协议：`<legacy-protocol>`（README、如何开始、角色定义、协作规则、模板）。

## 十一、已验证的事实（本机实测）

| 验证项 | 结果 |
|---|---|
| `tools/selftest.py` 基础用例（首轮 18 步） | 全过：门禁拦截、冻结、verify 篡改检测、audit 越界、报告/验收门禁 |
| `tools/selftest.py` 44 步（早期版本） | `amend` 后门禁拦截、`block/unblock`、runtime 冻结、`handshake` 正确/错误版本、`seal` 后证据篡改检测、外部源目录越界审计 |
| `tools/selftest.py` 54 步（早期版本） | 新增全过：`baseline` 自动发现兄弟 `*-dev` 外部源、`external` 数组新形态兼容、`doctor` 基线校验、`inspector` 输出无残留占位符且 `--json` 可解析 |
| `tools/selftest.py` **473 用例**（2026-11-22 实测，`failed=0`、`SKIP=0`；**现值以现跑末尾 `total=`/`failed=` 为准**） | `flow-quality-boost` 已收口到 `phase=DONE` / `current_candidate=C012`（冻结 9 个候选，C007/C009/C011 已 `drop` 归档；以 `flow.py status` 现读为准）：`selftest` 从 250 一路涨到 473（含 R 组交叉 `seal` 断言、W/X 审计判定、Y 组 `.ps1` 守卫；23 套 A–Y、无 F/O）；`build_bundle.py --check` exit 0（49 产物、版本 **1.2.6**，现读以 `--check` 为准）。逐候选内容与残留项见 [ROADMAP.md](ROADMAP.md) 的 §10 |
| 真实项目回归 | 周报能力包 C001–C007 全流程；「宿主半没重启」这次事故直接催生了 `handshake` 门禁与 `block --owner user` |
| `baseline` 自动发现 | 在 `weekly-report`（项目根只有 `docs/`）上实测：不写 `--source` 也找到 `weekly-report-dev` 的 15 个文件，`audit` 恢复可用 |
| `inspector` 命令 | 生成的 prompt 含真实项目/feature/候选/外部源/报告路径，`{{` 残留 0 处；`--json` 输出可被脚本直接解析 |
| `tools/install.ps1` | 在空项目与已有 `AGENTS.md` 的项目上各跑一次：技能复制、约定追加、幂等跳过都正常 |
| 技能热加载 | 写入 `.dsh/skills/` 后当前会话目录立即出现该技能（无需重启 DSH） |
| 真实多角色演示 | `examples/demo-wordstat`（**examples/ 仅源仓库存在，preset 内置副本 `flow/` 不含**）：Lead → executor → verifier 全链路，两个子智能体只与 Lead 通信；`gate` 拦住未填证据/未写结论的推进 |
| git / worktree | `git` 2.56.1 与 node v24.21.0 已在 PATH（`doctor` 实测）；`create_worktree` 是否可用**以 `doctor` 为准**，未验证前隔离走 `-dev` 副本 + 冻结包哈希 |
| 可分发 bundle | 产物目录由项目根 `.dsh-flow-bundle-dir` 决定：现为 `dsh-bundle-dist/`（**49 产物、版本 1.2.6**，均以 `build_bundle.py --check` 现读为准，**仅源仓库存在，preset 内置副本 `flow/` 不含**）。历史 `dsh-bundle/`（44 文件，v1.0.0）已随 2026-11-20 事故与 11-21 D 卷换盘退役，残骸归档在 `<workspace>\_attic-dsh-bundle-live-20261121`。内容 = 本流程包 + 技能 + `cordis.patch.yml`（用独立 provider `multi-role-flow` 挂 `skills/`）；`plugin_manager install_bundle target=<bundle 目录>` 实测 `application=applied`、无激活错误；`tools/build_bundle.py --check` 可做 CI 校验。**改完源文件必须按序** `build_bundle.py` → `build_bundle.py --check`（exit 0）→ `selftest.py` |
| 辅助工具 | Graphify 0.9.112 已装（MCP 14 工具；`init` 现在**默认**建图并维护 `.graphifyignore`，图谱从「可选旁证」变成交接包默认摘要；查询契约见 `ops/code-graph.md`）；Mnemon CLI v0.2.13 已装（sha256 校验、用户 PATH），等重启 DSH 后在 Plugins→dsh-mnemon 启用 Native provider；Stop That Shit / GitNexus / agentmem 评估见 `ops/aux-tools.md` |
