// workflow/review-candidate.workflow.js
// 用途：对一个已冻结候选做「多角度独立复核」——每条检查一个只读子智能体，
//       结论再交叉复核一次，最后由 Lead 汇总。这是 DSH workflow 工具的原生用法。
//
// 怎么用（Lead）：
//   1) 先把本文件读出来，把下面整个 script 作为 workflow 工具的 script 参数；
//   2) args 里给出 project / feature / candidate / checks（checks 可从
//      docs/<feature>/planning/VALIDATION-WORKPLAN.md 的「## 检查项」里摘出来）；
//   3) 复核结果只作 Lead 判断的输入，**不要**据此直接改 state.json；
//      验证线程仍要自己写 RELEASE-REPORT.md 并跑 flow.py advance。
//
// 安全约束：所有子智能体都被要求「只读」，不得修改项目文件、不得安装、不得改 state.json。
// 但请记住：这是流程纪律而非沙箱强制（本机无 git、write_scopes 仅建议性），
//       所以复核结束后 Lead 仍要跑一次 flow.py audit。

phase('准备');
log(`候选复核：${args.candidate} / ${args.feature}`);

const base = `${args.project}/docs/${args.feature}`;
const checks = (args.checks || []).slice(0, 8);
if (checks.length === 0) return { error: 'args.checks 为空：先从 VALIDATION-WORKPLAN.md 摘出检查项' };
// 默认只对「非 pass」结论做交叉复核（省一半 agent）；要全量双人复核传 args.crossCheckPass=true。
const crossCheckPass = args.crossCheckPass === true;

const common = [
  `项目根：${args.project}`,
  `feature：${args.feature}`,
  `候选：${args.candidate}`,
  `候选冻结目录：${base}/releases/${args.candidate}/（只读：manifest.json、files/、RELEASE-REPORT.md）`,
  `证据目录：${base}/evidence/${args.candidate}/`,
  '硬约束：',
  '1) 只读。不要修改、创建、删除任何项目文件；不要安装任何东西；不要改 state.json。',
  '2) 证据优先：能跑命令就用命令原文 + 退出码；跑不了就明确写 insufficient，不要猜。',
  '3) 先读 manifest.json，核对你要检查的产物 sha256 是否与文件一致；不一致直接判 fail。',
  '4) 不要相信 RELEASE-REPORT.md 里的自述，只看你自己复现的结果。',
].join('\n');

const verifySchema = {
  type: 'object',
  additionalProperties: false,
  required: ['check_id', 'verdict', 'grade', 'commands', 'notes'],
  properties: {
    check_id: { type: 'string' },
    verdict: { type: 'string', enum: ['pass', 'fail', 'insufficient'] },
    grade: { type: 'string', enum: ['A', 'B', 'C', 'D'] },
    commands: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
    evidence_path: { type: 'string' },
  },
};

const checked = await pipeline(
  checks,
  async (check) => {
    phase(`核查 ${check.id}`);
    const prompt = [
      common,
      '',
      `你要独立核查这一条：${check.id} ${check.title}`,
      `判定标准：${check.criterion}`,
      check.evidence ? `执行线程声称的证据：${check.evidence}（必须自己复现，不许直接采信）` : '执行线程未提供证据 → 大概率 insufficient',
      '',
      '输出要求：verdict=pass 只在你有 A/B 级证据且通过时使用；证据不足用 insufficient；明确不满足用 fail。',
      'notes 写清「你跑了什么、看到什么、为什么这么判」，不要写空话。',
    ].join('\n');
    return await agent(prompt, { label: `${check.id} 核查`, phase: `核查 ${check.id}`, schema: verifySchema });
  },
  async (first, check) => {
    if (!first) return null;
    if (first.verdict === 'pass' && !crossCheckPass) {
      // 结论字段保持形状一致：cross_checked 永远存在（false 时写明为什么没复核）
      return {
        ...first,
        title: check.title,
        cross_checked: false,
        cross_check_reason: 'pass 不触发交叉复核；需要双人复核时传 args.crossCheckPass=true',
      };
    }
    phase(`交叉复核 ${check.id}`);
    const prompt = [
      common,
      '',
      `另一个核查者判定 ${check.id} 为「${first.verdict}」，理由：${first.notes}`,
      `请独立再判一次：${check.id} ${check.title}；判定标准：${check.criterion}`,
      '你可以不同意它。必须给出你自己的证据。',
    ].join('\n');
    const second = await agent(prompt, { label: `${check.id} 交叉复核`, phase: `交叉复核 ${check.id}`, schema: verifySchema });
    return {
      check_id: check.id,
      title: check.title,
      verdict: second ? second.verdict : first.verdict,
      cross_checked: true,
      first_verdict: first.verdict,
      second_verdict: second ? second.verdict : null,
      disagreement: second ? second.verdict !== first.verdict : false,
      notes: [first.notes, second ? second.notes : '(交叉复核失败)'].join(' | '),
    };
  }
);

const results = checked.filter(Boolean);
const failed = results.filter((r) => r.verdict !== 'pass');
const disagreed = results.filter((r) => r.disagreement);
const crossChecked = results.filter((r) => r.cross_checked);

phase('汇总');
log(`复核完成：${results.length} 项，非通过 ${failed.length} 项，交叉复核 ${crossChecked.length} 项，结论冲突 ${disagreed.length} 项`);

return {
  candidate: args.candidate,
  feature: args.feature,
  overall: failed.length === 0 ? 'candidate_ready' : 'candidate_blocked',
  failed,
  disagreed,
  cross_checked_count: crossChecked.length,
  results,
  next_step: failed.length === 0
    ? '交给验证线程写 RELEASE-REPORT.md，再由 Lead 跑 advance --to TRIAL'
    : '退回执行线程修复（不要改本候选；冻结新候选 C00X），把不通过项写进 EXECUTION-PLAN 的「发现未处理」',
};
