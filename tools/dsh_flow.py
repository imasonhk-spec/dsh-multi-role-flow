#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""dsh_flow.py —— DSH 多角色协作开发流程的状态机与候选凭证工具。

设计目标：在没有 git / 没有 worktree 的机器上，仍然让「执行线程不能自证、
验证线程只信用哈希」这条核心纪律成立。所有交接都在磁盘上留凭证。

用法（在项目根目录执行，或显式 -p 指定项目）：

  init     初始化一个 feature 的文档骨架与 state.json
  baseline 记录 E0 基线（scope 内所有文件的 sha256），用于越界审计
  freeze   把候选产物冻结到 releases/<C>/files/，自动生成 manifest.json
  verify   校验 manifest 与实际文件、证据文件是否一致（含篡改检测）
  audit    对比 baseline 与当前树，列出声明范围外的改动
  evidence 生成一条格式统一、可被 freeze 解析的证据文件
  status   打印当前阶段、候选、阻塞项、门禁状态、下一步
  scope    补正声明写范围（只追加 state.scope，不动 baseline.json）
  next     生成下一位角色的完整交接包（可直接作为 subagent prompt）
  advance  推进阶段（每个转换都过门禁，失败即拒绝）
  gate     汇总当前阶段的全部门禁检查
  drive    只读合成：phase + 门禁（硬/软）+ 下一位 + 能否推进 + 建议命令
  ledger   追加或查看台账
  doctor   自检运行环境
  lesson   跨 feature 教训库：add 追加一条 / list 只读列出（不写 state.json）

约定：docs/<feature>/ 下所有产物；候选编号 C001、C002…；证据分级 A/B/C/D。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCHEMA_STATE = "dsh-flow/state@1"
SCHEMA_BASELINE = "dsh-flow/baseline@1"
SCHEMA_MANIFEST = "dsh-flow/candidate@1"
SCHEMA_HEALTH = "dsh-flow/health@1"
TZ = timezone(timedelta(hours=8))

# 「待用户试用清单」小节：报告里常写成 `## 三、待用户试用清单`、`## 待用户试用清单（可选）`，
# 所以按「标题行 + 可选序号」包含匹配，而不是字面量 `## 待用户试用清单`（旧写法会把带序号
# 的标题误判成「缺少清单」）。仍然是标题级匹配：正文里偶然提到这几个字不算存在该节。
RE_TRIAL_CHECKLIST = re.compile(
    r"^#{1,6}[ \t]*[一二三四五六七八九十百0-9、.．，,：:\-—]*[ \t]*待用户试用清单",
    re.MULTILINE,
)

# 根级文档默认纳入 scope：它们由 Lead/planner 改，不写进 scope 的话 `audit` 一律归到
# 「不在声明写范围」，每次都要手工补 --scope。用户显式传 --scope 时是**追加**而非覆盖。
ROOT_SCOPE_DOCS = ("README.md", "ROADMAP.md", "GLOSSARY.md")

PHASES = ["DESIGN", "PLAN", "EXECUTING", "VERIFYING", "TRIAL", "DONE"]
ANOMALY_PHASES = ["ROLLED_BACK"]
PHASE_ROLE = {
    "DESIGN": "planner",
    "PLAN": "lead",
    "EXECUTING": "executor",
    "VERIFYING": "verifier",
    "TRIAL": "user",
    "DONE": "none",
    "ROLLED_BACK": "lead",
}
ROLE_FILES = {
    "lead": "00-lead.md",
    "planner": "01-planner.md",
    "executor": "02-executor.md",
    "verifier": "03-verifier.md",
    "inspector": "04-inspector.md",
}
TRANSITIONS = {
    "DESIGN": ["PLAN", "ROLLED_BACK"],
    "PLAN": ["EXECUTING", "ROLLED_BACK"],
    "EXECUTING": ["VERIFYING", "ROLLED_BACK"],
    "VERIFYING": ["TRIAL", "EXECUTING", "ROLLED_BACK"],
    "TRIAL": ["DONE", "EXECUTING", "VERIFYING", "ROLLED_BACK"],
    "DONE": ["EXECUTING"],
    "ROLLED_BACK": ["EXECUTING", "PLAN", "DESIGN"],
}
STATUS_VALUES = {"pass", "fail", "skip", "unknown"}
GRADES = {"A", "B", "C", "D"}
THREE_STATES = ["已上线可试用", "待用户试用", "完整业务验收通过"]

SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode",
    ".pytest_cache", "dist", "build", ".dsh", ".agents", ".mypy_cache", ".ruff_cache",
    # 工具缓存/索引产物：不是源码，纳入基线只会制造噪音（2026-11-20 巡检发现）
    ".gitnexus", "graphify-out", ".graphify", ".cache", ".turbo", ".next",
    # 分发产物目录（flow-audit-hygiene C001，2026-11-22）：`build_bundle.py` 每重建一次，
    # `dsh-bundle-dist/**` 就整片变哈希 → audit 报 8-9 条「未登记」假红，把真孤儿埋掉。
    # 它的新鲜度由 `build_bundle.py --check` 逐文件 sha256 对源仓库校验（比 audit 更强），
    # 所以这里只排目录、不跟踪内容；**不要**因此删改该目录里的任何文件。
    "dsh-bundle-dist",
}
MAX_HASH_BYTES = 8 * 1024 * 1024

# 封存包异地快照根（flow-backup-a，DESIGN §3.2）：
# 事故教训（2026-11-20 23:37 误删）——`manifest.json` / `verification.json` / `files/**`
# 是**工具写**的凭证，不在会话日志里，回放永远补不回来；所以 seal 成功后必须留异地副本。
# 默认落 C 盘用户目录、**不在项目内**（项目内新增文件会污染 audit / verify 的口径）。
# 优先级：`seal --backup-dir` > 环境变量 `FLOW_BACKUP_ROOT` > 这里的默认值。
DEFAULT_BACKUP_ROOT = Path.home() / ".dsh" / "flow-snapshots"
BACKUP_ROOT = Path(os.environ.get("FLOW_BACKUP_ROOT") or str(DEFAULT_BACKUP_ROOT)).expanduser()


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #

def now_iso() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def die(msg: str, code: int = 2):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)


