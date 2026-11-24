# 历史候选登记表（永久不可恢复的冻结包）

> **口径（写死，不接受例外）**：**冻结包 = `releases/<C>/files/` 的内容 + 冻结时逐文件 sha256**。
> 这两样在 2026-11-20 23:37 的误删事故后**已不存在任何副本**（源仓库、`-dev` 副本、`dsh-bundle*`、`%USERPROFILE%\.dsh\flow-snapshots` 异地快照、其他候选的 `files/` 都没有覆盖它们）。
> 因此本表**只登记、不补建**：据此重建 `manifest.json` 或 `files/` 等于**伪造冻结包**——任何角色不得执行，`freeze`/`seal`/`verify` 也不为这些候选补跑。
> 需要新结论时一律开新候选（`C00N+1`），不修改、不复活下表任何一行。

## 1. 登记表（A 类 10 条 + 未 seal 中间态 1 条）

| # | feature | 候选 | 缺什么 | 分类 | 不可恢复依据 | 现存证据路径 |
|---|---|---|---|---|---|---|
| 1 | `dev-toolchain-boost` | `C002` | `manifest.json` ✗、`files/` ✗（37 个产物）、`verification.json` ✗ | A 类：冻结包丢失 | 冻结包 = files 内容 + 逐文件 sha256，两者均已无副本；仅存的 `RELEASE-REPORT.md` 只记 manifest **文件级** sha256（`de308d55…ee93`），无法反推 artifacts 清单与文件内容 | `docs/dev-toolchain-boost/evidence/C002/`（12 个） |
| 2 | `flow-context-boost` | `C001` | `manifest.json` ✗、`files/` ✗、`verification.json` ✗ | A 类：冻结包丢失 | 同上；`releases/C001/` 只剩 `RELEASE-REPORT.md`，无条件副本 | `docs/flow-context-boost/evidence/C001/`（19 个） |
| 3 | `flow-context-boost` | `C002` | `manifest.json` ✗、`files/` ✗、`verification.json` ✗ | A 类：冻结包丢失 | 同上；无异地快照覆盖（`flow-snapshots` 机制晚于本候选建立） | `docs/flow-context-boost/evidence/C002/`（17 个） |
| 4 | `flow-context-boost` | `C003` | `manifest.json` ✗、`files/` ✗、`verification.json` ✗ | A 类：冻结包丢失 | 同上 | `docs/flow-context-boost/evidence/C003/`（21 个） |
| 5 | `flow-context-boost` | `C004` | `manifest.json` ✗、`files/` ✗、`verification.json` ✗ | A 类：冻结包丢失 | 同上 | `docs/flow-context-boost/evidence/C004/`（20 个） |
| 6 | `flow-hardening` | `C001` | `manifest.json` ✗、`files/` ✗、`verification.json` ✗ | A 类：冻结包丢失 | 同上 | `docs/flow-hardening/evidence/C001/`（11 个） |
| 7 | `flow-hardening` | `C002` | `manifest.json` ✗、`files/` ✗、`verification.json` ✗ | A 类：冻结包丢失 | 同上 | `docs/flow-hardening/evidence/C002/`（11 个） |
| 8 | `preset-resync` | `C001` | `manifest.json` ✗、`files/` ✗（43 个产物）、`verification.json` ✗ | A 类：冻结包丢失 | 同上；`RELEASE-REPORT.md` 记 manifest sha256 = `60d077c2…662b`、产物数 43，仅此可考 | `docs/preset-resync/evidence/C001/`（12 个） |
| 9 | `toolchain-fixups` | `C002` | `manifest.json` ✗、`files/` ✗、`verification.json` ✗ | A 类：冻结包丢失 | 同上 | `docs/toolchain-fixups/evidence/C002/`（11 个） |
| 10 | `toolchain-fixups` | `C003` | `manifest.json` ✗、`files/` ✗、`verification.json` ✗ | A 类：冻结包丢失 | 同上 | `docs/toolchain-fixups/evidence/C003/`（12 个） |
| 11 | `toolchain-fixups` | `C005` | `manifest.json` ✓、`files/` ✓（38 文件）、**`verification.json` ✗** | 未 seal 中间态（**不是丢失**） | 判据：`state.json` 记 `status=frozen`（`frozen_at` 08:44:11、`manifest_sha256` `f472d596…e5dd`、`artifacts` 38），**无 `sealed_at`/`verified_at`**；5 分 43 秒后（08:49:54）被 `C006` 取代；`history` 无 `drop` 记录，`archive/` 无同名副本（目录都不存在）。**登记为「未 seal 残留，不补建」**——不补 `verification.json`、不补 `seal` | `docs/toolchain-fixups/evidence/C005/`（20 个） |

