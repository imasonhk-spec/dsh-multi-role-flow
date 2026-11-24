# ROADMAP · 后续任务

> 更新：2026-11-22（Asia/Shanghai，`flow-b-group-fixup` E2 数字口径校准：**步数 / 套件数 / 产物数 / 候选链一律现读**，写死的旧值已清；本节仍不写 `current_candidate` / `phase` / 版本号 / 步数）
> 依据：`weekly-report` 全流程复盘、`flow-quality-boost` 收口（2026-11-22 13:00 时点现读：`phase=DONE`、`current_candidate=C012`、冻结 **9 个候选**——C001–C006 改代码 v1.2.0 → v1.2.3，C007/C009/C011 已 `drop` 归档，C008 起只修缺陷到 v1.2.6）文档收口、D 卷换盘（exFAT → SSD/NTFS）后基线重记。
> **现值读取口径（本文与任何文档都不许再抄一份）**：阶段/候选看 `flow.py status` 或 `flow.py drive`；`selftest` 步数看 `selftest` 现跑；bundle 版本看 `build_bundle.py --check`。**带明确时点的历史陈述保留**（§0.1 是 11-18 快照、§10 各行是各候选收口时点），但不作为现值。
> 约定：每项写清 **产物 / 证据 / 完成判据**；P0 的完成判据统一加「selftest 通过 + 一次真实巡检报告」。

## 0. 当前状态

| 项 | 状态 |
|---|---|
| 流程包 | 可用：角色 5 份、模板 12 份、`dsh_flow.py` **24 个子命令**（`--help` 现读）；`selftest` 步数/通过数、bundle 版本**一律现读**——`& $PY tools\selftest.py` 看末尾 `total=/failed=`，`& $PY tools\build_bundle.py --check` 看版本（历史时点值一律见 §10 与 `ops/schedules.md`，**这里不复述**；2026-11-22 实测 **473 用例 / 0 失败**、**49 产物 / 版本 1.2.6**；**不要引用任何历史值当现值**） |
| `flow-quality-boost`（引擎质量） | ✅ **已收口**（2026-11-22 13:00 时点现读）：`phase=DONE`、`current_candidate=C012`、冻结 **9 个候选**（C001–C006 / C008 / C010 / C012；C007 / C009 / C011 已 `drop` 归档），版本链 v1.2.0 → v1.2.3 → v1.2.6（C008 起只修缺陷）。**阶段与候选一律以 `flow.py status` / `flow.py drive` 现读为准**——本节此前写死过 `C004` / `C005` / `C008` 与 `phase=EXECUTING`，全是当时快照，已被后续推进取代。逐候选说明与**残留项**见 §10 |
| D 卷（2026-11-21 换盘） | 原 exFAT（`HealthStatus=Warning` / `OperationalStatus=Full Repair Needed`）→ 现 **NTFS / Healthy / OperationalStatus=OK**；旧 `dsh-bundle-live` 残骸已**可逆归档**到 `<workspace>\_attic-dsh-bundle-live-20261121`（项目外，不再进 `audit`）；bundle 产物仍走 `dsh-bundle-dist`（`.dsh-flow-bundle-dir` 指向它） |
| `weekly-report` 能力包 | ⚠️ **2026-11-20 23:37 误删事故**：旧 `<workspace>\weekly-report`（DONE/C007 v0.4.1 + 36 文件封存）与 `weekly-report-dev` 已随 `cmd /c rd /s /q` 全失；**继任项目为 `<weekly-report-project>`**——C001–C004，v0.1.2，**`phase=DONE`**（2026-11-21 09:47:26 用户拍板「通过」，TRIAL→DONE；`C004=accepted`、已 seal，运行时 0.1.2 握手 PASS／端口 54023，磁盘与宿主半已一致）。原写「phase=VERIFYING、宿主半仍 0.1.1、等用户重启收口」**已过期** |
| 隔离手段 | 流程包**不含** `worktree` 子命令：隔离统一走 `<项目根>-dev` 副本 + `baseline`/`freeze` 的 sha256 差集；宿主原生 `create_worktree` 是否可用以 `doctor` 输出为准（本机 git 2.56.1 + node 24.21.0 已在 PATH） |
| 定时审计 | **已开**：`schedule-201bad05-f214-4903-a269-be90fd487a93`，每天 09:00（Asia/Shanghai），**下次 2026-11-22 09:00**；最近一次投递 **2026-11-21 09:00**（旧 `001-开发\weekly-report` 已随 11-20 事故消失，目标已迁到 `<weekly-report-project>`；该次为 BLOCKED，未写报告）（见 `ops/schedules.md`） |
| 基线 | 已重记并规范成数组：**项目内 101 文件 + 外部源 0 个文件（0 个目录）**，文档层 13 个受跟踪文件；重记时间 `2026-11-21T19:32:10+08:00`、`roots=['.']`（2026-11-21 换盘 + 残骸归档后重记）；换盘前的 `weekly-report-dev` 外部源（曾 15 文件）随 11-20 事故已失；`baseline` 仍自动发现兄弟 `*-dev` 与 `package.json` link 目标，`doctor` 校验 |
| 已知缺口 | ① ~~`baseline` 要手工 `--source`~~；② ~~巡检 prompt 手抄~~（`flow.py inspector`）；③ ~~静止 7 天建议暂停未实测~~（11-20 已触发静止短路）；④ ~~runtime 无告警~~；⑤ ~~证据双清单口径~~；⑥ ~~`create_worktree` 未验证~~；⑦ ~~ACCEPTANCE 滞后无自动检查~~（KNOWN-EXCEPTIONS 机制；自动检查属 P0-7）；⑧ ~~dev 源未登记文件~~；⑨ ~~封存后改报告~~；⑩ **旧 C008 计划作废**（C007 已随事故丢失，KE-001 无对象）；新线 `103-周报` 已到 C004 且 **`phase=DONE`**（2026-11-21 09:47 用户「通过」，C004 `accepted`、运行时 0.1.2 握手 PASS），收口已完成 |

