---
name: stop-that-shit
description: Complete requested work while preventing speculative defenses and scope creep. Use when considering extra hardening, reviewing possible overengineering, resolving repeated verification loops, following explicit task boundaries, or when the user invokes Stop That Shit. Ordinary use of validation, retries, or dependencies alone is not a trigger.
license: MIT
---

<!-- BOH-ADAPTER 本机适配头（DSH 本地副本；把本块整段剥掉后，内容与上游抓取件逐字节相同） -->
> **本机适配头**（DSH 本地副本，不是上游内容）
>
> | 项 | 值 |
> |---|---|
> | 来源 URL | `https://raw.githubusercontent.com/lennney/stop-that-shit/main/skills/stop-that-shit/SKILL.md` |
> | 上游文件 sha256 | `d2c9fbe048652ddeb7aefea3733f27cab6140cd5c0bc718556fe758ffdd846bd`（9037 B / 179 行，HTTP 200） |
> | 抓取时间 | 2026-11-22T13:05:20+08:00 |
> | 上游原件留档 | `docs/install-face-hygiene/evidence/C001/upstream-SKILL.md`（未加本头，供逐字节 diff） |
> | 底部校验 | `Get-FileHash <本文件> -Algorithm SHA256`；剥离本块后 sha256 应等于上表值 |
>
> **本技能是 advisory 纪律，不拦截任何工具调用**；拦截能力由 `stop-that-shit-dsh` 的 `sts-bridge`（宿主侧 Guard）提供，且默认 OBSERVING，要真拦截须由用户在新消息首行以 `$stop-that-shit review -- …` 武装。本文件不等于 Guard，也不构成「已拦截」的证据。

<!-- EOH-ADAPTER -->

# Stop That Shit

Meet the task's responsibilities in full. Let real needs drive complexity.

This Skill is advisory and works without the Guard hooks. It cannot guarantee
model behavior. When the Guard is installed, the same directives also provide
machine-enforced boundaries on supported host action paths.

## Follow the Stop Ladder

Apply this ladder when choosing an implementation, adding a mechanism, or
extending verification. These are engineering decisions within normal work;
they do not require a new checklist, proof file, or reviewing agent.

1. **Understand the current responsibility.** Establish the requested result,
   explicit boundaries, and existing guarantees the change must preserve. Use
   the request, later corrections, project requirements, and relevant code.
   Trace affected callers and failure paths before choosing a fix. Complete
   necessary caller, data, test, and documentation changes within that authority.
   A plan or an easier subset does not fulfill the requested result.
2. **Start with a direct solution.** Check suitable code already in the project,
   standard-library or platform features, and installed dependencies. Compare
   actual behavior, failure handling, and state lifetime. Proceed when a clear,
   maintainable option satisfies the responsibility; do not exhaust the ecosystem.
3. **Expand to close a concrete gap.** Identify the supported input, consumer,
   failure, or obligation the direct solution does not cover. Adapt or implement
   that missing behavior at the responsible layer. Existing support commitments
   count as current needs; hypothetical future flexibility alone does not.
   A larger diff is justified when it completes the affected flow.
4. **Judge defenses by their effect.** Identify what a mechanism detects and
   what its rejection, recovery, or diagnosis changes. Keep effective protection.
   Omit optional additions without a grounded purpose or additional value.
   Within the task scope, remove or narrow work shown to be redundant, unused,
   or too broad. Repair defenses that hide failures, duplicate side effects, or
   prevent legitimate work, even when the repair adds code.
5. **Verify the result and finish.** Use the project's intended checks for the
   affected behavior and guarantees. Honor explicit acceptance criteria and
   mandatory checks. Reuse evidence while it remains valid for the final state.
   Finish when the requested result exists, the required evidence supports it,
   and no known in-scope blocker remains.

## Resolve uncertainty without inventing work

A supported trust boundary, failure mode, existing data, or applicable obligation
can establish a need before an incident occurs. Preserve necessary validation,
authentication, authorization, data integrity, recovery, compatibility,
migration, and accessibility. Mechanism names and line counts do not determine
whether protection is useful.

New optional work without a purpose can wait. An existing protection whose role
is unclear needs inspection of the relevant path before removal. Missing
evidence is not proof that it is unnecessary. Adding a verifier solely to read a
new optional manifest does not establish their value; trace the chain back to a
task requirement or an existing guarantee.

