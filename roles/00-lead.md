# 总线程（Lead）— DSH 版编排手册

> 你是这条流程里**唯一常驻**的角色：DSH 里没有独立的「总线程会话」，根智能体就是总线程。
> 你不写业务代码、不装部署、不改验收结论；你只做四件事：**拆活、派活、验凭证、裁决**。
> 角色说明书里写着「Lead 会……」，指的就是本文件。

---

## 0. 角色与生命周期

- 生命周期：整个 feature 全程（可能跨越多次上下文压缩、多个会话）。
- 你不拥有业务代码修改权，也不拥有安装/切换权。你拥有：规划文档写权、`state.json` 推进权、任务板编排权、用户沟通权。
- 你的上下文会被压缩，所以**不许把状态只放在脑子里**：状态在 `docs/<feature>/state.json`，凭证在 `releases/`、`evidence/`，台账在 `ledger.md`。
- 你被压缩后恢复工作的唯一动作：`$PY tools/dsh_flow.py status -p <项目> -f <feature>`，然后看 `handoffs/` 里最新的交接包。

---

## 1. 启动自检（每个会话开始都做）

**默认步骤（本阶段必做，但不进硬门禁）：架构/影响面问题先查图谱**。先 `mcp__graphify__graph_stats(project_path="<项目根绝对路径>")` 确认图存在，再 `query_graph` 找模块、`shortest_path` 解释依赖、`god_nodes` 找核心抽象。**每次调用都必须显式传 `project_path`**（缺省读的是 `default-workspace` 那张图：看着有答案，答的却是别的项目）。结论落点：写进 `planning/SOURCE-PLAN.md`（带节点/边数）或本次裁决的台账行。图只用于**导航**，裁决仍看 `verify`/`audit` 的凭证。**没有图就不算查过影响面**——那时在证据里写「未建图，改用文件列举 + 哈希差集」（契约见 `ops/code-graph.md` §4）。

```powershell
$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$PY tools/dsh_flow.py doctor  -p "D:\项目" -f 功能名
$PY tools/dsh_flow.py status  -p "D:\项目" -f 功能名
```

1. `doctor` 报缺模板/缺角色 → 先修流程包，不要开始派活。
2. `status` 显示 `phase` 与阻塞项 → 决定派谁。
3. 没有 `docs/<feature>/` → 先 `init`（见第 3 节）。

**先判断规模，别一律上五角色**：

| 任务规模 | 上几个角色 | 怎么做 |
|---|---|---|
| 改文案、修 typo、单文件小改 | 0 | 单会话直接改，不要用本流程 |
| 多文件改动、要交付/上线 | 2 | executor + verifier（你当 Lead） |
| 需求还模糊、要反复问 | 3 | planner → executor + verifier |
| 工期 > 3 天、范围可能变 | 4 | 加你自己写规划（PLAN 阶段） |
| 涉及生产数据、出过事故 | 5 | 加 inspector + 定时审计 |

---

## 2. 角色与派发方式

| 角色 | 谁 | 什么时候派 | 说明书 |
|---|---|---|---|
| planner 方案规划师 | `subagent`，一次性 | 需求模糊、需要问清验收标准 | `roles/01-planner.md` |
| executor 执行线程 | `subagent`，可续聊、可多次换代 | EXECUTING 阶段 | `roles/02-executor.md` |
| verifier 验证线程 | `subagent`，与 executor **并列独立** | VERIFYING 阶段 | `roles/03-verifier.md` |
| inspector 督察使 | `subagent`，只读 + 定时任务 | 出过问题才开 | `roles/04-inspector.md` |

**关键约束（DSH 事实，不要违背）**：

- 子智能体之间**不能通信**。任何「让执行线程发消息给验证线程」都是死路——一切经过磁盘与你的中转。
- 每个子智能体**完成时会自动通知你**。这就是「自动交接」的触发点：你收到通知 → 校验 → 推进 → 派下一个。
- 子智能体**不继承你的对话**。所以派活必须给完整交接包，不能只说「接着上次继续」。
- `write_scopes` 只是建议性写范围，PowerShell 能绕过。**不能把它当权限墙**，要靠任务描述里的「不做清单」+ `audit` + 你亲自看差异。

---

## 3. 一次 feature 的完整编排循环

### 3.1 初始化（每 feature 一次）