---

## 0.1 本轮复核结论（2026-11-18 14:20，**历史时点**）

> **本节是 2026-11-18 的历史快照，数字一律不随后续候选更新**（如「44 步」「`weekly-report` DONE/C007」「下次投递 11-19」均已被后续事实取代：`weekly-report` 已于 11-20 事故消失，`inspector`/`dashboard` 早已实现，`selftest` 步数已远超当时——现值一律现跑）。**现状看 §0 与 `flow.py status/drive`，不要引用本节的数字当现值。**

| 检查 | 结果 |
|---|---|
| `tools/selftest.py` | 44 步全过（`total=44 failed=0`）；末尾 audit 的 1 条告警是「篡改用例」的预期结果 |
| `weekly-report` 状态 | `phase=DONE`、`current_candidate=C007`、候选 C001–C007 齐全、`verification.json` 存在 |
| 定时任务 | `schedule_list` 实测 1 条 active，`scheduledAtLocal=2026-11-19T09:00+08:00`，与台账一致 |
| 未实现的 P0 项 | `inspector`、`dashboard` 子命令不存在；`freeze` 无 `capabilityPack` 告警；无 `templates/plugin-pack/`、无 `ops/host-restart-sop.md` |
| 文档 | 新命令（`block/unblock/amend/handshake/seal`）在 README/roles/ops 中均有描述，无「文档说有、实现没有」的倒挂（`worktree` 不是流程包子命令，已从清单剔除） |

**结论**：流程本身可用，剩余工作集中在「无人值守可靠性」与「分发/工程化」两类，不需要再改状态机核心。

---

## 1. P0 · 让"定时审计"真正可长期无人值守（本周）