> 说明：第 11 条不是事故损失，而是「冻结后未 seal 就被下一候选取代」的中间态；它的 `files/`+`manifest.json` 还在，缺的只是 `seal` 生成的 `verification.json`。**它同样不补建**——补 seal 会造出一份当时并不存在的凭证。

## 2. 现存证据文件清单（`Get-ChildItem -File` 实测）

- `docs/dev-toolchain-boost/evidence/C002/`：`V1.md`、`V2.md`、`V3.md`、`V4.md`、`V5.md`、`V6.md`、`V7.md`、`V8.md`、`V9.md`、`V10.md`、`V11.md`、`V12.md`
- `docs/flow-context-boost/evidence/C001/`：`P1-selftest.md`、`P2-gate-no-new-checks.md`、`P3-handoff-context-size.md`、`P4-init-graph-ignore.md`、`P5-lessons-key.md`、`V1-known-context.md`、`V2-not-hardcoded.md`、`V3-handoff-size.md`、`V4-roles-default-graph.md`、`V5-init-default-graph.md`、`V6-degrade-no-block.md`、`V7-lessons-loop.md`、`V8-gate-no-new-checks.md`、`V9-selftest.md`、`V10-zero-pollution.md`、`V11-affected-files.md`、`V12-template-sync.md`、`V13-memory-injection.md`、`V14-clean-graph.md`
- `docs/flow-context-boost/evidence/C002/`：`P1-selftest.md`、`P2-v7-lessons-order.md`、`P3-handoff-byte-cap.md`、`V1-known-context.md`、`V2-not-hardcoded.md`、`V3-handoff-size.md`、`V4-roles-default-graph.md`、`V5-init-default-graph.md`、`V6-degrade-no-block.md`、`V7-lessons-loop.md`、`V8-gate-no-new-checks.md`、`V9-selftest.md`、`V10-zero-pollution.md`、`V11-affected-files.md`、`V12-template-sync.md`、`V13-memory-injection.md`、`V14-clean-graph.md`
- `docs/flow-context-boost/evidence/C003/`：`P1-selftest.md`、`P2-g1-scope.md`、`P3-g2-reused.md`、`P4-g3-roles-mustkeep.md`、`V1-known-context.md`、`V2-not-hardcoded.md`、`V3-handoff-size.md`、`V4-roles-default-graph.md`、`V5-init-default-graph.md`、`V6-degrade-no-block.md`、`V7-lessons-loop.md`、`V8-gate-no-new-checks.md`、`V9-selftest.md`、`V10-zero-pollution.md`、`V11-affected-files.md`、`V12-template-sync.md`、`V13-memory-injection.md`、`V14-clean-graph.md`、`V15-scope-gitignore.md`、`V16-freeze-reused.md`、`V17-five-roles-must-keep.md`
- `docs/flow-context-boost/evidence/C004/`：`P1-selftest.md`、`P2-v17-control-chars-and-anchors.md`、`P3-lesson-l006.md`、`V1-known-context.md`、`V2-not-hardcoded.md`、`V3-handoff-size.md`、`V4-roles-default-graph.md`、`V5-init-default-graph.md`、`V6-degrade-no-block.md`、`V7-lessons-loop.md`、`V8-gate-no-new-checks.md`、`V9-selftest.md`、`V10-zero-pollution.md`、`V11-affected-files.md`、`V12-template-sync.md`、`V13-memory-injection.md`、`V14-clean-graph.md`、`V15-scope-gitignore.md`、`V16-freeze-reused.md`、`V17-five-roles-must-keep.md`
- `docs/flow-hardening/evidence/C001/`：`V1.md`、`V2.md`、`V3.md`、`V4.md`、`V5.md`、`V6.md`、`V7.md`、`V8.md`、`V9.md`、`V10.md`、`V11.md`
- `docs/flow-hardening/evidence/C002/`：`P7.md`、`P9.md`、`P10.md`、`V1.md`、`V2.md`、`V9.md`、`V10.md`、`V11.md`、`V12.md`、`V13.md`、`V14.md`
- `docs/preset-resync/evidence/C001/`：`V1.md`、`V2.md`、`V3.md`、`V3b.md`、`V4.md`、`V5.md`、`V6.md`、`V7.md`、`V8.md`、`V9.md`、`V10.md`、`V11.md`
- `docs/toolchain-fixups/evidence/C002/`：`V1.md`、`V2.md`、`V3.md`、`V4.md`、`V5.md`、`V6.md`、`V7.md`、`V8.md`、`V9.md`、`V10.md`、`V11.md`
- `docs/toolchain-fixups/evidence/C003/`：`P9.md`、`V1.md`、`V2.md`、`V3.md`、`V4.md`、`V5.md`、`V6.md`、`V7.md`、`V8.md`、`V9.md`、`V10.md`、`V11.md`
- `docs/toolchain-fixups/evidence/C005/`：`P1.md`、`P2.md`、`P3.md`、`P4.md`、`P5.md`、`P6.md`、`P7.md`、`P8.md`、`P9.md`、`V1.md`、`V2.md`、`V3.md`、`V4.md`、`V5.md`、`V6.md`、`V7.md`、`V8.md`、`V9.md`、`V10.md`、`V11.md`

