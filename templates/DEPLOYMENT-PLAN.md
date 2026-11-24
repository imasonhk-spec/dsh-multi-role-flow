# DEPLOYMENT-PLAN · 验证线程部署台账

**怎么用**：候选冻结、状态机进入 `VERIFYING` 后，验证子智能体第一件事就是建本文件；每次核验、安装、重启、回滚、线上核验后当场补一行。执行线程只读不改，业务问题写回 `releases/{{CANDIDATE}}/RELEASE-REPORT.md`。

| 项 | 值 |
|---|---|
| 项目根 | `{{PROJECT_ROOT}}` |
| 功能 | `{{FEATURE}}` |
| 候选 | `{{CANDIDATE}}` |
| 验证子智能体 | `{{VERIFIER_AGENT}}` |
| 建档时间 | {{STARTED_AT}} |
| 当前阶段 | `VERIFYING` |

> 平台 Windows；git 2.56.1 与 node v24.21.0 在 PATH、`create_worktree` 可用但本仓库不是 git 仓库（未 `git init`，没有 diff 基线）；无 bash。Python 统一用 `$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"`。

## 一、当前状态

| 项 | 内容 |
|---|---|
| 正在做 | {{CURRENT_TASK}} |
| 等待 | {{WAITING_FOR}} |
| 下一步 | {{NEXT_ACTION}} |

## 二、候选核验结果

| 核验项 | 方法 | 结果 | 备注 |
|---|---|---|---|
| 冻结包完整 | 文件数 + 逐个 `Get-FileHash -Algorithm SHA256` | {{RESULT}} | 与 `manifest.json` 的 `artifacts` 逐条比对 |
| 证据可复核 | 打开 `evidence/{{CANDIDATE}}/`，看时间晚于冻结、输出未截断 | {{RESULT}} | 等级 A/B/C/D |
| 引用旧结论 | 核对 `checks.reused[].reason` 与本次改动文件 | {{RESULT}} | 理由不成立即退回 |
| 门禁 | `$PY tools/dsh_flow.py gate -p {{PROJECT_ROOT}} -f {{FEATURE}}` | `{{GATE_STATUS}}` | 参数以 `--help` 为准 |
| 在途任务 | 核对 `manifest.json` 的 `active_tasks` 与实际查询 | {{RESULT}} | 空数组也要核对 |

**核验结论**：{{VERDICT}}（放行安装 / 退回执行线程补证据）。

## 三、安装步骤与顺序

| 序 | 动作 | 命令 | 预期 | 实际 |
|---|---|---|---|---|
| 1 | 备份现网文件 | `Copy-Item -Recurse -LiteralPath {{TARGET_PATH}} -Destination {{BACKUP_DIR}}` | 备份可读 | {{RESULT}} |
| 2 | 按 `install_order` 覆盖 | `Copy-Item -Force -LiteralPath {{SOURCE_ARTIFACT}} -Destination {{TARGET_PATH}}` | 哈希与 manifest 一致 | {{RESULT}} |
| 3 | 精确重启 | 见第四节 | 启动时间晚于文件修改 | {{RESULT}} |
| 4 | 线上核验 | 见第六节 | 见第六节 | {{RESULT}} |

顺序不可颠倒：**先备份 → 再覆盖 → 再重启 → 最后核验**。每覆盖一个文件立刻重算哈希，不要全部装完再一次性验。

## 四、重启目标

| 组件 | 端口 | 实际 PID | 精确重启方式 | 禁止操作 |
|---|---|---|---|---|
| {{COMPONENT}} | {{PORT}} | {{PID}} | `Stop-Process -Id {{PID}} -Force`，再 `{{START_COMMAND}}` 拉起 | `Stop-Process -Name python`、`taskkill /IM python.exe` |

进程归属核实（**不要凭印象**）：

```powershell
Get-NetTCPConnection -LocalPort {{PORT}} -State Listen | Select-Object -ExpandProperty OwningProcess
Get-CimInstance Win32_Process -Filter "ProcessId={{PID}}" | Select-Object ProcessId,ParentProcessId,CommandLine
(Get-Process -Id {{PID}}).StartTime
```

❌ `taskkill /IM python.exe`、❌ `Stop-Process -Name {{GENERIC_NAME}}`、❌ 重启整个进程树、❌ 有待处理任务时强制切换。

## 五、回滚步骤

| 序 | 动作 | 命令 / 判据 |
|---|---|---|
| 1 | 保留新产生的数据 | `{{PRESERVE_PATH}}` 不得被旧备份覆盖 |
| 2 | 记录在途任务原 ID | 写回 `manifest.json` 的 `rollback.preserve` |
| 3 | 关闭新入口 | {{CLOSE_ENTRY}} |
| 4 | 恢复代码与配置 | `Copy-Item -Force -LiteralPath {{BACKUP_ARTIFACT}} -Destination {{TARGET_PATH}}` |
| 5 | 恢复后核验 | 第六节全部重跑一遍 |

`rollback.restore_from` 取 `previous_candidate` 或 `baseline`，二选一写清，不要留空。
❌ 只看备份目录存在；✅ 实际恢复到临时位置并读出文件，确认可恢复。

## 六、线上核验证据

| 核验项 | 命令 | 期望 | 证据路径 | 结果 |
|---|---|---|---|---|
| 实际加载版本 | `Invoke-RestMethod {{HEALTH_URL}}` 的版本字段 | 与 `artifacts` 哈希一致 | `docs/{{FEATURE}}/evidence/{{CANDIDATE}}/V1-health.json` | {{RESULT}} |
| 进程状态 | `Get-Process -Id {{PID}}` | 启动时间晚于文件修改 | 同上 | {{RESULT}} |
| 页面回执 | 浏览器 asset hash | 与候选一致 | `evidence/{{CANDIDATE}}/V2-page.md` | {{RESULT}} |
| 原有数据可访问 | {{DATA_CHECK}} | 历史记录可打开 | 同上 | {{RESULT}} |
| 异常日志 | {{LOG_PATH}} | 无新增 error | 同上 | {{RESULT}} |

❌ 用文件 mtime 或进程启动时间证明加载版本；✅ 用运行时读到的版本号 / 构建哈希。

## 七、问题归属

| 现象 | 证据 | 归属 | 处理 |
|---|---|---|---|
| {{SYMPTOM}} | `{{EVIDENCE_PATH}}` | 业务代码 / 部署方式 / 环境 | {{ACTION}} |

业务代码问题 → 交执行线程出下一个候选；部署方式问题 → 调本文件第三、四节；环境问题 → 记录并评估是否阻塞。

## 八、下一步（留给 Lead / 执行线程）

> 交接摘要写这里，不要另写交接包（`handoffs/` 由 Lead 用 `next` 生成）。

- 发布结论：{{CONCLUSION}}（三态之一）
- 需执行线程修的（如有）：{{EXECUTOR_ACTION}}
- 需 Lead 做的（advance / 用户试用 / 回滚决定）：{{LEAD_ACTION}}
- 待用户试用项：{{USER_TRIAL_ITEMS}}
- 下一候选（如已存在）：{{NEXT_CANDIDATE}}

## 必填项清单

- [ ] 五个必填小节齐全：候选核验结果、安装步骤与顺序、重启目标、回滚步骤、线上核验证据
- [ ] 核验结论明确写"放行"或"退回"
- [ ] 每个文件哈希都与 `manifest.json` 比对过
- [ ] 重启只作用于精确 PID，未用通配杀进程
- [ ] 回滚保留范围与 `rollback.preserve` 一致
- [ ] 线上核验证据是运行时读取值，不是文件 mtime
