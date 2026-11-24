---
name: dsh-multi-role-flow
description: 多角色/多智能体协作开发流程（需求→规划→执行→验证→上线）。当任务需要拆成方案、开发、验证、上线多个角色并自动交接，或用户提到「多角色协作」「多智能体开发」「按流程走一遍」「交接给验证/执行角色」「候选冻结」「验收台账」时使用。流程包在 <流程包根>。
whenToUse: 任务涉及多文件改动并需要交付/上线；需求模糊需要先问清；有执行与验证职责分离要求；或用户明确要求按多角色协作流程推进。
---

> 本技能随 `dsh-multi-role-flow` bundle 分发：**流程包根 = 本技能目录向上两级**（`<skill base>/../..`，即 bundle 根目录）；`$FLOW` = `<流程包根>/tools/dsh_flow.py`。


# DSH 多角色协作开发流程

流程包：`<流程包根>`（角色说明书 `roles/`，模板 `templates/`，状态机工具 `tools/dsh_flow.py`）。

## 1. 先判断要不要用

| 任务 | 做法 |
|---|---|
| 改文案/typo/单文件小改 | 直接做，不要用本流程 |
| 多文件改动、要交付 | 执行 + 验证两个 `subagent` |
| 需求模糊 | 先派 planner 问清验收标准 |
| 范围可能变、工期长 | Lead 亲自写 `planning/` 四份规划 |
| 生产数据、出过事故 | 加 inspector 与定时审计 |

## 2. 启动三步

```powershell
$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$FLOW = "<流程包根>\tools\dsh_flow.py"

# 1. 初始化（每 feature 一次；--scope 是执行线程允许改的目录）
$PY $FLOW init -p "<项目根>" -f <feature> --scope src

# 2. 记基线（越界审计的参照）
$PY $FLOW baseline -p "<项目根>" -f <feature>

# 3. 看状态与下一位角色
$PY $FLOW status -p "<项目根>" -f <feature>
```

## 3. 状态机

```
DESIGN --planner--> PLAN --Lead(写规划三份)--> EXECUTING --executor-->
VERIFYING --verifier--> TRIAL --用户试用--> DONE
异常：ROLLED_BACK（回滚）；每个阶段都可能带 blocked 标记
```

阶段门禁由 `advance` 自动检查，不满足就拒绝推进：

| 转换 | 必须存在 |
|---|---|
| DESIGN→PLAN | `DESIGN.md` 有 `## 验收标准`、`## 不改什么（边界）`、独占一行 `状态：已确认`、无 `{{占位符}}` |
| PLAN→EXECUTING | `planning/` 四份：`## 权限矩阵`、`## 任务分解`、`## 检查项`、来源登记 |
| EXECUTING→VERIFYING | 已冻结候选且 `verify --id C00X` 通过 |
| VERIFYING→TRIAL | `RELEASE-REPORT.md` 有 `## 待用户试用清单` 与独占一行 `结论：<三态之一>`，无占位符；候选声明了 `runtime` 时 `handshake` 已 PASS（实际版本 = `manifest.runtime.version`）；`seal_required` 时 `verification.json` 已存在 |
| TRIAL→DONE | `ACCEPTANCE.md` 有独占一行 `用户结论：通过`（候选有 `runtime` 时仍要求握手 PASS） |

三个阶段之外的**动作**也会挡路，都会写进 `state.json` 与 `ledger.md`：

| 动作 | 命令 | 作用 | 不做的后果 |
|---|---|---|---|
| 握手 | `handshake --id C00N --expect <版本> --url <健康检查>` | 拉 JSON 健康检查、比对运行时版本、写 `evidence/<C>/R1-handshake.md`（A 级）并记 `candidates.<C>.runtime`；版本不符退出码 1 | 有 `runtime` 声明的候选推不到 `TRIAL`/`DONE` |
| 封存 | `seal --id C00N` | 把 `evidence/<C>/**`、`RELEASE-REPORT.md`、`DEPLOYMENT-PLAN.md` 的 sha256 封进 `releases/<C>/verification.json` | `advance --to TRIAL` 被拒；封存后再改或新增证据 = `verify` 失败，只能出新候选 |
| 阻塞 | `block --reason "…" --owner user\|lead\|executor\|verifier\|env --kind user\|env\|tech\|external` | 在状态里记「在等谁」（等用户重启、等环境、技术卡住），并挡住 `advance` | 用「再出一个候选」掩盖等重启，台账无法解释 |

