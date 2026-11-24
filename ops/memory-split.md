# 记忆分工：memory-evolve 与 mnemon 各记什么、冲突以谁为准

> 2026-11-20 定稿（feature `dev-toolchain-boost`，候选 C001）。适用于本机 `desktop` profile 上的全部多角色流程会话。
> 一句话：**流程事实进 memory-evolve，代码库知识进 mnemon（Provider 未就绪时降级到仓库文件 + 代码图谱），同一个事实只在一处当权威。**

## 0. 为什么必须写死

本机同时装着两套记忆：`dsh-memory-evolve`（0.1.0，已跑 key/daily/project 三轨）与 `dsh-mnemon`（0.5.50，分层记忆 + Memory Spaces；版本以 profile 实装为准，见 `ops/aux-tools.md` 第 1 节）。两套都能「记住」，如果同一事实两边各写一份，第二天就会漂移：一边说候选是 C001，另一边还停在 C000；一边说验收通过，另一边说待试用。分工的目的不是省事，是**让每个问题只有一个权威来源**。

## 1. 两套各管什么

| 维度 | memory-evolve | mnemon |
|---|---|---|
| 定位 | 流程与协作的记忆：谁在哪个阶段、做过什么决定、今天踩了什么坑 | 代码库与知识的记忆：这个仓库有哪些模块、为什么这么设计、某个结论的依据在哪 |
| 存储形态 | `MEMORY.md` / `USER.md` / 项目 `KEY.md` + 每日日志 + 项目日志 | Memory Space（本地 SQLite 或 Provider）+ Documents（项目级 Markdown 正文） |
| 注入方式 | 关键条目自动进上下文；日志按需读 | 不自动进上下文，按需 `recall` / `document_search` |
| 写入粒度 | 一行一条的短事实 | 成段的知识正文 + 一条索引记忆 |
| 生命周期 | 随流程推进不断追加，会被归档 | 长期沉淀，可修订、可链接 |
| 谁写 | 各角色收尾时用 `memory` 工具批量写 daily/project | executor 写代码知识；Lead 写决策结论 |

## 2. 四问（本文档的核心）

### 问题 1：流程事实进哪套？

**进 memory-evolve，不进 mnemon。**

流程事实 = 阶段、候选编号、门禁结论、阻塞、谁派了谁、这次改了什么、验收到哪一步。判据很简单：**下一个会话要用它才知道「现在该做什么」**，那就是流程事实。

| 例子 | 落位 |
|---|---|
| 「`dev-toolchain-boost` 候选 C001 已冻结，phase=VERIFYING」 | memory-evolve（项目 key / project 日志） |
| 「P5 因插件版本门禁被拒，待用户接受风险」 | memory-evolve（project 日志）+ `EXECUTION-PLAN.md` §八 |
| 「用户要求所有交付先过 verify 再谈上线」 | memory-evolve（user 轨） |

理由：流程事实要**自动进上下文**才起作用，mnemon 需要显式 recall，等你想起来去查时已经做错了。

### 问题 2：代码库知识进哪套？

**进 mnemon（Documents + 一个用途为「代码库知识」的 Memory Space）；Provider 未就绪时见问题 4。**

代码库知识 = 模块职责、关键调用链、为什么这样分层、某个坑的根因、某段配置的含义、图谱与索引的规模。判据：**删掉所有会话历史后它仍然成立**，且**对下一个读代码的人有用**。

| 例子 | 落位 |
|---|---|
| 「`weekly-report-dev` 用 graphify 建了 240 节点的图、GitNexus 建了 590 节点索引，查询入口分别是…」 | mnemon Documents |
| 「`pack/lib/store.js` 的 `saveWeek` 是周报落盘唯一入口，上游只有 `handleRequest`」 | mnemon Documents（可附 UID / 文件行号） |
| 「为什么选 `--code-only` 建图：语义提取要外发内容」 | mnemon Documents |

**代码本身仍是第一权威**：Documents 是二手描述，描述与代码不一致时以代码为准，并把 Documents 更新掉。

### 问题 3：两套冲突以谁为准？

按**事实类型**裁决，不按写入时间裁决（时间只用来判断「谁过期了」）：

