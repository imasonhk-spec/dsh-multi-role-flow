# Issue 草稿 — dsh-mnemon Documents 持久化位置与 `~/.mnemon/documents/index.json` 不一致

> **状态**：待提交给上游（`omdsh-dev/dsh-mnemon`）。本文件只做取证与复现整理，**未**修改任何 mnemon 数据。
> **取证时间**：2026-11-22 01:14–01:20（Asia/Shanghai）
> **取证者**：DSH Lead（多角色协作流程会话 `session-a2da8277`）

## 环境

| 项 | 值 |
|---|---|
| OS | Windows 11 build 10.0.22631 |
| DSH | `0.2.2-rc.5` |
| Node | `v24.21.0` |
| `dsh-mnemon` | **0.5.50** |
| `dsh-mnemon-source-documents` | **0.6.3** |
| `dsh-mnemon-source-memory-spaces` | **0.5.31** |
| Mnemon CLI | `0.2.14`（`D:\Tools\mnemon\mnemon.exe`） |
| profile | `desktop` |
| 会话 cwd / workspace | `<workspace>` |

## 现象：三组互相矛盾的观察

### 观察 1 — 写入报成功，且计数递增

```
mnemon_document_create(title="探针-2201-Documents闭环验证", content="…zebra-quasar-2201…")
→ success: true
  document.id = 2f793cf1-094c-4fd9-bdd4-edb6c038de98
  document.sizeBytes = 658
  documents: { active: 3, archived: 0, activeBytes: 9449, limitBytes: 10485760 }
```

（此前一次同类调用把 `documents.active` 从 1 变成 2，本次从 2 变成 3。）

### 观察 2 — 检索能命中（跨 DSH 重启）

```
mnemon_document_search(query="代码图谱使用契约 graphify GitNexus")
→ total: 1
  results[0].id = e5b1e7c4-5284-4fe4-8c28-32db99ea33c1
  results[0].relativePath = "documents/active/code-graph-e5b1e7c4.md"
  results[0].score = 30
```

`e5b1e7c4` 创建于 **2026-11-21 08:45**，而当前 DSH 进程启动于 **2026-11-21 19:25:40** —— 即**文档跨进程重启仍然存在**，说明数据是持久化的。

### 观察 3 — 但磁盘上的「文档目录」恒为空

```
~/.mnemon\documents\index.json
  38 B   2026-11-19 21:48:44（此后从未更新）
  内容：{ "version": 1, "documents": [] }

~/.mnemon\documents\active\      → 0 项
~/.mnemon\documents\archived\    → 0 项

~/.mnemon\data\default\mnemon.db → 94208 B  2026-11-20 02:39:41（此后从未更新）
```

全盘搜索 `.mnemon` 目录，**只存在 `~/.mnemon` 一个**；`<workspaceRoot>\.mnemon`（`shards` 默认值 `join(workspaceRoot, ".mnemon")`）**不存在**。全盘搜索 `code-graph-e5b1e7c4.md` 与 `2f793cf1` 的文件名也**未命中**。

## 矛盾点

| 问题 | 事实 |
|---|---|
| 数据到底存在哪？ | 能读写、能跨重启存活，但 `documents/index.json` 与 `active/` 目录都不反映它 |
| `index.json` 是不是死文件？ | 若是，为何仍会被创建并保留 38 B 的 `{"documents":[]}` 结构？若否，为何写入不更新它 |
| `mnemon status` 与 MCP 计数为何不一致 | CLI `mnemon status` 报 `total_insights: 0`、`edge_count: 0`；MCP `mnemon_status` 报 `totalInsights: 2`、`edgeCount: 4`（同一时刻，`db_size_bytes` 都是 94208） |

## 影响

1. **排障误导**：按「Documents 存储在哪」去看 `~/.mnemon/documents/`，会得出「文档没落盘、检索不可用」的错误结论。本项目此前据此把该能力判为 fail（`toolchain-fixups` 的 P2），直到 11-22 复测才发现检索其实可用。
2. **备份/迁移风险**：若用户按 `~/.mnemon/` 做备份，可能**漏掉真实文档数据**（它不在这个目录树里）。
3. **CLI 与 MCP 口径不一致**：`mnemon status` 无法反映 DSH 侧实际拥有的记忆量，用户用 CLI 自查会以为「什么都没有」。

## 建议上游确认的问题

1. `dsh-mnemon-source-documents@0.6.3` 的 `storageRoot` 在 DSH 宿主里的**实际取值**是什么？是否有与 `~/.mnemon` 不同的默认路径（例如落在 DSH profile 或 `storages/` 下）？
2. `documents/index.json` 在当前版本是否**已废弃**？若已废弃，建议启动时删除或写入带 `"deprecated": true` 的说明，避免误导。
3. `mnemon status` 是否应该读 DSH 侧同一份 store？若刻意分离，文档里应明确写明「CLI 看不到 DSH 的 Documents / Memory Spaces」。

## 闭环验证（2026-11-22 01:19 补测，已通过）

探针文档 `2f793cf1` 的检索回读**已完成**：

```
mnemon_document_search(query="zebra-quasar-2201 探针 Documents 闭环")
→ total: 1
  results[0].id            = 2f793cf1-094c-4fd9-bdd4-edb6c038de98
  results[0].relativePath  = "documents/active/2201-documents-2f793cf1.md"
  results[0].score         = 13
  results[0].content       = 「…唯一标记词：zebra-quasar-2201…」
```

**结论：Documents 的「写入 → 索引 → 检索」在功能层是完整闭环的**，两次独立验证（`e5b1e7c4` 跨重启命中、`2f793cf1` 写入即命中）都通过。

因此本 issue 的定位进一步收窄：**这不是功能缺陷，而是一处会误导排障与备份的「存储位置/口径不一致」问题**。

## 仍未验证（诚实标注）

- 未做「删除文档后用 CLI 检查 db 变化」的实验，故不能断言数据一定不在 `mnemon.db` 内（可能以非明文形式存入）。
- 未定位真实存储路径：`relativePath` 报 `documents/active/2201-documents-2f793cf1.md`，但该路径在 `~/.mnemon\documents\active\` 下**不存在**，全盘也未搜到同名文件。推测是相对某个未公开的 `storageRoot` 的虚拟路径。

## 本机结论（供本项目使用，不影响 issue 正文）

- Documents **写入 + 检索可用**（至少在本进程周期内、且能跨一次重启存活）。
- 「`index.json` 恒空」**不等于**「Documents 不可用」，两者不能互相推断。
- 在此之前写下的「不得声称 mnemon 文档检索可用」应改为「**可以用，但持久化位置与 `~/.mnemon/documents/` 不一致，备份时需另行确认**」。
