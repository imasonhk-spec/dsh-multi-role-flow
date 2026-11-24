# 发布报告 · {{CANDIDATE}}

**怎么用**：验证线程在部署完成后写本文件，落到 `docs/{{FEATURE}}/releases/{{CANDIDATE}}/RELEASE-REPORT.md`；执行线程只读。它是"装了什么、验了什么、能不能给用户试"的唯一对外结论。

| 项 | 值 |
|---|---|
| 项目根 | `{{PROJECT_ROOT}}` |
| 功能 | `{{FEATURE}}` |
| 候选 | `{{CANDIDATE}}` |
| 父候选 | `{{PARENT_CANDIDATE_OR_NULL}}` |
| 验证子智能体 | `{{VERIFIER_AGENT}}` |
| 发布编号 | `{{RELEASE_ID}}` |
| 时间 | {{RELEASED_AT}} |

## 安装事实

| 项 | 值 |
|---|---|
| 开始 / 结束 | {{STARTED_AT}} / {{FINISHED_AT}}（耗时 {{DURATION}}） |
| 安装文件数 | {{FILE_COUNT}}，与 `manifest.json` 的 `artifacts` 条数一致 |
| 关键文件指纹 | `{{ARTIFACT_PATH}}` → `{{SHA256}}` |
| 安装前备份 | `{{BACKUP_DIR}}`（已验证可恢复） |

## 运行时版本与重启

> 期望版本以 `manifest.runtime.version` 为准，以运行时实际返回为准；不以文件 mtime、进程启动时间或安装回执代替。

| 字段 | 值 |
|---|---|
| 健康检查地址 | `{{HEALTH_URL}}`（GET，应返回 `{ok, version, routes}`） |
| 期望版本（`manifest.runtime.version`） | `{{RUNTIME_VERSION}}` |
| 实际版本（运行时读到） | `{{ACTUAL_VERSION}}` |
| 握手证据 | `evidence/{{CANDIDATE}}/R1-handshake.md`（`flow.py handshake` 退出码 {{HANDSHAKE_EXIT_CODE}}） |
| 是否需要重启 | {{RESTART_REQUIRED}}（是 / 否） |
| 重启影响面 | {{RESTART_SCOPE}}（客户端热更新 / 宿主半 / 数据迁移） |

判定：期望 == 实际且退出码 0 → 运行时已生效；否则结论只能写「待用户试用」，并 `block --reason "等待重启 DSH" --owner user`，重启后重跑 `handshake`。**已安装 ≠ 已生效；`requires_restart` 时，未重启 + 握手通过前不得写「已上线可试用」。**

无运行时（`runtime: null`）时写「无运行时，不适用」，不留空、不编造版本号。

顺序：`handshake`（写 `R1-handshake.md`）→ 填完本节与报告 → `seal`。`seal` 之后不得再新增或修改任何证据或报告，否则 `verify` 报「封存后新增/改动文件」。

## 运行时实际加载版本

> 必须是运行时读到的值，不是文件 mtime、不是进程启动时间。

| 组件 | 读取方式 | 实际值 | 与候选一致 |
|---|---|---|---|
| {{COMPONENT}} | `Invoke-RestMethod {{HEALTH_URL}}` 的版本字段 | `{{LOADED_VERSION}}` | {{MATCH}} |
| 前端 | 浏览器回执 asset hash | `{{ASSET_HASH}}` | {{MATCH}} |
| 进程 | `Get-Process -Id {{PID}}` | 启动时间 {{PROCESS_START}} | {{MATCH}} |

## 核验结果

| 检查项 | 方法 | 结果 | 证据 |
|---|---|---|---|
| 页面入口可访问 | {{ENTRY_CHECK}} | {{RESULT}} | `evidence/{{CANDIDATE}}/V2-page.md` |
| 加载版本正确 | 运行时读取 | {{RESULT}} | `evidence/{{CANDIDATE}}/V1-health.json` |
| 进程运行正常 | `Get-Process -Id {{PID}}` | {{RESULT}} | 同上 |
| 必要接口可达 | `Invoke-RestMethod {{API_URL}}` | {{RESULT}} | 同上 |
| 原有数据可访问 | {{DATA_CHECK}} | {{RESULT}} | 同上 |
| 无新增异常日志 | {{LOG_PATH}} | {{RESULT}} | 同上 |

## 结论

> 门禁行：`tools/dsh_flow.py gate` 按行匹配，三态互斥，只写一个取值，不加前后缀。

结论：待用户试用

| 取值 | 何时可用 |
|---|---|
| 已上线可试用 | 必要检查通过，待用户试用清单已明确列出 |
| 待用户试用 | 已安装未上线，或阻断项未全部通过 |
| 完整业务验收通过 | 仅当用户已实际测完全部待验项且反馈已处理 |

❌ "基本完成"、❌ "应该没问题"、❌ 未说明待验项就说"功能已全部可用"。

## 待用户试用清单

> 与 `ACCEPTANCE.md` 第二节一致，逐条给步骤与观察点，用户能照着做。

