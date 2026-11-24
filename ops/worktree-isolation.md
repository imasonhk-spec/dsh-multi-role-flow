# 工作树隔离：开法与实测结论

> 结论：**原生 `create_worktree` 已实测可用**（2026-11-18）。本机 git 2.56.1 + node 24.21.0 都在 DSH 进程 PATH 里，DSH 也已重启。
> 用途：给执行线程一个**物理上独立**的代码副本，让「改代码的人」与「验证的人」不共享同一个工作目录。
> 与 `-dev` 副本、原生 `create_worktree` 的关系见第 2 节选择表。注意：本流程包**不提供** `worktree` 子命令（`dsh_flow.py` 的 24 个子命令里没有它；计数以 `& $PY tools\dsh_flow.py --help` 的 choices 为准，2026-11-21 实测 24），CLI 级建树直接用 `git worktree add`，或走 `<项目根>-dev` 副本 + `baseline`/`freeze` 的 sha256 差集。

---

## 1. 实测记录（2026-11-18 16:10）

| 步骤 | 命令 / 调用 | 结果 |
|---|---|---|
| 建仓库 | `git init -b main` + 一次提交 `5f30faa init` | 正常 |
| **原生工具** | `create_worktree(name="wt-probe", from="main")` | 返回 `{"path":"...\\dsh-wt-test\\.agents\\worktrees\\wt-probe","branch":"wt-probe","baseCommit":"5f30faa…","repositoryRoot":"…\\dsh-wt-test"}` |
| 会话目录 | 调用后 `Get-Location` | `…\dsh-wt-test` → `…\dsh-wt-test\.agents\worktrees\wt-probe`（**会话 cwd 被切换**） |
| 分支 | 工作树内 `git branch --show-current`；原目录 | `wt-probe`；原目录仍是 `main` |
| 提交 | 工作树内新建 `wt-probe.txt` → `git add` → `git commit` | `[wt-probe 5e7bb3a] wt probe / 1 file changed`；原目录 `git log` 仍是 `5f30faa`，主目录无该文件、`status` 干净 |
| 忽略 | `git check-ignore -v .agents/worktrees/wt-probe` | 命中 `.agents/worktrees/.gitignore:1:*` → 工作树目录**不进主仓库版本库** |
| 工作树列表 | `git worktree list` | 两条：主工作树 `[main]` + `.agents/worktrees/wt-probe [wt-probe]` |

**Lead 独立复核**：`worktree list`、分支、`wt-probe.txt` 内容（`ok`）、主目录无该文件、`.gitignore` 命中——全部一致。子智能体回报与磁盘事实相符。

---

## 2. 两种隔离方式，怎么选

| 方式 | 目录 / 分支 | 前置条件 | 适用 |
|---|---|---|---|
| **① 原生 `create_worktree`** | `<仓库>/.agents/worktrees/<name>`，分支 `<name>` | git + node 在 PATH；**会切换调用者会话 cwd** | 执行线程是子智能体时首选（它切自己的 cwd，不影响 Lead） |
| **② `<项目根>-dev` 副本 + 哈希** | 兄弟目录 | 无 | 项目不是 git 仓库、或不允许建分支 |

> 只想用 `git` 手工开树时，直接用 `git worktree add <路径> -b <分支>`（本流程包不提供 `worktree` 子命令包装）。

三者都满足同一条底线：**候选真相以 `releases/<C>/files/` 的 sha256 为准**，工作树/commit 只是旁证。

---

## 3. 原生工具的使用约定（踩坑清单）

1. **它会切你的 cwd**：调用后所有相对路径都指向工作树。Lead 用完后要 `working_directory(cd=<项目根>)` 回去；子智能体的 cwd 变化只影响它自己。
2. **名字唯一**：同一仓库并发开树时用 `<角色>-<seq>`（如 `exec-001`），重名会失败。
3. **不要把工作树塞进候选**：`freeze --from <工作树路径>` 只取 `scope` 里的文件；`freeze` 的排除列表已含 `docs/`、`releases/`、`evidence/`、`handoffs/`、`.git/`。
4. **清理**（在仓库内执行，先确认没人在里面）：
   ```powershell
   git worktree remove .agents/worktrees/wt-probe --force
   git branch -D wt-probe
   ```
   有未提交改动时 `--force` 会丢改动；执行线程的批次没冻结前不要删。
5. **`.agents/` 已被 `audit` 跳过**（`SKIP_DIR_NAMES` 含 `.agents`），不会污染越界审计；但**不要**把业务文件写进 `.agents/`。
6. 验证线程**只读** `releases/<C>/files/`，**不进**工作树——否则「独立见证」失效。

---

## 4. 与状态机的配合

```
EXECUTING 起批次
  → Lead 开工作树（① 或 ②）
  → subagent(cwd=<工作树>)，执行线程只在里面改
  → 批次内 git add/commit（可选，给审计留旁证）
  → flow.py freeze --from <工作树> --scope <声明范围> → C00N
  → Lead verify + audit（audit 跳过 .agents/ 与 -wt/）
  → advance --to VERIFYING（验证线程只读冻结包）
```

**失败回退**：工作树里改坏了 → 直接从主仓库重新开一棵，**不要**在工作树里 `git reset --hard` 掩盖（会丢证据）。要保留这次尝试就先把改动 `git stash` 或提交到临时分支，再开新树。

---

## 5. 自检清单

- [ ] `flow.py doctor` 显示 git 与 node 都在 PATH
- [ ] `git worktree list` 能看到主工作树与你开的树，分支名符合约定
- [ ] 工作树目录在 `.agents/worktrees/`（①）或 `<仓库>-wt/`（②），**不在** `docs/` 里
- [ ] 主仓库 `git status` 干净（工作树内容未混进主仓库）
- [ ] `freeze --from <工作树>` 的 `manifest.artifacts` 只含声明范围
- [ ] 清理工作树前已确认没有未冻结的改动