| 冲突 | 以谁为准 | 理由 / 动作 |
|---|---|---|
| 流程进度类（阶段、候选、门禁、阻塞） | **memory-evolve**（且以 `docs/<feature>/state.json` 为最终事实） | 阶段只有一个写者（`flow.py`），记忆只是它的摘要；冲突时去读 `status`，把记忆改正 |
| 代码库描述类（模块职责、调用链、规模） | **仓库里的代码 / 图谱产物**，其次 mnemon Documents | 代码变了 Documents 就该改；反过来说，代码没变而 Documents 说变了 → Documents 错 |
| 两者都记了同一条通用事实 | **memory-evolve** | 通用事实要自动注入，mnemon 里那条删掉或改成指向流程结论的链接 |
| mnemon 与 memory-evolve 都被引用作为证据 | 都不算证据 | 候选真相只认 `manifest.json` 的 sha256 + `verify`；记忆是旁证 |

**操作纪律**：发现冲突时，先读权威来源（`status` / 代码 / `manifest.json`），再改记忆；**不许两边都留着让下一个人猜**。修正 memory-evolve 用 `memory ... replace`，修正 mnemon 用 `document_manage(action=update)` / `remember(action=replace)`，都保留修订痕迹。

### 问题 4：Provider 缺失时怎么降级？

mnemon 的 Memory Space 依赖 Provider（当前配置为 `mnemon-native`，需要本机 `mnemon` CLI 可被宿主拉起）。**Provider 不可用时，不要让知识无处可去，也不要假装写进去了。**

> **判据已在 2026-11-20（feature `toolchain-fixups`）更正**：`providers` 数组只列**非 native 的外部 Provider**（`providerServices()` 里 `filter(provider => !isNativeProvider(provider))`），只用 Mnemon Native 时**恒为空**。把它当就绪判据会永远判「不可用」——旧判据已废止，详见 `ops/aux-tools.md` §5.1。

| 阶段 | 做法 |
|---|---|
| 判断可用性（**现行判据**） | ① `mnemon_status.commandFound === true`；② `memorySpaces.total ≥ 1` 且 `memorySpaces.unhealthy === 0`；③ `mnemon_memory_bodies` 能列出 Space 且 `capabilities.remember = true`。三条同时满足即「可用」，**不看 `providers` 长度**；`providers` 只在配了外部 Provider（openviking / mem0 / honcho …）时才有内容 |
| Provider 真的缺失时 | ① 代码知识**先落仓库文件**：`ops/code-graph.md`、`ops/*.md`、feature 的 `EXECUTION-PLAN.md`「发现但不处理」；② 关键结论同时写 memory-evolve 的 project 日志（可以，但只写一句话摘要，正文不进日志）；③ 在回报里写明「mnemon 暂不可用」，不许写「已存入记忆」 |
| 修复顺序 | 确认 CLI 路径 → profile 的 `dsh-mnemon` 配置写 `cliPath`（或环境变量 `MNEMON_CLI_PATH`）→ **用户重启 DSH** → 重跑 `mnemon_status`；Provider 就绪后再建/激活 Memory Space，并把仓库文件里的知识搬进 Documents（搬完在仓库文件里留一行「已迁入 mnemon」） |
| 已知的好用写法 | `mnemon_document_create` 写入返回 `memoryReceipt.completion = committed`；检索是**纯词法**（标题 12 / 描述 7 / 正文 4 分 + token 命中，不依赖向量或 FTS，见 §6），**没有索引延迟**；**跨回合可命中**（2026-11-20 实测：写入探针 `fixups-probe-20261120-1105` 后，另一回合 `mnemon_document_search("zebra-quasar-9517")` → `total=1`、`score=5`）。`document_search` 受宿主「每回合一次」预算限制（超了返回 `budgetExhausted: true`，空数组 ≠ 没命中），别用它做批量试错 |
| 永远不做的降级 | 把 mnemon 的数据目录内容手写/拼接来冒充 Provider 写入；用另一套记忆的条目伪造 mnemon 回执 |

## 3. 写入速查

| 想记的东西 | 用什么 | 注意 |
|---|---|---|
| 今天做了什么、踩了什么坑 | `memory target=daily` + `target=project`（一次调用两条） | 不要带时间前缀，程序自动盖 |
| 长期有效的项目约定/关键结论 | `memory target=key`（走待确认队列） | 用户确认后才生效 |
| 用户偏好、称呼、边界 | `memory target=user` | 用户说了才算 |
| 代码库知识正文 | `mnemon_document_create`（Provider 就绪后） | 写清采集时间与依据（文件/命令） |
| 一条需要被 recall 的结论 | `mnemon_remember`（到「代码库知识」Space） | 一条一句，带 tags |

