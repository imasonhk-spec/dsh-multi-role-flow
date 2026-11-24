#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建可分发 DSH bundle：dsh-多角色协作流程/dsh-bundle/

产物 = 流程包本体（角色/模板/工具/文档，去掉 examples 与自身）+ 技能目录 + bundle 清单。
用法：python tools/build_bundle.py            # 重建 dsh-bundle/
      python tools/build_bundle.py --check    # 只检查产物是否最新（selftest 用）
      python tools/build_bundle.py --check --dir <路径>   # 只读检查**另一个** bundle 目录（副本探针用）
安装：plugin_manager install_bundle target=<本目录>
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path

# 2026-11-21：Windows 控制台默认 GBK，直接 print "✓/✗" 会抛 UnicodeEncodeError 并以非 0 退出，
# 被 selftest J 套误判成「bundle 有问题」（假红会埋掉 G4 的真反向断言）。
# 这里自保，不依赖调用方设 PYTHONIOENCODING。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

PKG = Path(__file__).resolve().parent.parent


def bundle_dir(pkg: Path = PKG) -> Path:
    """bundle 产物目录：优先读项目根 `.dsh-flow-bundle-dir` 的一行路径，缺失用 dsh-bundle/。

    为什么需要这层间接（2026-11-20 事故善后）：`dsh-bundle/skills` 在 exFAT 上成了
    **损坏目录项**——枚举/改名/删除全 `Access denied`，`shutil.rmtree` 报「目录不是空的」，
    连 ACL 修复脚本都在 Test-Path 这一步就 `UnauthorizedAccessException`。
    于是无法原地重建。约定：项目根放一行 `.dsh-flow-bundle-dir`（例如 `dsh-bundle-live`），
    构建与自测都读它，符号链接也指向它，功能等价。
    配置缺失时行为与旧版完全一致（默认 `dsh-bundle/`）。
    """
    cfg = pkg / ".dsh-flow-bundle-dir"
    try:
        if cfg.is_file():
            raw = cfg.read_text(encoding="utf-8").strip()
            if raw:
                p = Path(raw)
                return p if p.is_absolute() else (pkg / p)
    except OSError:
        pass
    return pkg / "dsh-bundle"


BUNDLE = bundle_dir()


def guard_bundle_dir(target: Path) -> Path:
    """**删除产物目录前的守卫**：绝对路径 + 段数 ≥3 + 叶子名以 `dsh-bundle` 开头，任一不满足就拒绝。

    为什么必须有（2026-11-20 事故同族形态）：`.dsh-flow-bundle-dir` 是项目根下一个**可编辑文本**，
    内容直接决定 `build()` 要 `shutil.rmtree` 哪个目录。旧版 `bundle_dir()` 只判了
    `is_absolute()`——写成 `D:\\`（绝对路径、`is_absolute()` 为真）就被原样返回，于是
    `shutil.rmtree(Path("D:\\\\"))` 会把整个 D 盘删掉，与 L009「一条 cmd 从 D 盘根递归删除」
    是同一种灾难。

    判定原则（ops/lessons.md L009、DESIGN「宁可拒绝，不可删除」）：**拒绝的代价是一次报错，
    删除的代价是全盘损失**。因此三条都取「保守」侧：
      - 用 `os.path.abspath` 而不是 `Path.resolve` 规范化：只做 `..`/冗余分隔符归一，
        **不跟随**符号链接/junction（`rmtree` 本身也拒绝符号链接，跟随会改变语义）；
      - 段数 ≥3：`D:\\` 只有 1 段、`D:\\x` 只有 2 段，都是浅路径，一律拒；
      - 叶子名以 `dsh-bundle` 开头（`dsh-bundle-dist` / `dsh-bundle-live` / `dsh-bundle` 都过）。

    不满足时**打印中文原因并以 2 退出**，绝不执行 `rmtree`。返回规范化后的绝对路径。
    """
    abs_path = Path(os.path.abspath(str(target)))
    parts = abs_path.parts
    reasons: "list[str]" = []
    if not abs_path.is_absolute():
        reasons.append("解析后不是绝对路径")
    if len(parts) < 3:
        reasons.append(f"路径段数 {len(parts)} < 3（盘符根 `D:\\` 只有 1 段、`D:\\<一级>` 只有 2 段）")
    if not abs_path.name.startswith("dsh-bundle"):
        reasons.append(f"叶子名 {abs_path.name!r} 不以 'dsh-bundle' 开头（产物目录必须叫 dsh-bundle*）")
    if reasons:
        print("✗ 拒绝删除产物目录（guard: 绝对路径 + 段数≥3 + 叶子名 dsh-bundle*）", file=sys.stderr)
        print(f"  实际路径：{abs_path}", file=sys.stderr)
        print(f"  原始配置：{target}", file=sys.stderr)
        for r in reasons:
            print(f"  拒绝原因：{r}", file=sys.stderr)
        print(f"  修法：把 {PKG / '.dsh-flow-bundle-dir'} 改为项目根下的相对目录名"
              "（如 dsh-bundle-dist）；**不要**写成盘符根或过浅路径。", file=sys.stderr)
        sys.exit(2)
    return abs_path
