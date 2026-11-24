# {{PACK_TITLE}}（{{PACK_NAME}}）

> 能力包骨架，由 `flow.py init --kind plugin` 生成。占位符已替换成你的项目值：`{{PACK_ID}}`、`{{PACK_TITLE}}`、`{{PACK_VERSION}}` 等。
> 交付前请通读 `ops/dsh-plugin-dev.md`（硬事实 + 10 节检查清单），它比这份 README 更权威。

## 1. 这个骨架包含什么

| 文件 | 作用 |
|---|---|
| `package.json` | 包声明：`dsh.bundle.patch`、`dsh.client`、`dsh.capabilityPack`（9 个字段齐全） |
| `cordis.patch.yml` | 向 Loader roster 插入本 bundle 行（`id` 用短 id，`name` 用包名） |
| `index.js` | 宿主半：`GET /api/{{PACK_ID}}/health`、`POST /ping` 示例、结构化 404、`apply(ctx)` 注册路由与能力清单 |
| `client.js` | 浏览器半：`__ModuleLoader__.load({ id: '{{PACK_NAME}}' })` + 主面板/侧栏入口 + 示例按钮 |
| `scripts/smoke.mjs` | 零依赖自检：契约字段、patch、模块 id、health / 404 / ping 行为 |
| `icon.svg` | 包图标（列表里显示的是 `capabilityPack.icon` 的 emoji，可选） |

## 2. 收尾三件事（顺序固定）

```powershell
# 1) 自检：零依赖，只读
node scripts/smoke.mjs

# 2) 安装（把绝对路径给 plugin_manager）
#    plugin_manager install_bundle target=<项目根>\pack
#    返回 version / stage / application；application: applied ≠ 已生效

# 3) 版本握手（装完/宿主半改动后必须重启 DSH 再握手）
$PY = "~/.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $PY "<flow-home>\tools\dsh_flow.py" handshake -p <项目根> -f {{FEATURE}} `
  --id <候选> --expect {{PACK_VERSION}} --url http://127.0.0.1:<端口>/api/{{PACK_ID}}/health
```

握手 FAIL 的处置见 `ops/host-restart-sop.md`：先判断「没装上」还是「没重启」，再用 `block --owner user` 等用户重启，不要出新候选掩盖。

## 3. 热更新边界（最容易踩）

| 改动 | 是否要重启 DSH |
|---|---|
| `client.js` / 前端资源 | 否，刷新页面（以实际加载 asset hash 为准） |
| `index.js`（宿主半）、`cordis.patch.yml` | **是**，ESM 不热替换；禁用再启用插件也不能重载 |
| 数据文件 / 配置 JSON | 否 |

## 4. 两条高频事故

1. **浏览器模块 id 必须等于 package.json 的 `name`**（`{{PACK_NAME}}`），不是短 id `{{PACK_ID}}`。写错的表现：工作台能看到入口，点「打开」没反应。
2. **`entryKey` 必须是 `cap:<短id>`**（`{{PACK_ENTRY_KEY}}`），`openEvent` 与前端监听名一致（`{{PACK_OPEN_EVENT}}`）。

`scripts/smoke.mjs` 对这两条都有断言。

## 5. 交付前检查

- [ ] `node scripts/smoke.mjs` 全 PASS
- [ ] `plugin_manager install_bundle` 成功，`list_bundles` 里可见且 enabled
- [ ] 重启 DSH 后 `handshake` 通过（实际版本 = package.json version）
- [ ] `GET /api/{{PACK_ID}}/health` 可达，未知路由是结构化 404
- [ ] 主面板能从侧栏入口打开（打开事件 `{{PACK_OPEN_EVENT}}` 生效）
- [ ] `manifest.json` 带 `--runtime-kind plugin --runtime-version {{PACK_VERSION}} --health-url ...`
- [ ] 回滚材料（`rollback.preserve`、备份、回滚步骤）可执行