## 4. 不进记忆的东西

密钥 / token / 账号密码；用户上传的原始资料正文；一次性进度播报（「正在跑测试」）；能从 `state.json` / `manifest.json` / 代码直接读到的原文（记指针即可，别复制整份）。

## 5. 维护

- 每次改本文件的分工规则 = 改流程约定，需 Lead 审核 + 与 `roles/02-executor.md`、`roles/03-verifier.md` 的指针段保持一致。
- mnemon 从「不可用」变为「可用」时，必须回来更新问题 4 的状态行，否则下一个人会照着过期的降级路径走。

## 6. 检索是纯词法的：向量检索本机未启用（2026-11-20 实测，feature `toolchain-fixups` P15）

**结论先说**：本机 mnemon 的检索**全部是词法匹配**，没有向量、没有 FTS、没有索引延迟；「向量检索未启用」是**配置 + 服务缺失**，不是索引损坏，也不影响 remember / recall / document_search 的可用性。

**现状取证（2026-11-20）**：

| 项 | 实测值 | 取证方式 |
|---|---|---|
| 检索实现 | 标题 12 分 / 描述 7 分 / 正文 4 分 + token 命中计数，纯打分、无 embedding 调用 | 读 `dsh-mnemon-source-documents/lib/index.js` 的检索段（`lexicalSearchTokens()` 按 2-gram 切中文 → `requiredTokenMatches` 阈值 → 按 score 排序 `slice(limit)`，全文件无 embedding 调用） |
| profile 配置 | `~/.dsh\profiles\desktop\cordis.patch.yml` → `mnemon.config.embedding`：`enabled: false`、`endpoint: http://localhost:11434`、`model: nomic-embed-text`（`/v1` 结尾走 OpenAI 兼容协议，否则走 Ollama 协议） | 读配置文件 161–164 行 |
| 本地 embedding 服务 | **没有**：`127.0.0.1:11434` 未监听；`ollama` / `lms` / `lm-studio` / `lmstudio` 命令都不存在；`%LOCALAPPDATA%\Programs\Ollama`、`…\lm-studio`、`…\LM Studio`、`%ProgramFiles%\Ollama` 四个目录也都不存在 | `Get-NetTCPConnection -LocalPort 11434 -State Listen` → 空；`Get-Command …` 全 not found；`Test-Path` 全 False |
| 后果 | 语义/近义检索不可用；按标题/描述/正文关键词查找可用 | 上面两条合起来的直接结论 |

**词法检索的两个实操后果**（本 feature 实测）：

1. **只认字面重叠**：同义改写、跨语言、概念相近但用词不同的查询查不到 → 写 `ops/*.md` 与 Documents 时，正文措辞要当成「检索键」来写（用真实会出现在查询里、而不是只描述它的词）；**「检索不到 ≠ 没写过」**，0 命中先怀疑查询词，再怀疑写入。
2. **没有索引延迟，跨回合可命中**：2026-11-20 实测写入探针 `fixups-probe-20261120-1105` 后，另一回合 `mnemon_document_search("zebra-quasar-9517")` → `total=1`、`score=5`。限制不是索引而是**每回合 1 次** `document_search` 预算（超了返回 `budgetExhausted: true`，空数组 ≠ 没命中）。

**要开启向量检索，三条必须同时满足（缺一条就是白开）**：

1. **有服务**：本地 embedding 服务在 `11434` 监听（可选：把 `endpoint` 改成任一回 `{embedding:[…]}` 的 OpenAI 兼容地址）。
2. **有模型**：服务侧已拉取对应模型（默认 `nomic-embed-text`，约 274 MB；换模型名要同步改配置）。
3. **配置 + 重启**：`embedding.enabled` 改 `true`，然后**用户重启 DSH**（mnemon 配置在宿主启动时读取，热改不生效）。

**代价与风险（决定开之前先认这三条）**：

| 代价 | 说明 |
|---|---|
| 首次全量向量化 | 启用后要对既有 Documents / 记忆条目批量生成向量；数据量小也仍要跑一轮，且失败不会自动回退到纯词法（需人工回退 `enabled: false`） |
| 写入变慢、强依赖服务 | 每次写入都要调一次 embedding；服务挂了就是写入失败，纯词法时代没有这个失败面 |
| 换模型 = 换向量空间 | 换 `model` 必须重建全部向量，否则检索质量悄悄下降且**不报错**（最难查的一类问题） |
| 常驻资源 | embedding 服务要常驻内存/显存，本机是桌面机，没有专门的推理预算 |

