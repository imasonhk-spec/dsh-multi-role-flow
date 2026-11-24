# MIGRATION：Codex 桌面协议 → DSH 版

> 迁移日期：2026-11-17　│　目标平台：Windows + DSH Desktop（git 2.56.1 与 node v24.21.0 在 PATH；本机无 bash）
> 本文件只讲**差异、降级与补偿**。角色职责见 `roles/*.md`，操作手册见 `ops/*.md`。

## 一、结论

- **文档层 0 改动**：角色职责、四份规划模板、候选编号、证据 A/B/C/D 分级、验收三态（`已上线可试用`/`待用户试用`/`完整业务验收通过`）原样可用。
- **传输层重写约 30%**：变的是"怎么开会话、怎么传消息、怎么隔离、怎么定时、怎么判停止"这五件事。
- **最关键的一句**：DSH 上「**开发者不能自证**」从 **物理隔离** 降级为 **流程纪律 + 哈希凭证**。
  原文靠"两个会话 + 两个独立副本"实现互斥；DSH 只有一个进程、一个共享 cwd，`write_scopes` 仅建议性。
  补偿手段集中在第三节，缺了这些补偿，"独立验证"就只剩名义。
- 原文《平台适配-WorkBuddy与DSH.md》的 DSH 章节写于旧版，工具名与"无 worktree"的结论**已被本版取代**，以本文件为准。

## 二、工具名对照表

| 原文（Codex / 旧 DSH 文档） | 现版本 DSH | 是否可用 | 语义变化 |
|---|---|---|---|
| `spawn_teammate` | `subagent`（可续聊，用 `send_message` 追加） | ✅ | 会话由父 Agent 派生，不是平级"开会话" |
| （原文无） | `subagent_fork` | ✅ | 子 Agent 继承本会话已完成轮次，适合"接着刚才的上下文复核" |
| （原文无） | `subagent_codex` | ✅ | 独立 Codex 进程；**一次性、不能续聊、无人工审批** |
| `send_message` | `send_message` | ✅ | 只能父↔子；子智能体之间**不能**互发 |
| `list_agents` | `list_agents` | ✅ | 只列本 subagent 树，看不到别的会话 |
| `wait_agent` | `wait_agent` | ⚠️ | 仍存在，但**不再接受 agent 名**：等的是"下一个输入"（消息/完成通知/用户插话） |
| `interrupt_agent` | `job_kill`（仅后台作业） | ⚠️ | 降级：无法打断前台子 Agent；只能杀后台作业，或 `send_message` 引导转向 |
| `task_create` / `task_update` / `task_get` / `task_list` | `team_task_create` / `team_task_update` / `team_task_get` / `team_task_list` | ✅ | 改名，能力增强（结构化状态、revision、write_scopes 提示） |
| `set_dependencies` | `team_task_update` 的 `action: set_dependencies` | ✅ | 合并进 update，需带 `expected_revision` |
| （原文说）"DSH 不支持 worktree" | `create_worktree` | ✅ **可用** | git 2.56.1 与 node v24.21.0 都在 PATH，`create_worktree` 已实测可用；但**本仓库不是 git 仓库**（未 `git init`），所以没有 diff 基线；见第三节第 2 条 |
| （原文无） | `schedule_create` / `schedule_edit` / `schedule_list` / `schedule_view` | ✅ | 新增，督察使定时审计靠它（不是"纯脚本定时器"） |
| （原文无） | `$PY tools/dsh_flow.py {init,baseline,freeze,verify,audit,evidence,status,next,advance,gate,ledger,doctor}` | ✅ | 新增：状态机与候选凭证。只读的有 `status/gate/audit/verify/ledger --tail/doctor`；`next` 会写 `handoffs/` 并改 `state.json`，`advance/freeze/evidence/baseline/init` 均写盘 |

## 三、能力降级与补偿（逐条）

### 1. `write_scopes` 只是建议性

- **降级**：任务板的写范围不拦人。Bash/脚本/格式化工具、直接外部写入都能绕过版本检查。
- **补偿**：① 越界靠**事后审计**发现，不靠事前拦截 —— `flow.py audit` 用 `baseline.json` 的哈希清单对比当前树；
  ② 冻结产物进 `releases/<candidate>/files/` 并登记 `manifest.json` 的 sha256；
  ③ 任务描述里显式写"不做什么"；④ **Lead 必须自己复核最终 diff**，这条不能委托。
- **残余风险**：越界只能在下一个审计点被发现，期间可能已经跑过检查。

### 2. 无 diff 基线时的隔离