- `unblock --note "…"` 解除阻塞；`block` 期间 `advance` 会被拒（`ROLLED_BACK` 除外）。
- **已确认的 DESIGN 要改，必须走 `amend --reason "…"`**：归档旧版到 `design-history/`、状态改为 `状态：待用户确认`、自动 `block`（owner=user）、`design_version`+1。改完 DESIGN、用户重新确认后：`unblock` → 按阶段推进（还在 `DESIGN` 就 `advance --to PLAN`；在 `VERIFYING/TRIAL/DONE` 就 `advance --to EXECUTING` 开新候选；已在 `EXECUTING` 就直接冻下一候选，不敲 `EXECUTING→EXECUTING`），**不继承旧候选结论**；DESIGN 尚未确认时不用 amend，让规划师改。

## 4. 主循环（角色自动交接）

```
status → next（生成 handoffs/HANDOFF-<seq>-<role>.md）
       → team_task_create(..., blocked_by=上一任务)
       → subagent(name, cwd, prompt=交接包全文)
       → 子智能体完成自动通知 Lead
       → 亲自 verify / audit / 读回报
       → advance --to <下一阶段> --actor <角色>
       → 回到 status
```

- **子智能体之间不能通信**：交接只走磁盘 + Lead 中转，不要让它们「互相发消息」。
- **子智能体不继承对话**：派活必须给交接包全文，不能说「接着上次」。
- **`write_scopes` 只是建议**：靠任务「不做清单」+ `audit` + Lead 亲自看差异兜底。
- **git worktree（可选）**：项目是 git 仓库时，Lead 可 `create_worktree` 开隔离工作树交执行线程；候选凭证仍以 `manifest.json` 的 sha256 为准，worktree/commit 只作旁证。
- **收口两步不能省**：候选声明了 `runtime` → 先 `handshake`，FAIL 就是宿主没重启（`block --owner user`），**不要靠出新候选掩盖**；报告写完 → 必须 `seal`（先把 `DEPLOYMENT-PLAN.md` 的 `## 下一步` 定稿，`seal` 之后一个字节都别再动，否则 `verify` 判「封存后被改」）。
- **DSH 重启后角色消失**：别重做磁盘产物，按当前 `state.json` 用 `next --role <原角色>` 重派同一交接包即可。

## 5. 命令速查