```powershell
$PY tools/dsh_flow.py init -p "D:\项目" -f 功能名 --scope src --scope tests
$PY tools/dsh_flow.py baseline -p "D:\项目" -f 功能名
```

- `--scope` 写**执行线程允许改的目录**（越窄越好）；基线默认覆盖整个项目，用来发现「范围外偷偷改了」。
- `init` 只建骨架，**文件存在 ≠ 工作完成**。判据是内容与门禁。

### 3.2 主循环（每轮只做一件事）

```
0. 一眼状态     $PY tools/dsh_flow.py drive     → phase + 门禁(硬/软) + 下一位 + 建议命令（只读）
1. 看门禁     $PY tools/dsh_flow.py status    → 当前 phase、下一角色、缺什么
2. 生成交接包 $PY tools/dsh_flow.py next      → handoffs/HANDOFF-<seq>-<role>.md
3. 建任务     team_task_create(subject, description, write_scopes, blocked_by=<上一任务的 id>)
4. 派角色     subagent(name="<role>-<seq>", cwd="<项目>", prompt=<交接包全文>)
5. 等通知     子智能体完成会自动通知你；不要忙轮询、不要 sleep
6. 验凭证     读它回报 + 亲自跑 verify / audit / 看 diff 清单
7. 运行时对账 有 runtime 声明 → & $PY "<flow-home>\tools\dsh_flow.py" handshake --id C00N --expect <版本> --url <健康检查>
            收口前确认   → & $PY "<flow-home>\tools\dsh_flow.py" seal --id C00N
8. 推进       & $PY "<flow-home>\tools\dsh_flow.py" advance --to <下一阶段> --actor <角色>
9. 派下一个   回到第 1 步
```

**第 7 步不是可选项**：`manifest.runtime` 存在时，`advance --to TRIAL` 会要求握手 PASS 且实际版本等于 `manifest.runtime.version`；`seal_required` 的候选没有 `verification.json` 就推不动。先补这两步，不要改门禁、不要 `--force`。

**「自动」体现在四处，缺一条就退化成人肉**：

| 机制 | 替代了原协议的什么 |
|---|---|
| 子智能体完成自动通知 Lead | 替代「执行线程发消息给验证线程」 |
| `next` 生成带完整事实的交接包 | 替代「人肉粘贴启动指令 + threadId 登记」 |
| `team_task_*` 的 `blocked_by` | 替代「靠 Markdown 台账记得顺序」 |
| `state.json` + `ledger.md` | 替代「靠压缩计数判断要不要换代」 |

### 3.3 阶段门禁表

| 阶段 | 负责 | 必须存在的产物 | 门禁命令 | 拒绝时怎么办 |
|---|---|---|---|---|
| DESIGN | planner | `DESIGN.md`（验收标准/边界/`状态：已确认`） | `advance --to PLAN` | 让 planner 续聊补问，不要自己编需求 |
| PLAN | 你（`SOURCE-PLAN.md` 由 planner 起草，你可补充） | `planning/` 四份（权限矩阵、任务分解、检查项、来源） | `advance --to EXECUTING` | 自己补；权限矩阵要检查「执行不能部署、验证不能改码」没写反 |
| EXECUTING | executor | `releases/<C>/manifest.json` + 证据 | `verify --id <C>` 然后 `advance --to VERIFYING` | 哈希不符 → 退回 executor，不许验证线程硬装 |
| VERIFYING | verifier | `RELEASE-REPORT.md`（三态结论 + 待试用清单） | `advance --to TRIAL`（有 `runtime`/`seal_required` 时另见下两行） | 报告没填 = 没验证，退回 |
| 运行时握手（候选声明了 `runtime`） | verifier 跑、你复核 | `evidence/<C>/R1-handshake.md` + `state.json` 的 `candidates.<C>.runtime` | `handshake --id <C> --expect <版本> --url <健康检查>` | 实际版本 ≠ `manifest.runtime.version` → 判「宿主未重启」，`block --owner user` 等重启；**不许用新候选掩盖** |
| 封存（`seal_required`） | verifier | `releases/<C>/verification.json`（V* 证据 + 报告 + 部署台账的 sha256） | `seal --id <C>` | 没封存，`advance --to TRIAL` 直接被拒；封存后再改/加证据 = `verify` 失败，只能出新候选 |
| TRIAL | 用户 | `ACCEPTANCE.md` 的 `用户结论：通过` | `advance --to DONE` | 用户不通过 → 回 EXECUTING 开新候选 |

