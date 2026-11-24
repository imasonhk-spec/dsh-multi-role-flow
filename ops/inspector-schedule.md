# 督察使定时审计操作手册（Lead 专用）

> 用途：把 `roles/04-inspector.md` 变成"每天自动跑一次"。
> 前提：**默认不开**。只有出过问题才开。

## 一、什么时候才该开

| 该开 | 不该开 |
|---|---|
| 本项目出过越界或虚假完成，用户明确要求每日审计 | 只是"想有人盯着"→ 用一次性 `subagent` 复核更省 |
| 关键上线窗口（TRIAL 阶段），需要每天固定看门禁与证据 | 还没有 `state.json`/`baseline.json` → 没事实可审，先补齐 |
| 长任务跨多天、你的上下文已压缩多次，需要外部事实校准 | 你本来每天就会自己跑 gate/audit → 定时任务只是重复动作 |

判断标准一句话：**定时审计是"事故后的常设岗"，不是"默认配置"。**

## 二、开之前的三项准备

1. `$PY "<flow-home>\tools\dsh_flow.py" doctor -p <项目> -f <feature>` 跑得通（`$PY` = `~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`）
2. `docs/<feature>/state.json` 与 `baseline.json` 存在，且 baseline 早于本轮改动
3. 建议先 `team_task_create` 一条"每日审计"任务，让审计轮次在任务板上留痕

**基线口径（11-19 补充，务必遵守）**：

- `baseline` 在**每次冻结候选之前**记（插件类项目带 `--source <源码目录>`，或依赖自动发现）；`seal`/`DONE` 之后**不要重记**——重记会把 11:31–13:04 这类窗口抹成"无变化"，越界审计就失去可信基线（11-18 D5 的根因）。
- 如果确实需要重记（例如源码目录搬迁），先写一条 `ledger -m` 说明重记原因与时间，报告里标"基线重记，窗口不可回溯"。
- **已封存文件不可改**：`releases/<C>/RELEASE-REPORT.md`、`verification.json` 及被其覆盖的 `V*` 一旦 `seal`，任何改动都会让 `verify` FAIL。结论文档只回填 `ACCEPTANCE.md`；要改发布报告只能由验证线程重封存或出新候选。

## 三、生成 prompt（首选：命令）

```powershell
$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$FLOW = "<flow-home>\tools\dsh_flow.py"

& $PY $FLOW inspector -p "<项目根>" -f <feature>                        # 打印 title / rrule / prompt
& $PY $FLOW inspector -p "<项目根>" -f <feature> --out ops\inspector-prompt.md   # 同时落盘
& $PY $FLOW inspector -p "<项目根>" -f <feature> --json                 # 给脚本读
```

它会把项目根、feature、当前候选、外部源目录、报告路径**全部填实**，并按「静止短路 → 子智能体 → 自停阈值 → 纪律」生成整段 prompt。输出里不应残留 `{{`（`selftest` 有断言）。
换频率用 `--rrule`（两行字符串）；改标题用 `--title`；指定候选用 `--candidate`。

### 3.1 手工模板（仅当命令不可用）

```text
title : 每日审计 <项目简称> <feature> 越界与证据
target: this_session
rrule : DTSTART;TZID=Asia/Shanghai:YYYYMMDDT090000
        RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0
prompt: <见下方模板，占位符已手工替换>
```

要点：

- `rrule` 是**一个字符串里的两行**：DTSTART 一行 + RRULE 一行，中间是换行符（JSON 里写 `\n`）。少写 RRULE、或多塞空行都会判非法。
- `DTSTART` 必须是真实存在的本地时间；写未来的时刻没问题，首次投递从创建后的第一个满足点开始。
- `target: this_session` = 投递到你这个会话，**串行**：上一轮没跑完不会叠加，只会补投最近一次。
- 工作日版本：`RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0`（DTSTART 行不变）
- 一次性版本：`RRULE:FREQ=DAILY;COUNT=1`
- **占位符不会自动替换**：`{{PROJECT}}`、`{{FEATURE}}` 必须在调用前手工换成真实值，否则审计会对着字面量跑，报告无效。

prompt 模板（整段填进 `prompt`）：