| # | 任务 | 产物 | 完成判据 | 现状 |
|---|---|---|---|---|
| P0-1 | 把巡检 prompt 固化成命令：`flow.py inspector --project … --feature …` 输出可直接粘进 `schedule_create` 的 prompt（含静止短路、子智能体派发、报告路径、自停阈值） | `tools/dsh_flow.py` 新子命令 + `ops/inspector-schedule.md` 改指向它 | `--help` 有该子命令；输出里的路径与实际一致；`selftest` 加一条断言 | ✅ 2026-11-18（`inspector` + `--json/--out`；selftest 4 条断言） |
| P0-2 | `baseline` 自动发现外部源：项目根只有 `docs/` 时，从 `state.sources`、`*-dev` 兄弟目录、`package.json` 的 link 目标推断候选源并提示；`doctor` 校验 `baseline.external` 非空；**顺便把 `external` 规范成 `{path, files, created_at, discovered_by}` 数组** | `cmd_baseline`/`cmd_doctor` 改动 + 1 条自测 | `weekly-report` 上不手写 `--source` 也能得到非空 `external`；`audit` 不再报"基线为空" | ✅ 2026-11-18（`weekly-report` 实测自动发现 15 文件；旧 dict 形态兼容） |
| P0-3 | 静止自动降噪：巡检判断「`phase==DONE` 且 audit 0/0/0 且 verify 通过」→ 一行回报、不写报告；连续 7 天 → 回报建议暂停 | `ops/inspector-schedule.md` 定稿 + 一次真实投递记录 | 连续 2 天投递里，至少 1 天走"静止短路"且未新建报告文件 | ✅ 2026-11-20 首次真实**静止短路**（项目内 0/0/0、外部源仅 KE-001、文档层仅预期写入；未写报告、未起子智能体） |
| P0-4 | 定时任务台账与巡检记录打通：`ops/schedules.md` 已建；加一节「最近 10 次巡检」由巡检追加（只追加一行结论） | `ops/schedules.md` | 连续两次巡检各追加一行；表内 id 与 `schedule_list` 一致 | ✅ 2026-11-19 已追加首行（11-18 人工 + 11-19 定时） |
| P0-5 | 定时任务异常兜底：DSH 未运行/崩溃期间不投递，恢复后只补最近一次——写进 `ops/schedules.md` 的「已知行为」，并在巡检报告里注明"本次为补投" | 文档 + 巡检报告字段 | 文档有该说明；报告有补投标记位置 | 🟡 文档已写（5 条已知行为），补投标记待首次补投验证 |
| P0-6 | `freeze` 对插件项目强制运行时声明：检测 `package.json` 的 `dsh.capabilityPack` / `dsh.bundle` 时，缺 `--runtime-kind/--runtime-version/--health-url` 给**警告**（不阻断），并在 `gate TRIAL` 说明"未声明 runtime，握手不计入门禁" | `cmd_freeze` 改动 + 1 条自测 | 下一候选 manifest 含 `runtime`；`gate TRIAL` 对无 runtime 的候选给出提示（原写「下一候选（C008）」——**C008 计划已作废**；现役 feature 是 `flow-quality-boost`，**已冻结候选全部 `runtime=null`**，逐候选以 `releases/C00x/manifest.json` 的 `runtime` 现读为准，别抄本文） | 🟡 **2026-11-21 校准：两条行为均已生效**——`freeze` 实测对 C005 打出「检测到能力包/插件项目…但本候选未声明 runtime」警告（见 `releases/C005/RELEASE-REPORT.md`），`gate TRIAL` 也已说明握手不计入门禁（见 §10.2-3）；仍缺 ① `selftest` 断言 ② 一个真正声明 `runtime` 的候选（**可行性已评估：本项目当前不可行，见 §10.2-6**） |
| P0-7 | **ACCEPTANCE 与台账一致性自动检查**：`gate` 在 `TRIAL/DONE` 时校验 ①「更新」行时间不早于最后一条 `advance`；② §二 若仍有 `⏳` 而 §六 已是 `用户结论：通过` → 警告（不阻断，因 D 级口述确认合法）；③ 必填项未勾提示 | `cmd_gate` 改动 + fixture（11-18 回填前副本）+ 2 条 selftest | 用旧副本跑 `gate` 能复现 D1–D4 中至少 2 条；`weekly-report` 现文本跑出 0 警告 | 🆕 2026-11-19 巡检发现（D1–D4 已人工回填） |
| P0-8 | **封存后不可改**写死：`roles/03-verifier.md`、`roles/00-lead.md`、`AGENTS.md` 三处明确「`seal` 后 `RELEASE-REPORT.md` 不得改，改则 `verify` FAIL；结论文档只回填 `ACCEPTANCE.md`」 | 三处文档 + 1 条 selftest（改封存报告→verify FAIL） | 三处有该规则；自测能报出被封存报告被改 | 🆕 11-18 巡检 D4 的直接教训（昨日建议 a 里有"升级报告"是错的） |
| P0-9 | **巡检后刷新 `health.json`**：inspector 只读、不能跑 `flow.py health`（会写盘），由 Lead 在收到回报后跑一次；或在巡检 prompt 里明确"Lead 汇报前刷新" | 巡检 prompt + `ops/inspector-schedule.md` | `health.json.updated_at` 与最近一次巡检同日；看板读到的是最新阶段 | ✅ 2026-11-19（schedule prompt 增加「Lead 收口必跑 health」；今日已刷新） |
| P0-10 | **巡检窗口冻结写入（D6）**：审计开始时对 `state/ledger/ACCEPTANCE/verification.json` 取哈希快照，结束时核对；期间若有 Lead 写入，报告标注"对象移动"并注明以哪个快照为准 | inspector 角色说明书 + 报告模板加「窗口快照」字段 | 报告有快照字段；连续两次巡检无未标注的并发写入 | ✅ 2026-11-19（用户批准"允许并发写入 + 标注"；04-inspector §1/§4 加窗口快照与第 7 节；ops/schedule prompt 同步） |
| P0-11 | **D5 文档层盲区**：当前 baseline 排除 `docs/`，`ACCEPTANCE/ledger/state` 改动 audit 报 0。为 `docs/<feature>/{ACCEPTANCE.md,ledger.md,state.json,health.json,DESIGN.md}` + `releases/*/verification.json` + `releases/*/RELEASE-REPORT.md` 生成哈希清单，纳入 `audit` | `baseline` 写入 `docs_meta` + `audit` 新增「文档层」段 + `baseline --docs-only` + selftest | 手工改 `ACCEPTANCE.md` 后 `audit` 报"文档层修改"（预期），改封存件报 ⚠，`--docs-only` 不动源码基线 | ✅ 2026-11-19（weekly-report 实测 13 个受跟踪文件；selftest K 套 5 条断言，total 119 步 0 失败） |
| P0-12 | **工具缓存目录不入基线/审计**：`.gitnexus/`、`graphify-out/`、`.graphify/`、`.cache/` 等索引产物被当成"源目录未登记改动"，11-20 一次报 39 项噪音 | `SKIP_DIR_NAMES` + selftest L 套 | 新增缓存文件后 `audit` 不告警；基线里不含这些目录 | ✅ 2026-11-20（weekly-report 从 39 项降到仅 KE-001；selftest L 套 2 条断言，total 123 步 0 失败） |

**P0 建议顺序**：P0-1 → P0-2 →（11-19 首次投递后）P0-3 → P0-4/P0-5 → P0-6。P0-1/P0-2 可一起做完再统一跑 selftest。

## 2. P1 · 下一轮功能与工程化（下周）