```powershell
$PY $FLOW init      -p <项目> -f <feature> [--scope src] [--kind plugin] [--no-graph] [--graph-timeout 300]
                                                   # plugin = 同时生成 <项目>/pack 能力包骨架
                                                   # 默认维护项目根 .graphifyignore 并自动建图（失败只降级、退出码 0）
$PY $FLOW baseline  -p <项目> -f <feature>
$PY $FLOW status    -p <项目> -f <feature>
$PY $FLOW next      -p <项目> -f <feature> [--role <角色>] [--key-note "文本|@文件"] [--memories-dir <目录>] [--no-context] [--max-context-chars 3000]
                                                   # 交接包默认带「已知上下文」四子块 + 按阶段裁剪的角色要点
$PY $FLOW lesson    -p <项目> add --symptom "…" --cause "…" --fix "…" --tags executor[,verifier] [--role executor]
$PY $FLOW lesson    -p <项目> list [--role executor]
$PY $FLOW scope     -p <项目> -f <feature> --add .graphifyignore   # 存量补正：只追加 state.scope，不动 baseline.json
$PY $FLOW advance   -p <项目> -f <feature> --to <阶段> --actor <角色>
$PY $FLOW freeze    -p <项目> -f <feature> --id C001 --from <dev目录> [--scope src]
$PY $FLOW freeze    -p <项目> -f <feature> --id C001 --from <dev目录> --reused "V4:roles/*.md 与 ops/code-graph.md 逐字节未变"
$PY $FLOW verify    -p <项目> -f <feature> --id C001
$PY $FLOW drop      -p <项目> -f <feature> --id C001 --reason "作废理由"   # 作废候选：releases/evidence 移入 archive/，只移动不删除
$PY $FLOW audit     -p <项目> -f <feature> [--strict]
$PY $FLOW evidence  -p <项目> -f <feature> --check P1 --grade A --command "..." --output "..."
$PY $FLOW gate      -p <项目> -f <feature>
$PY $FLOW drive     -p <项目> -f <feature> [--json]
                                                   # 只读合成：phase / 候选 / 下一角色 / 门禁(硬+软) / 阻塞 / 能否推进 / 建议命令
                                                   # 不写 state.json、不生成交接包、不写 health.json；退出码与 gate 对齐
$PY $FLOW ledger    -p <项目> -f <feature> [-m "备注"]
$PY $FLOW doctor    -p <项目> -f <feature>
$PY $FLOW inspector -p <项目> -f <feature> [--json|--out 文件]   # 生成可粘进 schedule_create 的巡检 prompt
$PY $FLOW health    -p <项目> -f <feature> [--out 文件] [--no-gate] [--json]
                                                   # 输出 docs/<feature>/health.json（阶段/门禁/候选/封存/最近台账）
$PY $FLOW dashboard -p <项目> [--root 扫描根] [--gate [--to <阶段>]] [--strict] [--json]
                                                   # 多 feature 看板（扫描 **/docs/*/state.json；不需要 -f）
$PY $FLOW block     -p <项目> -f <feature> --reason "…" [--owner user|lead|executor|verifier|env] [--kind user|env|tech|external]
$PY $FLOW unblock   -p <项目> -f <feature> [--note "…"]
$PY $FLOW amend     -p <项目> -f <feature> --reason "…"          # DESIGN 变更：归档旧版、置为待用户确认、自动 block
$PY $FLOW handshake -p <项目> -f <feature> [--id C001] [--url <健康检查>] [--expect <版本>] [--field version|data.version] [--timeout 10]
$PY $FLOW seal      -p <项目> -f <feature> [--id C001]
```

本期新增命令（`$FLOW` 即 `<流程包根>\tools\dsh_flow.py` 的绝对路径，展开后形如 `<flow-home>\tools\dsh_flow.py`；禁止写 `flow.py` 这类相对名）：

```powershell
& $PY "<flow-home>\tools\dsh_flow.py" block     -p <项目> -f <feature> --reason "等用户重启 DSH 以加载插件宿主半" --owner user --kind env
& $PY "<flow-home>\tools\dsh_flow.py" unblock   -p <项目> -f <feature> --note "用户已重启，握手 PASS"
& $PY "<flow-home>\tools\dsh_flow.py" amend     -p <项目> -f <feature> --reason "汇总口径从按天改为按周"
& $PY "<flow-home>\tools\dsh_flow.py" handshake -p <项目> -f <feature> --id C001 --expect 0.4.1 --url "http://127.0.0.1:61081/plugin-health"
& $PY "<flow-home>\tools\dsh_flow.py" seal      -p <项目> -f <feature> --id C001
& $PY "<flow-home>\tools\dsh_flow.py" drop      -p <项目> -f <feature> --id C001 --reason "freeze 时 runtime 参数写错，作废"
```

`freeze` 新增 runtime 参数（有运行时必带，否则事后没有期望版本可比）：

```powershell
& $PY "<flow-home>\tools\dsh_flow.py" freeze -p <项目> -f <feature> --id C001 --from <dev目录> `
  --runtime-kind plugin --runtime-version 0.4.1 `
  --health-url "http://127.0.0.1:61081/plugin-health" --requires-restart
```