```text
你是本项目的督察使。严格按 <flow-home>\roles\04-inspector.md 执行，不要自由发挥。
项目：{{PROJECT}}
feature：{{FEATURE}}
权限：只读。唯一允许写的是 docs/<feature>/evidence/inspector-<YYYYMMDD>.md。
必做六步（$PY = ~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe）：
0. 读 docs/<feature>/KNOWN-EXCEPTIONS.md（已知例外；命中 KE-xxx 的项不算新告警，但要核对是否仍成立/到期）
1. $PY "<flow-home>\tools\dsh_flow.py" status -p {{PROJECT}} -f {{FEATURE}}
2. $PY "<flow-home>\tools\dsh_flow.py" gate   -p {{PROJECT}} -f {{FEATURE}}
3. $PY "<flow-home>\tools\dsh_flow.py" audit  -p {{PROJECT}} -f {{FEATURE}}    ← 越界清单以此为准（含项目内/外部源/文档层三段）
4. 核对 releases/<最新候选>/manifest.json 的哈希与 RELEASE-REPORT.md 的结论三态；verification.json 抽查 ≥2 条哈希
5. 检查 state.json / ledger.md / 磁盘产物 三者是否一致（漂移）
6. 窗口快照：开始与结束各记一次 state.json/ledger.md/ACCEPTANCE.md/verification.json 的 sha256；被 Lead 并发写入时在报告标「对象移动」并以结束快照为准
回报：结论（PASS/FAIL/BLOCKED）+ 事实来源命令 + 越界清单 + 命中例外 + 需我裁决的 ≤3 条，20 行内。
命中自停条件（baseline 缺失或被改、同一越界 ≥3 次、只有 D 级自述）立刻停审并说明原因。
不要改任何文件（审计报告除外），不要部署，不要重启服务，不要用 create_worktree 改建工作区。
本会话不得被 $stop-that-shit review 武装：巡检要跑 status/gate/audit（`& $PY …` 形态），武装后这些命令必被拒，整条巡检链跑不起来。若发现本会话已被武装，立刻停止并在报告里写明原因（改用其它命令硬绕 = 伪造审计）。
```

### 3.2 巡检会话不得被 `$stop-that-shit review` 武装（硬约束）

**规则**：跑定时审计的会话**必须是未武装（OBSERVING / watch-only）会话**。不要在巡检会话里执行 `$stop-that-shit review -- …`，也不要在巡检开始前把它切到 ARMED。

**为什么**：巡检必做的 `status` / `gate` / `audit` / `health` 都是 `& $PY "…\tools\dsh_flow.py" …` 形态；STS 在 `review` 契约下按 `src/shell-analysis.cjs` 判命令：

