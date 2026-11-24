# DSH 能力包 / 插件开发硬事实

> 适用：Lead、执行（executor）、验证（verifier）。开发前读第 1—9 节，交付前逐条跑第 10 节清单。
> 参考已装包：`dsh-meetai@0.4.0`、`@local/huiwen-ppt@0.5.5`、`@local/dsh-workbench@2.8.0`（位于 `$DSH_PROFILE_DIR/node_modules/`）。

## 1. 角色分工

| 角色 | 做 | 不做 |
|---|---|---|
| Lead | 定验收标准、冻结候选、裁决重启时机 | 不看证据就宣布上线 |
| 执行 | 写四件套、自测、`freeze` | 手改 profile、跳过握手 |
| 验证 | 安装、`handshake`、`seal`、写发布报告 | 改业务代码、靠出新候选掩盖旧宿主 |

## 2. 包结构（最小四件套）

| 文件 | 作用 | 硬检查 |
|---|---|---|
| `package.json` | 声明 `dsh.bundle.patch`、`dsh.client`、`dsh.capabilityPack` | `name` 唯一；`version` 与健康检查返回一致；`files` 覆盖全部运行文件 |
| `index.js` | 宿主半：`export function apply(ctx)` 或 service class，注册 `GET /api/<短id>/health` | 路由不占用 `/api/workbench`；未知路由返回结构化 404 |
| `client.js` | 浏览器半：`window.__ModuleLoader__.load({ id, factory })` | `id` == `package.json` 的 `name`，不是短 id |
| `cordis.patch.yml` | 向 Loader 插入本包行 | `- insert: - id: <短id> name: <包名> config: {}`（自定义入口可写相对路径）；不重复插同名 id |

`dsh.capabilityPack`：`id` 用短 id；`entryKey` 固定 `cap:<短id>`；`openEvent` 与前端监听名一致；`version` 可带 `v` 前缀，但健康检查必须返回纯版本号。

## 3. 模块 id 规则（最高频事故）

| 概念 | 正确取值 | 写错的表现 |
|---|---|---|
| 浏览器模块 id（`__ModuleLoader__.load({ id })`） | manifest 包名，如 `@local/dsh-weekly-report` | 能力列表能显示，点打开找不到面板 |
| `capabilityPack.id` | 短 id，如 `weekly-report` | 入口或事件对不上 |
| `entryKey` | `cap:<短id>` | 打开事件无效 |

自检：`Select-String client.js -Pattern "__ModuleLoader__"` 的 id 与 `package.json` 的 `name` 逐字符相等。

## 4. 热更新边界

| 改动 | 是否需重启 DSH | 依据 |
|---|---|---|
| `client.js` / 前端 bundle | 否，刷新页面（整包替换以实际加载 asset hash 为准） | 浏览器 HMR |
| `index.js`（宿主半） | **是** | ESM 不热替换；替换已安装包要新的 JS 模块代 |
| `cordis.patch.yml` / 行定义 | 是 | Loader 启动时读取 |
| 数据文件 / 配置 JSON | 否 | 运行时读取 |

- `plugin_manager` 禁用再启用**不能**重载宿主半（实测）。
- 「新版是否在跑」只认握手，不认安装回执、进程启动时间或文件 mtime。

## 5. 版本握手

- 每个能力包暴露 `GET /api/<短id>/health`，返回 `{ok: true, version: "0.4.1", routes: [...]}`；`version` 必须等于 `package.json` 的 `version`。
- 前端发业务请求前应先查 `/health` 的 `routes`；缺路由直接提示重启 DSH，不再发业务请求。
- 命令：`flow.py handshake --id C00N --expect <版本> --url <健康检查地址>`；退出码 0 = PASS，1 = FAIL；证据落在 `evidence/C00N/R1-handshake.md`。
- PASS 条件：HTTP 200 且版本相等（`v` 前缀与大小写已归一）。

## 6. 别用新候选掩盖旧宿主

装上后行为没变时，按顺序：

1. 跑 `handshake`；FAIL 先怀疑宿主半仍是旧版。
2. 精确重启 DSH（由用户重启；不要杀 `python`/`node` 全体进程）。
3. 重启后再 `handshake`。
4. 仍 FAIL 才查代码或出新候选；禁止连续冻结 `C00N+1` 试错。

等待用户重启时用 `flow.py block --reason "等待重启 DSH" --owner user`，不要靠出新候选推进。

## 7. 错误格式

- 前端统一显示 `HTTP <status> <METHOD> <path>（<code>）`，如 `HTTP 404 POST /api/<短id>/analyze（NOT_FOUND）`；路径必须带 `/api/<短id>` 前缀。
- 服务端返回结构化错误：`{ error, method, path, hint }`；未知路由 404 也必须带方法与路径。
- 禁止裸 `NOT FOUND`、`Something went wrong`、只给错误码不给上下文。

## 8. 旧数据迁移

- 读时迁移、只读、原文件不改：旧 Markdown 在展示层转纯文本（去 `#` 等标记），不批量重写历史文件。
- 证据必须含：原文件改前 / 改后 sha256 一致 + 页面回执。**哈希由 Lead 在非武装会话执行并留证据**（`flow.py verify`，或本机未被 `$stop-that-shit review` 武装的 pwsh 里跑 `Get-FileHash -Algorithm SHA256`）；武装会话里 `Get-FileHash` 属未白名单程序，**必被拒**（`shell_command_unproven`，见 `ops/aux-tools.md` 的「武装后哪些命令形态会被拒」一节），别把它写进复核 agent 的任务里。
- 需要落新格式时写新文件或新目录，不覆盖旧数据。

## 9. 安装与「装上了」的含义

- `plugin_manager install_bundle target=<项目根>/docs/<feature>/releases/C00N/files/pack`（绝对路径）。
- 返回 `version / stage / enabled / application`；`application: applied` 只说明本次变更进入运行时；`restart-required` = 未生效。
- 安装成功 ≠ 运行新版；以 `handshake` 的期望/实际版本为准。

## 10. 提交前检查清单

- [ ] `package.json` 的 `name` == `client.js` 模块 id（`@local/<短id>` 或 `dsh-<短id>`）
- [ ] `entryKey` == `cap:<短id>`，`openEvent` 与前端监听一致
- [ ] `GET /api/<短id>/health` 可达，`version` == `package.json` 版本
- [ ] 未知路由返回结构化 404（含 method、path、hint）
- [ ] 前端错误统一 `HTTP <status> <METHOD> <path>（<code>）`
- [ ] 宿主半改动后已重启 DSH，不是禁用再启用
- [ ] 装完/重启后 `handshake` 退出码 0，证据为 `R1-handshake.md`
- [ ] 旧数据读时迁移正确，原文件 sha256 未变
- [ ] 回滚材料（备份、回滚命令、保留范围）可执行
- [ ] `RELEASE-REPORT.md` 结论三态与握手结果一致
