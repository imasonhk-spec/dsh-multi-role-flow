# workflow 多角度复核：实测记录

> 结论：`workflow/review-candidate.workflow.js` 这条**脚本化编排链**可用。
> 2026-11-18 对 `weekly-report` 的 `C007` 跑了两轮：① 4 条检查各 1 个只读子智能体（全 pass）；② 强制交叉复核路径（`crossCheckPass: true`，2 个 agent），交叉复核字段全部非空。
> 本轮还从两个独立复核者处收到 4 条真实问题，已记进 `weekly-report` 的 `EXECUTION-PLAN.md`「发现但不处理」。

---

## 1. 两轮运行

| 轮次 | args | agents | 结论 |
|---|---|---|---|
| ① 全量复核 | `checks=[V1,V3,V6,V8]`（默认 `crossCheckPass=false`） | 4 | 4/4 `pass`（V1/V3/V6/V8 均 A 级），无冲突 |
| ② 交叉复核路径 | `checks=[V8]`, `crossCheckPass=true` | 2 | `cross_checked=true`，`first_verdict=pass`、`second_verdict=pass`、`disagreement=false` |

第二轮的返回结构（节选）：

```json
{
  "candidate": "C007",
  "overall": "candidate_ready",
  "cross_checked_count": 1,
  "results": [{
    "check_id": "V8",
    "verdict": "pass",
    "cross_checked": true,
    "first_verdict": "pass",
    "second_verdict": "pass",
    "disagreement": false,
    "notes": "<两个独立复核者的完整理由，含命令原文>"
  }]
}
```

**结论字段永远存在**：pass 且未开 `crossCheckPass` 时 `cross_checked=false` + `cross_check_reason` 说明为什么不复核（省一半 agent），不会再出现「字段缺失」。

---

## 2. 复核者提交的 4 条真实问题（只读发现，未改代码）

| # | 发现 | 级别 | 影响 | 处理 |
|---|---|---|---|---|
| 1 | `cleanItemText` 只剥一层 Markdown 前缀：模型返回 `## 二级标题` 时正文变成 `2、# 二级标题`；`**加粗**` 残留 `*` | 体验 | 不影响 `validateReport`，行首无标记 | 记入「发现但不处理」，下一候选循环剥离 |
| 2 | `.wr-preview.wr-print-only` 是**死规则**：两个 class 在 `client.js` 里只出现在 CSS，无对应节点；6 条 `@media print` 规则实际 5 条生效 | 代码整洁 | 打印靠 `.wr-print-area` + `ReportView`，功能不受影响 | 清理死规则 |
| 3 | **编辑态点「打印为 PDF」会打出接近空白页**：`printPdf` 的 `disabled` 只看 `!draft`，而编辑态打印区全是 `.wr-draft{display:none}` / `.wr-noprint` | UX 缺陷 | 真实用户可能踩到；`smoke.mjs` 对 print/pdf 零断言 | 下一候选修 `disabled` 条件 + 补 smoke 断言 |
| 4 | `verification.json` 存在但 `manifest.seal_required` 缺失（C007 是旧候选）→ `verify` 不打印封存分支；另 `flow.py` 帮助文本仍写 `flow.py` 别名 | 文档/兼容 | 不影响校验（`verify` 仍跑了封存校验） | 旧候选补 `seal_required` 说明；帮助文案统一 |

> 第 3 条最值得修：它是**可复现的用户可见缺陷**，且现有 smoke 覆盖不到。

---

## 3. 怎么跑（Lead）

```text
workflow(
  meta = { name: "review-candidate", description: "候选多角度复核" },
  args = {
    project: "D:\\01-AI空间\\001-开发\\weekly-report",
    feature: "weekly-report",
    candidate: "C007",
    crossCheckPass: false,          # 需要全量双人复核时改 true（agent 数翻倍）
    checks: [ { id, title, criterion, evidence }, ... ]   # 从 VALIDATION-WORKPLAN 的「## 检查项」摘
  },
  script = <workflow/review-candidate.workflow.js 全文>
)
```

- `checks` 上限 8 条（`slice(0, 8)`）；每条 1 个 agent，非 pass 再 +1 个。
- 每个 agent 都是**只读**：只跑 `read` 与**白名单只读命令**，不写项目文件、不安装、不改 `state.json`。
- **不要给复核 agent 派 `Get-FileHash`，也不要派 `& $PY "…dsh_flow.py" …`**：会话一旦被 `$stop-that-shit review` 武装，这两类形态**必被拒**（`shell_command_unproven` / `shell_syntax_unproven`）。哈希核对改为两条合法路径：① 复核 agent 用 `read` 打开 `manifest.json` 与目标文件逐项比对（只读、无 shell）；② 由 **Lead 在非武装会话**跑 `flow.py verify --id <候选>`，把命令原文与退出码贴进结论。武装下的完整命令白名单见 `ops/aux-tools.md` 的「武装后哪些命令形态会被拒」一节。
- 复核结论**只作 Lead 判断输入**：仍要验证线程写 `RELEASE-REPORT.md` 并 `seal`，Lead 再 `advance`。
- 跑完 Lead 必须再跑一次 `flow.py audit`（纪律不是沙箱）。

---

## 4. 成本与边界

| 项 | 实测 |
|---|---|
| 单轮 agent 数 | 4 条检查 = 4 个（全 pass 时）；强制交叉复核 = 8 个 |
| 单轮耗时 | 约 2—4 分钟（本轮 4 条并行） |
| 局限 | 只读静态复现；未在真实浏览器点打印、未真机安装（这些仍归验证线程与用户试用） |
| 与 selftest 的关系 | selftest 只做脚本语法检查（`node --check` 包一层 async function）；语义正确性靠本记录 |

---

## 5. 自检清单

- [ ] `checks` 从 `VALIDATION-WORKPLAN.md` 抄，`criterion` 是可判断的（不是「体验好」）
- [ ] 每个 agent 都被告知「先核对 manifest 哈希，不一致直接 fail」——核对手段用 `read` 逐项比对（或 Lead 在非武装会话跑 `flow.py verify`），**不是** `Get-FileHash`
- [ ] 返回里 `results[].cross_checked` 字段存在；`disagreement` 与 `notes` 非空
- [ ] 复核发现的缺陷记进 `EXECUTION-PLAN.md` 的「发现但不处理」，不就地改冻结候选
- [ ] 复核后补跑 `flow.py audit`