- 只读白名单不在本文档维护：以 `src/shell-analysis.cjs` 的常量 `READ_POWERSHELL_COMMANDS`（PowerShell cmdlet）与 `READ_SHELL_COMMANDS`（前者 + 若干 unix 只读命令）为准，提取命令见 `ops/aux-tools.md` §3.1；
- 不在白名单的程序一律拒（`Get-FileHash`、`Format-Table` 同样被拒）；
- 未加引号的 `$` `{` `}` `(` `)` `<` `@` `%` `*` `?` `[` `]` `#` `` ` ``、`&`（call operator）、`>` 重定向、`&&` 一律判语法无法证明。

所以武装后巡检要么全被拒（`shell_command_unproven` / `shell_syntax_unproven`，见 `src/control-protocol.cjs`），要么逼巡检去用别的命令绕过——两者都会把「审计没跑成」变成「审计通过」的假结论。完整白名单与可用/被拒样例见 `ops/aux-tools.md` 的「武装后哪些命令形态会被拒」一节。

**替代约束（武装不是审计的前提）**：

| 想要的效果 | 用什么 | 不用什么 |
|---|---|---|
| 只读纪律 | `roles/04-inspector.md`：只读、唯一可写 `evidence/inspector-<YYYYMMDD>.md`；DSH 侧无写权扩展 = 纪律层，靠审计复核 | 不靠 `review` 硬拦 |
| 越界判据 | `flow.py audit`（基线 sha256 差集：项目内 + 外部源 + 文档层三段） + `manifest.json` 哈希 | 不靠 Guard 的 `files=` 锁 |
| 证据诚实 | 报告第 1 节贴 `status/gate/audit` 命令原文与退出码；静止短路只回一行「静止：无变化」 | 不靠「我没改文件」的自述 |

## 四、查看 / 暂停 / 删除

| 动作 | 调用 |
|---|---|
| 看有哪些 | `schedule_list`（`active:true` 只看在跑的，`active:false` 只看已停） |
| 看某一条 | `schedule_view { id }`（含 title、rrule、scheduledAt/scheduledAtLocal） |
| 暂停 | `schedule_edit { id, action:"update", active:false }` —— 定义保留、不再投递 |
| 恢复 | `schedule_edit { id, action:"update", active:true }`；若已无未来发生点，需同时给新 `rrule` |
| 改 prompt/时间 | `schedule_edit { id, action:"update", prompt:"...", rrule:"..." }` |
| 删除 | `schedule_edit { id, action:"delete" }` —— **已排队消息不会撤回** |

并发保护：带上 `expectedUpdatedAt`（上一次结果里给的值）；任务期间被别人改过会返回 `schedule_conflict`，
此时先 `schedule_view` 拿最新值再重试，不要盲目重发。

## 五、审计产物落在哪

- 报告：`<项目>/docs/<feature>/evidence/inspector-<YYYYMMDD>.md`（同日追加，不覆盖）
- 事实来源：`status/gate/audit` 的命令原文与退出码，写进报告第 1 节
- 不新建目录、不写 `ledger.md`、不往 `state.json` 追加结论

## 六、每天的最小检查清单（5 项，超过就不叫"最小"了）

1. `gate` 是否 PASS：`DESIGN.md` 的三段、`RELEASE-REPORT.md` 的清单与结论三态、`ACCEPTANCE.md` 的用户结论是否齐全
2. `audit` 的越界条目与昨天报告相比是否新增
3. 最新候选 `manifest.json` 的 sha256 与实际文件是否一致
4. `state.json` / `ledger.md` / 磁盘产物三者是否一致（漂移）
5. "需用户裁决"项是否已清零

## 八、当前已开启的定时审计

| 项 | 值 |
|---|---|
| schedule id | `schedule-201bad05-f214-4903-a269-be90fd487a93` |
| 对象 | 项目 `<weekly-report-project>` / feature `weekly-report`（旧 `001-开发\weekly-report` 已于 2026-11-20 23:37 事故删除，不再是审计对象） |
| 频率 | 每天 09:00（`DTSTART;TZID=Asia/Shanghai:20261119T090000` + `RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0`） |
| 下次投递 | 2026-11-22 09:00 +08:00（`schedule_list` 2026-11-21 实测：`scheduledAtLocal=2026-11-22T09:00:00+08:00`、`status=active`；上次投递 2026-11-21 09:00。每日滚动，**以 `schedule_list` 为唯一真源**，本行只记录最近一次核实值） |
| 投递方式 | `this_session`（回到 Lead 会话，串行） |
| 台账 | `ops/schedules.md`（id 与暂停/删除命令以那份为准） |
| 暂停 | `schedule_edit { id:"schedule-201bad05-f214-4903-a269-be90fd487a93", action:"update", active:false }` |

**静止短路**：`phase==DONE` 且 `audit` 0/0/0 且 `verify` 通过 → 只回一行"静止：无变化"，不写报告、不起子智能体；连续 7 天静止会建议暂停。这是为了省 token，别把它当成"审计失败"。

**首次巡检**：2026-11-18 人工触发一次（`evidence/inspector-20261118.md`），用于验证 prompt 可执行；之后由定时任务接续。

## 九、常见坑

- `gate` / `verify` / `audit --strict` 的**退出码 1 表示"未通过/有嫌疑"**，不是命令崩溃；报告里按结论写。
- 关机/休眠期间不投递；恢复后**只补投最近一次**错过的，不会补跑一整天；崩溃后可能重复投递一次，看到重复报告以时间最新的为准。
- 每次定时审计都是一次模型调用，会消耗 token —— 只在必要时开，进入 `DONE` 就暂停。
- `target: new` 会为每次投递开新会话，报告不回到你的上下文；需要你在场时坚持 `this_session`。
- 同一 feature 不要开两条日审计；要加频率就改现有那条的 `rrule`。
- **`audit`/`verify` 里看到 `C001 封存校验失败` 是已知历史遗留，不是新事故**（2026-11-21 起写入本手册）：`flow-quality-boost` 的 `C001` 封的是 11:47 时刻的**共用** `DEPLOYMENT-PLAN.md`，15:37 被 C002 的验证线程写过后哈希对不上，2 项不匹配全部指向它；C004 起已治本（`seal` 改封每候选快照），但历史候选**不重封、不补快照**。巡检按「已知遗留」记录，不计入自停条件、不要据此改判据或另开候选。
- **`dsh-bundle-live` 不会再出现在 `audit` 里**：2026-11-21 D 卷换 SSD 后，其残骸（7 个根级文件）已可逆归档到项目外 `<workspace>\_attic-dsh-bundle-live-20261121`；bundle 产物目录为 `dsh-bundle-dist`（`.dsh-flow-bundle-dir` 指向它，`build_bundle.py --check` exit 0）。若 `audit` 又报 `dsh-bundle-live/**`，说明有人把它捞回项目内，按越界处理并停下报 Lead。
- **巡检会话被 `$stop-that-shit review` 武装过**：`status/gate/audit` 全是 `& $PY …` 形态，必被 Guard 拒（`shell_command_unproven`），巡检会「跑不起来」而不是「发现没问题」。发现武装就停审并说明，别换命令硬绕（见 §3.2）。
