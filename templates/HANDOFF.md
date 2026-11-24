# HANDOFF · 递归交接包

**怎么用**：任一线程交棒前（Lead 换人、子智能体结束、上下文被裁剪后重开）写本文件，落到 `docs/{{FEATURE}}/handoffs/{{HANDOFF_ID}}.md`。**下一任只看这一个文件就必须能续上**；写含糊等于让下一任重复劳动或做错事。

| 项 | 值 |
|---|---|
| 项目根 | `{{PROJECT_ROOT}}` |
| 功能 | `{{FEATURE}}` |
| 当前阶段 | `{{STAGE}}`（`EXECUTING` / `VERIFYING` / `TRIAL` / `DONE`） |
| 当前候选 | `{{CANDIDATE}}` |
| 写入方 | `{{FROM_AGENT}}` |
| 接手方 | `{{TO_AGENT}}` |
| 写入时间 | {{WRITTEN_AT}} |
| generation | {{GENERATION}} |
| candidates_frozen | {{CANDIDATES_FROZEN}} |

> 执行线程与验证线程是 Lead 用 `subagent` 派出的两个子智能体，**互相不能通信**；所有交接走磁盘文件与本文件。本文件不改变状态机，状态只由 `tools/dsh_flow.py` 写 `state.json`。

## 一、当前阶段与下一步唯一动作

| 项 | 内容 |
|---|---|
| 下一步唯一动作 | {{NEXT_SINGLE_ACTION}} |
| 完成判据 | {{DONE_CRITERIA}} |
| 做之前的核验 | 先只读核验第三节与第四节，核验不过就停手报告，不要先动手 |

## 二、当前候选

| 项 | 值 |
|---|---|
| 候选编号 | `{{CANDIDATE}}` |
| 父候选 | `{{PARENT_CANDIDATE_OR_NULL}}` |
| 冻结时间 | {{FROZEN_AT}} |
| 冻结包 | `docs/{{FEATURE}}/releases/{{CANDIDATE}}/files/` |
| 清单 | `docs/{{FEATURE}}/releases/{{CANDIDATE}}/manifest.json` |
| 安装顺序 | {{INSTALL_ORDER}} |
| 门禁 | `{{GATE_STATUS}}`（`ready` / `blocked`） |
| 已安装到 | {{INSTALLED_TO_OR_NONE}} |

## 三、已完成证据索引

| 检查项 | 结果 | 等级 | 路径 | sha256 |
|---|---|---|---|---|
| {{CHECK_ID}} | {{RESULT}} | {{GRADE}} | `docs/{{FEATURE}}/evidence/{{CANDIDATE}}/{{CHECK_ID}}.md` | `{{SHA256}}` |

等级：**A** 命令原文与退出码／**B** 文件哈希与清单／**C** 截图或页面回执／**D** 自述。D 级只能写"声称通过"，不能当通过依据。

## 四、未完成项

| 未完成 | 卡在哪 | 需要谁 | 影响 |
|---|---|---|---|
| {{TODO_ITEM}} | {{BLOCKER}} | {{OWNER}} | {{IMPACT}} |

在途但未收到结果的操作，必须记原 ID：**先对账，不重发**。

| 类型 | 原 ID | 状态 | 是否可重发 |
|---|---|---|---|
| {{TASK_TYPE}} | `{{TASK_ID}}` | unknown | ❌ 先对账 |

## 五、关键路径

| 用途 | 路径 |
|---|---|
| 状态机 | `docs/{{FEATURE}}/state.json`（只由工具写） |
| 基线 | `docs/{{FEATURE}}/baseline.json` |
| 台账 | `docs/{{FEATURE}}/ledger.md` |
| 执行台账 | `docs/{{FEATURE}}/EXECUTION-PLAN.md` |
| 部署台账 | `docs/{{FEATURE}}/DEPLOYMENT-PLAN.md` |
| 验收 | `docs/{{FEATURE}}/ACCEPTANCE.md` |
| 证据 | `docs/{{FEATURE}}/evidence/{{CANDIDATE}}/` |
| 候选包 | `docs/{{FEATURE}}/releases/{{CANDIDATE}}/` |
| 开发副本 | `{{DEV_DIR}}` |
| 流程工具 | `$PY tools/dsh_flow.py`（`freeze` / `audit` / `gate`，参数以 `--help` 为准） |

## 六、禁止事项

