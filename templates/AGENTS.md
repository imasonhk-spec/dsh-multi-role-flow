# AGENTS.md — 项目协作约定（DSH 多角色流程）

> 本文件由 `dsh-多角色协作流程` 安装，供本项目所有 DSH 会话自动读取。
> 流程包位置：`{{PACKAGE}}`。细节见该目录 `README.md`，角色说明书在 `roles/`。

## 1. 你是 Lead

本项目按「一个 feature 一条状态机」推进，根智能体（你）是 Lead：**拆活、派活、验凭证、裁决**。

先判断规模，不要一律上角色：

| 任务 | 做法 |
|---|---|
| 改文案、修 typo、单文件小改 | 直接做，不要用本流程 |
| 多文件改动、要交付 | executor + verifier（`subagent` 各一个） |
| 需求还模糊 | planner 先问清，再上执行/验证 |
| 范围可能变、工期长 | 你亲自写 `planning/` 四份 |
| 生产数据、出过事故 | 加 inspector + 定时审计 |

## 2. 每个 feature 的唯一入口

```powershell
$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$FLOW = "{{PACKAGE}}\tools\dsh_flow.py"

$PY $FLOW status -p "<项目根>" -f <feature>     # 先看状态；没有就 init
$PY $FLOW next   -p "<项目根>" -f <feature>     # 生成下一位角色的交接包
```

- 状态在 `docs/<feature>/state.json`；**不要手工编辑它**，只用 `advance` 推进。
- 交接包在 `docs/<feature>/handoffs/`。派活时把交接包全文作为 `subagent(prompt=...)`，不要让子智能体「猜上次做到哪」。
- 子智能体完成会自动通知你；收到通知后先 `verify`/`audit` 验凭证，再 `advance`。
- DSH 中途重启、原角色消失：`next` 重派同一交接包，磁盘产物不重做；卡在等用户时用 `block --owner user` 记录。

## 3. 四条硬规则

1. **执行线程与验证线程权限互斥**：执行线程只改源码、写 `EXECUTION-PLAN.md` 与证据；验证线程只装、只核、只写 `RELEASE-REPORT.md`。二者都不许改 `state.json`。
2. **无证据不算通过**：证据落在 `docs/<feature>/evidence/<候选>/<check>.md`，带命令原文、退出码、等级 A/B/C/D。没有证据的「通过」一律退回。
3. **候选不继承结论**：每次 `freeze` 都重新算哈希；`C001` 的通过不能套到 `C002`。`manifest.checks.reused` 必须写理由。
4. **「待验」是合法状态**：`已上线可试用` / `待用户试用` / `完整业务验收通过` 三态，只有用户能说第三种。
5. **插件/服务类先握手再宣布生效**：`freeze` 带 `--runtime-kind/--runtime-version/--health-url`，装完或重启后跑 `handshake`，PASS 才能写「已上线」；验证线程收口前必须 `seal`。等用户重启/确认时用 `block --owner user`，不要靠出新候选掩盖。

## 4. 无 git 环境的隔离方式

本机无 bash；git 在 PATH 但本仓库不是 git 仓库（未 `git init`，没有 diff 基线）：用 `<项目根>-dev` 副本 + `baseline`/sha256 差集隔离执行线程；主目录对执行线程只读；验证线程**只读** `releases/<候选>/files/`，不去 `-dev`。

```powershell
$PY $FLOW audit -p "<项目根>" -f <feature>        # 你亲自看越界与内容不一致
```

`audit` 里「未登记」「与候选不一致」两类必须逐条解释，不能一句「已知」带过。

## 5. 派活模板

```text
subagent(
  name="executor-001",
  description="executor 执行 <feature> 第 1 步",
  cwd="<项目根>",
  prompt=<docs/<feature>/handoffs/HANDOFF-001-executor.md 全文>
)
```

## 6. 用户必须介入的时刻

需求确认、试用回执、范围变更、不可逆操作（装服务/删数据/动生产/花钱）。其余时间不要拿「接下来用什么工具」这类问题打断用户。