# 唯一版本源（G4）：dsh-bundle/package.json 的 version 由它生成。
# 1.0.0 → 1.1.0（SemVer minor）：新增 lesson/scope 子命令与 --reused/--memories-dir/--key-note 可选项、
# 记忆真读；未删除/重命名既有子命令或 flag、manifest/state schema 未变 → 不升 major。
# 1.1.0 → 1.2.0（SemVer minor）：新增 drive 只读子命令（8 行文本 / 12 键 JSON）、freeze 内挂载
# QC-static 静态检查（--skip-qc）、next 第 5 块「知识入口」（--rag-dir/--mnemon-cli）、
# gate/status 的 ⚠ 软告警；既有子命令与 manifest/state schema 一个没动 → 不升 major。
# 1.2.0 → 1.2.1（SemVer patch，C002）：**只修缺陷、不新增子命令**——QC 对 templates/** 假阳性
# 与 `!!js` 标签误判（降 fail 为 skip）、warn_for 增「缺 P* 证据」软告警、doctor 的 node 探测、
# `--key-note` 支持多次（既有 flag 的可选性变强，向后兼容）、GLOSSARY 子命令计数 23 → 24。
# 子命令集合与 manifest/state schema 未变 → patch 而非 minor。
# 1.2.1 → 1.2.2（SemVer patch，C003）：**同样只修缺陷**——`.graphifyignore` 的排除清单补
# `dsh-bundle-live/`、`dsh-bundle-dist/`（图谱被分发副本污染），两处污染检测正则合并为
# `RE_GRAPH_COPY_SOURCE`（覆盖 `dsh-bundle` 及 `dsh-bundle-<后缀>`，不误伤 `dsh-bundleable/`）。
# 无新增/删除子命令、无 flag 变化、manifest/state schema 未变 → patch。
# 1.2.2 → 1.2.3（SemVer patch，C004）：**只修缺陷**——`seal` 不再把全 feature 共用的
# `DEPLOYMENT-PLAN.md` 直接登记哈希，改为先快照到 `releases/<C>/DEPLOYMENT-PLAN.md` 再封存该副本
# （旧格式 verification.json 仍按记录路径校验，C002/C003 不受影响）；
# 无新增/删除子命令、无 flag 变化、manifest/state schema 未变 → patch。
# 1.2.3 → 1.2.4（SemVer patch，C007）：**只修缺陷 + 文档**——`warn_for()` 的 E1 条改为先判
# 「文档类候选」：不再只看「产物里有没有代码类扩展名」，改为「相邻候选的**变更集**里有没有
# 代码类文件」（`_doc_only_delta()`；全量扩展名 `_doc_only_candidate()` 降级为首候选回退）；
# `ROADMAP.md` 的状态值改为「以 `flow.py status` / `drive` 现读为准」。
# 1.2.4 → 1.2.5（SemVer patch，C007 裁决后补）：Lead 2026-11-21 裁决——本项目 `--scope .`
# 整包冻结，全量扩展名判据恒判代码候选（C006 实测 8/48），**零收益**；主判据改为变更集
# （新增 + 修改 + 删除，删除按原 path 扩展名判），全量降级为首候选回退。判据函数拆成
# `_prev_frozen_candidate` / `_artifact_shas` / `_doc_only_delta` / `_doc_only_verdict`。
# 1.2.5 → 1.2.6（SemVer patch，C008）：**只修回归**——E1 的 P 证据识别正则曾收紧成
# `re.fullmatch(r"P\d+", check_id)`，只认「P29」不认「P29-doc-only-candidate」，而
# `roles/02-executor.md` 的命名规范就是 `P<编号>-<短名>.md` → 正常格式被误杀（C007 因此作废）。
# 改为 `RE_P_CHECK_ID = re.compile(r"P\d+(?:-[A-Za-z0-9._-]+)?")`，两种格式都认；
# 「证据文件真实存在且在 evidence/<候选>/ 下」这一步**保留**（防伪造靠它，不靠正则）。
# 子命令集合、flag、manifest/state schema 未变 → patch。
VERSION = "1.2.6"

