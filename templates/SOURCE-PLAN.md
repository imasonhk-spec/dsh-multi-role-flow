# SOURCE-PLAN · 需求来源与假设登记

> **怎么用**：由 **Lead** 在 `PLAN` 阶段最先写这一份，落盘到 `docs/{{FEATURE}}/SOURCE-PLAN.md`。它不参与门禁判定，作用只有一个：把「需求从哪来、当时按什么假设做的、后来改过什么」固定下来，避免执行到一半没人记得依据是什么。
> **填完触发什么**：不触发门禁，但它是 `EXECUTION-WORKPLAN.md` 里每条任务「依据」列的引用源；假设被推翻时，必须回来改这里并说明影响面。

| 项 | 值 |
|---|---|
| 项目 / 功能 | {{PROJECT}} / {{FEATURE}} |
| 制定 | Lead（根智能体） |
| 日期 | {{DATE}} |
| 版本 | v{{VERSION}} |
| 上游 | `docs/{{FEATURE}}/DESIGN.md` v{{VERSION}} |
| 当前状态 | {{CURRENT_STATE}} |

## 需求来源

### 用户原话

> 一字不改，按时间顺序列出每一次明确表述。转述会丢掉边界条件。

```text
{{USER_WORDING_LOG}}
```

### 需求演进

| 时间 | 用户表述摘要 | 对方案的影响 |
|---|---|---|
| {{DATE}} | {{EVOLUTION_SUMMARY}} | {{EVOLUTION_IMPACT}} |

> 为什么要记演进：需求变更后旧文档会误导执行子智能体。有了这张表，才能说清「哪一版方案对应哪个时间点的需求」。

## 假设登记

> 每条假设都要能被核验；核验不了就写成风险，不要写成结论。

| 编号 | 假设 | 为什么这样假设 | 核验方式 | 不成立时怎么办 |
|---|---|---|---|---|
| A1 | {{ASSUMPTION_1}} | {{ASSUMPTION_BASIS}} | {{READONLY_COMMAND}} | {{ASSUMPTION_FALLBACK}} |
| A2 | {{ASSUMPTION_2}} | {{ASSUMPTION_BASIS_2}} | {{READONLY_COMMAND_2}} | {{ASSUMPTION_FALLBACK_2}} |

## 关键决策

| 决策 | 选定 | 放弃的方案 | 理由 |
|---|---|---|---|
| {{DECISION_TOPIC}} | {{CHOSEN_OPTION}} | {{REJECTED_OPTION}} | {{DECISION_REASON}} |

## 方案出处

| 文档 | 路径 | 版本 | 状态 |
|---|---|---|---|
| 设计方案 | `docs/{{FEATURE}}/DESIGN.md` | v{{VERSION}} | {{DESIGN_STATUS}} |
| 本规划 | `docs/{{FEATURE}}/SOURCE-PLAN.md` | v{{VERSION}} | 生效 |
| 协调规划 | `docs/{{FEATURE}}/COORDINATION-PLAN.md` | v{{VERSION}} | 生效 |
| 执行计划 | `docs/{{FEATURE}}/EXECUTION-WORKPLAN.md` | v{{VERSION}} | 生效 |
| 验证计划 | `docs/{{FEATURE}}/VALIDATION-WORKPLAN.md` | v{{VERSION}} | 生效 |

规则：四份规划同版本发布，任一份改了版本，其余三份一起改。

## 历史教训继承

> 只保留一句结论，不复述完整故事。

| 教训 | 在本项目的落点 |
|---|---|
| 文档描述的运行状态与真实状态不一致 | E1 必须查运行时，不读文档就下结论 |
| 把「计划完成」当「交付完成」 | 报告必须区分「已上线可试用」与「已验收」 |
| 「看起来相关」就顺手改 | 每份计划都有「不做」一行，越界即回退 |

## 背景材料索引

> 只记路径和用途，不复制内容。

| 材料 | 路径 | 用途 |
|---|---|---|
| 现有实现 | `{{PATH_IMPL}}` | E1 核实用 |
| 接口 / 配置 | `{{PATH_CONFIG}}` | 契约与环境基线 |
| 历史方案 | `{{PATH_HISTORY}}` | 已废弃，仅作参考 |

## 不在本方案范围

| 事项 | 原因 | 后续条件 |
|---|---|---|
| {{OUT_OF_SCOPE_ITEM}} | {{OUT_OF_SCOPE_REASON}} | {{DEFERRED_CONDITION}} |

## 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | {{DATE}} | 初版 |

## 必填项清单

> 本文件不进自动门禁，但下列项缺了就说明来源没固定住。

- [ ] 用户原话是原文块，不是摘要
- [ ] 需求演进表覆盖每一次明确的需求变更
- [ ] 每条假设都有核验方式与不成立时的处理
- [ ] 四份规划的版本号与本文件一致
- [ ] 全文没有残留的未替换占位符