| # | 任务 | 产物 | 完成判据 |
|---|---|---|---|
| P1-1 | **证据双清单口径**：写死 `manifest.evidence`（冻结时 P*）与 `verification.json`（封存时 V*/报告/部署台账）的边界，`gate TRIAL` 提示"未 seal" | `MIGRATION.md` 一节 + `gate` 提示 + 1 条自测 | 新项目从初始化到 DONE 只走一套口径；旧项目补一段说明（原写「weekly-report」——该项目已随 11-20 事故消失，旧项目样本改取 `<weekly-report-project>`） |
| P1-2 | 插件/能力包骨架模板：把 `weekly-report-dev/pack` 结构（`package.json` + `cordis.patch.yml` + `index.js` + `client.js` + 图标 + `lib/` + `scripts/smoke.mjs`）抽成 `templates/plugin-pack/` | 模板目录 + `init --kind plugin` | 新建空能力包能 `plugin_manager install_bundle` 装上并出现在侧栏。**现状（2026-11-21 核实）**：`templates/plugin-pack/` 已有 7 个文件、`init --kind plugin` 走 `scaffold_plugin_pack()` 复制替换占位符 → 产物侧已具备；`weekly-report-dev/pack` 原件随 11-20 事故已失，判据里的「抽」只能以现存模板为准 |
| P1-3 | 宿主半重启 SOP：`装完 → handshake → FAIL 就请用户重启 DSH → 再 handshake → seal` 写成 `ops/host-restart-sop.md`，verifier 角色引用 | 文档 + 角色说明书一节 | 假版本（改 `version` 不重启）能被 `handshake` 判 FAIL 并给出重启指引 |
| P1-4 | 多 feature 看板：`flow.py dashboard` 扫描 `**/docs/*/state.json`，输出 项目 / feature / 阶段 / 阻塞 / 最近台账 | 新子命令 | 在 `<workspace>` 下能同时列出 `weekly-report` 与 `demo-wordstat`，并标出 `blocked`。**现状（2026-11-21 核实）**：`dashboard` 子命令已在（24 子命令含它）；判据里的 `weekly-report` 已随 11-20 事故消失，样本宜改为 `dsh-多角色协作流程` 与 `demo-wordstat` |
| P1-5 | `workflow/review-candidate.workflow.js` 实测：对 `C007` 跑一次多角度独立复核，产出结构化结论 | 运行记录 + 修复（如有） | 4 条检查各有一个子智能体结论，交叉复核字段非空。**注**：`weekly-report` 的 `C007` 已随 11-20 事故消失，本项需改绑现存候选（如 `flow-quality-boost` C00x）才有对象 |
| P1-6 | 原生 `create_worktree` 可用性验证（DSH 已重启）：在临时 git 仓库里建树 → 回归，并把结论写回 AGENTS/README | 验证记录 | 可用则更新「隔离方式」段；不可用则记录缺失依赖 |
| P1-7 | **`install-manifest.json` 归属**：dev 源 `pack/install-manifest.json`（v0.4.1 运行要求声明）未进任何候选，11-19 `audit` 报"源目录有未登记改动" | 处置记录（进 C008 或从 dev 源移除）+ `templates/plugin-pack/` 决定是否内置 | 二选一后 `audit` 回到 0/0/0；若内置模板，新插件包 `freeze` 时 `manifest.artifacts` 含它。**✅ 决策：纳入 C008**（用户 2026-11-19）；落地清单：① C008 启动前 `baseline` 重记（含该文件）② `freeze` 的 artifacts 含它 ③ `templates/plugin-pack/` 评估内置 ④ 冻结后删除 `KNOWN-EXCEPTIONS.md` 的 KE-001。**⚠️ 2026-11-21 校准：本项已失效**——`weekly-report-dev` 与 `KNOWN-EXCEPTIONS.md`/KE-001 均随 11-20 事故消失，C008 计划作废（同 §0「已知缺口」⑩）；现存 `install-manifest.json` 只剩 `103-周报` 侧需重新登记 |

## 3. P2 · 分发与体验（本月）

| # | 任务 | 产物 | 完成判据 |
|---|---|---|---|
| P2-1 | 打包成分发用的 DSH bundle（`plugin_manager install_bundle` 一键装，替代 `install.ps1` 手工复制） | `package.json` + `cordis.patch.yml` + 技能目录 | 干净 profile 上装一次即可用 `dsh-multi-role-flow` 技能。**现状（2026-11-21 核实）**：`dsh-bundle-dist/` 已产出（**49 产物**；版本以 `& $PY tools\build_bundle.py --check` 现读为准——2026-11-22 现读 1.2.6，两个数字都随候选变）；含 `package.json`、`cordis.patch.yml`、`skills/dsh-multi-role-flow/SKILL.md`；**未在干净 profile 上实装验证**，判据未闭环 |
| P2-2 | 健康快照：`flow.py health` 输出 `docs/<feature>/health.json`（阶段/门禁/候选/封存/最后台账），供外部看板读 | 新子命令 + JSON schema | 每次巡检后 `health.json` 更新且可被脚本解析。**现状（2026-11-21 核实）**：`health` 子命令已在（24 子命令含它），`docs/flow-quality-boost/health.json` 存在；「每次巡检后刷新」由 P0-9 的 prompt 约束保证 |
| P2-3 | Windows 兜底：任务计划开机自检（DSH 未运行时提醒），可选，默认关 | `ops/windows-fallback.md` | 文档给出可执行命令与卸载步骤。**现状**：文件未建（`ops/` 下无 `windows-fallback.md`） |
| P2-4 | 术语表 / 英文版 README | `GLOSSARY.md` | 术语与角色名一一对应，指向源码行。**现状**：`GLOSSARY.md` 已存在（含「源码索引」节），英文版 README 未做 |
| P2-5 | 自测扩展：把"文档里的命令"与 `--help` 对照，防止文档漂移 | `selftest.py` 新增 2 条断言 | 故意改坏一条 `--help` 文案，自测能报出来 |

---

## 6. 工具接入（2026-11-20，feature `dev-toolchain-boost`）