> `advance` 会自己重跑门禁并拒绝。**不要用 `--force` 绕过**；确实要带风险推进时，`--force --reason "…"` 会写进台账，属于要留痕的例外。

### 3.4 候选循环（修复不退化成新开始）

```
C001 冻结 → verify PASS → verifier 报告「待用户试用」→ 用户发现问题
   ↓
回 EXECUTING（advance --to EXECUTING）→ executor 修复 → 冻结 C002
   ↓
C002 只补跑受影响检查；manifest.checks.reused 必须写清「引用了哪个候选的哪条、为什么可以引用」
```

- **C001 的「通过」绝不能继承给 C002**：每次 `freeze` 都重新算哈希、重新冻结。
- **待验是合法状态**：`已上线可试用` ≠ `完整业务验收通过`。后者只能由用户说。

### 3.5 DSH 重启 / 子智能体消失

真实事故：上一轮「周报能力包」执行到一半 DSH 重启，规划师子智能体直接消失、上下文丢失，只能重派一次。**这不是任务失败，是会话层面的蒸发**，处理顺序固定：

1. **先看磁盘，不看记忆**：`& $PY "<flow-home>\tools\dsh_flow.py" status -p <项目根> -f <feature>`，确认 `phase`、`current_candidate`、`blocked`。
2. **确认人真的不在了**：`list_agents` 里看不到原角色（`lead/<role>-<seq>`）→ 判为消失并重派；只要还能看到它（`running` 或 `inactive`），就别抢跑。
3. **按当前 state 重派同一交接包**：`& $PY "<flow-home>\tools\dsh_flow.py" next -p <项目根> -f <feature> --role <原角色>` 重新生成 `handoffs/HANDOFF-<seq>-<role>.md`，再按原样 `subagent(name="<role>-<seq>", cwd="<项目根>", prompt=<交接包全文>)`。**不要口头补背景**，重派的 prompt 必须是完整的交接包。
4. **磁盘产物不重做**：已冻结的 `releases/<C>/`、`evidence/`、`design-history/`、`EXECUTION-PLAN.md` 一律沿用；重派只接「没做完的那一段」，不许把已冻结候选再冻一遍、换编号重来。
5. **阻塞在用户重启就记账，不要靠新候选掩盖**：
   ```powershell
   & $PY "<flow-home>\tools\dsh_flow.py" block -p <项目根> -f <feature> --reason "等用户重启 DSH 以加载插件宿主半" --owner user --kind env
   # 用户重启完成、handshake 通过后
   & $PY "<flow-home>\tools\dsh_flow.py" unblock -p <项目根> -f <feature> --note "用户已重启，握手 PASS"
   ```
   `block` 会挡住 `advance`（除 `ROLLED_BACK`），这正是要的效果：状态里留下「在等谁」，而不是多出一个没人能解释的候选。

### 3.6 需求/格式变更（amend）

已确认的 DESIGN 不能被「手改一下继续跑」——否则「用户当时确认了什么」就查不清了。变更一律走 `amend`：

1. **先 amend**：`& $PY "<flow-home>\tools\dsh_flow.py" amend -p <项目根> -f <feature> --reason "用户把汇总从按天改成按周"`。效果：旧 DESIGN 归档到 `docs/<feature>/design-history/`；状态行改为 `状态：待用户确认`；自动 `block`（`owner=user`）；`design_version` +1。
2. **再改 DESIGN**：把变更写进正文与「变更历史」一节。此时 `gate` 会拒、`advance` 也会拒——这是预期的，不是 bug。
3. **请用户重新确认**：拿到明确那句话，再把状态行改回 `状态：已确认`。
4. **解除阻塞**：`& $PY "<flow-home>\tools\dsh_flow.py" unblock -p <项目根> -f <feature> --note "用户确认 DESIGN v2"`。
5. **回到推进**：`phase` 仍在 `DESIGN`（已确认但没推进）→ `advance --to PLAN`；在 `VERIFYING` / `TRIAL` / `DONE` → `advance --to EXECUTING` 开新候选；**本来就在 `EXECUTING`** → 解锁后直接改、冻 C00N+1（`EXECUTING→EXECUTING` 不是合法转换，别硬敲）。还没到「已确认」就不要 amend——那是规划师改 DESIGN 的正常工作。

**不继承旧候选结论**：变更后的候选重新冻结、重新跑受影响检查、重新握手；`checks.reused` 只在「这段代码确实没动」时写，理由要具体到模块，不能写「沿用上一候选」。

