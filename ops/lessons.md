# 跨 feature 教训库（ops/lessons.md）

> 一行一条，跨 feature 复用。**唯一写入口是 `dsh_flow.py lesson add`**（自动取下一个 `L00n`、追加一行、打印新 ID），
> `lesson list` 只读。行契约（改动等于改接口，`next` 的「同类坑」按它解析）：

```text
| L00n | 症状：一句话，能被人搜到 | 根因：为什么会这样 | 做法：下次怎么办 | executor,verifier | 2026-11-20 |
```

- 正则契约：`^\|\s*(L\d{3})\s*\|(.+)\|(.+)\|(.+)\|\s*([a-z,]+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|$`
- 适用角色取值：`lead,planner,executor,verifier,inspector,all`（`all` 对任何角色都注入）。
- 不合正则的行不会被跳过隐藏：`lesson list` 会标 `⚠ 行格式无效`。
- 这里只记**会重复犯**的坑，不记一次性进度（进度在 `docs/<feature>/`）。
- `next` 生成交接包时按角色注入：角色命中 ≤3 条 + `all` ≤2 条，每条一行「症状 → 做法（L00x）」。

| ID | 症状 | 根因 | 做法 | 适用角色 | 日期 |
|---|---|---|---|---|---|
| L001 | 上一候选 `verify` 突然报「封存后内容被改」，但没人改过候选文件 | `DEPLOYMENT-PLAN.md` 是全 feature 单一台账，却被上一候选的 `verification.json` 登记过哈希，于是本轮写台账就等于改封存件 | 验证线程本轮不写 `DEPLOYMENT-PLAN.md`；发布事实写进 `releases/<C>/RELEASE-REPORT.md`（每个候选自己的文件） | verifier | 2026-11-20 |
| L002 | 用 `edit` 工具写出 `.ps1` 后，脚本执行报语法错或中文乱码 | 工具写出的 `.ps1` 没有 BOM，Windows PowerShell 5.1 按本地代码页解析中文 | `.ps1` 用带 BOM 的方式生成（或改用 `.cmd` 包装）；脚本与证据里别塞多行双引号 | executor | 2026-11-20 |
| L003 | 直接双击或直接调用 `.ps1` 报「禁止运行脚本」 | 本机执行策略默认 `Restricted` | 一律 `powershell -ExecutionPolicy Bypass -File <脚本>`，或用 `.cmd` 包装一层 | executor,verifier | 2026-11-20 |
| L004 | 手改了 preset 镜像 `flow/` 却「没生效」，过一阵还被覆盖回去 | 镜像由 `scripts/sync-flow.ps1` 从源仓库单向覆盖 | 只改源仓库 `dsh-多角色协作流程`；镜像同步交给 Lead 在验收后跑 `sync-flow.ps1` | lead,executor | 2026-11-20 |
| L005 | 新加的教训不进交接包 | 按角色过滤后取文件最早 N 条，满额后新条目永远带不出来 | 改为从文件尾向前累计取最新 N 条（[-N:]），输出按时间正序 | executor | 2026-11-21 |
| L006 | 用 PowerShell 写 markdown 时反引号代码词变成控制字符 | PowerShell 把反引号b/a/v/n 当转义序列，写进文件变成 0x08/0x07/0x0b/换行 | markdown 一律用 write/edit 工具写；写完扫 0x00-0x08/0x0b/0x0c/0x0e-0x1f 必须 0 命中 | executor | 2026-11-21 |
| L007 | 测试断言依赖进程 cwd 或本机真实记忆文件，时通时不通 | 断言读了真实环境而非 fixture，换机器或换目录就红 | 有真实数据则断言命中、无则 skip 并打印原因，skip 不算通过 | executor,verifier | 2026-11-21 |
| L008 | 误判 ops 文档丢失并急着重写，导致 build_bundle --check 与 selftest 双双失败 | 恢复前没有先查 dsh-bundle-live 与 releases 下的 files 副本，那里有完整原版 10126 字节与 12959 字节 | 恢复任何文件前，先 Get-ChildItem 搜 dsh-bundle-live、releases 下的 files、TEMP 备份目录；有原版就用原版 Copy-Item 回来，不要用自己的简版覆盖 | lead,executor,verifier | 2026-11-21 |
| L009 | 2026-11-20 23:37 一条 cmd 命令从 D 盘根递归删除，丢失源仓库与多个项目 | PowerShell 不认双引号转义，cmd 收到盘符根 D 冒号反斜杠 | 删目录一律先 Resolve-Path 校验绝对路径，再用 Remove-Item -LiteralPath 路径 -Recurse -Force；禁止 cmd /c rd /s /q | all | 2026-11-21 |
| L010 | 会话日志回放重建后 selftest 全绿，但 state.json baseline.json ledger.md 全缺，候选无法 seal | 这些是工具写的文件，不在 write/edit 回放范围内 | 事故善后时把 state.json baseline.json ledger.md 单独列为必补项；用 init 幂等重建（跳过已存在文档），再重冻新候选，不要指望回放 | lead,inspector | 2026-11-21 |
| L011 | build_bundle.py 报 OSError [WinError 145] 目录不是空的: ...\dsh-bundle-live\skills；此前 shutil.rmtree 已先删掉包内 41 个文件，把分发包变成半删状态 | D: 是 exFAT 且卷 HealthStatus=Warning，dsh-bundle-live\skills 成了损坏目录项：Get-Item / Rename-Item / Remove-Item / [System.IO.Directory]::Delete / fsutil reparsepoint 全部 Access is denied，ACL 修复脚本也在 Test-Path 处失败（与 2026-11-20 的 dsh-bundle\skills 同型） | 重建分发包前先 Test-Path + Get-ChildItem 探测目标目录可枚举；撞上损坏目录项不要换更暴力手段（cmd rd /s、takeown、chkdsk 都要用户在场），停下报 Lead，由用户重启或管理员 chkdsk D: /f 清项后重跑 build_bundle.py；校准判据是 build_bundle.py --check exit 0，不是「删掉了」 | executor,lead | 2026-11-21 |
| L012 | 改完 tools/ roles/ GLOSSARY.md 没重建 bundle，selftest 的 J 套 --check 连锁红 3 条 | build_bundle 的 COPY_DIRS/COPY_FILES 覆盖 tools/roles/ops/templates/skills 与 GLOSSARY.md 等，源文件一动 bundle 就变陈旧；--check 按 sha256 判陈旧，先红第一条、后面「多余文件」断言全被带红 | 顺序固定为：改源 → `& $PY tools/build_bundle.py` → `& $PY tools/build_bundle.py --check`（exit 0）→ 再跑 selftest；只改 docs/** 时不必重建（docs 不在 COPY_DIRS/COPY_FILES 里） | executor | 2026-11-21 |
| L013 | 解析 Markdown 某小节时把后面章节的表格行也算进来（rows=25、extra=['main']） | 用 `text.split('## 4. 命令',1)[1]` 取到文件尾，§8 源码索引表里的 `main` 行也被当成命令行 | 再切一刀 `.split('\n## ',1)[0]` 只取本节；表格行用正则锚定「行首竖线 + 反引号命令名 + 竖线」的首列，别用子串 `in` 判命中 | executor,verifier | 2026-11-21 |
| L014 | graphify 重建后只报 pruned 10 node(s) from 1 newly-ignored file(s)，但图里实际少了几百个副本节点；同时旧污染判据报 0 命中，图里 322/675 节点其实是 dsh-bundle-live 下的重复副本 | .graphifyignore 的排除清单只写了一个历史目录名 dsh-bundle/，产物目录改名后（dsh-bundle-live/、dsh-bundle-dist/）没同步；污染判据正则也只枚举 dsh-bundle 这一种拼写，所以既污染了图又不报警。graphify 自己的 pruned 计数只反映「本次被新 ignore 规则裁掉的缓存条目」，不能当「图已干净」的证据 | 排除清单与污染判据都按「家族」维护：.graphifyignore 显式列出所有历史变体（dsh-bundle/、dsh-bundle-live/、dsh-bundle-dist/），判据用共用一个常量 RE_GRAPH_COPY_SOURCE = dsh-bundle(?:-[A-Za-z0-9]+)*（**不要**用 dsh-bundle[^/]*，它会误伤 dsh-bundleable/）；验收只认重建后 nodes[].source_file 的实测分布，不认 graphify 的 pruned 行 | executor,inspector | 2026-11-21 |
| L015 | 每封一个新候选，前一个候选 verify 就报「封存后内容被改」，指向 DEPLOYMENT-PLAN.md | cmd_seal 原先登记全 feature 共用的单一台账，写台账等于改上一候选的封存件 | C004 起 seal 自动生成 releases/<C>/DEPLOYMENT-PLAN.md 快照并封该快照，共用台账仍可写但不再被登记；历史候选 C002/C003 仍绑共用台账，别去写它 | lead,executor,verifier | 2026-11-21 |
| L016 | 候选封存包丢了，会话日志回放补不回来 | manifest/verification/files 是工具写的凭证，不在 write/edit 回放范围；实测 243 个会话日志对它们命中 0 次 | seal 成功后自动异地快照到 %USERPROFILE%\.dsh\flow-snapshots（flow-backup-a）；恢复只回 manifest/verification/files，**不要**盖回 state.json/baseline.json/ledger.md（会让状态机回退） | lead,executor,verifier | 2026-11-22 |
| L017 | 另一个会话直接改本仓 tools/ ops/ ROADMAP.md 而不开 feature，导致 flow-quality-boost C011 作废、flow-backup-a C003 收编一版、audit 永久红 | 没有「改源码前必须开 feature」的硬约束，共享工作区无写隔离 | 改本仓源码前先在本仓 init feature（或只允许读）；发现未登记改动先 audit 定位、再开候选收口，不要顺手收编 | all | 2026-11-22 |
| L018 | .ps1 被 edit/重写后丢 UTF-8 BOM，PS 5.1 按 ANSI(cp936) 解析直接报「字符串缺少终止符」，脚本连语法都过不了、根本跑不起来 | 改文件的工具默认写无 BOM 的 UTF-8；而 PS 5.1 只在有 BOM 时才用 UTF-8 解码，否则按系统 ANSI 解，中文注释里的引号/字节被吃掉后字符串未终止 | 改完 .ps1 必须重写为带 BOM 的 UTF-8（`[IO.File]::WriteAllText($p, $t, (New-Object Text.UTF8Encoding($true)))`），并跑 `[System.Management.Automation.Language.Parser]::ParseFile` 断言 errors=0（`tools/selftest.py` 的 `suite_y` 已把这条做成回归守卫）；递归删除前必须先 `Resolve-Path` 校验绝对路径且段数≥3（`tools/build_bundle.py` 的 `guard_bundle_dir`、`tools/install-git.ps1` 的删除守卫） | executor,verifier | 2026-11-22 |
| L019 | 按工单给的行号改口径，改完仍有命中：工单只列 5 处，验收却是整文件 grep=0 | 工单行号是人手逐行摘的，验收判据来自 DESIGN/V 表的全文 grep；同一文件里还有同句式的其他行没被摘到（本次 MIGRATION.md 另有 3 处） | 动手前先按验收判据在整文件（必要时整目录）grep 一遍拿到全集，以判据为准；多改的行逐条写进回报的「上游问题」，不自行扩到别的文件 | executor | 2026-11-22 |
| L020 | 同一项目重复跑 install.ps1 会把 AGENTS.md 越装越长（3756→7587B、模板重复、首跑就没包 begin/end 标记）；init --scope tools,ops 存成单条 tools,ops，audit 把 tools/* 判「不在声明写范围内」 | 两处都把「结构化分隔」当普通字符串：install.ps1 在 AGENTS.md 为空时直接写模板、没包 begin/end 标记，下次就判不到标记再追加一份；cmd_init 对 action=append 的 --scope 只做 list()，逗号没拆成独立条目 | 写进磁盘又要「可重复执行」的段落必须包唯一 begin/end 标记，有标记就整段替换并保留标记外内容（无标记才追加）；CLI 多值参数（--scope 等）在 cmd_* 里先按逗号拆分→strip→去空→去重再落 state；验收用双断言：连跑两次 AGENTS.md 字节数不变且 begin/end 各 1 次；state.scope 无含逗号元素且 audit 对该文件不再报越界 | executor,verifier | 2026-11-22 |
| L021 | 写了证据文档后全仓 selftest 突然红，报 docs/<feature>/evidence/C002/V2.md:<某个不存在的子命令> | evidence 已从『整目录跳过』改为按『调用位』判据扫描（命令名后行尾结束或跟 -x 参数即判为真调用），而证据里描述夹具时写了『脚本路径 + 词 + 参数』的线性串 | 证据/文档里描述夹具一律用文字表述（如『路径 + 不存在的子命令 + 参数』），不写线性调用串；MD_CMD_REF_EXEMPT 有 len==2 的硬断言，不能靠加豁免续命 | executor,verifier,lead | 2026-11-22 |
| L022 | 给 build_bundle.py 的 COPY_DIRS 加了新目录后，build 成功但 --check 永远红，报某文件『陈旧』 | 该目录里有一个文件是由脚本**生成**的（如 skills/dsh-multi-role-flow/SKILL.md 带分发头与占位符替换），与源必然不同；它被当成『逐字节复制』进了 sha256 比对集 | 加目录前先查该目录里有没有『生成版同名文件』；把生成路径登记进 GENERATED，并在 _copied_files() 里 out.pop(g) 剔除、build() 复制循环里跳过它 | executor | 2026-11-22 |
| L023 | selftest 偶发假红在 J 套（探针）或 V 套（D-07 tools/__pycache__ 基线），重跑又绿 | 同仓多条会话线并行，两个 selftest 实例会互踩：J 套改字节比 bundle、V 套是**状态型**断言（比目录快照），任何并发写者都能弄红 | 跑前必须确认无并发实例（Get-CimInstance Win32_Process 过滤 selftest.py 为空）；跑完删 tools/__pycache__；把『因并发而重跑』如实写进证据备注，不要据此判 fail | executor,verifier,lead | 2026-11-22 |
| L024 | bundle 里某个文件是死引用（文档引用了它，但 bundle 里根本没有），而 build_bundle.py --check 仍 exit 0 | 收录范围漏了该目录/文件时，源与 bundle **都不含**它 → 无从比对 → 永远通过（典型的『盲区』，与 G4 只比存在性同族） | 修法是把收录范围补上，并造一条『删掉 bundle 里该文件必须 exit 1 并点名』的反向断言；反向断言要带前提门禁（副本原状必须先 exit 0），否则会平凡通过 | executor,verifier | 2026-11-22 |
| L025 | 把工具目录从 D:\Programs 搬到别处后，MCP 立即失败 / 旧路径命令报「找不到」 | ① DSH 的 mcp-client 会在子进程被杀后一两秒自动重拉，所以「先搬目录再改配置」必然撞锁；② graphify\Scripts 下 15 个 exe 内嵌 #!<旧路径>\python.exe，只改 PATH 救不回来 | 顺序必须是「先改配置指向新路径（新路径尚不存在→重拉失败不锁文件）→ 杀 MCP 子进程 → 同卷 Move-Item → 留 Junction 兜底 shebang → 改 PATH → 校验」；回滚靠「配置备份 + 目录搬回 + 删 Junction」 | executor,verifier | 2026-11-22 |
| L026 | 把 17 处 X 替换成包装函数后，用 grep 数 X 的剩余处数仍报 2 处，看起来像没替换干净 | 第一版在注释里原样写出了被替换的符号+左括号，grep 把注释也算进去了 | 替换类改动不要在注释/文档里原样保留「被替换符号 + 左括号」，改用文字描述（如「裸的子进程调用」）；验收用的 grep 要么排除注释，要么用 AST 统计真实调用点 | executor | 2026-11-22 |
| L027 | 候选的 rollback.restore_from 指向 baseline 目录，但那个目录里已是改后字节，回滚等于没回滚 | freeze --from 用的是「改后」的隔离副本，manifest.base.path 记的就是它；真正能回滚的只有提交前冻结的旧候选 files/ | 要可回滚，base 必须指向改前状态（上一次 seal 的 releases/<C>/files/），或至少不要 promise restore_from=baseline；生成候选时把回滚源单独写在 RELEASE-REPORT 里并核实它的哈希是改前值 | executor,verifier,lead | 2026-11-22 |
