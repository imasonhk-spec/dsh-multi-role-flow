# EXECUTION-WORKPLAN · 执行子智能体任务分解

> **怎么用**：由 **Lead** 在 `PLAN` 阶段写，落盘到 `docs/{{FEATURE}}/EXECUTION-WORKPLAN.md`，然后整份交给执行子智能体（`subagent(name="{{DEV_NAME}}")`）。每条任务都可以单独派单，派单时把该条的编号、产出文件、不做清单一并写进 `prompt`。
> **填完触发什么**：`## 任务分解` 小节存在、任务从 `E1` 起连续编号、每条都有「产出文件 / 检查项 / 证据文件名」，才允许把 `state.json` 推进到 `EXECUTING` 并派单；缺项的任务不允许下发。

| 项 | 值 |
|---|---|
| 项目 / 功能 | {{PROJECT}} / {{FEATURE}} |
| 制定 | Lead（根智能体） |
| 执行 | 执行子智能体 `{{DEV_NAME}}` |
| 日期 | {{DATE}} |
| 配套必读 | `COORDINATION-PLAN.md`（权限矩阵与越界处理） |

## 执行约定

| 项 | 约定 |
|---|---|
| 平台 | Windows + DSH；git 2.56.1 与 node v24.21.0 在 PATH、`create_worktree` 可用但**本仓库不是 git 仓库**（未 `git init`，没有 diff 基线）；**无 bash**，shell 一律用 PowerShell |
| Python | `$PY = ~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe` |
| 改动尺度 | 最小、清晰、完整：补齐受影响的调用方、配置、测试与必要文档，但不以精简为由省略必要功能、安全校验、错误处理 |
| 不新增的东西 | 新依赖、抽象层、兼容层、防御机制，除非它针对本次真实失败路径；用途不明先调查再决定 |
| 范围 | 需求与计划确认后连续完成已授权工作，不逐步重复询问；影响已确认范围或重要取舍时才回报 Lead |
| 交接 | 只认磁盘文件与任务板；子智能体之间不能互相通信 |
| 证据诚实 | 只改 A 模块时 B 的旧证据可引用，但必须在 `manifest.json` 写明引用来源与理由；工具不可用就写「未运行」，不能写成通过 |

## 任务分解

> 基线阶段并入 E1，任务编号从 E1 起。`检查项` 列引用 `DESIGN.md` 的 P 编号；**证据文件名用检查编号（`P1.md`），不要用任务编号（`E2.md`）**——`freeze` 按证据里的 `检查：` 字段解析，编号对不上时验证线程无法复核。

| 编号 | 任务 | 产出文件 | 检查项 | 证据文件名 | 不做（本任务不碰） |
|---|---|---|---|---|---|
| E1 | 建立副本与事实核实 | `docs/{{FEATURE}}/EXECUTION-PLAN.md` | 无（记入台账） | 无（写进 `EXECUTION-PLAN.md`） | 不写业务代码，不安装任何东西 |
| E2 | {{TASK_1}} | `{{PATH_1}}` | P2 | `evidence/{{CANDIDATE}}/P2.md` | 不碰 `{{PATH_X}}` |
| E3 | {{TASK_2}} | `{{PATH_2}}` | P2、P3 | `evidence/{{CANDIDATE}}/P2.md`、`P3.md` | 不碰 `{{PATH_Y}}` |
| E4 | 补齐受影响方（调用方 / 配置 / 测试 / 文档） | `{{PATH_3}}` | P5 | `evidence/{{CANDIDATE}}/P5.md` | 不改已确认的业务规则 |
| E5 | 冻结候选并自验 | `releases/{{CANDIDATE}}/`（由 `freeze` 生成） | 全部 P | `verify` 输出写进 `EXECUTION-PLAN.md` | 不改已冻结内容，不自行部署 |

**E1 完成判据**：能说出「实际运行的是哪份代码（路径 + 版本）」「有哪些在途任务（ID 清单）」「独立副本能单独跑起来」。
**E5 完成判据**：`freeze` 退出码 0、`verify --id {{CANDIDATE}}` 退出码 0、`EXECUTION-PLAN.md` 的 `## 八、下一步` 已写清。

## 候选冻结

```powershell
$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$FLOW = "<flow-home>\tools\dsh_flow.py"
& $PY $FLOW freeze -p "<项目根>" -f {{FEATURE}} --id {{CANDIDATE}} --from "<项目根>-dev" --scope src
& $PY $FLOW verify -p "<项目根>" -f {{FEATURE}} --id {{CANDIDATE}}
```

| 步骤 | 内容 |
|---|---|
| 1 | `freeze` 把 dev 副本中 `scope` 内的文件复制到 `releases/{{CANDIDATE}}/files/`，并生成 `manifest.json`（**不手写**） |
| 2 | `verify` 复核哈希；不通过就修 dev 副本、出新候选编号，**不许改已冻结的候选** |
| 3 | 证据放在 `evidence/{{CANDIDATE}}/`，每条 P 检查一个 md，含 `检查：`/`等级：`/`结果：` |
| 4 | 把安装顺序、重启目标、回滚保留范围写进 `EXECUTION-PLAN.md` 的 `## 八、下一步` |
| 5 | 不部署；写完回报，由 Lead `advance` 后转验证线程 |

**必须出新候选**：候选交出后任何代码改动、冻结后发现问题需修复、配置项变更。**不需要**：只改文档。

## 报告格式

向 Lead 报告时按此填，禁止「进展顺利」「快完成了」这类话。

| 字段 | 内容 |
|---|---|
| 当前任务 | E{{TASK_NO}} {{TASK_NAME}} |
| 状态 | 进行中 / 完成 / 阻塞 |
| 本轮产出 | `{{OUTPUT_PATH}}` |
| 证据 | `evidence/{{CANDIDATE}}/{{EVIDENCE_FILE}}`（级别 {{EVIDENCE_LEVEL}}） |
| 下一步 | {{NEXT_ACTION}} |
| 阻塞 | {{BLOCKER}} |
| 发现未处理 | {{UNHANDLED_ITEM}}（只记录，不处理） |

## 状态推进

| 时点 | 动作 |
|---|---|
| E1 完成 | Lead 核对基线与「不做清单」，确认后放行 E2 |
| E2—E4 每完成一条 | 代码改动只落在「产出文件」列内；不在列内的改动先报 Lead |
| E5 完成 | 候选冻结，`state.json` 推进到 `VERIFYING`，交给验证子智能体 |
| 收到问题报告 | 按原任务编号与证据定位，判断是业务问题还是部署问题，不口头通知 |

## 必填项清单

- [ ] 存在标题完全等于 `## 任务分解` 的小节
- [ ] 任务编号从 `E1` 起连续，无 E0、无跳号
- [ ] 每条任务都有非空的「产出文件」「检查项」「证据文件名」三格
- [ ] 每条任务都有「不做」内容，不许留空或写「无」
- [ ] 证据文件名与 `evidence/{{CANDIDATE}}/` 下的真实文件对应
- [ ] 全文没有残留的未替换占位符