| # | 操作步骤 | 观察重点 | 结果 |
|---|---|---|---|
| 1 | {{USER_STEPS}} | {{WATCH_FOR}} | ⏳ |
| 2 | {{USER_STEPS}} | {{WATCH_FOR}} | ⏳ |

## 回滚材料

| 项 | 内容 |
|---|---|
| 备份 | `{{BACKUP_DIR}}`（已验证可恢复） |
| 回滚命令 | `Copy-Item -Force -LiteralPath {{BACKUP_ARTIFACT}} -Destination {{TARGET_PATH}}`，再按精确 PID 重启 |
| 保留范围 | `{{PRESERVE_PATH}}`、在途任务原 ID 清单，旧备份不得覆盖 |
| 触发条件 | {{ROLLBACK_TRIGGER}}；效果类问题只记录不回滚 |

## 已知问题

| 问题 | 影响 | 规避 | 后续 |
|---|---|---|---|
| {{ISSUE}} | {{IMPACT}} | {{WORKAROUND}} | {{TRACKED_AS}} |

## 给执行线程的信息

| 类别 | 内容 |
|---|---|
| 需要你处理 | {{TODO_FOR_EXECUTOR}}（附证据路径） |
| 请你确认 | {{CONFIRM_ASK}} |
| 已排除 | {{RULED_OUT}} |

## 附录：manifest.json 字段契约

`manifest.json` 由 `$PY tools/dsh_flow.py freeze` 自动算出哈希并生成，**不要手填全部字段**；下表只约定键名与取值，键名不得自创。模板里的枚举与布尔取了合法默认值（`copy`/`source`/`B`/`pass`/`previous_candidate`/`ready`/`plugin`/`true`），替换时只能从右列取值中选。

| 字段 | 取值 | 说明 |
|---|---|---|
| `schema` | `dsh-flow/candidate@1` | 固定值 |
| `feature` / `project` | 功能名 / 项目根绝对路径 | |
| `candidate` | `C001` 起，不跳号不复用 | 与 `releases/` 目录同名 |
| `created_at` | ISO8601 带时区 | 冻结时刻 |
| `frozen_by` | `executor` | 只有执行线程能冻结 |
| `base.type` | `copy` / `direct` / `worktree` | 无 git 环境用 `copy`（`{{DEV_DIR}}` 副本） |
| `base.path` / `base.baseline_ref` | 开发副本路径 / `baseline.json` | 越界审计的对照物 |
| `artifacts[]` | `path`、`sha256`（64 位小写 hex）、`bytes`、`role`（`source`/`test`/`config`/`doc`/`asset`） | 必须覆盖所有将被安装的文件 |
| `install_order[]` | 安装顺序 | 逐项覆盖，顺序不可颠倒 |
| `restart_targets[]` | 服务/进程名；无重启填空数组 | 与 DEPLOYMENT-PLAN 第四节一致 |
| `runtime` | 对象或 `null` | 无运行时写 `null`；`freeze` 未带 `--runtime-kind` 时自动写 `null`；非 `null` 时四个子键都必填 |
| `runtime.kind` | `plugin` / `service` / `cli` / `none` | `plugin`=插件/能力包（宿主半 + 客户端半）；`service`=常驻服务；`cli`=命令行工具；`none` 与 `null` 同义。枚举只写在这里，不写进 JSON |
| `runtime.version` | 非空字符串，如 `0.4.1` | 握手期望值，必须等于包 `package.json` 的 `version` |
| `runtime.health_url` | `http(s)://...` | 健康检查地址，插件类形如 `http://127.0.0.1:<端口>/api/<短id>/health`；`cli` 可为空 |
| `runtime.requires_restart` | `true` / `false` | `true` 时重启 DSH 并通过握手才算生效 |
| `rollback` | `preserve[]`、`restore_from`（`previous_candidate`/`baseline`）、`steps[]` | 保留路径不得被旧备份覆盖 |
| `evidence[]` | `check_id`、`file`、`sha256`、`grade`（`A`/`B`/`C`/`D`）、`result`（`pass`/`fail`/`skip`）、`note` | 每条证据一个文件 |
| `checks.new[]` / `checks.reused[]` | 本候选新跑 / 引用旧候选（含 `check_id`、`from_candidate`、`reason`） | 引用必须写理由 |
| `gate` | `status`（`ready`/`blocked`）、`blocked_by[]` | 由门禁写入，不手改 |
| `seal_required` | `true` / `false` | `true` = 验证线程收口前必须 `seal`，生成 `releases/{{CANDIDATE}}/verification.json`；封存后改动会被 `verify` 查出 |

## 必填项清单

- [ ] 安装事实与 `manifest.json` 一致（文件数、哈希）
- [ ] 加载版本是运行时读取值
- [ ] 「运行时版本与重启」已填：健康检查地址、期望/实际版本、握手证据、是否重启、影响面（无运行时写不适用）
- [ ] `requires_restart` 为 true 时已重启并 `handshake` PASS，才写「已上线可试用」
- [ ] 「结论」行只有一个，取值在三态之内
- [ ] 「待用户试用清单」有操作步骤与观察重点
- [ ] 回滚材料可直接执行，保留范围已写明
- [ ] 给执行线程的信息有归属，不是空表