- **降级**：git 2.56.1 与 node v24.21.0 都在 PATH，`create_worktree` 可用；但**本仓库不是 git 仓库**（未 `git init`），所以没有分支、没有 commit hash、没有 `git diff` 兜底。
- **补偿**：① 用 `baseline.json` + 文件哈希代替 `git diff`，用 `manifest.json` 的 sha256 代替 commit hash；
  ② 候选"冻结"= 把文件复制进 `releases/<candidate>/files/` 并锁哈希，此后以该目录为准；
  ③ 需要比对改动时用 `$PY` 脚本逐文件算哈希（`baseline`/sha256 差集即对照基线），不要为找 diff 去 `git init` 本仓库。
- **残余风险**：没有历史版本可回退。回滚只能靠"再复制回来"，因此**冻结快照必须真的复制**，不能只登记路径。

### 3. 子智能体不能互通

- **降级**：Codex 版是网状会话，"执行线程直接发给验证线程"；DSH 是星型，子 Agent 只与 Lead 通信。
- **补偿**：交接只走 **磁盘 + Lead 中转**：候选进 `releases/`、交接单进 `handoffs/`、结论进任务板；
  Lead 是唯一消息总线，不得让子 Agent"等另一个子 Agent 的消息"。
- **残余风险**：Lead 成为单点，它的上下文质量直接决定交接质量 → 用 `state.json`/`ledger.md` 把状态外置。

### 4. 上下文压缩

- **降级**：原文靠读 rollout 日志统计压缩次数。DSH 的会话记录是 `~/.dsh/sessions/<workspace>/<session-id>/session.v4.jsonl.zstd`，
  zstd 压缩的内部格式、无稳定文档保证 → **不能作为审计依据**，压缩计数监控整体作废。
- **补偿**：① 阶段级交接代替阈值交接：每完成一个阶段（DESIGN→PLAN→EXECUTING→VERIFYING→TRIAL）就落一次 `state.json` + `ledger.md`；
  ② 督察使改做**漂移检查**（`state.json` / `ledger.md` / 磁盘产物 三者一致），它同样能抓到"压缩后忘边界"；
  ③ 关键事实一律写盘，不留在对话里。
- **残余风险**：压缩发生在阶段中间时，只能靠下一轮漂移检查兜住，粒度比原版粗。

### 5. 线程 ID 核验

- **降级**：没有 `codex://threads/<UUID>` 这种可核验地址。`list_agents` 只给名字与状态，不给可校验元信息。
- **补偿**：① 启动子 Agent 时在 prompt 里**写死角色名、项目路径、feature 名**，回执里要求复述；
  ② Lead 用 `list_agents` 交叉核对名字（`reviewer/checker` 这类路径名天然不可混淆）；
  ③ 交接单 `handoffs/` 记录"谁交给谁、时间、产物路径"。
- **残余风险**：核验强度从"不可伪造地址"降到"自述 + 名字交叉"，属于流程级核验。

### 6. 投递状态（SENT / QUEUED / ACKNOWLEDGED）

- **降级**：原文三级状态是为"桌面锁屏导致投递受阻"设计的；DSH 没有输入框投递环节，也没有 `task_complete` 事件可读。
  `send_message` 返回投递确认，但"确认送达"≠"目标已读、已执行"。
- **补偿**：① ACK 以**磁盘回执**为准：`handoffs/<id>.ack.md` 或任务板 `complete`；
  ② 只有"回执落盘 + 任务板状态改变"才算送达，其余一律记"已发出，未确认"；
  ③ 判"已停止"用 `job_list` 无 running + 任务板已 complete + 回执文件存在，三件套替代原来的三项证据。
- **残余风险**：子 Agent 忘记写回执时，你只能判"未确认"，不能推断它执行了。

## 四、不可迁移项与替代方案