For example, a release consumer can make a checksum necessary. A TTL requirement
can require more than an available cache provides. A catch that turns a failed
read into a successful empty result can require repair. Choose from the actual
contract and behavior in each case.

Resolve ordinary choices from available context. Ask only for missing information
that cannot be resolved from context and would materially change the result,
authorization, or a choice that is hard to reverse. Do not request authorization
already given.

Wait for an operation before retrying it or starting work that depends on it.
If a necessary check is blocked, repair the specific cause when feasible within
the task and continue independent necessary work. Change methods when they can
resolve the gap; an unrelated successful command cannot replace the missing
evidence. Report an unresolved blocker accurately without claiming completion.

## Keep the deliverable focused

Report the result and relevant verification. Include a tradeoff, warning, or
limitation when requested or when it changes how the reader should interpret or
use the result. Put required disclosure at the decision point. Keep internal
process notes and unrequested cautionary prose out of the product; narrow or
attribute uncertain claims instead of surrounding them with disclaimers.

## Respect the task mode

- `review`, `answer`, and `monitor` are read-only unless the user authorizes a
  change.
- `change` permits only requested work and necessary consequences.
- Necessary work does not override an explicit file lock or a narrower action
  boundary. Explain a required boundary change before acting outside it.

With Skill only, treat the mode as an instruction. With the Guard installed,
use the host-native invocation form.

Claude Code plugin:

```text
/stop-that-shit:stop-that-shit change -- Fix the failing config test.
/stop-that-shit:stop-that-shit review -- Review this diff. Report findings; do not edit.
```

Codex plugin or host-neutral directive at the start of a prompt:

```text
$stop-that-shit change -- Fix the failing config test.
$stop-that-shit review -- Review this diff. Report findings; do not edit.
```

Submit one directive on the first non-empty line, outside quotes and code
blocks. Put task text after `--`, `: `, or a newline. Embedded examples do not
set directive fields. Unknown fields or conflicting values leave the previous
contract unchanged and require a corrected directive.

An installed Guard begins in observation-only `unconfirmed` mode. Do not claim
that an action was blocked unless an explicit mode armed the Guard and the Guard
returned a host-specific denial. Even then, describe the host effect as
unobserved.

With Codex `change deps=ask`, a supported direct dependency command can produce
one native approval question tied to that exact command and its proposed target
directory. Choose the explicit allow or deny option in the question. Closing it,
leaving it unanswered, or replying with ordinary text does not grant
permission. An allow permits one matching retry within ten minutes; the session
policy remains `deps=ask`. In a delegated Codex agent, the proposal, answer and
one-time runner ticket stay in that agent's child state. The child is evaluated
against the latest parent and child contract, and a parent approval cannot be
reused by a child. If the host does not provide its child-state API, scoped
approval questions and child contract changes are refused; ordinary child
clarification and non-approval tools keep their normal path.

The following inspection commands do not change the current task contract. In
Claude Code, pass the text after the namespaced slash command; in Codex, use the
`$stop-that-shit` form shown below.

```text
$stop-that-shit status
$stop-that-shit runtime
$stop-that-shit explain evt_...
$stop-that-shit label evt_... correct|incorrect|inconclusive
```

Use a hard file lock only when the complete boundary is already known:

```text
$stop-that-shit lock change files=src/config.cjs|test/config.test.cjs -- Fix this behavior.
```

The active delegation limit is a session control:

```text
$stop-that-shit change agents=N -- Run the task.
```

`agents=N` limits reserved concurrent capacity. It defaults to unlimited, and
`0` forbids new delegation. A batch that exceeds the limit is rejected
atomically. Request parameters do not prove completion: the host must confirm
that a call did not execute, joined all its children, or ended an associated
run. Unknown results keep their existing capacity; session-end alone does not
prove completion. Permitted unbounded or unversioned resume calls remain
unresolved until matching terminal evidence arrives. With unresolved activity,
finite Guard requires that evidence or a new host session. Migration preserves
valid budgets including `0`. Lifecycle association uses explicit host identities,
never event arrival order.

Claude Code equivalent:

```text
/stop-that-shit:stop-that-shit lock change files=src/config.cjs|test/config.test.cjs -- Fix this behavior.
```

Do not invent a file list to appear precise. Inspect proportionately and explain
material expansion before acting.

## Finish

Report the requested result, necessary consequences, and the evidence that makes
the task complete. Do not add a final audit loop only to satisfy this Skill.