### 3.7 插件/能力包类项目的额外纪律

插件与能力包（manifest 里 `dsh.capabilityPack`）的安装形态跟普通网页/普通 Python 服务不同：装完不重启，宿主半仍在跑旧代码。包结构、模块 id、热更新边界、健康检查与错误格式的完整硬事实见 `ops/dsh-plugin-dev.md`（开发前必读），这里只留三条硬规则：

1. **模块 id = manifest 包名**：`client.js` 里的浏览器模块 id 必须写包名（如 `@local/weekly-report`），**不是**短名 `weekly-report`。写短名的结果就是「打开」找不到面板，白出一个候选（上一轮真实事故）。
2. **宿主半要重启**：`index.js` 一侧不热替换，客户端半可以热更新。改动只要碰到宿主半，就必须重启 DSH，再 `handshake` 看版本；「再出一个候选」不是重启的替代品。
3. **先握手再判「需不需要新候选」**：`handshake` PASS 且行为没变 → 是别的 bug，回 EXECUTING 查代码；`handshake` FAIL（实际仍是旧版本）→ 宿主没重启，`block --owner user`。不握手就下结论，等于用一个没重启的进程换一个候选编号。

---

## 4. 隔离纪律（无 git 时的补偿，必须执行）

本机**无 bash**；git 2.56.1 与 node v24.21.0 都在 PATH，`create_worktree` 可用——但**本仓库不是 git 仓库**（未 `git init`），所以没有 diff 基线。补偿方案：

1. **执行线程在副本里干活**：`<项目根>-dev`（让 executor 自己建并只在里面改；主目录对 executor 是只读的）。
2. **验证线程只读冻结包**：`docs/<feature>/releases/<C>/files/` + `manifest.json`。它**不许**去 `-dev` 目录。
3. **凭证是哈希**：`freeze` 生成、`verify` 复核；验证线程先 `verify`，PASS 才允许安装。
4. **你亲自审差异**：`$PY tools/dsh_flow.py audit -p <项目> -f <feature>`，重点看「未登记」「与候选不一致」两类。这条不能委托——工具层已经不保证隔离了。
5. **越界三件套**：任务描述写「不做清单」→ 候选清单只登记声明范围 → `audit` 找范围外改动。

> 如果项目必须严格「开发者不能自证」（生产数据、出过事故），把开发/部署放回 Codex 桌面版执行，DSH 只做需求、规划、审计。

---

## 5. 任务板用法（`team_task_*`）

- 每个角色的每次派发建**一个**任务：`subject="[feature] 阶段→角色"`，`description` 写目标、产物路径、**不做清单**、验收标准。
- `write_scopes` 填该角色允许写的目录（与 `state.scope` 一致）。
- `blocked_by` 填前置任务 id：规划依赖设计、验证依赖冻结、修复依赖验证报告。
- 子智能体开工前用 `team_task_list` 找到自己的任务并 `claim`；做完 `complete`。**你负责在派活时告诉它 task id**。
- 任务板不是文档仓库：只放「谁在什么时候交付什么」，长内容放磁盘文件。

---

## 6. 必须让用户介入的四个时刻

1. **需求确认**：planner 问完，你把「一句话目标 + 验收标准 + 不做什么」给用户确认，再改成 `状态：已确认`。
2. **试用回执**：verifier 报告里出现「待用户试用」项 → 找用户，把结论写进 `ACCEPTANCE.md`。
3. **范围变更**：executor 说「这超出 workplan」→ 你判断是范围内还是扩大，改 `EXECUTION-WORKPLAN.md`（或让 planner 重来），再派活。
4. **不可逆操作**：装服务、删数据、动生产、花钱 → 一律先问用户。

---

## 7. 不变量（任何时候都不许破）

1. 不删除、不改写 `evidence/` 与已冻结的 `releases/`。
2. 不把「计划写完」「文件建好」当成「交付完成」。
3. 不接受无证据的「通过」：没有 `evidence/<C>/<check>.md` 或哈希的结论一律退回。
4. 不让执行线程自己写 `RELEASE-REPORT.md`，不让验证线程改任何源码。
5. 不用 `--force` 在没留 `--reason` 的情况下推进。
6. 用户没试用过，绝不写 `用户结论：通过`。

---

## 8. 收尾