> 落地原则：**先算「接上之后谁受益」，再接**；每个工具都要能说清「它替代了哪一步人工动作」。四项落地里三项当天可用、一项卡在宿主版本门禁上。

| # | 工具 | 现状 | 谁受益 / 替代了什么人工动作 | 未完成部分 |
|---|---|---|---|---|
| T1 | **stop-that-shit**（Skill 层） | ✅ 文件已落 `skills/stop-that-shit/SKILL.md` + `W\.dsh\skills\`，正文与上游 0.2.6 逐字一致，仅加本机适配头 | executor 判断「要不要加这层防御」时有了固定的 Stop Ladder 五步，不用每次现推；明确写了它**不是**执行拦截，避免拿它冒充 `audit` | 新会话是否列出该技能待实测（需重启/新会话） |
| T2 | **graphify 多项目建图** | ✅ `weekly-report-dev` 建出 240 节点 / 468 边；查询契约写进 `ops/code-graph.md` | 改前查调用方、定回归范围；不再「靠印象判断影响面」 | 文档/图片语义提取未启用（需 key，且会外发内容） |
| T3 | **GitNexus 影响面** | 🟡 `weekly-report-dev` 已建索引 590 节点 / 1751 边，`impact -u` 可用；但需先本地补 `vcruntime140*.dll` 才能加载原生库，FTS/BM25 仍不可用 | `impact` 给出精确 upstream 调用方 + 受影响流程，比 graphify 的边更贴近「改这里会坏哪里」 | ① `npm install -g` 无法执行（npm 不在 PATH）② FTS 关键字检索缺失 ③ 目标目录非 git 仓库 → 无 `detect_changes` |
| T4 | **agentmem 跨端记忆** | 🟡 已索引 dsh 8 会话 / 2795 事件，`search` 实测 675 命中；**未跑 `connect`**，MCP 工具尚未接进 DSH | 接上后可回答「上次是谁怎么修的」，替代人工翻历史会话 | `connect` + 重启（Lead 决策）；`workbuddy` 端 347 会话未授权未索引 |
| T5 | **mnemon 记忆分工** | 🟡 CLI 0.2.13 在位（`D:\Tools\mnemon`）、`cliPath` 已写进 profile 配置；`providers=[]`，Memory Space unhealthy | 代码库知识有了长期落点（Documents），不必塞进会话记忆 | 需重启让宿主拉起 CLI → Provider 就绪 → 建/激活「代码库知识」Space → 迁移 `ops/` 里的知识 |

**下一步（按顺序）**：
1. ~~用户重启 DSH → 复验 `mnemon_status.providers≥1`、`$stop-that-shit status`~~ → **已完成两轮重启**：`mnemon` 已 `healthy=true`/`commandFound=true`/Space active；`providers` 仍为 `[]`（见 T5）。
2. ~~Lead 决定是否 `agentmem.py connect --client dsh`~~ → **已做**（只接 DSH，`--client dsh`，未 `--all`），重启后 MCP 工具实测可用。
3. GitNexus 的 FTS 缺口：要么装 VC++ 运行时 / OpenSSL 3（系统级改动，需用户批准），要么接受「无关键字检索，只用图查询」。**用户 2026-11-20 决定：不动 `System32`，接受降级。**
4. 把 `ops/code-graph.md` 的建图步骤纳入新项目初始化清单（`init` 之后第一次改动前建一次图）。**→ 2026-11-20 已在 `flow-context-boost` 收编：`init` 默认维护 `.graphifyignore` + 自动建图（失败降级、退出码 0），详见 `ops/code-graph.md` §8/§9（原「见 §9」所指的本节已随 11-20 事故丢失）。**

## 7. 工具接入结论（2026-11-20，`dev-toolchain-boost` C002 已 DONE）

| 项 | 结论 |
|---|---|
| 验收 | 阻断项 9 项过 7；`P5`（STS Guard 被 `engines.dsh=0.2.2-rc.3` 版本门禁拒绝，未装）、`P6`（mnemon 无 Provider）**未达成**，用户知情接受降级后回「通过」 |
| 封存 | `releases/C002/verification.json` 覆盖 22 个文件；`selftest` 123 步 0 失败；`weekly-report C007` 回归 exit 0 |
| 对外口径 | **不得**声称「Guard 已拦截」；**不得**声称「mnemon 记忆可用」；可以说「stop-that-shit 纪律技能可加载」「agentmem 跨会话检索可用」「graphify/GitNexus 图查询可用」 |

**遗留（按优先级）**：

| # | 事项 | 判据 | 备注 |
|---|---|---|---|
| R1 | mnemon Provider 就绪 + Documents 检索闭环 | ~~`mnemon_status.providers≥1`~~ → **判据已废止**：改为 `commandFound=true` + `memorySpaces.unhealthy=0` + `memory_bodies` 带 `capabilities` | 已在 `toolchain-fixups` C001 收编，详见 `ops/aux-tools.md` §5/§5.1 与 `ops/memory-split.md` 问题 4（原「见 §8」的本节已随 11-20 事故丢失）；旧判据错在「`providers` 只列非 native Provider」 |
| R2 | `ops/memory-split.md` 第 4 问判据已过期 | 该节仍以 `commandFound=false` 作降级判据，现为 `true` | **已在 `toolchain-fixups` C001 改掉**（同时把 `providers≥1` 的错判据一并更正），不再留到 C003 |
| R3 | 流程外并发写入未收编 | `ops/schedules.md`、`ROADMAP.md`（本节）、`tools/dsh_flow.py`、`tools/selftest.py`（119→123 步）均在 09:00–09:02 被本 feature 之外来源改动 | 非执行/验证线程所为，已记台账；出 C003 时纳入 `baseline` 重记 |
| R4 | STS Guard 版本适配 | 上游发布支持 DSH ≥ rc.5 的版本后重测 | **已带用户批准的版本豁免装在 desktop profile**（`stop-that-shit-dsh@0.2.6` + `0.2.2-rc.5`），待用户重启后实测；详见 `ops/aux-tools.md` §3/§3.1（原「见 §8」的本节已随 11-20 事故丢失；实测补充：宿主半已热加载 `enabled=true`/`fiberPhase=active`，无需重启也可加载） |
| R5 | `ops/code-graph.md` 进新项目初始化清单 | `init` 之后、首次改动前建图成为固定步骤 | **已在 `flow-context-boost` 收编**：`init` 默认维护 `.graphifyignore` + 自动建图（失败降级、退出码 0），详见 `ops/code-graph.md` §8/§9（原「见 §9」的本节已随 11-20 事故丢失） |

---

## 4. 用户拍板结果（2026-11-18 14:30）

1. **`weekly-report` 不再开下一轮** → 精力转到流程工程化；C007 就是该能力包的终点，后续候选只在修 bug 时开。
2. **定时审计频率**：保持每天 09:00（暂不改工作日）。
3. **发布为 DSH 插件**：**同意**（P2-1 解锁，但排在 P0/P1 之后；装 bundle 会改 profile 全局，执行前再确认一次目标版本）。
4. **`weekly-report` 是否 `git init`**：暂不；真需要隔离时，用 `<项目根>-dev` 副本 + `baseline`/`freeze` 的 sha256 差集即可（流程包不含 `worktree` 子命令，`create_worktree` 是否可用以 `doctor` 为准）。

## 5. 建议的推进顺序

```
已完成：P0-1（inspector 命令）→ P0-2（baseline 自动发现 + external 数组）→ selftest 54 步（当时值；现值以现跑为准）
11-19 09:00 首次投递：观察 P0-3 静止短路，补 P0-4 巡检行 + P0-5 补投标记
随后：P0-6（runtime 告警）→ P1-1（证据双清单口径）→ P1-3（重启 SOP）
下周：P1-2（插件模板）→ P1-4（看板）→ P1-6（worktree 验证）→ P1-5（workflow 实测）
本月：P2-1（发布 DSH 插件，需再确认版本）→ P2-2（health.json）→ P2-5（自测扩项）
```

> **本段是 2026-11-18/19 的排期快照，不随后续事实更新**：P1-2（`templates/plugin-pack/`）与 `dashboard` 子命令此后已落地，`weekly-report` 已随 11-20 事故消失（P1-5 的 `C007` 对象不存在），`selftest` 步数已远超当时。现状以 §0 与 `flow.py drive` 为准。

> 每完成一项：改 `README.md` 的「已验证的事实」表 + 追加 `tools/selftest.py` 断言 + 在对应 feature 的 `docs/<feature>/ledger.md` 记一条（`flow.py ledger -m`）。（原文写「`weekly-report` 的 `ledger.md`」——该 feature 已随 11-20 事故消失，改按现存 feature 记。）

---

## 10. flow-quality-boost 收口（2026-11-21 → 11-22，C001–C012，v1.2.0 → v1.2.6；现 `phase=DONE`）

> 一句话：本轮修的是**流程引擎自己**的质量——假绿灯、证据闸、图谱污染、封存台账串味、审计误报、`.ps1` 编码。C001–C006 改代码（v1.2.0 → v1.2.3），C008 起只修缺陷（→ v1.2.6）；C007 / C009 / C011 冻结后被 `drop` 归档。下表按 `docs/flow-quality-boost/state.json` **现读**补到 C012。
> **现值只看 `flow.py status` / `flow.py drive`**：现为 `phase=DONE` / `current_candidate=C012`（冻结 9 个候选）。本节任何写死的阶段与候选号都只是**当时**快照——照抄必错的历史案例：2026-11-21 20:30 写的 `current_candidate=C005` / `phase=EXECUTING` 让 C006 验证线程判出 2 条 ❌。

| 候选 | 版本 | 修了什么 | 关键数字 |
|---|---|---|---|
| C001 | 1.2.0 | A：`freeze` 内挂 QC 静态检查；B：`next` 交接包第 5 块「知识入口」；C：新增 `drive` 只读合成子命令；D：图谱陈旧/污染改软检查（只 `⚠` 提示，不堵门禁） | `selftest` **250 → 312**；子命令 23 → 24 |
| C002 | 1.2.1 | QC 假阳性清零（`templates/**` 与 `!!js` 标签降 fail 为 skip）；`warn_for` 增「缺 `P*` 证据」闸；GLOSSARY 补到 24 子命令；`doctor` 加 node 探测 | QC `fail 5 → 0`；证据 **1 → 6** 条；`selftest` **326** |
| C003 | 1.2.2 | `.graphifyignore` 排除清单补 `dsh-bundle-live/`、`dsh-bundle-dist/`；两处污染检测正则合并为 `RE_GRAPH_COPY_SOURCE` | 节点 **675 → 395**，`dsh-bundle-live` 副本节点 **322 → 0**（以上为 **C003 时点**；**C005 时点实测 397 节点 / 919 边 / 24 社区、副本污染 0**，见 `ops/code-graph.md` §8）；`selftest` **333** |
| C004 | 1.2.3 | `seal` 不再登记全 feature 共用的 `DEPLOYMENT-PLAN.md`，改为先快照到 `releases/<C>/DEPLOYMENT-PLAN.md` 再封存该副本（治本 L001） | 交叉 seal 探针实证（旧格式对照组必红 / 新格式双侧 exit 0）；当时 `selftest` 354 条 |
| C005 | 1.2.3 | 纯文档收口（代码未改）：校准 `ROADMAP` 状态口径与残留项 | 47 产物；`seal` 6 文件 |
| C006 | 1.2.3 | 纯文档收口；随后用户 `TRIAL→DONE`（20:58） | 48 产物；`seal` 6 文件 |
| ~~C007~~ | 1.2.5 | **已 `drop`**：E1 把 `re.fullmatch(r'P\d+')` 收得过紧，带后缀的 `check_id` 被判「无 P 证据」 | 48 产物；归档 `archive/C007-20261121-224447` |
| C008 | 1.2.6 | 修 P 证据识别回归（放宽判据 + 补断言），只修缺陷不扩功能 | 48 产物；`seal` 11 文件 |
| ~~C009~~ | 1.2.6 | **已 `drop`**：§7 新措辞与事实不符（写「作废候选占号不复用」，而 C008 的 `P29/P30/P31/P33` 正是复用 C007 的号） | 归档 `archive/C009-20261122-002109` |
| C010 | 1.2.6 | 按 verifier 建议重做 §7 措辞：同一检查沿用同号 / 没有的检查留空档 / 已占号不得改发另一种检查 | 48 产物；`seal` 5 文件 |
| ~~C011~~ | 1.2.6 | **已 `drop`**：候选混入另一会话（`session-a2da8277`）的并发改动（`tools/**`、`ops/**` 均非本 feature 授权），只应含 `roles/02-executor.md` 一处 | 49 产物；改冻 C012 并限 `--scope roles` |
| C012 | 1.2.6 | 只含 `roles/02-executor.md` 一处修正 | 5 产物；21:41 `seal` + 异地快照；2026-11-22 07:17 用户 `TRIAL→DONE`（该时点起 `phase=DONE`） |

### 10.1 D 卷换盘（2026-11-21）

- **换盘前**：D 盘是 **exFAT**，卷 `HealthStatus=Warning` / `OperationalStatus=Full Repair Needed`；`dsh-bundle-live\skills` 成了**损坏目录项**（`Access is denied`），41 个生成物在 `shutil.rmtree` 中丢失，bundle 产物被迫迁到 `dsh-bundle-dist`。
- **换盘后实测**：D 盘为 **NTFS / Healthy / OperationalStatus=OK**；`skills` 目录项不再报 `Access is denied`（改报「不存在」）。
- **旧残骸处置**：`dsh-bundle-live` 只剩 7 个根级文件（其中 `package.json`、`README.md`、`GLOSSARY.md` 与 `dsh-bundle-dist` 不同），已**可逆归档**到 `<workspace>\_attic-dsh-bundle-live-20261121`（项目外，不进 `audit`）。
- **产物目录不变**：bundle 仍构建到 `dsh-bundle-dist`，`.dsh-flow-bundle-dir` 指向它；换盘时点（2026-11-21）`build_bundle.py --check` exit 0（当时 48 个产物、版本 1.2.3）。**版本号与产物数一律现读以 `--check` 为准**——2026-11-22 15:40 现读为 **52 个产物 / 版本 1.2.6**（`skills/` 从「只收 `dsh-multi-role-flow`」改为**全目录收录**后 +1，见下方 `bundle-skills-coverage`）；两个数字都随候选增长，不要写死。
- **基线**：换盘后已重记 `baseline`（101 个项目文件 + 0 个外部源，roots=`['.']`；ledger 2026-11-21T19:32:10），`audit` 项目内 0/0/0、文档层只剩 `ledger.md`/`state.json` 的预期写入；四个候选的 `verify` 结论不变——**C001 红（历史遗留）、C002/C003/C004 绿**；**C005 亦绿**（20:09 seal，`RELEASE-REPORT.md` 记录 `verify` 独立重算全等，47 产物 / 2 条证据）。

### 10.2 残留项（如实记录，不写「已全部修复」）

1. **`C001` 封存校验永久红**：`verify --id C001` exit 1，2 项不匹配**全部**指向 `DEPLOYMENT-PLAN.md`。它封的是 11:47 时刻的**共用**台账，15:37 被 C002 的验证线程写过后就对不上；C004 起已治本，但 C001 是历史——**不许补快照、不许改判据抹平**。
2. **`C002`/`C003` 仍绑共用台账**：今后任何人写 `docs/flow-quality-boost/DEPLOYMENT-PLAN.md`（执行线程、验证线程、巡检都算）都会把这俩弄红——**要么别写**，要么写了在各自 `releases/<C>/RELEASE-REPORT.md` 留痕，并在 `ledger.md` 记一条。
3. **`v1.2.0`–`v1.2.6` 的 9 个冻结候选全部未声明 `manifest.runtime`**（插件项目但 `runtime=None`；逐候选以 `releases/C00x/manifest.json` 现读为准）：`gate TRIAL` 的「运行时版本握手」**不计入**本轮门禁；上线前需出**声明 runtime** 的候选（`freeze --runtime-kind plugin --runtime-version … --health-url …`），届时握手才进闸。**可行性评估结论见第 6 条：本项目当前做不到，不是漏做**（C007 起草、C008 原样收编）。
4. **ROADMAP 的 §8/§9 两节在 2026-11-20 事故中随文件丢失**：现存最早的封存副本 `docs/flow-quality-boost/releases/C001/files/ROADMAP.md` 里已只有 §0/§0.1/§1/§2/§3/§6/§7/§4/§5，**同样没有 §8/§9**（可证是更早已经丢，不是后来删的）。§6/§7 原来 4 处「见 §8」「见 §9」的悬空引用已于 2026-11-21 20:30 **改指真实存在的位置**——`ops/aux-tools.md` §5/§5.1（mnemon 判据）与 §3/§3.1（STS）、`ops/code-graph.md` §8/§9（`init` 自动建图与 `.graphifyignore`）；**两节原文本身没有回补**，不凭空编造，回补留待下一候选。
5. **`ROADMAP.md` 本轮校准后与快照不一致，属预期**：① 相对 19:32 的 `baseline`，本文件有 1 处文件改动（`audit` 会报，属预期写入；下次 `baseline` 重记时吸收）；② C005 封存副本 `releases/C005/files/ROADMAP.md` 是 19:40 时点快照，与本文现状自然不同——**冻结件不许回改**，也不许拿它反推本文。
6. **「声明 runtime 的候选」本项目当前做不到（C007 评估，2026-11-21；证据 `evidence/C007/P31-runtime-feasibility.md`）**：三条硬事实共同堵死——① 本 bundle **没有宿主半**（`dsh-bundle-dist/` 只有 `package.json` + `cordis.patch.yml`，后者仅向 Loader 插入 `@deepseek-ai/dsh-skill-filesystem`，不注册任何 HTTP 路由），而握手要求能力包自报 `GET /api/<短id>/health`（`ops/dsh-plugin-dev.md` §5）；② 本机宿主 **`/api/*` 全部 401**（实测 `/api/health`、`/api/boot`、`/api/multi-role-flow/health` 与不存在的随机路径返回**同一** 401，认证门在先），而 `handshake` 的 `_fetch_json()` 只发 `Accept`/`User-Agent`、**不带任何凭证** → 即便路由存在也必然 401 FAIL；③ profile 里 `dsh-multi-role-flow` 的 link 目标 `…\dsh-bundle-live` **已不存在**（11-20 归档到项目外），当前装的是悬空链接。**要具备什么条件才能做**：(a) bundle 增加宿主半 `index.js`（`apply(ctx)` 注册 `GET /api/multi-role-flow/health` 返回 `{ok,version,routes}` 且 version == `package.json` 版本）；(b) 该路由可在无认证下访问，或 `handshake` 增加凭证参数（如 `--header Authorization: …` / `--cookie`）；(c) profile link 改指 `dsh-bundle-dist` 并重装。**替代方案（不是握手，别混）**：用 `dsh-bundle-dist/package.json` 的 `version` 做**静态核对**（`build_bundle.py --check` 已经是逐文件 sha256 + 版本一致），但它证明的是「磁盘上的产物是哪一版」，**证明不了「宿主里正在跑的是哪一版」**——后者只有真实握手能给。

---

## 11. 2026-11-22 巡检增量（`103-周报` C004 收口后）

> 定时巡检结论 **PASS**；督察使报告 `<weekly-report-project>\docs\weekly-report\evidence\inspector-20261122.md`（22.2 KB）。本轮未新建候选、未推进阶段、未改 C004 封存件。

| 项 | 结果 |
|---|---|
| P0-13 `audit` 时间线误报 | ✅ 已修：`cmd_audit` 对「新增且已登记」的文件改为按 mtime vs `manifest.created_at` 判定——冻结前创建且哈希一致 → 「开发期新增（已登记，冻结前）」**不告警**；mtime 晚于冻结才告警。`103-周报` 的 10 条误报清零 |
| P0-14 lesson 文件归类 | ✅ `ops/lessons.md` 是 `flow.py lesson` 子命令唯一写入口，`audit` 视为「工具生成（预期）」；已对 `103-周报` 执行 `scope --add ops`，不再报「不在声明写范围」 |
| 自测与产物 | ✅ `selftest` **473 用例 0 失败**（该次巡检时点为 453 条，本轮新增 W 套 3 条断言；现读一律以现跑 `total=`/`failed=` 为准）；bundle 重建 **v1.2.6 / 49 产物**（该时点值，2026-11-22 15:40 现读已 **52**），`--check` 通过 |
| 待决策 | ① 主目录 `pack/` 与 `103-周报-dev` **双源**：建议主目录为唯一源、dev 归档；② `C004` 旧格式封存的是**共享** `DEPLOYMENT-PLAN.md`，任何人再写即「假红」：**开 C005 时改封 `releases/<C>/DEPLOYMENT-PLAN.md` 快照**；③ `ops/lessons.md` 是否长期留在项目内（现 scope 已含 `ops`） |
| 未做 | UI 端到端、DSH 崩溃补投复测；`103-周报` 无 `KNOWN-EXCEPTIONS.md`（本轮未创建） |


