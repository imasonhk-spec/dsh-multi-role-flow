# EXECUTION-PLAN · 执行线程工作台账

**怎么用**：Lead 派出执行子智能体后，执行线程在 `EXECUTING` 阶段开工第一件事就是建立本文件；每完成一个动作追加一行，不要攒到最后。本文件是执行线程自己的工作记忆，验证线程与 Lead 只读不改。

| 项 | 值 |
|---|---|
| 项目根 | `{{PROJECT_ROOT}}` |
| 功能 | `{{FEATURE}}` |
| 开发副本 | `{{DEV_DIR}}` |
| 执行子智能体 | `{{EXECUTOR_AGENT}}` |
| 当前候选 | `{{CANDIDATE}}` |
| 开工时间 | {{STARTED_AT}} |

> 状态机 `EXECUTING → VERIFYING → TRIAL → DONE` 由 `tools/dsh_flow.py` 写进 `docs/{{FEATURE}}/state.json`。本文件只记事、**不改状态**；要转阶段就跑工具，不要手改 `state.json`。

## 一、进度（当前在做）

| 项 | 内容 |
|---|---|
| 正在做 | {{CURRENT_TASK}} |
| 做到哪一步 | {{CURRENT_STEP}} |
| 下一步 | {{NEXT_ACTION}} |
| 预计产出 | {{EXPECTED_OUTPUT}} |
| 卡点 | {{BLOCKER_OR_NONE}} |

改完一处就更新本表，别让本表落后于实际进度。

## 二、发现但不处理

> **越界最常见的借口是"看起来相关"。判据只有一条：在不在本阶段文件白名单里。不在就记这里，不动手。**

| 发现 | 位置 | 为什么不处理 | 建议 |
|---|---|---|---|
| {{FINDING}} | `{{FILE_PATH}}:{{LINE_NO}}` | 超出本次授权范围 | 另开候选 `{{NEXT_CANDIDATE}}` |

**本候选文件白名单**（不在表内的一律算越界）：

| 类型 | 允许改动的路径 |
|---|---|
| 源码 | `{{SOURCE_PATH}}` |
| 测试 | `{{TEST_PATH}}` |
| 配置 | `{{CONFIG_PATH}}` |

**越界审计**（每阶段结束跑一次；无 git 环境靠它兜底）：

```powershell
$PY tools/dsh_flow.py audit -p {{PROJECT_ROOT}} -f {{FEATURE}}
```

审计对比 `docs/{{FEATURE}}/baseline.json` 与当前树。白名单外的改动必须能在上面「发现但不处理」里找到，否则立即停手补授权。

## 三、在途任务

> 发出去但没收到结果的操作，必须记原 ID：**先对账，不重发**。

| 类型 | 原 ID | 发出时间 | 状态 | 是否可重发 |
|---|---|---|---|---|
| {{TASK_TYPE}} | `{{TASK_ID}}` | {{SENT_AT}} | unknown | ❌ 先对账 |

对账结论只有三种：已完成（记结果，不重发）／未执行（可重发）／无法确认（记永久未知，交验证线程部署时保留）。漏记的后果是任务 ID 丢失，只能永远记为"未知"。

## 四、候选历史

| 候选 | 冻结时间 | 变更摘要 | 状态 | 交付时间 | 验证结论 |
|---|---|---|---|---|---|
| `{{CANDIDATE}}` | {{FROZEN_AT}} | {{CHANGE_SUMMARY}} | 开发中 | {{DELIVERED_AT}} | {{VERDICT}} |

状态：开发中 / 已冻结 / 已交付 / 已安装 / 已部署 / 已被替代。

冻结不可逆：候选一旦冻结，再改文件就出下一个候选 `{{NEXT_CANDIDATE}}`，并在 `releases/{{CANDIDATE}}/manifest.json` 留痕；不要回头改已冻结的包。

## 五、开发日志

| 时间 | 做了什么 | 改动文件 | 产出证据 |
|---|---|---|---|
| {{TIMESTAMP}} | {{ACTION}} | `{{FILE_PATH}}` | `docs/{{FEATURE}}/evidence/{{CANDIDATE}}/{{EVIDENCE_FILE}}` |

写清"产出 + 证据 + 怎么验的"，不要只写"完成了 X"。

## 六、检查证据

证据分级：**A** 命令原文与退出码／**B** 文件哈希与清单／**C** 截图或页面回执／**D** 自述。声称"已通过"至少 B 级，D 级只能写"声称通过"。

| 编号 | 检查项 | 结果 | 等级 | 证据路径 | 命令与退出码 |
|---|---|---|---|---|---|
| T-01 | 构建/语法 | {{RESULT}} | {{GRADE}} | `docs/{{FEATURE}}/evidence/{{CANDIDATE}}/T-01.md` | `{{COMMAND}}` → exit {{EXIT_CODE}} |
| T-02 | {{CHECK_NAME}} | {{RESULT}} | {{GRADE}} | `docs/{{FEATURE}}/evidence/{{CANDIDATE}}/T-02.md` | `{{COMMAND}}` → exit {{EXIT_CODE}} |

**诚实性备注**（必填，缺一项就算未报告）：哪些证据是接口注入而非真实端到端、哪些检查工具不可用未运行、哪些旧证据被引用及其理由。

## 七、阻塞与升级

| 阻塞 | 影响 | 已尝试 | 需要谁做什么 |
|---|---|---|---|
| {{BLOCKER}} | {{IMPACT}} | {{ATTEMPTED}} | {{OWNER_ACTION}} |

- 技术问题：自查 2 轮无果 → 报 Lead。
- 范围问题：立即停手，交 Lead 裁决，不自行扩大改动。
- 权限问题：立即停手，等明确授权；本线程不安装、不重启、不改生产数据。

## 八、下一步（下一批次可直接执行）

> 接力必读：下一批执行线程（或压缩后的新会话）只看本文件这一节 + `handoffs/` 最新交接包就能续上。

- 当前候选：{{CANDIDATE}}（状态：{{STATUS}}）
- 下一批次要做什么：{{NEXT_BATCH_ACTION}}
- 需要 Lead 做的：{{LEAD_ACTION}}
- 安装请求（给验证线程）：`manifest.install_order` 与 `restart_targets` 已写清；无则填「无」

## 必填项清单

- [ ] 表头六项齐全，`{{CANDIDATE}}` 与 `releases/` 下实际目录一致
- [ ] 「当前在做」已更新到最近一步
- [ ] 「发现但不处理」记录了白名单外的一切改动
- [ ] 白名单与实际改动文件一致，`audit` 结果已贴
- [ ] 「在途任务」无遗漏；没有在途也要写"无"
- [ ] 「候选历史」状态与实际一致
- [ ] 每条证据都有等级、路径、命令与退出码
- [ ] 诚实性备注已填，未运行项已列出
