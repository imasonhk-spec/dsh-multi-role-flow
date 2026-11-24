# 定时任务台账（Lead 维护）

> **唯一台账 = 源仓库 `<flow-home>\ops\schedules.md`**（唯一可编辑的那份）。
> 安装包 `dsh-plugins\dsh-ms-dev-preset\flow\ops\schedules.md` 是**镜像副本，勿编辑，以源仓库为准**（由 preset 的 `scripts/sync-flow.ps1` 单向覆盖）。
> 登记、改行、暂停恢复都只改源仓库那份，改完跑一次 `npm run sync-flow`；看到镜像副本与它不一致时以源仓库为准。

> 定时任务由 DSH 的 `schedule_create` 创建，**属于 Host、不属于某个项目**；本文件只是人读台账，创建/修改后手工同步一行。
> 查当前真实状态：`schedule_list`（`active:true` 只看在跑）；看一条：`schedule_view { id }`。

## 当前登记

| id | 项目 / feature | 频率（本地） | 下次投递 | 用途 | 暂停 / 删除 |
|---|---|---|---|---|---|
| `schedule-201bad05-f214-4903-a269-be90fd487a93` | `<weekly-report-project>` / `weekly-report`（旧 `001-开发\weekly-report` 已于 11-20 事故删除） | 每天 09:00（Asia/Shanghai） | 2026-11-22 09:00 | 督察使日审计：门禁 / 越界（项目内 + 外部源）/ 证据与封存 / 漂移；静止则一行回报、不起子智能体；`blocked.owner=user` 时只回 3 行 | `schedule_edit { id, action:"update", active:false }` / `schedule_edit { id, action:"delete" }` |

## 最近巡检

| 时间（Asia/Shanghai） | 触发 | 结论 | 报告 | 处置 |
|---|---|---|---|---|
| 2026-11-18 14:20 | 人工（首次，验证 prompt） | **FAIL（文档级）**：D1 陈旧运行时结论、D2 待验项与用户结论不一致、D3 更新时间/必填项、D4 与已封存报告的时序 | `evidence/inspector-20261118.md` | Lead 已回填 `ACCEPTANCE.md`（§二 五项标 D 级确认、§六 时序说明、§七 变更记录）；**未改**已封存的 `RELEASE-REPORT.md` |
| 2026-11-19 09:00 | 定时（首次投递） | **PASS**（D1–D4 已闭环；1 项 L1；D5 基线盲区仍在；D6 审计窗口与 Lead 写入重叠） | `evidence/inspector-20261119.md`（12128 B） | 回填 ACCEPTANCE（已做）+ 刷新 `health.json`（已做）；`install-manifest.json` 待 ROADMAP P1-7；D5/D6 记 P0-9/10/11 |
| 2026-11-20 09:00 | 定时 | **静止短路**（项目内 0/0/0；外部源仅 KE-001；文档层仅 state/ledger/health 预期写入；verify 通过） | 无（静止不写报告） | 发现 dev 源 39 个工具缓存文件（`.gitnexus/`、`graphify-out/`）→ 已加入 `SKIP_DIR_NAMES` 并补 selftest L 套（123 步）。**注（2026-11-21 09:35 更正）**：KE-001（`install-manifest.json` 例外）随旧项目 `001-开发\weekly-report` 在 11-20 23:37 事故中消失而**失效**；继任项目 `103-周报` 没有 `KNOWN-EXCEPTIONS.md`，本行历史保留、不再作为现行例外 |
| 2026-11-22 09:00 | 定时 | **PASS**（C004/DONE：gate 8/8、verify 通过、封存 16/16、/health=0.1.2=manifest；audit 11 告警 = 10 条冻结前开发期新增误报 + 1 条 `ops/lessons.md` 未登记） | `103-周报\docs\weekly-report\evidence\inspector-20261122.md`（22.2 KB） | 已 `scope --add ops` 收口 lessons.md；已修 audit 判定（新增文件按 mtime vs 冻结时间区分；`ops/lessons.md` 视为 lesson 工具生成）；bundle 重建 1.2.6；selftest **453 步 0 失败** |

> 巡检行只追加、不改历史；报告结论以对应 `evidence/inspector-<日期>.md` 为准。

## 封存包异地副本：方案 A / 方案 B 的分工与时间窗口（flow-backup-a）

> 背景：2026-11-20 23:37 误删事故永久丢了 5 个候选的 `manifest.json` / `verification.json` / `files/`。
> 实测把 243 个会话日志全量解压统计后，这三类文件的 **write/edit 命中数 = 0** —— 它们是**工具写**的凭证，
> 不在会话日志里，**回放永远补不回来**。所以副本只能靠「主动复制」，不能靠「事后重建」。