| 机制 | 为什么迁不走 | 替代方案 | 残余风险 |
|---|---|---|---|
| 压缩计数监控（纯脚本定时器） | 会话日志是 zstd 压缩的内部格式，且无"本代新增压缩"这类可读字段 | 阶段级交接 + 督察使漂移检查；需要真定时用 `schedule_create` | 粒度从"计数阈值"变成"阶段边界" |
| 三项停止门禁（停止回执 / task_complete / 无新回合） | DSH 子 Agent 没有可读的回合事件流 | `job_list` 无 running + 任务板 complete + 回执文件 | 后台作业可证，前台子 Agent 只能靠回执 |
| STS Guard（工具层路径写保护） | 本仓库不是 git 仓库、无平台级路径白名单；`write_scopes` 仅建议 | 文件只读属性（`attrib +R`，未实测）+ `flow.py audit` 高频抽查 + 反复越界升级为用户裁决 | 属"提高成本"，不是"物理阻断" |
| 独立副本 + 独立会话的物理隔离 | 单进程单 cwd，无 worktree、无文件锁 | 哈希基线 + 冻结快照 + Lead 复核 diff + 任务板写死边界 | **这是最实质的降级**，见第一节结论 |
| 锁屏导致投递受阻的人工解锁流程 | 桌面 GUI 由用户自己控制，不存在"程序投递到输入框"环节 | 不需要 | 无 |
| 人肉粘贴启动指令（`gen-kickoff.py` 输出） | 子 Agent 由工具调用创建 | 生成的指令改作 `subagent` 的 prompt 素材；占位符必须手工替换 | 少了"粘贴前人工看一眼"这一道校验 |

## 五、与 Codex 桌面版混用的推荐组合

| 阶段 | 建议平台 | 理由 |
|---|---|---|
| 需求澄清、方案规划 | DSH（`roles/01`） | 只读、产出文档，隔离要求低 |
| 拆组、写三份规划（SOURCE-PLAN 由 planner 起草） | DSH（`roles/00-lead.md`） | 纯文档工作 |
| 开发（长期跟进） | DSH `subagent` 或 Codex 桌面 | DSH 需靠纪律；核心诉求是"不能自证"时优先 Codex |
| 部署与线上核验 | **Codex 桌面优先** | 需要真独立见证 + 人工审批通道 |
| 每日审计 | DSH `schedule_create` + `roles/04` | 只读、可哈希核验，DSH 足够 |

混用的三条铁律：

1. **磁盘是唯一事实来源**：跨平台交接只认 `docs/<feature>/` 下的文件与哈希，不认"上一个会话说过"。
2. **Lead 必须自己看最终 diff**：DSH 官方要求，且工具层已无法保证隔离；这条不能派给任何 Agent。
3. **状态机只在一处推进**：`state.json` 只由 `tools/dsh_flow.py` 写，别让两个平台各写一份。

## 六、事实来源

### 已确认（读安装包/本地实测，2026-11-17）

| 事实 | 依据 |
|---|---|
| 当前工具清单与参数（含 `subagent`/`team_task_*`/`schedule_*`/`job_kill`/`create_worktree`/`wait_agent` 语义） | `cordis_inspect_query(host, Tool, listTools)` 实测输出 |
| git 2.56.1 与 node v24.21.0 已在 PATH；本包**不是 git 仓库**（`Test-Path .git` = False） | `git --version` / `Test-Path .git` 实测（2026-11-22 复核；本机仍无 bash） |
| PowerShell 5.1.22621.4111；Python 3.12.14（`$PY` 可执行） | 本地实测 |
| 会话持久化为 `~/.dsh/sessions/<workspace>/<session-id>/session.v4.jsonl.zstd` | 本地目录实测（8 个会话文件） |
| DSH Desktop 为 nightly 通道；运行时 node 24.21.0 / pnpm 11.28.5 | `resources/app-update.yml`、`resources/runtime/versions.json` |
| 原文 DSH 章节的工具名与"无 worktree"结论过时 | 逐条比对《平台适配-WorkBuddy与DSH.md》第二节表格 |
| `flow.py` 的子命令、只读性、`audit` 的告警分类、`gate/verify/audit --strict` 用退出码 1 表达"未通过" | 读 `tools/dsh_flow.py` 源码（1208 行，state schema `dsh-flow/state@1`） |

### 推断（未实测，使用前请自行验证一次）

| 推断 | 依据 | 风险 |
|---|---|---|
| `wait_agent` 不再能"等某个子 Agent 完成" | 工具描述只提"等下一个输入"，未提 agent 参数 | 交接逻辑若依赖"精确等某人"，需改成分阶段推进 |
| `send_message` 的"投递确认"不等于目标已读 | 描述为 delivery confirmation，未承诺 ACK | 回执必须落盘 |
| `attrib +R` 可作为弱写保护 | Windows 文件属性常识，未在本项目验证 | 提权/脚本可清除，只能算"提高成本" |
| `flow.py audit` 在真实项目里的误报率（未登记 vs 内容不一致的边界） | 只读了判定逻辑，未在真实项目跑过 | 首轮审计建议人工复核一遍告警再定级 |
| `schedule_*` 的休眠/崩溃补投行为 | 依据工具描述（"只补投最近一次"、"崩溃后可能重复投递"） | 首次上线先跑 `COUNT=1` 验证一次 |