# `skills/` 是**整目录收录**（按目录枚举，不写死技能名：将来新增技能自动进 bundle）。
# 唯一例外是 `skills/dsh-multi-role-flow/SKILL.md`——它由 `_skill_text()` 生成（插分发头 +
# 替换占位符），与源技能必然不同，因此登记在 `GENERATED` 里：既不参与「逐字节复制」的
# sha256 比对，也不走复制循环，只由 `build()` 末尾单独写入。
# 缺口背景（2026-11-22，bundle-skills-coverage）：旧版这里没有 "skills"，于是 bundle 里只有
# 生成版那 1 个技能，而源仓库有 2 个；bundle 内 README/ROADMAP/roles/GLOSSARY 引用的
# `skills/stop-that-shit/SKILL.md` 全是死引用，且 `--check` 因「源和 bundle 都不含」而成盲区。
COPY_DIRS = ["roles", "templates", "tools", "ops", "workflow", "skills"]
# cordis.patch.yml 是**静态内容**（不含版本号），从源仓库逐字节复制：
# 之前它在 build_bundle.py 里另存一份常量，结果源文件早改成 baseUrl 写法、常量还停在
# 读 DSH_PROFILE_DIR 的旧版，bundle 一重建就把旧写法带回来（J 套「patch 用独立 provider
# 且不残留旧环境变量」当场变红）。版本号才是唯一版本源（VERSION），patch 不是。
COPY_FILES = ["README.md", "MIGRATION.md", "ROADMAP.md", "GLOSSARY.md", "cordis.patch.yml"]
SKIP_NAMES = {"__pycache__", ".pytest_cache"}
# 由脚本生成（内容经过加工）的文件：内容单独校验，不参与「源↔bundle」sha256 比对，
# 也不走 build() 的复制循环。注意 `skills/dsh-multi-role-flow/SKILL.md` **在源仓库里有同名文件**，
# 但 bundle 里那一份是 `_skill_text()` 生成的（分发头 + 占位符替换）→ 必然不同，所以必须登记在这里。
GENERATED = ("package.json", "BUNDLE-README.md",
             "skills/dsh-multi-role-flow/SKILL.md")

PACKAGE_JSON = """{
  "name": "dsh-multi-role-flow",
  "version": "%s",
  "private": true,
  "type": "module",
  "description": "DSH 多角色协作开发流程：角色说明书 / 模板 / 状态机工具 + dsh-multi-role-flow 技能（安装后技能目录可见）",
  "files": [
    "cordis.patch.yml",
    "skills/",
    "roles/",
    "templates/",
    "tools/",
    "ops/",
    "workflow/",
    "README.md",
    "MIGRATION.md",
    "ROADMAP.md",
    "GLOSSARY.md"
  ],
  "dsh": {
    "bundle": {
      "patch": "./cordis.patch.yml"
    }
  }
}
""" % VERSION

BUNDLE_README = """# dsh-multi-role-flow（可分发 bundle）

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
powershell -NoProfile -ExecutionPolicy Bypass -File tools\\install.ps1 -Project "D:\\你的项目"
```

## 已知限制

- skill 提供方用 `!!js` 读 `process.env.DSH_PROFILE_DIR` 拼包路径；若宿主环境没有该变量，安装会报激活失败——此时改用 `install.ps1` 的项目级安装。
- bundle 自带的技能与项目 `.dsh/skills` 下的同名技能可能同时出现；DSH 按扫描优先级取一个，内容相同不冲突。
"""