| 方案 | 谁触发 | 时间窗口 | 覆盖范围 | 落点 | 失败语义 |
|---|---|---|---|---|---|
| **A：seal 快照**（已实现） | `dsh_flow.py seal` 自动执行 | **seal 成功的那一刻**（`EXECUTING → VERIFYING → TRIAL` 之间，二级窗口） | 该次 seal 的**整个** `docs/<feature>/`（含 `releases/`、`evidence/`、`planning/`、`state.json`、`baseline.json`、`ledger.md`、`ACCEPTANCE.md`、`DESIGN.md`） | `%USERPROFILE%\.dsh\flow-snapshots\<项目目录名>\<feature>\<C>-<yyyyMMdd-HHmmss>\` | 只打印 `⚠ 快照失败` + `ledger.md` 记 `backup-failed`，**seal 退出码仍 0**（保险失败不等于封存失败） |
| **B：每日 robocopy**（外部定时任务） | DSH 定时任务 `schedule-c93da418`（登记见上方「当前登记」表，现读以 `schedule_view { id }` 为准） | **每天 03:00**（Asia/Shanghai；避开 09:00 巡检与人工操作时段） | D 盘项目的 `docs/**` **全量镜像**（所有 feature、所有候选，含 A 漏掉的历史件） | `~/.dsh\flow-backup\` | 任务失败只影响「今天的全量镜像」，不影响任何 seal 结论 |

**为什么要两个都要，而不是二选一**：

1. **粒度不同**：A 是「每候选一份、seal 当刻的完整树」，能精确回滚到某个候选；B 是「每天一份全量快照」，
   只能回到「昨天 03:00 的样子」。事故里最常要的是前者（某个候选的三个件），A 的更直接。
2. **窗口互补**：A 的窗口是 seal 之后到 B 的下一次投递之间（最长 ~24 小时）；B 的窗口是「一天之内所有 seal」。
   两者叠加后，任何已封存候选最坏情况下也有「最近的 A 副本」或「昨天的 B 镜像」之一。
3. **A 可能被关掉**：`seal --no-backup` 或 A 失败（磁盘满/权限）时只剩 B。反过来 A 覆盖了 B 的断电窗口
   （每日任务在关机/休眠期间不投递，恢复后只补投最近一次）。

**不做的事**：本轮**不做**自动清理/轮转（避免误删，保留策略交给外部脚本）；A 的副本**只增不删**，
一次 seal 约 1 MB，C 盘余量 4.3 GB 够一年多。

### 恢复语义（重要，别把状态机一起回滚）

回填时**只回这三样**：`releases/<C>/manifest.json`、`releases/<C>/verification.json`、`releases/<C>/files/**`。

**不要**把 `state.json` / `baseline.json` / `ledger.md` 盖回项目——它们是**状态机与台账**，
用旧副本覆盖会让 `phase` 回退到旧阶段、台账回退、`audit` 基线错位（等于用副本伪造出「什么都没发生过」）。
候选件回填后按顺序自查：`verify --id <C>` → 应「封存校验通过」；`doctor` → 快照健康一项应回到 ✅。

## 规则

1. **同一 feature 只开一条日审计**；要加频率就改现有那条的 `rrule`，别新建。
2. 进入 `DONE` 且连续静止 ≥7 天后，巡检会回报"建议暂停"；确认暂停用上面的 `schedule_edit`。
3. 暂停是**保留定义、停止投递**；恢复用 `active:true`（若已无未来发生点，需同时给新 `rrule`）。
4. 删除**不会撤回已排队消息**；删完把本表对应行标记为「已删除 + 日期」。
5. 巡检 prompt 必须自带全部绝对路径（`$PY`、`$FLOW`、项目根、feature），因为投递时不会带上文；改路径要同步改 `prompt`。
6. 巡检只读：只写 `docs/<feature>/evidence/inspector-<YYYYMMDD>.md`，不改代码、不改 `state.json`、不新建候选。

## 创建时的参数模板

```text
title : 每日审计 <项目简称> <feature> 越界与证据
target: this_session
rrule : DTSTART;TZID=Asia/Shanghai:20261119T090000
        RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0
prompt: 见 ops/inspector-schedule.md 的完整模板（含静止短路、子智能体派发、回报格式、自停阈值）
```

> 注意：`rrule` 是一个字符串里的**两行**（DTSTART + RRULE），中间是换行；`{{占位符}}` 不会自动替换，创建前手工填实。
> 更省事的做法：`& $PY $FLOW inspector -p "<项目根>" -f <feature>` 直接生成填好的 title/rrule/prompt（见 `ops/inspector-schedule.md` 第三节）。

## 已知行为（DSH 定时任务）

1. **关机/休眠期间不投递**；恢复后**只补投最近一次**错过的，不会补跑整天。
2. **崩溃后可能重复投递一次**；看到重复报告以时间最新的为准。
3. 补投的那次，巡检报告开头必须写 `补投：是（错过 <日期>）`，避免把「昨天的结论」当成今天的事实。
4. 定时任务属于 **Host 全局**，不属于某个项目；换项目要改 `prompt` 里的绝对路径，或删掉重建。
5. 进入 `DONE` 且连续静止 ≥7 天后，巡检会回报「建议暂停」；确认后用 `schedule_edit { id, action:"update", active:false }` 暂停（保留定义）。

## 最近 10 次巡检

> **已合并**（2026-11-21 09:35）：原「最近巡检」与「最近 10 次巡检」两张表内容重叠且互相矛盾，现**只保留上面「## 最近巡检」一张表**。
> 规则不变：每次巡检**只追加一行**结论，超过 10 行删最旧的；没有投递记录就写「无」。