**本 feature 的决定**：**不启用**（用户未批准安装模型服务，且当前需求是「按标题/关键词找回文档」，纯词法已够）。要开时按上面三条走，并回来改本节状态行。

**纪律**：不要用「有没有向量」判断记忆是否可用——可用性判据仍是问题 4 的三条（`commandFound` / `memorySpaces.unhealthy=0` / `capabilities.remember=true`），`embedding.enabled=false` 不影响其中任何一条。GitNexus 的 FTS（`bm25`）是**另一套东西**（关键词倒排，不是向量），别混为一谈，见 `ops/aux-tools.md` 的「GitNexus FTS 前置条件：OpenSSL 3 与 wrapper」一节。

## 7. RAG-Anything 的落位与降级（与 mnemon 分开判）

> 2026-11-21 定稿（feature `flow-quality-boost`）。一句话：**RAG 管「文档/资料正文与多模态解析」，不管流程事实，也不管代码库知识**；它的可用性判据与 mnemon 完全不同，别混。

### 7.1 落位：RAG 记什么、不记什么

| 内容 | 进 RAG？ | 理由 |
|---|---|---|
| 文档 / 资料正文（PDF、Word、扫描件、图片里的文字） | ✅ | 这是 RAG 的唯一强项：版面 + 多模态解析（MinerU 侧车）后按块检索 |
| 某个结论「依据是这份文档的第几节」 | ✅ | 引用回原文，别的记忆层给不了 |
| 流程事实（阶段 / 候选编号 / 门禁结论 / 阻塞 / 谁派了谁） | ❌ | 归 memory-evolve（§2 问题 1）；RAG 没有状态机语义 |
| 代码库知识（模块职责、调用链、为什么这么设计） | ❌ | 归 mnemon Documents（§2 问题 2）；RAG 的切片会打散调用关系 |
| 密钥 / token / 用户上传的原始资料正文 | ❌ | 见 §4「不进记忆的东西」 |

### 7.2 四态降级表（交接包「知识入口」块里的 RAG 行按此措辞）

| 情形 | 交接包写法 | 是否阻塞 |
|---|---|---|
| 配置目录存在、日志文件存在 | `配置在、有运行日志（最后活动 <mtime>）` | 否 |
| 配置目录存在、无日志 | `配置在、无运行日志；未提供（RAG sidecar 不可达）` | 否 |
| 配置目录不存在 | `未安装（未提供）` | 否 |
| 任何情形 | 都**不得**写「RAG 可用 / RAG 已就绪」——离线判不了 | — |

**`dsh_flow.py next` 的实现口径**（`_ctx_knowledge_entries`，只读、离线）：默认配置目录 `%USERPROFILE%\.dsh\raganything`；目录里**一个文件都没有**（含指向空目录 / 目录不存在）就记「未安装（未提供）」，否则按有没有文件名含 `log` 的文件分成前两行。`--rag-dir` 是**仅测试用**的覆盖参数（默认取真实位置，文档不宣传）。

### 7.3 与 mnemon 的可用性判据不混

**mnemon 的三条判据（§2 问题 4）需要 MCP 活体调用**：`mnemon_status.commandFound`、`memorySpaces.unhealthy=0`、`capabilities.remember=true`——离线判不了，只能现场调。
**RAG 的离线判据只能给「配置/日志层证据」**：配置目录在不在、有没有运行日志、最后活动时间。两者不混：交接包里的 RAG 行**永远**是「未提供（RAG sidecar 不可达）」这一降级措辞，绝不用它推断 mnemon 的状态，也不反过来用 mnemon 的结论推断 RAG。

### 7.4 现状记录（2026-11-21 实测）

- 配置目录存在（`~/.dsh\raganything\config.json`、`logs\sidecar.log`、`storage\**` 等），但 `rag_docs` / `rag_query` 实测 **`fetch failed`**（sidecar 不可达）。
- 因此本轮把它写成**明确的降级契约**：不可用时不阻塞、交接包写「未提供（RAG sidecar 不可达）」；要恢复可用性，先按 `rag_status` 诊断 sidecar 进程与端口，再回来更新本节的状态行（**不要**只在交接包里改措辞）。

