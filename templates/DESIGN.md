# DESIGN · {{PROJECT}} / {{FEATURE}}

> **怎么用**：由 **Lead** 在 `DESIGN` 阶段填写，落盘到 `docs/{{FEATURE}}/DESIGN.md`。DSH 里没有独立的「总线程」会话——总线程就是 Lead 本身，所以规划文档只能由 Lead 写。需求每问清一轮就更新一次，不要攒到最后再写。
> **填完触发什么**：出现 `状态：已确认` 后，才能用 `$PY tools/dsh_flow.py` 把 `docs/{{FEATURE}}/state.json` 从 `DESIGN` 推进到 `PLAN`；未确认时只能停在 `DESIGN`。本文件的「验收标准」和「不改什么（边界）」两节，是 PLAN 阶段另外四份规划的唯一输入来源。

| 项 | 值 |
|---|---|
| 项目 / 功能 | {{PROJECT}} / {{FEATURE}} |
| 工作区 | `{{WORKSPACE}}` |
| 方案版本 | v{{VERSION}} |
| 制定 | Lead（根智能体） |
| 日期 | {{DATE}} |
| 需求来源 | `docs/{{FEATURE}}/SOURCE-PLAN.md` |

状态：待用户确认

> 上面一行是门禁字段，只允许 `状态：待用户确认` 或 `状态：已确认` 两个取值；不加粗、不加后缀、不写成别的说法。

## 用户需求原文

> 一字不改贴用户原话。转述会失真，失真的需求会在执行阶段被子智能体放大成返工。

```text
{{USER_REQUEST}}
```

## 目标与不做

**一句话目标**：{{GOAL_ONE_SENTENCE}}

| 不做的事 | 理由 | 后续何时考虑 |
|---|---|---|
| {{OUT_OF_SCOPE_ITEM}} | {{OUT_OF_SCOPE_REASON}} | {{DEFERRED_CONDITION}} |

> 这一节比「做什么」更重要：它防止执行子智能体顺手扩大范围。

## 必须交付的行为

| 行为 | 触发 | 成功标准（可验证） | 失败 / 异常 | 验收动作 |
|---|---|---|---|---|
| {{BEHAVIOR_1}} | {{TRIGGER}} | {{SUCCESS_CRITERION}} | {{FAILURE_HANDLING}} | {{ACCEPTANCE_ACTION}} |

规则：{{BEHAVIOR_RULE}}

## 验收标准

> 编号 P1、P2… 含义固定，PLAN 阶段的 `VALIDATION-WORKPLAN.md` 逐条对应成 V 编号。没有证据文件的条目不算通过。

| 编号 | 检查项 | 通过标准（命令 + 期望结果） | 证据级别 | 证据文件名 |
|---|---|---|---|---|
| P1 | PowerShell 语法 / 构建 / 受影响测试 | `{{P1_COMMAND}}` 退出码 0 | A | `evidence/{{CANDIDATE}}/P1.log` |
| P2 | {{CORE_CHAIN}} | {{CORE_CHAIN_RESULT}} | A 或 C | `evidence/{{CANDIDATE}}/P2.log` |
| P3 | 权限与越权 | 越权请求被拒绝，无跨账号访问 | A | `evidence/{{CANDIDATE}}/P3.log` |
| P4 | 故障保留 | {{FAULT_RETENTION}} | B | `evidence/{{CANDIDATE}}/P4.json` |
| P5 | 受影响旧功能回归 | {{REGRESSION_RESULT}} | A 或 C | `evidence/{{CANDIDATE}}/P5.log` |

**待用户试用项**（不阻塞上线，但不能算已验收）：{{TRIAL_ITEMS}}

## 不改什么（边界）

> 这是「不做清单」的方案层版本。`write_scopes` 只是建议性写范围，PowerShell 想绕就能绕过，所以边界只能靠这张表加越界处理规则来守。

| 层面 | 是否可改 | 说明 |
|---|---|---|
| 业务规则与结果 | ❌ 不改 | {{PROTECTED_BEHAVIOR}} |
| 源码实现 | ✅ 仅最小改动 | {{IMPLEMENTATION_BOUNDARY}} |
| 数据格式 / 配置 | {{DATA_FORMAT_VERDICT}} | {{DATA_FORMAT_NOTE}} |

**本次明确不碰**（即使看起来相关）：

| 不碰的文件或目录 | 理由 |
|---|---|
| `{{PATH_A}}` | {{PATH_A_REASON}} |
| `{{PATH_B}}` | {{PATH_B_REASON}} |

判断标准只有一个：**在不在上面这张表里**。拿不准时先只读调查，记入「发现未处理」，不要先做了再说。

## 风险与前提

| 假设 / 风险 | 验证方式 | 不成立时怎么办 |
|---|---|---|
| {{ASSUMPTION_1}} | {{VERIFY_COMMAND}} | {{FALLBACK_ACTION}} |
| {{ASSUMPTION_2}} | {{VERIFY_COMMAND_2}} | {{FALLBACK_ACTION_2}} |

## 待用户裁决

| 编号 | 问题 | 我的建议 | 用户回答 |
|---|---|---|---|
| Q1 | {{DECISION_QUESTION}} | {{LEAD_ADVICE}} | {{USER_ANSWER}} |

## 变更历史

| 版本 | 日期 | 变更内容 | 来源 |
|---|---|---|---|
| v1 | {{DATE}} | 初版 | Lead 与用户逐轮确认 |

需求、验收标准或数据格式变更必须走 `flow.py amend --reason "..."`：旧版归档到 `design-history/`、方案版本 +1、状态置回 `状态：待用户确认`，用户重新确认后再 `unblock` + `advance`。不要在已确认版本上直接改验收标准——旧验收标准是已发生事实的对照物。

## 必填项清单

> 门禁逐条检查；任一不满足即视为未完成 `DESIGN`。

- [ ] `状态：` 行存在，取值为 `状态：待用户确认` 或 `状态：已确认`，没有第三种写法
- [ ] 存在标题完全等于 `## 验收标准` 的小节，且至少有 P1 一行、每行都有证据文件名
- [ ] 存在标题完全等于 `## 不改什么（边界）` 的小节，且「明确不碰」表至少一行
- [ ] 用户需求原文是原文块，不是转述
- [ ] 每条「必须交付的行为」都有可执行的验收动作
- [ ] 全文没有残留的未替换占位符