## 3. 不补建：具体禁止动作

1. **不得**据 `RELEASE-REPORT.md`、`evidence/*` 里出现的哈希片段重建 `manifest.json`——那只是「曾经存在过某个 manifest」的旁证，不是冻结时的逐文件清单。
2. **不得**把当前源码或现存 `files/`（别的候选）复制进这些 `releases/<C>/` 充当原冻结内容。
3. **不得**为这些候选跑 `seal` / `verify` / `evidence --check`，也不得在 `state.json` 里给它们补 `sealed_at`/`verified_at`。
4. 需要引用历史结论时，**只引用现存 evidence 文件原文**，并注明「冻结包已永久不可恢复，本结论无法用哈希复核」。
5. 新验证一律开新候选；本表只增行不改行——若将来又发现同类残件，按第 11 条那种「缺什么 / 分类 / 依据 / 现存证据」四列补登记。

## 4. 事实来源与复核方式

| 事实 | 依据 |
|---|---|
| 事故时间与形态 | 2026-11-20 23:37 一条 cmd 命令从 D 盘根递归删除（`ops/lessons.md` L009） |
| 10 个 A 类候选的 `releases/<C>/` 只剩 `RELEASE-REPORT.md` | `Get-ChildItem docs/<feature>/releases/<C>` 逐条实测；`Test-Path manifest.json` / `files/` / `verification.json` 全为 `False` |
| 第 11 条未 seal | `docs/toolchain-fixups/state.json` 的 `candidates.C005`（`status=frozen`，无 `sealed_at`/`verified_at`）、`history` 无 `drop`、`archive/` 目录不存在 |
| 证据文件清单与条数 | `Get-ChildItem docs/<feature>/evidence/<C> -File` 实测（本文件第 2 节，逐文件名列出） |

**复核命令（只读，可复跑）**：

```powershell
$env:PYTHONIOENCODING='utf-8'
foreach ($p in @(@('dev-toolchain-boost','C002'), @('flow-context-boost','C001'), @('flow-context-boost','C002'), @('flow-context-boost','C003'), @('flow-context-boost','C004'), @('flow-hardening','C001'), @('flow-hardening','C002'), @('preset-resync','C001'), @('toolchain-fixups','C002'), @('toolchain-fixups','C003'), @('toolchain-fixups','C005'))) {
  $d = "docs/$($p[0])/releases/$($p[1])"
  "{0}/{1}: manifest={2} files={3} verification={4} 证据={5} 个" -f $p[0], $p[1], (Test-Path "$d/manifest.json"), (Test-Path "$d/files"), (Test-Path "$d/verification.json"), (Get-ChildItem "docs/$($p[0])/evidence/$($p[1])" -File).Count
}
```