def _iter_copy(src: Path):
    for p in sorted(src.rglob("*")):
        if p.is_dir():
            continue
        if any(part in SKIP_NAMES for part in p.parts):
            continue
        if p.suffix == ".pyc":
            continue
        yield p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copied_files() -> "dict[str, Path]":
    """产物清单里「从源仓库逐字节复制」的文件：{bundle 内相对路径(posix): 源文件}。

    build() 与 check() 共用同一份清单，避免两边口径漂移（G4 的坑就是 check 只看存在性）。

    `GENERATED` 里的路径**必须排除**（2026-11-22 bundle-skills-coverage）：`COPY_DIRS` 收录
    `skills/` 之后，`skills/dsh-multi-role-flow/SKILL.md` 会被枚举进来，但它是由 `_skill_text()`
    生成的（插分发头 + 占位符替换），与源技能**必然不同**；留在比对集里会让 `--check` 永远红。
    生成版的内容由 `check()` 里单独的「期望内容比对」把关，强度不降。
    """
    out: "dict[str, Path]" = {}
    for d in COPY_DIRS:
        src = PKG / d
        if not src.is_dir():
            continue
        for p in _iter_copy(src):
            out[p.relative_to(PKG).as_posix()] = p
    for f in COPY_FILES:
        src = PKG / f
        if src.is_file():
            out[f] = src
    for g in GENERATED:
        out.pop(g, None)
    return out


def _skill_text() -> str:
    """bundle 里 `skills/dsh-multi-role-flow/SKILL.md` 的**期望内容**（源技能 + 分发头 + 占位符替换）。"""
    skill_src = PKG / "skills" / "dsh-multi-role-flow" / "SKILL.md"
    text = skill_src.read_text(encoding="utf-8")
    text = text.replace("{{PACKAGE}}", "<流程包根>")
    header = ("> 本技能随 `dsh-multi-role-flow` bundle 分发：**流程包根 = 本技能目录向上两级**"
              "（`<skill base>/../..`，即 bundle 根目录）；`$FLOW` = `<流程包根>/tools/dsh_flow.py`。\n")
    if text.startswith("---"):
        end = text.find("\n---", 4)
        front = text[:end + 4]
        body = text[end + 4:]
        text = front + "\n\n" + header + body
    else:
        text = header + text
    return text


def build() -> None:
    # 删除守卫（L009 / 2026-11-20 事故同族）：校验必须在**任何**写盘/删除之前，
    # 且不只在 `BUNDLE.exists()` 时校验——目录不存在也会往那里写产物，浅路径同样要拒。
    # 守卫只做判定（不通过就 sys.exit(2)），不改写 BUNDLE：`abspath` 归一与 `rmtree`
    # 对同一目标等价，保持单一变量口径更不容易漂移。
    guard_bundle_dir(BUNDLE)
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    BUNDLE.mkdir(parents=True)
    (BUNDLE / "package.json").write_text(PACKAGE_JSON, encoding="utf-8", newline="\n")
    (BUNDLE / "BUNDLE-README.md").write_text(BUNDLE_README, encoding="utf-8", newline="\n")

    for d in COPY_DIRS:
        src = PKG / d
        if not src.is_dir():
            continue
        for p in _iter_copy(src):
            rel = p.relative_to(PKG)
            if rel.as_posix() in GENERATED:
                # 生成版（技能正文）不先复制再覆盖：只由下面那一次写盘产生，避免中间态
                # 与「复制成功的错觉」（`_skill_text()` 的产出与源技能必然不同）。
                continue
            dest = BUNDLE / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
    for f in COPY_FILES:
        src = PKG / f
        if src.is_file():
            shutil.copy2(src, BUNDLE / f)

    dest_skill = BUNDLE / "skills" / "dsh-multi-role-flow" / "SKILL.md"
    dest_skill.parent.mkdir(parents=True, exist_ok=True)
    dest_skill.write_text(_skill_text(), encoding="utf-8", newline="\n")

    n = len([p for p in BUNDLE.rglob("*") if p.is_file()])
    print(f"✓ bundle 已构建：{BUNDLE}")
    print(f"  文件 {n} 个，版本 {VERSION}")


