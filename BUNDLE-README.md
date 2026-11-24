# dsh-multi-role-flow（可分发 bundle）

> 由 `tools/build_bundle.py` 从流程包生成，**不要手改这里的副本**；改流程包后重新构建。

## 安装（一次）

```powershell
plugin_manager install_bundle target="<本目录的绝对路径>"
```

装完在**新会话**里应能看到技能 `dsh-multi-role-flow`（技能目录刷新，无需重启 DSH；若没出现，刷新页面或重启一次）。
卸载：`plugin_manager remove_bundle target="dsh-multi-role-flow"`（宿主侧已导入的 provider 需重启 DSH 才彻底消失）。

## 包含什么

- `roles/` 5 份角色说明书、`templates/` 文档与能力包模板、`tools/dsh_flow.py`（20 个子命令）、`ops/` 运维文档、`workflow/` 复核脚本、术语表/迁移说明；
- `skills/dsh-multi-role-flow/SKILL.md`：技能正文，**流程包根 = 技能目录向上两级**（即本目录）。

## 手工安装（不用 bundle 时）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\install.ps1 -Project "<your-project>"
```

## 已知限制

- skill 提供方用 `!!js` 读 `process.env.DSH_PROFILE_DIR` 拼包路径；若宿主环境没有该变量，安装会报激活失败——此时改用 `install.ps1` 的项目级安装。
- bundle 自带的技能与项目 `.dsh/skills` 下的同名技能可能同时出现；DSH 按扫描优先级取一个，内容相同不冲突。