| 禁止 | 原因 |
|---|---|
| 手工改 `state.json` 或跳阶段 | 状态只由 `tools/dsh_flow.py` 推进，跳阶段等于绕过门禁 |
| 改已冻结候选的文件 | 冻结不可逆，要改就出下一个候选 |
| 执行线程安装 / 重启 / 线上核验 | 纵向越界，失去独立见证 |
| 验证线程改业务代码或"顺手修 bug" | 横向越界，问题应退回执行线程 |
| 删除或覆盖 `baseline.json`、证据、在途任务记录 | 越界审计与回滚的唯一依据 |
| 用 D 级证据声明"已通过" | 自述不构成证据 |

## 七、计数器与写回规则

| 计数器 | 当前值 | 规则 |
|---|---|---|
| `generation` | {{GENERATION}} | 每写一个交接包 +1，不重置、不从 0 猜 |
| `candidates_frozen` | {{CANDIDATES_FROZEN}} | 必须等于 `releases/` 下候选目录数，不相等即事故，先对账再干活 |

写交接包时同步：更新本文件三处计数器 → 把新文件路径记进第四节 → 不修改上一代交接包。

## 八、接手核验清单

- [ ] 前一位线程已停止，无在途写入
- [ ] `state.json` 的阶段与本文件表头一致
- [ ] `releases/` 候选数与 `candidates_frozen` 一致
- [ ] 第三节证据文件都存在且可读
- [ ] 第四节在途任务原 ID 已记录，未知结果已列明
- [ ] 禁止事项已读，权限范围已确认
- [ ] 只执行第一节的"下一步唯一动作"，不扩大范围

## 九、已知上下文（自动摘要）

> `dsh_flow.py next` 生成的交接包 §1 就是这一节，人工交接也必须带。五个子块缺哪个都写「未提供（原因 + 怎么补）」，**不许留空**；整节默认 ≤3000 字符，超出按块裁剪并写「已截断，完整见 <路径>」。

| 子块 | 来源（写绝对/项目内路径，让接手方能自己核对） | 内容要求 |
|---|---|---|
| 图谱摘要 | `<项目根>/graphify-out/graph.json` | 节点数/边数（边在 `links` 键）+ 文件分布 top5 + 与 scope 相交的文件节点数；无图写「未建图」+ 手工建图命令 |
| 上一候选已报的坑 | `docs/{{FEATURE}}/releases/{{CANDIDATE}}/RELEASE-REPORT.md` | 只摘 `## 已知问题` 与 `## 给执行线程的信息` 两节，各 ≤15 行；无候选写「尚无候选」 |
| 同类坑（跨 feature） | `ops/lessons.md`（按「适用角色」过滤） | 每条一行「症状 → 做法（L00x）」，角色条 ≤3 + `all` 条 ≤2；库未建写「教训库未建（`lesson add` 补）」 |
| 项目关键事实 | `<memories>/projects/<sha1(项目根)[:12]>/KEY.md` → `docs/{{FEATURE}}/CONTEXT-NOTES.md` → `--key-note` | 顺序即优先级（后者排最后），每条一行并标注来源绝对路径；三项都没有写「未提供」 |
| 知识入口 | `docs/{{FEATURE}}/DESIGN.md` + `state.scope` + `graphify-out/graph.json` | mnemon/agentmem 检索建议词 + 三套记忆离线探测（只写「在/不在」，不写「可用/不可用」）+ RAG 降级行；**不调 MCP、不发网络请求**；预算不足时压成一行 |

## 十、同类坑

> 本 feature / 本阶段该防的坑，从 `ops/lessons.md` 按角色取（`lesson list --role <角色>`）；踩到新坑收尾时用 `lesson add` 追加，不要只写在回报正文里。

| 教训 ID | 症状 | 做法（下次怎么防） | 来源 |
|---|---|---|---|
| `L00x` | 一句话，能被人搜到 | 具体动作，不是「注意一下」 | `ops/lessons.md` |

## 必填项清单

- [ ] 表头八项齐全，含 `generation` 与 `candidates_frozen`
- [ ] 当前阶段在三态之内，且与 `state.json` 一致
- [ ] 当前候选有冻结包路径与门禁状态
- [ ] 已完成证据有等级与路径
- [ ] 未完成项有归属与影响
- [ ] 关键路径与禁止事项已列全
- [ ] 「下一步唯一动作」只有一个，且可判定完成