def check(bundle: "Path | None" = None) -> int:
    """检查 dsh-bundle 是否存在、关键文件齐全，且**内容与源仓库逐文件一致**（不重建）。

    `bundle`：只读检查的**目标目录**（C002 / N-06：selftest 的 J 套反向探针要改字节、塞多余文件，
    以前直接改真 bundle，两个 selftest 并发时互相踩 → 间歇性假失败）。传了就覆盖 `BUNDLE`；
    不传时行为与旧版**完全一致**（包括最后一行打印的路径）——`build()` 不看这个参数。

    G4（E19 ⑥）：1.1.0 之前的 check 只验证「关键文件存在 + package.json 关键字 + 技能无占位符」，
    所以 bundle 陈旧到 `tools/dsh_flow.py` 110149B（源 175074B）、`ops/lessons.md` 根本不存在
    也照样通过——这个坑就是这么埋的。现在加两条硬判据：
      ① 源 ↔ bundle 逐文件 sha256 比对（COPY_DIRS + COPY_FILES + 技能文件）；
      ② 多余文件检测（bundle 里出现不在产物清单内的文件）。
    `--dir` 只换「被检查的目录」，判据与产物清单一律仍以源仓库为准（所以副本也能验）。
    """
    target = BUNDLE if bundle is None else Path(bundle)
    need = ["package.json", "cordis.patch.yml", "tools/dsh_flow.py",
            "roles/00-lead.md", "skills/dsh-multi-role-flow/SKILL.md"]
    if not target.is_dir():
        print(f"✗ bundle 目录不存在：{target}")
        return 1
    missing = [x for x in need if not (target / x).exists()]
    if missing:
        print("✗ bundle 缺少：" + ", ".join(missing))
        return 1
    pkg = (target / "package.json").read_text(encoding="utf-8")
    if "dsh-multi-role-flow" not in pkg or "cordis.patch.yml" not in pkg:
        print("✗ bundle package.json 不完整")
        return 1
    skill = (target / "skills" / "dsh-multi-role-flow" / "SKILL.md").read_text(encoding="utf-8")
    if "{{PACKAGE}}" in skill:
        print("✗ bundle 技能仍有 {{PACKAGE}} 占位符")
        return 1

    # ① 源 ↔ bundle 逐文件 sha256（陈旧但存在 → 必须红）
    expected = _copied_files()
    if not expected:
        print("✗ 产物清单为空：源仓库目录结构不符合预期")
        return 1
    absent, stale = [], []
    for rel in sorted(expected):
        src, dst = expected[rel], target / rel
        if not dst.is_file():
            absent.append(rel)
            continue
        if _sha256(dst) != _sha256(src):
            stale.append(f"{rel}（源 {src.stat().st_size}B / bundle {dst.stat().st_size}B）")
    if absent:
        print(f"✗ bundle 缺少 {len(absent)} 个产物文件（源仓库有、bundle 没有）：")
        for x in absent[:20]:
            print(f"  - {x}")
    if stale:
        print(f"✗ bundle 有 {len(stale)} 个文件与源仓库内容不一致（陈旧）：")
        for x in stale[:20]:
            print(f"  - {x}")
    if absent or stale:
        print("  修法：& $PY tools/build_bundle.py 重建（已装 bundle 需先 plugin_manager remove_bundle）")
        return 1

    # 技能文件是生成的（插入分发头 + 替换占位符），按期望内容比对
    if skill != _skill_text():
        print("✗ bundle 技能文件与源技能的生成结果不一致（陈旧）：skills/dsh-multi-role-flow/SKILL.md")
        return 1

    # ② 多余文件（不在产物清单内 → 必须红）
    allowed = set(expected) | set(GENERATED)
    extra = [p.relative_to(target).as_posix() for p in sorted(target.rglob("*"))
             if p.is_file() and p.relative_to(target).as_posix() not in allowed]
    if extra:
        print(f"✗ bundle 有 {len(extra)} 个多余文件（不在产物清单内）：")
        for x in extra[:20]:
            print(f"  - {x}")
        return 1

    print(f"✓ bundle 自检通过：{target}")
    print(f"  产物 {len(expected) + len(GENERATED)} 个，逐文件 sha256 与源仓库一致（版本 {VERSION}）")
    return 0


def _arg_dir(argv: "list[str]") -> "tuple[Path | None, str]":
    """解析 `--dir <path>`：返回 (路径, 错误信息)。不存在/缺值都算参数错误（exit 2）。

    `--dir` **只在 `--check` 下有意义**；不带 `--check` 时被忽略（build() 的默认行为一字不改）。
    """
    if "--dir" not in argv:
        return None, ""
    i = argv.index("--dir")
    if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
        return None, "--dir 需要一个目录路径"
    return Path(argv[i + 1]), ""


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        target, err = _arg_dir(sys.argv[1:])
        if err:
            print(f"✗ {err}", file=sys.stderr)
            sys.exit(2)
        sys.exit(check(target))
    build()