def read_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def posix_rel(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def is_skipped(rel: str) -> bool:
    parts = rel.split("/")
    return any(p in SKIP_DIR_NAMES for p in parts[:-1])


def docs_root(project: Path, feature: str) -> Path:
    return project / "docs" / feature


def state_path(project: Path, feature: str) -> Path:
    return docs_root(project, feature) / "state.json"


def baseline_path(project: Path, feature: str) -> Path:
    return docs_root(project, feature) / "baseline.json"


def load_state(project: Path, feature: str) -> dict:
    p = state_path(project, feature)
    if not p.exists():
        die(f"没有找到 {p}，先用 init 初始化 feature。")
    st = read_json(p)
    if st.get("schema") != SCHEMA_STATE:
        die(f"state.json schema 不是 {SCHEMA_STATE}，拒绝继续。")
    return st


def save_state(project: Path, feature: str, st: dict) -> None:
    st["updated_at"] = now_iso()
    write_json(state_path(project, feature), st)


def append_history(st: dict, action: str, actor: str, detail: str) -> None:
    ts = now_iso()
    st.setdefault("history", []).append({"at": ts, "action": action, "actor": actor, "detail": detail})
    # 台账同时写一份人读的 markdown
    base = Path(st["project"]) / "docs" / st["feature"]
    base.mkdir(parents=True, exist_ok=True)
    line = f"- {ts} | {actor} | {action} | {detail}\n"
    with (base / "ledger.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write(line)


def role_doc(package: Path, role: str) -> str:
    name = ROLE_FILES.get(role)
    if not name:
        return ""
    p = package / "roles" / name
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def scope_roots(st: dict) -> list[str]:
    roots = st.get("scope") or []
    return [r.strip("/") for r in roots if r.strip()]


def iter_scope_files(project: Path, roots: list[str]):
    """遍历 scope 内的文件，返回 (relpath, abspath)。roots 为空时退化为整个项目。"""
    seen = set()
    if not roots:
        roots = ["."]
    for root in roots:
        base = project / root if root != "." else project
        if not base.exists():
            continue
        if base.is_file():
            rel = posix_rel(base, project)
            if rel not in seen:
                seen.add(rel)
                yield rel, base
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and d != "docs"]
            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    rel = posix_rel(p, project)
                except ValueError:
                    continue
                if rel in seen or is_skipped(rel):
                    continue
                seen.add(rel)
                yield rel, p


# --------------------------------------------------------------------------- #
# 门禁检查
# --------------------------------------------------------------------------- #

def _text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def check_design(base: Path) -> list[tuple[str, bool, str]]:
    t = _text(base / "DESIGN.md")
    if not t.strip():
        return [("DESIGN.md 存在且有内容", False, "文件为空或不存在")]
    status = re.findall(r"^状态\s*[：:]\s*(\S+)\s*$", t, re.MULTILINE)
    confirmed = status == ["已确认"]
    return [
        ("DESIGN.md 含『## 验收标准』", "## 验收标准" in t, "" if "## 验收标准" in t else "缺少验收标准小节"),
        ("DESIGN.md 含『## 不改什么（边界）』", "## 不改什么" in t, "" if "## 不改什么" in t else "缺少边界小节"),
        ("DESIGN.md 状态行唯一且为『状态：已确认』", confirmed,
         "需要一个独占一行的『状态：已确认』；当前状态行: " + (str(status) if status else "缺失")),
        ("DESIGN.md 无未替换占位符", "{{" not in t, "仍有 {{...}} 占位符，需填实或删掉"),
    ]


def check_plan(base: Path) -> list[tuple[str, bool, str]]:
    plan = base / "planning"
    out = []
    for fn, marker, label in [
        ("COORDINATION-PLAN.md", "## 权限矩阵", "分工与权限矩阵"),
        ("EXECUTION-WORKPLAN.md", "## 任务分解", "执行任务分解"),
        ("VALIDATION-WORKPLAN.md", "## 检查项", "验证检查项"),
        ("SOURCE-PLAN.md", "", "需求来源登记"),
    ]:
        p = plan / fn
        t = _text(p)
        ok = bool(t.strip()) and (not marker or marker in t)
        detail = "文件缺失或为空" if not t.strip() else (f"缺少『{marker}』小节" if marker and marker not in t else "")
        out.append((f"planning/{fn} ({label})", ok, detail))
    return out


def check_frozen_candidate(base: Path, st: dict) -> list[tuple[str, bool, str]]:
    cid = st.get("current_candidate")
    if not cid:
        return [("存在已冻结候选", False, "state.current_candidate 为空，先 freeze")]
    manifest = base / "releases" / cid / "manifest.json"
    if not manifest.exists():
        return [(f"候选 {cid} 的 manifest.json", False, "文件不存在")]
    errors = verify_manifest(base, cid)
    return [(f"候选 {cid} manifest 校验", not errors, "; ".join(errors[:5]))]


def check_report(base: Path, st: dict) -> list[tuple[str, bool, str]]:
    cid = st.get("current_candidate")
    if not cid:
        return [("存在当前候选", False, "state.current_candidate 为空")]
    p = base / "releases" / cid / "RELEASE-REPORT.md"
    t = _text(p)
    if not t.strip():
        return [(f"候选 {cid} 的 RELEASE-REPORT.md", False, "文件为空或不存在")]
    has_checklist = bool(RE_TRIAL_CHECKLIST.search(t))
    out = [("发布报告含『待用户试用清单』小节（允许带序号）", has_checklist,
            "" if has_checklist else "缺少待用户试用清单（须是独占一行的标题，如 `## 三、待用户试用清单`）")]
    m = re.search(r"^结论\s*[：:]\s*(已上线可试用|待用户试用|完整业务验收通过)\s*$", t, re.MULTILINE)
    out.append(("发布报告结论行唯一且为三态之一", bool(m), "需要独占一行的『结论：已上线可试用|待用户试用|完整业务验收通过』"))
    out.append(("发布报告无未替换占位符", "{{" not in t, "仍有 {{...}} 占位符，说明没真正填写"))
    return out


def check_acceptance(base: Path) -> list[tuple[str, bool, str]]:
    t = _text(base / "ACCEPTANCE.md")
    m = re.search(r"^用户结论\s*[：:]\s*(通过|不通过|待用户试用)\s*$", t, re.MULTILINE)
    ok = bool(m) and m.group(1) == "通过" and "{{" not in t
    detail = "需要独占一行的『用户结论：通过』（用户真的试用过）；占位符要填实" if not ok else ""
    return [("验收台账含『用户结论：通过』", ok, detail)]


def _fetch_json(url: str, timeout: float = 10.0) -> tuple[int, dict | str]:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "dsh-flow/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
            status = getattr(r, "status", 200)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:  # 连接失败、超时、DNS 等
        return 0, f"{type(e).__name__}: {e}"
    try:
        return status, json.loads(raw)
    except Exception:
        return status, raw


def _dig(data, path: str):
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _norm_version(v) -> str:
    return str(v or "").strip().lower().lstrip("v")


def manifest_runtime(base: Path, cid: str) -> dict:
    mp = base / "releases" / cid / "manifest.json"
    if not mp.exists():
        return {}
    try:
        rt = read_json(mp).get("runtime") or {}
    except Exception:
        return {}
    return rt if isinstance(rt, dict) and rt.get("kind") not in (None, "", "none") else {}


PACK_MANIFESTS = ("package.json", "pack/package.json", "plugin/package.json")


def detect_pack(project: Path) -> dict | None:
    """识别插件/能力包项目。

    只看 `package.json` 的 `dsh.capabilityPack` / `dsh.bundle`（以及常见的
    `pack/`、`plugin/` 子目录布局）。返回 None 表示不是能力包项目。
    用途：插件/服务类项目如果 `freeze` 没声明 runtime，装完无法做版本握手，
    这种候选要给出告警，而不是静默通过。
    """
    for rel in PACK_MANIFESTS:
        p = project / rel
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        dsh = data.get("dsh") if isinstance(data.get("dsh"), dict) else {}
        kind = "capabilityPack" if "capabilityPack" in dsh else ("bundle" if "bundle" in dsh else None)
        if not kind:
            continue
        return {
            "path": p.as_posix(),
            "name": data.get("name"),
            "version": (str(data.get("version") or "")).strip(),
            "kind": kind,
        }
    return None


def check_runtime(base: Path, st: dict) -> list[tuple[str, bool, str]]:
    """候选声明了 runtime（插件/服务/CLI）时，必须做过版本握手且实际版本匹配。"""
    cid = st.get("current_candidate")
    if not cid:
        return []
    rt = manifest_runtime(base, cid)
    if not rt:
        return []
    rec = ((st.get("candidates") or {}).get(cid) or {}).get("runtime") or {}
    want = rt.get("version")
    ok = bool(rec.get("ok")) and _norm_version(rec.get("actual")) == _norm_version(want)
    detail = ""
    if not ok:
        detail = ("需先跑 `flow.py handshake --id %s --url <%s> --expect %s`，且实际版本与 manifest.runtime.version 一致"
                  % (cid, rt.get("health_url") or "<健康检查地址>", want))
        if rec and not rec.get("ok"):
            detail += f"；最近一次握手实际={rec.get('actual')!r} ok={rec.get('ok')}"
    return [(f"运行时版本已握手（期望 {want}）", ok, detail)]


def verify_verification(base: Path, cid: str) -> list[str]:
    """校验 verification.json：封存后是否被改过、是否有新增文件。"""
    errors: list[str] = []
    vp = base / "releases" / cid / "verification.json"
    if not vp.exists():
        return ["verification.json 不存在"]
    try:
        v = read_json(vp)
    except Exception as e:
        return [f"verification.json 无法解析: {e}"]
    if v.get("schema") != "dsh-flow/verification@1":
        errors.append(f"verification.schema 应为 dsh-flow/verification@1，实际 {v.get('schema')!r}")
    files = v.get("files") or []
    listed: set[str] = set()
    for f in files:
        rel = f.get("path")
        if not rel:
            errors.append("verification.files 条目缺少 path")
            continue
        listed.add(rel)
        p = base.parent.parent / rel
        if not p.exists():
            errors.append(f"封存文件不存在: {rel}")
            continue
        if sha256_file(p) != f.get("sha256"):
            errors.append(f"封存后内容被改: {rel}")
        if f.get("bytes") is not None and p.stat().st_size != f.get("bytes"):
            errors.append(f"封存后大小变化: {rel}")
    ev_dir = base / "evidence" / cid
    if ev_dir.exists():
        for p in ev_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = posix_rel(p, base.parent.parent)
            if rel not in listed:
                errors.append(f"封存后新增证据文件: {rel}")
    return errors


def check_seal(base: Path, st: dict) -> list[tuple[str, bool, str]]:
    cid = st.get("current_candidate")
    if not cid:
        return []
    mp = base / "releases" / cid / "manifest.json"
    if not mp.exists():
        return []
    try:
        m = read_json(mp)
    except Exception:
        return []
    if not m.get("seal_required"):
        return []
    vp = base / "releases" / cid / "verification.json"
    if not vp.exists():
        return [("验证证据已封存（verification.json）", False,
                 f"未 seal：先跑 `flow.py seal --id {cid}`。manifest.evidence 只覆盖冻结时的 P*，"
                 "V* 证据 / 发布报告 / 部署台账必须靠 verification.json 封存，否则无法证明「装的是哪一版」。")]
    errs = verify_verification(base, cid)
    return [("封存校验（verification.json）", not errs, "; ".join(errs[:3]))]


def gate_for(project: Path, feature: str, target_phase: str) -> list[tuple[str, bool, str]]:
    base = docs_root(project, feature)
    st = load_state(project, feature)
    if target_phase == "PLAN":
        return check_design(base)
    if target_phase == "EXECUTING":
        return check_design(base) + check_plan(base)
    if target_phase == "VERIFYING":
        return check_plan(base) + check_frozen_candidate(base, st)
    if target_phase == "TRIAL":
        return (check_frozen_candidate(base, st) + check_report(base, st)
                + check_runtime(base, st) + check_seal(base, st))
    if target_phase == "DONE":
        return check_report(base, st) + check_acceptance(base) + check_runtime(base, st)
    return []


# --------------------------------------------------------------------------- #
# 软告警（DESIGN §5.3 / §5.7）：返回 (标签, 明细) 二元组
# --------------------------------------------------------------------------- #
# **类型上就进不了门禁**：没有布尔位，所以不可能被 `all(ok for _, ok, _ in checks)` 吃掉。
# 只被 cmd_gate / cmd_status / cmd_drive 打印，永不出现在 gate_for() 的返回值里。
RE_GRAPH_EVIDENCE = re.compile(r"project_path|get_neighbors|god_nodes|graph_stats|未建图")


def _section_body(text: str, heading_prefix: str) -> "str | None":
    """按**前缀**取 `##` 级小节的正文（到下一个同级标题为止）；小节不存在返回 None。

    必须用前缀匹配：既有文档实际写成 `## 受影响文件（E11）`，字面全等会漏（DESIGN §5.7）。
    只看该节正文、不看全文——否则只要别处提过一次图谱参数就永远不告警。
    """
    lines = text.splitlines()
    pat = re.compile(r"^##\s*" + re.escape(heading_prefix))
    start = None
    for i, ln in enumerate(lines):
        if start is None:
            if pat.match(ln):
                start = i + 1
            continue
        if re.match(r"^##\s", ln):
            return "\n".join(lines[start:i])
    return None if start is None else "\n".join(lines[start:])


# --------------------------------------------------------------------------- #
# 文档类候选判据（C007 / DESIGN §六 边界）：纯文档候选没有代码行为可写 P 证据，
# 硬要求只会逼人造假（C006 验证线程原话：「没有对应代码行为可写 P 证据，补了就是造假」）。
# --------------------------------------------------------------------------- #
# 判据只看 `manifest.artifacts[].path` 的**扩展名**，不看 `role` 字段：
# `role` 是 `_guess_role()` 按目录/名称猜的（.json → config、.svg → asset），
# 而「有没有可执行行为」是**文件类型**问题——手写一份 .json 配置，一行代码行为都没有。
# 混合候选（哪怕只有一个 .py/.js）仍算代码候选：那份代码的行为确实需要 P 证据。
CODE_SUFFIXES = (
    ".py", ".pyw", ".pyi", ".ipynb",
    ".js", ".mjs", ".cjs", ".jsx", ".ts", ".mts", ".cts", ".tsx",
    ".ps1", ".psm1", ".psd1", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".exe", ".dll", ".so", ".dylib", ".node", ".wasm", ".jar", ".class",
    ".go", ".rs", ".java", ".kt", ".kts", ".cs", ".fs", ".vb",
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".m", ".mm",
    ".rb", ".php", ".pl", ".pm", ".lua", ".r", ".jl", ".scala", ".swift",
    ".sql", ".tf", ".gradle",
)
# 代码类以外一律算文档类（.md/.txt/.json/.yml/.yaml/.csv/.svg/.html/.css/.toml/.ini …），
# 所以上面这份清单**就是**唯一的判据源：往里加扩展名 = 收紧「文档类」的适用范围。
#
# P 证据 check_id 的合法形态（C008 修）：`P29` 与 `P29-doc-only-candidate` **两种都认**。
# 为什么不用「前缀匹配 `P\d+.*`」：那等于任何 `P<数字>…` 都算，没有可核对的边界；
# 为什么不用「纯 `P\d+`」：`roles/02-executor.md` 的命名规范就是 `P<编号>-<短名>.md`，
# 收紧成纯数字会把**正常格式**误杀（C007 实测：该候选自己的 P 证据被判「不存在」）。
RE_P_CHECK_ID = re.compile(r"P\d+(?:-[A-Za-z0-9._-]+)?")


def _doc_only_candidate(manifest: dict) -> "tuple[bool, str]":
    """候选是否「纯文档」（产物里一个代码/可执行类扩展名都没有）。

    返回 `(是否文档类, 原因/产物统计)`；第二个返回值给 `warn_for()` 的 ⚠ 行与 `selftest`
    直接使用，不需要调用方再拼字符串（也保证两处措辞不会漂）。

    边界（DESIGN §六）：
    - 产物清单**为空** → 判不了，按代码候选处理（宁可多报，不静默放过）；
    - 混合候选（同时含 `.md` 与 `.py`）→ 代码候选（P* 证据仍要）；
    - `.json` / `.yml` 算文档类（配置），`.node` / `.wasm` / `.dll` 算代码类（可执行）。
    """
    arts = manifest.get("artifacts") or []
    paths = [str((a or {}).get("path") or "")
             for a in arts if isinstance(a, dict)]
    paths = [p for p in paths if p]
    if not paths:
        return False, "产物清单为空，无法判定文档类（按代码候选处理）"
    code = [p for p in paths if p.lower().endswith(CODE_SUFFIXES)]
    if code:
        return False, f"{len(code)}/{len(paths)} 个产物是代码类（如 {code[0]}）"
    exts = sorted({(p.rsplit(".", 1)[-1].lower() if "." in p.rsplit("/", 1)[-1] else "(无扩展名)")
                   for p in paths})
    return True, f"{len(paths)} 个产物均非代码类（扩展名：{'/'.join(exts[:8])}）"


# --------------------------------------------------------------------------- #
# **主判据（Lead 2026-11-21 裁决）**：相邻候选的**变更集**里有没有代码类文件。
# --------------------------------------------------------------------------- #
# 为什么不能只用「产物全量扩展名」：本项目 `freeze --scope .` 是**整包冻结**，每个候选都
# 固定带着 `tools/*.py`、`templates/plugin-pack/*.js` 等 8 个代码类产物——哪怕这一轮只改
# 文档，全量判据也永远判「代码候选」，于是「纯文档候选免 P* 」这条规则在本项目**零收益**
# （C006 实测 8/48 个代码类产物）。判据必须看「**这一轮改了什么**」，而不是「包里有什么」。
# 全量扩展名判据降级为回退：只有**没有相邻候选可对照**（首个候选）时才用它。
#
# 四态（R01 评审 §二.2 裁决后收紧，**别把 None 和 False 混为一谈**）：
#   "delta"    → True/False：有变更集，按代码类命中数判；
#   "zero"     → None：产物集与上一候选**逐字节相同**（零变更）→ 判不了，走**独立告警**；
#                为什么不能判 False：`docs/` 在 `freeze` 里是结构性排除的（`iter_scope_files`
#                的 `d != "docs"` + `cmd_freeze` 的 `startswith("docs/")`），所以「只改 docs/」
#                的候选产物集必然无变化——判 False 恰好把本规则最想救的那类打成要有 P*。
#   "no_prev"  → None：首个候选，没有对照 → 回退全量扩展名判据；
#   "no_sha"   → None：任一侧某条 sha256 为空（>8MB 被跳过 / manifest 残缺）→ 判不了，
#                不能把「两边都是空」当成「未修改」（R01 §二.6 E2：唯一可能漏报的点）。
DOC_ONLY_NO_PREV = "无相邻候选可对照，回退全量扩展名判据"
DOC_ONLY_ZERO_DELTA = "产物集与上一候选逐字节相同（零变更），本判据不适用"
DOC_ONLY_NO_SHA = "产物 sha256 缺失（>8MB 被跳过或 manifest 残缺），判不了"


def _prev_frozen_candidate(base: Path, cid: str) -> str:
    """`cid` **之前最近的已冻结候选**（按 C 编号**数值序**，只认有 manifest.json 的目录）。

    必须按数值比：`sorted()` 的字典序会把 `C1000` 排在 `C101` 之前（R01 §四.5 的坑），
    跨过 C999 之后就会选错对照物。
    """
    rel = base / "releases"
    if not rel.is_dir():
        return ""
    nums = re.sub(r"\D", "", cid or "")
    if not nums:
        return ""
    limit = int(nums)
    best, best_n = "", -1
    for d in rel.iterdir():
        if not d.is_dir() or not re.fullmatch(r"C\d{3,}", d.name):
            continue
        if not (d / "manifest.json").is_file():
            continue
        n = int(re.sub(r"\D", "", d.name))
        if n < limit and n > best_n:
            best, best_n = d.name, n
    return best


def _artifact_shas(base: Path, cid: str) -> "dict[str, str]":
    """`{path: sha256}`：读不到 manifest 时返回空字典（调用方按「判不了」处理）。"""
    mp = base / "releases" / cid / "manifest.json"
    try:
        arts = (read_json(mp) or {}).get("artifacts") or []
    except Exception:
        return {}
    out: "dict[str, str]" = {}
    for a in arts:
        if isinstance(a, dict) and a.get("path"):
            out[str(a["path"])] = str(a.get("sha256") or "")
    return out


DOC_JS_HEAD_BYTES = 65536          # 内容覆盖面只读前 64KB（大文件不整读）
# 只有**能装配可执行 JS 的配置格式**才做内容层检查。为什么不能对所有非代码文件查 `!!js`：
# `ROADMAP.md` / `ops/*.md` 的正文里**提到**了 `!!js` 这个标签（解释 Cordis 用法），
# 一次实测就把它们误判成代码类（假阳性）。文档提到标签 ≠ 可执行。
DOC_JS_TAG_SUFFIXES = (".yml", ".yaml", ".json", ".jsonc", ".toml")


def _js_tag_paths(base: Path, owners: "list[tuple[str, str]]") -> "list[str]":
    """`[(候选, 产物路径)]` 里**内容含 `!!js` 标签**的那些路径。

    R01 §二.8 的实测反例：根 `cordis.patch.yml` 里嵌着真 JS
    （`- !!js "process.getBuiltinModule(...).resolve('dsh-multi-role-flow/package.json')"`），
    它决定**从哪个目录加载 skills**——改它就是改运行时行为，但按扩展名 `.yml` 会被判「文档类」
    → 真实漏报口子。所以扩展名判据之后必须有这一层内容覆盖（`QC_JS_TAG` 常量复用，不另造）。

    **只查 `DOC_JS_TAG_SUFFIXES`**（YAML/JSON 一类能装配 JS 的配置），不查 `.md`：
    文档正文里提到 `!!js` 不构成可执行行为（实测假阳性来源）。
    """
    hits: "list[str]" = []
    tag = QC_JS_TAG.encode()
    for owner, rel in owners:
        if not rel.lower().endswith(DOC_JS_TAG_SUFFIXES):
            continue
        p = base / "releases" / owner / "files" / rel
        try:
            with p.open("rb") as fh:
                head = fh.read(DOC_JS_HEAD_BYTES)
        except OSError:
            continue
        if tag in head:
            hits.append(rel)
    return hits


def _doc_only_delta(base: Path, cid: str) -> "tuple[bool | None, str, str]":
    """候选的**变更集**里有没有代码类文件（相邻候选对照）。

    返回 `(判定, 说明, 种类)`，种类 ∈ `{"delta","zero","no_prev","no_sha"}`：
    - `(True,  …, "delta")`  → 文档类：变更集非空且代码类命中 0 个；
    - `(False, …, "delta")`  → 代码候选：变更集含代码类；
    - `(None,  …, "zero")`   → 零变更（产物集逐字节相同）→ 判不了，走**独立告警**；
    - `(None,  …, "no_prev")`→ 首个候选，回退全量扩展名判据；
    - `(None,  …, "no_sha")` → sha256 缺失，判不了，回退全量扩展名判据。

    变更集 = 新增（只在 cid 里）+ 修改（同名不同 sha256）+ 删除（只在 prev 里）
            + 重命名（sha256 相同但 path 不同，**单列**，不混进「删除」）。
    **删除/重命名的旧侧按它原来那个 path 的扩展名判代码类**（删掉一个 `.py` 就是代码类变更）：
    删代码 = 行为变了，与「改代码」同罪。分类取新旧两侧**并集**（任一侧代码类即代码类，保守）。
    """
    prev = _prev_frozen_candidate(base, cid)
    if not prev:
        return None, f"{DOC_ONLY_NO_PREV}（{cid} 是首个已冻结候选）", "no_prev"
    cur = _artifact_shas(base, cid)
    old = _artifact_shas(base, prev)
    if not cur or not old:
        return None, f"{DOC_ONLY_NO_PREV}（{prev} 或 {cid} 的 manifest.artifacts 为空）", "no_prev"
    if "" in cur.values() or "" in old.values():
        # R01 §二.6 E2：空 sha 两边相等 → 会被当成「未修改」静默漏报，必须判不了
        return None, f"{DOC_ONLY_NO_SHA}（{prev} 或 {cid}）", "no_sha"

    added = sorted(set(cur) - set(old))
    deleted = sorted(set(old) - set(cur))
    modified = sorted(p for p in set(cur) & set(old) if cur[p] != old[p])

    # 重命名：sha256 相同 + path 不同（纯改名 / 整包搬迁）→ 单列，避免「删除 40+」吓人
    del_by_sha: "dict[str, list[str]]" = {}
    for p in deleted:
        del_by_sha.setdefault(old[p], []).append(p)
    renamed: "list[tuple[str, str]]" = []
    added_rest: "list[str]" = []
    for p in added:
        bucket = del_by_sha.get(cur[p])
        if bucket:
            renamed.append((bucket.pop(0), p))
        else:
            added_rest.append(p)
    renamed_old = {a for a, _ in renamed}
    deleted_rest = [p for p in deleted if p not in renamed_old]

    changed = added_rest + modified + deleted_rest + [x for pair in renamed for x in pair]
    if not changed:
        return None, f"{DOC_ONLY_ZERO_DELTA}（对照 {prev}）", "zero"

    # 内容覆盖：变更集里**能装配 JS 的配置**含 `!!js` → 算代码类（文档正文提到标签不算）
    owners = [(prev if p in old and p not in cur else cid, p) for p in changed]
    js_hits = _js_tag_paths(base, owners)
    by_ext = [p for p in changed if p.lower().endswith(CODE_SUFFIXES)]
    code = sorted(set(by_ext) | set(js_hits))

    stat = (f"变更集 {len(changed)} 个文件（新增 {len(added_rest)} / 修改 {len(modified)} / "
            f"删除 {len(deleted_rest)} / 重命名 {len(renamed)}），对照 {prev}")
    if abs(len(cur) - len(old)) > 20:
        # R01 §二.7：manifest 没记 scope，产物数差异过大时明确「结论仅供参考」
        stat += f"；产物数差 {abs(len(cur) - len(old))}，可能 scope 不同，结论仅供参考"
    if code:
        # 只有「靠内容层才判成代码类」的才标注，扩展名本身就是代码的不加噪
        content_only = [p for p in js_hits if p not in by_ext]
        extra = f"（含 `!!js` 内容：{content_only[0]}）" if content_only else ""
        return False, f"{stat}，其中代码类 {len(code)} 个（如 {code[0]}{extra}）", "delta"
    shown = "/".join(changed[:6]) + ("…" if len(changed) > 6 else "")
    return True, f"{stat}，代码类 0 个（{shown}）", "delta"


def _doc_only_verdict(manifest: dict, base: Path, cid: str) -> "tuple[bool | None, str, str]":
    """对外唯一入口：主判据（变更集）→ 判不了时回退全量扩展名判据。

    返回 `(判定, 说明, 种类)`；种类 ∈ `{"delta","zero","fallback"}`。
    - `"zero"`  → 判定为 None：**零变更**，必须打**独立告警**，不许并进「缺 P* 证据」；
    - `"fallback"` → 首个候选 / sha 缺失，用全量扩展名判据，说明里明示「回退」；
    - `"delta"` → 主判据，说明里带「判据：变更集」。
    说明里**必须**能看出来用的是哪条判据，否则读者分不清「免检是因为没改代码」还是「包里本来没代码」。
    """
    doc_only, why, kind = _doc_only_delta(base, cid)
    if kind == "zero":
        return None, why, "zero"
    if doc_only is None:
        fb, why_full = _doc_only_candidate(manifest)
        return fb, f"{why} → {why_full}", "fallback"
    return doc_only, f"{why}（判据：变更集）", "delta"


def _has_p_evidence(base: Path, manifest: dict, cid: str) -> "tuple[bool, str]":
    """E1 口径（C008 修正）：`check_id` 必须是**纯** `P<数字>` 或 `P<数字>-<短名>`，
    **且**证据文件真实存在于 `evidence/<候选>/` 下。两步都满足才算「有 P 证据」。

    历史（两版都错过，别再改回去）：
    - 旧写法 `re.fullmatch(r"P\\d+.*", i)` 是**前缀**匹配——写一份 `P33-随便写.md` 就能静默关掉
      告警，与「那份证据是否真对应本候选的代码行为」无关；
    - C007 把它收紧成 `re.fullmatch(r"P\\d+", i)` **收得过头**：`roles/02-executor.md` 的命名
      规范是 `P<编号>-<短名>.md`，`parse_evidence()` 取到的 check_id 就是 `P29-doc-only-candidate`
      这种**带短名**的形态 → 正常格式被误杀，C007 冻结后反而报「缺执行线程侧 P* 证据」。
    - **现在**：两种格式都认（`P29` / `P29-doc-only-candidate`）。

    真正防伪造的是**第二步**（文件必须真实存在、且就在本候选的 `evidence/<cid>/` 下）：
    analyst 说的「写一份 P33-随便写.md 就能关掉告警」防的是**空有名字没有文件**；有文件才会过，
    前后缀都不构成漏洞。
    """
    ev = [e for e in (manifest.get("evidence") or []) if isinstance(e, dict)]
    ids = [str(e.get("check_id") or "") for e in ev]
    ev_dir = base / "evidence" / cid
    for e in ev:
        check_id = str(e.get("check_id") or "")
        if not RE_P_CHECK_ID.fullmatch(check_id):
            continue
        raw = str(e.get("file") or "")
        if not raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = base.parent.parent / raw          # manifest 里记的是项目相对路径
        if not p.is_file():
            alt = ev_dir / Path(raw).name         # 兜底：只记了文件名
            p = alt if alt.is_file() else p
        if p.is_file() and ev_dir in p.parents:
            return True, check_id
    return False, "、".join(ids) or "空"


def warn_for(project: Path, feature: str) -> "list[tuple[str, str]]":
    """A5 + D1 + D2 + E1 四条软告警（DESIGN §二 A5 / D 组 / §六 证据链）。

    告警只出现在 `⚠` 行：不进「门禁 N/M」计数、不进 `✗`、不影响 `gate` / `drive` 退出码。
    """
    base = docs_root(project, feature)
    st = load_state(project, feature)
    out: "list[tuple[str, str]]" = []
    cid = st.get("current_candidate") or ""

    # A5 静态检查：只在当前候选的 QC 证据存在且结果为 fail 时告警（文件缺失不告警、不报错）
    if cid:
        qc = base / "evidence" / cid / "QC-static.md"
        if qc.is_file():
            txt = _text(qc)
            m = re.search(r"结果\s*[：:]\s*(pass|fail|skip|unknown)", txt)
            if m and m.group(1).lower() == "fail":
                fails = [ln for ln in txt.splitlines()
                         if ln.startswith("|") and re.search(r"\|\s*fail\s*\|", ln)]
                cats: "list[str]" = []
                for ln in fails:
                    cols = [c.strip() for c in ln.strip().strip("|").split("|")]
                    if len(cols) >= 2 and cols[1] and cols[1] not in cats:
                        cats.append(cols[1])
                out.append(("静态检查",
                            f"{len(fails)} 个文件失败（类：{'/'.join(cats) or '?'}），"
                            f"明细见 evidence/{cid}/QC-static.md"))

    # D1 EXECUTION-PLAN『受影响文件』：节不存在 → 不告警（还没到写影响面的阶段）
    ep = base / "EXECUTION-PLAN.md"
    if ep.is_file():
        body = _section_body(_text(ep), "受影响文件")
        if body is not None and not RE_GRAPH_EVIDENCE.search(body):
            out.append(("图谱证据·EXECUTION-PLAN",
                        "『受影响文件』未写图谱参数也未写「未建图」"
                        "（依据 ops/code-graph.md §4/§6）"))

    # D2 RELEASE-REPORT『核验结果』：无当前候选 → 不检查
    if cid:
        rp = base / "releases" / cid / "RELEASE-REPORT.md"
        if rp.is_file():
            body = _section_body(_text(rp), "核验结果")
            if body is not None and not RE_GRAPH_EVIDENCE.search(body):
                out.append(("图谱证据·RELEASE-REPORT",
                            f"候选 {cid}『核验结果』未写图谱参数也未写「未建图」"
                            "（依据 ops/code-graph.md §6）"))

    # E1 执行线程侧 P* 证据（DESIGN §六）：C001 只登记了自动生成的 QC-static，
    # P1..P17 一份都没有，验证线程据此判「证据链不完整」。这里做成**软告警**（只 ⚠、不阻断）：
    # 硬要求写在 roles/02-executor.md（freeze 之前必须先写 P* 证据），门禁不放这一条。
    if cid:
        man = base / "releases" / cid / "manifest.json"
        if man.is_file():
            try:
                manifest = read_json(man) or {}
            except Exception:
                manifest = {}
            has_p, ids_txt = _has_p_evidence(base, manifest, cid)
            if not has_p:
                # C007 裁决：主判据 = 相邻候选**变更集**；判不了才回退全量扩展名。
                doc_only, why, kind = _doc_only_verdict(manifest, base, cid)
                if kind == "zero":
                    # 零变更是**流程事故**，不是「本轮没改代码」——独立一条，别混进「缺 P*」里。
                    out.append(("零变更", f"候选 {cid}：{why}；"
                                          "若本轮只改了 `docs/`（freeze 结构性排除该前缀）"
                                          "请在 RELEASE-REPORT 里写明"))
                elif doc_only:
                    # 文档类：**不打**「缺 P* 证据」，只提示判据（C007）。仍只 ⚠、不阻断。
                    out.append(("证据", f"候选 {cid} 为文档类（{why}），按 §六 无需 P* 证据；"
                                        "判据见 warn_for() 的 _doc_only_verdict()"))
                else:
                    out.append(("证据", f"候选 {cid} 缺执行线程侧 P* 证据（§六 要求 freeze 前写）；"
                                        f"当前 manifest.evidence = {ids_txt}（{why}）"))
    return out


# --------------------------------------------------------------------------- #
# manifest 校验
# --------------------------------------------------------------------------- #

def verify_manifest(base: Path, cid: str) -> list[str]:
    """返回错误列表；空列表 = 通过。"""
    rel_dir = base / "releases" / cid
    manifest_path = rel_dir / "manifest.json"
    errors: list[str] = []
    if not manifest_path.exists():
        return [f"manifest.json 不存在: {manifest_path}"]
    try:
        m = read_json(manifest_path)
    except Exception as e:
        return [f"manifest.json 无法解析: {e}"]
    for key in ["schema", "feature", "candidate", "artifacts", "install_order", "rollback", "gate"]:
        if key not in m:
            errors.append(f"manifest 缺少字段 {key}")
    if m.get("schema") != SCHEMA_MANIFEST:
        errors.append(f"schema 应为 {SCHEMA_MANIFEST}，实际 {m.get('schema')!r}")
    if m.get("candidate") != cid:
        errors.append(f"manifest.candidate={m.get('candidate')!r} 与目录 {cid} 不一致")

    files_dir = rel_dir / "files"
    registered: set[str] = set()
    artifacts = m.get("artifacts") or []
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("artifacts 为空：没有任何被冻结的产物")
    for a in artifacts:
        if not isinstance(a, dict):
            errors.append(f"artifacts 条目格式错误: {a!r}")
            continue
        rel = a.get("path")
        sha = a.get("sha256")
        if not rel or not isinstance(rel, str):
            errors.append(f"artifacts 条目缺少 path: {a!r}")
            continue
        registered.add(rel)
        p = files_dir / rel
        if not p.exists():
            errors.append(f"产物文件不存在: files/{rel}")
            continue
        actual = sha256_file(p)
        if sha != actual:
            errors.append(f"哈希不一致: files/{rel} 登记 {str(sha)[:12]}… 实际 {actual[:12]}…")
        if a.get("bytes") is not None and a.get("bytes") != p.stat().st_size:
            errors.append(f"字节数不一致: files/{rel}")
        if a.get("role") not in {"source", "test", "config", "doc", "asset", None}:
            errors.append(f"artifacts[{rel}].role 非法: {a.get('role')!r}")

    # 篡改检测：files/ 里出现未登记文件
    if files_dir.exists():
        for p in files_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(files_dir).as_posix()
            if rel not in registered:
                errors.append(f"未登记文件（可能被篡改或漏登记）: files/{rel}")

    # 证据
    evidence = m.get("evidence") or []
    ev_base = base
    check_ids = set()
    for e in evidence:
        if not isinstance(e, dict):
            errors.append(f"evidence 条目格式错误: {e!r}")
            continue
        cid_ = e.get("check_id")
        f = e.get("file")
        if not cid_:
            errors.append(f"evidence 缺少 check_id: {e!r}")
            continue
        check_ids.add(cid_)
        if not f:
            errors.append(f"证据 {cid_} 缺少 file")
            continue
        p = Path(f)
        if not p.is_absolute():
            p = ev_base.parent.parent / p  # 相对项目根
            if not p.exists():
                p = ev_base / f
        if not p.exists():
            errors.append(f"证据文件不存在: {f}")
            continue
        if e.get("sha256") and sha256_file(p) != e.get("sha256"):
            errors.append(f"证据哈希不一致: {f}")
        if e.get("grade") not in GRADES:
            errors.append(f"证据 {cid_} 等级非法: {e.get('grade')!r}")
        if e.get("result") not in STATUS_VALUES:
            errors.append(f"证据 {cid_} 结果非法: {e.get('result')!r}")

    # 检查复用必须写明理由
    checks = m.get("checks") or {}
    for r in checks.get("reused") or []:
        if not isinstance(r, dict) or not r.get("reason"):
            errors.append(f"复用检查未写 reason: {r!r}")
        else:
            if r.get("from_candidate") and r.get("from_candidate") not in (m.get("candidates") or {}):
                pass  # 历史候选可不在 state 里，不强制

    # 安装顺序必须覆盖且不超出产物
    order = m.get("install_order") or []
    unknown = [o for o in order if o not in registered]
    if unknown:
        errors.append(f"install_order 含未登记产物: {unknown}")
    missing = [a for a in registered if a not in order]
    if missing:
        errors.append(f"install_order 遗漏产物: {missing}")

    # 回滚字段
    rb = m.get("rollback") or {}
    if not isinstance(rb, dict) or "preserve" not in rb or "steps" not in rb:
        errors.append("rollback 必须含 preserve 与 steps")
    gate = m.get("gate") or {}
    if gate.get("status") not in {"ready", "blocked"}:
        errors.append(f"gate.status 非法: {gate.get('status')!r}")
    if gate.get("status") == "blocked":
        errors.append(f"候选自报 blocked: {gate.get('blocked_by')}")

    # 运行时声明（可选）：插件/服务必须能回答「运行时到底是哪一版」
    rt = m.get("runtime")
    if rt is not None:
        if not isinstance(rt, dict):
            errors.append("runtime 必须是对象")
        else:
            if rt.get("kind") not in {"plugin", "service", "cli", "none"}:
                errors.append(f"runtime.kind 非法: {rt.get('kind')!r}")
            if not str(rt.get("version") or "").strip():
                errors.append("runtime.version 不能为空（否则握手没有期望值）")
            url = str(rt.get("health_url") or "")
            if rt.get("kind") != "cli" and not url.startswith(("http://", "https://")):
                errors.append("runtime.health_url 必须是 http(s) 地址")
            if not isinstance(rt.get("requires_restart"), bool):
                errors.append("runtime.requires_restart 必须是布尔值")

    # 封存文件存在才校验（旧候选没有 verification.json 不阻塞）
    if (rel_dir / "verification.json").exists():
        errors.extend(verify_verification(base, cid))

    # 结论里不能把「待用户试用」写成「完整业务验收通过」由执行线程自封
    return errors


# --------------------------------------------------------------------------- #
# 命令实现
# --------------------------------------------------------------------------- #

PACK_TEXT_SUFFIXES = {".json", ".yml", ".yaml", ".js", ".mjs", ".cjs", ".md", ".svg", ".txt", ".ps1"}


def scaffold_plugin_pack(project: Path, feature: str, package: Path, args) -> dict:
    """把 templates/plugin-pack 抽出来的四件套复制到 <项目>/pack，并替换占位符。"""
    tpl = package / "templates" / "plugin-pack"
    if not tpl.is_dir():
        die(f"缺少能力包模板: {tpl}")
    pack = project / "pack"
    pid = (args.pack_id or feature).strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", pid):
        die("--pack-id 只能用小写字母/数字/连字符（如 weekly-report）")
    version = (args.pack_version or "0.1.0").strip()
    mapping = {
        "{{PACK_ID}}": pid,
        "{{PACK_NAME}}": f"@local/dsh-{pid}",
        "{{PACK_TITLE}}": (args.pack_title or feature).strip(),
        "{{PACK_DESC}}": (args.pack_desc or f"{feature} 能力包（待填一句话说明）").strip(),
        "{{PACK_VERSION}}": version,
        "{{PACK_ICON}}": (args.pack_icon or "🧩").strip(),
        "{{PACK_CATEGORY}}": (args.pack_category or "协作效率").strip(),
        "{{PACK_ORDER}}": str(args.pack_order),
        "{{PACK_ENTRY_KEY}}": f"cap:{pid}",
        "{{PACK_OPEN_EVENT}}": f"cappacks:open-{pid}",
        "{{FEATURE}}": feature,
        "{{PROJECT}}": project.as_posix(),
        "{{DATE}}": now_iso()[:10],
    }
    created, kept = [], []
    for src in sorted(tpl.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(tpl)
        dest = pack / rel
        if dest.exists() and not args.force:
            kept.append(rel.as_posix())
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in PACK_TEXT_SUFFIXES:
            text = src.read_text(encoding="utf-8")
            for k, v in mapping.items():
                text = text.replace(k, v)
            dest.write_text(text, encoding="utf-8", newline="\n")
        else:
            shutil.copy2(src, dest)
        created.append(rel.as_posix())
    leftovers = []
    for p in pack.rglob("*"):
        if p.is_file() and p.suffix.lower() in PACK_TEXT_SUFFIXES:
            try:
                if "{{" in p.read_text(encoding="utf-8", errors="replace"):
                    leftovers.append(p.relative_to(pack).as_posix())
            except OSError:
                continue
    return {"pack": pack, "id": pid, "name": mapping["{{PACK_NAME}}"], "version": version,
            "created": created, "kept": kept, "leftovers": leftovers}


# --------------------------------------------------------------------------- #
# flow-context-boost C001：交接包上下文摘要 / 角色裁剪 / 教训库 / init 建图
#
# 设计口径（DESIGN.md「闸门强度：轻量」）：
#   - 这里全部是**默认步骤 + 自检提示**，不参与 gate_for()/check_*() 判定，
#     任何数据源缺失只影响对应子块，next/init 退出码仍为 0。
#   - 唯一的非零退出只来自命令行参数自身错误（--key-note @不存在文件 / lesson add 缺必填）。
# --------------------------------------------------------------------------- #

# `init` 维护的项目根 `.graphifyignore`（只排除封存副本与工具产物）。
# 实测（本项目，2026-11-20）：不带它建图 2378 节点 / 26.8s，其中约 89% 是
# docs/*/releases/*/files/ 的封存副本，god_nodes 全指向重复副本；带上后 269 节点 / 6.5s。
# 2026-11-21（C003）：分发产物目录在事故后改名为 `dsh-bundle-live/`、后来又改 `dsh-bundle-dist/`，
# 旧清单只排了 `dsh-bundle/` → 同名副本又被吃进图里（675 节点里 322 个在 `dsh-bundle-live/**`，
# 且 `_qc_static`/`warn_for`/`drive` 等新符号查不到）。故把两个变体一并列进排除清单：
# 三条并列写（不用通配 `dsh-bundle*/`）——只排真正是分发副本的三个目录名，
# 不误伤将来可能出现的 `dsh-bundleable/` 之类同前缀目录。
GRAPH_IGNORE_HEADER = "# 由 dsh_flow.py init 维护；只排除封存副本与工具产物"
GRAPH_IGNORE_LINES = (
    "docs/**/releases/",
    "docs/**/archive/",
    "docs/**/files/",
    "docs/**/evidence/",
    "examples/",
    "dsh-bundle/",
    "dsh-bundle-live/",
    "dsh-bundle-dist/",
    "graphify-out/",
)
# 「图上不该出现的副本路径」判据：`_graph_pollution()` 与 `_ctx_graph_summary()` 共用一份，
# 避免两处各写一遍正则后漂移（C003 之前就是两处各写一份 `dsh-bundle`）。
# 形状：`dsh-bundle` 本身，或 `dsh-bundle-<后缀>`（live / dist / 将来的 live2 …）。
# **不要**改回 `dsh-bundle[^/]*`：那会匹配 `dsh-bundleable/`，把同名前缀的普通目录误判成副本
# （selftest `Q: F3` 有反向断言）。
RE_GRAPH_COPY_SOURCE = re.compile(
    r"(^|/)(releases|archive|evidence|files|dsh-bundle(?:-[A-Za-z0-9]+)*)(/|$)")
GRAPHIFY_EXE = r"<graphify-tools>\Scripts\graphify.exe"
GRAPH_TIMEOUT_DEFAULT = 300
# `init` 自己维护的工具配置文件：进基线/候选（要随候选交付），但不算「本项目有源码」
TOOL_ARTIFACT_FILES = {".graphifyignore"}

LESSONS_REL = "ops/lessons.md"
LESSONS_TITLE = "# 跨 feature 教训库（ops/lessons.md）"
LESSONS_HEADER = "| ID | 症状 | 根因 | 做法 | 适用角色 | 日期 |"
LESSONS_SEP = "|---|---|---|---|---|---|"
RE_LESSON_ROW = re.compile(
    r"^\|\s*(L\d{3})\s*\|(.+)\|(.+)\|(.+)\|\s*([a-z,]+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|$")
LESSON_ROLES = ("lead", "planner", "executor", "verifier", "inspector", "all")

DEFAULT_MAX_CONTEXT_CHARS = 3000
HANDOFF_MAX_BYTES = 12000  # 单份交接包字节上限（§1 之外的章节固定，§1 吃剩余预算）
KEY_MAX_ITEMS = 8
KEY_MAX_CHARS = 1500
# MEMORY.md（project 轨）只在没有 KEY.md 时兜底；语义不同，单独标注、单独压更小的上限
MEM_TAIL_ITEMS = 2
MEM_TAIL_CHARS = 400
# 单条记忆正文上限：真实 KEY.md 的一条能有 500+ 字符，整条塞进 §1 会把别的子块挤没。
# §1 的**实际渲染**上限是「最新 2 条、每条 ≤180 字符」（DESIGN 的 8 条 / 1500 字符是「不超过」的
# 上限，不是必须填满）；末尾写「只显示最新 N 条」并给完整路径，剩下的让子智能体自己去读。
KEY_RENDER_ITEMS = 2
KEY_ENTRY_MAX_CHARS = 180
# §1 的最小字节配额：真实数据下「图谱/上一候选/同类坑/关键事实」都要有落点，
# 不能因为 §2 角色要点先占满 12000 字节而把记忆整段裁光（E18① 的教训）
HANDOFF_CTX_MIN_BYTES = 2600
ROLE_SECTION_MAX_LINES = 30
ROLE_EXTRA_SECTION_MAX_LINES = 10  # 非必保小节的行上限（比必保小节更紧）
ROLE_DIGEST_MAX_BYTES = 6500
# 五节「必保」：裁剪后必须在内嵌里可定位（找不到同名小节时降级为指针，仍写明文件路径）。
# 每项 = (显示名, 用于匹配小节标题的关键字元组)——角色文件里的小节标题写法不完全统一
# （例如 executor 写的是「回报给 Lead 的固定格式」而不是「回报格式」）。
ROLE_MUST_KEEP = (
    ("启动自检", ("启动自检",)),
    ("权限边界", ("权限边界",)),
    ("交接物", ("交接物",)),
    ("回报格式", ("回报给", "回报格式")),
    ("常见失败与拒绝条件", ("常见失败",)),
)
# 每角色同义词（G3）：只认 DESIGN v2 表里列出的映射，**绝不泛化**——泛化会让 ✅ 变成假绿，
# 即「小节正文其实没内嵌，只是标题撞词了」。
#   lead      ：权限边界≅隔离纪律、回报格式≅收尾
#   inspector ：交接物≅产出物
# 已按 V17 撤回两条偏松的映射（原始值也留在这里，避免有人再"顺手加回来"）：
#   ~~lead：常见失败≅必须让用户介入~~（"必须停下问用户" ≠ "常见失败与拒绝条件"）
#   ~~inspector：常见失败≅自停阈值~~（`## 6 自停阈值` 在文档里排在 `## 8` 之前，
#     关键字取「首个命中」→ 新 §8 永远选不中，等于补了个从不被使用的节）
# 现在两处都用**标准标题**直接命中：`roles/00-lead.md` 的 `## 10. 常见失败与拒绝条件`、
# `roles/04-inspector.md` 的 `## 8 常见失败与拒绝条件`。
ROLE_MUST_KEEP_SYNONYMS = {
    "lead": {
        "权限边界": ("隔离纪律",),
        "回报格式": ("收尾",),
    },
    "inspector": {
        "交接物": ("产出物",),
    },
}


def role_must_keep(role: str):
    """返回该角色的五节必保表 [(显示名, 关键字元组)]（含该角色的同义词，别的角色不加）。"""
    syn = ROLE_MUST_KEEP_SYNONYMS.get(role) or {}
    out = []
    for label, words in ROLE_MUST_KEEP:
        out.append((label, tuple(words) + tuple(syn.get(label) or ())))
    return tuple(out)
# 角色 × 阶段 → 内嵌小节名单。_default 与 <PHASE> 合并（阶段专属排前面），按顺序装填，
# 装不下（超 ROLE_DIGEST_MAX_BYTES）的小节自动降级为一行指针。
ROLE_SECTION_POLICY = {
    "lead": {
        "_default": ["启动自检", "必须让用户介入", "阶段门禁表", "主循环", "隔离纪律", "不变量", "收尾"],
    },
    "planner": {
        "_default": ["启动自检", "权限边界", "工作流程", "交接物", "回报给", "常见失败"],
        "DESIGN": ["启动自检", "权限边界", "工作流程", "交接物", "回报给", "常见失败"],
    },
    "executor": {
        "_default": ["启动自检", "权限边界", "工作流程", "交接物", "回报给", "常见失败"],
        "EXECUTING": ["启动自检", "权限边界", "工作流程", "交接物", "回报给", "常见失败"],
    },
    "verifier": {
        "_default": ["启动自检", "权限边界", "工作流程", "交接物", "回报给", "常见失败"],
        "VERIFYING": ["启动自检", "权限边界", "工作流程", "交接物", "回报给", "常见失败"],
        "TRIAL": ["启动自检", "待用户试用清单", "权限边界", "工作流程", "交接物", "回报给", "常见失败"],
    },
    "inspector": {
        "_default": ["启动自检", "权限边界", "审计流程", "产出物", "回报格式", "自停阈值"],
    },
}

RE_KEY_ID = re.compile(r"^\[id:[0-9A-Za-z_\-]{3,}\]\s*")
RE_KEY_ENTRY = re.compile(r"^\[id:[0-9A-Za-z_\-]{3,}\]")
RE_KEY_TS = re.compile(r"^\[\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?\]\s*")
RE_LESSON_PREFIX = re.compile(r"^(症状|根因|做法)\s*[：:]\s*")


def _clean_heading(raw: str) -> str:
    t = re.sub(r"^#+[ \t]*", "", (raw or "").strip())
    t = re.sub(r"^[\d一二三四五六七八九十百]+[.、．)）]?[ \t]*", "", t)
    # 去掉标题里的旁注（`## 待用户试用清单     ← 标题字面一致…` 这类）
    t = re.split(r"\s{2,}|←", t)[0]
    return t.strip()


def _md_sections(text: str) -> list[tuple[str, list[str]]]:
    """按 `## ` 切小节（`###` 归入父小节）。返回 [(标题原始行, 正文行)]。"""
    secs: list[tuple[str, list[str]]] = []
    cur = None
    for line in (text or "").splitlines():
        if re.match(r"^##\s+", line):
            if cur is not None:
                secs.append(cur)
            cur = (line.strip(), [])
        elif cur is not None:
            cur[1].append(line.rstrip())
    if cur is not None:
        secs.append(cur)
    return secs


def _pick_section(secs, keywords):
    for raw, body in secs:
        title = _clean_heading(raw)
        if any(k in title for k in keywords):
            return raw, body
    return None, None


# ---------------------------- 建图（init 默认步骤） ---------------------------- #

def _graphify_exe() -> str:
    """返回可用的 graphify CLI 路径；找不到返回空串（调用方降级）。"""
    if GRAPHIFY_EXE and Path(GRAPHIFY_EXE).is_file():
        return GRAPHIFY_EXE
    found = shutil.which("graphify")
    return found or ""


def _ensure_graphifyignore(path: Path) -> list[str]:
    """创建 / 补行 `.graphifyignore`；只追加缺失排除行，不重写、不删用户行、不改顺序。"""
    want = list(GRAPH_IGNORE_LINES)
    try:
        if not path.exists():
            path.write_text(GRAPH_IGNORE_HEADER + "\n" + "\n".join(want) + "\n",
                            encoding="utf-8", newline="\n")
            return [f"  .graphifyignore：已创建（{len(want)} 行排除 + 首行注释）"]
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
        existing = {ln.strip() for ln in raw.splitlines()}
        missing = [ln for ln in want if ln not in existing]
        if not missing:
            return ["  .graphifyignore：已存在且排除项齐全（未改动）"]
        prefix = "" if (not raw or raw.endswith("\n")) else "\n"
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(prefix + "\n".join(missing) + "\n")
        return [f"  .graphifyignore：已追加 {len(missing)} 行缺失排除项（既有行未动、顺序未改）"]
    except OSError as e:
        return [f"  ⚠ .graphifyignore 写入失败（{type(e).__name__}: {e.strerror or e}）；继续建图"]


def _graph_pollution(project: Path) -> int:
    """图里含封存副本（releases/archive/evidence/files）、分发副本（dsh-bundle*）的节点数；读不到返回 -1。"""
    gp = project / "graphify-out" / "graph.json"
    try:
        d = read_json(gp)
    except Exception:
        return -1
    n = 0
    for node in (d.get("nodes") or []):
        sf = str(node.get("source_file") or node.get("file") or "").replace("\\", "/")
        if sf and RE_GRAPH_COPY_SOURCE.search(sf):
            n += 1
    return n


def _run_graphify(project: Path, timeout: int) -> list[str]:
    """有图走 update，无图走 extract --code-only；任何失败只打印 ⚠ + 手工命令。"""
    exe = _graphify_exe()
    has_graph = (project / "graphify-out" / "graph.json").exists()
    mode = "update" if has_graph else "extract"
    manual = f'graphify {mode} "{project.as_posix()}"' + ("" if has_graph else " --code-only")
    if not exe:
        return ["  ⚠ 建图失败（找不到 graphify CLI）",
                f"    手工命令：{manual}"]
    cmd = [exe, mode, str(project)] + ([] if has_graph else ["--code-only"])
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return [f"  ⚠ 建图失败（超时 {timeout}s）", f"    手工命令：{manual}"]
    except OSError as e:
        return [f"  ⚠ 建图失败（{type(e).__name__}: {e.strerror or e}）", f"    手工命令：{manual}"]
    if p.returncode != 0:
        tail = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()[-3:]
        detail = ("：" + " / ".join(x.strip() for x in tail)) if tail else ""
        return [f"  ⚠ 建图失败（exit={p.returncode}）{detail}", f"    手工命令：{manual}"]
    out_lines = [f"  graphify {mode}：完成（{manual}）"]
    gp = project / "graphify-out" / "graph.json"
    try:
        d = read_json(gp)
        links = d.get("links")
        if links is None:  # graphify 写的是 links
            links = d.get("edges") or []
        out_lines.append(f"    → {len(d.get('nodes') or [])} 节点 / {len(links)} 边：{gp.as_posix()}")
    except Exception:
        pass
    poll = _graph_pollution(project)
    if poll > 0:
        out_lines.append(f"  ⚠ 检测到图中含封存副本 {poll} 个节点，建议 "
                         f'graphify update "{project.as_posix()}" --force 重建（不自动执行）')
    return out_lines


# ---------------------------- 上下文采集（next） ---------------------------- #

def _memories_root(args=None) -> "Path | None":
    """<memories> 解析顺序（第一个存在目录的赢）：--memories-dir > 三个环境变量 > DSH_HOME\\memories > ~\\.dsh\\memories。"""
    cands: list[Path] = []
    md = getattr(args, "memories_dir", None) if args is not None else None
    if md:
        cands.append(Path(md))
    for env in ("DSH_FLOW_MEMORIES_DIR", "DSH_MEMORY_DIR", "DSH_MEMORIES_DIR"):
        v = os.environ.get(env)
        if v:
            cands.append(Path(v))
    home = os.environ.get("DSH_HOME")
    if home:
        cands.append(Path(home) / "memories")
    up = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    if up:
        cands.append(Path(up) / ".dsh" / "memories")
    for p in cands:
        try:
            if p.is_dir():
                return p
        except OSError:
            continue
    return None


def _project_id(path_str: str) -> str:
    """projectId = sha1(<路径字符串>).hex[:12]；**不做任何规范化**（正/反斜杠算不同 id）。"""
    return hashlib.sha1(path_str.encode("utf-8")).hexdigest()[:12]


def _prov_display_name(prov: Path) -> str:
    txt = _text(prov)
    try:
        j = json.loads(txt)
        if isinstance(j, dict):
            return str(j.get("displayName") or j.get("display_name") or "")
    except Exception:
        pass
    m = re.search(r'"?displayName"?\s*[:=]\s*"?([^"\n,}]+)', txt)
    return m.group(1).strip() if m else ""


def _memory_project_dirs(project: Path, memories: Path) -> list[tuple[Path, str]]:
    """G5/W15：定位链改为「会话 cwd hash 首选 → 项目根 hash → PROVENANCE 唯一匹配」，
    三候选**全部尝试、命中即合并**（按绝对路径去重），各自带来源说明。

    为什么 cwd 排第一：memory-evolve 用**会话 cwd** 算 projectId 写盘，而 `next` 的 `-p` 是项目根；
    本机实测 `sha1("D:\\01-AI空间\\001-开发")[:12]=d027fff0a9da`（KEY.md 在这），
    `sha1(<项目根>)[:12]=1a279f3b5b30`（目录不存在）。旧实现把项目根排首位，于是恒为「未提供」。
    """
    out: list[tuple[Path, str]] = []
    seen: set[str] = set()
    proj_root = memories / "projects"

    def add(d: Path, why: str) -> None:
        try:
            if not d.is_dir():
                return
        except OSError:
            return
        key = str(d)
        if key in seen:
            return
        seen.add(key)
        out.append((d, why))

    try:
        cwd = Path.cwd()
    except OSError:
        cwd = None
    if cwd is not None:
        add(proj_root / _project_id(str(cwd)), "会话 cwd hash（memory-evolve 写入方）")
    add(proj_root / _project_id(str(project)), "项目根 hash")

    # PROVENANCE.displayName 唯一匹配：memory-evolve 记的是**会话 cwd** 的目录名，所以除项目根
    # 自身名外还要沿祖先目录逐级比对（本项目实测 displayName="001-开发" = 项目根的父目录名）。
    names: list[str] = []
    for p in [project] + list(project.parents):
        try:
            nm = p.name
        except Exception:
            nm = ""
        if nm and nm not in names:
            names.append(nm)
    try:
        dirs = [d for d in sorted(proj_root.iterdir()) if d.is_dir()] if proj_root.is_dir() else []
    except OSError:
        dirs = []
    for nm in names:
        hits = [d for d in dirs if _prov_display_name(d / "PROVENANCE") == nm]
        if len(hits) == 1:  # 不唯一就不猜
            add(hits[0], f"PROVENANCE displayName={nm} 唯一匹配")
    return out


def _key_entries(path: Path) -> tuple[list[str], str]:
    """读 KEY.md，按条目（`[id:…]` 开头）切分并剥掉 `[id:…]`/`[时间]`/`[summary:…]` 外壳。
    返回 (条目正文列表[文件顺序=旧→新], 错误说明)。"""
    try:
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as e:
        return [], f"读取失败（{type(e).__name__}: {e.strerror or e}）"
    except Exception as e:  # 编码等异常一律降级
        return [], f"读取失败（{type(e).__name__}）"

    def clean(line: str) -> str:
        s = line.strip()
        if not s or s.startswith("#") or s == "§" or set(s) <= set("-— "):
            return ""
        s = RE_KEY_ID.sub("", s)
        s = RE_KEY_TS.sub("", s).strip()
        if s.startswith("[summary:"):
            s = s[len("[summary:"):].strip()
            if s.endswith("]"):
                s = s[:-1].strip()
        return s

    entries: list[str] = []
    chunk: list[str] = []

    def push():
        text = " ".join(x for x in chunk if x).strip()
        if not text:
            return
        if len(text) > KEY_ENTRY_MAX_CHARS:
            text = text[: KEY_ENTRY_MAX_CHARS - 1].rstrip() + "…"
        entries.append(text)

    for line in raw.splitlines():
        if RE_KEY_ENTRY.match(line.strip()):
            if chunk:
                push()
            chunk = [clean(line)]
        else:
            c = clean(line)
            if c:
                chunk.append(c)
    if chunk:
        push()
    return [e for e in entries if e], ""


def _memory_entries(path: Path, expect_label: str) -> tuple[list[str], str]:
    """读 MEMORY.md（`§` 分隔的条目）；只用于 KEY.md 缺失时的兜底，语义与 KEY 不同。"""
    return _key_entries(path)


def _tail_pick(items: list[str], max_items: int, max_chars: int) -> tuple[list[str], int]:
    """从**尾部**向前累计（新的优先），返回 (按时间正序的选中项, 被丢弃条数)。

    这是 L005/V7 的同型坑：早先用 `for item in items:` 从文件头累计，满额即停，
    于是**新写进 KEY.md 的事实永远进不了交接包**。
    """
    picked: list[str] = []
    total = 0
    for e in reversed(items):
        if len(picked) >= max_items:
            break
        if picked and total + len(e) > max_chars:
            break
        picked.append(e)
        total += len(e)
    picked.reverse()
    return picked, len(items) - len(picked)


def _read_key_md(path: Path) -> tuple[list[str], str]:
    """兼容旧调用：返回 KEY.md 的条目正文（已剥前缀）。"""
    return _key_entries(path)


def _ctx_graph_summary(project: Path, st: dict) -> list[str]:
    gp = project / "graphify-out" / "graph.json"
    if not gp.exists():
        return [f"- 未建图（跑 `init` 或 `graphify extract --code-only`）：{gp.as_posix()}"]
    try:
        d = read_json(gp)
    except Exception as e:
        return [f"- 读取失败（{type(e).__name__}）：{gp.as_posix()}"]
    nodes = d.get("nodes") or []
    links = d.get("links")
    if links is None:  # graphify 写的是 links，没有 edges 键
        links = d.get("edges") or []
    lines = [f"- 规模：{len(nodes)} 节点 / {len(links)} 边（来源：{gp.as_posix()}）"]
    roots = scope_roots(st)
    counts: dict[str, int] = {}
    scope_hits = 0
    polluted = 0
    for node in nodes:
        sf = str(node.get("source_file") or node.get("file") or "").replace("\\", "/")
        if not sf:
            continue
        if RE_GRAPH_COPY_SOURCE.search(sf):
            polluted += 1
        parts = sf.split("/")
        top = parts[0] if len(parts) > 1 else "."
        counts[top] = counts.get(top, 0) + 1
        for r in roots:
            r2 = r.strip("/")
            if r2 and (sf == r2 or sf.startswith(r2 + "/")):
                scope_hits += 1
                break
    top5 = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    if top5:
        lines.append("- 文件分布 top5：" + "、".join(f"{k}（{v}）" for k, v in top5))
    lines.append(f"- 与声明写范围（scope）相交的文件节点：{scope_hits}")
    if polluted:
        lines.append(f"- ⚠ 图中含封存副本 {polluted} 个节点，建议 "
                     f'graphify update "{project.as_posix()}" --force 重建')
    if not (project / ".graphifyignore").exists():
        lines.append("- ⚠ 项目根缺 `.graphifyignore`，下次 `update` 会把封存副本重新吃进图里（`init` 会补）")
    return lines


def _ctx_prev_report(base: Path, st: dict) -> list[str]:
    rel_root = base / "releases"
    cands: list[str] = []
    cur = st.get("current_candidate")
    if cur:
        cands.append(str(cur))
    try:
        if rel_root.is_dir():
            for p in sorted(rel_root.iterdir()):
                if p.is_dir() and re.fullmatch(r"C\d{3,}", p.name) and p.name not in cands:
                    cands.append(p.name)
    except OSError:
        pass
    for c in cands:
        rp = rel_root / c / "RELEASE-REPORT.md"
        if not rp.is_file():
            continue
        secs = _md_sections(_text(rp))
        out = [f"- 候选 `{c}`（来源：{rp.as_posix()}）"]
        for key, label in ((("已知问题",), "已知问题"), (("给执行线程",), "给执行线程的信息")):
            raw, body = _pick_section(secs, key)
            if raw is None:
                out.append(f"- 『{label}』：报告无该小节")
                continue
            keep = [x for x in body if x.strip()][:15]
            out.append(f"- 『{label}』：")
            out.extend("  " + x.strip() for x in keep) if keep else out.append("  （该节为空）")
        return out
    return ["- 尚无候选（`releases/` 下没有带 RELEASE-REPORT.md 的候选）"]


def _load_lessons(project: Path) -> tuple[list[dict], list[str], str]:
    """返回 (有效行, 无效行原文, 错误说明)。"""
    p = project / LESSONS_REL
    if not p.exists():
        return [], [], "未建"
    try:
        raw = p.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as e:
        return [], [], f"读取失败（{type(e).__name__}）"
    rows: list[dict] = []
    invalid: list[str] = []
    in_fence = False
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("```"):  # 文档里的「行契约」示例块不算数据行
            in_fence = not in_fence
            continue
        if in_fence or not s.startswith("|"):
            continue
        if set(s) <= set("|-: "):  # 分隔行
            continue
        if s.startswith("| ID"):
            continue
        m = RE_LESSON_ROW.match(s)
        if not m:
            invalid.append(s)
            continue
        cell = lambda x: RE_LESSON_PREFIX.sub("", x.strip()).strip()
        rows.append({
            "id": m.group(1),
            "symptom": cell(m.group(2)),
            "cause": cell(m.group(3)),
            "fix": cell(m.group(4)),
            "roles": [t.strip() for t in m.group(5).split(",") if t.strip()],
            "date": m.group(6),
        })
    return rows, invalid, ""


def _ctx_lessons(project: Path, role: str) -> list[str]:
    rows, invalid, err = _load_lessons(project)
    p = project / LESSONS_REL
    if err == "未建":
        return [f"- 教训库未建（用 `lesson add` 补，路径：{p.as_posix()}）"]
    if err:
        return [f"- {err}：{p.as_posix()}"]
    # 取**最新**的 N 条（文件自上而下是旧→新，所以用 [-N:]）：教训库的意义是「新踩的坑
    # 能进下一个交接包」。早先用 [:3] 取到的是最早 3 条，该角色命中满 3 条后新条目永远
    # 带不出来，闭环等于断开（C001 的 V7 缺陷，C002 修）。
    mine = [r for r in rows if role in r["roles"]][-3:]
    common = [r for r in rows if "all" in r["roles"]][-2:]
    out = [f"- {r['symptom']} → {r['fix']}（{r['id']}）" for r in mine + common]
    if not out:
        out = [f"- 无同类坑（教训库 {len(rows)} 条）"]
    # 每块都要给出可自查的来源路径（A：交接包每块带来源）
    out.append(f"- 来源：{p.as_posix()}（`lesson list --role {role}` 可回看）")
    if invalid:
        out.append(f"- ⚠ 另有 {len(invalid)} 行格式无效（`lesson list` 可看）")
    return out


def _key_note_items(args) -> list[str]:
    """把 `--key-note` 归一成**非空字符串列表**（C002：`action="append"`，可多次）。

    向后兼容：既接受 `argparse` 给的 `list[str]`，也接受旧调用方/测试直接塞进来的单个 `str`
    （单值等价于只传一次）。空值、纯空白一律丢掉，避免交接包里出现空标题。
    """
    raw = getattr(args, "key_note", None)
    if raw is None or raw == "":
        return []
    items = [raw] if isinstance(raw, str) else list(raw)
    return [s.strip() for s in items if isinstance(s, str) and s.strip()]


def _ctx_key_facts(project: Path, feature: str, args) -> list[str]:
    """项目关键事实：KEY.md → CONTEXT-NOTES.md → --key-note →（必要时）MEMORY.md 尾部兜底。

    体积止损顺序（写死在这里，便于回归）：`--key-note` > `CONTEXT-NOTES.md` > KEY 条目 >
    **MEMORY 尾部（最先牺牲）**。实现方式：MEMORY 兜底放在本块**最后**，而 §1 的裁剪是从块尾
    弹行，所以放不下时先掉 MEMORY，再掉 key-note / CONTEXT / KEY；五节必保在 §2，不受影响。
    """
    out: list[str] = []
    # ① memory-evolve 项目记忆：KEY.md（key 轨）首选，缺失才用 MEMORY.md（project 轨）尾部兜底
    memories = _memories_root(args)
    key_src = ""
    mem_src = ""
    mem_tail: list[tuple[str, str]] = []
    if memories is None:
        out.append("- KEY.md：未提供（找不到记忆目录；可用 `--memories-dir` 或环境变量 "
                   "`DSH_FLOW_MEMORIES_DIR` 指定，或加 `--key-note`）")
    else:
        dirs = _memory_project_dirs(project, memories)
        if not dirs:
            out.append("- KEY.md：未提供（定位链三个候选都没有命中记忆目录；可加 `--key-note` 补，"
                       "或让 Lead 用 memory 写 target=key）")
        picked: list[tuple[str, str]] = []   # (条目, 来源路径)
        dropped = 0
        for d, _why in dirs:
            kp = d / "KEY.md"
            if kp.is_file():
                ents, err = _key_entries(kp)
                if err:
                    out.append(f"- KEY.md：{err}（{kp.as_posix()}）")
                    continue
                keep, drop = _tail_pick(ents, KEY_RENDER_ITEMS, KEY_MAX_CHARS)
                picked.extend((e, kp.as_posix()) for e in keep)
                dropped += drop
                key_src = key_src or kp.as_posix()
        if key_src:
            # 多目录合并时按「取尾部」语义保留最新的一批
            picked = picked[-KEY_RENDER_ITEMS:]
            for e, src in picked:
                out.append(f"- {e}（来源：{src}）")
            if dropped:
                out.append(f"- 只显示最新 {len(picked)} 条（更早的 {dropped} 条已截断，"
                           f"完整见 {key_src}）")
        else:
            # 文件链兜底：没有 KEY.md 才看 MEMORY.md 尾部（语义不同，单独标注）
            for d, _why in dirs:
                mp = d / "MEMORY.md"
                if not mp.is_file():
                    continue
                ents, err = _key_entries(mp)
                if err:
                    out.append(f"- MEMORY.md：{err}（{mp.as_posix()}）")
                    continue
                keep, drop = _tail_pick(ents, MEM_TAIL_ITEMS, MEM_TAIL_CHARS)
                mem_tail = [(e, mp.as_posix()) for e in keep]
                mem_src = mp.as_posix()
                break
            if not mem_src and dirs:
                # `dirs` 为空时上面已经写过「定位链三个候选都没有命中记忆目录」，
                # 再写「定位到的记忆目录里既没有…」会自相矛盾（C005 实测一屏两条「未提供」）。
                out.append("- KEY.md：未提供（定位到的记忆目录里既没有 KEY.md 也没有 MEMORY.md；"
                           "可加 `--key-note` 补，或让 Lead 用 memory 写 target=key）")
    # ② 项目内 CONTEXT-NOTES.md（可选，叠加）
    notes = docs_root(project, feature) / "CONTEXT-NOTES.md"
    if notes.is_file():
        keep = [ln.rstrip() for ln in _text(notes).splitlines() if ln.strip()][:15]
        if keep:
            out.append(f"- CONTEXT-NOTES.md（来源：{notes.as_posix()}）：")
            out.extend("  " + ln for ln in keep)
    # ③ --key-note（最高优先级，排最后；C002 起可多次，按传入顺序全部叠加）
    notes_kn = _key_note_items(args)
    multi = len(notes_kn) > 1
    for idx, kn in enumerate(notes_kn, 1):
        tag = f"#{idx}" if multi else ""
        if kn.startswith("@"):
            src = kn[1:].strip().strip('"')
            out.append(f"- --key-note{tag}（来源：{Path(src).as_posix()}）：")
            out.extend("  " + ln for ln in _text(Path(src)).splitlines() if ln.strip())
        else:
            out.append(f"- --key-note{tag}（来源：命令行参数）：")
            out.extend("  " + ln for ln in kn.splitlines() if ln.strip())
    # ④ MEMORY.md 尾部兜底（**最先牺牲**：放不下时 §1 的裁剪从块尾弹行，先掉这里）
    if mem_tail:
        out.append(f"- 项目最近进展（来自 MEMORY.md 尾部）（来源：{mem_src}）：")
        out.extend(f"  - {e}" for e, _src in mem_tail)
        out.append(f"  - 只显示最新 {len(mem_tail)} 条（完整见 {mem_src}）")
    return out


def _mnemon_cli_path(args=None) -> Path:
    """mnemon CLI 路径：`--mnemon-cli` > profile 的 `mnemon.config.cliPath` > 默认安装位置。

    纯离线：只读 profile 的 `cordis.patch.yml` 文本，不拉起 CLI、不调 MCP。
    """
    raw = (getattr(args, "mnemon_cli", "") or "").strip()
    if raw:
        return Path(raw)
    up = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    if up:
        prof_root = Path(up) / ".dsh" / "profiles"
        try:
            cfgs = sorted(prof_root.glob("*/cordis.patch.yml"),
                          key=lambda p: (p.parent.name != "desktop", p.as_posix()))
        except OSError:
            cfgs = []
        for cfg in cfgs:
            try:
                txt = cfg.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            m = re.search(r"^[ \t]*cliPath[ \t]*:[ \t]*[\"']?([^\"'\r\n]+)", txt, re.MULTILINE)
            if m and m.group(1).strip():
                return Path(m.group(1).strip())
    return Path(r"D:\Tools\mnemon\mnemon.exe")


def _ctx_knowledge_entries(project: Path, feature: str, st: dict, graph_lines,
                           *, rag_dir=None, mnemon_cli=None, args=None) -> list[str]:
    """「知识入口」四行（DESIGN §5.4 / §5.5）：**纯离线**，不调 MCP、不发网络请求。

    可用性一律不判（离线判不了）：只输出「配置/文件在不在」这类可离线核对的事实；
    任一项缺失写「未安装 / 未配置」，**不写「不可用」**（B3）。RAG 的固定降级措辞见 §5.5。
    """
    # ① 检索建议词：feature 名 + state.scope 目录名（文件项取主干）+ 图谱中与 scope 相交的前 3 个主干
    terms: "list[str]" = []

    def add_term(t: str) -> None:
        t = (t or "").strip()
        if t and t not in terms:
            terms.append(t)

    add_term(feature)
    roots = scope_roots(st)
    for root in roots:
        name = Path(root).name
        if "." in name.lstrip("."):
            name = Path(name).stem
        add_term(name)

    stems: "list[str]" = []
    for ln in (graph_lines or []):
        for m in re.finditer(r"[A-Za-z0-9_.\-]+\.(?:py|js|mjs|cjs|json|ya?ml|md|ps1)", ln):
            stem = Path(m.group(0)).stem
            if stem and stem not in stems:
                stems.append(stem)
    if not stems:
        gp = project / "graphify-out" / "graph.json"
        try:
            nodes = (read_json(gp).get("nodes") or []) if gp.is_file() else []
        except Exception:
            nodes = []
        clean = [r.strip("/") for r in roots]
        for node in nodes:
            sf = str(node.get("source_file") or node.get("file") or "").replace("\\", "/")
            if not sf or not any(r and (sf == r or sf.startswith(r + "/")) for r in clean):
                continue
            stem = Path(sf).stem
            if stem and stem not in stems:
                stems.append(stem)
            if len(stems) >= 3:
                break
    for s in stems[:3]:
        add_term(s)
    terms = terms[:6]
    while terms and len("、".join(terms).encode("utf-8")) > 300:
        terms.pop()
    words = "、".join(f"`{t}`" for t in terms) or f"`{feature}`"
    agentmem_q = f"{feature} {terms[1] if len(terms) > 1 else '流程'}"

    # ② 记忆离线层：只报可离线核对的计数与存在性
    memories = _memories_root(args)
    key_n = mem_n = 0
    if memories is not None:
        for d, _why in _memory_project_dirs(project, memories):
            for fname in ("KEY.md", "MEMORY.md"):
                fp = d / fname
                if not fp.is_file():
                    continue
                ents, err = _key_entries(fp)
                if err:
                    continue
                if fname == "KEY.md":
                    key_n += len(ents)
                else:
                    mem_n += len(ents)
    cli = Path(mnemon_cli) if mnemon_cli else _mnemon_cli_path(args)
    try:
        cli_ok = cli.is_file()
    except OSError:
        cli_ok = False

    # ③ RAG：配置/日志层证据（活体可达性不在离线判据内，DESIGN §5.5）
    if rag_dir:
        rd = Path(rag_dir)
    else:
        up = os.environ.get("USERPROFILE") or os.environ.get("HOME") or "."
        rd = Path(up) / ".dsh" / "raganything"
    try:
        rag_files = [p for p in rd.rglob("*") if p.is_file()] if rd.is_dir() else []
    except OSError:
        rag_files = []
    if not rag_files:
        rag_state = "未安装（未提供）"
        rag_line = "- RAG-Anything：未安装（未提供）"
    else:
        logs = [p for p in rag_files if "log" in p.name.lower()]
        if logs:
            try:
                last = max(logs, key=lambda p: p.stat().st_mtime)
                last_txt = datetime.fromtimestamp(last.stat().st_mtime, TZ) \
                    .replace(microsecond=0).isoformat()
            except OSError:
                last_txt = "未知"
            rag_state = f"配置在、有运行日志（最后活动 {last_txt}）"
        else:
            rag_state = "配置在、无运行日志"
        rag_line = (f"- RAG-Anything：未提供（RAG sidecar 不可达）；{rag_state}；"
                    "活体探测不在离线范围内，实测口径见 ops/memory-split.md 的 RAG 节")

    return [
        f"- mnemon 检索词：{words}（入口 `mnemon_document_search` / `mnemon_recall`；"
        "可用性判据见 ops/memory-split.md §2 问题 4，离线不判）",
        f"- agentmem 查询词：`{agentmem_q}`（跨端历史会话，`search_events`；离线不判）",
        f"- 记忆离线层：memory-evolve=KEY.md 命中（{key_n} 条）/ MEMORY.md 命中（{mem_n} 条）；"
        f"mnemon CLI={cli.as_posix()} {'存在' if cli_ok else '未安装'}；"
        f"RAG-Anything={rag_state}",
        rag_line,
    ]


def _render_context_section(blocks, budget: int, budget_bytes: "int | None" = None,
                            min_lines=None) -> str:
    """拼 `## 1. 已知上下文（自动摘要）`，超预算按块从最长块裁行并标注截断来源。

    双预算：`budget` 是**字符**预算（DESIGN 的 `--max-context-chars`，默认 3000）；
    `budget_bytes` 是**字节**预算（保证整份交接包 ≤ HANDOFF_MAX_BYTES，中文一个字 3 字节，
    只按字符算会把 12000 字节上限撑破）。任一超出就继续裁。

    `min_lines`：每块至少保留几行（默认每股 2 行、项目关键事实 3 行）。**这条是给「真实数据」
    兜底的**：本机真实 KEY.md 条目很长，若纯按「裁最大的块」，记忆会被整段裁光（E18① 就是这么
    漏掉的）。有了保底行数，图谱/上一候选/同类坑/关键事实各留最关键的几行。
    """
    work = [(t, [x for x in lines], src) for t, lines, src in blocks]
    cut = [False] * len(work)
    mins = list(min_lines) if min_lines else [2] * max(0, len(work) - 1) + [3]
    while len(mins) < len(work):
        mins.append(0)

    def size(i):
        return len("\n".join(work[i][1]))

    def size_bytes(i):
        return len("\n".join(work[i][1]).encode("utf-8"))

    def over(i_list):
        chars = sum(size(i) for i in i_list)
        byts = sum(size_bytes(i) for i in i_list)
        return chars > budget or (budget_bytes is not None and byts > budget_bytes)

    guard = 0
    while over(range(len(work))) and guard < 4000:
        guard += 1
        # 只在「还行数可裁」的块里挑最大的裁；全都到保底行数了才放开
        pool = [i for i in range(len(work)) if len(work[i][1]) > mins[i]] \
            or [i for i in range(len(work)) if len(work[i][1]) > 1]
        if not pool:
            break
        idx = max(pool, key=size)
        lines = work[idx][1]
        if len(lines) <= 1:
            # 单行块仍超预算：直接截断该行文本
            if lines and len(lines[0]) > 80:
                lines[0] = lines[0][: max(40, len(lines[0]) - 40)] + "…"
                cut[idx] = True
                continue
            # 已无法再裁：从「非首位」的块里删掉整块以保护前面的块
            others = [i for i in range(len(work)) if i != idx and len(work[i][1]) > 1]
            if not others:
                break
            cut[idx] = True
            work[idx] = (work[idx][0], lines[:1], work[idx][2])
            continue
        lines.pop()
        cut[idx] = True

    out = ["## 1. 已知上下文（自动摘要）", "",
           f"> 由 `next` 离线采集（不调 MCP/LLM/网络），预算 {budget} 字符；"
           "任一数据源缺失只影响对应子块。", ""]
    for i, (title, lines, src) in enumerate(work):
        out.append(f"### {title}")
        out.extend(lines if lines else ["- （空）"])
        if cut[i]:
            out.append(f"- 已截断，完整见 {src}" if src else "- 已截断")
        out.append("")
    return "\n".join(out)


def _render_role_digest(package: Path, role: str, phase: str, doc: str,
                        max_bytes: "int | None" = None) -> "str | None":
    """按 ROLE_SECTION_POLICY 裁剪角色说明书；返回 None 表示裁剪失败（调用方退回全文内嵌）。

    `max_bytes` 可下调本节的字节预算（调用方发现整份交接包超标时用它继续收）。
    """
    name = ROLE_FILES.get(role, "")
    rel = f"roles/{name}" if name else "roles/"
    if not (doc or "").strip():
        return None
    secs = _md_sections(doc)
    if not secs:
        return None
    policy = ROLE_SECTION_POLICY.get(role) or {}
    wanted: list[str] = []
    for w in list(policy.get(phase) or []) + list(policy.get("_default") or []):
        if w not in wanted:
            wanted.append(w)

    def index_of(word, used):
        words = (word,) if isinstance(word, str) else tuple(word)
        for i, (raw, _body) in enumerate(secs):
            if i in used:
                continue
            title = _clean_heading(raw)
            if any(w in title for w in words):
                return i
        return -1

    used: set[int] = set()
    must_idx: list[int] = []
    must_keep = role_must_keep(role)  # 每角色同义词表（G3）
    for _label, words in must_keep:
        i = index_of(words, used)
        if i >= 0:
            must_idx.append(i)
            used.add(i)
    keep: list[int] = list(must_idx)
    for w in wanted:
        i = index_of(w, used)
        if i >= 0:
            keep.append(i)
            used.add(i)
    if not keep:
        return None
    rest = [i for i in range(len(secs)) if i not in used]

    must_txt = []
    for label, words in must_keep:
        hit = any(any(w in _clean_heading(secs[i][0]) for w in words) for i in keep)
        must_txt.append(f"{label}{' ✅' if hit else ' ➖'}")

    head = [f"> 完整说明书：`{rel}`（阶段 `{phase}` 已裁剪；✅=本包内嵌，➖=仅见完整说明书）",
            f"> 必保五节：{' / '.join(must_txt)}", ""]
    is_must = {i for i in keep
               if any(any(w in _clean_heading(secs[i][0]) for w in words)
                      for _label, words in must_keep)}
    core = [i for i in keep if i in is_must]
    extra = [i for i in keep if i not in is_must]

    def render_block(i: int, cap: int) -> list[str]:
        raw, lines = secs[i]
        # 内嵌到交接包 §2 下面，标题降一级，避免与交接包自己的 `## N` 编号冲突
        block = ["### " + raw.lstrip("#").strip()] + list(lines)
        while block and not block[-1].strip():
            block.pop()
        if len(block) - 1 > cap:
            total = len(block) - 1
            block = block[:cap + 1]
            block.append(f"…（本节共 {total} 行，只内嵌前 {cap} 行，"
                         f"完整见 `{rel}` 的「{_clean_heading(raw)}」）")
        return block + [""]

    budget = ROLE_DIGEST_MAX_BYTES if max_bytes is None else max(600, int(max_bytes))
    body: list[str] = []
    trimmed: list[str] = []
    best = None  # 在预算内选「装得最多」的那一档 cap（同等字节数取更大的 cap）
    # 必保小节永远优先占预算：先按上限裁行装填，装不下就整体降 cap 再试；
    # 其余小节只在剩余预算里追加（装不下降级为指针）。
    for cap in (ROLE_SECTION_MAX_LINES, 16, 12, 9, 6, 4, 3, 2):
        trial: list[str] = []
        trial_trim: list[str] = []
        for i in core:
            trial.extend(render_block(i, cap))
        for i in extra:
            # 非必保小节用更小的行上限，让「工作流程」这类关键小节也能挤进预算
            block = render_block(i, min(cap, ROLE_EXTRA_SECTION_MAX_LINES))
            if len("\n".join(head + trial + block).encode("utf-8")) > budget:
                trial_trim.append(_clean_heading(secs[i][0]))
                continue
            trial.extend(block)
        size = len("\n".join(head + trial).encode("utf-8"))
        included = len(core) + len(extra) - len(trial_trim)
        # 先比「内嵌了多少小节」，再比「装了多少字节」——宁可每节短一点，也别把
        # 工作流程这类关键小节整节省掉
        rank = (included, size)
        if size <= budget and (best is None or rank > best[0]):
            best = (rank, trial, trial_trim)
    if best is not None:
        _, body, trimmed = best
    tail = [f"「{_clean_heading(secs[i][0])}」" for i in rest]
    if trimmed:
        tail.extend(trimmed)
    if tail:
        body.append(f"> 其余纪律见 `{rel}`：" + "、".join(tail))
    return "\n".join(head + body)


def cmd_init(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    base = docs_root(project, feature)
    package = Path(args.package).resolve()
    tpl = package / "templates"
    if base.exists() and (base / "state.json").exists() and not args.force:
        die(f"{base} 已初始化（state.json 存在）。要重来请加 --force（会保留已有文档）。")

    for d in ["", "planning", "evidence", "releases", "handoffs"]:
        (base / d).mkdir(parents=True, exist_ok=True)

    mapping = {
        "DESIGN.md": base / "DESIGN.md",
        "SOURCE-PLAN.md": base / "planning" / "SOURCE-PLAN.md",
        "COORDINATION-PLAN.md": base / "planning" / "COORDINATION-PLAN.md",
        "EXECUTION-WORKPLAN.md": base / "planning" / "EXECUTION-WORKPLAN.md",
        "VALIDATION-WORKPLAN.md": base / "planning" / "VALIDATION-WORKPLAN.md",
        "EXECUTION-PLAN.md": base / "EXECUTION-PLAN.md",
        "DEPLOYMENT-PLAN.md": base / "DEPLOYMENT-PLAN.md",
        "ACCEPTANCE.md": base / "ACCEPTANCE.md",
    }
    created, kept = [], []
    for name, dest in mapping.items():
        if dest.exists():
            kept.append(str(dest.relative_to(base)))
            continue
        src = tpl / name
        if src.exists():
            text = src.read_text(encoding="utf-8")
        else:
            text = f"# {name.replace('.md','')}（{{{{FEATURE}}}}）\n\n> 未找到模板 <{src}>，请手工补全。\n"
        text = (text.replace("{{FEATURE}}", feature)
                    .replace("{{PROJECT}}", project.as_posix())
                    .replace("{{DATE}}", now_iso()[:10]))
        dest.write_text(text, encoding="utf-8", newline="\n")
        created.append(str(dest.relative_to(base)))

    pack_info = None
    if getattr(args, "kind", "project") == "plugin":
        pack_info = scaffold_plugin_pack(project, feature, package, args)

    # G1（W11）：`.graphifyignore` 由 init 维护，所以「文件真实存在」时就该进 state.scope，
    # 否则 audit 会一直把它记成「不在声明写范围内」。先维护文件、再据文件存在与否决定 scope。
    # **两条死路钉死在这里**：
    #   ① 不许用 `baseline --scope` 改 scope —— 它会把 baseline.roots 从 ["."] 缩小成指定目录，
    #      越界审计当场失效（E15③ 会逐字核对 roots 仍是 ["."]）；
    #   ② 不许让 `freeze --scope` 回写 scope —— freeze 的 --scope 只是本次收集范围，语义不同。
    no_graph = bool(getattr(args, "no_graph", False))
    ignore_msgs: list[str] = []
    if not no_graph:
        ignore_msgs = _ensure_graphifyignore(project / ".graphifyignore")
    auto_scoped_ignore = False

    # 根级文档默认进 scope；显式 --scope 是追加，不覆盖用户给的范围（老项目 state.json 不动）。
    # C002/P9：`--scope` 是 action="append"，用户常写成 `--scope "tools,ops"`（整串一个元素）。
    # 这里按逗号拆分 → strip → 丢弃空串 → 去重（保持首次出现顺序），等价于 `--scope tools --scope ops`；
    # 否则 state.scope 会存成一条 "tools,ops"，audit 逐条比对时就判 tools/* 不在声明写范围内。
    scope: list[str] = []
    comma_split = False
    for item in (args.scope or []):
        raw = str(item)
        parts = raw.split(",")
        if len(parts) > 1:
            comma_split = True
        for part in parts:
            name = part.strip()
            if not name or name in scope:
                continue
            scope.append(name)
    if comma_split:
        print(f"ℹ --scope 里的逗号已拆成独立条目: {', '.join(scope)}")
    if not scope:
        scope = ["pack"] if getattr(args, "kind", "project") == "plugin" else ["."]
    for doc in ROOT_SCOPE_DOCS:
        if doc not in scope:
            scope.append(doc)
    if (project / ".graphifyignore").is_file() and ".graphifyignore" not in scope:
        scope.append(".graphifyignore")
        auto_scoped_ignore = True
    st = {
        "schema": SCHEMA_STATE,
        "feature": feature,
        "project": project.as_posix(),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "phase": "DESIGN",
        "blocked": None,
        "scope": scope,
        "sources": [str(Path(s).resolve()) for s in (args.source or [])],
        "current_candidate": None,
        "candidates": {},
        "actors": {},
        "generation": 1,
        "next_seq": 1,
        "history": [],
    }
    (base / "baseline.json").write_text(
        json.dumps({"schema": SCHEMA_BASELINE, "created_at": None, "roots": scope, "files": {}},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (base / "ledger.md").write_text(
        f"# 台账：{feature}\n\n", encoding="utf-8", newline="\n")
    append_history(st, "init", "lead", f"scope={scope or '(整个项目)'}")
    if auto_scoped_ignore:
        append_history(st, "scope-add", "lead", ".graphifyignore（init 自动追加：init 维护该文件）")
    save_state(project, feature, st)

    print(f"✓ 已初始化 {base}")
    print(f"  新建文档 {len(created)} 个: {', '.join(created) if created else '(无)'}")
    if kept:
        print(f"  已存在跳过 {len(kept)} 个: {', '.join(kept)}")
    print("\n下一步：")
    print(f"  1) 先记录基线: $PY tools/dsh_flow.py baseline -p \"{project}\" -f {feature}")
    print(f"  2) 看交接包:   $PY tools/dsh_flow.py next -p \"{project}\" -f {feature}")
    # 建图是默认步骤（graphify 的 AST 提取只需数秒，且失败只降级、不阻断）；
    # gitnexus analyze 在非 git 目录上会空转十几分钟，**仍然只打印提示、不自动执行**。
    proj_posix = project.as_posix()
    is_git = (project / ".git").exists()
    graph_lines: list[str] = []
    if no_graph:
        print("\n建图（--no-graph：未维护 .graphifyignore、未建图；下面是手工命令）：")
    else:
        graph_lines.extend(ignore_msgs)  # 文件维护在 scope 计算之前已完成（G1）
        try:
            timeout = int(getattr(args, "graph_timeout", GRAPH_TIMEOUT_DEFAULT) or GRAPH_TIMEOUT_DEFAULT)
        except (TypeError, ValueError):
            timeout = GRAPH_TIMEOUT_DEFAULT
        graph_lines.extend(_run_graphify(project, timeout))
        print("\n建图（graphify 已自动执行；gitnexus 只打印提示）：")
        for line in graph_lines:
            print(line)
        if auto_scoped_ignore:
            print("  scope  ：已自动追加 `.graphifyignore`（init 维护该文件，audit 不再报越界）")
    print(f"  graphify : graphify \"{proj_posix}\"")
    print("             → 输出 graphify-out/graph.json；每个仓库各一张图，MCP 调用要带 project_path")
    print(f"  gitnexus : & \"D:\\Tools\\gitnexus\\gitnexus.cmd\" analyze "
          f"\"{proj_posix}\" --skip-git")
    print("             → 必须走 wrapper（内含 OpenSSL 3 的 PATH），裸 gitnexus 会让 FTS 退回 "
          "『FTS extension failed』")
    if is_git:
        print("             → 本项目已是 git 仓库，可去掉 --skip-git 以启用 detect_changes")
    else:
        print("             → 本项目不是 git 仓库：analyze 不带 --skip-git 会空转十几分钟后报 "
              "『Not inside a git repository』")
    if pack_info:
        print(f"\n✓ 能力包骨架已生成：{pack_info['pack']}")
        print(f"  新建 {len(pack_info['created'])} 个文件"
              + (f"，跳过已存在 {len(pack_info['kept'])} 个" if pack_info["kept"] else ""))
        if pack_info["leftovers"]:
            print(f"  ⚠ 仍有未替换占位符：{', '.join(pack_info['leftovers'])}")
        print(f"  包名 {pack_info['name']} ｜ 能力 id {pack_info['id']} ｜ 版本 {pack_info['version']}")
        smoke = pack_info["pack"] / "scripts" / "smoke.mjs"
        print("\n能力包收尾（顺序固定）：")
        print(f"  1) 自检:      node \"{smoke}\"")
        print(f"  2) 安装:      plugin_manager install_bundle target=\"{pack_info['pack']}\"")
        print(f"  3) 重启 DSH:  宿主半（index.js / cordis.patch.yml）改动必须重启才生效")
        print(f"  4) 握手:      $PY tools/dsh_flow.py handshake -p \"{project}\" -f {feature} "
              f"--id <候选> --expect {pack_info['version']} "
              f"--url http://127.0.0.1:<端口>/api/{pack_info['id']}/health")
        print("  握手 FAIL 先看 ops/host-restart-sop.md；冻结时记得带 "
              f"--runtime-kind plugin --runtime-version {pack_info['version']} --health-url <地址>")


def cmd_scope(args) -> None:
    """G1-b：给已有 feature 补正声明写范围（只追加 state.scope，**不动 baseline.json**）。

    为什么需要它：`.graphifyignore` 是 `init` 维护的工具配置，早期 feature 的 scope 里没有它，
    于是 `audit` 每次都报「不在声明写范围内」。修法只有「追加声明」，绝不能走这两条死路：
      - `baseline --scope` 会把 `baseline.roots` 从 `["."]` 缩小成指定目录 → 越界审计当场失效；
      - `freeze --scope` 只是本次收集范围，不回写 scope（语义混淆）。
    """
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    raw_adds = list(args.add or [])
    if not raw_adds:
        print("✗ scope 需要 --add <相对路径>（可多次，相对项目根）", file=sys.stderr)
        print(f'  用法：scope -p "{project.as_posix()}" -f {feature} --add .graphifyignore', file=sys.stderr)
        sys.exit(2)
    cur = list(st.get("scope") or [])
    added: list[str] = []
    skipped: list[str] = []
    for raw in raw_adds:
        p = (raw or "").strip().strip('"')
        if not p:
            die("--add 不能是空路径", 2)
        if Path(p).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", p) or p.startswith(("\\\\", "/")):
            die(f"--add 只接受相对项目根的路径，收到绝对路径: {p!r}", 2)
        if ".." in p.replace("\\", "/").split("/"):
            die(f"--add 不许含 `..`（不能跳到项目外）: {p!r}", 2)
        if re.search(r"[*?\[\]]", p):
            die(f"--add 不许含通配符（scope 是目录/文件前缀，不是模式）: {p!r}", 2)
        norm = p.replace("\\", "/").strip("/")
        if not (project / norm).exists():
            die(f"--add 指向的路径不存在：{norm}（相对项目根 {project.as_posix()}）", 2)
        if norm in cur:
            skipped.append(norm)
            append_history(st, "scope-add", args.actor, f"{norm} (skip:duplicate)")
            continue
        cur.append(norm)
        added.append(norm)
        append_history(st, "scope-add", args.actor, norm)
    if added:
        st["scope"] = cur
    save_state(project, feature, st)
    for a in added:
        print(f"  ✓ 已追加写范围：{a}")
    for s in skipped:
        print(f"  - 已在写范围内（跳过）：{s}")
    print(f"✓ scope 现为：{', '.join(st.get('scope') or []) or '(空)'}")
    print("  baseline.json 未改动（roots 保持原样；越界审计仍然覆盖整个项目）")


def scan_dir(base_dir: Path) -> dict[str, dict]:
    """扫描一个目录，返回 {相对路径: {sha256, bytes}}（跳过依赖/缓存/文档）。"""
    out: dict[str, dict] = {}
    for rel, p in iter_scope_files(base_dir, ["."]):
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > MAX_HASH_BYTES:
            continue
        out[rel] = {"sha256": sha256_file(p), "bytes": size}
    return out


def _external_map(bl: dict) -> dict[str, dict]:
    """兼容两种 external 形态：旧 `{path: files}` 与新 `[{path, files, ...}]`。"""
    ext = bl.get("external") or {}
    if isinstance(ext, dict):
        return {str(k): (v or {}) for k, v in ext.items()}
    out: dict[str, dict] = {}
    if isinstance(ext, list):
        for item in ext:
            if isinstance(item, dict) and item.get("path"):
                out[str(item["path"])] = item.get("files") or {}
    return out


DOCS_META_NAMES = ("DESIGN.md", "ACCEPTANCE.md", "ledger.md", "state.json", "health.json")


def collect_docs_meta(project: Path, feature: str) -> dict[str, dict]:
    """文档层凭证：收口文件（DESIGN/ACCEPTANCE/ledger/state/health）+ 封存件（verification/RELEASE-REPORT）。

    `baseline` 记录它，`audit` 用它发现「文档层被改」——源码审计排除 `docs/`，
    这里是 docs 元数据唯一的留痕手段（D5 盲区的补丁）。
    """
    base = docs_root(project, feature)
    out: dict[str, dict] = {}

    def add(p: Path) -> None:
        if p.is_file():
            try:
                out[posix_rel(p, project)] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
            except OSError:
                pass

    for name in DOCS_META_NAMES:
        add(base / name)
    rel_dir = base / "releases"
    if rel_dir.is_dir():
        for p in sorted(rel_dir.glob("*/verification.json")):
            add(p)
        for p in sorted(rel_dir.glob("*/RELEASE-REPORT.md")):
            add(p)
    return out


def sealed_record_sha(base: Path, rel: str) -> str | None:
    """取 `releases/<C>/verification.json` 里 `rel` 在 seal 时记录的 sha256。

    `audit` 判「封存件是不是真被改」靠它：记录与现状一致 = seal 的正常回写；
    查不到记录（或 verification.json 缺失/不可解析）= 无法证明，调用方按「被改」处理。
    """
    want = str(rel).replace("\\", "/")
    m = re.search(r"(?:^|/)releases/([^/]+)/", want)
    if not m:
        return None
    vp = base / "releases" / m.group(1) / "verification.json"
    if not vp.is_file():
        return None
    try:
        v = read_json(vp)
    except Exception:
        return None
    for f in (v.get("files") or []):
        if isinstance(f, dict) and str(f.get("path") or "").replace("\\", "/") == want:
            return f.get("sha256")
    return None


def _discover_external_sources(project: Path) -> list[tuple[Path, str]]:
    """项目根只有 docs/ 时（插件/能力包项目），推断源码可能在哪。"""
    found: dict[str, str] = {}
    parent = project.parent
    base = project.name
    if parent.is_dir():
        for p in sorted(parent.iterdir()):
            if not p.is_dir() or p.name == project.name:
                continue
            for suf, reason in (("-dev", "兄弟开发副本"), ("-worktree", "git 工作树"),
                                ("-src", "外部源码目录"), ("-pack", "能力包目录")):
                if p.name.startswith(base + suf):
                    found.setdefault(str(p.resolve()), reason)
    # package.json 的 link:/file: 依赖（指向项目外）
    manifests = [project / "package.json"] + [Path(x) / "package.json" for x in list(found)]
    for pj in manifests:
        if not pj.exists():
            continue
        try:
            data = read_json(pj)
        except Exception:
            continue
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            for _name, spec in (data.get(section) or {}).items():
                if not isinstance(spec, str) or ":" not in spec:
                    continue
                scheme, target = spec.split(":", 1)
                if scheme not in ("link", "file"):
                    continue
                tp = Path(target)
                if not tp.is_absolute():
                    tp = (pj.parent / tp).resolve()
                try:
                    tp.relative_to(project)
                    continue  # 项目内，不算外部源
                except ValueError:
                    pass
                if tp.is_dir():
                    found.setdefault(str(tp), "package.json link 目标")
    return [(Path(k), v) for k, v in sorted(found.items())]


def cmd_baseline(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    if getattr(args, "docs_only", False):
        bp = baseline_path(project, feature)
        if not bp.exists():
            die("没有基线，无法只更新 docs 元数据；先跑一次完整 baseline。")
        bl = read_json(bp)
        bl["docs_meta"] = {"created_at": now_iso(),
                           "files": collect_docs_meta(project, feature)}
        write_json(bp, bl)
        append_history(st, "baseline-docs", "lead",
                       f"只更新 docs 元数据（{len(bl['docs_meta']['files'])} 个文件），源码基线不动")
        save_state(project, feature, st)
        print(f"✓ docs 元数据已更新（{len(bl['docs_meta']['files'])} 个受跟踪文件）；源码基线保持不变")
        return
    if args.scope:
        st["scope"] = args.scope
    # 基线默认覆盖整个项目（排除 docs 与依赖/缓存目录），这样越界改动才查得出来；
    # 候选冻结仍使用声明写范围（state.scope）。
    roots = args.scope or ["."]
    files: dict[str, dict] = {}
    skipped_large = []
    for rel, p in iter_scope_files(project, roots):
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > MAX_HASH_BYTES:
            skipped_large.append(rel)
            continue
        files[rel] = {"sha256": sha256_file(p), "bytes": size}

    # 插件类项目的源码常不在项目根（项目根只有 docs/）：
    # 显式 --source 优先；否则在「项目根没有任何源码文件」时自动发现兄弟目录/link 目标。
    # `.graphifyignore` 是 `init` 自己维护的工具配置文件（同 graphify-out/ 一类），
    # 它出现在项目根不代表「本项目有源码」，否则 docs-only 项目的自动发现会被它关掉。
    source_files = {k: v for k, v in files.items() if k not in TOOL_ARTIFACT_FILES}
    sources: list[tuple[Path, str]] = []
    explicit = [str(Path(s).resolve()) for s in (args.source or [])]
    if explicit:
        sources = [(Path(s), "显式 --source") for s in explicit]
    elif not source_files and not args.no_auto:
        sources = _discover_external_sources(project)
        if sources:
            print("  自动发现外部源（项目根没有源码文件）：")
            for sp, reason in sources:
                print(f"    - {sp.as_posix()}  [{reason}]")
    st["sources"] = sorted({sp.as_posix() for sp, _ in sources})
    save_state(project, feature, st)

    external: list[dict] = []
    for sp, reason in sources:
        if sp.is_dir():
            external.append({
                "path": sp.as_posix(),
                "files": scan_dir(sp),
                "created_at": now_iso(),
                "discovered_by": reason,
            })
        else:
            print(f"  ⚠ 源目录不存在，跳过: {sp.as_posix()}")
    data = {
        "schema": SCHEMA_BASELINE,
        "created_at": now_iso(),
        "roots": roots or ["."],
        "files": files,
        "external": external,
        "docs_meta": {"created_at": now_iso(), "files": collect_docs_meta(project, feature)},
        "skipped_large": skipped_large,
    }
    write_json(baseline_path(project, feature), data)
    n_ext = sum(len(e["files"]) for e in external)
    n_docs = len((data.get("docs_meta") or {}).get("files") or {})
    append_history(st, "baseline", "lead",
                   f"{len(files)} 个项目文件 + {n_ext} 个外部源文件，roots={roots or ['.']}")
    save_state(project, feature, st)
    print(f"✓ 基线已写入 {baseline_path(project, feature)}")
    print(f"  项目内 {len(files)} 个文件；roots={roots or ['.']}；"
          f"外部源 {n_ext} 个文件（{len(external)} 个目录）；文档层 {n_docs} 个受跟踪文件")
    for e in external:
        print(f"    - {e['path']}  [{e['discovered_by']}]")
    if not files and not external:
        print("  ⚠ 项目内 0 文件且没有外部源：插件类项目请用 "
              "`baseline --source <源码目录>`，或确认兄弟目录名是 `<项目名>-dev`")
    if skipped_large:
        print(f"  ⚠ 超过 {MAX_HASH_BYTES // 1024 // 1024}MB 跳过 {len(skipped_large)} 个: {skipped_large[:5]}")


def _guess_role(rel: str) -> str:
    low = rel.lower()
    if low.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".ps1", ".psm1", ".go", ".rs", ".java", ".cs", ".c", ".cpp", ".h", ".sh", ".sql")):
        return "source"
    if "test" in low or low.endswith(("_test.py", ".test.js", ".spec.ts")):
        return "test"
    if low.endswith((".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".env", ".xml")):
        return "config"
    if low.endswith((".md", ".txt", ".rst")):
        return "doc"
    return "asset"


# --------------------------------------------------------------------------- #
# A 组：只读静态检查（挂在 freeze 内，DESIGN §5.1 / §5.2）
# --------------------------------------------------------------------------- #
# **铁律**：`python -B` 只关掉「导入时写字节码」，`py_compile` 仍会在源文件旁建
# `__pycache__`；必须同时把 `PYTHONPYCACHEPREFIX` 指到临时目录（已实测：源目录 0 命中）。
# 落进 `releases/<C>/files/` 会让 `verify` 判「候选被篡改」——那是硬失败，不是软告警。
QC_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".json", ".yml", ".yaml"}
QC_FILE_TIMEOUT = 20      # 单文件超时（秒）：超时记 skip，不中断
QC_TOTAL_BUDGET = 180     # 整轮预算（秒）：超预算余下记 skip（备注「超预算」）
QC_ESM_HINTS = ("Cannot use import statement outside a module", "Unexpected token 'export'")
QC_MAX_JSON_BYTES = MAX_HASH_BYTES  # 与 MAX_HASH_BYTES 对齐，避免 OOM
# C002（QC 假阳性修复）：模板骨架判据与 `!!js` 标签容忍
QC_TEMPLATE_PREFIX = "templates/"   # 模板骨架目录前缀（相对候选 files/，判据见 _qc_template_reason）
QC_PLACEHOLDER_HEAD = 65536         # 占位符探测只读前 64KB（大文件不整读）
QC_JS_TAG = "!!js"                  # Cordis bundle patch 的 JS 表达式标签（有意写法，不是语法错）
_QC_YAML_LOADER = None              # 进程内缓存的 SafeLoader 子类（见 _qc_yaml_loader）


def _qc_run(cmd: "list[str]", env=None, stdin_bytes: "bytes | None" = None) -> "tuple[int | None, str]":
    """跑一条只读检查命令，返回 (退出码 | None=超时/无法启动, 完整 stderr)。"""
    try:
        if stdin_bytes is None:
            p = subprocess.run(cmd, capture_output=True, env=env, timeout=QC_FILE_TIMEOUT)
        else:
            p = subprocess.run(cmd, input=stdin_bytes, capture_output=True, env=env,
                               timeout=QC_FILE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"超时（>{QC_FILE_TIMEOUT}s）"
    except (FileNotFoundError, OSError, PermissionError) as e:
        return None, f"无法启动（{type(e).__name__}）"
    return p.returncode, (p.stderr or b"").decode("utf-8", "replace")


def _qc_pycache_hits(root: Path, limit: int = 20) -> "list[str]":
    """递归找 `__pycache__` 目录（其余 `SKIP_DIR_NAMES` 照常跳过）。

    只报告、**不删除**：删除属破坏性操作，交执行线程用 `Remove-Item -LiteralPath` 处理
    （DESIGN §5.2 末段）。`__pycache__` 本身在 `SKIP_DIR_NAMES` 里，所以必须单独判。
    """
    hits: list[str] = []
    if not root.is_dir():
        return hits
    for dirpath, dirnames, _filenames in os.walk(root):
        keep: list[str] = []
        for d in dirnames:
            if d == "__pycache__":
                hits.append((Path(dirpath) / d).as_posix())
            elif d not in SKIP_DIR_NAMES:
                keep.append(d)
        dirnames[:] = keep
        if len(hits) >= limit:
            break
    return hits


def _qc_yaml_loader(yaml):
    """返回一个**容忍 `!!js` 自定义标签**的 `SafeLoader` 子类（进程内只建一次）。

    `!!js`（`tag:yaml.org,2002:js`）是 Cordis bundle patch 的**有意写法**：值里放一段 JS
    表达式字符串，由 Loader 求值。它不是 YAML 语法错误，但 PyYAML 的 `SafeLoader` 没有该标签的
    构造器，`yaml.safe_load` 会直接抛
    `ConstructorError: could not determine a constructor for the tag 'tag:yaml.org,2002:js'`。
    C001 据此把根 `cordis.patch.yml` 判成 `fail` 是**假阳性**（见 RELEASE-REPORT 已知问题第 1 条）。

    这里只做一件事：**认得**这个标签并原样返回字符串（不求值、不执行、不构造任意对象），
    安全姿态与 `SafeLoader` 一致——所有其它标签的行为一个字节没变。
    """
    global _QC_YAML_LOADER
    if _QC_YAML_LOADER is not None:
        return _QC_YAML_LOADER

    class _FlowSafeLoader(yaml.SafeLoader):
        """SafeLoader 子类：只多认 `tag:yaml.org,2002:js`。"""

    def _construct_js(loader, node):
        # 标量（`!!js "…"`）→ 原字符串；复合节点保守返回 None（不构造任何对象）
        return loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else None

    _FlowSafeLoader.add_constructor("tag:yaml.org,2002:js", _construct_js)
    _QC_YAML_LOADER = _FlowSafeLoader
    return _QC_YAML_LOADER


def _qc_yaml_load(yaml, text: str) -> "tuple[int | None, str, str]":
    """用容忍 `!!js` 的 SafeLoader 解析 yaml，返回 `(退出码 | None=skip, 错误首行, 备注)`。

    判据（三条，**不新增硬门禁**）：
    - 解析成功 → `pass`（文件若用了 `!!js`，备注写「已容忍 !!js 标签」，让读者知道判据与裸
      `safe_load` 不同）；
    - 仍失败但文件确实写了 `!!js` → `skip` + 原因（**不许再当语法错误**：可能只是本机 PyYAML
      对其它自定义标签的处理差异，不能据此判代码坏）；
    - 仍失败且文件没用 `!!js` → `fail`（`bad.yml` 这类真语法错的判据保持不变）。
    """
    try:
        yaml.load(text, Loader=_qc_yaml_loader(yaml))
        return 0, "", ("已容忍 !!js 自定义标签" if QC_JS_TAG in text else "")
    except Exception as e:
        if QC_JS_TAG in text:
            return None, f"{type(e).__name__}: {e}", "文件用了 !!js 但解析仍未通过 → 按 skip 记（非语法错误判据）"
        return 1, f"{type(e).__name__}: {e}", ""


def _qc_has_placeholder(path: Path) -> bool:
    """文件是否含未替换的 `{{...}}` 模板占位符（只读前 `QC_PLACEHOLDER_HEAD` 字节）。"""
    try:
        with path.open("rb") as f:
            head = f.read(QC_PLACEHOLDER_HEAD)
    except (OSError, PermissionError):
        return False
    text = head.decode("utf-8", "ignore")
    return "{{" in text and "}}" in text


def _qc_template_reason(rel: str, path: Path, code: "int | None") -> str:
    """失败项若属「模板骨架」返回备注（调用方据此把结果从 `fail` 降为 `skip`），否则返回空串。

    **为什么用路径前缀当主判据**：`templates/**` 下的文件整体是骨架（`{{PACK_ID}}` 这类占位符
    本来就要部署时才替换），它们不是可直接编译的代码——用「内容含 `{{`」当唯一判据会**漏掉**
    恰好没有占位符、但仍然是模板的骨架文件（例如只含说明性 yaml 的 `cordis.patch.yml`），
    判据会随模板内容漂移。内容判据作为**兜底**保留：路径不在 `templates/` 下却留着未替换
    `{{...}}` 的文件（被挪出模板目录的骨架）同样不算代码缺陷，备注里写明它是因为「挪了位置」
    才走到兜底分支。

    **只对失败项生效**：能通过检查的模板文件仍记 `pass`（那是真跑出来的结果，不丢信息）。
    这样 C002 的 QC 是「pass 数上去、fail 降到 0」，而不是把所有模板一律涂成 skip。
    """
    if code in (0, None):
        return ""
    if rel.startswith(QC_TEMPLATE_PREFIX):
        return "模板骨架，含占位符，不可直接编译（路径前缀 templates/）"
    if _qc_has_placeholder(path):
        return "非 templates/ 路径但含未替换 {{...}} 占位符，按模板骨架判 skip"
    return ""


def _qc_static(files_dir: Path, out_path: Path, *, skip: bool = False) -> dict:
    """对 `releases/<C>/files/` 做只读静态检查并渲染 `evidence/<C>/QC-static.md`。

    **绝不新增硬门禁**：任何失败只写进证据文件与 `freeze` 回显，不改 `freeze` 退出码。
    返回统计 dict（供 `freeze` 回显）：files/pass/fail/skip/failed_categories/pycache。
    """
    summary = {"files": 0, "pass": 0, "fail": 0, "skip": 0,
               "failed_categories": [], "pycache": 0, "skipped": bool(skip)}
    if skip:
        print("  ⚠ 已按 --skip-qc 跳过只读静态检查（本候选没有 QC-static 证据）")
        return summary

    project = None
    for anc in out_path.parents:
        if anc.name == "docs":
            project = anc.parent
            break

    cache_prefix = tempfile.mkdtemp(prefix="dsh-flow-qc-")
    env = dict(os.environ)
    env["PYTHONPYCACHEPREFIX"] = cache_prefix
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    node = shutil.which("node")
    try:
        import yaml  # 本机 PyYAML 6.0.3 可用；不可用就整类 skip（不得写 pass）
    except Exception:
        yaml = None

    rows: "list[tuple[str, str, str, str, str, str]]" = []
    counts = {"pass": 0, "fail": 0, "skip": 0}
    categories: "dict[str, int]" = {}
    failed_categories: "list[str]" = []
    other = 0
    tpl_skips = 0     # 模板骨架降级为 skip 的条数（C002；只用于结论行自述，不进 fail 计数）
    started = time.monotonic()
    files = sorted(p for p in files_dir.rglob("*") if p.is_file()) if files_dir.is_dir() else []

    def record(rel, category, cmd, code, note="", *, as_skip=False):
        # `as_skip=True`：模板骨架的失败项（判据见 _qc_template_reason）。**保留退出码**作证据，
        # 只把「结果」从 fail 降为 skip——读表的人既能看见它确实没编译过，也不会把它当代码缺陷。
        if as_skip:
            result = "skip"
            shown = "-" if code is None else str(code)
        elif code is None:
            result = "skip"
            shown = "-"
        else:
            result = "pass" if code == 0 else "fail"
            shown = str(code)
        counts[result] += 1
        if result == "fail" and category not in failed_categories:
            failed_categories.append(category)
        rows.append((rel, category, cmd, shown, result, note))

    try:
        for p in files:
            rel = p.relative_to(files_dir).as_posix()
            yaml_note = ""      # 只有 yaml 分支会写（`!!js` 容忍说明），其余类别保持空
            suffix = p.suffix.lower()
            if suffix not in QC_SUFFIXES:
                other += 1
                continue
            category = {".py": "py", ".js": "js", ".mjs": "js", ".cjs": "js",
                        ".json": "json", ".yml": "yaml", ".yaml": "yaml"}[suffix]
            categories[category] = categories.get(category, 0) + 1
            if time.monotonic() - started > QC_TOTAL_BUDGET:
                counts["skip"] += 1
                rows.append((rel, category, "（未执行）", "-", "skip",
                             f"超预算（整轮 >{QC_TOTAL_BUDGET}s）"))
                continue
            if category == "py":
                code, err = _qc_run([sys.executable, "-B", "-m", "py_compile", str(p)], env=env)
                cmd = "python -B -m py_compile"
            elif category == "js":
                if not node:
                    counts["skip"] += 1
                    rows.append((rel, category, "（node 不在 PATH）", "-", "skip", "node 不可用"))
                    continue
                code, err = _qc_run([node, "--check", str(p)])
                cmd = "node --check"
                if code != 0 and any(h in (err or "") for h in QC_ESM_HINTS):
                    # 老 Node 对 ESM 报「outside a module」：用 --input-type=module 读同一文件重试一次
                    code2, err2 = _qc_run([node, "--input-type=module", "--check"],
                                          stdin_bytes=p.read_bytes())
                    cmd = "node --input-type=module --check <stdin 重定向同一文件>"
                    code, err = code2, (err2 or err)
            elif category == "json":
                cmd = "json.load"
                if p.stat().st_size > QC_MAX_JSON_BYTES:
                    counts["skip"] += 1
                    rows.append((rel, category, cmd, "-", "skip",
                                 f"文件 > {QC_MAX_JSON_BYTES // 1024 // 1024}MB（避免 OOM）"))
                    continue
                try:
                    with p.open("r", encoding="utf-8-sig") as f:
                        json.load(f)
                    code, err = 0, ""
                except Exception as e:
                    code, err = 1, f"{type(e).__name__}: {e}"
            else:
                # C002：`!!js` 是 Cordis bundle patch 的有意写法，不许再当 YAML 语法错误（见 _qc_yaml_load）
                cmd = "yaml.load(SafeLoader+!!js)"
                if yaml is None:
                    counts["skip"] += 1
                    rows.append((rel, category, "yaml.safe_load", "-", "skip",
                                 "解析器不可用（ImportError: yaml）"))
                    continue
                code, err, yaml_note = _qc_yaml_load(
                    yaml, p.read_text(encoding="utf-8-sig", errors="replace"))
            first = ((err or "").strip().splitlines() or [""])[0]
            note = "；".join(x for x in (first.replace("|", "\\|")[:160], yaml_note) if x)
            tpl = _qc_template_reason(rel, p, code)
            if tpl:
                tpl_skips += 1
                record(rel, category, cmd, code, "；".join(x for x in (note, tpl) if x),
                       as_skip=True)
            else:
                record(rel, category, cmd, code, note)

        # `__pycache__` 自检（releases/<C>/files/ 与项目根；只报告不删除）
        pycache_hits: "list[str]" = []
        for root in ([files_dir] + ([project] if project else [])):
            for h in _qc_pycache_hits(root):
                if h not in pycache_hits:
                    pycache_hits.append(h)
    finally:
        shutil.rmtree(cache_prefix, ignore_errors=True)

    n = sum(counts.values())
    if counts["fail"] or pycache_hits:
        overall = "fail"
    elif counts["pass"]:
        overall = "pass"
    else:
        overall = "skip"

    cand = out_path.parent.name
    lines = [
        f"# QC-static — 候选 {cand} 只读静态检查",
        "",
        "- 检查：QC-static",
        "- 等级：A",
        f"- 结果：{overall}",
        f"- 候选：{cand}",
        f"- 时间：{now_iso()}",
        "- 执行者：freeze（自动）",
        "",
        "## 命令",
        "",
        "```text",
        "python -B -m py_compile <绝对路径>            （PYTHONPYCACHEPREFIX=<临时目录>）",
        "node --check <绝对路径>",
        "node --input-type=module --check <stdin 重定向同一文件>",
        "json.load / yaml.safe_load（同进程内解析）",
        "  ↑ yaml 判据：`yaml.load(Loader=<SafeLoader 子类>)`——只多认 `!!js`（Cordis 的 JS 表达式标签），",
        "    其余标签行为与 safe_load 一致（不求值、不构造任意对象）；用了 `!!js` 仍解析失败 → skip，不判 fail",
        "  ↑ 模板骨架：路径前缀 `templates/`（或非该前缀但含未替换 `{{...}}`）的**失败项** → skip + 备注，",
        "    不进 fail 计数（它们不是可直接编译的代码）；能通过的模板文件仍记 pass",
        "```",
        "",
        "## 逐文件结果",
        "",
        "| 文件 | 类别 | 命令 | 退出码 | 结果 | 备注 |",
        "|---|---|---|---|---|---|",
    ]
    lines.extend(f"| {rel} | {cat} | {cmd} | {code} | {res} | {note} |"
                 for rel, cat, cmd, code, res, note in rows)
    if other:
        lines.append(f"| （其它扩展名 {other} 个文件） | other | 不检查 | - | skip | 只计数不逐文件列 |")
    lines.extend([
        "",
        "## 结论",
        "",
        f"静态检查 {n} 个文件：pass {counts['pass']} / fail {counts['fail']} / skip {counts['skip']}；"
        f"失败类别：{', '.join(failed_categories) if failed_categories else '无'}；明细见本文件上表。",
        f"模板骨架（skip，不进 fail 计数）：{tpl_skips} 个"
        + ("（路径前缀 `templates/` 或含未替换 `{{...}}`；不是可直接编译的代码）" if tpl_skips else ""),
        f"__pycache__ 自检：{len(pycache_hits)}"
        + (f"（发现：{', '.join(pycache_hits[:5])}；QC 不删除，交执行线程用 `Remove-Item -LiteralPath` 清理）"
           if pycache_hits else "（releases/<C>/files/ 与项目根均无命中）"),
        "",
    ])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    summary.update({"files": n, "pass": counts["pass"], "fail": counts["fail"],
                    "skip": counts["skip"], "failed_categories": failed_categories,
                    "pycache": len(pycache_hits)})
    print(f"  QC-static：{n} 个文件 pass {summary['pass']} / fail {summary['fail']} / "
          f"skip {summary['skip']}"
          + (f"（失败类别：{'/'.join(failed_categories)}）" if failed_categories else "")
          + (f"（其中模板骨架 {tpl_skips} 个，不进 fail 计数）" if tpl_skips else "")
          + f" → {out_path.as_posix()}")
    if pycache_hits:
        print(f"  ⚠ __pycache__ 自检发现 {len(pycache_hits)} 个目录（不得留在候选里）："
              f"{', '.join(pycache_hits[:3])}")
    return summary


def parse_evidence(path: Path) -> dict:
    """解析证据文件的三行元信息（`检查/等级/结果`），取不到就用文件名主干兜底。

    2026-11-21（C002）：`检查` 后面允许跟一个 `项` 字——`roles/02-executor.md` §4 与
    `evidence/C001/V*.md` 的既有写法是 `- 检查项：V2（对应 DESIGN P2）`，旧正则只认
    `检查：`，于是**所有按说明书写的证据文件都悄悄退化成文件名主干**（`P18-qc-templates-skip`
    这种），`manifest.evidence[].check_id` 因此既长又对不上 DESIGN 的检查号。
    这里只放宽一个可选的 `项`，向量、其它行为一律不变。
    """
    t = _text(path)
    def grab(pat, default):
        m = re.search(pat, t)
        return m.group(1).strip() if m else default
    return {
        "check_id": grab(r"检查(?:项)?\s*[：:]\s*([A-Za-z0-9_.\-]+)", path.stem),
        "grade": grab(r"等级\s*[：:]\s*([ABCD])", "D"),
        "result": grab(r"结果\s*[：:]\s*(pass|fail|skip|unknown)", "unknown").lower(),
    }


RE_REUSED_PATH = re.compile(r"[\\/]|\.(?:md|py|js|ts|tsx|jsx|json|ps1|psm1|yaml|yml|toml|txt|sh)\b")
RE_REUSED_CHANGE = re.compile(r"未变|未改动|逐字节|模块|文件")
RE_REUSED_JUMP = re.compile(r"上一候选|直接继承|继承上一|C\d{3}\s*已通过")


def _parse_reused_items(items) -> list[dict]:
    """G2（W12）：解析 `--reused "<检查号>:<具体理由>"`（可多次、保序）。

    `checks.reused` 是 manifest 的**既有字段**（`{"new": [...], "reused": []}`），这里只填不改 schema。
    理由质量门是命令行契约（退出码 2，不是阶段门禁）；「跳候选继承」措辞只 `⚠` 不阻断。
    """
    out: list[dict] = []
    for raw in (items or []):
        s = (raw or "").strip()
        if ":" not in s:
            die(f'--reused 需要「检查号:具体理由」，收到 {s!r}', 2)
        check, reason = s.split(":", 1)
        check, reason = check.strip(), reason.strip()
        if not check:
            die(f'--reused 缺检查号：收到 {s!r}', 2)
        if not reason:
            die(f"--reused {check!r} 缺理由：必须写清「为什么可以复用」（具体到模块/文件）", 2)
        if reason.isdigit():
            die(f"--reused {check!r} 的理由是纯数字（{reason}），不构成复用依据", 2)
        if not re.sub(r"[\W_]+", "", reason):
            die(f"--reused {check!r} 的理由全是标点，不构成复用依据", 2)
        if len(re.sub(r"\s+", "", reason)) < 8:
            die(f"--reused {check!r} 的理由太短（去空白后 <8 字符）：{reason!r}", 2)
        # 「跳候选继承」措辞：轻量原则——只警告、不阻断（且不要求它满足下面的具体性门，
        # 因为它本来就**不是**复用，警告才是它该得的待遇）
        if RE_REUSED_JUMP.search(reason):
            print("  ⚠ 这不是复用，是候选间跳跃继承，必须重跑")
            out.append({"check": check, "reason": reason})
            continue
        if not (RE_REUSED_PATH.search(reason) or RE_REUSED_CHANGE.search(reason)):
            die(f"--reused {check!r} 的理由没有可核对线索：要写清哪个模块/文件、"
                f"或说明「未变 / 逐字节 / 未改动」。收到 {reason!r}", 2)
        out.append({"check": check, "reason": reason})
    return out


def cmd_freeze(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    cid = args.id
    if not re.fullmatch(r"C\d{3,}", cid):
        die(f"候选编号必须是 C001 形式，收到 {cid!r}")
    base = docs_root(project, feature)
    rel_dir = base / "releases" / cid
    # 先校验 --reused：坏理由要**在任何写操作之前**就退出码 2（不留半成品候选）
    reused_checks = _parse_reused_items(getattr(args, "reused", None))
    if rel_dir.exists() and not args.force:
        die(f"{rel_dir} 已存在；重复冻结同一候选会破坏『通过结论不跨候选继承』。请用新编号或 --force。")
    src = Path(args.from_).resolve()
    if not src.is_dir():
        die(f"--from 目录不存在: {src}")

    roots = args.scope or scope_roots(st)
    if not roots:
        die("没有 scope：请用 --scope 指定本次候选涉及的目录/文件（例如 --scope src --scope tests）。")
    artifacts = []
    copied = []
    for rel, p in iter_scope_files(src, roots):
        # 排除文档/证据/候选目录本身
        if rel.startswith(("docs/", "releases/", "evidence/", "handoffs/", ".git/")):
            continue
        if p.stat().st_size > MAX_HASH_BYTES:
            print(f"  ⚠ 跳过 > {MAX_HASH_BYTES // 1024 // 1024}MB 文件: {rel}")
            continue
        dest = rel_dir / "files" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        artifacts.append({
            "path": rel,
            "sha256": sha256_file(dest),
            "bytes": dest.stat().st_size,
            "role": _guess_role(rel),
        })
        copied.append(rel)
    if not artifacts:
        die(f"在 {src} 的 scope {roots} 里没有找到任何可冻结文件。")

    # A 组（DESIGN §4.1 落点 2 / §4.3）：产物已复制完 → 只读静态检查 → 落 evidence/<C>/QC-static.md。
    # 必须在下面的「证据扫描」之前：QC 结果靠同一次 freeze 登记进 manifest.evidence。
    # 绝不新增硬门禁：检查失败只写证据文件与 ⚠ 回显，不改 freeze 退出码。
    qc = _qc_static(rel_dir / "files", base / "evidence" / cid / "QC-static.md",
                    skip=bool(getattr(args, "skip_qc", False)))

    # 证据
    ev_dir = base / "evidence" / cid
    evidence = []
    check_ids = []
    if ev_dir.exists():
        for p in sorted(ev_dir.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in {".md", ".txt", ".log", ".json"}:
                continue
            meta = parse_evidence(p)
            rel_ev = posix_rel(p, project)
            evidence.append({
                "check_id": meta["check_id"],
                "file": rel_ev,
                "sha256": sha256_file(p),
                "grade": meta["grade"],
                "result": meta["result"],
                "note": p.stem,
            })
            check_ids.append(meta["check_id"])

    prev = None
    for k in sorted(st.get("candidates") or {}):
        if k != cid:
            prev = k
    install_order = [a["path"] for a in sorted(artifacts, key=lambda x: x["path"])]
    if args.install_order:
        ordered = [x.strip() for x in args.install_order.split(",") if x.strip()]
        install_order = [p for p in ordered if p in install_order] + [p for p in install_order if p not in ordered]
    restart = [x.strip() for x in (args.restart_targets or "").split(",") if x.strip()]
    runtime = None
    if args.runtime_kind and args.runtime_kind != "none":
        runtime = {
            "kind": args.runtime_kind,
            "version": (args.runtime_version or "").strip(),
            "health_url": (args.health_url or "").strip(),
            "requires_restart": bool(args.requires_restart),
        }
        if not runtime["version"]:
            die("声明了 --runtime-kind 就必须给 --runtime-version（否则握手没有期望值）")

    # 能力包/插件项目：没声明 runtime 时不能静默通过（装完无法握手 = 无法自证生效）
    pack = detect_pack(project)
    pack_warnings: list[str] = []
    if pack:
        if runtime is None:
            pack_warnings.extend([
                f"检测到能力包/插件项目（{pack['path']}，{pack['name'] or '未命名'} {pack['version'] or '?'}），"
                "但本候选未声明 runtime。",
                "后果：装完/重启后无法做版本握手，`gate TRIAL` 会把『运行时版本』视为未声明、不计入门禁。",
                "建议：出下一个候选时加 "
                f'`--runtime-kind plugin --runtime-version {pack["version"] or "<package.json version>"} '
                "--health-url <健康检查地址> [--requires-restart]`。",
            ])
        elif pack["version"] and _norm_version(runtime["version"]) != _norm_version(pack["version"]):
            pack_warnings.append(
                f"manifest.runtime.version={runtime['version']} 与 {pack['path']} 的 version={pack['version']} 不一致；"
                "握手按 manifest 的期望值判定，请确认不是漏改版本。"
            )

    manifest = {
        "schema": SCHEMA_MANIFEST,
        "feature": feature,
        "candidate": cid,
        "project": project.as_posix(),
        "created_at": now_iso(),
        "frozen_by": args.actor,
        "note": args.note or "",
        "base": {
            "type": args.base_type,
            "path": src.as_posix(),
            "baseline_ref": "baseline.json" if baseline_path(project, feature).exists() else "",
        },
        "artifacts": artifacts,
        "install_order": install_order,
        "restart_targets": restart,
        "rollback": {
            "preserve": args.preserve or [],
            "restore_from": "previous_candidate" if prev else "baseline",
            "steps": ([f"用 releases/{prev}/files 覆盖回同名路径"] if prev else ["无上一候选，按 baseline.json 还原改动文件"])
                     + ["按 install_order 逆序卸载新增文件", "重启 restart_targets"],
        },
        "evidence": evidence,
        "checks": {"new": check_ids, "reused": reused_checks},
        "gate": {"status": "ready", "blocked_by": []},
        "runtime": runtime,
        "seal_required": True,
    }
    write_json(rel_dir / "manifest.json", manifest)

    # 发布报告占位
    report = rel_dir / "RELEASE-REPORT.md"
    tpl = Path(args.package) / "templates" / "RELEASE-REPORT.md"
    if not report.exists():
        text = tpl.read_text(encoding="utf-8") if tpl.exists() else "# 发布报告 {{CANDIDATE}}\n\n## 待用户试用清单\n\n- （未填）\n\n结论：待用户试用\n"
        text = (text.replace("{{FEATURE}}", feature)
                    .replace("{{PROJECT}}", project.as_posix())
                    .replace("{{CANDIDATE}}", cid)
                    .replace("{{DATE}}", now_iso()[:10]))
        report.write_text(text, encoding="utf-8", newline="\n")

    st.setdefault("candidates", {})[cid] = {
        "status": "frozen",
        "frozen_at": now_iso(),
        "manifest_sha256": sha256_file(rel_dir / "manifest.json"),
        "frozen_by": args.actor,
        "artifacts": len(artifacts),
    }
    st["current_candidate"] = cid
    append_history(st, "freeze", args.actor,
                   f"{cid}: {len(artifacts)} 个产物, {len(evidence)} 条证据, from={src.name}")
    if pack_warnings:
        append_history(st, "freeze-warning", args.actor, pack_warnings[0])
    save_state(project, feature, st)

    print(f"✓ 候选 {cid} 已冻结到 {rel_dir}")
    print(f"  产物 {len(artifacts)} 个，证据 {len(evidence)} 条，安装顺序 {len(install_order)} 项")
    # G7（E21 ④）：落盘后回显「检查号 → 理由」，让 reused 编号笔误（如把 scope 逻辑记成 V11）
    # 当场可见。编号语义无法机器判定，只做回显 + 人工核对，不新增门禁检查。
    for _r in reused_checks:
        print(f"  reused: {_r['check']} → {_r['reason']}")
    if not evidence:
        print("  ⚠ 没有证据文件：验证线程会把它当作不可核验的候选")
    if pack_warnings:
        print("\n  ⚠ 能力包/插件项目的运行时声明有问题（不阻断冻结，但会影响 TRIAL 门禁）：")
        for w in pack_warnings:
            print(f"    - {w}")
    if qc.get("fail"):
        print(f"\n  ⚠ 静态检查：{qc['fail']} 个文件失败"
              f"（类：{'/'.join(qc['failed_categories']) or '?'}），"
              f"明细见 evidence/{cid}/QC-static.md（软告警，不阻断冻结）")
    print("\n下一步（执行线程必须做）：")
    print(f"  $PY tools/dsh_flow.py verify -p \"{project}\" -f {feature} --id {cid}")


def cmd_verify(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    base = docs_root(project, feature)
    cid = args.id
    if not cid:
        st = load_state(project, feature)
        cid = st.get("current_candidate")
        if not cid:
            die("没有当前候选，请用 --id 指定。")
    errors = verify_manifest(base, cid)
    manifest = base / "releases" / cid / "manifest.json"
    if errors:
        print(f"✗ 候选 {cid} 校验失败（{len(errors)} 项）：")
        for e in errors:
            print(f"  - {e}")
        if args.json:
            print(json.dumps({"candidate": cid, "ok": False, "errors": errors}, ensure_ascii=False))
        sys.exit(1)
    m = read_json(manifest)
    print(f"✓ 候选 {cid} 校验通过")
    print(f"  产物 {len(m.get('artifacts') or [])} 个，证据 {len(m.get('evidence') or [])} 条，"
          f"manifest sha256={sha256_file(manifest)[:16]}…")
    # G2 读侧（E16②）：登记了必须**读得到**，不能只写进 manifest 就算完
    _checks = m.get("checks") or {}
    _reused = _checks.get("reused") or []
    print(f"  reused {len(_reused)} 条")
    for _r in _reused[:5]:
        if isinstance(_r, dict):
            print(f"    - {_r.get('check') or _r.get('check_id')}: {str(_r.get('reason') or '')[:90]}")

    # 证据双清单的第二份：verification.json（封存时生成）
    vp = base / "releases" / cid / "verification.json"
    if m.get("seal_required"):
        if not vp.exists():
            print("  ℹ 未 seal：manifest.evidence 只覆盖冻结时的 P*；V* 证据 / 发布报告 / 部署台账"
                  f"尚未封存（`flow.py seal --id {cid}`），`gate TRIAL` 会拦截。")
        else:
            serrs = verify_verification(base, cid)
            if serrs:
                print(f"✗ 封存校验失败（{len(serrs)} 项）：")
                for e in serrs[:10]:
                    print(f"  - {e}")
                if args.json:
                    print(json.dumps({"candidate": cid, "ok": False, "seal_errors": serrs},
                                     ensure_ascii=False))
                sys.exit(1)
            try:
                _vfiles = read_json(vp).get("files") or []
                sealed = len(_vfiles)
                # 旧格式（seal 早于 C004）：封的是共用台账本身，会被下一轮验证线程写红。
                # 只做提示，不改判定——历史红项是事实，不许靠改判据抹平。
                _legacy_ledger = [
                    str(f.get("path")) for f in _vfiles
                    if str(f.get("path") or "").replace("\\", "/").endswith("/DEPLOYMENT-PLAN.md")
                    and "/releases/" not in str(f.get("path") or "").replace("\\", "/")
                ]
            except Exception:
                sealed = 0
                _legacy_ledger = []
            print(f"  ✓ 封存校验通过（verification.json 覆盖 {sealed} 个文件）")
            if _legacy_ledger:
                print(f"  ℹ 旧格式（seal 早于 C004）：本候选封存的是共用台账 {_legacy_ledger[0]}，"
                      "它每轮验证都会被人写；再写一次本候选就会判红，属历史遗留、不是封存件被篡改。"
                      "新候选改封 releases/<C>/DEPLOYMENT-PLAN.md 快照。")
    if args.json:
        print(json.dumps({"candidate": cid, "ok": True, "manifest": m}, ensure_ascii=False))


def cmd_drop(args) -> None:
    """作废候选清理：把 releases/<C> 与 evidence/<C> 移到 archive/ 并从 state 移除。

    只移动、不删除（不变量：已冻结包不可改、也不可凭空消失；archive 里留原件可追）。
    `verify` / `seal` / `advance` 的判据一行不动：只是把一个已作废的候选从「当前候选表」里摘掉，
    否则 `status` 会一直提示它「待重启生效」，把噪音当成待办。
    """
    project = Path(args.project).resolve()
    feature = args.feature
    base = docs_root(project, feature)
    st = load_state(project, feature)
    cid = args.id
    if not re.fullmatch(r"C\d{3,}", cid):
        die(f"候选编号必须是 C001 形式，收到 {cid!r}")
    cands = st.get("candidates") or {}
    if cid not in cands:
        die(f"{cid} 不在 candidates 里（已登记：{', '.join(sorted(cands)) or '(空)'}）。"
            "drop 只处理已登记候选，不会去猜档案目录。")
    info = cands[cid] or {}
    if (info.get("sealed_at") or info.get("status") == "sealed") and not args.force:
        die(f"{cid} 已 seal（sealed_at={info.get('sealed_at')}）。封存件是『通过结论』的载体，"
            "drop 会把它移出 releases/ 让 seal 证据失去落点；确需作废请显式加 --force 并写清理由。")
    if not args.reason.strip():
        die("drop 必须带 --reason：作废候选要留痕，否则后人只看到目录消失。")

    src_rel = base / "releases" / cid
    src_ev = base / "evidence" / cid
    stamp = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
    dest = base / "archive" / f"{cid}-{stamp}"
    if dest.exists():
        die(f"{dest} 已存在；换一次时间戳重跑（同一秒内重复 drop 会覆盖档案）。")
    dest.mkdir(parents=True, exist_ok=True)

    moved: list[str] = []
    for src in (src_rel, src_ev):
        if not src.exists():
            continue
        target = dest / src.parent.name / src.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(target))
        moved.append(posix_rel(target, base))

    note = f"""# DROP {cid}

- 候选：{cid}
- 原状：{json.dumps(info, ensure_ascii=False)}
- 时间：{now_iso()}
- 执行者：{args.actor}
- 理由：{args.reason.strip()}

## 移动了什么（只移动，未删除）

{chr(10).join('- ' + m for m in moved) or '- （releases/ 与 evidence/ 下都没有该候选目录）'}

## 怎么还原

把上面每个目录按原相对路径移回 `{base.as_posix()}/` 即可
（例如 `archive/{dest.name}/releases/{cid}` → `releases/{cid}`）。
"""
    (dest / "DROP-NOTE.md").write_text(note, encoding="utf-8", newline="\n")

    cands.pop(cid, None)
    st["candidates"] = cands
    if st.get("current_candidate") == cid:
        rest = sorted(cands)
        st["current_candidate"] = rest[-1] if rest else None
    append_history(st, "drop", args.actor,
                   f"{cid} 作废归档到 archive/{dest.name}（理由：{args.reason.strip()}）")
    save_state(project, feature, st)

    print(f"✓ {cid} 已从候选中移除，产物移入 {dest}")
    for m in moved:
        print(f"  moved: {m}")
    print(f"  当前候选：{st.get('current_candidate') or '(无)'}；剩余已冻结 {len(cands)} 个")
    print("  ℹ 只移动未删除；还原方法见 " + posix_rel(dest / "DROP-NOTE.md", base))


def _artifact_new_state(cur: dict, art_sha: str | None,
                        freeze_ts: float | None) -> tuple[str, bool]:
    """`audit` 判「已登记的新增」该不该免报（P0-13 补口，flow-audit-hygiene C001）。

    免报必须是**两个正向证据同时成立**：内容与冻结一致（sha256 相等），
    且 `mtime` 证明该文件创建于冻结之前（`<= freeze_ts + 2s`，容忍文件系统时间精度）。

    宽严口径（这是本函数存在的全部理由，改之前先读 DESIGN §3.1）：
    - `mtime` **缺失 → 不免报**。旧实现 `current[rel].get("mtime", 0)` 把缺值当 0，
      等价于「1970 年创建」→ 恒判「冻结前」→ 可以静默放过一个真改过的文件（宽严不对称）。
      输出里明写「mtime 缺失，按严格处理」，不让人猜为什么红。
    - 没有冻结时间戳（旧 manifest / 解析失败）→ 同样无法证明「冻结前」，按严格处理。
    - 内容不一致 → 一律告警（真篡改口径不变，DESIGN §「不改什么」）。

    抽成独立函数是为让 selftest 能直接注入「缺 mtime 的 current 项」（suite X / E4）：
    `current` 由 `cmd_audit` 现场 stat 出来、CLI 层构造不出缺字段的项，只有单元级能压这个分支。
    """
    if cur.get("sha256") != art_sha:
        return "主目录内容与候选冻结内容不一致", True
    mtime = cur.get("mtime")
    if mtime is None:
        return "内容与候选一致，但 mtime 缺失，按严格处理（核对来源）", True
    if freeze_ts is None:
        return "内容与候选一致，但无冻结时间戳，无法证明冻结前（核对来源）", True
    if mtime <= freeze_ts + 2:
        return "开发期新增（已登记，冻结前）", False
    return "内容与候选一致，但 mtime 晚于冻结（核对来源）", True


def cmd_audit(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    base = docs_root(project, feature)
    bp = baseline_path(project, feature)
    if not bp.exists():
        die("没有基线。先运行 baseline；否则无法判断『改了什么』。")
    st = load_state(project, feature)
    bl = read_json(bp)
    if not (bl.get("files") or bl.get("external")):
        die("基线里没有任何文件。插件类项目的源码常在项目根之外，请用 "
            "`baseline --source <源码目录>` 重新记基线（可多次）。")
    old = bl.get("files") or {}
    # `current` 早就跳过 SKIP_DIR_NAMES（iter_scope_files 已滤），旧基线却可能记着它们
    # （新增跳过项之前记的基线，例如 2026-11-22 之前的 51 个 `dsh-bundle-dist/**`）。
    # 不滤基线的话，一加跳过项就会一次性冒出几十条「删除 → 未登记」假红——
    # 那是「口径变了」，不是「文件被删了」（flow-audit-hygiene C001）。
    old = {k: v for k, v in old.items() if not is_skipped(k)}
    roots = bl.get("roots") or ["."]
    current = {}
    for rel, p in iter_scope_files(project, roots):
        try:
            current[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size,
                            "mtime": p.stat().st_mtime}
        except OSError:
            continue
    added = sorted(set(current) - set(old))
    deleted = sorted(set(old) - set(current))
    modified = sorted(k for k in (set(current) & set(old)) if current[k]["sha256"] != old[k]["sha256"])

    cid = st.get("current_candidate")
    artifact_hash: dict[str, str] = {}
    freeze_ts: float | None = None
    if cid:
        mp = base / "releases" / cid / "manifest.json"
        if mp.exists():
            try:
                mdata = read_json(mp)
                for a in mdata.get("artifacts") or []:
                    artifact_hash[a.get("path")] = a.get("sha256")
                ts = mdata.get("created_at")
                if ts:
                    freeze_ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
            except Exception:
                artifact_hash = {}
    declared = scope_roots(st)

    def in_declared(rel: str) -> bool:
        if not declared:
            return True
        for d in declared:
            if d in (".", ""):
                return True
            if rel == d or rel.startswith(d.rstrip("/") + "/"):
                return True
        return False

    rows: list[tuple[str, str, str, bool]] = []
    for kind, items in (("新增", added), ("修改", modified), ("删除", deleted)):
        for rel in items:
            scope_exempt = False
            if rel in artifact_hash:
                if kind == "删除":
                    state, warn = "候选已登记，但主目录里被删了", True
                elif kind == "新增":
                    state, warn = _artifact_new_state(current[rel], artifact_hash[rel], freeze_ts)
                elif current[rel]["sha256"] == artifact_hash[rel]:
                    state, warn = "已登记且与候选一致", False
                else:
                    state, warn = "主目录内容与候选冻结内容不一致", True
            elif rel.replace("\\", "/").endswith(LESSONS_REL):
                # flow.py 的 lesson 子命令是唯一写入口，不是交付物；视为工具生成、预期。
                # P0-14 补口（flow-audit-hygiene C001，2026-11-22）：**连「不在声明写范围」一起免**——
                # `ops/` 往往不在个别 feature 的 scope 里，但 lessons.md 照样会被 lesson 子命令写
                # （实测 `dsh-bundle-dist/ops/lessons.md` 就吃过「工具生成；且不在声明写范围内」）。
                state, warn = "工具生成（lesson 子命令，预期）", False
                scope_exempt = True
            else:
                state, warn = "未登记（越界嫌疑）", True
            if not scope_exempt and not in_declared(rel):
                state += "；且不在声明写范围内"
                warn = True
            rows.append((kind, rel, state, warn))

    # 外部源目录（插件类项目源码常在项目根之外）
    external = _external_map(bl)
    ext_rows: list[tuple[str, str, str, bool]] = []
    ext_counts = {"新增": 0, "修改": 0, "删除": 0}
    for sdir, old_ext in external.items():
        sp = Path(sdir)
        if not sp.is_dir():
            ext_rows.append(("源目录", sdir, "目录不存在（源码被移动或删除）", True))
            continue
        cur_ext = scan_dir(sp)
        for kind, items in (
            ("新增", sorted(set(cur_ext) - set(old_ext))),
            ("修改", sorted(k for k in (set(cur_ext) & set(old_ext))
                            if cur_ext[k]["sha256"] != old_ext[k]["sha256"])),
            ("删除", sorted(set(old_ext) - set(cur_ext))),
        ):
            ext_counts[kind] += len(items)
            for rel in items:
                if rel in artifact_hash:
                    if kind == "修改" and cur_ext[rel]["sha256"] == artifact_hash[rel]:
                        state, warn = "已登记且与候选一致", False
                    elif kind == "新增":
                        state, warn = "候选已登记，但冻结后源目录才出现", True
                    elif kind == "删除":
                        state, warn = "候选已登记，但源目录里被删了", True
                    else:
                        state, warn = "源目录内容与候选冻结内容不一致", True
                else:
                    state, warn = "源目录有未登记改动（越界嫌疑）", True
                ext_rows.append((kind, f"{sdir}/{rel}", state, warn))

    # 文档层（源码审计排除 docs/，这里单独留痕）
    old_docs = (bl.get("docs_meta") or {}).get("files") or {}
    docs_rows: list[tuple[str, str, str, bool]] = []
    docs_counts = {"新增": 0, "修改": 0, "删除": 0}
    if old_docs:
        cur_docs = collect_docs_meta(project, feature)
        for kind, items in (
            ("新增", sorted(set(cur_docs) - set(old_docs))),
            ("修改", sorted(k for k in (set(cur_docs) & set(old_docs))
                            if cur_docs[k]["sha256"] != old_docs[k]["sha256"])),
            ("删除", sorted(set(old_docs) - set(cur_docs))),
        ):
            docs_counts[kind] += len(items)
            for rel in items:
                low = rel.replace("\\", "/")
                if low.endswith(("/verification.json", "/RELEASE-REPORT.md")):
                    # 这两个文件本来就是 freeze/seal 生成的：新增是预期，不告警；
                    # 修改要先查 verification.json 记录哈希——一致才是 seal 的正常回写。
                    # 查不到记录（旧候选没封存过 / JSON 坏了）一律按「被改」告警，不放过真篡改。
                    if kind == "新增":
                        state, warn = "freeze/seal 生成（预期）", False
                    elif kind == "修改":
                        rec_sha = sealed_record_sha(base, rel)
                        cur_sha = (cur_docs.get(rel) or {}).get("sha256")
                        if rec_sha and cur_sha and rec_sha == cur_sha:
                            state, warn = "封存记录与现状一致（seal 回写，预期）", False
                        else:
                            state, warn = ("封存件被改（严重：seal 后不可改；"
                                           "与 verification.json 记录哈希不一致）"), True
                    else:
                        state, warn = "封存件被删（严重：seal 后不可删）", True
                elif low.endswith("/ACCEPTANCE.md"):
                    state, warn = "Lead 回填/验收文档更新（预期，需在 §七 留痕）", False
                elif low.endswith(("/state.json", "/ledger.md")):
                    state, warn = "工具写入（预期）", False
                elif low.endswith("/health.json"):
                    state, warn = "看板/巡检刷新（预期）", False
                elif low.endswith("/DESIGN.md"):
                    state, warn = "方案文档更新（需在变更历史留痕）", False
                else:
                    state, warn = "文档层变化", False
                docs_rows.append((kind, rel, state, warn))

    print(f"审计：{feature}  基线 {bl.get('created_at')}  →  现在")
    print(f"审计范围: {roots}   声明写范围: {declared or '(未声明，按整个项目)'}   当前候选: {cid or '(无)'}")
    print(f"项目内 新增 {len(added)} / 修改 {len(modified)} / 删除 {len(deleted)}")
    if external:
        print(f"外部源 新增 {ext_counts['新增']} / 修改 {ext_counts['修改']} / 删除 {ext_counts['删除']}"
              f"（{len(external)} 个目录）")
    if old_docs:
        print(f"文档层 新增 {docs_counts['新增']} / 修改 {docs_counts['修改']} / 删除 {docs_counts['删除']}"
              f"（{len(old_docs)} 个受跟踪文件）")
    else:
        print("文档层 未登记（旧基线；重新 baseline 后启用 docs 元数据留痕）")
    shown = 0
    for kind, rel, state, warn in rows:
        if shown >= args.limit:
            print(f"  …还有 {len(rows) - shown} 项")
            break
        print(f"  [{kind}] {rel}  — {state}" + (" ⚠" if warn else ""))
        shown += 1
    for kind, rel, state, warn in ext_rows:
        print(f"  [{kind}] {rel}  — {state}" + (" ⚠" if warn else ""))
    for kind, rel, state, warn in docs_rows:
        print(f"  [{kind}] {rel}  — {state}" + (" ⚠" if warn else ""))
    warns = [r for r in rows if r[3]] + [r for r in ext_rows if r[3]] + [r for r in docs_rows if r[3]]
    if warns:
        print(f"\n⚠ {len(warns)} 项需要解释：未登记、内容不符、源目录被改、或在声明范围外。")
        if args.strict:
            sys.exit(1)
    else:
        print("\n✓ 所有改动都在当前候选清单内，且内容与冻结一致。")


def cmd_evidence(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    base = docs_root(project, feature)
    cid = args.candidate or "C001"
    dest = base / "evidence" / cid / f"{args.check}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = args.output or ""
    text = f"""# {args.check} — {args.title}

- 检查：{args.check}
- 等级：{args.grade}
- 结果：{args.result}
- 候选：{cid}
- 时间：{now_iso()}
- 执行者：{args.actor}

## 命令

```
{args.command or '(未记录命令)'}
```

## 输出（原文）

```
{out}
```

## 结论

{args.note or '(一句话说明这条证据证明了什么)'}
"""
    dest.write_text(text, encoding="utf-8", newline="\n")
    print(f"✓ 证据已写入 {dest}")


def cmd_status(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    base = docs_root(project, feature)
    phase = st.get("phase", "?")
    nxt = PHASE_ROLE.get(phase, "?")
    cand = st.get("current_candidate")
    print(f"feature : {feature}")
    print(f"project : {project}")
    print(f"phase   : {phase}   下一角色: {nxt}")
    print(f"候选    : {cand or '(无)'}   已冻结 {len(st.get('candidates') or {})} 个")
    if st.get("design_version"):
        print(f"DESIGN  : v{st['design_version']}   amend {len(st.get('amendments') or [])} 次")
    if st.get("blocked"):
        b = st["blocked"]
        print(f"阻塞    : [{b.get('kind') or '?'}/{b.get('owner')}] {b.get('reason')}  (since={b.get('since')})")
        print(f"          解除：flow.py unblock -p \"{project}\" -f {feature} --note \"...\"")
    # 已装但运行时未确认的候选（典型：插件宿主半没重启）
    pending_rt = []
    for cid_, info in (st.get("candidates") or {}).items():
        rt = manifest_runtime(base, cid_)
        rec = (info or {}).get("runtime") or {}
        if rt.get("requires_restart") and not (
                rec.get("ok") and _norm_version(rec.get("actual")) == _norm_version(rt.get("version"))):
            pending_rt.append(f"{cid_}({rt.get('version')})")
    if pending_rt:
        print(f"待重启生效: {', '.join(pending_rt)}  → 重启 DSH 后跑 handshake，别再出新候选")
    hs = sorted((base / "handoffs").glob("HANDOFF-*.md"), key=lambda p: p.stat().st_mtime) \
        if (base / "handoffs").exists() else []
    if hs:
        print(f"最近交接: {hs[-1].name}")
    if phase == "DONE":
        print("\n✓ 流程已到 DONE。新需求请开新 feature；同一 feature 的下一轮用 advance --to EXECUTING。")
    else:
        print("\n门禁（当前阶段通往下一阶段）:")
        transitions = TRANSITIONS.get(phase, [])
        if transitions:
            target = transitions[0]
            checks = gate_for(project, feature, target)
            for name, ok, detail in checks:
                print(f"  {'✓' if ok else '✗'} {name}" + (f"  — {detail}" if detail and not ok else ""))
            ok_all = all(ok for _, ok, _ in checks) if checks else True
            print(f"\n{'✓ 可以推进到 ' + target if ok_all else '✗ 还不能推进'}")
            # 软告警（DESIGN §5.3）：只打 ⚠，不计入上面的「门禁 N/M」、不影响退出码
            for name, detail in warn_for(project, feature):
                print(f"  ⚠ {name}：{detail}")
    print("\n最近 5 条台账:")
    for h in (st.get("history") or [])[-5:]:
        print(f"  {h['at']} {h['actor']:8s} {h['action']:10s} {h['detail']}")
    if args.json:
        print(json.dumps({"phase": phase, "candidate": cand, "next_role": nxt}, ensure_ascii=False))


def cmd_next(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    package = Path(args.package).resolve()
    st = load_state(project, feature)
    base = docs_root(project, feature)
    phase = st.get("phase", "DESIGN")
    role = args.role or PHASE_ROLE.get(phase, "lead")
    if role == "none":
        print("✓ 流程已结束（DONE）。新需求请开新 feature 或回退到 EXECUTING。")
        return
    if role == "user":
        print("下一步在你（用户）：请试用并回执『通过/不通过』，然后 Lead 执行")
        print(f"  $PY tools/dsh_flow.py advance -p \"{project}\" -f {feature} --to DONE --actor user")
        return
    # --key-note @文件 不存在：命令行参数错误 → 退出码 2（唯一的非零退出情形，不动 state）
    # C002 起 `--key-note` 可多次（`action="append"`），逐个校验、任一不存在即退出码 2。
    for kn in _key_note_items(args):
        if kn.startswith("@"):
            kp = Path(kn[1:].strip().strip('"'))
            if not kp.is_file():
                die(f"--key-note 指向的文件不存在: {kp.as_posix()}", 2)
    seq = st.get("next_seq", 1)
    st["next_seq"] = seq + 1
    doc = role_doc(package, role)
    cand = st.get("current_candidate") or "（尚无）"
    scope = ", ".join(scope_roots(st)) or "（整个项目）"
    blocked_txt = ""
    if st.get("blocked"):
        b = st["blocked"]
        blocked_txt = (f"\n> **当前阻塞**（owner={b.get('owner')}，kind={b.get('kind') or '?'}）：{b.get('reason')}\n"
                       f"> 解除后 Lead 才会推进；你不要绕过它。\n")
    rt = manifest_runtime(base, cand) if cand and cand != "（尚无）" else {}
    rt_txt = ""
    if rt:
        rt_txt = (f"\n> **运行时握手（硬要求）**：装好/重启后必须跑\n"
                  f"> `flow.py handshake --id {cand} --expect {rt.get('version')} --url \"{rt.get('health_url') or '<健康检查地址>'}\"`，\n"
                  f"> PASS 才能把报告结论写成「已上线可试用」；结论为 fail 时先重启 DSH，不要靠出新候选掩盖。\n")
    seal_txt = (f"\n> **收口要求**：报告与部署台账定稿后跑 `flow.py seal --id {cand}` 封存 V* 证据；\n"
                f"> 没封存，Lead 的 `advance --to TRIAL` 会被门禁拒绝。\n"
                f"> **seal 输出记台账**（`ledger.md` 与回报正文），**不要回写报告**——seal 之后报告再动一个字节，\n"
                f"> `verify` 就判「封存后内容被改」，那时只能出新候选。\n") if role == "verifier" else ""
    # ---- 上下文摘要（默认供给；--no-context 关闭）----
    # 两段式：先用占位符渲染其余章节，量出「除上下文外」的字节数，把剩下的预算交给
    # §1（同时受 --max-context-chars 字符预算约束），保证整份交接包 ≤ HANDOFF_MAX_BYTES。
    no_context = bool(getattr(args, "no_context", False))
    try:
        ctx_chars = int(getattr(args, "max_context_chars", DEFAULT_MAX_CONTEXT_CHARS)
                        or DEFAULT_MAX_CONTEXT_CHARS)
    except (TypeError, ValueError):
        ctx_chars = DEFAULT_MAX_CONTEXT_CHARS
    if ctx_chars <= 0:
        ctx_chars = DEFAULT_MAX_CONTEXT_CHARS

    # ---- 角色要点（按阶段裁剪；裁不下来就退回全文并打 ⚠）----
    role_fallback = ("> ⚠ 裁剪失败（角色文件缺失或小节标题对不上），已退回全文内嵌。\n\n"
                     + (doc if doc else '（未找到角色说明书，请让 Lead 检查 roles/ 目录）'))
    role_txt = role_fallback

    mission = f"""# 交接包 {seq:03d} — {role}

> 由 `dsh_flow.py next` 于 {now_iso()} 生成。你是被 Lead 用 `subagent` 派出的**{role}**。
> 你与其他角色不能直接通信；一切交接走磁盘文件与本文件末尾的「交接要求」。
> 你没有当前候选之前的对话历史，只能根据下面的事实开始工作——这正是设计意图。
> **如果 DSH 中途重启、你这个角色被换掉**：直接重派同一交接包，磁盘上的产物与状态不会丢；已完成的批次不要重做。
{blocked_txt}{rt_txt}{seal_txt}

## 0. 硬事实（先看，不要猜）

| 项 | 值 |
|---|---|
| 项目根 | `{project.as_posix()}` |
| feature | `{feature}` |
| 文档目录 | `{base.as_posix()}` |
| 当前阶段 | `{phase}` |
| 当前候选 | `{cand}` |
| 声明写范围（scope） | {scope} |
| 状态文件 | `{state_path(project, feature).as_posix()}` |
| 工具 | `& $PY "{package.as_posix()}/tools/dsh_flow.py" <子命令> -p "{project.as_posix()}" -f {feature}` |

其中 `$PY` = `C:\\Users\\81901\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe`
（若该路径不存在，用 `python`；Shell 用 PowerShell；git 是否可用以 `doctor` 输出为准，可用时优先用 `create_worktree` 开隔离工作树。）

@@CTX@@## 2. 角色要点（按阶段裁剪）

以下内容来自 `roles/{ROLE_FILES.get(role, '')}`：按当前阶段 `{phase}` 只内嵌必要小节，其余小节给指针。
**小节之间冲突时，以 `roles/` 里的完整说明书为准**；你随时可以只读全文。

---

@@ROLE@@

---

## 3. 本次任务（唯一目标）

- 角色：{role}
- 要交付的东西：按角色说明书第 4 节「交接物」执行。
- 进入条件已完成：{args.entry_note or '（由 Lead 确认）'}
- 不允许做的事（违反即视为事故）：
  1. 不修改 `docs/{feature}/state.json`（只能 Lead 用 `advance` 改）；
  2. 不碰其他角色的文件（执行线程不写 RELEASE-REPORT，验证线程不写任何源码）；
  3. 不写 `docs/{feature}/` 以外的路径（除非角色说明书明确要求，且必须在 allow 列表内）；
  4. 不声称「已验证/已通过」而没有对应证据文件与哈希；
  5. 不运行 `next`（它会改 `state.json` 的 `next_seq`）；你的交接包已由 Lead 生成。

## 4. 交接要求与回报格式（含启动自检）

**启动自检（做完再动手）**

```powershell
& $PY "{package.as_posix()}/tools/dsh_flow.py" doctor -p "{project.as_posix()}" -f {feature}
& $PY "{package.as_posix()}/tools/dsh_flow.py" status -p "{project.as_posix()}" -f {feature}
```
若 doctor 报错或 status 显示的门禁不满足，立即停止并回报，不要硬扛。

**交接要求（你必须做，不做等于没完成）**

1. 把结论写成磁盘文件（路径见角色说明书的「交接物」一节）。
2. 回报给 Lead 的**固定格式**见角色说明书第 5 节；回报正文不超过 40 行。
3. 需要用户拍板的事写进「待用户决策」，不要自己扩大范围。
4. 如果发现上游文档有错，**不要直接改**：写进回报的「上游问题」一节，由 Lead 决定。

**踩坑就记一条（`lesson add`，不参与门禁）**：遇到「症状能一句话说清、下次还会再犯」的坑，
用 `& $PY "{package.as_posix()}/tools/dsh_flow.py" lesson -p "{project.as_posix()}" add --symptom "…" --cause "…" --fix "…" --tags {role}`
追加到 `ops/lessons.md`，下一个 feature 的交接包会自动带出来。
"""

    # ---- 装填 §1 / §2：两段式 + 迭代收敛，保证整份交接包 ≤ HANDOFF_MAX_BYTES ----
    # 先量出「除 §1、§2 之外」的固定字节，把余量分给 §1；仍超标就按超出量继续收 §2。
    ctx_marker, role_marker = "@@CTX@@", "@@ROLE@@"
    base_bytes = (len(mission.encode("utf-8")) - len(ctx_marker) - len(role_marker))
    if no_context:
        ctx_txt = ("## 1. 已知上下文（自动摘要）\n\n"
                   "- 已按 `--no-context` 关闭（排障用；去掉该参数即恢复默认供给）。\n\n")
        ctx_blocks = None
    else:
        graph_lines = _ctx_graph_summary(project, st)
        # B 组（DESIGN §5.4）：第 5 块「知识入口」放最后；采集失败只降级成一行，不阻断派活。
        try:
            know_lines = _ctx_knowledge_entries(
                project, feature, st, graph_lines,
                rag_dir=getattr(args, "rag_dir", ""),
                mnemon_cli=getattr(args, "mnemon_cli", ""),
                args=args)
        except Exception as e:
            know_lines = [f"- 知识入口：未提供（采集失败：{type(e).__name__}）"]
        ctx_blocks = [
            ("图谱摘要", graph_lines,
             (project / "graphify-out" / "graph.json").as_posix()),
            ("上一候选已报的坑", _ctx_prev_report(base, st),
             (base / "releases").as_posix()),
            ("同类坑（跨 feature）", _ctx_lessons(project, role),
             (project / LESSONS_REL).as_posix()),
            ("项目关键事实", _ctx_key_facts(project, feature, args),
             (base / "CONTEXT-NOTES.md").as_posix()),
            ("知识入口（离线采集，不调 MCP/LLM/网络）", know_lines,
             (base / "DESIGN.md").as_posix()),
        ]
        ctx_txt = ""
    digest_cap = ROLE_DIGEST_MAX_BYTES
    mission_tpl = mission
    ctx_floor = HANDOFF_CTX_MIN_BYTES - 700   # 700 = §1 自己的脚手架开销，下面按「含脚手架」算
    for _ in range(8):
        digest = _render_role_digest(package, role, phase, doc, digest_cap)
        role_txt = digest if digest is not None else role_fallback
        m2 = mission_tpl.replace(role_marker, role_txt)
        fixed_bytes = len(m2.encode("utf-8")) - len(ctx_marker)
        if ctx_blocks is not None:
            try:
                # 双闸：既要「剩余字节」（12000 - 固定 - 脚手架），又要「§1 保底 2600 字节含脚手架」；
                # 两者冲突时先收 §2 角色要点，角色要点收到下限仍超 → 放弃 §1 保底（绝不破 12000）。
                ctx_budget = max(ctx_floor, HANDOFF_MAX_BYTES - fixed_bytes - 700)
                # 5 块必须显式传 min_lines：默认值按块数补齐会把「项目关键事实」的 3 行保底
                # 静默压成 2 行（DESIGN §5.4 / R8——不报错，只是悄悄变弱）。
                ctx_txt = _render_context_section(
                    ctx_blocks, ctx_chars, ctx_budget,
                    min_lines=(2, 2, 2, 3, 1)) + "\n\n"
            except Exception as e:  # 采集永不阻断派活
                ctx_txt = ("## 1. 已知上下文（自动摘要）\n\n"
                           f"- 未提供（采集失败：{type(e).__name__}）\n\n")
        out_text = m2.replace(ctx_marker, ctx_txt)
        overshoot = len(out_text.encode("utf-8")) - HANDOFF_MAX_BYTES
        if overshoot <= 0:
            break
        if digest is not None and digest_cap > 1200:
            digest_cap = max(1200, digest_cap - overshoot - 200)
            continue
        if ctx_floor > 400:
            ctx_floor = 400
            continue
        break
    mission = out_text

    out = base / "handoffs" / f"HANDOFF-{seq:03d}-{role}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(mission, encoding="utf-8", newline="\n")
    append_history(st, "handoff", "lead", f"生成 {out.name} → {role}")
    save_state(project, feature, st)

    print(f"✓ 交接包已写入 {out}\n")
    print("=== 直接把下面这段作为 subagent 的 prompt ===")
    print(f"prompt = <读取 {out} 的全文>\n")
    print("=== Lead 要同时做的事 ===")
    print(f"""team_task_create(
  subject="[{feature}] {phase} → {role}",
  description="读交接包 {out.as_posix()}；按角色说明书执行；回报格式固定。\\n不做：改 state.json、改其它角色文件、声称通过而无证据。",
  write_scopes=[{', '.join(json.dumps(s) for s in (scope_roots(st) or ['docs/' + feature]))}],
  blocked_by=[{('"' + args.blocked_by + '"') if args.blocked_by else ''}]
)""")
    print("\n=== 角色派发建议 ===")
    print(f"""subagent(
  name="{role}-{seq:03d}",
  description="{role} 执行 {feature} 第 {seq} 步",
  cwd="{project.as_posix()}",
  prompt=<上面交接包全文>
)""")


def cmd_lesson(args) -> None:
    """跨 feature 教训库的唯一写入口：add 追加一行并打印新 ID；list 只读。
    不写 state.json，不进入 gate_for（命令行契约，不是阶段门禁）。"""
    project = Path(args.project).resolve()
    path = project / LESSONS_REL
    act = getattr(args, "lesson_cmd", "")
    rows, invalid, err = _load_lessons(project)

    if act == "list":
        role = (getattr(args, "role", "") or "").strip().lower()
        if err == "未建":
            print(f"教训库未建（{path.as_posix()}）；用 `lesson add` 建第一条。")
            return
        if err:
            print(f"✗ {err}: {path.as_posix()}")
            return
        picked = [r for r in rows if (not role or role in r["roles"] or "all" in r["roles"])]
        print(f"教训库：{path.as_posix()}（{len(rows)} 条有效"
              + (f"，{len(invalid)} 行格式无效" if invalid else "") + "）")
        for r in picked:
            print(f"  {r['id']}  [{','.join(r['roles'])}]  {r['symptom']} → {r['fix']}  ({r['date']})")
        if not picked:
            print("  （没有匹配的教训）")
        for bad in invalid:
            print(f"  ⚠ 行格式无效：{bad[:100]}")
        return

    # add
    symptom = (getattr(args, "symptom", "") or "").strip()
    cause = (getattr(args, "cause", "") or "").strip()
    fix = (getattr(args, "fix", "") or "").strip()
    if not symptom or not fix:
        print("✗ lesson add 需要 --symptom 与 --fix（缺一不可）", file=sys.stderr)
        print("  用法：lesson -p <项目根> add --symptom \"…\" --cause \"…\" --fix \"…\" "
              "--tags executor[,verifier] [--role executor]", file=sys.stderr)
        sys.exit(2)
    tags = [t.strip().lower() for t in re.split(r"[,\s]+", getattr(args, "tags", "") or "") if t.strip()]
    role_opt = (getattr(args, "role", "") or "").strip().lower()
    if role_opt and role_opt not in tags:
        tags.append(role_opt)
    tags = [t for t in tags if t in LESSON_ROLES]
    if not tags:
        tags = ["all"]
    if err and err != "未建":
        die(f"{err}: {path.as_posix()}")
    max_n = 0
    for r in rows:
        max_n = max(max_n, int(r["id"][1:]))
    for bad in invalid:  # 无效行里的 ID 也不能复用
        m = re.match(r"^\|\s*L(\d{3})\s*\|", bad)
        if m:
            max_n = max(max_n, int(m.group(1)))
    new_id = f"L{max_n + 1:03d}"

    def cell_of(s: str) -> str:
        v = (s or "").replace("|", "／").replace("\r", " ").replace("\n", " ").strip()
        return v if v else "-"

    row = (f"| {new_id} | {cell_of(symptom)} | {cell_of(cause)} | {cell_of(fix)} | "
           f"{','.join(tags)} | {now_iso()[:10]} |")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(LESSONS_TITLE + "\n\n> 一行一条，跨 feature 复用；`lesson add` 是唯一写入口，"
                            "行契约见 DESIGN/接口约定（改动等于改接口）。\n\n"
                            + LESSONS_HEADER + "\n" + LESSONS_SEP + "\n" + row + "\n",
                            encoding="utf-8", newline="\n")
        else:
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            if not raw.strip():
                path.write_text(LESSONS_TITLE + "\n\n" + LESSONS_HEADER + "\n" + LESSONS_SEP
                                + "\n" + row + "\n", encoding="utf-8", newline="\n")
            else:
                prefix = "" if raw.endswith("\n") else "\n"
                with path.open("a", encoding="utf-8", newline="\n") as f:
                    f.write(prefix + row + "\n")
    except OSError as e:
        die(f"写入 {path.as_posix()} 失败（{type(e).__name__}: {e.strerror or e}）")
    print(f"✓ {new_id} 已写入 {LESSONS_REL}")
    print(f"  症状：{symptom}")
    print(f"  适用角色：{','.join(tags)}")


def cmd_block(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    if st.get("blocked"):
        b = st["blocked"]
        die(f"已经处于阻塞（{b.get('reason')}，owner={b.get('owner')}）；先 unblock 再改。")
    _set_blocked(st, args.reason, args.owner)
    st["blocked"]["kind"] = args.kind
    append_history(st, "block", args.actor, f"[{args.kind}/{args.owner}] {args.reason}")
    save_state(project, feature, st)
    print(f"✓ 已标记阻塞（owner={args.owner}, kind={args.kind}）：{args.reason}")
    print("  解除：flow.py unblock --note \"...\"")


def cmd_unblock(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    old = st.get("blocked")
    if not old:
        print("（当前没有阻塞标记）")
        return
    st["blocked"] = None
    append_history(st, "unblock", args.actor, f"解除[{old.get('owner')}] {old.get('reason')}｜{args.note or ''}")
    save_state(project, feature, st)
    print(f"✓ 已解除阻塞：{old.get('reason')}")


def cmd_amend(args) -> None:
    """DESIGN 变更：归档旧版、状态改为待用户确认、记台账，等用户重新确认后再 advance。"""
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    base = docs_root(project, feature)
    design = base / "DESIGN.md"
    if not design.exists():
        die("DESIGN.md 不存在，无法 amend。")
    version = int(st.get("design_version", 1) or 1)
    next_version = version + 1
    hist = base / "design-history"
    hist.mkdir(parents=True, exist_ok=True)
    archived = hist / f"DESIGN-v{version}-{datetime.now(TZ).strftime('%Y%m%d-%H%M%S')}.md"
    shutil.copy2(design, archived)

    text = design.read_text(encoding="utf-8")
    new_text, n = re.subn(r"^状态\s*[：:].*$", "状态：待用户确认", text, count=1, flags=re.MULTILINE)
    if n == 0:
        new_text = text.rstrip() + "\n\n状态：待用户确认\n"
    design.write_text(new_text, encoding="utf-8", newline="\n")

    st["design_version"] = next_version
    st.setdefault("amendments", []).append({
        "at": now_iso(),
        "actor": args.actor,
        "reason": args.reason,
        "from_version": version,
        "to_version": next_version,
        "archived": posix_rel(archived, project),
    })
    _set_blocked(st, f"DESIGN v{next_version} 待用户确认：{args.reason}", "user")
    st["blocked"]["kind"] = "user"
    append_history(st, "amend", args.actor, f"DESIGN v{version}→v{next_version}：{args.reason}")
    save_state(project, feature, st)

    print(f"✓ DESIGN 已升到 v{next_version}，旧版归档：{archived}")
    print("  已把状态改为『状态：待用户确认』并标记阻塞（owner=user）")
    print("  下一步：")
    print("   1) 改 DESIGN.md（把变更写进正文与『变更历史』）")
    print("   2) 请用户确认后，把状态行改回『状态：已确认』")
    print("   3) flow.py unblock --note \"用户确认 DESIGN v%d\"" % next_version)
    print("   4) flow.py advance --to EXECUTING（开新候选，不继承旧候选结论）")


def cmd_handshake(args) -> None:
    """运行时版本握手：拉健康检查，比对期望版本，落 R1 证据并记 state。"""
    project = Path(args.project).resolve()
    feature = args.feature
    base = docs_root(project, feature)
    st = load_state(project, feature)
    cid = args.id or st.get("current_candidate")
    if not cid:
        die("没有候选：用 --id 指定，或先 freeze。")
    rt = manifest_runtime(base, cid)
    url = args.url or rt.get("health_url") or ""
    expect = args.expect or rt.get("version") or ""
    if not url:
        die("缺少 --url（manifest.runtime.health_url 也为空）")
    if not expect:
        die("缺少 --expect（manifest.runtime.version 也为空）")

    status, data = _fetch_json(url, timeout=args.timeout)
    actual = _dig(data, args.field) if isinstance(data, dict) else None
    ok = status == 200 and _norm_version(actual) == _norm_version(expect)
    body = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)[:1200]

    ev_dir = base / "evidence" / cid
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev = ev_dir / "R1-handshake.md"
    ev.write_text(f"""# R1 — 运行时版本握手

- 检查：R1
- 等级：A
- 结果：{'pass' if ok else 'fail'}
- 候选：{cid}
- 时间：{now_iso()}
- 执行者：{args.actor}

## 命令

```
GET {url}
期望 {args.field} = {expect}；实际 = {actual!r}（HTTP {status}）
```

## 输出（原文，截断 1200 字符）

```
{body}
```

## 结论

{'运行时版本与候选声明一致。' if ok else '运行时版本与候选不一致：宿主半可能仍是旧版，先重启 DSH 再重跑握手；不要靠出新候选掩盖。'}
""", encoding="utf-8", newline="\n")

    rec = {"checked_at": now_iso(), "url": url, "expected": expect,
           "actual": actual, "http_status": status, "ok": ok, "evidence": posix_rel(ev, project)}
    st.setdefault("candidates", {}).setdefault(cid, {})["runtime"] = rec
    append_history(st, "handshake", args.actor,
                   f"{cid}: expect={expect} actual={actual!r} http={status} → {'PASS' if ok else 'FAIL'}")
    save_state(project, feature, st)

    print(f"{'✓' if ok else '✗'} 运行时握手 {cid}: 期望 {expect}，实际 {actual!r}（HTTP {status}）")
    print(f"  证据：{ev}")
    if not ok:
        print("  提示：插件/能力包的宿主半不热替换时，先重启 DSH；重启后重跑本命令。")
        sys.exit(1)


# --------------------------------------------------------------------------- #
# 封存包异地快照（flow-backup-a / DESIGN §3.2–§3.5）
# --------------------------------------------------------------------------- #

# 快照目录名契约：`<C>-<yyyyMMdd>-<HHmmss>`（候选号 + 本机时区时间戳，可排序、可人读）
RE_SNAPSHOT_DIR = re.compile(r"^(C\d+)-(\d{8}-\d{6})$")


def _backup_root(backup_dir=None) -> Path:
    """本次快照用的根：`--backup-dir` > 环境变量 `FLOW_BACKUP_ROOT` > 默认 `BACKUP_ROOT`。"""
    if backup_dir:
        return Path(str(backup_dir)).expanduser()
    return BACKUP_ROOT


def _backup_root_source(backup_dir=None) -> str:
    """快照根是从哪来的（写进 seal 输出，便于事后复核「这次到底写去了哪」）。"""
    if backup_dir:
        return "--backup-dir"
    if os.environ.get("FLOW_BACKUP_ROOT"):
        return "环境变量 FLOW_BACKUP_ROOT"
    return f"默认 {DEFAULT_BACKUP_ROOT}"


def _backup_snapshot(project: Path, feature: str, cid: str, backup_dir=None):
    """把 `docs/<feature>/` 整目录复制到 `<root>/<项目目录名>/<feature>/<C>-<时间戳>/`。

    为什么复制整目录而不是只挑三个文件（DESIGN §3.2）：事故里丢的是「工具写的那批凭证」，
    它们分散在 `releases/`、`evidence/`、`planning/`、`state.json`、`baseline.json`、
    `ledger.md`、`ACCEPTANCE.md`、`DESIGN.md`，逐个挑必然漏；整目录复制是唯一不靠记性的做法。

    契约（DESIGN §3.3 / §3.4）：
    - **幂等**：目标目录已存在 → 直接跳过（同一秒内重跑 seal 不重复创建、不覆盖）；
    - **原子**（C002 / D-02）：先 `copytree` 到**同一父目录**下的隐藏临时名
      `.<最终名>.partial-<pid>`，成功后再 `os.replace` 成最终名；失败/中断时 `finally`
      清掉临时目录。这样中途失败（磁盘满、权限、进程被杀）**不会留下半成品最终名**，
      下次 seal 会老老实实重试，而不是命中上面那条「已存在，跳过」把残片当成品（D-02 的根因）；
    - **失败不抛**：打印 `⚠ 快照失败: <原因>` 并返回 `None`，由调用方决定是否记台账；
      seal 的结论与退出码不受影响——保险失败不能把已经生效的封存报成失败；
    - 返回值为目标目录 Path（成功）或 None（失败），供调用方写台账用。

    为什么用隐藏前缀 `.`：`RE_SNAPSHOT_DIR` 只认「候选号-时间戳」这一种形状
    （`C<编号>-<yyyyMMdd>-<HHmmss>`），临时名（`.C002-20261122-073000.partial-1234`）
    不会被 `_latest_snapshot()` / `doctor` 当成候选；
    正常路径下临时目录只在 copytree 期间存在，收尾必然消失。
    `os.replace` 在同卷上是原子的；若并发 seal 恰好抢到同一秒的同一个最终名，
    后到者 replace 失败 → 走告警分支（临时目录被清掉），先到者的快照保持完整——宁可少一份也不留残片。
    """
    src = docs_root(project, feature)
    root = _backup_root(backup_dir)
    tmp: "Path | None" = None
    try:
        if not src.is_dir():
            raise FileNotFoundError(f"源目录不存在：{src}")
        stamp = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
        dest_parent = root / project.resolve().name / feature
        dest = dest_parent / f"{cid}-{stamp}"
        if dest.exists():
            print(f"  （快照已存在，跳过：{dest.as_posix()}）")
            return dest
        dest_parent.mkdir(parents=True, exist_ok=True)
        tmp = dest_parent / f".{dest.name}.partial-{os.getpid()}"
        if tmp.exists():  # 上一进程异常退出留下的残留（pid 复用）：先清，否则 copytree 报「已存在」
            shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(src, tmp)
        os.replace(tmp, dest)   # 同一卷内目录改名：原子生效
        tmp = None
    except Exception as e:  # 权限、磁盘满、路径非法、盘符不存在……一律降级为告警
        print(f"⚠ 快照失败: {type(e).__name__}: {e}")
        return None
    finally:
        if tmp is not None:             # 中途失败：临时目录必须消失，否则下次会攒一地残片
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"  ✓ 异地快照：{dest.as_posix()}")
    return dest


def _latest_snapshot(project: Path, feature: str, backup_dir=None):
    """该 feature 最新的一份候选快照（按「候选号 → 时间戳」排序）；没有则返回 None。

    `backup_dir`：与 `seal --backup-dir` 同语义的根覆盖（C002 / D-03：doctor 要能看到自定义根，
    否则 `seal --backup-dir X` 写下的副本在 doctor 眼里等于不存在）。
    """
    d = _backup_root(backup_dir) / project.resolve().name / feature
    if not d.is_dir():
        return None
    best, best_key = None, None
    try:
        entries = list(d.iterdir())
    except OSError:
        return None
    for p in entries:
        m = RE_SNAPSHOT_DIR.match(p.name)
        if not m:
            continue
        try:
            if not p.is_dir():
                continue
        except OSError:
            continue
        key = (int(m.group(1)[1:]), m.group(2))
        if best_key is None or key > best_key:
            best, best_key = p, key
    return best


def _doctor_backup(project: Path, feature: str, backup_dir=None) -> "list[str]":
    """`doctor` 的「快照健康」：根存在且可写 + 最新副本两份凭证与项目内 sha256 一致。

    `backup_dir`：与 `seal --backup-dir` 同语义（C002 / D-03）。不传时行为与旧版**逐字相同**
    （读 `BACKUP_ROOT`，即环境变量或默认值）。

    **只告警、不阻塞**（DESIGN §3.5）：副本旧了/被改了需要人看，但不该让 `doctor` 退出码非 0，
    否则定时巡检会因为「副本比项目旧」整条变红，最后人会去关掉这项检查。
    """
    lines: "list[str]" = []
    root = _backup_root(backup_dir)
    if not root.exists():
        lines.append(f"⚠ 备份根不存在（{root.as_posix()}）：首次 seal 会自动创建；"
                     "若此前 seal 过，说明副本已丢 → 查方案 B 的每日镜像（ops/schedules.md）")
    elif not root.is_dir():
        lines.append(f"⚠ 备份根不是目录（{root.as_posix()}）")
    else:
        probe = None
        try:
            fd, name = tempfile.mkstemp(prefix=".doctor-write-probe-", dir=str(root))
            os.close(fd)
            probe = Path(name)
        except OSError as e:
            lines.append(f"⚠ 备份根不可写（{root.as_posix()}）：{type(e).__name__}: {e}")
        else:
            lines.append(f"✅ 备份根存在且可写（{root.as_posix()}）")
        finally:
            if probe is not None:
                try:
                    probe.unlink()
                except OSError:
                    pass
    snap = _latest_snapshot(project, feature, backup_dir)
    if snap is None:
        lines.append(f"最新副本：无（{feature} 还没有候选快照；seal 成功时自动生成）")
        return lines
    m = RE_SNAPSHOT_DIR.match(snap.name)
    cid = m.group(1) if m else snap.name.split("-", 1)[0]
    lines.append(f"最新副本：{project.resolve().name}/{feature}/{snap.name}")
    for name in ("manifest.json", "verification.json"):
        cur = docs_root(project, feature) / "releases" / cid / name
        cp = snap / "releases" / cid / name
        if not cur.is_file():
            lines.append(f"{name}: ⚠ 项目内缺失（{cur.as_posix()}）")
            continue
        if not cp.is_file():
            lines.append(f"{name}: ⚠ 副本缺失（{cp.as_posix()}）")
            continue
        try:
            a, b = sha256_file(cur), sha256_file(cp)
        except OSError as e:
            lines.append(f"{name}: ⚠ 读取失败：{type(e).__name__}: {e}")
            continue
        if a == b:
            lines.append(f"{name}: ✅ 与项目内一致（{a[:12]}）")
        else:
            lines.append(f"{name}: ⚠ 副本已变（副本 {b[:12]} ≠ 项目 {a[:12]}）")
    return lines


def cmd_seal(args) -> None:
    """把 V* 证据、发布报告、部署台账**快照**一起封存，随后任何改动都会被 verify 查出。

    为什么台账要快照（C004 治本，根因见 `ops/lessons.md` L001）：
    `DEPLOYMENT-PLAN.md` 是**全 feature 共用的单人读台账**，验证线程每轮都会写它。
    若 seal 直接登记共用路径的哈希，写法就自相矛盾——后一个候选封存时写台账，
    前面**所有**候选立刻被判「封存后内容被改」（C001 就是这么红的：11:47 封存，
    15:37 被 C002 的验证线程写了一次，之后永远红；而 C002/C003 封的是各自时点的现值，暂时是绿的）。
    所以 seal 先把**当时**的台账复制成 `releases/<C>/DEPLOYMENT-PLAN.md`，再封存这个副本：
    共用台账继续随便写（人读台账的能力一点没减），每个候选的可验证性冻结在自己那一刻。
    旧候选（C001–C003）的 verification.json 是旧格式，verify 端保持按记录路径校验的旧行为。
    """
    project = Path(args.project).resolve()
    feature = args.feature
    base = docs_root(project, feature)
    st = load_state(project, feature)
    cid = args.id or st.get("current_candidate")
    if not cid:
        die("没有候选：用 --id 指定。")
    rel_dir = base / "releases" / cid
    if not (rel_dir / "manifest.json").exists():
        die(f"候选 {cid} 的 manifest.json 不存在。")
    paths: list[Path] = []
    ev_dir = base / "evidence" / cid
    if ev_dir.exists():
        paths.extend(sorted(p for p in ev_dir.rglob("*") if p.is_file()))
    for extra in [rel_dir / "RELEASE-REPORT.md"]:
        if extra.exists():
            paths.append(extra)
    # 部署台账：每候选独立快照。共用台账仍是「人读的那一份」，只是不再作为封存对象。
    ledger = base / "DEPLOYMENT-PLAN.md"
    ledger_snapshot = rel_dir / "DEPLOYMENT-PLAN.md"
    if ledger.is_file():
        data = ledger.read_bytes()
        if not ledger_snapshot.is_file() or ledger_snapshot.read_bytes() != data:
            ledger_snapshot.write_bytes(data)
    if ledger_snapshot.is_file():
        # 共用台账已被移走时沿用已有快照，不静默丢掉这一项封存
        paths.append(ledger_snapshot)
    # 去重（同一文件可能同时命中证据目录以外的来源），保留首次出现顺序
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in paths:
        key = posix_rel(p, project)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    paths = uniq
    if not paths:
        die("没有可封存的文件（证据与报告都为空）。")
    files = []
    for p in paths:
        files.append({"path": posix_rel(p, project), "sha256": sha256_file(p), "bytes": p.stat().st_size})
    payload = {
        "schema": "dsh-flow/verification@1",
        "feature": feature,
        "candidate": cid,
        "sealed_at": now_iso(),
        "sealed_by": args.actor,
        "files": files,
    }
    write_json(rel_dir / "verification.json", payload)
    st.setdefault("candidates", {}).setdefault(cid, {})["sealed_at"] = payload["sealed_at"]
    append_history(st, "seal", args.actor, f"{cid}: 封存 {len(files)} 个文件")
    save_state(project, feature, st)
    print(f"✓ 已封存 {cid}：{len(files)} 个文件 → {rel_dir / 'verification.json'}")
    if ledger_snapshot.is_file():
        print(f"  部署台账已快照到 releases/{cid}/DEPLOYMENT-PLAN.md："
              "之后再写共用台账不会把这个候选弄红。")
    print("  之后任何改动或新增证据都会被 verify 判为失败；要改就出新候选。")

    # 异地快照（flow-backup-a §3.3）：封存已生效，快照只是保险——
    # 保险失败**不改退出码**、不回滚 seal，只打印 ⚠ 并记一条 backup-failed 台账。
    if getattr(args, "no_backup", False):
        print("  已按 --no-backup 跳过异地快照（本次不写副本）。")
        return
    bdir = getattr(args, "backup_dir", "") or ""
    root_used = _backup_root(bdir or None)
    print(f"  异地快照根: {root_used.as_posix()}（来源：{_backup_root_source(bdir or None)}）")
    snap = _backup_snapshot(project, feature, cid, bdir or None)
    if snap is None:
        append_history(st, "backup-failed", args.actor,
                       f"{cid}: 异地快照失败（root={root_used.as_posix()}）；seal 结论不变")
        save_state(project, feature, st)
        print("  快照失败不影响本次封存（退出码 0）；缺副本时靠每日 robocopy 兜底，"
              "见 ops/schedules.md。")
    else:
        append_history(st, "backup", args.actor, f"{cid}: 异地快照 → {snap.as_posix()}")
        save_state(project, feature, st)


def _set_blocked(st: dict, reason: str, owner: str):
    st["blocked"] = {"reason": reason, "owner": owner, "since": now_iso()}


def cmd_advance(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    cur = st.get("phase")
    target = args.to.upper()
    if target not in PHASES + ANOMALY_PHASES:
        die(f"非法阶段 {target}；可用: {PHASES + ANOMALY_PHASES}")
    if target not in TRANSITIONS.get(cur, []):
        die(f"不允许的转换 {cur} → {target}；本阶段可去: {TRANSITIONS.get(cur, [])}")
    if st.get("blocked") and target != "ROLLED_BACK" and not args.force:
        b = st["blocked"]
        die(f"当前处于阻塞（[{b.get('kind') or '?'}/{b.get('owner')}] {b.get('reason')}）。"
            f"先 unblock（或确认用户已处理）再推进。", 1)
    checks = gate_for(project, feature, target)
    failed = [(n, d) for n, ok, d in checks if not ok]
    if failed and not args.force:
        print(f"✗ 门禁未通过，拒绝推进到 {target}：")
        for n, d in failed:
            print(f"  - {n}  {d}")
        die("修好后重试；确认要带风险推进请加 --force --reason \"…\"（会写进台账）。", 1)
    if failed and args.force:
        if not args.reason:
            die("--force 必须同时给 --reason，把风险写清楚。")
        append_history(st, "gate-forced", args.actor, f"{cur}→{target}: " + "; ".join(n for n, _ in failed))
    if target == "ROLLED_BACK":
        append_history(st, "rollback", args.actor, args.note or "回滚")
    st["phase"] = target
    if target != "ROLLED_BACK":
        st["blocked"] = None
    if target in ("EXECUTING", "PLAN", "DESIGN"):
        # 回到执行前：新候选必须重新冻结
        pass
    if target == "TRIAL":
        cid = st.get("current_candidate")
        if cid and cid in st.get("candidates", {}):
            st["candidates"][cid]["status"] = "verified"
            st["candidates"][cid]["verified_at"] = now_iso()
            st["candidates"][cid]["report"] = f"releases/{cid}/RELEASE-REPORT.md"
    if target == "DONE":
        cid = st.get("current_candidate")
        if cid and cid in st.get("candidates", {}):
            st["candidates"][cid]["status"] = "accepted"
        st["generation"] = st.get("generation", 1) + 1
    save_state(project, feature, st)
    append_history(st, "advance", args.actor, f"{cur}→{target}" + (f" ({args.note})" if args.note else ""))
    save_state(project, feature, st)
    print(f"✓ 阶段推进 {cur} → {target}（actor={args.actor}）")
    nxt = PHASE_ROLE.get(target, "?")
    print(f"  下一角色: {nxt}")
    print(f"  生成交接包: $PY tools/dsh_flow.py next -p \"{project}\" -f {feature}")


def cmd_gate(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    cur = st.get("phase")
    target = (args.to or (TRANSITIONS.get(cur) or ["?"])[0]).upper()
    checks = gate_for(project, feature, target)
    print(f"门禁：{cur} → {target}")
    for name, ok, detail in checks:
        print(f"  {'✓' if ok else '✗'} {name}" + (f"  — {detail}" if detail and not ok else ""))
    base = docs_root(project, feature)
    cid = st.get("current_candidate") or ""
    pack = detect_pack(project)
    if target == "TRIAL" and pack and cid and not manifest_runtime(base, cid):
        print(f"\nℹ 能力包项目（{pack['name'] or pack['path']}）未在 manifest 声明 runtime："
              "『运行时版本握手』不计入本次门禁；上线前建议出声明 runtime 的候选"
              "（`freeze --runtime-kind plugin --runtime-version <版本> --health-url <地址>`）。")
    ok_all = all(ok for _, ok, _ in checks)
    warns = warn_for(project, feature)
    if warns:
        print("\n软告警（⚠ 不阻断推进，也不计入「门禁 N/M」）:")
        for name, detail in warns:
            print(f"  ⚠ {name}：{detail}")
    print(f"\n{'全部通过' if ok_all else '未通过'}")
    if checks and not ok_all:
        sys.exit(1)


def _plan_drive(st: dict, checks, warnings) -> dict:
    """把「阶段 + 硬门禁 + 软告警」合成 `drive` 的输出契约（DESIGN §5.6，顶层 12 键）。

    **只读**：不调 `cmd_health`（会写 `health.json`）、不调 `cmd_next`（会改 `next_seq`
    并生成交接包）、不 `save_state`。
    """
    phase = st.get("phase") or "?"
    target = (TRANSITIONS.get(phase) or ["?"])[0]
    items = [{"name": n, "ok": bool(ok), "detail": d} for n, ok, d in checks]
    passed = sum(1 for it in items if it["ok"])
    total = len(items)
    # 只看硬门禁：软告警没有布尔位，从类型上就进不了这里（DESIGN §5.3）
    ok_all = passed == total if total else True

    pkg = Path(__file__).resolve().parent.parent.as_posix()
    flow = f'& $PY "{pkg}/tools/dsh_flow.py"'
    proj = st.get("project") or ""
    feat = st.get("feature") or ""

    def cmd_of(verb: str) -> str:
        return f'{flow} {verb} -p "{proj}" -f {feat}'

    blocked = st.get("blocked") or None
    if blocked:
        next_command = cmd_of("unblock") + ' --note "…"'
    elif phase == "DONE":
        next_command = "新需求请 `init` 新 feature（DONE 不再给推进命令）"
    elif ok_all:
        next_command = cmd_of("advance") + f" --to {target} --actor lead"
    elif checks:
        next_command = cmd_of("gate")
    else:
        next_command = cmd_of("status")

    return {
        "schema": "dsh-flow/drive@1",
        "generated_at": now_iso(),
        "project": proj,
        "feature": feat,
        "phase": phase,
        "candidate": st.get("current_candidate") or "",
        "next_role": PHASE_ROLE.get(phase, "?"),
        "gate": {"target": target, "passed": passed, "total": total,
                 "ok": ok_all, "items": items},
        "warnings": [{"name": n, "detail": d} for n, d in warnings],
        "blocked": blocked,
        "can_advance": ok_all,
        "next_command": next_command,
    }


def cmd_drive(args) -> None:
    """只读合成（DESIGN §5.6）：一次给出 phase / 门禁（硬+软）/ 下一角色 / 能否推进 / 建议命令。

    **严格只读**：不写 `state.json`、不写 `ledger.md`、不生成 `handoffs/` 文件、不写 `health.json`。
    退出码与 `gate` 对齐：硬门禁未过 → 1；全过 → 0；`state.json` 缺失 → 2（沿用 `die()` 默认码）。
    """
    project = Path(args.project).resolve()
    feature = args.feature
    st = load_state(project, feature)
    phase = st.get("phase") or "?"
    target = (TRANSITIONS.get(phase) or ["?"])[0]
    checks = gate_for(project, feature, target)
    warnings = warn_for(project, feature)
    plan = _plan_drive(st, checks, warnings)

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        gate = plan["gate"]
        gate_txt = f"{gate['passed']}/{gate['total']} 通过"
        failed = [it["name"] for it in gate["items"] if not it["ok"]]
        if failed:
            gate_txt += f"（未过：{'；'.join(failed)}）"
        if plan["warnings"]:
            warn_txt = f"{len(plan['warnings'])} 项（" + "；".join(
                f"⚠ {w['name']}：{w['detail']}" for w in plan["warnings"]) + "）"
        else:
            warn_txt = "无"
        blocked = plan["blocked"]
        blocked_txt = ("无" if not blocked else
                       f"[{blocked.get('kind') or '?'}/{blocked.get('owner') or '?'}] "
                       f"{blocked.get('reason')}")
        print(f"phase    : {plan['phase']}")
        print(f"候选     : {plan['candidate'] or '(无)'}")
        print(f"下一角色 : {plan['next_role']}")
        print(f"门禁     : {gate_txt}")
        print(f"软告警   : {warn_txt}")
        print(f"阻塞     : {blocked_txt}")
        print(f"能否推进 : {'能' if plan['can_advance'] else '否'}")
        print(f"建议命令 : {plan['next_command']}")

    if checks and not all(ok for _, ok, _ in checks):
        sys.exit(1)


def cmd_ledger(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    base = docs_root(project, feature)
    p = base / "ledger.md"
    if args.message:
        st = load_state(project, feature)
        append_history(st, "note", args.actor, args.message)
        save_state(project, feature, st)
        print(f"✓ 已记入台账: {args.message}")
        return
    if not p.exists():
        die("台账不存在")
    lines = p.read_text(encoding="utf-8").splitlines()
    for line in lines[-args.tail:]:
        print(line)


def _doctor_node() -> "tuple[str, str]":
    """探测 node：返回 `(可执行文件路径, 来源说明)`；找不到返回 `("", "")`。

    **只在 `doctor` 里用，不做门禁**（DESIGN §5.2：QC 的 node 判据仍以 `shutil.which` 为准）。
    旧版 `doctor` 直接印死「无 node on PATH 属正常」，但本机 `where.exe node` 明明命中
    `…\\dependencies\\node\\bin\\node.exe`（v24.21.0），QC 也靠它判出了 js 行的退出码——
    这条文案是**假告警**（RELEASE-REPORT 已知问题：doctor 误报无 node）。

    探测顺序：① `shutil.which("node")`（PATH 口径，与 QC 一致）→ 报「PATH」；
    ② 已知安装位置（DSH 运行时自带的 `dependencies/node/bin/node.exe`、`%ProgramFiles%\\nodejs`，
    以及 `%LOCALAPPDATA%\\Programs\\nodejs` 这类用户级安装）→ 报「找到（非 PATH）」；
    ③ 都没有 → 空串，由调用方写「未安装」。
    """
    node = shutil.which("node")
    if node:
        return node, "PATH"
    deps = Path(sys.executable).resolve().parent.parent      # …/dependencies
    candidates = [
        deps / "node" / "bin" / "node.exe",                  # DSH 运行时自带
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "node.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "nodejs" / "node.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs" / "node.exe",
    ]
    for c in candidates:
        try:
            if c.is_file():
                return str(c), "找到（非 PATH）"
        except OSError:
            continue
    return "", ""


def _doctor_node_version(node: str) -> str:
    """读 `node --version`（只读、失败不抛；拿不到就返回空串）。"""
    try:
        p = subprocess.run([node, "--version"], capture_output=True, timeout=10,
                           text=True, encoding="utf-8", errors="replace")
        return (p.stdout or "").strip() or (p.stderr or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def cmd_doctor(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    package = Path(args.package).resolve()
    print(f"python   : {sys.version.split()[0]}  ({sys.executable})")
    print(f"package  : {package}  ({'存在' if package.exists() else '缺失'})")
    print(f"project  : {project}  ({'存在' if project.exists() else '缺失'})")
    git = shutil.which("git")
    print(f"git      : {git or '未安装 → 使用 baseline + sha256 代替 diff/worktree'}")
    node, node_src = _doctor_node()
    if node:
        ver = _doctor_node_version(node)
        print(f"node     : {ver or '（版本读取失败）'}  ({node})"
              + ("" if node_src == "PATH" else f"  [{node_src}]"))
    else:
        print("node     : 未安装（PATH 与已知安装位置都没命中 → QC 的 .js/.mjs 整类 skip）")
    tpl = package / "templates"
    missing_tpl = [n for n in ["DESIGN.md", "COORDINATION-PLAN.md", "EXECUTION-WORKPLAN.md",
                               "VALIDATION-WORKPLAN.md", "RELEASE-REPORT.md", "ACCEPTANCE.md"]
                   if not (tpl / n).exists()]
    print(f"templates: {'齐全' if not missing_tpl else '缺少 ' + ', '.join(missing_tpl)}")
    roles_dir = package / "roles"
    missing_roles = [v for v in ROLE_FILES.values() if not (roles_dir / v).exists()]
    print(f"roles    : {'齐全' if not missing_roles else '缺少 ' + ', '.join(missing_roles)}")
    sp = state_path(project, feature)
    if sp.exists():
        st = read_json(sp)
        print(f"state    : 可读，phase={st.get('phase')}，候选={list((st.get('candidates') or {}).keys())}")
    else:
        print(f"state    : 未初始化（{sp}）")
    bp = baseline_path(project, feature)
    if bp.exists():
        bl = read_json(bp)
        ext = _external_map(bl)
        n_ext = sum(len(v) for v in ext.values())
        print(f"baseline : 项目内 {len(bl.get('files') or {})} 个文件，"
              f"外部源 {n_ext} 个文件（{len(ext)} 个目录）")
        missing = [p for p in ext if not Path(p).is_dir()]
        if missing:
            print(f"  ⚠ 外部源目录不存在: {missing[:3]}")
        if not (bl.get("files") or ext):
            print("  ⚠ 基线为空：插件类项目请跑 `baseline --source <源码目录>`，"
                  "或把开发副本命名为 `<项目名>-dev` 让自动发现生效")
    else:
        print("baseline : 未记录（先跑 baseline）")
    bdir = getattr(args, "backup_dir", "") or ""
    root_used = _backup_root(bdir or None)
    print(f"snapshot : {root_used.as_posix()}"
          f"（来源：{_backup_root_source(bdir or None)}；seal 后自动快照）")
    for ln in _doctor_backup(project, feature, bdir or None):
        print(f"  {ln}")
    print("env      : 无 bash（PowerShell only）；DSH 子智能体不共享对话上下文。")


def _default_rrule() -> str:
    tomorrow = (datetime.now(TZ) + timedelta(days=1)).strftime("%Y%m%d")
    return f"DTSTART;TZID=Asia/Shanghai:{tomorrow}T090000\nRRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0"


def build_health(project: Path, feature: str, include_gate: bool = True) -> dict:
    """汇总一个 feature 的健康快照（阶段/门禁/候选/封存/最近台账），供外部看板读。"""
    base = docs_root(project, feature)
    st = load_state(project, feature)
    phase = st.get("phase") or "?"
    cid = st.get("current_candidate") or ""
    cand = (st.get("candidates") or {}).get(cid) or {}
    manifest_path = (base / "releases" / cid / "manifest.json") if cid else None
    runtime = manifest_runtime(base, cid) if cid else {}
    verification = None
    vp = (base / "releases" / cid / "verification.json") if cid else None
    if vp is not None and vp.exists():
        try:
            v = read_json(vp)
            verification = {"sealed_at": v.get("sealed_at"),
                            "files": len(v.get("files") or []),
                            "sha256": sha256_file(vp)}
        except Exception as e:
            verification = {"error": str(e)}
    gate = None
    if include_gate:
        if phase == "DONE":
            # DONE 是终态：TRANSITIONS["DONE"] = ["EXECUTING"] 只表示「同一 feature 可开新一轮」，
            # 不是「必须过 DESIGN/planning 门禁才能前进」。对已完结的 feature 跑 gate_for 会拿
            # DESIGN.md 的历史状态去判 FAIL（2026-11-22 实测 dev-toolchain-boost 即如此）。
            # 因此 DONE 不下发门禁结论，只给一条说明，避免看板/巡检把已完结误判为受阻。
            gate = {"to": None, "ok": True, "failed": [],
                    "note": "DONE：流程已完结，无下一门禁；新需求请 init 新 feature"}
        else:
            target = (TRANSITIONS.get(phase) or ["?"])[0]
            try:
                checks = gate_for(project, feature, target)
                failed = [n for n, ok, _ in checks if not ok]
                gate = {"to": target, "ok": not failed, "failed": failed}
            except Exception as e:
                gate = {"to": target, "ok": False, "failed": [f"gate error: {e}"]}
    hist = st.get("history") or []
    last = hist[-1] if hist else {}
    ev_dir = (base / "evidence" / cid) if cid else None
    ev_count = len([p for p in ev_dir.rglob("*") if p.is_file()]) if ev_dir and ev_dir.exists() else 0
    # G2 读侧（E16③）：manifest.checks 要能被 health.json 读到（只读，不改 manifest）
    cand_checks = None
    if manifest_path and manifest_path.exists():
        try:
            _c = read_json(manifest_path).get("checks") or {}
            cand_checks = {"new": list(_c.get("new") or []), "reused": list(_c.get("reused") or [])}
        except Exception:
            cand_checks = None
    return {
        "schema": SCHEMA_HEALTH,
        "generated_at": now_iso(),
        "project": project.as_posix(),
        "feature": feature,
        "phase": phase,
        "blocked": st.get("blocked"),
        "candidate": {
            "id": cid or None,
            "status": cand.get("status"),
            "frozen_at": cand.get("frozen_at"),
            "sealed_at": cand.get("sealed_at"),
            "artifacts": cand.get("artifacts"),
            "runtime": runtime or None,
            "manifest_sha256": (sha256_file(manifest_path) if manifest_path and manifest_path.exists() else None),
            "checks": cand_checks,
        },
        "sealed": verification is not None,
        "verification": verification,
        "gate": gate,
        "counts": {
            "candidates": len(st.get("candidates") or {}),
            "evidence_files": ev_count,
            "history": len(hist),
        },
        "last": {"at": last.get("at"), "actor": last.get("actor"),
                 "action": last.get("action"), "detail": last.get("detail")},
        "ledger_tail": [f"{h.get('at')} | {h.get('actor')} | {h.get('action')} | {h.get('detail')}"
                        for h in hist[-5:]],
        "paths": {
            "state": state_path(project, feature).as_posix(),
            "health": (base / "health.json").as_posix(),
            "manifest": manifest_path.as_posix() if manifest_path else None,
            "verification": vp.as_posix() if vp else None,
        },
    }


def cmd_health(args) -> None:
    project = Path(args.project).resolve()
    feature = args.feature
    data = build_health(project, feature, include_gate=not args.no_gate)
    out = Path(args.out).expanduser() if args.out else (docs_root(project, feature) / "health.json")
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    write_json(out, data)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    gate = data.get("gate") or {}
    print(f"✓ health 已写入 {out}")
    print(f"  phase={data['phase']} ｜ 候选={data['candidate']['id'] or '-'} ｜ "
          f"封存={'yes' if data['sealed'] else 'no'} ｜ "
          f"门禁={'PASS' if gate.get('ok') else 'FAIL'} ｜ 阻塞={'yes' if data['blocked'] else 'no'}")
    if gate and gate.get("failed"):
        print(f"  门禁未过：{', '.join(gate['failed'][:5])}")
    print("  外部看板可直接读这个 JSON；它不参与冻结/封存，可随时重算。")


def cmd_inspector(args) -> None:
    """生成可直接粘进 schedule_create 的巡检 prompt（路径全部填实）。"""
    project = Path(args.project).resolve()
    feature = args.feature
    package = Path(args.package).resolve()
    st = load_state(project, feature)
    base = docs_root(project, feature)
    cid = args.candidate or st.get("current_candidate") or "C000"
    today = datetime.now(TZ).strftime("%Y%m%d")
    report = (base / "evidence" / f"inspector-{today}.md").as_posix()
    py = args.python or sys.executable or "python"
    flow = (package / "tools" / "dsh_flow.py").as_posix()
    role = (package / "roles" / "04-inspector.md").as_posix()
    bp = baseline_path(project, feature)
    ext = _external_map(read_json(bp)) if bp.exists() else {}
    ext_dirs = list(ext) or ["（无外部源）"]
    dev = project.parent / (project.name + "-dev")
    rrule = args.rrule or _default_rrule()
    title = args.title or f"每日审计 {feature} 越界与证据"
    ext_list = "\n".join(f"- `{p}`" for p in ext_dirs)
    prompt = f"""【定时巡检】{feature} 每日督察使审计（Lead 触发）

你是 Lead。按 `{role}` 组织一次**只读**审计。

## 0. 先做低成本判断（不写文件、不起子智能体）

```powershell
& "{py}" "{flow}" status --json -p "{project.as_posix()}" -f {feature}
& "{py}" "{flow}" audit -p "{project.as_posix()}" -f {feature}
& "{py}" "{flow}" verify --id {cid} -p "{project.as_posix()}" -f {feature}
```

- 若 phase 仍是 `DONE`，audit 的项目内与外部源都是 0 新增/0 修改/0 删除，且 verify 退出码 0、`releases/{cid}/manifest.json` 的 sha256 与 `state.json` 记录一致、`releases/{cid}/verification.json` 未变 → 只回一行：`静止：{feature} 无变化，无需动作（下次 09:00）`，结束；不写报告、不起子智能体。
- 若最近 7 天台账（`ledger --tail 20`）没有新增且 phase=DONE，另加一句：`建议暂停本条定时任务：schedule_edit {{ id, action:"update", active:false }}`。

## 1. 有变化或非 DONE 时

用 `subagent` 起一个一次性只读督察使（name=`inspector-<YYYYMMDD>`，不复用其他子智能体上下文），prompt 必须含：

- 角色说明书绝对路径：`{role}`
- 项目根 `{project.as_posix()}`、feature `{feature}`、当前候选 `{cid}`
- 外部源：
{ext_list}
- 必做检查：`status --json` / `gate` / `audit` / `verify --id {cid}` / `ledger --tail 20` / 读 `RELEASE-REPORT.md` 结论三态 / `ACCEPTANCE.md` 用户结论 / `verification.json` 抽查 2 个哈希 / 三处漂移（`state.json`、`ledger.md`、磁盘）
- 只写一个文件：`{report}`（6 节结构，同日追加；不要放进 `evidence/{cid}/`，会被 freeze 当候选证据）
- 禁止：改任何代码/文档/状态；跑 `next/advance/freeze/seal/amend/block`；装依赖；重启进程；`create_worktree`
- 回报格式：角色说明书第 5 节七行，≤20 行

## 2. 收到督察使回报后

- 把结论、越界清单、需裁决项原样转给用户（≤10 行）。
- 若 audit 报「基线里没有任何文件」：先跑 `& "{py}" "{flow}" baseline -p "{project.as_posix()}" -f {feature} --source "{dev.as_posix()}"` 重记基线，再让督察使重审；不要假装通过。
- 若结论 FAIL/BLOCKED：不要自己改，写清「已实现 / 未实现 / 卡在哪」和需要用户做的事。
- 不要为这次巡检新建候选、不要 `advance`。

## 3. 纪律

- 只读；本会话可能没有挂载 `team_task_*`，不要依赖任务板。
- 同一 feature 只开一条日审计；要暂停用 `schedule_edit` 改现有那条。
"""
    if args.out:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prompt, encoding="utf-8", newline="\n")
    if args.json:
        print(json.dumps({"title": title, "target": "this_session", "rrule": rrule,
                          "prompt": prompt, "report": report}, ensure_ascii=False, indent=2))
        return
    print("=" * 70)
    print("定时任务（可直接 schedule_create）")
    print("=" * 70)
    print(f"title : {title}")
    print("target: this_session")
    print("rrule :")
    for line in rrule.splitlines():
        print(f"  {line}")
    print()
    print("prompt（复制下面整段；占位符已全部填实）：")
    print("-" * 70)
    print(prompt)
    print("-" * 70)
    print()
    print("等价调用：")
    print(f'schedule_create(title="{title}", target="this_session", '
          f'rrule="""{rrule}""", prompt="<上面整段>")')
    if args.out:
        print(f"\n✓ prompt 已写入 {Path(args.out).expanduser()}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def cmd_dashboard(args) -> None:
    """多 feature 看板：扫描 <root>/**/docs/<feature>/state.json，只读。"""
    root = Path(args.root or args.project).resolve()
    if not root.is_dir():
        die(f"扫描根目录不存在: {root}")

    items: list[dict] = []
    bad: list[dict] = []
    for sp in sorted(root.rglob("state.json")):
        parts = set(p for p in sp.relative_to(root).parts)
        if parts & SKIP_DIR_NAMES or "node_modules" in parts:
            continue
        if sp.parent.parent.name != "docs":
            continue
        feature = sp.parent.name
        project = sp.parent.parent.parent
        try:
            st = read_json(sp)
        except Exception as e:  # 损坏的 state 不能让整个看板挂掉
            bad.append({"project": project.as_posix(), "feature": feature, "error": str(e),
                        "state_file": sp.as_posix()})
            continue
        hist = st.get("history") or []
        last = hist[-1] if hist else {}
        blocked = st.get("blocked") or None
        item = {
            "project": project.as_posix(),
            "feature": feature,
            "phase": st.get("phase") or "?",
            "candidate": st.get("current_candidate") or "-",
            "blocked": blocked,
            "updated_at": st.get("updated_at") or "",
            "last": {
                "at": last.get("at", ""),
                "actor": last.get("actor", ""),
                "action": last.get("action", ""),
                "detail": last.get("detail", ""),
            },
            "state_file": sp.as_posix(),
        }
        if args.gate:
            try:
                target = (args.to or (TRANSITIONS.get(item["phase"]) or ["?"])[0]).upper()
                checks = gate_for(project, feature, target)
                fails = [n for n, ok, _ in checks if not ok]
                item["gate"] = {"target": target, "ok": not fails, "failed": fails}
            except Exception as e:  # 门禁异常只标注，不影响看板
                item["gate"] = {"target": "?", "ok": False, "failed": [f"门禁执行失败: {e}"]}
        items.append(item)

    items.sort(key=lambda x: x["updated_at"], reverse=True)
    shown = items[: args.limit]

    if args.json:
        print(json.dumps({
            "root": root.as_posix(),
            "total": len(items),
            "blocked": sum(1 for i in items if i["blocked"]),
            "items": shown,
            "broken": bad,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"扫描根：{root}")
        phases: dict[str, int] = {}
        for i in items:
            phases[i["phase"]] = phases.get(i["phase"], 0) + 1
        dist = "，".join(f"{k}={v}" for k, v in sorted(phases.items())) or "（无）"
        print(f"共 {len(items)} 个 feature ｜ 阻塞 {sum(1 for i in items if i['blocked'])} ｜ 阶段分布 {dist}")
        if not items:
            print("（没有找到 docs/<feature>/state.json；先 flow.py init）")
        else:
            head = ["项目", "feature", "阶段", "候选", "阻塞", "最近台账"]
            if args.gate:
                head.insert(5, "门禁")
            rows = []
            for i in shown:
                blocked = "-"
                if i["blocked"]:
                    b = i["blocked"]
                    blocked = f"{str(b.get('reason') or '')[:26]}（{b.get('owner') or '?'}）"
                last = i["last"]
                last_txt = f"{last['at'][11:19]} {last['actor']} {last['action']}" if last.get("at") else "-"
                row = [Path(i["project"]).name or i["project"], i["feature"], i["phase"],
                       i["candidate"], blocked, last_txt]
                if args.gate:
                    g = i.get("gate") or {}
                    row.insert(5, "PASS" if g.get("ok") else "FAIL(" + ",".join(g.get("failed") or [])[:24] + ")")
                rows.append(row)
            widths = [max(len(str(r[c])) for r in [head] + rows) for c in range(len(head))]
            def fmt(r):
                return "  ".join(str(v).ljust(widths[c]) for c, v in enumerate(r))
            print("\n" + fmt(head))
            print("  ".join("-" * w for w in widths))
            for r in rows:
                print(fmt(r))
        if bad:
            print(f"\n⚠ {len(bad)} 个 state.json 损坏：")
            for b in bad[:10]:
                print(f"  - {b['project']} / {b['feature']}: {b['error']}")
        print("\n提示：`--json` 给脚本用；`--gate` 顺带跑门禁；`--strict` 有阻塞/损坏时退出码 1。")

    if args.strict and (bad or any(i["blocked"] for i in items)):
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dsh_flow.py", description="DSH 多角色协作开发流程状态机工具")
    # 公共参数既支持写在子命令前，也支持写在子命令后（子命令里的默认值用 SUPPRESS 避免覆盖）。
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-p", "--project", default=argparse.SUPPRESS, help="项目根目录")
    common.add_argument("-f", "--feature", default=argparse.SUPPRESS, help="feature 名称")
    common.add_argument("--package", default=argparse.SUPPRESS, help="流程包目录")
    p.add_argument("-p", "--project", default=".", help="项目根目录（默认当前目录）")
    p.add_argument("-f", "--feature", default=None, help="feature 名称，如 export-report")
    p.add_argument("--package", default=str(Path(__file__).resolve().parent.parent),
                   help="流程包目录（默认脚本上一级）")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, **kwargs):
        kwargs.setdefault("parents", [common])
        return sub.add_parser(name, **kwargs)

    s = add("init", help="初始化 feature 骨架（--kind plugin 同时生成能力包四件套）")
    s.add_argument("--scope", action="append", help="声明写范围（可多次，如 --scope src --scope tests）")
    s.add_argument("--source", action="append", help="项目根之外的源码目录（可多次；插件类项目常用）")
    s.add_argument("--kind", default="project", choices=["project", "plugin"],
                   help="project=普通项目（默认）；plugin=同时生成 <项目>/pack 能力包骨架")
    s.add_argument("--pack-id", default="", help="能力包短 id，默认取 feature")
    s.add_argument("--pack-title", default="", help="能力包标题，默认取 feature")
    s.add_argument("--pack-desc", default="", help="能力包一句话说明")
    s.add_argument("--pack-version", default="0.1.0", help="初始版本号（默认 0.1.0）")
    s.add_argument("--pack-icon", default="🧩", help="列表 emoji 图标")
    s.add_argument("--pack-category", default="协作效率", help="工作台分类")
    s.add_argument("--pack-order", type=int, default=50, help="排序序号（默认 50）")
    s.add_argument("--force", action="store_true")
    s.add_argument("--no-graph", dest="no_graph", action="store_true",
                   help="跳过建图与 .graphifyignore 维护（恢复旧行为 / 排障）")
    s.add_argument("--graph-timeout", dest="graph_timeout", type=int,
                   default=GRAPH_TIMEOUT_DEFAULT, help=f"建图超时秒数（默认 {GRAPH_TIMEOUT_DEFAULT}，超时降级）")
    s.set_defaults(func=cmd_init)

    s = add("baseline", help="记录 E0 基线")
    s.add_argument("--scope", action="append")
    s.add_argument("--source", action="append", help="项目根之外的源码目录（可多次）")
    s.add_argument("--no-auto", action="store_true",
                   help="关闭外部源自动发现（项目根只有 docs/ 时默认会找兄弟 *-dev 目录与 link 目标）")
    s.add_argument("--docs-only", action="store_true",
                   help="只刷新 docs 元数据哈希清单（ACCEPTANCE/ledger/state/health/DESIGN + 封存件），源码基线不动")
    s.set_defaults(func=cmd_baseline)

    s = add("freeze", help="冻结候选")
    s.add_argument("--id", required=True, help="候选编号 C001")
    s.add_argument("--from", dest="from_", required=True, help="开发副本目录")
    s.add_argument("--scope", action="append", help="覆盖 state 里的 scope")
    s.add_argument("--actor", default="executor")
    s.add_argument("--note", default="")
    s.add_argument("--base-type", default="copy", choices=["copy", "direct", "worktree"])
    s.add_argument("--install-order", default="", help="逗号分隔的相对路径，按此顺序安装")
    s.add_argument("--restart-targets", default="", help="逗号分隔的重启目标")
    s.add_argument("--preserve", action="append", help="回滚时必须保留的路径（可多次）")
    s.add_argument("--runtime-kind", default="none", choices=["plugin", "service", "cli", "none"],
                   help="运行时类型；plugin/service 建议声明，便于事后握手核版本")
    s.add_argument("--runtime-version", default="", help="安装后运行时应报的版本，如 0.4.1")
    s.add_argument("--health-url", default="", help="健康检查地址（返回 JSON，含版本字段）")
    s.add_argument("--requires-restart", action="store_true", help="安装后必须重启宿主才生效")
    s.add_argument("--reused", action="append", metavar="检查号:理由",
                   help='登记「本候选未触及而可复用」的检查项（可多次、保序），如 --reused "V4:tools/roles 逐字节未变"')
    s.add_argument("--skip-qc", dest="skip_qc", action="store_true",
                   help="跳过冻结时的只读静态检查（排障用；跳过时本候选没有 QC-static 证据）")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_freeze)

    s = add("verify", help="校验候选 manifest")
    s.add_argument("--id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_verify)

    s = add("drop", help="作废候选清理：releases/evidence 移入 archive/，从 state 移除（只移动不删除）")
    s.add_argument("--id", required=True, help="要作废的候选编号，如 C001")
    s.add_argument("--reason", required=True, help="作废理由（写入台账与 archive/<C>-<时间戳>/DROP-NOTE.md）")
    s.add_argument("--actor", default="executor")
    s.add_argument("--force", action="store_true", help="已 seal 的候选也允许作废（需自行承担封存证据失去落点）")
    s.set_defaults(func=cmd_drop)

    s = add("audit", help="越界审计：对比基线")
    s.add_argument("--strict", action="store_true", help="有越界嫌疑时退出码 1")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_audit)

    s = add("evidence", help="生成统一格式的证据文件")
    s.add_argument("--check", required=True)
    s.add_argument("--candidate")
    s.add_argument("--grade", default="A", choices=["A", "B", "C", "D"])
    s.add_argument("--result", default="pass", choices=["pass", "fail", "skip", "unknown"])
    s.add_argument("--command", default="")
    s.add_argument("--output", default="")
    s.add_argument("--title", default="")
    s.add_argument("--note", default="")
    s.add_argument("--actor", default="executor")
    s.set_defaults(func=cmd_evidence)

    s = add("status", help="显示状态与门禁")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    s = add("scope", help="补正声明写范围：只追加 state.scope（不动 baseline.json）")
    s.add_argument("--add", action="append", metavar="相对路径",
                   help="要追加进 scope 的相对项目根路径（可多次）")
    s.add_argument("--actor", default="lead")
    s.set_defaults(func=cmd_scope)

    s = add("next", help="生成下一位角色的交接包")
    s.add_argument("--role", choices=list(ROLE_FILES) + ["user", "none"])
    s.add_argument("--blocked-by", default="", help="共享任务板上的前置 task id")
    s.add_argument("--entry-note", default="")
    s.add_argument("--key-note", dest="key_note", action="append", default=[], metavar="文本|@文件",
                   help='叠加注入「项目关键事实」子块：文本，或 @<文件绝对路径>（文件不存在 → 退出码 2）；'
                        '可多次传，按传入顺序全部拼进交接包（C002 起；只传一次仍照旧生效）')
    s.add_argument("--memories-dir", dest="memories_dir", default="",
                   help="覆盖记忆根目录（隔离测试用；等价于环境变量 DSH_FLOW_MEMORIES_DIR）")
    s.add_argument("--no-context", dest="no_context", action="store_true",
                   help="关闭「已知上下文」摘要（排障用，回到旧交接包）")
    s.add_argument("--max-context-chars", dest="max_context_chars", type=int,
                   default=DEFAULT_MAX_CONTEXT_CHARS,
                   help=f"上下文摘要字符预算（默认 {DEFAULT_MAX_CONTEXT_CHARS}）")
    # 仅测试用的「隐藏旋钮」（DESIGN §九 Q3）：默认取本机真实位置，文档里不宣传。
    s.add_argument("--rag-dir", dest="rag_dir", default="",
                   help="覆盖 RAG-Anything 配置目录（隔离测试用；默认 %%USERPROFILE%%\\.dsh\\raganything）")
    s.add_argument("--mnemon-cli", dest="mnemon_cli", default="",
                   help="覆盖 mnemon CLI 路径（隔离测试用；默认读 profile 的 mnemon.config.cliPath）")
    s.set_defaults(func=cmd_next)

    s = add("lesson", help="跨 feature 教训库：add 追加一条 / list 只读列出")
    lsub = s.add_subparsers(dest="lesson_cmd", required=True)
    la = lsub.add_parser("add", parents=[common], help="追加一条教训（自动编号，打印新 ID）")
    la.add_argument("--symptom", default="", help="症状（必填：一句话，能被人搜到）")
    la.add_argument("--cause", default="", help="根因")
    la.add_argument("--fix", default="", help="做法（必填：下次怎么办）")
    la.add_argument("--tags", default="", help="适用角色，逗号分隔（lead,planner,executor,verifier,inspector,all）")
    la.add_argument("--role", default="", help="等价于把该角色并入 --tags")
    la.set_defaults(func=cmd_lesson)
    ll = lsub.add_parser("list", parents=[common], help="只读列出教训（可按角色过滤）")
    ll.add_argument("--role", default="", help="只看该角色的教训（含 all）")
    ll.set_defaults(func=cmd_lesson)

    s = add("advance", help="推进阶段（过门禁）")
    s.add_argument("--to", required=True)
    s.add_argument("--actor", required=True)
    s.add_argument("--note", default="")
    s.add_argument("--force", action="store_true")
    s.add_argument("--reason", default="")
    s.set_defaults(func=cmd_advance)

    s = add("gate", help="汇总门禁")
    s.add_argument("--to")
    s.set_defaults(func=cmd_gate)

    s = add("drive", help="只读合成：phase + 门禁(硬/软) + 下一位 + 能否推进 + 建议命令")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_drive)

    s = add("ledger", help="追加/查看台账")
    s.add_argument("-m", "--message", default="")
    s.add_argument("--actor", default="lead")
    s.add_argument("--tail", type=int, default=20)
    s.set_defaults(func=cmd_ledger)

    s = add("doctor", help="环境自检")
    s.add_argument("--backup-dir", dest="backup_dir", default="",
                   help="覆盖快照根（与 seal 同语义：--backup-dir > 环境变量 FLOW_BACKUP_ROOT > "
                        "默认 %%USERPROFILE%%\\.dsh\\flow-snapshots；排障/自测用）")
    s.set_defaults(func=cmd_doctor)

    s = add("health", help="输出 docs/<feature>/health.json（阶段/门禁/候选/封存/最近台账）")
    s.add_argument("--out", default="", help="输出路径，默认 docs/<feature>/health.json")
    s.add_argument("--no-gate", action="store_true", help="不跑门禁（更快）")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_health)

    s = add("dashboard", help="多 feature 看板（扫描 **/docs/*/state.json）")
    s.add_argument("--root", default="", help="扫描根目录，默认取 -p")
    s.add_argument("--gate", action="store_true", help="同时跑当前阶段门禁")
    s.add_argument("--to", default="", help="配合 --gate 指定目标阶段")
    s.add_argument("--strict", action="store_true", help="有阻塞或 state 损坏时退出码 1")
    s.add_argument("--limit", type=int, default=100)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_dashboard)

    s = add("inspector", help="生成可直接 schedule_create 的巡检 prompt")
    s.add_argument("--candidate", default="")
    s.add_argument("--rrule", default="", help="默认每天 09:00（Asia/Shanghai）")
    s.add_argument("--title", default="")
    s.add_argument("--python", default="", help="覆盖 $PY 路径")
    s.add_argument("--out", default="", help="把 prompt 写入文件")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_inspector)

    s = add("block", help="标记阻塞（用户在等你/环境不可用/技术卡住）")
    s.add_argument("--reason", required=True)
    s.add_argument("--owner", default="user", choices=["user", "lead", "executor", "verifier", "env"])
    s.add_argument("--kind", default="user", choices=["user", "env", "tech", "external"])
    s.add_argument("--actor", default="lead")
    s.set_defaults(func=cmd_block)

    s = add("unblock", help="解除阻塞")
    s.add_argument("--note", default="")
    s.add_argument("--actor", default="lead")
    s.set_defaults(func=cmd_unblock)

    s = add("amend", help="DESIGN 变更：归档旧版、置为待用户确认、记台账")
    s.add_argument("--reason", required=True)
    s.add_argument("--actor", default="lead")
    s.set_defaults(func=cmd_amend)

    s = add("handshake", help="运行时版本握手（拉健康检查，比对期望版本，落 R1 证据）")
    s.add_argument("--id")
    s.add_argument("--url", default="")
    s.add_argument("--expect", default="")
    s.add_argument("--field", default="version", help="JSON 里版本字段的路径，如 version 或 data.version")
    s.add_argument("--timeout", type=float, default=10.0)
    s.add_argument("--actor", default="verifier")
    s.set_defaults(func=cmd_handshake)

    s = add("seal", help="封存验证证据（V* + 发布报告 + 部署台账），并把 docs/<feature>/ 异地快照")
    s.add_argument("--id")
    s.add_argument("--actor", default="verifier")
    s.add_argument("--no-backup", dest="no_backup", action="store_true",
                   help="本次不写异地快照（排障/磁盘紧张时用；DESIGN flow-backup-a §3.6）")
    s.add_argument("--backup-dir", dest="backup_dir", default="",
                   help="覆盖快照根（默认 %%USERPROFILE%%\\.dsh\\flow-snapshots；自测用）")
    s.set_defaults(func=cmd_seal)
    return p


def main() -> None:
    args = build_parser().parse_args()
    # lesson / dashboard 不按 feature 工作（lesson 只读写 ops/lessons.md，不碰 state.json）
    if args.cmd not in {"dashboard", "lesson"} and not getattr(args, "feature", None):
        print("✗ 缺少 -f/--feature", file=sys.stderr)
        sys.exit(2)
    args.project = str(Path(args.project).resolve())
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # 兜底：给出可行动的错误，不打印整段 traceback
        print(f"✗ 执行失败: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
