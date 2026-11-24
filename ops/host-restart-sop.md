# 宿主重启 SOP（插件 / 能力包 / 服务类）

> 适用：**验证线程**与 **Lead**。触发条件：装完候选后行为没变、`handshake` FAIL、或版本对不上。
> 一句话：**先判断是「没装上」还是「没重启」，再请用户重启；重启后必须重新握手，PASS 才能写「已上线」。**

环境常量：

```powershell
$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$FLOW = "<flow-home>\tools\dsh_flow.py"
```

---

## 0. 先判断：是「没装上」还是「没重启」

| 现象 | 判定 | 下一步 |
|---|---|---|
| `handshake` HTTP 200，`version` 与 `manifest.runtime.version` 相等 | 已生效 | 不重启，直接 `seal` |
| `handshake` HTTP 200，但 `version` 是**旧版号** | 宿主半仍是旧模块（ESM 不热替换） | 走本 SOP 第 1—3 节 |
| `handshake` 连接失败 / 404 / 500 | 包没装上，或 `/health` 路由没注册 | 查安装与路由，**不要**靠重启碰运气 |
| 版本相同但行为不同 | 不是重启问题（代码/缓存/数据） | 记录现象，按 P1 排查或出新候选 |

**「新版是否在跑」只认握手**：不认安装回执、进程启动时间、文件 mtime、页面缓存。

---

## 1. 重启前必须落盘的三件事（缺一件不许请用户动手）

1. **证据**：`handshake` 已把失败原因写进 `docs/<feature>/evidence/<C>/R1-handshake.md`（`结果：fail` + 实际版本 + HTTP 状态）。没有就补跑一次。
2. **阻塞标记**：`$PY $FLOW block -p <项目根> -f <feature> --reason "等待重启 DSH 以加载宿主半" --owner user --kind env`
   —— 用 `block` 记录「在等用户」，而不是靠出新候选推进。
3. **备份**：把将被替换的组件复制到 `<项目根>-backup/<yyyyMMdd-HHmmss>/`，哈希与 `baseline.json` 一致；路径写进 `DEPLOYMENT-PLAN.md` 的备份列。

然后给用户三句话（**只说这三句**）：为什么重启、要重启什么、重启后你做什么。

---

## 2. 谁来重启：只有用户

- **禁止**：`Stop-Process -Name python` / `taskkill /IM node.exe` / 杀 DSH 的 Electron 子进程。DSH 会话进程被杀会丢在途回合。
- **正确**：关闭 DSH 窗口（或托盘退出）→ 重新打开 → 会话从 `state.json` 恢复，磁盘产物不重做。
- 重启后先 `list_agents` 看子智能体还在不在：**不在就 `next` 重派同一交接包**（不要重做产物，不要让新子智能体「猜上次做到哪」）。
- 用户重启期间，Lead 可以在新会话里 `status --json` 确认 `phase`、`current_candidate` 未变；变了要解释来源（谁改的、为什么）。

---

## 3. 重启后四步（顺序不能换）

```powershell
# 1) 状态没漂移
& $PY $FLOW status --json -p <项目根> -f <feature>

# 2) 重新握手（PASS 才算加载了新版）
& $PY $FLOW handshake -p <项目根> -f <feature> --id C00N --expect <manifest.runtime.version> --url <健康检查地址>

# 3) 失败：不要连开新候选，先判断
#    - 实际版本仍是旧版 → 宿主半没重载：确认 package.json version 是否改过（见第 4 节）
#    - 404/500 → 路由没注册：查 index.js 与 cordis.patch.yml
# 4) PASS：更新部署台账 → 再封存
& $PY $FLOW unblock -p <项目根> -f <feature> --note "用户已重启，握手通过"
```

PASS 之后还必须：
- 把「运行时实际加载版本」写进 `DEPLOYMENT-PLAN.md`（**运行时读到的值**，不是文件 mtime）；
- 确认 `RELEASE-REPORT.md` 的结论三态与握手结果一致；
- 再 `seal --id C00N`（`gate TRIAL` 要求封存），然后由 Lead `advance`。

---

## 4. 「版本没变但代码变了」——最常见的假重启

宿主半是 ESM，**同版本号重装不会触发重载**，重启也未必换模块。判定与处理：

| 情况 | 处理 |
|---|---|
| `package.json` 的 `version` 没改 | 要么改版本（出 `C00N+1` 候选，走完整冻结），要么重启 DSH 清模块缓存 |
| 改了版本但没重装 | 重新 `install_bundle`（`releases/C00N/files/pack`）再重启 |
| 前端资源没变 | 看 asset hash / 页面回执，不能只看 `index.js` |

**禁止**用「连续冻结 C001→C002→C003」试错：这会让「哪个版本真的在跑」彻底不可考。

---

## 5. 反例（都是真实踩过的）

- ❌ 靠出新候选掩盖旧宿主：报告写「已修复」，实际跑的还是旧版。
- ❌ 用 `plugin_manager` 禁用再启用当重载：宿主半不热替换（实测）。
- ❌ 用文件 mtime / 进程启动时间证明生效：都不是运行时版本。
- ❌ 杀 `python.exe` 全体：会带走 DSH 的运行时与其他会话。
- ❌ 用户在重启，Lead 同时 `advance`：状态与磁盘会错位。

---

## 6. 一次完整的证据链（照抄）

```
handshake FAIL            → evidence/C00N/R1-handshake.md（result=fail，实际版本=旧版）
block --owner user        → state.blocked = {owner:user, reason:"等待重启 DSH"}
用户重启 DSH
list_agents / status      → 候选与阶段未变
handshake PASS            → R1 被覆盖为 result=pass；state.candidates.C00N.runtime.ok=true
unblock                   → 解除阻塞，台账留一条
DEPLOYMENT-PLAN           → 「运行时实际加载版本」= 期望版本
seal --id C00N            → verification.json（V*/报告/部署台账哈希）
gate TRIAL → advance      → 进入用户试用
```

---

## 7. 与其它角色的接口

| 角色 | 在这件事里做什么 |
|---|---|
| 用户 | **只有他能重启**；确认窗口与回执 |
| Lead | 批准重启窗口、发那三句话、重启后 `next` 重派、`advance` |
| 验证线程 | 执行第 1、3 节；写 R1 与部署台账；收口前 `seal` |
| 执行线程 | 不碰宿主；只交候选与证据；版本号改动由它出 `C00N+1` |

---

## 8. 自检清单

- [ ] 已区分「没装上」与「没重启」（第 0 节）
- [ ] `R1-handshake.md` 落盘且 `结果：fail` 时写清实际版本
- [ ] `block --owner user` 已记，没有靠新候选推进
- [ ] 重启只作用于 DSH 本身，没杀 python/node 全体
- [ ] 重启后 `handshake` 退出码 0，实际版本 = `manifest.runtime.version`
- [ ] `DEPLOYMENT-PLAN.md` 的「运行时实际加载版本」是运行时读到的值
- [ ] 已 `seal`，`gate TRIAL` 通过后才 `advance`
- [ ] 全程没有用 mtime / 安装回执 / 页面缓存当证据