- `--runtime-kind`：`plugin|service|cli|none`；`--runtime-version`：装完之后运行时会自报的版本（声明了 kind 就必须给）。
- `--health-url`：返回 JSON 且含版本字段的健康检查地址；`--requires-restart`：装完必须重启宿主才生效。
- `manifest.json` 会因此多出 `runtime{kind,version,health_url,requires_restart}` 与 `seal_required: true`。
- `handshake` 的 `--field` 默认 `version`，版本在嵌套字段时写 `data.version`；实际版本与期望不一致时退出码 1。

**作废候选用 `drop`，不要手工删目录**：`drop` 把 `releases/<C>` 与 `evidence/<C>` **移动**到 `docs/<feature>/archive/<C>-<时间戳>/`（附 `DROP-NOTE.md` 记理由与还原方法），并从 `state.candidates` 移除——只有这样才能让 `status` 不再打印「待重启生效: C001」。已 seal 的候选默认拒收（封存件是「通过结论」的载体），确需作废要显式加 `--force`。

**建图是 `init` 的默认步骤**：`init` 会先维护项目根 `.graphifyignore`（缺行只追加、不删用户行、幂等），再按「有图走 `graphify update`、无图走 `graphify extract --code-only`」自动建图；失败（CLI 缺失/超时/报错）只打 `⚠` 与手工命令，**退出码仍是 0**，`--no-graph` 可整套关掉，`--graph-timeout` 改超时（默认 300s）。之所以必须配 `.graphifyignore`：本项目不带它建图是 2378 节点 / 26.8s，其中约 89% 是 `docs/*/releases/*/files/` 的封存副本；带上后 269 节点 / 6.5s。`init` 仍会打印 `graphify` 与 `& "<gitnexus-tools>\gitnexus.cmd" analyze "<项目根>" --skip-git` 两条手工提示：GitNexus 必须走 wrapper（内含 OpenSSL 3 的 PATH），非 git 目录不加 `--skip-git` 会空转十几分钟后报 `Not inside a git repository`，所以**只打印不自动跑**。

**教训库是跨 feature 的**：`lesson add` 追加到 `ops/lessons.md`（自动取下一个 `L00n`）；`next` 生成交接包时按角色注入「同类坑」（角色条 ≤3 + `all` 条 ≤2）。缺 `--symptom`/`--fix` 退出码 2（命令行契约，不是阶段门禁）。它不写 `state.json`，也不参与 `gate`。

## 6. 不变量

1. 不删/不改 `evidence/` 与已冻结的 `releases/`。
2. 无证据不算通过：`evidence/<候选>/<check>.md` 带命令、退出码、A/B/C/D 等级。
3. 候选不继承结论：`C002` 必须重新冻结、重新验证；复用检查要写理由。
4. 三态结论只有用户能说「完整业务验收通过」。
5. `--force` 必须带 `--reason`，会进台账。
6. 插件/能力包类项目：**运行时版本不一致时不得宣布「已上线」**——`handshake` FAIL（实际版本 ≠ `manifest.runtime.version`）就是宿主半还是旧版，先重启再握手，不要出新候选。
7. **DESIGN 变更必须 `amend` + 用户重新确认**：手改已确认的 `DESIGN.md` 再继续跑，等于伪造确认；`amend` 会归档旧版并自动置为「待用户确认」。
8. 封存后不许再改证据：`seal` 之后动 `evidence/<C>/**`、`RELEASE-REPORT.md`、`DEPLOYMENT-PLAN.md`，`verify` 直接判失败，只能出新候选。

## 7. 角色说明书

派活时用 `& $PY "<流程包根>\tools\dsh_flow.py" next -p <项目根> -f <feature>` 生成的交接包：**它已经带项目上下文**（§1 已知上下文：图谱摘要 / 上一候选已报的坑 / 同类坑 / 项目关键事实，含 `KEY.md` 直读）与**按阶段裁剪的角色要点**（§2，必保五节 + 指针，完整说明书随时可读）。手工派发时读：
`roles/00-lead.md`、`01-planner.md`、`02-executor.md`、`03-verifier.md`、`04-inspector.md`。