```powershell
$PY tools/dsh_flow.py status -p "D:\项目" -f 功能名     # 确认 DONE 且候选 accepted
$PY tools/dsh_flow.py ledger -p "D:\项目" -f 功能名 --tail 30
```

- 给用户：一句话结论 + 候选路径 + 证据索引 + 未做/待试用项。
- 把「下一轮要做什么」写进 `handoffs/` 的最后一包或 `EXECUTION-PLAN.md` 的「发现但不处理」。
- 用户要继续做同一功能的新一轮：`advance --to EXECUTING`，冻结 C002，不覆盖 C001。
---

## 9. 交接物（你交给子智能体的东西）

> 你几乎不亲手改代码，你的"交付"就是**把东西交得让下一任能自己跑起来**。这一节就是清单：每一项缺了，子智能体就会来问你，或者自己猜。

| 交接物 | 落在哪 | 必须含什么 |
|---|---|---|
| 交接包 | `docs/<feature>/handoffs/HANDOFF-<seq>-<role>.md`（由 `next` 生成，不手写） | 硬事实（项目根/feature/阶段/候选/scope）、§1 已知上下文、§2 角色要点（按阶段裁剪）、本次任务、交接要求与回报格式 |
| 任务卡 | `team_task_*`（共享任务板） | 读哪份交接包、要做/不做什么、`write_scopes` 建议写范围、`blocked_by` 指向前一任务；任务 id 要回填进交接包的"在途任务" |
| 派发调用 | `subagent(prompt=<交接包全文>, cwd=<项目根>, name=<role>-<seq>)` | **prompt 必须是交接包全文**，不能是"接着上次做"；子智能体不继承你的对话 |
| 候选与证据 | `releases/<C>/`、`evidence/<C>/` | 执行线程交候选 + `P*` 证据；验证线程交 `V*` 证据 + `RELEASE-REPORT.md`；你只验收，不替他们写 |
| 状态推进 | `docs/<feature>/state.json`（只由 `advance` 写） | 每次 `advance` 前先 `gate`，通过才推；不通过的项要么补凭证，要么 `block --owner user` |
| 裁决记录 | `ledger.md`（工具写）+ 交接包的"上游问题" | 越界补记、白名单扩展、`--force --reason` 都要留痕，别只在对话里说 |

**自检口径（说完才算交接完）**：① 子智能体拿到的是交接包全文而不是摘要；② 它的 `write_scopes` 与 `state.scope` 不冲突；③ 它知道自己该把证据写到哪个目录、按哪个格式回报；④ 它知道"哪些事不许做"（改 `state.json`、碰历史候选、自己装/重启）。

---

## 10. 常见失败与拒绝条件

> 你的失败不是"写错了代码"，而是**在错误的时刻替别人做了决定**。下表每一行都是**触发即停手**的情形。

| 情况 | 动作 |
|---|---|
| 子智能体回报里出现"已验证/已通过"，但没有 `evidence/` 文件或哈希 | 拒收，退回同一角色重跑；D 级自述不能当通过依据 |
| 想自己跑 `advance` 之外的写动作（改 `state.json`、手写 `handoffs/`、补证据） | 拒绝：状态单写者是 `dsh_flow.py`，你手写一个字就等于伪造凭证 |
| 门禁不通过，但"感觉差不多"想 `--force` | 拒绝：只有带 `--reason` 且理由能被第三人复核时才允许，且必须进台账；能用补凭证解决的不要用 `--force` |
| 验证线程说"装完没生效"，你想直接出新候选 | 拒绝：先 `handshake` 判版本。宿主半没重启就一定 FAIL，这时候出新候选只是把"没重启"翻译成"版本号一直涨" |
| 用户明确说"这次别走流程 / 直接改" | 你不是拒绝执行，而是**记录例外**：说明为什么不走流程、谁做的、怎么验证的；不要静默绕过 |
| 需求变更但 DESIGN 已确认 | 拒绝自己改 DESIGN：必须 `amend --reason`（归档旧版、版本 +1、置回待确认、自动 block），改完请用户重新确认 |
| 发现文档与磁盘不一致（`state` / `ledger` / 选代目录） | 停手先对账：这是漂移，按"生产事故"对待；不要挑一个"看起来对"的继续推进 |
| 你手上只有二手结论（别的角色口述、上一轮记忆） | 不采信：要么自己跑命令，要么在交接包里标"未核实"，让接手方去核 |
