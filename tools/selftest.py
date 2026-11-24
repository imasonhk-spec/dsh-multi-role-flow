# -*- coding: utf-8 -*-
"""dsh_flow.py 端到端自测（临时目录，不污染项目）。

覆盖四套：
  A. 无运行时：init → baseline → 设计/规划门禁 → freeze → verify 篡改 → 越界 → 报告 → seal → TRIAL → DONE
  B. 有运行时（插件类）：amend 变更、block/unblock、runtime 冻结、handshake 版本握手、
     seal 封存后篡改检测、门禁拦截 TRIAL。
  C. 只有 docs/ 的项目：baseline 自动发现外部源、audit 外部漂移、inspector 输出。
  D. 能力包项目：未声明 runtime 告警、声明后 manifest.runtime 生效、版本不一致告警。
  E. 看板：无 -f 跨项目扫描、阻塞标注、--gate 门禁列、--json、--strict。
  G. 能力包骨架：init --kind plugin 生成四件套、无残留占位符、契约字段、smoke 33 条断言。
  H. health.json：落盘、结构、随阶段更新、--json 可解析。
  I. 文档漂移：SKILL/全包 md 的命令 ↔ --help 双向对照（docs/<feature>/releases/** 是封存件、扫描跳过；
     docs/<feature>/evidence/** 抄本仍扫，但只认「命令调用位」，数据列/反引号引用不误报）、
     漂移检查器自检（跨行/数据列/路径片段/调用位/豁免名单五向压测）、术语表完整性。
  J. 可分发 bundle：dsh-bundle 产物完整性、patch 用独立 provider、技能无占位符、build --check；
     反向探针走 %TEMP% 副本（`--check --dir`），**不改真 bundle**（N-06 并发假失败的根因）。
     **C001（bundle-skills-coverage）**：`skills/` 整目录收录——按源仓库 `skills/*/` 枚举（不写死技能名），
     非生成技能全部进 `_copied_files()` 比对集，生成版（`_skill_text()` 产出）是唯一例外；三条反向断言
     （删文件 / 改一字节 / 塞 ghost 技能）证明「源和 bundle 都不含 → 不比 → exit 0」的盲区已消失。
  N. flow-hardening：门禁「待用户试用清单」标题包含匹配（带序号通过 / 无该节仍拒）、
     audit 对 freeze/seal 产物不误报（新增免报 + 修改时校 verification.json 记录哈希，
     改一字节仍必须告警）、init 默认把根级文档纳入 scope（--scope 是追加）。
  P. flow-context-boost：交接包 §1「已知上下文」四子块（含 KEY.md 直读、--key-note、--no-context）、
     角色要点按阶段裁剪与五节必保（交接包 ≤12000 字节）、ops/lessons.md 教训库闭环
     （lesson add/list + next 同类坑）、init 默认建图与 .graphifyignore（幂等 / 保留自定义行 /
     只含真实源码 / --no-graph 可关）、缺数据一律退出码 0 而参数错误退出码 2；
     G5（记忆真读）：MEMORY.md 兜底与语义标注、尾部取序、三候选合并各标来源、真实记忆命中
     与只读证明、带记忆时五角色仍 ≤12000 字节且必保五节全 ✅。
  Q. flow-quality-boost：A 组只读静态检查（freeze 内挂载、QC-static 证据契约、
     `__pycache__` 铁律、`--skip-qc`）、B 组「知识入口」四行（离线采集 / `--rag-dir` 降级 /
     五角色 ≤12000 字节 / 体积止损）、C 组 `drive` 只读合成（文本 8 标签 / JSON 12 键 /
     严格只读 / 三种退出码 / 四处文档同步）、D 组图谱证据软告警（前缀匹配 + 只看该节正文 + 不阻断）、
     F 组（C003）图谱污染：`.graphifyignore` 的 bundle 变体排除行（`_ensure_graphifyignore` 幂等 /
     只追加）、`RE_GRAPH_COPY_SOURCE` 命中 `dsh-bundle`/`-live`/`-dist` 而**不**误伤 `dsh-bundleable`。
     **G 组（C007，并入本套）**：回退判据 `_doc_only_candidate()` 的 6 个边界 + ROADMAP 不写死状态值
     （§0.1 历史快照之外的赋值式陈述必须同句标时点，现值只认 `flow.py status` / `flow.py drive`）；
     **G5（C008 回归守门员）**：P 证据 `check_id` 的两种合法形态（`P29` / `P29-doc-only-candidate`）
     都认、无文件不认——C007 就是死在「只认纯数字」这条收紧上。
  S. flow-quality-boost C007（Lead 裁决后的**主判据**）：文档类候选免 P* 证据改为看「相邻候选
     **变更集**」——7 个边界（首候选回退 / 变更集为空 / 只改文档 / 新增 .py / 只删 .py /
     文档重命名 / 代码类重命名）+ 真实 `flow-quality-boost` C001 与 C005→C006 实测。
  T. flow-backup-a：`seal` 后异地快照（E1 三件齐全 / E2 逐字节一致 / E3 `--no-backup` 不产生副本 /
     E4 备份失败不改 seal 结论且有 `backup-failed` 台账 / E5 doctor 快照健康「正常 ✅、改一字节 ⚠」
     + `BACKUP_ROOT` 默认值与 `FLOW_BACKUP_ROOT` 覆盖）。全部落 TEMP 的 `--backup-dir`，不写真实备份目录。
     **U（C002 缺陷回归）**：D-02 快照原子化（临时名 → rename；中途失败不留最终名/`.partial-*`、
     重跑自愈、冻结时钟下同秒重跑仍幂等）、D-03 `doctor --backup-dir`（显示与数据源都跟随、
     不传时旧行为不变）、D-04 `selftest.py --help`（exit 0、有用法、**不跑用例**）。
     **V（C003 缺陷回归）**：D-06 TEMP 根清理（正常路径 `finally` / 未捕获异常 / `atexit` 二次兜底 /
     目录名前缀双重校验，`--help` 路径不清理）、D-07 `sys.dont_write_bytecode`（子进程镜像验证
     `importlib` 载入 `dsh_flow` 不再写 `tools/__pycache__`）。
  W. P0-13 / P0-14（另一会话写入，`flow-backup-a` C003 收编，`flow-audit-hygiene` C001 认领）：
     audit 不把「冻结前创建且已登记」的开发期新增误报为越界；`ops/lessons.md` 视为工具生成。
  X. flow-audit-hygiene C001（audit 只报真问题）：E1 `dsh-bundle-dist/**` 生成物假红归零
     （`SKIP_DIR_NAMES` + 旧基线条目过滤，不能反过来变成几十条「删除」）、E2 `ROADMAP.md` 认领
     （认领前仍告警 / 认领后「已登记且与候选一致」）、E3 `ops/lessons.md` 豁免完整
     （「未登记」与「不在声明写范围内」一起免，且不连坐别的越界文件）、
     E4 `mtime` 缺失不豁免（单元级注入缺 `mtime` 的 current 项 + 确认 audit 真走该函数）、
     E5 `baseline` 重记后 audit「项目内 新增/修改/删除」= 0。
     E6（全量回归）由 `docs/flow-audit-hygiene/evidence/C001/P4-P6` 承载。
  Y. a-group-hardening：`.ps1` 静态守卫（Y1 扫描集非空 / Y2 仓内 .ps1 全部带 UTF-8 BOM /
     Y3 真实 PS 解析器逐个 0 error / Y4 无「cmd /c 与 rd /s｜rmdir /s｜del /f /s 同行」的
     危险删除形态（docs/** 豁免）/ Y5 检测器正反向对照 / Y6 反向断言：去 BOM 的副本必被判缺）。
     判据全在纯函数里（`ps1_files` / `has_utf8_bom` / `bom_missing` / `danger_lines`），
     不依赖任何 `.ps1` 自己能跑起来——这正是本组要守的坑（PS 5.1 按 ANSI 解必炸）。
"""
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# C003 / D-07：suite U（以及 Q/R/S 的部分探针）用 `importlib` 从 `tools/` 载入 `dsh_flow.py`，
# `SourceFileLoader` 会顺手把 `tools\__pycache__\dsh_flow.cpython-3xx.pyc`（实测 308,598 B）写出来。
# 这份缓存自己无害，但下一次 `freeze` 的 QC-static 会扫到 `__pycache__` 直接判 fail——C002 冻结时
# `QC-static.md` 那条 `result=fail` 的真因就是它。这里在本进程里统一关掉字节码写入：
# 只影响「本进程 import 时要不要落 .pyc」，不动任何已有缓存（本进程也没删过任何目录）。
# 子进程各自是独立解释器，不受这一行影响；而子进程跑的 `dsh_flow.py` 都是脚本入口，本来不生成缓存。
sys.dont_write_bytecode = True

PY = sys.executable
PKG = Path(__file__).resolve().parent.parent
FLOW = PKG / "tools" / "dsh_flow.py"
# 2026-11-21：TEMP 下用固定目录名时，两个并发 selftest 会互相删对方的 fixture
# （实测 suite_l 因此报 FileNotFoundError: noise-proj\baseline.json 假失败）。
# 加 pid 后缀隔离；收尾仍按本进程自己的 ROOT 清理。
ROOT = Path(os.environ.get("TEMP", str(PKG))) / f"dsh-flow-selftest-{os.getpid()}"
# C003 / D-07：开跑前 `tools/__pycache__` 的真实内容（suite V 用它判断「没新增缓存」，
# 而不是「缓存必须不存在」——用户自己跑过 py_compile 留下的缓存不该被本自测判红、更不该被删）。
TOOLS_PYCACHE_BASELINE = (
    tuple(sorted(p.name for p in (PKG / "tools" / "__pycache__").glob("*")))
    if (PKG / "tools" / "__pycache__").is_dir() else ()
)
RUNTIME_VERSION = "1.0.0"
# flow-backup-a：各套里的 `seal` 默认会把 `docs/<feature>/` 快照到 `%USERPROFILE%\.dsh\flow-snapshots`。
# 自测**绝不能**写真实备份目录（污染用户副本、还可能把 TEMP fixture 的路径写进真实台账），
# 所以在模块导入时把根钉到 TEMP（子进程继承本进程环境变量）；suite_t 再用 `--backup-dir` 显式覆盖。
os.environ.setdefault("FLOW_BACKUP_ROOT", str(ROOT / "flow-snapshots"))

results = []


def run(label, *args, expect=0):
    cmd = [PY, str(FLOW), *args]
    p = _sp(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    ok = (p.returncode == expect)
    results.append((label, ok, p.returncode))
    print(f"\n=== {label}  (exit={p.returncode}, expect={expect}) {'OK' if ok else 'FAIL'} ===")
    print(out.strip()[:2200])


def capture(*args, cwd=None):
    """跑一条命令并返回 (stdout+stderr, exitcode)，不打印、不记结果。

    `cwd`：子进程工作目录（默认继承本进程）。G5 的「会话 cwd hash」候选要靠它控制——
    `next` 用 `Path.cwd()` 算 projectId，所以不显式给 cwd 时测试结果会随操作者的当前目录变化。
    """
    p = _sp([PY, str(FLOW), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(cwd) if cwd else None)
    return (p.stdout or "") + (p.stderr or ""), p.returncode


def check(label, cond, detail=""):
    results.append((label, bool(cond), 0))
    print(f"\n=== {label}  {'OK' if cond else 'FAIL'} ===")
    if detail:
        print(detail[:1500])


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_design(docs: Path, confirmed: bool = True):
    write(docs / "DESIGN.md",
          "# DESIGN\n\n## 验收标准\n| P1 | 退出码 0 |\n\n## 不改什么（边界）\n| 不碰 docs/ |\n\n"
          f"状态：{'已确认' if confirmed else '待用户确认'}\n")


def write_plan(docs: Path):
    plan = docs / "planning"
    write(plan / "COORDINATION-PLAN.md", "# C\n\n## 权限矩阵\n| 执行线程 | src/ | 不改 docs/ |\n")
    write(plan / "EXECUTION-WORKPLAN.md", "# E\n\n## 任务分解\n- E1 写 src/demo.py\n")
    write(plan / "VALIDATION-WORKPLAN.md", "# V\n\n## 检查项\n- V1 py_compile\n")
    write(plan / "SOURCE-PLAN.md", "# S\n\n用户原话：做一个 demo。\n")


def write_report(docs: Path, cid: str = "C001"):
    write(docs / "releases" / cid / "RELEASE-REPORT.md",
          "# report\n\n## 待用户试用清单\n- 真实体验\n\n## 证据诚实性声明\n无 mock。\n\n结论：已上线可试用\n")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = json.dumps({"ok": True, "version": RUNTIME_VERSION, "routes": ["GET /health"]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # 静音
        pass


def start_server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def suite_a():
    PROJ = ROOT / "proj"
    DEV = ROOT / "proj-dev"
    (PROJ / "src").mkdir(parents=True)
    (DEV / "src").mkdir(parents=True)
    write(PROJ / "src" / "wordstat.py", '# v1\ndef main():\n    return "v1"\n')
    write(DEV / "src" / "wordstat.py", '# v2\ndef main():\n    return "v2"\n')
    P = ["-p", str(PROJ), "-f", "demo"]

    out, code = capture("init", *P, "--scope", "src")
    check("A: init", code == 0, out[-600:])
    check("A: init 打印建图提示（graphify + gitnexus wrapper + --skip-git）",
          code == 0 and "graphify" in out and "gitnexus.cmd" in out and "--skip-git" in out,
          out[-900:])
    check("A: init 建图提示包含项目根绝对路径", PROJ.as_posix() in out, out[-900:])
    # flow-context-boost B-1：init 现在**默认执行**建图并维护 .graphifyignore（旧断言保留、只加不减）
    ign = PROJ / ".graphifyignore"
    check("A: init 默认维护 .graphifyignore（首行注释 + 9 行排除，C003 起含 bundle 变体）",
          ign.is_file() and ign.read_text(encoding="utf-8").startswith("# 由 dsh_flow.py init 维护")
          and all(ln in ign.read_text(encoding="utf-8") for ln in
                  ("docs/**/releases/", "docs/**/archive/", "docs/**/files/",
                   "docs/**/evidence/", "examples/", "dsh-bundle/",
                   "dsh-bundle-live/", "dsh-bundle-dist/", "graphify-out/")),
          out[-400:])
    check("A: init 默认建图（graphify-out/graph.json 存在）",
          (PROJ / "graphify-out" / "graph.json").is_file(), out[-400:])
    run("A: baseline", "baseline", *P)
    run("A: DESIGN unfilled -> reject PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead", expect=1)

    docs = PROJ / "docs" / "demo"
    write_design(docs)
    run("A: DESIGN filled -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    write_plan(docs)
    run("A: PLAN -> EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")

    run("A: freeze C001", "freeze", *P, "--id", "C001", "--from", str(DEV), "--scope", "src", "--actor", "executor")
    out, code = capture("verify", *P, "--id", "C001")
    check("A: verify 通过并提示『未 seal』", code == 0 and "未 seal" in out, out[-700:])

    evil = docs / "releases" / "C001" / "files" / "src" / "evil.py"
    write(evil, "# unregistered\n")
    run("A: tampered -> verify FAIL", "verify", *P, "--id", "C001", expect=1)
    evil.unlink()
    run("A: restored -> verify", "verify", *P, "--id", "C001")

    run("A: EXECUTING -> VERIFYING", "advance", *P, "--to", "VERIFYING", "--actor", "executor")
    run("A: no report -> reject TRIAL", "advance", *P, "--to", "TRIAL", "--actor", "verifier", expect=1)

    write_report(docs)
    out, code = capture("gate", *P, "--to", "TRIAL")
    check("A: 未 seal 时 gate TRIAL 拦人并说明双清单",
          code == 1 and "未 seal" in out and "manifest.evidence" in out, out[-900:])
    run("A: seal C001", "seal", *P, "--id", "C001")
    out, code = capture("verify", *P, "--id", "C001")
    check("A: seal 后 verify 校验封存", code == 0 and "封存校验通过" in out, out[-700:])
    run("A: sealed -> TRIAL", "advance", *P, "--to", "TRIAL", "--actor", "verifier")
    run("A: acceptance empty -> reject DONE", "advance", *P, "--to", "DONE", "--actor", "user", expect=1)

    write(docs / "ACCEPTANCE.md", "# 验收\n\n用户结论：通过\n\n用户原话：可以。\n")
    run("A: acceptance filled -> DONE", "advance", *P, "--to", "DONE", "--actor", "user")

    write(PROJ / "src" / "wordstat.py", '# main tree edited directly\ndef main():\n    return "x"\n')
    write(PROJ / "unregistered.py", "# unregistered\n")
    run("A: audit flags drift", "audit", *P)
    run("A: status", "status", *P)
    run("A: doctor", "doctor", *P)


def suite_b():
    PROJ = ROOT / "plugin-proj"
    DEV = ROOT / "plugin-proj-dev"
    (PROJ / "src").mkdir(parents=True)
    (DEV / "src").mkdir(parents=True)
    write(PROJ / "src" / "plugin.js", "export const v = 'old'\n")
    write(DEV / "src" / "plugin.js", "export const v = 'new'\n")
    P = ["-p", str(PROJ), "-f", "plug"]

    run("B: init", "init", *P, "--scope", "src")
    run("B: baseline", "baseline", *P)
    docs = PROJ / "docs" / "plug"
    write_design(docs)

    run("B: amend DESIGN", "amend", *P, "--reason", "验收标准微调")
    run("B: blocked by amend -> reject PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead", expect=1)
    run("B: unblock", "unblock", *P, "--note", "用户已确认 DESIGN v2")
    write_design(docs)
    run("B: confirmed -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")

    write_plan(docs)
    run("B: PLAN -> EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")

    srv, port = start_server()
    health = f"http://127.0.0.1:{port}/health"
    run("B: freeze plugin with runtime", "freeze", *P, "--id", "C001", "--from", str(DEV), "--scope", "src",
        "--runtime-kind", "plugin", "--runtime-version", RUNTIME_VERSION,
        "--health-url", health, "--requires-restart", "--actor", "executor")
    run("B: verify C001", "verify", *P, "--id", "C001")
    run("B: EXECUTING -> VERIFYING", "advance", *P, "--to", "VERIFYING", "--actor", "executor")

    out, code = capture("handshake", *P, "--id", "C001", "--expect", "9.9.9", "--url", health)
    check("B: handshake FAIL 给出重启指引", code == 1 and "重启" in out, out[-700:])
    r1 = (docs / "evidence" / "C001" / "R1-handshake.md").read_text(encoding="utf-8")
    check("B: R1 证据记录 fail 与实际版本", "结果：fail" in r1 and "9.9.9" in r1, r1[:400])
    run("B: handshake correct -> PASS", "handshake", *P, "--id", "C001",
        "--expect", RUNTIME_VERSION, "--url", health)
    srv.shutdown()

    write_report(docs)
    run("B: report w/o seal -> reject TRIAL", "advance", *P, "--to", "TRIAL", "--actor", "verifier", expect=1)
    run("B: seal C001", "seal", *P, "--id", "C001")
    run("B: gate TRIAL passes", "gate", *P, "--to", "TRIAL")
    run("B: TRIAL", "advance", *P, "--to", "TRIAL", "--actor", "verifier")

    ev = docs / "evidence" / "C001" / "R1-handshake.md"
    with ev.open("a", encoding="utf-8") as f:
        f.write("\n篡改测试：封存后追加一行\n")
    run("B: sealed evidence tampered -> verify FAIL", "verify", *P, "--id", "C001", expect=1)
    ev.write_text(ev.read_text(encoding="utf-8").replace("\n篡改测试：封存后追加一行\n", ""),
                  encoding="utf-8", newline="\n")
    run("B: restored -> verify PASS", "verify", *P, "--id", "C001")

    # 双清单第二份：封存后的发布报告被改，verify 必须失败
    rep = docs / "releases" / "C001" / "RELEASE-REPORT.md"
    rep_orig = rep.read_text(encoding="utf-8")
    rep.write_text(rep_orig + "\n封存后追加一行\n", encoding="utf-8", newline="\n")
    run("B: sealed report tampered -> verify FAIL", "verify", *P, "--id", "C001", expect=1)
    rep.write_text(rep_orig, encoding="utf-8", newline="\n")
    run("B: report restored -> verify PASS", "verify", *P, "--id", "C001")

    run("B: block waiting user", "block", *P, "--reason", "等用户重启 DSH", "--owner", "user", "--kind", "env")
    run("B: blocked -> reject DONE", "advance", *P, "--to", "DONE", "--actor", "user", expect=1)
    run("B: unblock", "unblock", *P, "--note", "已重启，握手通过")
    write(docs / "ACCEPTANCE.md", "# 验收\n\n用户结论：通过\n\n用户原话：可以。\n")
    run("B: DONE", "advance", *P, "--to", "DONE", "--actor", "user")

    # 外部源目录：插件类项目的源码常在项目根之外
    ext = ROOT / "plugin-src"
    write(ext / "pack" / "index.js", "export const v = 'v1'\n")
    run("B: baseline with external source", "baseline", *P, "--source", str(ext))
    write(ext / "pack" / "index.js", "export const v = 'v2'\n")
    run("B: audit detects external drift", "audit", *P)
    run("B: audit --strict -> exit 1", "audit", *P, "--strict", expect=1)


def suite_c():
    """插件/能力包项目：项目根只有 docs/，源码在兄弟 *-dev 目录。"""
    PROJ = ROOT / "docs-only"
    DEV = ROOT / "docs-only-dev"
    (PROJ / "docs").mkdir(parents=True)
    write(DEV / "pack" / "index.js", "export const v = 'a'\n")
    P = ["-p", str(PROJ), "-f", "plug"]

    run("C: init docs-only project", "init", *P, "--scope", ".")
    run("C: baseline auto-discovers external", "baseline", *P)
    bl = json.loads((PROJ / "docs" / "plug" / "baseline.json").read_text(encoding="utf-8"))
    ext = bl.get("external")
    check("C: external 是数组且非空", isinstance(ext, list) and len(ext) == 1 and ext[0]["files"],
          json.dumps(ext, ensure_ascii=False)[:800])
    check("C: 自动发现标记正确", ext and ext[0]["discovered_by"] == "兄弟开发副本",
          str(ext[0].get("discovered_by") if ext else None))

    write(DEV / "pack" / "index.js", "export const v = 'b'\n")
    run("C: audit flags external drift", "audit", *P)
    run("C: audit --strict -> exit 1", "audit", *P, "--strict", expect=1)

    out, code = capture("doctor", *P)
    check("C: doctor 报外部源与基线", code == 0 and "baseline :" in out and "外部源" in out, out[-800:])

    out, code = capture("inspector", *P)
    check("C: inspector 无残留占位符", code == 0 and "{{" not in out, out[:400])
    check("C: inspector 填实了项目与 feature 路径",
          code == 0 and PROJ.as_posix() in out and "schedule_create" in out and "静止" in out, out[:600])
    jout, jcode = capture("inspector", *P, "--json")
    try:
        data = json.loads(jout)
        ok = jcode == 0 and data["prompt"] and data["report"].endswith(".md") and data["rrule"].count("\n") == 1
    except Exception as e:  # noqa: BLE001
        ok, data = False, {"error": str(e)}
    check("C: inspector --json 可解析", ok, json.dumps(data, ensure_ascii=False)[:600])


def suite_d():
    """P0-6：能力包/插件项目未声明 runtime 要告警；声明后 manifest.runtime 生效。"""
    PROJ = ROOT / "pack-proj"
    DEV = ROOT / "pack-proj-dev"
    (PROJ / "src").mkdir(parents=True)
    (DEV / "src").mkdir(parents=True)
    write(PROJ / "package.json",
          json.dumps({"name": "@local/plug", "version": "0.1.0",
                      "dsh": {"capabilityPack": {}}}, ensure_ascii=False, indent=2))
    write(PROJ / "src" / "plugin.js", "export const v = 'old'\n")
    write(DEV / "src" / "plugin.js", "export const v = 'new'\n")
    P = ["-p", str(PROJ), "-f", "plug"]
    docs = PROJ / "docs" / "plug"

    run("D: init", "init", *P, "--scope", "src")
    run("D: baseline", "baseline", *P)
    write_design(docs)
    write_plan(docs)
    run("D: DESIGN -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    run("D: PLAN -> EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")

    out, code = capture("freeze", *P, "--id", "C001", "--from", str(DEV), "--scope", "src",
                        "--actor", "executor")
    check("D: 未声明 runtime 给出告警", code == 0 and "未声明 runtime" in out, out[-900:])
    m1 = json.loads((docs / "releases" / "C001" / "manifest.json").read_text(encoding="utf-8"))
    check("D: 未声明时 runtime 为空", m1.get("runtime") is None, json.dumps(m1.get("runtime")))

    out, code = capture("gate", *P, "--to", "TRIAL")
    check("D: gate TRIAL 说明握手不计入门禁", "不计入本次门禁" in out, out[-700:])

    write(DEV / "src" / "plugin.js", "export const v = 'v2'\n")
    out, code = capture("freeze", *P, "--id", "C002", "--from", str(DEV), "--scope", "src",
                        "--runtime-kind", "plugin", "--runtime-version", "0.1.0",
                        "--health-url", "http://127.0.0.1:1/health", "--actor", "executor")
    m2 = json.loads((docs / "releases" / "C002" / "manifest.json").read_text(encoding="utf-8"))
    rt = m2.get("runtime") or {}
    check("D: 声明 runtime 后 manifest 记录 kind/version",
          code == 0 and rt.get("kind") == "plugin" and rt.get("version") == "0.1.0",
          json.dumps(rt, ensure_ascii=False))

    write(DEV / "src" / "plugin.js", "export const v = 'v3'\n")
    out, code = capture("freeze", *P, "--id", "C003", "--from", str(DEV), "--scope", "src",
                        "--runtime-kind", "plugin", "--runtime-version", "9.9.9",
                        "--health-url", "http://127.0.0.1:1/health", "--actor", "executor")
    check("D: 版本与 package.json 不一致告警", code == 0 and "不一致" in out, out[-900:])


def suite_e():
    """看板：无 -f、跨项目扫描、阻塞标注、--gate、--json、--strict。"""
    PROJ = ROOT / "dash-proj"
    (PROJ / "src").mkdir(parents=True)
    write(PROJ / "src" / "x.py", "print(1)\n")
    P = ["-p", str(PROJ), "-f", "dash"]
    run("E: init", "init", *P, "--scope", "src")
    docs = PROJ / "docs" / "dash"
    write_design(docs)
    run("E: block", "block", *P, "--reason", "等待用户确认", "--owner", "user", "--kind", "user")

    out, code = capture("dashboard", "--root", str(ROOT))
    check("E: dashboard 无 -f 可用且列出多个 feature",
          code == 0 and "dash" in out and "demo" in out and "plug" in out, out[-1200:])
    check("E: 表里标出阻塞", "等待用户确认" in out, out[-900:])

    jout, jcode = capture("dashboard", "--root", str(ROOT), "--json")
    try:
        data = json.loads(jout)
        items = data.get("items") or []
        dash = [i for i in items if i["feature"] == "dash"]
        ok = bool(jcode == 0 and dash and dash[0]["blocked"] and data.get("blocked", 0) >= 1)
    except Exception as e:  # noqa: BLE001
        ok, data = False, {"error": str(e)}
    check("E: --json 可解析且 blocked 计数正确", ok, json.dumps(data, ensure_ascii=False)[:600])

    out, code = capture("dashboard", "--root", str(ROOT), "--gate")
    check("E: --gate 输出门禁列", code == 0 and ("PASS" in out or "FAIL" in out), out[-700:])
    run("E: --strict 有阻塞 -> exit 1", "dashboard", "--root", str(ROOT), "--strict", expect=1)


def suite_g():
    """P1-2：能力包骨架（init --kind plugin）——生成、占位符、契约字段、smoke。"""
    PROJ = ROOT / "pack-init"
    PROJ.mkdir(parents=True, exist_ok=True)
    P = ["-p", str(PROJ), "-f", "demo-pack"]
    run("G: init --kind plugin", "init", *P, "--kind", "plugin", "--pack-title", "演示包", "--no-graph")
    pack = PROJ / "pack"
    for rel in ["package.json", "cordis.patch.yml", "index.js", "client.js", "icon.svg", "scripts/smoke.mjs"]:
        check(f"G: 生成 {rel}", (pack / rel).is_file())

    text_suffixes = {".json", ".yml", ".js", ".mjs", ".md", ".svg"}
    leftover = [p.relative_to(pack).as_posix() for p in pack.rglob("*")
                if p.is_file() and p.suffix.lower() in text_suffixes and "{{" in p.read_text(encoding="utf-8")]
    check("G: 骨架无残留占位符", not leftover, ",".join(leftover[:6]))

    pkg = json.loads((pack / "package.json").read_text(encoding="utf-8"))
    cap = pkg["dsh"]["capabilityPack"]
    check("G: 包名/entryKey/openEvent 正确",
          pkg["name"] == "@local/dsh-demo-pack" and cap["entryKey"] == "cap:demo-pack"
          and cap["openEvent"] == "cappacks:open-demo-pack", pkg["name"])
    st = json.loads((PROJ / "docs" / "demo-pack" / "state.json").read_text(encoding="utf-8"))
    # B4（E5）后契约变更：init 默认把三份根级文档纳入 scope，--scope 仍是追加。
    # 这里仍断言 scope **全等**（覆盖未削弱），只是期望值跟着新契约走。
    check("G: scope 默认 pack + 根级文档",
          st.get("scope") == ["pack", "README.md", "ROADMAP.md", "GLOSSARY.md"], str(st.get("scope")))

    node = shutil.which("node")
    if node:
        p = _sp([node, str(pack / "scripts" / "smoke.mjs")], cwd=str(pack),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("G: smoke.mjs 全过", p.returncode == 0 and "0 failed" in (p.stdout or ""),
              ((p.stdout or "") + (p.stderr or ""))[-500:])
        p2 = _sp([node, "--check", str(pack / "index.js")], capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
        check("G: index.js 语法可解析（ESM）", p2.returncode == 0, (p2.stderr or "")[:300])


def suite_h():
    """P2-2：health.json —— 落盘、结构、随阶段更新、--json 可解析。"""
    PROJ = ROOT / "health-proj"
    (PROJ / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    P = ["-p", str(PROJ), "-f", "health"]
    run("H: init", "init", *P, "--scope", "src")
    docs = PROJ / "docs" / "health"

    out, code = capture("health", *P)
    hp = docs / "health.json"
    check("H: health.json 落盘", code == 0 and hp.is_file(), out[-500:])
    data = json.loads(hp.read_text(encoding="utf-8"))
    check("H: schema/phase/gate 字段齐全",
          data.get("schema") == "dsh-flow/health@1" and data.get("phase") == "DESIGN"
          and isinstance(data.get("gate"), dict) and "ok" in data["gate"],
          json.dumps({k: data.get(k) for k in ("schema", "phase")}, ensure_ascii=False))
    check("H: paths 指向真实文件",
          (docs / "state.json").is_file() and Path(data["paths"]["state"]).is_file(),
          data["paths"]["state"])

    jout, jcode = capture("health", *P, "--json")
    try:
        d = json.loads(jout)
        ok = jcode == 0 and d.get("feature") == "health" and d.get("gate", {}).get("to") == "PLAN"
    except Exception as e:  # noqa: BLE001
        ok, d = False, {"error": str(e)}
    check("H: --json 可被脚本解析且门禁目标正确", ok, json.dumps(d, ensure_ascii=False)[:400])

    write_design(docs)
    write_plan(docs)
    run("H: DESIGN -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    run("H: health 重算", "health", *P)
    d2 = json.loads(hp.read_text(encoding="utf-8"))
    check("H: 随阶段更新", d2.get("phase") == "PLAN", str(d2.get("phase")))
    check("H: 门禁目标随阶段变", (d2.get("gate") or {}).get("to") == "EXECUTING",
          json.dumps(d2.get("gate"), ensure_ascii=False))


# ---- I 套「包内 md 引用 CLI 命令」的扫描范围 ----
# docs/<feature>/releases/** 是冻结产物副本（不可改、也不该被当成文档），整目录跳过。
# docs/<feature>/archive/** 是 `drop` 作废件（工具只移动不删除，留给还原用），同理整目录跳过——
# 2026-11-22 的教训：作废候选的证据抄本一旦被当活文档扫，会把「已作废」的东西一直报成红。
# docs/<feature>/evidence/** 是命令原文的输出抄本：**它进入扫描**（整目录跳过等于把这段检测
# 关掉——2026-11-22 前的写法就是这样，evidence 里真写错的命令一律看不见），改用「调用位」
# 判据过滤：抄本里的 `dsh_flow.py` 后面跟的多是数据列或引用，不是真调用。真实误报清单
# （收窄前实测，都会在 I 套里被误当成不存在的子命令）：
#   .../evidence/C001/V1.md:sha256          → `dsh_flow.py` 独占一行、下一行 `  sha256=…`（跨行）
#   .../evidence/C004/V28.md:foreach        → `$ROOT\tools\dsh_flow.py"` 换行后 `foreach (…`（跨行）
#   .../evidence/C001/V6-bundle-check.md:live|mtime / .../C002/V6…:live  → `  live 286e52…` / `mtime=…`
#   .../evidence/C001/V4-suite-x.md:exists  → `  exists=True  size=24`（数据列）
#   .../evidence/P5-md-cmd-ref-guard.md:dropx|ns|tools                   → 反引号里的引用（mention）
# DESIGN.md / planning/* / roles/* / README 等真文档**判据不放宽**：写错命令照样报。
MD_SCAN_SKIP_DIRS = frozenset({"releases", "archive"})
MD_EVIDENCE_DIR = "evidence"

# 显式豁免（DESIGN ② 失败条款：「若 evidence 里历史抄本有真错，逐条登记豁免，而不是恢复整目录跳过」）。
# **精确到「文件 + 捕获词」**：不是目录级豁免，也不是 `nosuch*` 这类通配。两条都来自**不可修改**的
# 历史证据，且都是以**调用形态**写下的夹具命令——词法与真写错完全一致，只能登记、不能靠判据区分。
# 免的是「这两条」，不是「这类」：捕获词改一个字符就不再生效（I 套有反向断言死守这一点）。
MD_CMD_REF_EXEMPT = frozenset({
    # `P5-md-cmd-ref-guard.md:53` 样本表 S2 行（演示「真的把 tools 当子命令」的反向样本夹具）：
    #   | `S2-tools-as-cmd.md` | `& $PY tools/dsh_flow.py tools -p x` | **报 `tools`** |
    ("docs/flow-backup-a/evidence/P5-md-cmd-ref-guard.md", "tools"),
    # `V12.md:49` / `:61` / `:114` 的 here-string 夹具（先把探针 DESIGN 写进临时项目，再跑自测）：
    #   & $PY tools/dsh_flow.py fake-cmd-xyz -p x
    ("docs/flow-hardening/evidence/C002/V12.md", "fake-cmd-xyz"),
})

# 真调用 = 命令名后**行尾结束**，或跟一个 `-x` / `--xxx` 参数；其余形态在抄本里都是数据或引用。
_CMD_USE = re.compile(r"^[ \t]+-{1,2}[A-Za-z]")


def is_md_transcript(p: Path) -> bool:
    """该 md 是否属于「封存副本」（扫描时跳过）。"""
    parts = set(p.parts)
    return "docs" in parts and bool(parts & MD_SCAN_SKIP_DIRS)


def is_md_evidence(p: Path) -> bool:
    """该 md 是否属于 `docs/<feature>/evidence/**` 的命令抄本（进入扫描，按调用位判据过滤）。"""
    parts = set(p.parts)
    return "docs" in parts and MD_EVIDENCE_DIR in parts


def _cmd_ref_in_use_position(txt: str, end: int) -> bool:
    """命中词是否处在「命令调用位」——只看同一行剩下的部分（不跨行）。"""
    rest = txt[end:].split("\n", 1)[0].rstrip()
    return rest == "" or bool(_CMD_USE.match(rest))


def scan_md_cmd_refs(subs, root: Path = PKG, skip_transcripts: bool = True):
    """扫 md 里 `dsh_flow.py <cmd>` 的引用，返回指向不存在子命令的 "相对路径:命令" 列表。

    判据收窄过三次，每次都是「只收窄判据、不关检测」，且都有反向断言盯着：
    ① **不跨行**（本候选 E1-1）：`\\s` 含 `\\n`，于是「`dsh_flow.py` 单独一行、下一行首个小写词」
       被当成子命令（真实误报：flow-hardening/evidence/C001/V1.md:sha256、flow-quality-boost/
       evidence/C004/V28.md:foreach）。改成 `[ \\t]+` 后只有同一行的词才可能被当子命令。
    ② **路径片段**（flow-backup-a）：`& $PY -m py_compile tools/dsh_flow.py tools/selftest.py`
       这类「脚本路径后面还跟另一个路径」的写法，`tools` 后面跟 `/`、`\\`、`.`，是路径第一段。
    ③ **调用位**（本候选 E1-2，只对 evidence 抄本生效）：抄本里的数据列（`mtime=…`/`exists=True`/
       `live=OK`）、校验和列（`live 286e52…`）和反引号里的引用都不报，真调用照报。
    ④ **显式豁免**（`MD_CMD_REF_EXEMPT`）：历史证据里以调用形态写下的夹具命令，精确到「文件 + 捕获词」
       逐条登记（见常量注释）；词改一位即失效，有反向断言盯着。
    判据之外一律不认词表：`dsh_flow.py tools/selftest.py` 不报，但 `dsh_flow.py tools -p x`
    （真的把 tools 当子命令）、`dsh_flow.py nosuchcmd`（真的写错）都仍会被报出。
    """
    bad = []
    ref = re.compile(r"(?:dsh_flow\.py\"?|flow\.py\"?)[ \t]+([a-z][a-z0-9\-]{1,20})")
    for p in Path(root).rglob("*.md"):
        if any(part in {".agents", "node_modules"} for part in p.parts):
            continue
        if skip_transcripts and is_md_transcript(p):
            continue
        evidence = is_md_evidence(p)
        rel = p.relative_to(root).as_posix()
        txt = p.read_text(encoding="utf-8", errors="replace")
        for m in ref.finditer(txt):
            cmd = m.group(1)
            if txt[m.end():m.end() + 1] in ("/", "\\", "."):
                continue                      # 路径片段（如 `dsh_flow.py tools/selftest.py` 里的 tools）
            if evidence and not _cmd_ref_in_use_position(txt, m.end()):
                continue                      # 抄本里的数据列 / 引用，不是调用（见 ③）
            if (rel, cmd) in MD_CMD_REF_EXEMPT:
                continue                      # 已登记的历史抄本夹具，精确到「文件 + 词」（见 ④）
            if cmd not in subs and cmd not in {"py"}:
                bad.append(f"{rel}:{cmd}")
    return bad


def _glossary_rows(text: str) -> "list[str]":
    """取 `GLOSSARY.md` §4 命令表第一列的命令名（去反引号）。

    C002 的教训：标题写「23 个子命令」而 `--help` 是 24 个，`suite_i` 原来只做 `c in gt`
    的子串检查，**测不出**这种漂移（`block` / `unblock` 挤在同一行也能命中）。这里改成
    按表行逐项对照，行数不一致就红。
    """
    parts = text.split("## 4. 命令", 1)
    if len(parts) < 2:
        return []
    body = parts[1].split("\n## ", 1)[0]   # 只取 §4 本节，别把 §8 源码索引表的 `main` 算进来
    rows: "list[str]" = []
    for ln in body.splitlines():
        m = re.match(r"^\|\s*`([a-z][a-z0-9\-]+)`\s*\|", ln)
        if m:
            rows.append(m.group(1))
    return rows


def suite_i():
    """P2-5：文档命令 ↔ --help 对照（防文档漂移）；P2-4 术语表完整性。"""
    help_out = capture("--help")[0] if False else _sp(
        [PY, str(FLOW), "--help"], capture_output=True, text=True,
        encoding="utf-8", errors="replace").stdout
    m = re.search(r"\{([a-z][a-z0-9,\-]+)\}", help_out)
    subs = set(m.group(1).split(",")) if m else set()
    check("I: --help 能列出子命令", bool(subs), help_out[:300])

    skill = (PKG / "skills" / "dsh-multi-role-flow" / "SKILL.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"\$FLOW[ \t]+([a-z][a-z0-9\-]+)", skill))
    documented |= set(re.findall(r"dsh_flow\.py[ \t]+([a-z][a-z0-9\-]+)", skill))
    documented.discard("py")
    missing = sorted(documented - subs)
    check("I: 文档里写的命令都存在", not missing, ",".join(missing))
    undocumented = sorted(subs - documented - {"help"})
    check("I: --help 里的命令都写进 SKILL", not undocumented, ",".join(undocumented))

    # 全包 md 里的 `flow.py <cmd>` 引用也不能指向不存在命令
    # （docs/<feature>/releases/** 是封存副本，按 MD_SCAN_SKIP_DIRS 跳过；evidence/** 仍扫）
    bad_refs = scan_md_cmd_refs(subs)
    check("I: 所有 md 引用的命令都存在", not bad_refs, ",".join(sorted(set(bad_refs))[:6]))

    # 判据收窄不能把检测关掉、也不能变成恒真：在 TEMP 隔离副本上双向压住（①②③ 是本候选 E1-3）
    #
    # C002 / N-06（并发）：探针以前写在 `PKG/_selftest_i_scope`——项目根里的**共享**路径。
    # 两个 selftest 并发时，A 的 `finally: rmtree` 会把 B 刚写好的探针删掉、A 的扫描又会读到
    # B 的 `PLAN-TRAP.md` 里的假命令，于是这些断言间歇性假红（2026-11-22 07:45 双实例实测：
    # 一个 435/0，另一个在 I 套红 3 条）。现在探针落在本进程自己的 `%TEMP%\dsh-flow-selftest-<pid>`
    # 下，并用 `scan_md_cmd_refs(..., root=probe_root)` 只扫这份隔离副本：
    # 真仓库里一个探针文件都不建，两个实例互不可见。
    probe_root = ROOT / "i-scope-probe"
    probe_docs = probe_root / "docs" / "demo"
    shutil.rmtree(probe_root, ignore_errors=True)
    try:
        # ① 跨行/数据列/引用都不误报（E1-1 的 `[ \t]+` + E1-2 的调用位判据）
        transcript = probe_docs / "evidence" / "C001" / "V1.md"
        write(transcript, "# 证据抄本\n\n原文抄本：\n\n```text\ntools/dsh_flow.py\n"
                          "  sha256=0123456789abcdef\n  bytes=118825\n\n"
                          "tools\\dsh_flow.py      live 286e52602fd1db770a2271714b5bddb1\n"
                          "tools/dsh_flow.py      mtime=2026-11-22T01:22:40+08:00\n"
                          "tools/dsh_flow.py      live=OK frozen=OK bytes=242418\n```\n\n"
                          "夹具说明：`dsh_flow.py nosuchcmd` 与 `flow.py dropx` 只是引用，不是调用。\n")
        clean = scan_md_cmd_refs(subs, root=probe_root)
        check("I: ① evidence 抄本里的跨行/数据列/反引号引用都不误报（正则不跨行 + 调用位判据）",
              clean == [], str(clean)[:400])

        # ② 真文档里真写错命令 → 必报（文档判据不放宽）
        write(probe_docs / "DESIGN.md", "# DESIGN\n\n& $PY tools/dsh_flow.py nosuchcmd -p x\n")
        in_doc = sorted(scan_md_cmd_refs(subs, root=probe_root))
        check("I: ② 真文档（DESIGN/planning 等）写错命令仍被报出",
              in_doc == ["docs/demo/DESIGN.md:nosuchcmd"], str(in_doc)[:400])

        # ③ evidence 里真写错命令 → 必报（证明「不再整目录跳过」真的把检测打开了，不是换了种关法）
        write(transcript, "# 证据抄本\n\n```text\n& $PY tools/dsh_flow.py nosuchcmd -p x\n```\n")
        in_evidence = sorted(scan_md_cmd_refs(subs, root=probe_root))
        check("I: ③ evidence 抄本里真写错的命令必被报出（收窄的是判据、不是关检测）",
              in_evidence == ["docs/demo/DESIGN.md:nosuchcmd",
                              "docs/demo/evidence/C001/V1.md:nosuchcmd"], str(in_evidence)[:400])

        # flow-backup-a：`py_compile tools/dsh_flow.py tools/selftest.py` 里的 `tools` 曾被误判成子命令
        # （planner 的 EXECUTION-WORKPLAN 正是这个写法，一跑就红）。判据收窄到「后面跟路径分隔符的算路径」。
        write(probe_docs / "PLAN.md",
              "# plan\n\n| 编译 | `& $PY -m py_compile tools/dsh_flow.py tools/selftest.py` | exit 0 |\n")
        in_path = sorted(scan_md_cmd_refs(subs, root=probe_root))
        check("I: `dsh_flow.py tools/selftest.py` 的 tools 是路径片段、**不**算子命令引用（假阳性已修）",
              "docs/demo/PLAN.md:tools" not in in_path, str(in_path)[:400])
        # 反向守门：同一位置真的把 `tools` 当子命令写，必须仍被报出（收窄的是判据，不是关掉检测）
        write(probe_docs / "PLAN-TRAP.md", "# trap\n\n& $PY tools/dsh_flow.py tools -p x\n")
        in_trap = sorted(scan_md_cmd_refs(subs, root=probe_root))
        check("I: 反向守门：`dsh_flow.py tools`（不带斜杠）仍被报出 —— 只认路径分隔符/调用位、没放宽到词表",
              "docs/demo/PLAN-TRAP.md:tools" in in_trap, str(in_trap)[:400])
        # releases 仍整目录跳过（封存件不可改）；`skip_transcripts=False` 能扫到它，说明该参数没有被架空
        write(probe_root / "docs" / "demo" / "releases" / "C001" / "files" / "R.md",
              "# 封存\n\n& $PY tools/dsh_flow.py nosuchcmd -p x\n")
        frozen = sorted(scan_md_cmd_refs(subs, root=probe_root))
        unscoped = sorted(scan_md_cmd_refs(subs, root=probe_root, skip_transcripts=False))
        check("I: releases 封存副本仍整目录跳过（不改「不可变产物」口径）",
              "docs/demo/releases/C001/files/R.md:nosuchcmd" not in frozen
              and "docs/demo/releases/C001/files/R.md:nosuchcmd" in unscoped,
              f"skipped={frozen} unscoped={unscoped}"[:400])
        # 豁免名单（`MD_CMD_REF_EXEMPT`）双向压测：登记过的那一对不报；同一路径把捕获词改一个字符 → **必报**。
        # 这条死守「豁免不是关检测」：名单精确到「文件 + 词」，任何近亲词/同目录其它文件都不受保护。
        #
        # 文档约定（写给后来写 evidence 的人）：**evidence 里引用夹具命令一律放反引号（mention 形态）**，
        # 例如 `` `dsh_flow.py nosuchcmd` ``；不要写成 `dsh_flow.py nosuchcmd -p x` 这种调用形态——
        # 那种写法与「真写错」在词法上完全无法区分，只能进豁免名单，而名单不该越加越长。
        check("I: 豁免名单恰好两条、且都指向磁盘上真实存在的 evidence 文件（不留空豁免）",
              len(MD_CMD_REF_EXEMPT) == 2
              and all((PKG / rel).is_file() for rel, _ in MD_CMD_REF_EXEMPT),
              repr(sorted(MD_CMD_REF_EXEMPT)))
        for exempt_rel, exempt_cmd in sorted(MD_CMD_REF_EXEMPT):
            mutated = exempt_cmd[:-1] + ("y" if exempt_cmd.endswith("z") else "z")
            probe_file = probe_root.joinpath(*exempt_rel.split("/"))
            write(probe_file, f"# 夹具抄本\n\n& $PY tools/dsh_flow.py {exempt_cmd} -p x\n")
            exempted = scan_md_cmd_refs(subs, root=probe_root)
            write(probe_file, f"# 夹具抄本\n\n& $PY tools/dsh_flow.py {mutated} -p x\n")
            mutated_hits = scan_md_cmd_refs(subs, root=probe_root)
            check(f"I: 豁免「{exempt_rel}:{exempt_cmd}」只豁免该词，改一个字符（{mutated}）仍必报",
                  f"{exempt_rel}:{exempt_cmd}" not in exempted
                  and f"{exempt_rel}:{mutated}" in mutated_hits,
                  f"豁免后={exempted} 改词后={mutated_hits}"[:400])
        # 名单也不是目录级：**同一目录下另一个文件**写同一个词，仍必须被报出
        sibling_rel, sibling_cmd = sorted(MD_CMD_REF_EXEMPT)[0]
        sibling_rel = sibling_rel.rsplit("/", 1)[0] + "/S2-sibling-probe.md"
        write(probe_root.joinpath(*sibling_rel.split("/")),
              f"# 同类样本\n\n& $PY tools/dsh_flow.py {sibling_cmd} -p x\n")
        sibling_hits = scan_md_cmd_refs(subs, root=probe_root)
        check("I: 豁免不是目录级——同目录另一个文件写同一个词仍必报",
              f"{sibling_rel}:{sibling_cmd}" in sibling_hits, str(sibling_hits)[:400])
    finally:
        shutil.rmtree(probe_root, ignore_errors=True)

    # 漂移检查器本身要有效：注入一个不存在的命令，必须能被报出来
    synthetic = sorted((documented | {"fake-command"}) - subs)
    check("I: 漂移检查器自身有效（注入假命令能报出）", synthetic == ["fake-command"], str(synthetic))

    # P2-4 术语表
    g = PKG / "GLOSSARY.md"
    gt = g.read_text(encoding="utf-8") if g.is_file() else ""
    check("I: GLOSSARY 存在且无占位符", bool(gt) and "{{" not in gt, str(g))
    roles = ["Lead", "planner", "executor", "verifier", "inspector"]
    check("I: 术语表覆盖 5 个角色", all(r in gt for r in roles),
          ",".join(r for r in roles if r not in gt))
    check("I: 术语表覆盖全部子命令", all(c in gt for c in subs if c != "help"),
          ",".join(sorted(c for c in subs if c != "help" and c not in gt)))
    # C002：标题计数与表行必须与 --help 逐项对齐（`block` / `unblock` 曾经挤在一行，计数差 1 测不出）
    gloss_rows = _glossary_rows(gt)
    check("I: 术语表 §4 命令表逐行等于 --help 的子命令集（24 行，不是只改标题数字）",
          sorted(gloss_rows) == sorted(subs - {"help"})
          and f"{len(subs - {'help'})} 个子命令" in gt,
          f"rows={len(gloss_rows)} help={len(subs) - 1} "
          f"missing={sorted((subs - {'help'}) - set(gloss_rows))}")


def _bundle_dir(pkg=None):
    """bundle 产物目录：读项目根 `.dsh-flow-bundle-dir` 的一行路径，缺失用 dsh-bundle/。

    与 tools/build_bundle.py 的 bundle_dir() 保持同一份约定（事故善后：dsh-bundle/skills
    在 exFAT 上成了损坏目录项，无法原地重建，改用 dsh-bundle-live/ + 符号链接）。
    """
    base = PKG if pkg is None else pkg
    cfg = base / ".dsh-flow-bundle-dir"
    try:
        if cfg.is_file():
            raw = cfg.read_text(encoding="utf-8").strip()
            if raw:
                p = Path(raw)
                return p if p.is_absolute() else (base / p)
    except OSError:
        pass
    return base / "dsh-bundle"


def suite_j():
    """P2-1：可分发 bundle 的产物完整性（bundle 目录，默认 dsh-bundle/）。

    C002 / N-06：G4 的两条反向探针（改字节 / 塞多余文件）**不再改真 bundle**，而是把真 bundle
    整份复制到 `%TEMP%\\dsh-flow-selftest-<pid>\\bundle-probe\\` 再对副本跑
    `build_bundle.py --check --dir <副本>`。并发的两个 selftest 因此互不干扰
    （旧做法实测会互相踩出间歇性假失败）。
    """
    b = _bundle_dir()
    if not b.is_dir():
        check("J: dsh-bundle 已构建", False, "先运行 tools/build_bundle.py")
        return
    check("J: dsh-bundle 已构建", True)
    check("J: 清单/补丁/技能文件齐全",
          (b / "package.json").is_file() and (b / "cordis.patch.yml").is_file()
          and (b / "skills" / "dsh-multi-role-flow" / "SKILL.md").is_file()
          and (b / "tools" / "dsh_flow.py").is_file())
    pkg = json.loads((b / "package.json").read_text(encoding="utf-8"))
    check("J: package.json 声明 dsh.bundle.patch",
          pkg.get("name") == "dsh-multi-role-flow" and pkg.get("dsh", {}).get("bundle", {}).get("patch") == "./cordis.patch.yml",
          pkg.get("name"))
    patch_text = (b / "cordis.patch.yml").read_text(encoding="utf-8")
    check("J: patch 用独立 provider 且不残留旧环境变量",
          "providerName: multi-role-flow" in patch_text and "baseUrl" in patch_text
          and "DSH_PROFILE_DIR" not in patch_text)
    skill = (b / "skills" / "dsh-multi-role-flow" / "SKILL.md").read_text(encoding="utf-8")
    check("J: 技能无未替换占位符", "{{PACKAGE}}" not in skill, "仍有 {{PACKAGE}}")
    check("J: 技能写明流程包根解析方式", "本技能目录向上两级" in skill)

    node = shutil.which("node")
    if node:
        pass  # 语法检查在 I 套做；这里只验产物
    p = _sp([PY, str(PKG / "tools" / "build_bundle.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("J: build_bundle.py --check 通过", p.returncode == 0,
          ((p.stdout or "") + (p.stderr or ""))[-400:])

    # ---- G4（DESIGN v4 / E19 ④⑥）：版本号 + --check 真的能查出「陈旧」与「多余文件」 ----
    # 1.0.0 的 --check 只查存在性，bundle 陈旧到 tools/dsh_flow.py 少 6 万字节照样通过（坑就是这么埋的）。
    # 2026-11-21（flow-quality-boost Q2）：新增 drive 子命令属 SemVer minor，期望值 1.1.0 → 1.2.0。
    # 2026-11-21（C002）：只修缺陷、不新增子命令 → patch 1.2.0 → 1.2.1（同样只改期望值、判据未变）。
    # 2026-11-21（C003）：同样只修缺陷（.graphifyignore 补 bundle 变体 + 污染正则合并）→ 1.2.1 → 1.2.2。
    # 2026-11-21（C004）：同样只修缺陷（seal 改封每候选台账快照）→ 1.2.2 → 1.2.3（同样只改期望值、判据未变）。
    # 2026-11-21（C007）：同样只修缺陷（文档类候选免 P* 告警 + ROADMAP 去写死状态）→ 1.2.3 → 1.2.4。
    # 2026-11-21（C007 裁决后补）：判据改为「相邻候选变更集」，全量扩展名降级为回退 → 1.2.4 → 1.2.5。
    # 2026-11-21（C008）：只修回归（P 证据 check_id 两种格式都认）→ 1.2.5 → 1.2.6。
    # **改的是期望值、不是判据**：这条断言校验的仍是「版本号只有一个来源」，不删断言、不放宽。
    check("J: G4 bundle package.json 的 version = 1.2.6（VERSION 是唯一版本源）",
          pkg.get("version") == "1.2.6", str(pkg.get("version")))

    def _bcheck(target=None) -> "tuple[int, str]":
        """跑 `build_bundle.py --check`；给了 target 就加 `--dir`（只读检查另一个 bundle 目录）。"""
        cmd = [PY, str(PKG / "tools" / "build_bundle.py"), "--check"]
        if target is not None:
            cmd += ["--dir", str(target)]
        r = _sp(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    # ---- C002 / N-06：反向探针**不再改真 bundle**，改在 %TEMP% 里整份副本上做 ----
    # 旧做法（改真 bundle 一字节 → 断言 exit 1 → 还原）在两个 selftest 并发时会互相踩：
    # A 正要断言「陈旧」时 B 把它还原了（或 A 的还原把 B 的探针提前修好），于是间歇性假失败
    # （2026-11-22 01:23–01:41 实测 4 个实例并发时踩到）。现在靠 build_bundle.py 的
    # `--check --dir <副本>` 只读检查副本，真 bundle 一个字节都不动。
    probe_root = ROOT / "bundle-probe"
    probe = probe_root / "bundle"
    shutil.rmtree(probe_root, ignore_errors=True)
    real_readme = b / "README.md"
    real_readme_sha = (hashlib.sha256(real_readme.read_bytes()).hexdigest()
                       if real_readme.is_file() else "")
    code_real, out_real = _bcheck()          # 不带 --dir：真 bundle，行为必须与旧版一致
    try:
        shutil.copytree(b, probe)
        code_copy, out_copy = _bcheck(probe)
        # T4 的核心等价断言：结论一致，且把打印的 bundle 路径归一化后输出**逐字节相同**
        norm_real = out_real.replace(str(b), "<BUNDLE>")
        norm_copy = out_copy.replace(str(probe), "<BUNDLE>")
        check("J: N-06 --check 与 --check --dir <真bundle副本> 结论一致（输出只差打印的 bundle 路径）",
              code_real == 0 and code_copy == 0 and norm_real == norm_copy,
              f"real(exit={code_real}) copy(exit={code_copy})\n--- real ---\n{out_real[-260:]}"
              f"\n--- copy ---\n{out_copy[-260:]}")
        check("J: N-06 真 bundle 里有 README.md（副本探针的前提）", bool(real_readme_sha))

        # 陈旧探针：只改副本
        orig_readme = (probe / "README.md").read_bytes()
        (probe / "README.md").write_bytes(orig_readme + b"\n<!-- selftest stale probe -->\n")
        code_s, out_s = _bcheck(probe)
        check("J: G4 --check 能查出陈旧文件（副本改一字节 → exit 1 并点名 README.md）",
              code_s == 1 and "README.md" in out_s and "陈旧" in out_s, out_s[-500:])
        (probe / "README.md").write_bytes(orig_readme)        # 还原副本（真 bundle 从未被碰）

        # 多余文件探针：只塞副本
        extra_probe = probe / "__selftest_extra__.txt"
        extra_probe.write_text("selftest extra file\n", encoding="utf-8", newline="\n")
        code_e, out_e = _bcheck(probe)
        check("J: G4 --check 能查出多余文件（副本内塞入未登记文件 → exit 1 并点名）",
              code_e == 1 and "__selftest_extra__.txt" in out_e and "多余" in out_e, out_e[-500:])
        extra_probe.unlink()

        code_ok, out_ok = _bcheck(probe)
        check("J: G4 清理探针后副本的 --check 退出码回到 0（探针自清理，不留脏文件）",
              code_ok == 0 and "__selftest_extra__.txt" not in out_ok, out_ok[-500:])

        # 反向守门：--dir 指到不存在 / 空目录 必须红（不能因为「检查对象换了」就静默通过）
        code_nd, out_nd = _bcheck(probe_root / "no-such-bundle")
        check("J: N-06 反向：--dir 指向不存在的目录 → exit 1 并说明（不是静默通过）",
              code_nd == 1 and "不存在" in out_nd, out_nd[-300:])
        empty = probe_root / "empty-bundle"
        empty.mkdir(parents=True, exist_ok=True)
        code_em, out_em = _bcheck(empty)
        check("J: N-06 反向：--dir 指向空目录 → exit 1 并点名缺 package.json",
              code_em == 1 and "package.json" in out_em, out_em[-300:])

        # ---- C001（bundle-skills-coverage）：skills/ 全目录收录，且 --check 真的覆盖到每个技能 ----
        # 缺口形态：COPY_DIRS 曾不含 skills → bundle 里只有 1 个「生成版」技能，而源仓库有 2 个；
        # 更糟的是「源和 bundle 都不含 → 不比 → exit 0」的盲区，bundle 内 ROADMAP/roles/GLOSSARY
        # 引用的另一个技能文件就成了永远红不了（也永远修不掉）的死引用。
        # 断言一律在 TEMP 副本上做（--dir），**不硬编码技能名**：按源仓库 skills/*/ 枚举，
        # 将来新增技能自动纳入；生成版那份是唯一例外（由 _skill_text() 生成，sha256 必然不同）。
        import importlib.util

        spec_bb = importlib.util.spec_from_file_location(
            "build_bundle_j_probe", PKG / "tools" / "build_bundle.py")
        bb = importlib.util.module_from_spec(spec_bb)
        spec_bb.loader.exec_module(bb)          # 只读：模块顶层只读 `.dsh-flow-bundle-dir`
        copied = bb._copied_files()
        src_skills = sorted(p.relative_to(PKG).as_posix()
                            for p in (PKG / "skills").glob("*/SKILL.md"))
        gen_rel = "skills/dsh-multi-role-flow/SKILL.md"
        plain_rel = [r for r in src_skills if r != gen_rel]

        check("J: P3④ 生成版技能不进 _copied_files() 的 sha256 比对集（那份与源必然不同）",
              gen_rel not in copied and gen_rel in bb.GENERATED,
              f"copied 里命中={gen_rel in copied}；GENERATED 里声明={gen_rel in bb.GENERATED}")
        check("J: P1 源仓库每个技能目录都被纳入比对集（新增技能自动收录，不写死名字）",
              bool(plain_rel) and all(r in copied for r in plain_rel),
              f"源仓库技能 {src_skills}；比对集里的技能项 {sorted(k for k in copied if k.startswith('skills/'))}")

        sp = probe_root / "skills-bundle"
        shutil.copytree(b, sp)
        code_base, out_base = _bcheck(sp)
        clean = code_base == 0
        # 前提门禁：副本本来就红的话，「删一个 → exit 1」会平凡通过，反向断言就成了摆设
        check("J: P3 反向断言的前提：技能齐全的副本 --check exit 0", clean, out_base[-400:])
        if clean and plain_rel:
            # ① 删掉**全部**非生成技能 → 必须 exit 1，且输出逐个点名（不再有「源和 bundle 都不含」的盲区）
            saved = {rel: (sp / rel).read_bytes() for rel in plain_rel}
            for rel in plain_rel:
                (sp / rel).unlink()
            code_d, out_d = _bcheck(sp)
            check("J: P3① 删掉副本里的非生成技能 → --check exit 1 并逐个点名该文件",
                  code_d == 1 and "缺少" in out_d and all(r in out_d for r in plain_rel),
                  out_d[-600:])
            for rel, data in saved.items():
                (sp / rel).parent.mkdir(parents=True, exist_ok=True)
                (sp / rel).write_bytes(data)

            # ② 改一字节 → 报「陈旧」并给两侧大小（源 X B / bundle Y B），不是只说一句不一致
            one = plain_rel[0]
            orig = saved[one]
            (sp / one).write_bytes(orig + b"\n")          # 只多一个字节
            code_s2, out_s2 = _bcheck(sp)
            check("J: P3② 改非生成技能一字节 → 报「陈旧」并给两侧大小",
                  code_s2 == 1 and "陈旧" in out_s2 and one in out_s2
                  and f"源 {len(orig)}B" in out_s2 and f"bundle {len(orig) + 1}B" in out_s2,
                  out_s2[-600:])
            (sp / one).write_bytes(orig)

            # ③ 塞一个源仓库没有的技能目录 → 报「多余文件」并点名
            ghost_rel = "skills/__selftest_ghost__/SKILL.md"
            write(sp / ghost_rel, "ghost skill placed by selftest\n")
            code_g, out_g = _bcheck(sp)
            check("J: P3③ 塞一个源仓库没有的技能文件 → 报「多余文件」并点名",
                  code_g == 1 and "多余" in out_g and ghost_rel in out_g, out_g[-600:])
            shutil.rmtree(sp / "skills" / "__selftest_ghost__", ignore_errors=True)

            # 三条反向断言都不是靠残留脏文件蒙出来的：还原后必须回到 0
            code_f2, out_f2 = _bcheck(sp)
            check("J: P3 技能探针自清理：副本 --check 回到 0（真 bundle 全程未碰）",
                  code_f2 == 0, out_f2[-400:])
    finally:
        shutil.rmtree(probe_root, ignore_errors=True)

    # N-06 的验收核心：整段探针跑完，真 bundle 仍逐字节未变、也没有残留探针文件
    code_after, out_after = _bcheck()
    real_readme_sha2 = (hashlib.sha256(real_readme.read_bytes()).hexdigest()
                        if real_readme.is_file() else "")
    check("J: N-06 探针全程不碰真 bundle（README sha256 不变 / 无残留探针 / --check 仍 0）",
          code_after == 0 and real_readme_sha == real_readme_sha2
          and not (b / "__selftest_extra__.txt").exists(),
          f"README sha {real_readme_sha[:12]} → {real_readme_sha2[:12]}\n{out_after[-300:]}")


def suite_k():
    """P0-11：docs 元数据留痕（D5）——baseline 记录、audit 分类、--docs-only 不动源码基线。"""
    PROJ = ROOT / "docsmeta-proj"
    (PROJ / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    P = ["-p", str(PROJ), "-f", "docsmeta"]
    run("K: init", "init", *P, "--scope", "src")
    docs = PROJ / "docs" / "docsmeta"
    write(docs / "ACCEPTANCE.md", "# 验收\n\n用户结论：待用户试用\n")
    rel = docs / "releases" / "C001"
    rel.mkdir(parents=True)
    write(rel / "verification.json", '{"sealed": 1}\n')

    run("K: baseline", "baseline", *P)
    bl = json.loads((docs / "baseline.json").read_text(encoding="utf-8"))
    check("K: baseline 记录 docs_meta",
          len(((bl.get("docs_meta") or {}).get("files") or {})) >= 3,
          json.dumps((bl.get("docs_meta") or {}).get("files", {}), ensure_ascii=False)[:300])

    write(docs / "ACCEPTANCE.md", "# 验收\n\n用户结论：通过\n")
    out, code = capture("audit", *P)
    check("K: audit 报文档层修改且分类为预期",
          code == 0 and "文档层" in out and "ACCEPTANCE.md" in out and "Lead 回填" in out,
          out[-600:])

    write(rel / "verification.json", '{"sealed": 2}\n')
    out2, _ = capture("audit", *P)
    check("K: 封存件被改会告警", "封存件被改" in out2, out2[-500:])

    write(PROJ / "src" / "a.py", "x = 2\n")
    run("K: baseline --docs-only", "baseline", *P, "--docs-only")
    out3, _ = capture("audit", *P)
    check("K: --docs-only 不改源码基线（仍报 src/a.py 修改）",
          "src/a.py" in out3, out3[-500:])


def suite_l():
    """P0-12：工具缓存目录不纳入基线/审计（.gitnexus / graphify-out 等噪音源）。"""
    PROJ = ROOT / "noise-proj"
    (PROJ / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    for d in (".gitnexus/parse-cache", "graphify-out/cache"):
        (PROJ / "src" / d).mkdir(parents=True)
        write(PROJ / "src" / d / "x.v8", "cache\n")
    write(PROJ / "graphify-out" / "graph.json", "{}\n")
    P = ["-p", str(PROJ), "-f", "noise"]
    run("L: init", "init", *P, "--scope", "src")
    run("L: baseline", "baseline", *P)
    bl = json.loads((PROJ / "docs" / "noise" / "baseline.json").read_text(encoding="utf-8"))
    files = bl.get("files") or {}
    ext = (bl.get("external") or [])
    if ext:
        files = ext[0].get("files") or {}
    check("L: 基线不含工具缓存", not any((".gitnexus" in k or "graphify-out" in k) for k in files),
          ",".join(list(files)[:5]))
    write(PROJ / "src" / ".gitnexus" / "parse-cache" / "y.v8", "cache2\n")
    out, code = capture("audit", *P)
    check("L: 新增缓存不告警", code == 0 and "y.v8" not in out, out[-400:])


def suite_m():
    """P12：drop 作废候选——只移动不删除、从 state 移除、status 不再提示「待重启生效」。"""
    PROJ = ROOT / "drop-proj"
    DEV = ROOT / "drop-proj-dev"
    (PROJ / "src").mkdir(parents=True)
    (DEV / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    write(DEV / "src" / "a.py", "x = 2\n")
    P = ["-p", str(PROJ), "-f", "drop"]
    run("M: init", "init", *P, "--scope", "src")
    run("M: baseline", "baseline", *P)
    docs = PROJ / "docs" / "drop"
    write_design(docs)
    write_plan(docs)
    run("M: DESIGN -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    run("M: PLAN -> EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")

    # 复现真实噪音：候选声明了 requires_restart 又没握手，status 会一直提示它
    run("M: freeze C001 (requires-restart)", "freeze", *P, "--id", "C001", "--from", str(DEV),
        "--scope", "src", "--runtime-kind", "cli", "--runtime-version", "1.0.0",
        "--health-url", "http://127.0.0.1:1/health", "--requires-restart", "--actor", "executor")
    out, code = capture("status", *P)
    check("M: drop 前 status 提示待重启生效", code == 0 and "待重启生效" in out, out[-600:])

    run("M: drop C001", "drop", *P, "--id", "C001", "--reason", "作废：freeze 时 runtime 参数写错")
    archived = sorted((docs / "archive").glob("C001-*/releases/C001/manifest.json"))
    check("M: 只移动不删除（archive 里留着原件）", bool(archived),
          str([p.as_posix() for p in archived])[:400])
    check("M: 原位 releases/C001 已不在", not (docs / "releases" / "C001").exists())
    check("M: archive 里有 DROP-NOTE 记录理由",
          bool(sorted((docs / "archive").glob("C001-*/DROP-NOTE.md"))))
    st = json.loads((docs / "state.json").read_text(encoding="utf-8"))
    check("M: state.candidates 已移除 C001", "C001" not in (st.get("candidates") or {}),
          json.dumps(st.get("candidates") or {}, ensure_ascii=False))
    out, code = capture("status", *P)
    check("M: drop 后 status 不再提示待重启生效", code == 0 and "待重启生效" not in out, out[-600:])

    run("M: drop 未登记候选 -> exit 2", "drop", *P, "--id", "C009", "--reason", "x", expect=2)
    run("M: drop 缺 --reason -> exit 2", "drop", *P, "--id", "C009", expect=2)
    run("M: audit 不因 archive 报新增", "audit", *P)


def suite_n():
    """P13（flow-hardening B1/B2/B4）：标题包含匹配、封存件误报、init 默认 scope。

    B1 双向：`## 三、待用户试用清单` 必须判为「存在」；完全没有该节必须判「缺失」。
    B2 双向：seal 之后 audit 对 verification.json / RELEASE-REPORT.md 告警 0；
             改一个字节必须告警；还原后回到 0（否则就是「修掉误报 = 掩盖真篡改」）。
    B4：新 init 的 state.scope 含 README.md / ROADMAP.md / GLOSSARY.md，且 --scope 是追加。
    """
    # ---- B4：scope 默认纳入根级文档 ----
    PROJ = ROOT / "hardening-proj"
    DEV = ROOT / "hardening-proj-dev"
    (PROJ / "src").mkdir(parents=True)
    (DEV / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    write(DEV / "src" / "a.py", "x = 2\n")
    P = ["-p", str(PROJ), "-f", "hardening"]
    run("N: init --scope src", "init", *P, "--scope", "src", "--no-graph")
    docs = PROJ / "docs" / "hardening"
    st = json.loads((docs / "state.json").read_text(encoding="utf-8"))
    check("N: B4 --scope 追加根级文档（不覆盖用户给的范围）",
          st.get("scope") == ["src", "README.md", "ROADMAP.md", "GLOSSARY.md"],
          json.dumps(st.get("scope"), ensure_ascii=False))

    PROJ2 = ROOT / "hardening-proj2"
    PROJ2.mkdir(parents=True, exist_ok=True)
    run("N: init 无 --scope", "init", "-p", str(PROJ2), "-f", "hardening", "--no-graph")
    st2 = json.loads((PROJ2 / "docs" / "hardening" / "state.json").read_text(encoding="utf-8"))
    check("N: B4 默认 scope 含三份根级文档",
          all(d in (st2.get("scope") or []) for d in ("README.md", "ROADMAP.md", "GLOSSARY.md")),
          json.dumps(st2.get("scope"), ensure_ascii=False))

    # ---- 造一个到 VERIFYING 的候选，供 B1 / B2 用 ----
    run("N: baseline", "baseline", *P)
    write_design(docs)
    write_plan(docs)
    run("N: DESIGN -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    run("N: PLAN -> EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")
    run("N: freeze C001", "freeze", *P, "--id", "C001", "--from", str(DEV), "--scope", "src",
        "--actor", "executor")
    run("N: EXECUTING -> VERIFYING", "advance", *P, "--to", "VERIFYING", "--actor", "executor")

    # ---- B1 正向：带序号的标题必须被识别 ----
    rep = docs / "releases" / "C001" / "RELEASE-REPORT.md"
    rep_ok = ("# report\n\n## 一、变更摘要\n- 修 6 处\n\n"
              "## 三、待用户试用清单\n- 手敲 .\\sync-flow.cmd -Check\n\n"
              "## 证据诚实性声明\n无 mock。\n\n结论：待用户试用\n")
    write(rep, rep_ok)
    out, _ = capture("gate", *P, "--to", "TRIAL")
    check("N: B1 `## 三、待用户试用清单` 判为存在",
          "✓ 发布报告含『待用户试用清单』小节" in out, out[-1200:])

    # ---- B1 反向：完全没有该节必须判缺失 ----
    write(rep, "# report\n\n## 一、变更摘要\n- 无清单\n\n"
               "## 证据诚实性声明\n无 mock。\n\n结论：待用户试用\n")
    out, _ = capture("gate", *P, "--to", "TRIAL")
    check("N: B1 无该节仍判缺失",
          "✗ 发布报告含『待用户试用清单』小节" in out, out[-1200:])

    # ---- B2 正向：baseline 记在报告草稿上，seal 回写后两个封存件都不该告警 ----
    # 这一条同时压住两条分支：verification.json 是「新增」（freeze/seal 生成），
    # RELEASE-REPORT.md 是「修改」但哈希与封存记录一致（seal 回写）。
    write(rep, "# report\n\n## 一、变更摘要\n- 草稿\n\n## 三、待用户试用清单\n- 待补\n\n"
               "## 证据诚实性声明\n无 mock。\n\n结论：待用户试用\n")
    run("N: baseline（报告草稿已在）", "baseline", *P)
    write(rep, rep_ok)
    run("N: seal C001", "seal", *P, "--id", "C001")
    out, code = capture("audit", *P, "--strict")
    check("N: B2 seal 后 audit 对封存件 0 告警（新增 + 封存记录一致）",
          code == 0 and "封存件被改" not in out
          and "freeze/seal 生成（预期）" in out and "封存记录与现状一致" in out,
          out[-1600:])

    # ---- B2 反向：改一个字节必须告警 ----
    write(rep, rep_ok + "\n封存后追加一行\n")
    out, code = capture("audit", *P, "--strict")
    check("N: B2 改封存件一字节必须告警",
          code == 1 and "封存件被改" in out, out[-1600:])

    # ---- B2 还原：哈希与封存记录一致 -> 回到 0 告警 ----
    write(rep, rep_ok)
    out, code = capture("audit", *P, "--strict")
    check("N: B2 还原后回到 0 告警（封存记录与现状一致）",
          code == 0 and "封存记录与现状一致" in out and "封存件被改" not in out,
          out[-1600:])
    run("N: 还原后 verify C001", "verify", *P, "--id", "C001")


def _handoff(project: Path, feature: str, role: str) -> Path:
    """取该角色最新一份交接包。"""
    hs = sorted((project / "docs" / feature / "handoffs").glob(f"HANDOFF-*-{role}.md"))
    return hs[-1]


def _sha_short(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def suite_p():
    """flow-context-boost C001：上下文摘要 / 角色裁剪 / 教训库 / init 建图与 .graphifyignore。

    全部用临时目录；涉及记忆必须走 --memories-dir 指向临时目录，**绝不写真实** ~/.dsh/memories。
    """
    PROJ = ROOT / "ctx-proj"
    (PROJ / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "def f():\n    return 1\n")
    P = ["-p", str(PROJ), "-f", "ctx"]
    # G5（E18）：`next` 默认会按「会话 cwd hash → 项目根 hash → PROVENANCE」去找真实记忆目录。
    # 若操作者恰好在真实工作区根下跑 selftest，cwd hash 会命中真实 KEY.md，本套里「两者都无 →
    # 未提供」这类断言就跟环境耦合、时通时不通（实测过一次 FAIL）。所以除「真实数据」那一条外，
    # 本套所有 `next` 都显式指向一个空记忆目录；`--memories-dir` 是定位链的第一优先，绝对隔离。
    MEMISO = ROOT / "ctx-memories-iso"
    MEMISO.mkdir(parents=True, exist_ok=True)
    PM = P + ["--memories-dir", str(MEMISO)]
    MUST = ("启动自检", "权限边界", "交接物", "回报格式", "常见失败与拒绝条件")

    # ---- B-1c / B-1：init --no-graph 什么都不建；默认建图见后面 graph-proj ----
    run("P: init --no-graph", "init", *P, "--scope", "src", "--no-graph")
    check("P: --no-graph 跳过建图与 .graphifyignore",
          not (PROJ / "graphify-out" / "graph.json").exists() and not (PROJ / ".graphifyignore").exists(),
          "")

    # ---- A：交接包 §1 已知上下文（四子块；数据源全缺也只降级）----
    out, code = capture("next", *PM, "--role", "executor")
    ho = _handoff(PROJ, "ctx", "executor")
    txt = ho.read_text(encoding="utf-8")
    check("P: next 退出码 0（缺图/缺教训库/缺 KEY.md 都不阻断）", code == 0 and ho.is_file(), out[-600:])
    check("P: 交接包含 §1 已知上下文与四个子块",
          "## 1. 已知上下文（自动摘要）" in txt
          and all(h in txt for h in ("### 图谱摘要", "### 上一候选已报的坑", "### 同类坑", "### 项目关键事实")),
          txt[:900])
    check("P: 缺图写「未建图」并给补法", "未建图" in txt and "graphify extract" in txt, txt[:1200])
    check("P: 缺教训库写「教训库未建」", "教训库未建" in txt, txt[:1200])
    check("P: 无候选写「尚无候选」", "尚无候选" in txt, txt[:1200])
    # G5 之后语义变了：KEY.md 缺失**不再**直接等于「未提供」，要先看 MEMORY.md 兜底；
    # 只有「定位到的目录里两个文件都没有」才写「未提供」。这条断言随之收紧（不是删除）。
    check("P: 记忆目录里 KEY.md 与 MEMORY.md 都无 → 才写「未提供」并给补法（退出码 0）",
          code == 0 and "KEY.md：未提供" in txt and "--key-note" in txt, txt[:1600])

    # ---- D-1 / D-2：角色要点按阶段裁剪 + 五节必保 + 交接包 ≤12000 字节 ----
    check("P: 角色要点按阶段裁剪（含完整说明书指针）",
          "## 2. 角色要点（按阶段裁剪）" in txt and "完整说明书：`roles/02-executor.md`" in txt, txt[:1200])
    check("P: 五个必保小节齐全", all(m in txt for m in MUST),
          ",".join(m for m in MUST if m not in txt))
    check("P: 裁剪后不再内嵌角色全文（§2 体积 ≤ 原全文一半）",
          len(txt.split("## 3. 本次任务")[0].encode("utf-8"))
          <= len((PKG / "roles" / "02-executor.md").read_text(encoding="utf-8").encode("utf-8")),
          "§0-§2 与角色全文对比")
    for role in ("planner", "verifier", "lead"):
        capture("next", *PM, "--role", role)
        f = _handoff(PROJ, "ctx", role)
        t = f.read_text(encoding="utf-8")
        check(f"P: {role} 交接包 ≤12000 字节且五节必保齐全",
              f.stat().st_size <= 12000 and all(m in t for m in MUST),
              f"bytes={f.stat().st_size}")

    # 回归（C001 实测缺陷）：验证线程写入 RELEASE-REPORT 后「上一候选已报的坑」子块会变长；
    # 交接包上限是 12000 **字节**，中文一字 3 字节，所以 §1 的预算必须双算（字符 + 字节），
    # 否则只按 --max-context-chars 的字符预算收，会撑破字节上限（实测曾到 14987 字节）。
    rel = PROJ / "docs" / "ctx" / "releases" / "C001"
    write(rel / "RELEASE-REPORT.md",
          "# report\n\n## 已知问题\n"
          + "\n".join(f"- 已知问题第 {i} 条：一段用于撑大上下文的较长描述文字，带细节与出处。" for i in range(20))
          + "\n\n## 给执行线程的信息\n"
          + "\n".join(f"- 给执行线程第 {i} 条：同样是一段较长的描述文字，用于压测裁剪。" for i in range(20))
          + "\n\n结论：待用户试用\n")
    st = json.loads((PROJ / "docs" / "ctx" / "state.json").read_text(encoding="utf-8"))
    st["current_candidate"] = "C001"
    (PROJ / "docs" / "ctx" / "state.json").write_text(
        json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for role in ("executor", "planner", "verifier", "lead", "inspector"):
        capture("next", *PM, "--role", role)
        f = _handoff(PROJ, "ctx", role)
        t = f.read_text(encoding="utf-8")
        check(f"P: 有上一候选报告时 {role} 交接包仍 ≤12000 字节",
              f.stat().st_size <= 12000 and "### 上一候选已报的坑" in t
              and all(m in t for m in MUST), f"bytes={f.stat().st_size}")

    # ---- A-3 / A-4：--key-note 叠加 与 KEY.md 直读（隔离记忆目录）----
    MEM = ROOT / "ctx-memories"
    pid = _sha_short(str(PROJ))
    write(MEM / "projects" / pid / "KEY.md",
          "[id:abc12345] [2026-11-20 00:40] probe-key-fact-7\n不加前缀的普通正文行\n")
    out, code = capture("next", *P, "--role", "executor", "--memories-dir", str(MEM),
                        "--key-note", "probe-keynote-9")
    txt2 = _handoff(PROJ, "ctx", "executor").read_text(encoding="utf-8")
    check("P: KEY.md 直读命中（去前缀、标来源路径）",
          code == 0 and "probe-key-fact-7" in txt2 and "[id:abc12345]" not in txt2
          and "[2026-11-20 00:40]" not in txt2
          and (MEM / "projects" / pid / "KEY.md").as_posix() in txt2, txt2[:2000])
    check("P: --key-note 叠加进「项目关键事实」", "probe-keynote-9" in txt2, txt2[:2000])
    # C002：`--key-note` 改成 action="append"，多个 note 都要拼进去（单次传仍兼容，见上一条）
    out_m, code_m = capture("next", *P, "--role", "executor",
                            "--key-note", "note-multi-A", "--key-note", "note-multi-B")
    txt_m = _handoff(PROJ, "ctx", "executor").read_text(encoding="utf-8")
    check("P: --key-note 可多次（append），两个 note 都进交接包且带 #1/#2 序号",
          code_m == 0 and "note-multi-A" in txt_m and "note-multi-B" in txt_m
          and "--key-note#1" in txt_m and "--key-note#2" in txt_m, txt_m[:2200])
    check("P: 只传一个 --key-note 时不加序号（向后兼容旧输出形态）",
          "--key-note（来源：命令行参数）" in txt2 and "--key-note#" not in txt2, txt2[:1500])
    run("P: --key-note 指向不存在文件 -> 退出码 2", "next", *P, "--role", "executor",
        "--key-note", "@" + str(ROOT / "no-such-note.md"), expect=2)
    run("P: 多个 --key-note 里任一 @文件不存在 -> 退出码 2（逐个校验）", "next", *P,
        "--role", "executor", "--key-note", "ok-note",
        "--key-note", "@" + str(ROOT / "no-such-note-2.md"), expect=2)
    out, code = capture("next", *PM, "--role", "executor", "--no-context")
    t3 = _handoff(PROJ, "ctx", "executor").read_text(encoding="utf-8")
    check("P: --no-context 关闭整节但保留编号与退出码 0",
          code == 0 and "## 1. 已知上下文（自动摘要）" in t3 and "--no-context" in t3
          and "### 图谱摘要" not in t3, t3[:800])

    # ---- C：教训库闭环（add → list → next「同类坑」；缺参退出码 2；不写 state.json）----
    st_path = PROJ / "docs" / "ctx" / "state.json"
    before = hashlib.sha256(st_path.read_bytes()).hexdigest()
    out, code = capture("lesson", "-p", str(PROJ), "add", "--symptom", "probe-symptom-X",
                        "--cause", "probe-cause", "--fix", "probe-fix", "--tags", "executor")
    after = hashlib.sha256(st_path.read_bytes()).hexdigest()
    check("P: lesson add 自动编号并写入 ops/lessons.md",
          code == 0 and "L001" in out and "probe-symptom-X" in
          (PROJ / "ops" / "lessons.md").read_text(encoding="utf-8"), out[-500:])
    check("P: lesson 不写 state.json", before == after, f"{before[:12]} vs {after[:12]}")
    out, code = capture("lesson", "-p", str(PROJ), "list", "--role", "executor")
    check("P: lesson list --role executor 命中", code == 0 and "probe-symptom-X" in out, out[-600:])
    run("P: lesson add 缺 --symptom -> 退出码 2", "lesson", "-p", str(PROJ), "add",
        "--cause", "C", expect=2)
    capture("next", *PM, "--role", "executor")
    t4 = _handoff(PROJ, "ctx", "executor").read_text(encoding="utf-8")
    check("P: next「同类坑」带出该条（症状 → 做法（L001））",
          "probe-symptom-X" in t4 and "L001" in t4 and "### 同类坑" in t4, t4[:1600])
    # 取序（C001 的 V7 缺陷）：必须带出**最新**的教训，不能因为库里该角色已命中 3 条
    # 就把新坑永远挤在门外。这里再加 3 条 executor 命中，断言最新 3 条在、最早的 L001 被挤出。
    for i in range(3):
        capture("lesson", "-p", str(PROJ), "add", "--symptom", f"probe-symptom-new-{i}",
                "--cause", "probe-cause", "--fix", f"probe-fix-{i}", "--tags", "executor")
    capture("next", *PM, "--role", "executor")
    t5 = _handoff(PROJ, "ctx", "executor").read_text(encoding="utf-8")
    block = t5.split("### 同类坑")[1].split("###")[0] if "### 同类坑" in t5 else ""
    check("P: 「同类坑」取最新 N 条（刚 add 的坑必带出来）",
          all(f"probe-symptom-new-{i}" in block for i in range(3)), block[:1200])
    check("P: 教训条数上限不变（最早一条被挤出，不是无限累加）",
          "probe-symptom-X" not in block and block.count("（L00") <= 3, block[:1200])
    # 角色不匹配的教训不注入；无效行不静默吞
    with (PROJ / "ops" / "lessons.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write("| L002 | 坏行缺日期 | x | y | executor |\n")
    out, code = capture("lesson", "-p", str(PROJ), "list")
    check("P: 无效行标「⚠ 行格式无效」（不猜、不静默吞）",
          code == 0 and "行格式无效" in out, out[-600:])
    run("P: 有无效行时 next 仍退出码 0", "next", *PM, "--role", "executor")

    # ---- B-1b / E14：init 默认建图 + .graphifyignore（幂等 / 保留自定义行 / 只含真实源码）----
    GP = ROOT / "graph-proj"
    (GP / "src").mkdir(parents=True)
    write(GP / "src" / "a.py", "def a():\n    return 1\n")
    write(GP / "docs" / "demo" / "releases" / "C001" / "files" / "src" / "dup.py",
          "def dup():\n    return 2\n")
    run("P: init 默认建图（fixture）", "init", "-p", str(GP), "-f", "g", "--scope", "src")
    gp_json = GP / "graphify-out" / "graph.json"
    check("P: 默认建图后 graph.json 存在", gp_json.is_file(), "")
    ign = GP / ".graphifyignore"
    check("P: .graphifyignore 有首行注释 + 9 行排除（C003 起含两个 bundle 变体）",
          ign.is_file() and ign.read_text(encoding="utf-8").startswith("# 由 dsh_flow.py init 维护")
          and all(ln in ign.read_text(encoding="utf-8") for ln in
                  ("docs/**/releases/", "docs/**/archive/", "docs/**/files/",
                   "docs/**/evidence/", "examples/", "dsh-bundle/",
                   "dsh-bundle-live/", "dsh-bundle-dist/", "graphify-out/")), "")
    h1 = hashlib.sha256(ign.read_bytes()).hexdigest()
    run("P: 第二次 init（已有图走 update）", "init", "-p", str(GP), "-f", "g", "--scope", "src", "--force")
    h2 = hashlib.sha256(ign.read_bytes()).hexdigest()
    check("P: .graphifyignore 幂等（连跑两次字节一致）", h1 == h2, f"{h1[:12]} vs {h2[:12]}")
    try:
        graph = json.loads(gp_json.read_text(encoding="utf-8"))
        nodes = graph.get("nodes") or []
        bad = [n.get("source_file") for n in nodes
               if re.search(r"(^|/)(releases|archive|dsh-bundle)(/|$)",
                            str(n.get("source_file") or "").replace("\\", "/"))]
        check("P: 图只含真实源码（封存副本被 .graphifyignore 排除）", nodes and not bad, str(bad)[:300])
    except Exception as e:  # noqa: BLE001
        check("P: 图只含真实源码（封存副本被 .graphifyignore 排除）", False, str(e))
    # 预置只含自定义行的 .graphifyignore：init 只追加缺行、不删用户行
    CP = ROOT / "ignore-proj"
    (CP / "src").mkdir(parents=True)
    write(CP / "src" / "a.py", "def a():\n    return 1\n")
    write(CP / ".graphifyignore", "*.tmp\n")
    run("P: 已存在自定义行时 init 仍成功", "init", "-p", str(CP), "-f", "g", "--scope", "src")
    ct = (CP / ".graphifyignore").read_text(encoding="utf-8")
    check("P: 自定义行 *.tmp 保留 + 缺失排除行被补上",
          "*.tmp" in ct and "docs/**/releases/" in ct and ct.splitlines()[0] == "*.tmp", ct[:400])

    # ---- G1（DESIGN v2 / E15）：`.graphifyignore` 进 state.scope，且绝不动 baseline.roots ----
    G1 = ROOT / "g1-proj"
    (G1 / "src").mkdir(parents=True)
    write(G1 / "src" / "a.py", "x = 1\n")
    P1 = ["-p", str(G1), "-f", "g1"]
    run("P: G1 init（建图开启）", "init", *P1, "--scope", "src")
    st1 = json.loads((G1 / "docs" / "g1" / "state.json").read_text(encoding="utf-8"))
    check("P: G1 init 后 scope 含 .graphifyignore 且只出现一次",
          st1.get("scope", []).count(".graphifyignore") == 1,
          json.dumps(st1.get("scope"), ensure_ascii=False))
    run("P: G1 第二次 init（幂等）", "init", *P1, "--scope", "src", "--force")
    st1b = json.loads((G1 / "docs" / "g1" / "state.json").read_text(encoding="utf-8"))
    check("P: G1 连跑两次 scope 里仍只有 1 条",
          st1b.get("scope", []).count(".graphifyignore") == 1,
          json.dumps(st1b.get("scope"), ensure_ascii=False))

    G1B = ROOT / "g1b-proj"
    (G1B / "src").mkdir(parents=True)
    write(G1B / "src" / "a.py", "x = 1\n")
    P1B = ["-p", str(G1B), "-f", "g1b"]
    run("P: G1 init --no-graph（原无该文件）", "init", *P1B, "--scope", "src", "--no-graph")
    st1c = json.loads((G1B / "docs" / "g1b" / "state.json").read_text(encoding="utf-8"))
    check("P: G1 --no-graph 且原本没有 → 不建文件、scope 不含它",
          not (G1B / ".graphifyignore").exists()
          and ".graphifyignore" not in (st1c.get("scope") or []),
          json.dumps(st1c.get("scope"), ensure_ascii=False))

    # 存量补正：先 baseline（roots 必须是 ["."]），再补一个真实存在的文件进 scope
    run("P: G1 存量 fixture baseline", "baseline", *P1B)
    write(G1B / ".graphifyignore", "*.tmp\n")
    out, code = capture("scope", *P1B, "--add", ".graphifyignore")
    st1d = json.loads((G1B / "docs" / "g1b" / "state.json").read_text(encoding="utf-8"))
    bl1 = json.loads((G1B / "docs" / "g1b" / "baseline.json").read_text(encoding="utf-8"))
    check("P: G1 scope --add 追加成功且不动 baseline.roots",
          code == 0 and st1d.get("scope", []).count(".graphifyignore") == 1 and bl1.get("roots") == ["."],
          f"scope={st1d.get('scope')} roots={bl1.get('roots')}")
    capture("scope", *P1B, "--add", ".graphifyignore")
    st1e = json.loads((G1B / "docs" / "g1b" / "state.json").read_text(encoding="utf-8"))
    check("P: G1 scope --add 重复添加幂等（仍 1 条）",
          st1e.get("scope", []).count(".graphifyignore") == 1,
          json.dumps(st1e.get("scope"), ensure_ascii=False))
    bad_codes = [capture("scope", *P1B, "--add", b)[1]
                 for b in ("../escape", str(G1B / "abs"), "src/*.py", "not-exist.dir")]
    check("P: G1 scope --add 四类非法参数均退出码 2（含 --add 缺省）",
          bad_codes == [2, 2, 2, 2] and capture("scope", *P1B)[1] == 2, str(bad_codes))
    out, _ = capture("audit", *P1B)
    check("P: G1 audit 不再把 .graphifyignore 记为「不在声明写范围」",
          not re.search(r"graphifyignore.*不在声明写范围", out), out[-800:])

    # ---- G2（DESIGN v2 / E16）：freeze --reused 落盘 + 读侧可见 + 理由质量门 ----
    PA = ["-p", str(ROOT / "proj"), "-f", "demo"]       # suite_a 的 fixture（已到 DONE，候选 C001）
    DEVA = ROOT / "proj-dev"
    run("P: G2 freeze --reused", "freeze", *PA, "--id", "C002", "--from", str(DEVA), "--scope", "src",
        "--reused", "V4:roles/*.md 与 ops/code-graph.md 逐字节未变")
    m2 = json.loads((ROOT / "proj" / "docs" / "demo" / "releases" / "C002" / "manifest.json")
                    .read_text(encoding="utf-8"))
    check("P: G2 manifest.checks.reused 落盘（check/reason 逐字一致）",
          m2.get("checks", {}).get("reused") ==
          [{"check": "V4", "reason": "roles/*.md 与 ops/code-graph.md 逐字节未变"}],
          json.dumps(m2.get("checks"), ensure_ascii=False)[:400])
    out, code = capture("verify", *PA, "--id", "C002")
    check("P: G2 verify 打印 reused N 条（读侧可见）",
          code == 0 and "reused 1 条" in out, out[-600:])
    run("P: G2 health 落盘", "health", *PA, "--no-gate")
    hp = json.loads((ROOT / "proj" / "docs" / "demo" / "health.json").read_text(encoding="utf-8"))
    check("P: G2 health.json 的 candidate.checks.reused 读得到",
          len((hp.get("candidate") or {}).get("checks", {}).get("reused") or []) == 1,
          json.dumps((hp.get("candidate") or {}).get("checks"), ensure_ascii=False)[:400])
    bad2 = [capture("freeze", *PA, "--id", "C003", "--from", str(DEVA), "--scope", "src", "--reused", r)[1]
            for r in ("V4:", "V4:123", "V4", "V4:，，，", "V4:看起来没问题吧")]
    check("P: G2 坏理由五例均退出码 2（空/纯数字/无冒号/纯标点/无线索）",
          bad2 == [2, 2, 2, 2, 2], str(bad2))
    out, code = capture("freeze", *PA, "--id", "C003", "--from", str(DEVA), "--scope", "src",
                        "--reused", "V4:C001 已通过，直接继承")
    check("P: G2 跳继承措辞 exit 0 且打 ⚠（不阻断）",
          code == 0 and "⚠ 这不是复用，是候选间跳跃继承，必须重跑" in out, out[-500:])
    run("P: G2 两条 --reused 保序", "freeze", *PA, "--id", "C004", "--from", str(DEVA), "--scope", "src",
        "--reused", "V4:a.md 逐字节未变", "--reused", "V7:ops/lessons.md 未变")
    m4 = json.loads((ROOT / "proj" / "docs" / "demo" / "releases" / "C004" / "manifest.json")
                    .read_text(encoding="utf-8"))
    check("P: G2 两条 --reused 保持命令行顺序",
          [r.get("check") for r in (m4.get("checks") or {}).get("reused") or []] == ["V4", "V7"],
          json.dumps((m4.get("checks") or {}).get("reused"), ensure_ascii=False)[:300])
    # G7（DESIGN v4 / E21 ④）：freeze 落盘后回显「检查号 → 理由」，让 reused 编号笔误当场可见
    # （C005 的 reused[2] 把 scope 逻辑记成 V11，实为 V15——编号语义无法机判，只能回显 + 人工核对）
    _g7_reason = "cmd_scope 与 cmd_init 的 .graphifyignore → state.scope 逻辑逐字节未变"
    out5, code5 = capture("freeze", *PA, "--id", "C005", "--from", str(DEVA), "--scope", "src",
                          "--reused", f"V15:{_g7_reason}")
    check("P: G7 freeze --reused 回显「reused: <检查号> → <理由>」一行",
          code5 == 0 and f"reused: V15 → {_g7_reason}" in out5, out5[-600:])

    # ---- G3（DESIGN v2 / E17）：五角色必保五节全 ✅，且 roles 只新增不改既有 ----
    lead_txt = (PKG / "roles" / "00-lead.md").read_text(encoding="utf-8")
    insp_txt = (PKG / "roles" / "04-inspector.md").read_text(encoding="utf-8")
    check("P: G3 roles 新增锚点小节（lead §9 交接物 / inspector §8 常见失败）",
          "## 9. 交接物" in lead_txt and "## 8 常见失败与拒绝条件" in insp_txt, "")
    check("P: G3 roles 既有小节标题仍在（只新增、不改既有）",
          "## 8. 收尾" in lead_txt and "## 7 证据要求" in insp_txt, "")
    flow_src = FLOW.read_text(encoding="utf-8")
    # C004（V17 缺陷②③）：两条偏松映射已撤回——否则 `## 6 自停阈值` 因为排在 `## 8` 之前，
    # 关键字「首个命中」永远选中旧节，新补的标准标题节等于从不生效。
    _syn = re.search(r"ROLE_MUST_KEEP_SYNONYMS = \{(.*?)\n\}", flow_src, re.S)
    syn_block = _syn.group(1) if _syn else ""
    check("P: G3 同义词表只认 DESIGN 列出的映射（自停阈值/必须让用户介入 两条已撤回）",
          "ROLE_MUST_KEEP_SYNONYMS" in flow_src and "隔离纪律" in syn_block
          and "产出物" in syn_block and "自停阈值" not in syn_block
          and "必须让用户介入" not in syn_block, syn_block[:400])

    # C004（V17 缺陷①）：roles 与交接包都不许有控制字符（会被原样喂进子智能体 prompt）
    def _ctrl_bytes(path: Path):
        b = path.read_bytes()
        return [(i, hex(c)) for i, c in enumerate(b)
                if c < 9 or c in (11, 12) or 14 <= c <= 31]

    role_bad = {r.name: _ctrl_bytes(r) for r in (PKG / "roles").glob("*.md")}
    check("P: G3 五份 roles/*.md 无控制字符（0x00-0x08/0x0b/0x0c/0x0e-0x1f）",
          all(not v for v in role_bad.values()),
          str({k: v[:3] for k, v in role_bad.items() if v})[:400])
    check("P: G3 lead/inspector 交接包无控制字符（不会被带进 subagent prompt）",
          not _ctrl_bytes(_handoff(PROJ, "ctx", "lead"))
          and not _ctrl_bytes(_handoff(PROJ, "ctx", "inspector")),
          f"lead={_ctrl_bytes(_handoff(PROJ, 'ctx', 'lead'))[:3]} "
          f"insp={_ctrl_bytes(_handoff(PROJ, 'ctx', 'inspector'))[:3]}")

    for role in ("lead", "planner", "executor", "verifier", "inspector"):
        capture("next", *PM, "--role", role)
        f = _handoff(PROJ, "ctx", role)
        line = ""
        for ln in f.read_text(encoding="utf-8").splitlines():
            if "必保五节" in ln:
                line = ln
                break
        check(f"P: G3 {role} 交接包「必保五节」5 个 ✅ / 0 个 ➖，且 ≤12000 字节",
              line.count("✅") == 5 and "➖" not in line and f.stat().st_size <= 12000,
              f"bytes={f.stat().st_size} {line[:120]}")

    # 标准标题必须真的被选中并内嵌正文（不是只落进「其余纪律见…」指针）
    lead_handoff = _handoff(PROJ, "ctx", "lead").read_text(encoding="utf-8")
    insp_handoff = _handoff(PROJ, "ctx", "inspector").read_text(encoding="utf-8")
    check("P: G3 lead §9/§10 正文内嵌（交接物 + 常见失败与拒绝条件 各自成节）",
          "### 9. 交接物" in lead_handoff and "### 10. 常见失败与拒绝条件" in lead_handoff,
          lead_handoff[lead_handoff.find("## 2. 角色要点"):][:600])
    check("P: G3 inspector §8 正文内嵌（自停阈值不再顶替常见失败节）",
          "### 8 常见失败与拒绝条件" in insp_handoff
          and "其余纪律见 `roles/04-inspector.md`" in insp_handoff,
          insp_handoff[insp_handoff.find("## 2. 角色要点"):][:600])

    # ---- G5（DESIGN v3 / E18）：记忆真读——MEMORY 兜底 / 尾部取序 / 三候选合并 / 真实数据 ----
    # 被验证的实现契约（tools/dsh_flow.py 的 _memory_project_dirs / _ctx_key_facts）：
    #   定位链：--memories-dir/env → 会话 cwd hash（首选）→ 项目根 hash → PROVENANCE.displayName 唯一匹配
    #   文件链：KEY.md（尾部 ≤2 条 / ≤1500 字符）→ 无则 MEMORY.md 尾部 2 条 / 400 字符 → 都没有「未提供」
    # 除「真实数据」那一条外，fixture 全在临时目录；真实记忆目录只读。
    gpid = _sha_short(str(PROJ))

    # ① KEY.md 缺失、只有 MEMORY.md → 读尾部并标成「项目最近进展」，不许混进关键事实
    GM = ROOT / "ctx-mem-g5"
    write(GM / "projects" / gpid / "MEMORY.md",
          "[id:aaa11111] [2026-11-20 01:00] mem-head-probe-1\n§\n"
          "[id:bbb22222] [2026-11-20 02:00] mem-mid-probe-2\n§\n"
          "[id:ccc33333] [2026-11-20 03:00] mem-tail-probe-9\n")
    _, code_mem = capture("next", *P, "--role", "executor", "--memories-dir", str(GM))
    t_mem = _handoff(PROJ, "ctx", "executor").read_text(encoding="utf-8")
    key_blk = t_mem.split("### 项目关键事实")[1] if "### 项目关键事实" in t_mem else ""
    key_blk = key_blk.split("\n### ")[0]
    check("P: G5 无 KEY.md 但有 MEMORY.md → 读尾部并标「项目最近进展（来自 MEMORY.md 尾部）」",
          code_mem == 0 and "mem-tail-probe-9" in t_mem
          and "项目最近进展（来自 MEMORY.md 尾部）" in t_mem
          and (GM / "projects" / gpid / "MEMORY.md").as_posix() in t_mem, t_mem[:2000])
    check("P: G5 MEMORY 兜底只取尾部 2 条（最早一条不出现）且 [id:…]/[时间] 前缀已剥",
          "mem-mid-probe-2" in t_mem and "mem-head-probe-1" not in t_mem
          and "[id:" not in key_blk
          and not re.search(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}", key_blk)
          and "只显示最新 2 条" in key_blk, key_blk[:1200])
    check("P: G5 MEMORY 尾部不当成「项目关键事实」（只有缩进的「项目最近进展」行，无独立事实行）",
          not any(ln.startswith("- mem-tail-probe-9") for ln in t_mem.splitlines())
          and any(ln.strip().startswith("- mem-tail-probe-9") for ln in t_mem.splitlines()),
          key_blk[:1200])

    # ② 尾部取序（L005 同型坑）：KEY.md 里**新写入**的条目必须出现，早期条目不因满额被挡
    GK = ROOT / "ctx-mem-g5-keys"
    pad = "旧条目填充内容" * 16
    olds = "\n".join(f"[id:k{i:07d}] [2026-11-20 0{i}:00] key-old-probe-{i} {pad}"
                     for i in range(1, 6))
    write(GK / "projects" / gpid / "KEY.md",
          olds + "\n[id:ktaillast] [2026-11-20 09:00] key-tail-probe-9\n")
    capture("next", *P, "--role", "executor", "--memories-dir", str(GK))
    t_key = _handoff(PROJ, "ctx", "executor").read_text(encoding="utf-8")
    kb = t_key.split("### 项目关键事实")[1].split("\n### ")[0] if "### 项目关键事实" in t_key else ""
    check("P: G5 KEY.md 从尾部向前累计（新写入的条目必须出现，最早的条目不占满额）",
          "key-tail-probe-9" in kb and "key-old-probe-5" in kb
          and "key-old-probe-1" not in kb and "只显示最新 2 条" in kb,
          kb[:1200])

    # ③ 三候选全部尝试、命中即合并、各标来源（同一文件不重复出现）
    MM = ROOT / "ctx-mem-multi"
    CWDX = ROOT / "ctx-cwd"
    CWDX.mkdir(parents=True, exist_ok=True)
    write(MM / "projects" / _sha_short(str(CWDX)) / "KEY.md", "cwd-dir-probe-4\n")
    write(MM / "projects" / gpid / "KEY.md", "proj-dir-probe-5\n")
    capture("next", *P, "--role", "executor", "--memories-dir", str(MM), cwd=CWDX)
    t_multi = _handoff(PROJ, "ctx", "executor").read_text(encoding="utf-8")
    check("P: G5 会话 cwd hash 与项目根 hash 都命中 → 合并输出且各标来源绝对路径",
          "cwd-dir-probe-4" in t_multi and "proj-dir-probe-5" in t_multi
          and (MM / "projects" / _sha_short(str(CWDX)) / "KEY.md").as_posix() in t_multi
          and (MM / "projects" / gpid / "KEY.md").as_posix() in t_multi,
          t_multi[t_multi.find("### 项目关键事实"):][:900])

    # ④ 真实数据（不是 fixture）：memory-evolve 按**会话 cwd**写记忆，本机就是工作区根 PKG.parent。
    #    不传 --memories-dir，让定位链自然命中；真实记忆目录只读（前后文件数一致）。
    #    G6（DESIGN v4 / E20）：这条断言依赖本机真实文件 → 换机器/清过记忆必红（时通时不通）。
    #    改成「有真实数据则真的断言、无则 skip 并打印原因」：skip 不计入通过数，也不许掩盖回归。
    REALP = ROOT / "ctx-realmem"
    (REALP / "src").mkdir(parents=True, exist_ok=True)
    write(REALP / "src" / "g.py", "def g():\n    return 7\n")
    capture("init", "-p", str(REALP), "-f", "r", "--scope", "src", "--no-graph")
    ws = PKG.parent
    # 定位口径必须与 dsh_flow.py 的 _memory_project_dirs 一致：--memories-dir（此处未传）→
    # 三个环境变量 → 默认 %USERPROFILE%\.dsh\memories，否则「模拟换机」时探针与实现会各看一处。
    _mem_env = next((os.environ[k] for k in
                     ("DSH_FLOW_MEMORIES_DIR", "DSH_MEMORY_DIR", "DSH_MEMORIES_DIR")
                     if os.environ.get(k)), "")
    real_mem = (Path(_mem_env) if _mem_env
                else Path(os.environ.get("USERPROFILE") or str(Path.home())) / ".dsh" / "memories")
    real_key = real_mem / "projects" / _sha_short(str(ws)) / "KEY.md"

    def _real_facts(path: Path) -> list:
        rows = []
        for ln in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            s = ln.strip()
            if not s or s.startswith("#") or s == "§":
                continue
            s = re.sub(r"^\[id:[0-9A-Za-z_\-]{3,}\]\s*", "", s)
            s = re.sub(r"^\[\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?\]\s*", "", s).strip()
            if s:
                rows.append(s)
        return rows

    def _mem_files(root: Path) -> int:
        return len([p for p in root.rglob("*") if p.is_file()]) if root.is_dir() else 0

    real_facts = _real_facts(real_key) if real_key.is_file() else []
    cnt_before = _mem_files(real_mem / "projects")
    _, code_real = capture("next", "-p", str(REALP), "-f", "r", "--role", "executor", cwd=ws)
    t_real = _handoff(REALP, "r", "executor").read_text(encoding="utf-8")
    cnt_after = _mem_files(real_mem / "projects")
    # 这条与环境无关（有/无真实记忆都必须退 0）：记忆缺失只降级，不阻断交接包生成
    check("P: G5 真实定位链跑完 next 退出码 0（记忆缺失只降级、不阻断）",
          code_real == 0, t_real[:800])
    if real_facts:
        probe = real_facts[-1][:14]
        check("P: G5 真实数据命中（真实 KEY.md 尾部条目 + 真实来源路径出现在「项目关键事实」）",
              code_real == 0 and probe in t_real
              and real_key.as_posix() in t_real and "KEY.md：未提供" not in t_real, t_real[:2000])
        check("P: G5 读真实记忆目录是只读（前后文件数一致，不写不删）",
              cnt_before == cnt_after and cnt_before > 0, f"{cnt_before} -> {cnt_after}")
    else:
        # skip ≠ 通过：不计入断言数、不写进「已通过」，只打印原因（E20 ②）。
        print(f"\n⏭ 跳过真实数据断言：本机无真实 KEY.md（{real_key.as_posix()}）")
        print(f"   跳过只读断言：记忆目录为空（{cnt_before} -> {cnt_after}）")

    # ⑤ 带记忆时五角色仍 ≤12000 字节、必保五节 ✅×5（体积止损不许压必保节）
    for role in ("lead", "planner", "executor", "verifier", "inspector"):
        capture("next", *P, "--role", role, "--memories-dir", str(GK))
        f = _handoff(PROJ, "ctx", role)
        t = f.read_text(encoding="utf-8")
        line = next((ln for ln in t.splitlines() if "必保五节" in ln), "")
        check(f"P: G5 带记忆时 {role} 交接包 ≤12000 字节且「必保五节」✅×5 / ➖=0",
              f.stat().st_size <= 12000 and line.count("✅") == 5 and "➖" not in line,
              f"bytes={f.stat().st_size} {line[:120]}")


def _section_lines(text: str, heading: str) -> int:
    """`heading` 小节正文的非空行数（到下一个标题为止）。"""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if start is None:
            if ln.startswith(heading):
                start = i + 1
            continue
        if ln.startswith("#"):
            return sum(1 for x in lines[start:i] if x.strip())
    return sum(1 for x in lines[start:] if x.strip()) if start is not None else 0


def suite_q():
    """flow-quality-boost：A 静态检查 / B 知识入口 / C drive 只读合成 / D 图谱软告警。

    全部 fixture 落在 `ROOT`（`%TEMP%` 下按 pid 隔离）里；记忆走 `--memories-dir`、
    RAG 走 `--rag-dir` 隔离真实 `~/.dsh`，**绝不写真实记忆目录**。
    """
    PROJ = ROOT / "qc-proj"
    DEV = ROOT / "qc-proj-dev"
    (PROJ / "src").mkdir(parents=True)
    (DEV / "src").mkdir(parents=True)
    write(PROJ / "src" / "keep.py", "x = 1\n")
    write(DEV / "src" / "good.py", "def f():\n    return 1\n")
    write(DEV / "src" / "bad_syntax.py", "def f(:\n")
    write(DEV / "src" / "good.mjs", "export const y = 2;\n")
    write(DEV / "src" / "esm-in-js.js", "import fs from 'node:fs';\nexport const z = fs;\n")
    write(DEV / "src" / "bad.mjs", "export const = 1;\n")
    write(DEV / "src" / "good.json", '{"a": 1}\n')
    write(DEV / "src" / "bad.json", '{"a":}\n')
    write(DEV / "src" / "good.yml", "a: 1\n")
    write(DEV / "src" / "bad.yml", "a: [1,\n")

    P = ["-p", str(PROJ), "-f", "qc"]
    run("Q: init", "init", *P, "--scope", "src", "--no-graph")
    docs = PROJ / "docs" / "qc"
    write_design(docs)
    write_plan(docs)
    run("Q: advance DESIGN→PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    run("Q: advance PLAN→EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")

    # ---------------- A：只读静态检查（freeze 内挂载，绝不新增硬门禁） ----------------
    run("Q: A freeze 自动跑只读静态检查（坏样本不阻断冻结）",
        "freeze", *P, "--id", "C001", "--from", str(DEV), "--scope", "src")
    qc = docs / "evidence" / "C001" / "QC-static.md"
    check("Q: A1 freeze 生成 evidence/C001/QC-static.md", qc.is_file(), str(qc))
    t = qc.read_text(encoding="utf-8") if qc.is_file() else ""
    check("Q: A1 QC 证据三行（检查/等级/结果）可被 parse_evidence 命中",
          "检查：QC-static" in t and "等级：A" in t and "结果：fail" in t, t[:700])
    # C002：说明书写的是 `- 检查项：P18（对应 …）`，旧正则只认 `检查：` → check_id 退化成文件名。
    # 这里直接对着 parse_evidence 压两种写法（不是只改文档去迁就正则）。
    # 用 `-B` 子进程调，避免把 __pycache__ 写进 tools/（铁律①）。
    _ev_probe = ROOT / "qc-evidence-probe.md"
    _ev_script = (
        "import json,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);"
        "import dsh_flow;print(json.dumps(dsh_flow.parse_evidence(Path(sys.argv[2])),"
        "ensure_ascii=False))"
    )

    def _parse_probe(text: str) -> dict:
        write(_ev_probe, text)
        r = _sp([PY, "-B", "-c", _ev_script, str(PKG / "tools"), str(_ev_probe)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            return json.loads((r.stdout or "").strip().splitlines()[-1])
        except (IndexError, ValueError):
            return {"error": (r.stdout or "") + (r.stderr or "")}

    _meta = _parse_probe("# 探针\n\n- 检查项：P18（对应 DESIGN P4）\n- 等级：B\n- 结果：pass\n")
    _meta2 = _parse_probe("# 探针\n\n- 检查：P19\n- 等级：A\n- 结果：fail\n")
    _ev_probe.unlink(missing_ok=True)
    check("Q: A1 parse_evidence 同时认「检查项：」与「检查：」（check_id 不退化成文件名）",
          _meta.get("check_id") == "P18" and _meta.get("grade") == "B"
          and _meta.get("result") == "pass" and _meta2.get("check_id") == "P19",
          f"{_meta} {_meta2}")
    check("Q: A2 坏 .py 判 fail 且退出码非 0、好 .py 判 pass",
          re.search(r"\| src/bad_syntax\.py \| py \| python -B -m py_compile \| [1-9]\d* \| fail \|", t)
          is not None
          and "| src/good.py | py | python -B -m py_compile | 0 | pass |" in t, t[:1500])
    check("Q: A2 QC 文件含 PYTHONPYCACHEPREFIX 与「__pycache__ 自检：0」",
          "PYTHONPYCACHEPREFIX" in t and "__pycache__ 自检：0" in t)
    pyc_hits = [p.as_posix() for p in PROJ.rglob("__pycache__")] \
        + [p.as_posix() for p in DEV.rglob("__pycache__")]
    check("Q: A2 仓库与副本里 __pycache__ 命中 0（-B 管不住 py_compile，靠 PYTHONPYCACHEPREFIX）",
          pyc_hits == [], str(pyc_hits)[:500])
    node = shutil.which("node")
    if node:
        check("Q: A3 .js/.mjs 判据（good.mjs 与 esm-in-js.js 判 pass、bad.mjs 判 fail 且退出码非 0）",
              "| src/good.mjs | js | node --check | 0 | pass |" in t
              and re.search(r"\| src/esm-in-js\.js \| js \| node (?:--check|--input-type=module --check)"
                            r" \| 0 \| pass \|", t) is not None
              and re.search(r"\| src/bad\.mjs \| js \| node (?:--check|--input-type=module --check)"
                            r" \| [1-9]\d* \| fail \|", t) is not None, t[:2000])
    else:
        print("\n⏭ 跳过 A3 断言：本机 node 不可用")
        check("Q: A3 node 不可用时整类 skip 并写明「node 不可用」",
              "| src/good.mjs | js | （node 不在 PATH） | - | skip | node 不可用 |" in t, t[:1500])
    check("Q: A4 .json 判据（bad.json fail、good.json pass）",
          re.search(r"\| src/bad\.json \| json \| json\.load \| [1-9]\d* \| fail \|", t) is not None
          and "| src/good.json | json | json.load | 0 | pass |" in t, t[:1500])
    try:
        import yaml  # noqa: F401
        yaml_ok = True
    except Exception:
        yaml_ok = False
    if yaml_ok:
        # C002：yaml 判据改成「容忍 !!js 的 SafeLoader 子类」，命令列同步改名（判据没放宽：
        # 坏样本仍 fail，只是不再把 Cordis 的 `!!js` 有意写法当语法错误）
        check("Q: A4 .yml 判据（bad.yml fail、good.yml pass，用容忍 !!js 的 SafeLoader 子类）",
              re.search(r"\| src/bad\.yml \| yaml \| yaml\.load\(SafeLoader\+!!js\) \| [1-9]\d* \| fail \|", t)
              is not None
              and "| src/good.yml | yaml | yaml.load(SafeLoader+!!js) | 0 | pass |" in t, t[:1500])
    else:
        print("\n⏭ 跳过 A4-yaml 断言：本机 yaml 不可用")
        check("Q: A4 解析器不可用时该行记 skip + 原因（不得写成 pass）",
              "解析器不可用" in t
              and "| src/good.yml | yaml | yaml.load(SafeLoader+!!js) | 0 | pass |" not in t, t[:1500])

    man = json.loads((docs / "releases" / "C001" / "manifest.json").read_text(encoding="utf-8"))
    ev = [(e.get("check_id"), e.get("result"), e.get("grade")) for e in (man.get("evidence") or [])]
    check("Q: A1 QC-static 被同一次 freeze 登记进 manifest.evidence（result=fail、grade=A）",
          ("QC-static", "fail", "A") in ev, str(ev)[:400])
    check("Q: A1 manifest.checks.new 含 QC-static",
          "QC-static" in ((man.get("checks") or {}).get("new") or []), str(man.get("checks"))[:300])
    run("Q: A1 verify 通过（QC 只写 evidence/，没往 files/ 塞未登记文件）", "verify", *P, "--id", "C001")

    # A5 软告警不阻断 + 反向样本（硬门禁坏掉时仍必须红）
    out, code = capture("gate", *P)
    check("Q: A5 软告警不阻断：gate 退出码 0、含「⚠ 静态检查」且输出不含「✗」",
          code == 0 and "⚠ 静态检查" in out and "✗" not in out, out[-1500:])
    orig = (docs / "DESIGN.md").read_text(encoding="utf-8")
    try:
        write(docs / "DESIGN.md", orig.replace("状态：已确认", "状态：待用户确认"))
        out_bad, code_bad = capture("gate", *P, "--to", "PLAN")
        check("Q: A5 反向样本：DESIGN 确认行改坏后 gate 退出码 1 且含「✗」（软告警没把门禁弄哑）",
              code_bad == 1 and "✗" in out_bad, out_bad[-900:])
    finally:
        write(docs / "DESIGN.md", orig)
    run("Q: A5 有 QC fail 的候选上 advance --to VERIFYING 仍成功", "advance", *P,
        "--to", "VERIFYING", "--actor", "executor")
    run("Q: 回到 EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")

    # --skip-qc 逃生参数
    run("Q: A1 --skip-qc 可跳过静态检查（freeze 仍 0）", "freeze", *P, "--id", "C002",
        "--from", str(DEV), "--scope", "src", "--skip-qc")
    check("Q: A1 --skip-qc 时本候选没有 QC-static 证据（跳过就是跳过，不伪造）",
          not (docs / "evidence" / "C002" / "QC-static.md").exists())
    run("Q: A1 verify C002", "verify", *P, "--id", "C002")

    # ---------------- B：知识入口（离线采集） ----------------
    run("Q: B next 生成交接包（executor）", "next", *P, "--role", "executor")
    h = _handoff(PROJ, "qc", "executor")
    t = h.read_text(encoding="utf-8")
    check("Q: B1 交接包含「### 知识入口」子块", "### 知识入口" in t, t[:500])
    check("Q: B1 知识入口含 mnemon / agentmem / RAG 降级措辞 / feature 名",
          all(x in t for x in ("mnemon", "agentmem", "未提供（RAG sidecar 不可达）", "qc")),
          t[t.find("### 知识入口"):][:1600])
    check("Q: B5 交接包 ≤ 12000 字节", h.stat().st_size <= 12000, f"bytes={h.stat().st_size}")
    mem_line = next((ln for ln in t.splitlines() if ln.startswith("- 记忆离线层")), "")
    check("Q: B3 记忆离线层只写离线事实（该行不含「可用」）",
          bool(mem_line) and "可用" not in mem_line, mem_line[:500])
    check("Q: B4 RAG 行不含「RAG 可用」「RAG 已就绪」（离线判不了可用性）",
          "RAG 可用" not in t and "RAG 已就绪" not in t, "")
    EMPTY = ROOT / "qc-rag-empty"
    EMPTY.mkdir(parents=True, exist_ok=True)
    run("Q: B --rag-dir 指向空目录 → 退出码 0（降级不阻塞）", "next", *P,
        "--role", "executor", "--rag-dir", str(EMPTY))
    t2 = _handoff(PROJ, "qc", "executor").read_text(encoding="utf-8")
    check("Q: B4 --rag-dir 空目录时该行变「未安装（未提供）」",
          "RAG-Anything：未安装（未提供）" in t2, t2[t2.find("### 知识入口"):][:1200])
    run("Q: B next --no-context 退出码 0", "next", *P, "--role", "executor", "--no-context")
    t3 = _handoff(PROJ, "qc", "executor").read_text(encoding="utf-8")
    check("Q: B1 --no-context 不含「### 知识入口」（关闭即回到旧交接包）",
          "### 知识入口" not in t3, t3[:700])
    for role in ("lead", "planner", "executor", "verifier", "inspector"):
        capture("next", *P, "--role", role)
        f = _handoff(PROJ, "qc", role)
        tt = f.read_text(encoding="utf-8")
        line = next((ln for ln in tt.splitlines() if "必保五节" in ln), "")
        check(f"Q: B5 {role} 交接包 ≤12000 字节、含「### 知识入口」且必保五节 ✅×5",
              f.stat().st_size <= 12000 and "### 知识入口" in tt and line.count("✅") == 5,
              f"bytes={f.stat().st_size} {line[:100]}")
    capture("next", *P, "--role", "executor", "--max-context-chars", "600",
            "--key-note", "关键事实 A\n关键事实 B\n关键事实 C")
    f = _handoff(PROJ, "qc", "executor")
    tt = f.read_text(encoding="utf-8")
    check("Q: B 止损：--max-context-chars 600 仍 ≤12000，知识入口仍在、项目关键事实 ≥2 行",
          f.stat().st_size <= 12000 and "### 知识入口" in tt and "### 项目关键事实" in tt
          and _section_lines(tt, "### 项目关键事实") >= 2,
          f"bytes={f.stat().st_size} facts={_section_lines(tt, '### 项目关键事实')}")
    check("Q: B5 HANDOFF_MAX_BYTES 常量仍为 12000（不许改大常量来达标）",
          "HANDOFF_MAX_BYTES = 12000" in FLOW.read_text(encoding="utf-8"))
    ms = (PKG / "ops" / "memory-split.md").read_text(encoding="utf-8")
    check("Q: B4 ops/memory-split.md 有 RAG 节（含「与 mnemon 的可用性判据不混」与 rag_docs）",
          "RAG" in ms and "与 mnemon 的可用性判据不混" in ms and "rag_docs" in ms)
    check("Q: B1 templates/HANDOFF.md §九 增「知识入口」数据源行",
          "知识入口" in (PKG / "templates" / "HANDOFF.md").read_text(encoding="utf-8"))

    # ---------------- C：drive 只读合成 ----------------
    out, code = capture("drive", *P)
    labels = ("phase", "候选", "下一角色", "门禁", "软告警", "阻塞", "能否推进", "建议命令")
    check("Q: C1 drive 文本 8 个固定标签逐行命中（且正好 8 行）",
          all(lb in out for lb in labels) and len(out.strip().splitlines()) == 8, out[:1200])
    out_j, _ = capture("drive", *P, "--json")
    try:
        j = json.loads(out_j)
    except Exception:
        j = {}
    expect_keys = {"schema", "generated_at", "project", "feature", "phase", "candidate",
                   "next_role", "gate", "warnings", "blocked", "can_advance", "next_command"}
    check("Q: C4 drive --json 顶层键精确等于 12 个（多键少键都不合格）",
          set(j) == expect_keys, str(sorted(set(j) ^ expect_keys))[:400])
    check("Q: C4 drive --json 的 schema = dsh-flow/drive@1",
          j.get("schema") == "dsh-flow/drive@1", str(j.get("schema")))

    def _ro_snapshot():
        snap = {}
        for n in ("docs/qc/state.json", "docs/qc/ledger.md", "docs/qc/health.json"):
            p = PROJ / n
            snap[n] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "-"
        names = sorted(x.name for x in (PROJ / "docs" / "qc" / "handoffs").glob("*"))
        return snap, names

    before, hs_before = _ro_snapshot()
    capture("drive", *P)
    capture("drive", *P, "--json")
    capture("drive", *P)
    after, hs_after = _ro_snapshot()
    check("Q: C2 drive 严格只读（state/ledger/health 哈希与 handoffs 文件名集合全等）",
          before == after and hs_before == hs_after, f"{before} -> {after}")

    BAD = ROOT / "qc-bad"
    (BAD / "src").mkdir(parents=True, exist_ok=True)
    write(BAD / "src" / "a.py", "x = 1\n")
    run("Q: C3 反向样本 init（DESIGN 未确认）", "init", "-p", str(BAD), "-f", "bad",
        "--scope", "src", "--no-graph")
    out_b, code_b = capture("drive", "-p", str(BAD), "-f", "bad")
    check("Q: C3 硬门禁未过 → drive 退出码 1", code_b == 1, out_b[-700:])
    out_m, code_m = capture("drive", "-p", str(ROOT / "qc-nope"), "-f", "nosuch")
    check("Q: C3 state.json 缺失 → drive 退出码 2（沿用 die() 默认码）", code_m == 2, out_m[-500:])
    run("Q: C3 block 标记阻塞", "block", *P, "--reason", "等用户重启 DSH",
        "--owner", "user", "--kind", "env")
    out_k, code_k = capture("drive", *P)
    check("Q: C3 blocked 但门禁通过 → 退出码 0 且建议命令给 unblock",
          code_k == 0 and "unblock" in out_k and "阻塞     : [" in out_k, out_k[:900])
    run("Q: C3 unblock 解除阻塞", "unblock", *P, "--note", "已重启")
    gt = (PKG / "GLOSSARY.md").read_text(encoding="utf-8")
    check("Q: C5 GLOSSARY 命令表含 drive 且小节标题为「24 个子命令」（C002 补 block/unblock 两行）",
          "24 个子命令" in gt and "| `drive` |" in gt and "`cmd_drive`" in gt
          and "| `block` |" in gt and "| `unblock` |" in gt, "")
    for path, label in ((PKG / "README.md", "README.md"),
                        (PKG / "roles" / "00-lead.md", "roles/00-lead.md"),
                        (PKG / "skills" / "dsh-multi-role-flow" / "SKILL.md", "skills/SKILL.md")):
        check(f"Q: C5 {label} 出现 drive 用法（四处文档同步）",
              "drive" in path.read_text(encoding="utf-8"))

    # ---------------- D：图谱证据化软检查（双向） ----------------
    ep = docs / "EXECUTION-PLAN.md"
    try:
        write(ep, "## 受影响文件（E11）\n\n- 待补\n\n## 下一步\n\n无\n")
        out_d, code_d = capture("gate", *P)
        check("Q: D1 有节无参数 → gate 打「⚠ 图谱证据·EXECUTION-PLAN」并指名 ops/code-graph.md §4，"
              "退出码 0",
              "⚠ 图谱证据·EXECUTION-PLAN" in out_d and "ops/code-graph.md §4" in out_d
              and code_d == 0, out_d[-1200:])
        write(ep, "## 受影响文件（E11）\n\n未建图，改用文件列举 + 哈希差集\n\n## 下一步\n\n无\n")
        out_d2, _ = capture("gate", *P)
        check("Q: D1 写「未建图」后该告警消失", "⚠ 图谱证据·EXECUTION-PLAN" not in out_d2,
              out_d2[-900:])
        write(ep, "## 受影响文件\n\n- 待补\n\n## 下一步\n\n无\n")
        out_d3, _ = capture("gate", *P)
        check("Q: D1 标题无序号后缀（## 受影响文件）也能命中（前缀匹配）",
              "⚠ 图谱证据·EXECUTION-PLAN" in out_d3, out_d3[-900:])
        write(ep, "# 台账\n\n没有该小节\n")
        out_d4, _ = capture("gate", *P)
        check("Q: D1 小节不存在时不告警（还没到写影响面的阶段）",
              "⚠ 图谱证据·EXECUTION-PLAN" not in out_d4, out_d4[-900:])
    finally:
        write(ep, "# EXECUTION-PLAN\n\n## 进度\n\n- 自测\n")
    rp = docs / "releases" / "C002" / "RELEASE-REPORT.md"
    orig_rp = rp.read_text(encoding="utf-8") if rp.is_file() else ""
    try:
        write(rp, "# 发布报告 C002\n\n## 核验结果\n\n- 待补\n\n## 待用户试用清单\n\n- 真实体验\n\n"
                  "结论：待用户试用\n")
        out_r, code_r = capture("gate", *P)
        check("Q: D2 RELEASE-REPORT 有节无参数 → 打「⚠ 图谱证据·RELEASE-REPORT」且退出码仍 0",
              "⚠ 图谱证据·RELEASE-REPORT" in out_r and "ops/code-graph.md §6" in out_r
              and code_r == 0, out_r[-1200:])
        write(rp, "# 发布报告 C002\n\n## 核验结果\n\n- graph_stats：269 节点 / 685 边\n\n"
                  "## 待用户试用清单\n\n- 真实体验\n\n结论：待用户试用\n")
        out_r2, _ = capture("gate", *P)
        check("Q: D2 含 graph_stats 后该告警消失（只看该节正文）",
              "⚠ 图谱证据·RELEASE-REPORT" not in out_r2, out_r2[-900:])
    finally:
        if orig_rp:
            write(rp, orig_rp)

    out_f, code_f = capture("drive", *P)
    check("Q: D3 软告警只出现在「软告警」行，不进「门禁 N/M」计数、不影响 drive 退出码",
          code_f == 0 and "软告警" in out_f, out_f[:1200])

    # ---------------- E：C002 QC 假阳性修复（模板骨架 skip + `!!js` 容忍） ----------------
    # 独立副本：只放本组样本，避免 src/ 里既有的 4 个坏样本把 fail 计数搅浑。
    DEV2 = ROOT / "qc-proj-dev2"
    write(DEV2 / "templates" / "plugin-pack" / "client.js", "const x = {{PACK_ID}};\n")
    write(DEV2 / "templates" / "plugin-pack" / "ok.json", '{"a": 1}\n')
    write(DEV2 / "src" / "patch.yml",
          "a: 1\nb: !!js \"process.getBuiltinModule('node:path')\"\n")
    write(DEV2 / "src" / "moved-tpl.js", "const y = {{PACK_NAME}};\n")
    run("Q: E freeze（模板骨架 + !!js 容忍）", "freeze", *P, "--id", "C003",
        "--from", str(DEV2), "--scope", "src", "--scope", "templates")
    qc3 = docs / "evidence" / "C003" / "QC-static.md"
    t3 = qc3.read_text(encoding="utf-8") if qc3.is_file() else ""
    check("Q: E1 templates/** 的失败项判 skip（结果列 skip、退出码仍如实保留）",
          re.search(r"\| templates/plugin-pack/client\.js \| js \| node --check \| [1-9]\d* \| skip \|",
                    t3) is not None
          and "模板骨架，含占位符，不可直接编译（路径前缀 templates/）" in t3, t3[:2200])
    check("Q: E1 能通过的模板文件仍判 pass（不是把 templates/ 一律涂成 skip）",
          "| templates/plugin-pack/ok.json | json | json.load | 0 | pass |" in t3, t3[:1800])
    check("Q: E2 根级 yaml 的 !!js 标签判 pass 且备注「已容忍」（C001 的假阳性）",
          re.search(r"\| src/patch\.yml \| yaml \| yaml\.load\(SafeLoader\+!!js\) \| 0 \| pass \| "
                    r"已容忍 !!js 自定义标签 \|", t3) is not None, t3[:2200])
    check("Q: E3 非 templates/ 路径但含 {{...}} 占位符的失败项走兜底判据判 skip",
          re.search(r"\| src/moved-tpl\.js \| js \| node --check \| [1-9]\d* \| skip \|", t3) is not None
          and "非 templates/ 路径但含未替换" in t3, t3[:2200])
    check("Q: E3 结论行自报模板骨架条数、fail 归零（软告警不因此变硬门禁）",
          "模板骨架（skip，不进 fail 计数）：2 个" in t3 and "fail 0 /" in t3
          and "结果：pass" in t3, t3[-1200:])

    # ---------------- E4：执行线程侧 P* 证据软告警（§六；只 ⚠ 不阻断） ----------------
    out_w, code_w = capture("gate", *P)
    check("Q: E4 候选只有 QC-static 时 gate 打「⚠ 证据：…缺执行线程侧 P* 证据」且退出码 0",
          code_w == 0 and "⚠ 证据：" in out_w and "缺执行线程侧 P* 证据" in out_w
          and "QC-static" in out_w and "✗" not in out_w, out_w[-1200:])
    # 先写 P 证据再 freeze（roles/02-executor.md 的硬要求）→ 该告警必须消失
    write(docs / "evidence" / "C004" / "P18-probe.md",
          "# P18 · 证据在位探针\n\n- 检查：P18\n- 等级：A\n- 结果：pass\n")
    run("Q: E4 freeze C004（先写 P* 证据再 freeze）", "freeze", *P, "--id", "C004",
        "--from", str(DEV2), "--scope", "src", "--scope", "templates")
    man4 = json.loads((docs / "releases" / "C004" / "manifest.json").read_text(encoding="utf-8"))
    ids4 = [e.get("check_id") for e in (man4.get("evidence") or [])]
    out_w2, code_w2 = capture("gate", *P)
    check("Q: E4 先写 P* 再 freeze → manifest.evidence 含 P18 且告警消失（不阻断门禁）",
          "P18" in ids4 and code_w2 == 0 and "缺执行线程侧 P* 证据" not in out_w2,
          f"ids={ids4} {out_w2[-900:]}")

    # ---------------- F：C003 图谱污染 —— bundle 变体的排除行与两处污染判据 ----------------
    # 直接压 dsh_flow 模块里的**真实函数**（`-B` 子进程 import，避免把 __pycache__ 写进 tools/，铁律①）：
    # `.graphifyignore` 的期望行集合、`_ensure_graphifyignore()` 的幂等/只追加、
    # `_graph_pollution()` 与 `_ctx_graph_summary()` 两处正则（共用 `RE_GRAPH_COPY_SOURCE`）。
    FW = ROOT / "c003-probe"
    probe = ROOT / "c003-graph-probe.py"
    write(probe, '''import hashlib, json, sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])          # tools/
import dsh_flow as f                     # noqa: E402
work = Path(sys.argv[2])
out = {}

out["ignore_lines"] = list(f.GRAPH_IGNORE_LINES)

# 1) 新建 + 连跑两次：字节一致（幂等）
fresh = work / "fresh" / ".graphifyignore"
fresh.parent.mkdir(parents=True, exist_ok=True)
f._ensure_graphifyignore(fresh)
h1 = hashlib.sha256(fresh.read_bytes()).hexdigest()
out["fresh_text"] = fresh.read_text(encoding="utf-8")
f._ensure_graphifyignore(fresh)
out["idempotent"] = hashlib.sha256(fresh.read_bytes()).hexdigest() == h1

# 2) 预置用户行：只追加缺行、不删用户行、不改顺序（`dsh-bundle-live/` 已有则不再追加）
up = work / "user" / ".graphifyignore"
up.parent.mkdir(parents=True, exist_ok=True)
up.write_text("*.tmp\\ndsh-bundle-live/\\n", encoding="utf-8", newline="\\n")
f._ensure_graphifyignore(up)
ut = up.read_text(encoding="utf-8")
out["user_lines"] = ut.splitlines()
out["user_live_count"] = ut.splitlines().count("dsh-bundle-live/")

def mk(rel, files):
    d = work / rel / "graphify-out"
    d.mkdir(parents=True, exist_ok=True)
    (d / "graph.json").write_text(
        json.dumps({"nodes": [{"source_file": s} for s in files]}), encoding="utf-8")
    return work / rel

# 3) 污染判据正样本：dsh-bundle / -live / -dist / releases 都算，`dsh-bundleable` 不算
pa = mk("graph-a", ["dsh-bundle-live/x.js", "dsh-bundle-dist/x.js",
                    "docs/demo/releases/C001/files/a.py", "dsh-bundle/x.py",
                    "dsh-bundleable/x.js", "tools/dsh_flow.py"])
out["poll_hits"] = f._graph_pollution(pa)
out["summary_hits"] = f._ctx_graph_summary(pa, {"scope": []})

# 4) 反向样本：只有 dsh-bundleable/ 时必须是 0（避免通配误伤）
pb = mk("graph-b", ["dsh-bundleable/x.js", "tools/dsh_flow.py"])
out["poll_false_positive"] = f._graph_pollution(pb)

print("PROBE_JSON " + json.dumps(out, ensure_ascii=False))
''')
    pr = _sp([PY, "-B", str(probe), str(PKG / "tools"), str(FW)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    _probe_line = [ln for ln in (pr.stdout or "").splitlines() if ln.startswith("PROBE_JSON ")]
    try:
        prj = json.loads(_probe_line[-1][len("PROBE_JSON "):]) if _probe_line else {}
    except ValueError:
        prj = {}
    if not prj:
        prj = {"probe_error": (pr.stdout or "") + (pr.stderr or "")}
    probe.unlink(missing_ok=True)

    check("Q: F1 GRAPH_IGNORE_LINES 覆盖三个 bundle 变体（含新加的 -live / -dist，保留 dsh-bundle/）",
          {"dsh-bundle/", "dsh-bundle-live/", "dsh-bundle-dist/"} <= set(prj.get("ignore_lines") or []),
          json.dumps(prj.get("ignore_lines") or prj, ensure_ascii=False)[:600])
    _ft = prj.get("fresh_text") or ""
    check("Q: F1 新建 .graphifyignore = 首行注释 + 9 行排除且顺序不改（与 GRAPH_IGNORE_LINES 逐行一致）",
          _ft.splitlines()[:1] == ["# 由 dsh_flow.py init 维护；只排除封存副本与工具产物"]
          and _ft.splitlines()[1:] == list(prj.get("ignore_lines") or []),
          repr(_ft)[:800])
    check("Q: F2 连续两次 _ensure_graphifyignore 字节一致（幂等，不重写）",
          prj.get("idempotent") is True, json.dumps(prj, ensure_ascii=False)[:600])
    _ul = prj.get("user_lines") or []
    check("Q: F2 预置用户行只追加缺行：首行仍是 *.tmp、既有 dsh-bundle-live/ 不重复、缺行顺序不变",
          _ul[:2] == ["*.tmp", "dsh-bundle-live/"] and prj.get("user_live_count") == 1
          and _ul[2:4] == ["docs/**/releases/", "docs/**/archive/"]
          and _ul[-1] == "graphify-out/" and "dsh-bundle-dist/" in _ul,
          json.dumps(_ul, ensure_ascii=False)[:900])
    check("Q: F3 _graph_pollution 认 dsh-bundle / -live / -dist / releases（4 个命中）",
          prj.get("poll_hits") == 4,
          f"hits={prj.get('poll_hits')} raw={json.dumps(prj, ensure_ascii=False)[:400]}")
    check("Q: F3 反样本：dsh-bundleable/ 不被判成副本（0 命中，正则不是 dsh-bundle[^/]*）",
          prj.get("poll_false_positive") == 0, str(prj.get("poll_false_positive")))
    check("Q: F4 _ctx_graph_summary 同步报「图中含封存副本 4 个节点」（第二处正则共用同一判据）",
          any("图中含封存副本 4 个节点" in ln for ln in (prj.get("summary_hits") or [])),
          "\n".join(prj.get("summary_hits") or [])[:800])

    # ---------------- G：C007 判据**本体**（纯函数）+ ROADMAP 不写死状态 ----------------
    # 口径变更（Lead 2026-11-21 裁决）：端到端双向断言已迁到 `suite_s()`——主判据改成
    # 「相邻候选**变更集**」，本组只留两个**与项目形态无关**的判据单测：
    #   ① `_doc_only_candidate()`（回退判据：产物全量扩展名）的 6 个边界；
    #   ② `ROADMAP.md` 的写死值守门员。
    # 为什么删掉原来的「freeze 纯文档源 → 不报」端到端断言：本项目 `--scope .` 整包冻结，
    # 跨源目录冻结时变更集里必然出现被删的 `.js` → 按新判据就是代码候选（断言会假红）。
    probe2 = ROOT / "c007-doc-probe.py"
    write(probe2, '''import json, sys
sys.path.insert(0, sys.argv[1])
import dsh_flow as f
cases = {
    "doc_only": [{"path": "handbook/guide.md"}, {"path": "README.md"},
                 {"path": "config/app.json"}, {"path": "data/x.csv"}, {"path": "logo.svg"}],
    "mixed": [{"path": "README.md"}, {"path": "tools/dsh_flow.py"}],
    "empty": [],
    "no_suffix": [{"path": "LICENSE"}],
    "upper": [{"path": "TOOLS/INSTALL.PS1"}],
    "wasm": [{"path": "addon/x.node"}, {"path": "docs/a.md"}],
}
print("PROBE_JSON " + json.dumps(
    {k: list(f._doc_only_candidate({"artifacts": v})) for k, v in cases.items()},
    ensure_ascii=False))
''')
    pr2 = _sp([PY, "-B", str(probe2), str(PKG / "tools")],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    probe2.unlink(missing_ok=True)
    _l2 = [ln for ln in (pr2.stdout or "").splitlines() if ln.startswith("PROBE_JSON ")]
    try:
        pj2 = json.loads(_l2[-1][len("PROBE_JSON "):]) if _l2 else {}
    except ValueError:
        pj2 = {}
    if not pj2:
        pj2 = {"probe_error": (pr2.stdout or "") + (pr2.stderr or "")}
    check("Q: G3 _doc_only_candidate 边界：文档类 True（附扩展名统计）/ 混合含 .py → False / "
          "空产物 → False（判不了按代码候选）/ 无扩展名 → True / 大写 .PS1 → False / .node → False",
          pj2.get("doc_only", [None])[0] is True
          and "json" in str(pj2.get("doc_only", ["", ""])[1])
          and pj2.get("mixed", [None])[0] is False
          and "代码类" in str(pj2.get("mixed", ["", ""])[1])
          and pj2.get("empty", [None])[0] is False
          and "无法判定" in str(pj2.get("empty", ["", ""])[1])
          and pj2.get("no_suffix", [None])[0] is True
          and "无扩展名" in str(pj2.get("no_suffix", ["", ""])[1])
          and pj2.get("upper", [None])[0] is False
          and pj2.get("wasm", [None])[0] is False,
          json.dumps(pj2, ensure_ascii=False)[:900])

    # ROADMAP 不再写死状态值（C007 ②）：§0.1 是标注过的历史快照（该节自带「不随后续候选更新」注），
    # 其余任何「状态赋值式陈述」都必须同句标时点，否则这条断言就红——它就是守门员。
    road = (PKG / "ROADMAP.md").read_text(encoding="utf-8")
    _keep, _skip = [], False
    for _ln in road.splitlines():
        if _ln.startswith("## 0.1"):
            _skip = True
        elif _skip and _ln.startswith("## "):
            _skip = False
        if not _skip:
            _keep.append(_ln)
    bare = [ln.strip() for ln in _keep
            if (re.search(r"current_candidate\s*=\s*C\d{3}", ln)
                or re.search(r"(?<![A-Za-z_])phase\s*=\s*(DESIGN|PLAN|EXECUTING|VERIFYING|TRIAL|DONE|ROLLED_BACK)\b", ln))
            and not (re.search(r"\d{4}-\d{2}-\d{2}", ln) or "时点" in ln or "历史" in ln)]
    check("Q: G4 ROADMAP（§0.1 历史快照之外）没有「写死状态值且未标时点」的赋值式陈述",
          bare == [], "\n".join(bare)[:900] or "无裸赋值")
    check("Q: G4 ROADMAP 写明「现值以 flow.py status / flow.py drive 现读为准」的口径",
          "flow.py status" in road and "flow.py drive" in road
          and "现读为准" in road, road[:300])

    # ---------------- G5：P 证据 check_id 的两种合法形态（C008 回归守门员） ----------------
    # 回归现场（C007 已 drop）：`warn_for()` 的 E1 曾收紧成 `re.fullmatch(r"P\d+", check_id)`，
    # 只认「P29」不认「P29-doc-only-candidate」——而 roles/02-executor.md 的命名规范**就是**
    # `P<编号>-<短名>.md`，于是正常格式被误杀：候选冻结后反而报「缺执行线程侧 P* 证据」。
    # 三条断言钉死「两种都认 + 无文件不认」。
    PEB = ROOT / "c008-pev-probe"
    pev = PEB / "docs" / "feat" / "evidence" / "C008"
    write(pev / "P29-doc-only-candidate.md", "# P29\n\n- 检查：P29-doc-only-candidate\n- 等级：A\n- 结果：pass\n")
    write(pev / "P30-roadmap-no-hardcoded-state.md", "# P30\n\n- 等级：A\n- 结果：pass\n")
    probe4 = ROOT / "c008-pev-probe.py"
    write(probe4, '''import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import dsh_flow as f

base = Path(sys.argv[2]) / "docs" / "feat"
EV = "docs/feat/evidence/C008/"


def man(check_id, file):
    return {"evidence": [{"check_id": check_id, "file": file, "grade": "A", "result": "pass"}]}


out = {
    "plain":  list(f._has_p_evidence(base, man("P29", EV + "P29-doc-only-candidate.md"), "C008")),
    "named":  list(f._has_p_evidence(base, man("P29-doc-only-candidate",
                                               EV + "P29-doc-only-candidate.md"), "C008")),
    "missing": list(f._has_p_evidence(base, man("P29-fake", EV + "P29-fake.md"), "C008")),
    "stem_fallback": list(f._has_p_evidence(
        base, man("P30-roadmap-no-hardcoded-state", EV + "P30-roadmap-no-hardcoded-state.md"), "C008")),
    "qc_only": list(f._has_p_evidence(base, man("QC-static", EV + "P29-doc-only-candidate.md"), "C008")),
    "regex": [bool(f.RE_P_CHECK_ID.fullmatch(s)) for s in
              ("P29", "P29-doc-only-candidate", "P29-fake", "P29-", "P", "QC-static", "P29_x")],
}
print("PROBE_JSON " + json.dumps(out, ensure_ascii=False))
''')
    pr4 = _sp([PY, "-B", str(probe4), str(PKG / "tools"), str(PEB)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    probe4.unlink(missing_ok=True)
    _l4 = [ln for ln in (pr4.stdout or "").splitlines() if ln.startswith("PROBE_JSON ")]
    try:
        pj4 = json.loads(_l4[-1][len("PROBE_JSON "):]) if _l4 else {}
    except ValueError:
        pj4 = {}
    if not pj4:
        pj4 = {"probe_error": (pr4.stdout or "") + (pr4.stderr or "")}
    _raw4 = json.dumps(pj4, ensure_ascii=False)[:900]
    check("Q: G5 ① `check_id=\"P29\"` + 文件存在 → **认**（纯数字形态）",
          (pj4.get("plain") or [False])[0] is True and (pj4.get("plain") or ["", ""])[1] == "P29", _raw4)
    check("Q: G5 ② `check_id=\"P29-doc-only-candidate\"` + 文件存在 → **认**"
          "（本轮回归守门员：C007 就是死在这一条上）",
          (pj4.get("named") or [False])[0] is True
          and (pj4.get("named") or ["", ""])[1] == "P29-doc-only-candidate", _raw4)
    check("Q: G5 ③ `check_id=\"P29-fake\"` + **文件不存在** → **不认**（防伪造靠文件存在，不靠正则）",
          (pj4.get("missing") or [True])[0] is False, _raw4)
    check("Q: G5 补充：文件名主干兜底（无「检查：」行）也认；`QC-static` 不算 P 证据；"
          "`RE_P_CHECK_ID` 对 `P29-`/`P`/`QC-static`/`P29_x` 全部不匹配",
          (pj4.get("stem_fallback") or [False])[0] is True
          and (pj4.get("qc_only") or [True])[0] is False
          and pj4.get("regex") == [True, True, True, False, False, False, False], _raw4)


def suite_r():
    """C004：部署台账**每候选独立快照**——连续 seal 两个候选后，前一个不许被后一个写台账弄红。

    回归探针（这条是本轮的验收核心）：旧实现下第二个 `seal` 必然把第一个候选判红
    （`cmd_seal` 直接登记共用 `docs/<feature>/DEPLOYMENT-PLAN.md` 的哈希）。
    """
    PROJ = ROOT / "seal-ledger-proj"
    DEV = ROOT / "seal-ledger-proj-dev"
    (PROJ / "src").mkdir(parents=True)
    (DEV / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    write(DEV / "src" / "a.py", "x = 2\n")
    P = ["-p", str(PROJ), "-f", "ledger"]
    docs = PROJ / "docs" / "ledger"
    ledger = docs / "DEPLOYMENT-PLAN.md"
    snap = {cid: docs / "releases" / cid / "DEPLOYMENT-PLAN.md" for cid in ("C001", "C002")}

    run("R: init", "init", *P, "--scope", "src")
    run("R: baseline", "baseline", *P)
    write_design(docs)
    run("R: DESIGN -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    write_plan(docs)
    run("R: PLAN -> EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")

    # ---- 候选 1 ----
    run("R: freeze C001", "freeze", *P, "--id", "C001", "--from", str(DEV), "--scope", "src",
        "--actor", "executor")
    write_report(docs, "C001")
    run("R: seal C001", "seal", *P, "--id", "C001")
    v1 = json.loads((docs / "releases" / "C001" / "verification.json").read_text(encoding="utf-8"))
    paths1 = [f.get("path") for f in (v1.get("files") or [])]
    check("R: seal 生成 releases/C001/DEPLOYMENT-PLAN.md 快照", snap["C001"].is_file(),
          json.dumps(paths1, ensure_ascii=False))
    check("R: C001 verification.json 记的是快照路径，不是共用台账",
          "docs/ledger/releases/C001/DEPLOYMENT-PLAN.md" in paths1
          and "docs/ledger/DEPLOYMENT-PLAN.md" not in paths1,
          json.dumps(paths1, ensure_ascii=False))
    check("R: C001 快照当时与共用台账逐字节一致",
          snap["C001"].is_file() and snap["C001"].read_bytes() == ledger.read_bytes(),
          f"snapshot={len(snap['C001'].read_bytes()) if snap['C001'].is_file() else 'missing'}B "
          f"ledger={len(ledger.read_bytes())}B")

    # ---- 验证线程写共用台账（L001 现场：C001 当年就是这么红的）----
    write(ledger, ledger.read_text(encoding="utf-8") + "\n## C001 之后验证线程补记\n- 写共用台账\n")
    out1a, code1a = capture("verify", *P, "--id", "C001")
    check("R: 只 seal 了 C001 时，写共用台账不弄红 C001", code1a == 0 and "封存校验通过" in out1a,
          out1a[-700:])

    # ---- 候选 2 ----
    run("R: freeze C002", "freeze", *P, "--id", "C002", "--from", str(DEV), "--scope", "src",
        "--actor", "executor")
    write_report(docs, "C002")
    run("R: seal C002", "seal", *P, "--id", "C002")

    out1, code1 = capture("verify", *P, "--id", "C001")
    check("R: 连续 seal 两个候选后 C001 仍 verify 通过（回归探针：旧实现必红）",
          code1 == 0 and "封存校验通过" in out1, out1[-900:])
    out2, code2 = capture("verify", *P, "--id", "C002")
    check("R: C002 verify 通过", code2 == 0 and "封存校验通过" in out2, out2[-900:])

    v2 = json.loads((docs / "releases" / "C002" / "verification.json").read_text(encoding="utf-8"))
    paths2 = [f.get("path") for f in (v2.get("files") or [])]
    check("R: 两个候选各有自己的快照，且 C002 记的是 C002 的快照",
          snap["C002"].is_file() and "docs/ledger/releases/C002/DEPLOYMENT-PLAN.md" in paths2
          and "docs/ledger/DEPLOYMENT-PLAN.md" not in paths2,
          json.dumps(paths2, ensure_ascii=False))
    check("R: 两份快照内容互不相同（各自冻结自己那一刻）",
          snap["C001"].read_bytes() != snap["C002"].read_bytes(),
          f"C001={len(snap['C001'].read_bytes())}B C002={len(snap['C002'].read_bytes())}B")

    # ---- 反向探针：再改一次共用台账，两个候选都不受影响 ----
    write(ledger, ledger.read_text(encoding="utf-8") + "\n- 第二次改共用台账\n")
    out1b, code1b = capture("verify", *P, "--id", "C001")
    out2b, code2b = capture("verify", *P, "--id", "C002")
    check("R: 再写一次共用台账后 C001 仍通过（反向探针）", code1b == 0, out1b[-700:])
    check("R: 再写一次共用台账后 C002 仍通过（反向探针）", code2b == 0, out2b[-700:])
    check("R: 共用台账本身没被 seal 改回（验证线程仍可写它，人读台账保留）",
          "第二次改共用台账" in ledger.read_text(encoding="utf-8"), ledger.read_text(encoding="utf-8")[-300:])
    check("R: 快照不跟着共用台账漂移",
          snap["C001"].read_bytes() != ledger.read_bytes()
          and snap["C002"].read_bytes() != ledger.read_bytes(), "")

    # ---- 封存检测没失灵：改候选自己的快照，必须红 ----
    write(snap["C001"], snap["C001"].read_text(encoding="utf-8") + "\n篡改\n")
    out1c, code1c = capture("verify", *P, "--id", "C001")
    check("R: 篡改候选自己的台账快照 → C001 verify 变红（封存检测未失灵）",
          code1c == 1 and "DEPLOYMENT-PLAN.md" in out1c, out1c[-700:])


def suite_s():
    """C007（Lead 裁决 + R01 评审后的**主判据**）：文档类候选免 P* 证据 —— 相邻候选**变更集**。

    为什么单开一套：旧口径（产物**全量**扩展名）在本项目**恒判代码候选**——`freeze --scope .`
    整包冻结，每个候选固定带 `tools/*.py` 等 8 个代码类产物（C006 实测 8/48），端到端断言只能
    假红。新口径看「**这一轮改了什么**」，才压得到「文档类不报 / 代码类必报」两侧。

    覆盖（R01 §四 点名的 12 条，逐条落地）：
    - 端到端 4 条：首候选回退 / **零变更独立告警** / 只改 `.md` → 文档类 / 新增 `.py` → 代码类 /
      删除 `.py` → 代码类 / 重命名（文档 / 代码 / `.bak` 三例）；
    - 纯函数 17 条：四态 + 删除分支 + 三个重命名 + 空 sha + `!!js` 内容覆盖 + scope 差异 +
      数值序 + 真实 6 候选回归 + **反向守门**（把 `.json` 塞进代码类，真实断言必红）。
    """
    PROJ = ROOT / "doc-delta-proj"
    SRC = ROOT / "doc-delta-src"
    (PROJ / "handbook").mkdir(parents=True)
    (SRC / "handbook").mkdir(parents=True)
    (SRC / "config").mkdir(parents=True)
    write(PROJ / "handbook" / "KEEP.md", "# 项目侧文档（不进候选，只让 baseline 非空）\n")
    P = ["-p", str(PROJ), "-f", "delta"]
    docs = PROJ / "docs" / "delta"

    run("S: init（scope=handbook/config，--no-graph）", "init", *P,
        "--scope", "handbook", "--scope", "config", "--no-graph")
    run("S: baseline", "baseline", *P)
    write_design(docs)
    run("S: DESIGN -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    write_plan(docs)
    run("S: PLAN -> EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")

    def _freeze(cid: str, label: str) -> None:
        run(f"S: freeze {cid}（{label}）", "freeze", *P, "--id", cid, "--from", str(SRC),
            "--scope", "handbook", "--scope", "config")

    def _gate() -> "tuple[str, int]":
        return capture("gate", *P)

    # ---- ① 首候选：无相邻对照 → 回退全量扩展名判据，提示里必须明示「回退」 ----
    write(SRC / "handbook" / "guide.md", "# 指南\n\n- 只改文档\n")
    write(SRC / "handbook" / "faq.txt", "常见问题\n")
    write(SRC / "config" / "app.json", '{"a": 1}\n')
    _freeze("C001", "首个候选，纯文档源")
    out, code = _gate()
    check("S: S1 首个候选无相邻对照 → **回退全量扩展名判据**（提示明示「回退」），"
          "文档类不报 P*，且不出现「判据：变更集」（exit 0）",
          code == 0 and "缺执行线程侧 P* 证据" not in out
          and "回退全量扩展名判据" in out and "为文档类" in out
          and "判据：变更集" not in out, out[-900:])

    # ---- ② 零变更（两次冻结逐字节相同）→ 判不了：走**独立**「零变更」告警 ----
    # R01 §二.2(a) 主漏洞：`docs/` 在 freeze 里结构性排除，所以「只改 docs/」的候选产物集
    # 必然无变化。若把它判成「代码候选（要有 P*）」，恰好把本规则最想救的那类打死；
    # 但也不能静默免检 → 必须是**独立一条** ⚠，两个概念不许合并。
    _freeze("C002", "与 C001 逐字节相同")
    out, code = _gate()
    check("S: S2 零变更（与 C001 逐字节相同）→ 打**独立**「零变更」告警；"
          "既不报「缺 P*」也不报「为文档类」（两个概念不合并）",
          code == 0 and "零变更" in out and "逐字节相同" in out
          and "缺执行线程侧 P* 证据" not in out and "为文档类" not in out, out[-900:])

    # ---- ③ 只改文档 → 文档类（相邻代码类变更 0） ----
    write(SRC / "handbook" / "guide.md", "# 指南 v2\n\n- 只改文档，没有代码行为\n")
    _freeze("C003", "只改 .md")
    out, code = _gate()
    check("S: S3 只改 1 个 .md → 文档类，**不报** P*，提示标明「判据：变更集」+「变更集 1 个文件」",
          code == 0 and "缺执行线程侧 P* 证据" not in out and "为文档类" in out
          and "判据：变更集" in out and "变更集 1 个文件" in out, out[-900:])

    # ---- ④ 新增 .py → 代码候选 ----
    write(SRC / "config" / "build.py", "VALUE = 1\n")
    _freeze("C004", "新增 config/build.py")
    out, code = _gate()
    check("S: S4 新增 1 个 .py → **仍报** P*，提示给出「变更集 1 个文件…代码类 1 个（如 config/build.py）」",
          code == 0 and "缺执行线程侧 P* 证据" in out and "代码类 1 个" in out
          and "config/build.py" in out, out[-900:])

    # ---- ⑤ 只删掉那个 .py（新增/修改都 0）→ 仍报：删除按原 path 扩展名判代码类 ----
    (SRC / "config" / "build.py").unlink()
    _freeze("C005", "只删 config/build.py")
    out, code = _gate()
    check("S: S5 只删 1 个 .py（新增 0 / 修改 0 / 删除 1）→ **仍报** P*（删代码 = 行为变了）",
          code == 0 and "缺执行线程侧 P* 证据" in out and "删除 1" in out
          and "代码类 1 个" in out, out[-900:])

    # ---- ⑥a 文档重命名（旧 path 删 + 新 path 增，都是 .txt）→ 文档类 ----
    (SRC / "handbook" / "faq.txt").rename(SRC / "handbook" / "faq-v2.txt")
    _freeze("C006", "文档重命名 faq.txt → faq-v2.txt")
    out, code = _gate()
    check("S: S6 文档重命名（删 .txt + 增 .txt，共 2 个变更）→ 文档类，**不报** P*",
          code == 0 and "缺执行线程侧 P* 证据" not in out and "为文档类" in out
          and "变更集 2 个文件" in out, out[-900:])

    # ---- ⑥b 重命名**涉及代码类**（.txt → .py）→ 仍报 ----
    (SRC / "handbook" / "faq-v2.txt").unlink()
    write(SRC / "handbook" / "faq_v2.py", "FAQ = 1\n")
    _freeze("C007", "代码类重命名 faq-v2.txt → faq_v2.py")
    out, code = _gate()
    check("S: S7 重命名涉及代码类（删 .txt + 增 .py）→ **仍报** P*，提示点名 faq_v2.py",
          code == 0 and "缺执行线程侧 P* 证据" in out and "faq_v2.py" in out, out[-900:])

    # ---- 判据本体（纯函数 + 临时目录造 manifest）：R01 点名的 8 个边界 ----
    # 为什么要这段：端到端两条只覆盖「文档类 / 代码类」；删除、重命名、空 sha、`!!js`、
    # 数值序、scope 差、反向守门都只能在函数层压测（真实数据里 deleted 恒为 0）。
    probe3 = ROOT / "c007-delta-probe.py"
    write(probe3, '''import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import dsh_flow as f

root = Path(sys.argv[2])
base = root / "docs" / "feat"
rel = base / "releases"
out = {}


def mk(cid, arts, scope=None):
    d = rel / cid
    (d / "files").mkdir(parents=True, exist_ok=True)
    m = {"schema": "dsh-flow/candidate@1", "candidate": cid, "artifacts": arts}
    if scope is not None:
        m["scope"] = scope
    (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


def art(path, sha):
    return {"path": path, "sha256": sha, "bytes": 1}


def put(cid, path, text):
    p = rel / cid / "files" / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# 四态：无 prev / 零变更 / 只改 md / 改 py
mk("C001", [art("a.md", "s1"), art("b.txt", "s2")])
mk("C002", [art("a.md", "s1"), art("b.txt", "s2")])
mk("C003", [art("a.md", "s9"), art("b.txt", "s2")])
mk("C004", [art("a.md", "s9"), art("b.txt", "s2"), art("x.py", "s3")])
out["no_prev"] = list(f._doc_only_delta(base, "C001"))
out["zero"] = list(f._doc_only_delta(base, "C002"))
out["doc_only"] = list(f._doc_only_delta(base, "C003"))
out["code"] = list(f._doc_only_delta(base, "C004"))
out["prev_of_4"] = f._prev_frozen_candidate(base, "C004")

# 删除分支：相对上一候选只删 tools/x.py
mk("C005", [art("a.md", "s9"), art("tools/x.py", "p1")])
mk("C006", [art("a.md", "s9")])
out["deleted_py"] = list(f._doc_only_delta(base, "C006"))

# 重命名三例：文档同 sha 改名 / 改名成 .py / 改名成 .py.bak
mk("C007", [art("b.md", "s9")])
out["rename_doc"] = list(f._doc_only_delta(base, "C007"))
mk("C008", [art("y.py", "s9")])
out["rename_code"] = list(f._doc_only_delta(base, "C008"))
mk("C009", [art("x.py", "p1")])
mk("C010", [art("x.py.bak", "p1")])
out["rename_bak"] = list(f._doc_only_delta(base, "C010"))

# 空 sha 不得当成「未修改」
mk("C011", [art("z.md", "")])
mk("C012", [art("z.md", "")])
out["no_sha"] = list(f._doc_only_delta(base, "C012"))

# !!js 内容覆盖（YAML 嵌真 JS = 运行时行为）
mk("C013", [art("cordis.patch.yml", "q1")])
put("C013", "cordis.patch.yml", "a: 1\\n")
mk("C014", [art("cordis.patch.yml", "q2")])
put("C014", "cordis.patch.yml", "- !!js process.getBuiltinModule(node_path)\\n")
out["js_tag"] = list(f._doc_only_delta(base, "C014"))
mk("C015", [art("cfg.yml", "w1")])
put("C015", "cfg.yml", "a: 1\\n")
mk("C016", [art("cfg.yml", "w2")])
put("C016", "cfg.yml", "a: 2\\n")
out["plain_yml"] = list(f._doc_only_delta(base, "C016"))

# scope 差异：产物数差 > 20 时必须标「可能 scope 不同」
mk("C017", [art("f%02d.md" % i, "h%d" % i) for i in range(30)], scope=["."])
mk("C018", [art("f%02d.md" % i, "h%d" % i) for i in range(5)], scope=["handbook"])
out["scope_diff"] = list(f._doc_only_delta(base, "C018"))

# 数值序（字典序会把 C1000 排到 C101 前面）
b2 = root / "docs" / "seq"
for cid in ("C100", "C101", "C1000"):
    d = b2 / "releases" / cid
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(
        json.dumps({"candidate": cid, "artifacts": [art("a.md", "s")]}), encoding="utf-8")
out["seq_1000"] = f._prev_frozen_candidate(b2, "C1000")
out["seq_101"] = f._prev_frozen_candidate(b2, "C101")

# 真实候选回归（只读冻结件）：C006 必须 True，C001-C004 必须 False
real = Path(sys.argv[3])


def realman(cid):
    return json.loads((real / "releases" / cid / "manifest.json").read_text(encoding="utf-8"))


out["real"] = {c: list(f._doc_only_verdict(realman(c), real, c))
               for c in ("C001", "C002", "C003", "C004", "C005", "C006")}
# 反向守门：把 .json 塞进代码类后，真实 C006 必须变红
f.CODE_SUFFIXES = f.CODE_SUFFIXES + (".json",)
out["real_c006_json_code"] = list(f._doc_only_verdict(realman("C006"), real, "C006"))
print("PROBE_JSON " + json.dumps(out, ensure_ascii=False))
''')
    pr3 = _sp([PY, "-B", str(probe3), str(PKG / "tools"),
                          str(ROOT / "c007-delta-probe-root"),
                          str(PKG / "docs" / "flow-quality-boost")],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    probe3.unlink(missing_ok=True)
    _l3 = [ln for ln in (pr3.stdout or "").splitlines() if ln.startswith("PROBE_JSON ")]
    try:
        pj3 = json.loads(_l3[-1][len("PROBE_JSON "):]) if _l3 else {}
    except ValueError:
        pj3 = {}
    if not pj3:
        pj3 = {"probe_error": (pr3.stdout or "") + (pr3.stderr or "")}
    _raw3 = json.dumps(pj3, ensure_ascii=False)[:900]

    def _v(key):
        return (pj3.get(key) or [None, "", ""])[0]

    def _r(key):
        return str((pj3.get(key) or ["", "", ""])[1])

    check("S: S8 四态①：首个候选无对照 → None +「回退全量扩展名判据」+ kind=no_prev",
          _v("no_prev") is None and "回退全量扩展名判据" in _r("no_prev")
          and (pj3.get("no_prev") or ["", "", ""])[2] == "no_prev", _raw3)
    check("S: S9 四态②：产物集逐字节相同 → None +「零变更」+ kind=zero（**不是** False）",
          _v("zero") is None and "零变更" in _r("zero")
          and (pj3.get("zero") or ["", "", ""])[2] == "zero", _raw3)
    check("S: S10 四态③：只改 1 个 .md → True +「代码类 0 个」+ kind=delta",
          _v("doc_only") is True and "代码类 0 个" in _r("doc_only")
          and (pj3.get("doc_only") or ["", "", ""])[2] == "delta", _raw3)
    check("S: S11 四态④：新增 1 个 .py → False +「代码类 1 个（如 x.py）」",
          _v("code") is False and "代码类 1 个" in _r("code"), _raw3)
    check("S: S12 删除分支：只删 tools/x.py（新增 0 / 修改 0）→ False + 文案含「删除 1」",
          _v("deleted_py") is False and "删除 1" in _r("deleted_py")
          and "tools/x.py" in _r("deleted_py"), _raw3)
    check("S: S13 重命名①：a.md → b.md（同 sha256）→ True +「重命名 1」（不混进「删除」）",
          _v("rename_doc") is True and "重命名 1" in _r("rename_doc")
          and "删除 0" in _r("rename_doc"), _raw3)
    check("S: S14 重命名②：b.md → y.py（同 sha256，新侧代码类）→ False",
          _v("rename_code") is False and "y.py" in _r("rename_code"), _raw3)
    check("S: S15 重命名③：x.py → x.py.bak（旧侧代码类，保守方向）→ False",
          _v("rename_bak") is False, _raw3)
    check("S: S16 空 sha256 不得当成「未修改」→ None +「sha256 缺失」+ kind=no_sha",
          _v("no_sha") is None and "sha256 缺失" in _r("no_sha")
          and (pj3.get("no_sha") or ["", "", ""])[2] == "no_sha", _raw3)
    check("S: S17 `!!js` 内容覆盖：改含真 JS 的 cordis.patch.yml（扩展名是 .yml）→ False + 文案含「!!js」",
          _v("js_tag") is False and "!!js" in _r("js_tag"), _raw3)
    check("S: S18 反样本：改不含 `!!js` 的普通 cfg.yml → True（内容层不误伤配置）",
          (pj3.get("plain_yml") or [None])[0] is True, _raw3)
    check("S: S19 scope 差异（产物数差 25 > 20）→ 文案标「可能 scope 不同，结论仅供参考」",
          "可能 scope 不同" in _r("scope_diff"), _raw3)
    check("S: S20 `_prev_frozen_candidate` 按**数值**序：C1000 的 prev 是 C101（字典序会错成 C100）"
          "、C004 的 prev 是 C003",
          pj3.get("seq_1000") == "C101" and pj3.get("seq_101") == "C100"
          and pj3.get("prev_of_4") == "C003", _raw3)

    _real = pj3.get("real") or {}

    def _rv(cid):
        return (_real.get(cid) or [None, "", ""])[0]

    def _rr(cid):
        return str((_real.get(cid) or ["", "", ""])[1])

    check("S: S21 真实回归（最值钱）：C005 / C006 判 **True**（文档类），"
          "C001–C004 判 **False**（代码候选）",
          _rv("C005") is True and _rv("C006") is True
          and all(_rv(c) is False for c in ("C001", "C002", "C003", "C004")),
          json.dumps(_real, ensure_ascii=False)[:900])
    check("S: S22 真实 C006 的文案含「变更集 6 个文件」「代码类 0 个」「判据：变更集」",
          "变更集 6 个文件" in _rr("C006") and "代码类 0 个" in _rr("C006")
          and "判据：变更集" in _rr("C006"), _rr("C006"))
    check("S: S23 真实 C001 走回退（kind=fallback、文案含「回退全量扩展名判据」）",
          (_real.get("C001") or ["", "", ""])[2] == "fallback"
          and "回退全量扩展名判据" in _rr("C001"), _rr("C001"))
    check("S: S24 **反向守门**：把 .json 塞进 CODE_SUFFIXES 后，真实 C006 必须变红（False）"
          "——证明 S21 的 True 真绑在判据上，不是「恰好没触发」",
          _v("real_c006_json_code") is False
          and "package.json" in _r("real_c006_json_code"), _raw3)


def suite_t():
    """flow-backup-a：seal 后异地快照（E1–E5）。

    **全部落 TEMP**：`--backup-dir` 显式指向 `ROOT/t-backup`，绝不写真实
    `%USERPROFILE%\\.dsh\\flow-snapshots`（自测污染真实副本目录是最忌讳的事之一）。
    顺序有意为之：E5 的两条断言（正常 ✅ / 篡改 ⚠）必须在第二次 seal 之前跑——
    重跑 seal 会重写 `verification.json`（`sealed_at` 变），副本与项目内必然不再一致，
    那时再断言「正常 ✅」就成了假通过。
    """
    PROJ = ROOT / "backup-proj"
    DEV = ROOT / "backup-proj-dev"
    BK = ROOT / "t-backup"
    (PROJ / "src").mkdir(parents=True)
    (DEV / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    write(DEV / "src" / "a.py", "x = 2\n")
    P = ["-p", str(PROJ), "-f", "bk"]

    # ---- T1：BACKUP_ROOT 默认值 + 环境变量覆盖（子进程里测，避免被本进程 env 带偏）----
    probe = "import sys; sys.path.insert(0, sys.argv[1]); import dsh_flow as f; print(f.BACKUP_ROOT)"
    env_clean = {k: v for k, v in os.environ.items() if k != "FLOW_BACKUP_ROOT"}
    p1 = _sp([PY, "-B", "-c", probe, str(PKG / "tools")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env_clean)
    d1 = (p1.stdout or "").strip()
    want_default = str(Path.home() / ".dsh" / "flow-snapshots")
    check("T: T1 未设 FLOW_BACKUP_ROOT 时 BACKUP_ROOT = <用户目录>\\.dsh\\flow-snapshots",
          p1.returncode == 0 and d1 == want_default, f"got={d1!r} want={want_default!r}")
    p2 = _sp([PY, "-B", "-c", probe, str(PKG / "tools")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        env=dict(env_clean, FLOW_BACKUP_ROOT=str(ROOT / "ov-root")))
    d2 = (p2.stdout or "").strip()
    check("T: T1 环境变量 FLOW_BACKUP_ROOT 可覆盖 BACKUP_ROOT（不是写死常量）",
          d2 == str(ROOT / "ov-root"), f"got={d2!r}")

    # ---- 造一个能 seal 的最小候选 ----
    run("T: init", "init", *P, "--scope", "src", "--no-graph")
    run("T: baseline", "baseline", *P)
    docs = PROJ / "docs" / "bk"
    write_design(docs)
    run("T: DESIGN -> PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    write_plan(docs)
    run("T: PLAN -> EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")
    run("T: freeze C001", "freeze", *P, "--id", "C001", "--from", str(DEV),
        "--scope", "src", "--actor", "executor")
    run("T: EXECUTING -> VERIFYING", "advance", *P, "--to", "VERIFYING", "--actor", "executor")
    write_report(docs)

    out, code = capture("seal", *P, "--id", "C001", "--backup-dir", str(BK))
    check("T: seal 打印快照根与来源（--backup-dir 生效，便于事后复核写到哪）",
          code == 0 and "异地快照根" in out and "--backup-dir" in out, out[-800:])

    # ---- E1：快照目录 + 三件齐全 ----
    snap_root = BK / PROJ.name / "bk"
    snaps = sorted(snap_root.glob("C001-*")) if snap_root.is_dir() else []
    snap = snaps[-1] if snaps else None
    check("T: E1 seal 后生成 <root>/<项目目录名>/<feature>/C001-<时间戳>/",
          snap is not None and snap.is_dir(), f"snaps={[p.name for p in snaps]}")
    check("T: E1 快照里 manifest.json / verification.json / files/ 三件齐全（在 releases/<C>/ 下）",
          snap is not None and all((snap / "releases" / "C001" / n).exists() for n in
                                   ("manifest.json", "verification.json", "files")),
          "\n".join(sorted(p.name for p in snap.iterdir())) if snap else "无快照")

    # ---- E2：副本与原件逐字节一致（manifest / verification / files/** 递归）----
    pairs = [docs / "releases" / "C001" / "manifest.json",
             docs / "releases" / "C001" / "verification.json"]
    pairs += [p for p in sorted((docs / "releases" / "C001" / "files").rglob("*")) if p.is_file()]
    diff: "list[str]" = []
    if snap is not None:
        for p in pairs:
            rel = p.relative_to(docs).as_posix()
            cp = snap / rel
            if not cp.is_file():
                diff.append(f"{rel}: 副本缺件")
            elif (hashlib.sha256(p.read_bytes()).hexdigest()
                  != hashlib.sha256(cp.read_bytes()).hexdigest()):
                diff.append(f"{rel}: 哈希不一致")
    check("T: E2 副本与原件逐字节一致（manifest/verification/files/** 全部 sha256 相等）",
          snap is not None and bool(pairs) and not diff,
          f"比对 {len(pairs)} 个文件；差异={diff[:5]}")

    # ---- E5-a：doctor 正常态 ✅ ----
    env_saved = os.environ.get("FLOW_BACKUP_ROOT")
    os.environ["FLOW_BACKUP_ROOT"] = str(BK)      # doctor 读的是 BACKUP_ROOT，与 --backup-dir 同一目录
    try:
        out_d1, code_d1 = capture("doctor", *P)
    finally:
        if env_saved is None:
            os.environ.pop("FLOW_BACKUP_ROOT", None)
        else:
            os.environ["FLOW_BACKUP_ROOT"] = env_saved
    check("T: E5-a doctor 正常态：备份根可写 + 两份凭证与项目内一致（exit 0）",
          code_d1 == 0 and "备份根存在且可写" in out_d1
          and "manifest.json: ✅" in out_d1 and "verification.json: ✅" in out_d1,
          out_d1[-900:])

    # ---- E5-b：在副本里改 1 字节 → doctor 必须 ⚠ 且仍 exit 0 ----
    copy_manifest = (snap / "releases" / "C001" / "manifest.json") if snap else None
    orig = copy_manifest.read_bytes() if copy_manifest and copy_manifest.is_file() else b""
    sha_before = hashlib.sha256(orig).hexdigest() if orig else ""
    out_d2, code_d2 = "", 0
    sha_after = ""
    if orig:
        tampered = orig[:-1] + (b" " if orig[-1:] != b" " else b"\n")
        copy_manifest.write_bytes(tampered)
        sha_after = hashlib.sha256(copy_manifest.read_bytes()).hexdigest()
        os.environ["FLOW_BACKUP_ROOT"] = str(BK)
        try:
            out_d2, code_d2 = capture("doctor", *P)
        finally:
            if env_saved is None:
                os.environ.pop("FLOW_BACKUP_ROOT", None)
            else:
                os.environ["FLOW_BACKUP_ROOT"] = env_saved
    check("T: E5-b 副本改 1 字节后 doctor 报 ⚠ 且退出码仍 0（只告警不阻塞）",
          bool(orig) and sha_after != sha_before and code_d2 == 0
          and "manifest.json: ⚠ 副本已变" in out_d2
          and "verification.json: ✅" in out_d2,
          f"bytes={len(orig)} sha {sha_before[:12]} → {sha_after[:12]}\n" + out_d2[-700:])
    if orig:
        copy_manifest.write_bytes(orig)           # 还原，后面的断言不再受污染
    out_d3, code_d3 = ("", 0)
    if orig:
        os.environ["FLOW_BACKUP_ROOT"] = str(BK)
        try:
            out_d3, code_d3 = capture("doctor", *P)
        finally:
            if env_saved is None:
                os.environ.pop("FLOW_BACKUP_ROOT", None)
            else:
                os.environ["FLOW_BACKUP_ROOT"] = env_saved
    check("T: E5-b 还原副本后 doctor 回到 ✅（证明 ⚠ 真绑在副本哈希上，不是必红文案）",
          bool(orig) and code_d3 == 0 and "manifest.json: ✅" in out_d3, out_d3[-700:])

    # ---- E3：--no-backup 不产生快照（前后目录清单做差，而不是只比计数）----
    before = sorted(p.name for p in snap_root.iterdir() if p.is_dir()) if snap_root.is_dir() else []
    out3, code3 = capture("seal", *P, "--id", "C001", "--no-backup", "--backup-dir", str(BK))
    after = sorted(p.name for p in snap_root.iterdir() if p.is_dir()) if snap_root.is_dir() else []
    check("T: E3 --no-backup 不产生快照（清单前后完全相同）且 seal 仍成功",
          code3 == 0 and "已按 --no-backup 跳过异地快照" in out3 and before == after,
          f"before={before}\nafter ={after}")

    # ---- E4：备份失败不改 seal 结论（不可写目标 → exit 0 + ⚠ + ledger backup-failed）----
    # Z: 不存在时用它（最贴近 V4 的做法）；万一本机真有 Z: 盘，改用「拿普通文件当父目录」制造不可写。
    if Path("Z:/").exists():
        blocker = ROOT / "t-not-a-dir"
        blocker.write_text("x\n", encoding="utf-8")
        bad = blocker / "sub"
        bad_desc = f"{bad}（父路径是普通文件）"
    else:
        bad = Path("Z:/no-such-dir") / f"probe-{os.getpid()}"
        bad_desc = f"{bad}（Z: 盘不存在）"
    out4, code4 = capture("seal", *P, "--id", "C001", "--backup-dir", str(bad))
    ledger = (docs / "ledger.md").read_text(encoding="utf-8-sig", errors="replace")
    check("T: E4 快照失败不打红 seal：exit 0 + 打印 ⚠ 快照失败 + ledger 记 backup-failed",
          code4 == 0 and "⚠ 快照失败" in out4 and "backup-failed" in ledger,
          f"目标 {bad_desc}\n" + out4[-900:])
    check("T: E4 反向：确实走到了备份分支（打印了异地快照根）且目标目录未被创建",
          "异地快照根" in out4 and bad.as_posix() in out4 and not bad.is_dir(),
          f"bad.is_dir()={bad.is_dir()}\n" + out4[-600:])
    verif = docs / "releases" / "C001" / "verification.json"
    after4 = sorted(p.name for p in snap_root.iterdir() if p.is_dir()) if snap_root.is_dir() else []
    check("T: E4 失败时 TEMP 快照目录数不变（不留半成品目录），且 verification.json 仍正常生成",
          after4 == before and verif.is_file(), f"before={before} after={after4}")
    # C002 / D-02：失败分支还必须**不留 `.partial-<pid>` 临时目录**（半成品副本的新形态）。
    stray = sorted(x.name for x in snap_root.rglob("*partial*")) if snap_root.is_dir() else []
    check("T: D-02 备份失败后快照根下没有 .partial-* 残留（临时名只在中途存在）",
          stray == [], str(stray[:5]))
    out5, code5 = capture("verify", *P, "--id", "C001")
    check("T: E4 备份失败后 verify 仍通过（封存结论未被保险失败污染）",
          code5 == 0 and "封存校验通过" in out5, out5[-700:])


def suite_u():
    """flow-backup-a C002 缺陷回归（只修不加功能，对应 ACCEPTANCE §二的 D-02 / D-03 / D-04）。

    D-02 `_backup_snapshot` 原子化：临时名 copytree → os.replace；中途失败不留最终名、
          不留 `.partial-*`，重跑自愈；同一秒重跑仍幂等（冻结时钟，不靠运气）。
    D-03 `doctor --backup-dir`：与 `seal --backup-dir` 对称，且**最新副本**也从该根读
          （只换显示不换数据源的话，doctor 等于还是看不见自定义根）。
    D-04 `selftest.py --help`：退出码 0、打印用法、**不跑任何用例**。
    """
    # ---------- D-04：`selftest.py --help` 只看用法、不开跑 ----------
    p = _sp([PY, str(PKG / "tools" / "selftest.py"), "--help"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out_h = (p.stdout or "") + (p.stderr or "")
    check("U: D-04 selftest.py --help 退出码 0（以前会被当成无参数直接开跑）",
          p.returncode == 0, out_h[:600])
    check("U: D-04 --help 输出用法，且写明「不加参数即全量」",
          "用法" in out_h and "不加参数即全量" in out_h and "全部用例" in out_h, out_h[:600])
    check("U: D-04 --help 没有执行任何用例（无 `=== A:` 套件头、无 total/failed 汇总行）",
          not re.search(r"(?m)^=== [A-Z]: ", out_h)
          and not re.search(r"(?m)^total=\d+ failed=\d+$", out_h), out_h[-600:])

    # 模块内直接调 `_backup_snapshot`：D-02 的失败窗口（copytree 中途抛错）只能靠单元级模拟，
    # CLI 那条路径（不存在的盘符）在 suite_t E4 已经端到端覆盖过了。
    import contextlib
    import importlib.util
    import io

    spec = importlib.util.spec_from_file_location("dsh_flow_c002_probe", FLOW)
    flow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(flow)          # 只导入常量/函数，不触发 main()

    PROJ = ROOT / "u-atomic-proj"
    write(PROJ / "docs" / "atomic" / "DESIGN.md", "# DESIGN\n\nx\n")
    write(PROJ / "docs" / "atomic" / "releases" / "C001" / "manifest.json", "{}\n")
    BK = ROOT / "u-atomic-backup"
    parent = BK / PROJ.name / "atomic"

    real_copytree = shutil.copytree

    def _boom(src, dst, *a, **k):
        """模拟磁盘满：先把临时目录建出来、写半份内容，再抛 OSError(ENOSPC)。"""
        Path(dst).mkdir(parents=True, exist_ok=True)
        (Path(dst) / "half-copy.txt").write_text("half\n", encoding="utf-8")
        raise OSError(28, "No space left on device (simulated)")

    got_fail = "unset"
    try:
        flow.shutil.copytree = _boom      # flow.shutil 就是全局 shutil：只在这一段临时替换
        got_fail = flow._backup_snapshot(PROJ, "atomic", "C001", BK)
    finally:
        flow.shutil.copytree = real_copytree
    partials = sorted(x.name for x in parent.glob("*partial*")) if parent.is_dir() else []
    finals = sorted(x.name for x in parent.glob("C001-*")) if parent.is_dir() else []
    check("U: D-02 中途失败返回 None，且不留 .partial-* 临时目录（临时名只在中途存在）",
          got_fail is None and partials == [], f"got={got_fail!r} partials={partials}")
    check("U: D-02 中途失败后最终名不存在（下次 seal 会重试，不会命中「已存在，跳过」把残片当成品）",
          finals == [], f"finals={finals}")

    # 失败后重跑（正常 copytree）：必须自愈
    got_ok = flow._backup_snapshot(PROJ, "atomic", "C001", BK)
    partials2 = sorted(x.name for x in parent.glob("*partial*")) if parent.is_dir() else []
    finals2 = sorted(x.name for x in parent.glob("C001-*")) if parent.is_dir() else []
    check("U: D-02 失败后重跑能自愈（最终目录生成、.partial-* 清零）",
          got_ok is not None and got_ok.is_dir() and partials2 == [] and len(finals2) == 1,
          f"got={got_ok} partials={partials2} finals={finals2}")
    check("U: D-02 原子落地的是完整副本（DESIGN.md 与 releases/C001/manifest.json 都在，不是空壳）",
          got_ok is not None
          and (got_ok / "DESIGN.md").is_file()
          and (got_ok / "releases" / "C001" / "manifest.json").is_file(),
          str(sorted(x.name for x in got_ok.iterdir())) if got_ok is not None else "无快照")

    # 幂等不变：同一秒/同一候选重跑 → 命中「快照已存在，跳过」，不重复创建、不覆盖。
    # 时钟冻结成同一秒，否则这条断言就得靠「两次调用恰好落在同一秒内」——那是 flaky 不是证据。
    BK2 = ROOT / "u-atomic-backup-idem"
    real_dt = flow.datetime

    class _Frozen(real_dt):                        # type: ignore[misc,valid-type]
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 11, 22, 7, 30, 0, tzinfo=tz)

    buf2 = io.StringIO()
    a1 = a2 = None
    try:
        flow.datetime = _Frozen
        with contextlib.redirect_stdout(io.StringIO()):
            a1 = flow._backup_snapshot(PROJ, "atomic", "C001", BK2)
        with contextlib.redirect_stdout(buf2):
            a2 = flow._backup_snapshot(PROJ, "atomic", "C001", BK2)
    finally:
        flow.datetime = real_dt
    idem_parent = BK2 / PROJ.name / "atomic"
    names = sorted(x.name for x in idem_parent.iterdir()) if idem_parent.is_dir() else []
    check("U: D-02 幂等不变（同一秒重跑 → 打印「快照已存在，跳过」，目录只有一份）",
          a1 is not None and a2 == a1 and a2.name == "C001-20261122-073000"
          and "快照已存在，跳过" in buf2.getvalue() and names == ["C001-20261122-073000"],
          f"names={names}\n{buf2.getvalue()[:400]}")

    # ---------- D-03：doctor 与 seal 对称 ----------
    d_alt = ROOT / "u-doctor-alt-root"
    (d_alt / PROJ.name / "atomic" / "C001-20261122-073000").mkdir(parents=True, exist_ok=True)
    out_d, code_d = capture("doctor", "-p", str(PROJ), "-f", "atomic", "--backup-dir", str(d_alt))
    line = next((ln for ln in out_d.splitlines() if ln.startswith("snapshot :")), "")
    env_root = (ROOT / "flow-snapshots").as_posix()   # doctor 打印用 as_posix，断言必须同形
    check("U: D-03 doctor 接受 --backup-dir 并显示该根与来源（--backup-dir）",
          code_d == 0 and d_alt.as_posix() in line and "--backup-dir" in line
          and env_root not in line, f"{line}\n{out_d[-400:]}")
    check("U: D-03 doctor --backup-dir 时「最新副本」也读该根（换了数据源，不只换了显示）",
          f"最新副本：{PROJ.name}/atomic/C001-20261122-073000" in out_d, out_d[-700:])
    out_d2, code_d2 = capture("doctor", "-p", str(PROJ), "-f", "atomic")
    line2 = next((ln for ln in out_d2.splitlines() if ln.startswith("snapshot :")), "")
    check("U: D-03 不带 --backup-dir 时仍读环境变量 FLOW_BACKUP_ROOT（C001 的旧行为不变）",
          code_d2 == 0 and env_root in line2 and "环境变量 FLOW_BACKUP_ROOT" in line2, line2)


def suite_v():
    """flow-backup-a C003 缺陷回归（只修不加功能，对应 ACCEPTANCE §二 D-06 / D-07）。

    D-06 TEMP 泄漏：`ROOT` 必须在本进程退出前被删掉。父进程自己的根要留到最后（不能边跑边删），
          所以全部用**子进程**验真实退出路径：
            1) 正常路径：`main()` 正常返回 → `finally` 清理；
            2) 未捕获异常：`main()` 抛错 → `finally` 清理（异常照旧向上抛）；
            3) `atexit` 兜底：`finally` 之后再有人把根建回来 → 进程退出时 atexit 再清一次；
            4) 前缀双重校验：名字不带 `dsh-flow-selftest-` 的目录绝不被清理逻辑碰；
            5) `--help` 路径不清理（不注册 atexit、不碰任何目录）。
    D-07 `__pycache__` 污染：本进程 `sys.dont_write_bytecode` 必须为 True；再在 TEMP 里复制一份
          `tools/{selftest,dsh_flow}.py` 镜像，起子进程照 suite U 的方式用 `importlib` 载入，
          断言镜像里没有生成 `__pycache__`（真实 `tools/` 完全不受影响，也顺带证明没新增缓存）。
    """
    selftest_src = PKG / "tools" / "selftest.py"
    child_env = dict(os.environ, PYTHONIOENCODING="utf-8")
    # 子进程要 `importlib` 载入 selftest.py 本体。直接载**真文件**的话，它自己的 `.pyc` 会在
    # 模块顶层代码执行**之前**就写进真实的 `tools/__pycache__`（import 机器先编译缓存、再执行
    # 模块体，`sys.dont_write_bytecode = True` 那一行来不及生效）——等于探针自己违反 D-07。
    # 所以复制一份到 ROOT 下再用：代码逐字节相同，产出的 pyc 落在 ROOT 里，随收尾一起删掉。
    probe_copy = ROOT / "v-probe" / "tools" / "selftest.py"
    probe_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(selftest_src, probe_copy)

    def _run_child(code: str, *extra):
        p = _sp([PY, "-c", code, str(probe_copy), *[str(x) for x in extra]],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=child_env)
        return (p.stdout or "") + (p.stderr or ""), p.returncode

    def _grab(out: str, key: str) -> str:
        m = re.search(rf"(?m)^{key}=(.*)$", out)
        return m.group(1).strip() if m else ""

    _load_m = (
        "import importlib.util, sys\n"
        "spec = importlib.util.spec_from_file_location('st_v', sys.argv[1])\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
    )

    # ---- D-06 路径 1：正常返回 → finally 清理 ----
    out1, code1 = _run_child(
        _load_m
        + "def fake_main():\n"
        "    m.ROOT.mkdir(parents=True, exist_ok=True)\n"
        "    (m.ROOT / 'fixture-marker.txt').write_text('x', encoding='utf-8')\n"
        "    return 0\n"
        "m.main = fake_main\n"
        "rc = m._run_cli([])\n"
        "print('ROOT=%s' % m.ROOT)\n"
        "print('RC=%d' % rc)\n"
        "print('EXISTS_AFTER=%s' % m.ROOT.exists())\n"
        "sys.exit(0 if rc == 0 and not m.ROOT.exists() else 3)\n")
    root1 = Path(_grab(out1, "ROOT")) if _grab(out1, "ROOT") else None
    check("V: D-06 正常跑完（finally）后本进程的 TEMP fixture 根被删除",
          code1 == 0 and _grab(out1, "EXISTS_AFTER") == "False"
          and root1 is not None and not root1.exists(), out1[-600:])
    check("V: D-06 被清理的目录名带 dsh-flow-selftest- 前缀（删的是自己的根，不是别人的）",
          root1 is not None and root1.name.startswith("dsh-flow-selftest-"),
          str(root1))

    # ---- D-06 路径 2：main() 抛未捕获异常 → finally 清理 ----
    out2, code2 = _run_child(
        _load_m
        + "def fake_main():\n"
        "    m.ROOT.mkdir(parents=True, exist_ok=True)\n"
        "    (m.ROOT / 'boom.txt').write_text('x', encoding='utf-8')\n"
        "    raise RuntimeError('boom (simulated crash)')\n"
        "m.main = fake_main\n"
        "try:\n"
        "    m._run_cli([])\n"
        "except RuntimeError:\n"
        "    print('ROOT=%s' % m.ROOT)\n"
        "    print('CLEANED=%s' % (not m.ROOT.exists()))\n"
        "    sys.exit(0 if not m.ROOT.exists() else 4)\n"
        "print('NO_RAISE')\n"
        "sys.exit(5)\n")
    check("V: D-06 用例抛未捕获异常时也清理（先清、再把异常抛出去）",
          code2 == 0 and _grab(out2, "CLEANED") == "True", out2[-600:])

    # ---- D-06 路径 3：atexit 兜底（finally 之后再建根，退出时仍要清） ----
    out3, code3 = _run_child(
        _load_m
        + "m.main = lambda: 0\n"
        "rc = m._run_cli([])\n"
        "m.ROOT.mkdir(parents=True, exist_ok=True)\n"
        "(m.ROOT / 'late-marker.txt').write_text('x', encoding='utf-8')\n"
        "print('ROOT=%s' % m.ROOT)\n"
        "print('EXISTS_BEFORE_EXIT=%s' % m.ROOT.exists())\n"
        "sys.exit(0)\n")
    root3 = Path(_grab(out3, "ROOT")) if _grab(out3, "ROOT") else None
    check("V: D-06 atexit 兜底生效：finally 之后再出现的根，进程退出时也被清掉",
          code3 == 0 and _grab(out3, "EXISTS_BEFORE_EXIT") == "True"
          and root3 is not None and not root3.exists(), out3[-600:])

    # ---- D-06 路径 4：前缀双重校验（不带前缀的目录绝不删） ----
    victim = ROOT / "v-guard-not-a-fixture"
    victim.mkdir(parents=True, exist_ok=True)
    (victim / "keep.txt").write_text("keep\n", encoding="utf-8")
    out4, code4 = _run_child(
        "import importlib.util, sys\n"
        "from pathlib import Path\n"
        "spec = importlib.util.spec_from_file_location('st_vg', sys.argv[1])\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "victim = Path(sys.argv[2])\n"
        "m.ROOT = victim\n"
        "m.cleanup_root()\n"
        "print('GUARD_KEPT=%s' % victim.is_dir())\n"
        "sys.exit(0 if victim.is_dir() else 6)\n", victim)
    check("V: D-06 清理前校验目录名前缀：名字不符的目录即使被指成 ROOT 也不删",
          code4 == 0 and _grab(out4, "GUARD_KEPT") == "True" and victim.is_dir(), out4[-600:])

    # ---- D-06 路径 5：--help 不清理、不注册 atexit ----
    help_victim = ROOT / f"dsh-flow-selftest-{os.getpid()}-helpprobe"
    help_victim.mkdir(parents=True, exist_ok=True)
    out5, code5 = _run_child(
        "import importlib.util, sys\n"
        "from pathlib import Path\n"
        "spec = importlib.util.spec_from_file_location('st_vh', sys.argv[1])\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "victim = Path(sys.argv[2])\n"
        "m.ROOT = victim\n"
        "rc = m._run_cli(['--help'])\n"
        "print('RC=%d' % rc)\n"
        "print('KEPT=%s' % victim.is_dir())\n"
        "sys.exit(0 if rc == 0 and victim.is_dir() else 7)\n", help_victim)
    check("V: D-06 --help 路径不清理任何目录（只看用法，不碰 TEMP）",
          code5 == 0 and _grab(out5, "KEPT") == "True" and help_victim.is_dir()
          and "用法" in out5, out5[-600:])

    # ---- D-07：本进程关掉字节码写入 ----
    check("V: D-07 本进程 sys.dont_write_bytecode=True（suite U 的 importlib 载入不再写 .pyc）",
          sys.dont_write_bytecode is True, f"dont_write_bytecode={sys.dont_write_bytecode!r}")

    mirror = ROOT / "v-d07-mirror"
    (mirror / "tools").mkdir(parents=True, exist_ok=True)
    shutil.copy2(selftest_src, mirror / "tools" / "selftest.py")
    shutil.copy2(FLOW, mirror / "tools" / "dsh_flow.py")
    # argv[1] 永远是真实 selftest.py（`_run_child` 固定塞的）；mirror 的两个文件排在后面。
    # 只断言 `dsh_flow*.pyc`：探针自己 import 镜像里的 selftest.py 时，**它自己的** pyc 会先落地
    # （import 机器在模块顶层代码执行前就编译缓存），那是探针产物、不是真实运行的产物
    # （真实运行里 selftest.py 是脚本入口，根本不产生缓存）。要防的是 `dsh_flow*.pyc`。
    out6, code6 = _run_child(
        "import importlib.util, sys\n"
        "spec = importlib.util.spec_from_file_location('st_vd7', sys.argv[2])\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "print('DONT_WRITE=%s' % sys.dont_write_bytecode)\n"
        "spec2 = importlib.util.spec_from_file_location('dsh_flow_d07', sys.argv[3])\n"
        "fm = importlib.util.module_from_spec(spec2)\n"
        "spec2.loader.exec_module(fm)\n"
        "print('LOADED=%s' % hasattr(fm, 'parse_evidence'))\n"
        "sys.exit(0)\n",
        mirror / "tools" / "selftest.py", mirror / "tools" / "dsh_flow.py")
    mirror_cache = mirror / "tools" / "__pycache__"
    flow_pyc = sorted(p.name for p in mirror_cache.glob("dsh_flow*.pyc")) if mirror_cache.is_dir() else []
    check("V: D-07 importlib 载入 dsh_flow 后镜像里没有 dsh_flow*.pyc（子进程真实验证）",
          code6 == 0 and _grab(out6, "DONT_WRITE") == "True"
          and _grab(out6, "LOADED") == "True" and flow_pyc == [],
          out6[-600:] + f"\nflow_pyc={flow_pyc} cache={mirror_cache}")

    real_cache = PKG / "tools" / "__pycache__"
    now_names = tuple(sorted(p.name for p in real_cache.glob("*"))) if real_cache.is_dir() else ()
    check("V: D-07 真实 tools/__pycache__ 与开跑前一致（本进程没新增任何缓存文件）",
          now_names == TOOLS_PYCACHE_BASELINE,
          f"before={TOOLS_PYCACHE_BASELINE} now={now_names}")


def _wants_help(argv) -> bool:
    """C002 / D-04：`--help` / `-h` 必须**只看用法、不开跑**。

    以前没有这个分支：`selftest.py --help` 会被当成「无参数」直接跑完全部 400+ 断言，
    排障时想看用法反而要吃满几分钟（验证线程试探时被截断过一次）。
    """
    return any(a in ("-h", "--help") for a in argv)


USAGE = """用法：python tools/selftest.py            跑全部用例（不加参数即全量）
      python tools/selftest.py --help, -h    只打印本用法，不执行任何用例
      python tools/selftest.py --list-suites 只列出可用套件名（A–Y，无 F/O），不跑任何用例
      python tools/selftest.py --suite j     只跑 J 套（可重复给，也可写成 --suite j,y）

不带参数时跑全套端到端自测（A B C D E G H I J K L M N P Q R S T U V W X Y），
临时 fixture 落在 %TEMP%\\dsh-flow-selftest-<pid>\\（按 pid 隔离，可与另一个 selftest 并发），
跑完自动删除该目录（正常退出与未捕获异常都会清；被强杀时不保证，见 suite V）。

子进程超时：每处子进程默认 180 秒，可用环境变量 DSH_SELFTEST_TIMEOUT 覆盖（单位秒）。
超时只把那条断言记成 FAIL，不中断整轮 total=/failed= 汇总、也不会抛 traceback。

退出码：0 = 全部通过（打印 total=<n> failed=0）；1 = 有失败用例（逐条列 FAIL）；
        2 = 参数错（套件名不存在 / 没给套件名），此时只打印可用套件列表、不跑用例。
"""


SUBPROCESS_TIMEOUT = int(os.environ.get("DSH_SELFTEST_TIMEOUT", "180"))


def _sp(cmd, **kw):
    """统一的子进程调用点：默认补上 `timeout=SUBPROCESS_TIMEOUT`，超时**不抛异常**。

    selftest-perf E1-1：本文件原有 17 处裸的子进程调用全都没有超时——某个外部命令
    一旦挂住（node 卡在 watch、PS 解析器碰上网络盘、某个 flow 子命令等锁），整轮自测会被
    无界拖住，排障时谁也说不清是「慢」还是「死」。现在全部收口到这一个包装：默认 180 秒
    （实测最慢的单条检查约 6 秒，30 倍余量），可用环境变量 `DSH_SELFTEST_TIMEOUT` 覆盖。
    调用方原有的 kwargs（`capture_output` / `text` / `encoding` / `errors` / `cwd` / `env`）
    一律原样透传，判据一条不动。

    超时为什么**返回假的 `CompletedProcess`** 而不是把 `TimeoutExpired` 抛给调用方：
    17 处调用方全都在用 `p.returncode` / `p.stdout` 做断言，异常一路冒到顶层会让整轮
    `total=/failed=` 汇总直接消失（进程以 traceback 退出，退出码也不是约定的 1）。
    这里返回 `returncode=-9` + stderr 写明超时，调用方那条断言于是**自然判 FAIL**、
    照常计入汇总——该红的地方仍然红，只是不再连累整轮。
    """
    kw.setdefault("timeout", SUBPROCESS_TIMEOUT)
    try:
        return subprocess.run(cmd, **kw)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, -9, "", f"<TIMEOUT {SUBPROCESS_TIMEOUT}s>")


def _print_suites(stream=None) -> None:
    """打印可用套件清单（`--list-suites` 与「套件名非法」两条路径共用同一份输出）。"""
    out = stream or sys.stdout
    keys = list(SUITES)
    print(f"可用套件（{len(keys)} 个，A–Y，无 F/O）：", file=out)
    for k in keys:
        print(f"  {k.upper()}  {SUITES[k].__name__}", file=out)


def _parse_suite_args(argv):
    """解析 `--suite X`（可重复）/ `--suite x,y`，返回 `(选中的 key 列表 或 None, 非法名列表, 缺值标志)`。

    返回 `None` 表示「argv 里根本没有 `--suite`」——这条路径必须继续跑**全量**、行为与改前
    逐字节一致（suite V 的探针会把 `main` 换成假函数再调 `_run_cli([])`，所以全量路径连
    实参都不许传，见 `_run_cli`）。
    校验就在这一处：不在 `SUITES` 里的名字一律进 `bad`，由 `_run_cli` 打印清单并退出 2
    （参数错 ≠ 用例失败，两者的退出码必须分得开）。
    """
    keys = None
    bad = []
    missing = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--suite":
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                missing = True
                i += 1
                continue
            raw = argv[i + 1]
            i += 2
        elif a.startswith("--suite="):
            raw = a.split("=", 1)[1]
            i += 1
        else:
            i += 1
            continue
        if keys is None:
            keys = []
        for part in raw.split(","):
            name = part.strip().lower()
            if not name:
                continue
            if name in SUITES:
                if name not in keys:
                    keys.append(name)       # 去重；最终执行顺序由 SUITES 决定，不看输入顺序
            elif name not in bad:
                bad.append(name)
    return keys, bad, missing


def cleanup_root() -> bool:
    """删掉本进程的 TEMP fixture 根（`%TEMP%\\dsh-flow-selftest-<pid>`），返回删完是否真的不存在。

    C003 / D-06 的**唯一**清理点。此前整个 selftest 没有删 `ROOT` 的代码（只有 suite_i/j 几处
    探针根），实测每跑一次留一个目录，累计 80 个 / 113 MB。
    - 目录名必须带 `dsh-flow-selftest-` 前缀才删：TEMP 被改到别处时也绝不误删不相干目录。
    - `ignore_errors=True`：Windows 上目录可能被子进程/杀软短暂占用，清不掉是「脏」不是「失败」，
      不能让退出码变红。
    - 兜得住正常退出与未捕获异常（`finally` + `atexit`）；`SIGKILL` / 任务管理器强杀不执行
      `finally` 也不跑 `atexit`，仍会留一个目录——已知边界，可接受（ACCEPTANCE 已记录）。
    - 可重复调用：目录已不在时是无副作用的 no-op（`atexit` 会在 `finally` 之后再调一次）。
    """
    try:
        if ROOT.name.startswith("dsh-flow-selftest-") and ROOT.is_dir():
            shutil.rmtree(ROOT, ignore_errors=True)
    except OSError:
        pass
    return not ROOT.exists()


def _run_cli(argv) -> int:
    """命令行入口：`--help` 只看用法；`--list-suites` 只列套件；`--suite` 选套；其余跑全量。

    **唯一出口都过 `cleanup_root()`**（除两条不建 fixture 根、不该碰目录的只读路径）。
    `--help` / `--list-suites` 明确不注册 `atexit`、也不清理（它们不建 TEMP 根）。
    真正开跑时才注册 `atexit`：`finally` 负责正常与异常路径，`atexit` 兜「`finally` 之后再有人
    把根建回来」这类边角（suite V 的三条子进程探针分别覆盖正常 / 异常 / atexit 路径）。

    分流顺序（`--help` 永远优先、秒回）：`--help` → `--list-suites` → `--suite` 校验 →
    跑用例（没给 `--suite` 就是全量）。参数错（套件名不存在 / 没给名字）一律退出 2，
    与「用例失败退出 1」分开——脚本化调用时才分得清「我命令写错了」还是「自测真红了」。
    """
    if _wants_help(argv):
        print(USAGE, end="")
        return 0
    if "--list-suites" in argv:
        _print_suites()
        return 0
    selected, bad, missing = _parse_suite_args(argv)
    if missing or bad or selected == []:
        if missing:
            print("✗ --suite 后面缺套件名（例：--suite j 或 --suite j,y）")
        for name in bad:
            print(f"✗ 未知套件：{name}")
        if selected == [] and not (missing or bad):
            print("✗ --suite 没选中任何套件（例：--suite j 或 --suite j,y）")
        _print_suites()
        print(f"退出码 2 = 参数错；用例失败才是 1（可用 {len(SUITES)} 个套件见上）。")
        return 2
    atexit.register(cleanup_root)
    try:
        # 全量路径**不传实参**：suite V 的探针把 `main` 换成零参假函数后调 `_run_cli([])`，
        # 传任何实参（哪怕 `None`）都会 TypeError。单套路径同理只传位置参数。
        return main() if selected is None else main(selected)
    finally:
        cleanup_root()


def suite_w():
    """P0-13：audit 不把「冻结前创建且已登记」的开发期新增误报为越界；lesson 文件视为工具生成。"""
    PROJ = ROOT / "audit-window-proj"
    (PROJ / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    P = ["-p", str(PROJ), "-f", "auditwin"]
    run("W: init", "init", *P, "--scope", "src")
    docs = PROJ / "docs" / "auditwin"
    run("W: baseline", "baseline", *P)
    write_design(docs)
    write_plan(docs)
    run("W: DESIGN->PLAN", "advance", *P, "--to", "PLAN", "--actor", "lead")
    run("W: PLAN->EXECUTING", "advance", *P, "--to", "EXECUTING", "--actor", "lead")
    write(PROJ / "src" / "b.py", "y = 2\n")
    write(PROJ / "ops" / "lessons.md", "| L001 | x |\n")
    run("W: scope add ops", "scope", *P, "--add", "ops", "--actor", "lead")
    run("W: freeze C001", "freeze", *P, "--id", "C001", "--from", str(PROJ), "--scope", "src")
    out, code = capture("audit", *P)
    check("W: 冻结前新增已登记 -> 不告警",
          code == 0 and "开发期新增（已登记，冻结前）" in out, out[-800:])
    check("W: lesson 文件算工具生成", "工具生成（lesson 子命令，预期）" in out, out[-400:])
    check("W: 全部改动被解释", "✓ 所有改动都在当前候选清单内" in out, out[-400:])


def suite_x():
    """flow-audit-hygiene C001：`audit` 只报真问题（E1–E5；E6 全量回归见 evidence/C001/P4-P6）。

    这一套刻意复刻 DESIGN §二 的实测拆解（11 条告警 = 9 条生成物假红 + 1 条真孤儿 + 1 条越界），
    只把规模压到 2 个生成物文件：**假红必须归零，真问题必须还在**——两侧都断言，不能靠删告警过测。
    """
    import importlib.util

    PROJ = ROOT / "x-hygiene-proj"
    (PROJ / "src").mkdir(parents=True)
    write(PROJ / "src" / "a.py", "x = 1\n")
    write(PROJ / "ROADMAP.md", "# 路线图\n\n## 0. 旧内容\n")
    write(PROJ / "roles" / "02-executor.md", "# executor（正主是另一个候选）\n")
    # 基线**之前**就存在的 dsh-bundle-dist 文件：旧基线会记录它们（实测 51 个），
    # 加跳过项后必须连「旧基线条目」一起滤掉，否则会反过来冒出「删除 → 未登记」假红。
    write(PROJ / "dsh-bundle-dist" / "tools" / "dsh_flow.py", "# generated v1\n")
    write(PROJ / "dsh-bundle-dist" / "ops" / "lessons.md", "# generated v1\n")

    X = ["-p", str(PROJ), "-f", "hygx"]
    run("X: init", "init", *X, "--scope", "src", "--no-graph")
    docs = PROJ / "docs" / "hygx"
    run("X: baseline", "baseline", *X)
    write_design(docs)
    write_plan(docs)
    run("X: DESIGN->PLAN", "advance", *X, "--to", "PLAN", "--actor", "lead")
    run("X: PLAN->EXECUTING", "advance", *X, "--to", "EXECUTING", "--actor", "lead")

    # 基线之后：1) 生成物重建（旧行为 8-9 条假红）2) 外来会话改 ROADMAP（真孤儿，仍未登记）
    write(PROJ / "dsh-bundle-dist" / "tools" / "dsh_flow.py", "# generated v2 (rebuilt)\n")
    write(PROJ / "dsh-bundle-dist" / "ops" / "lessons.md", "# generated v2 (rebuilt)\n")
    write(PROJ / "ROADMAP.md", "# 路线图\n\n## 0. 旧内容\n\n## 11. 2026-11-22 巡检增量\n")

    out1, code1 = capture("audit", *X)
    check("X: E1 生成物假红归零（dsh-bundle-dist/** 一个路径都不出现在 audit 里）",
          code1 == 0 and "dsh-bundle-dist" not in out1, out1[-900:])
    check("X: E1 旧基线条目被一并滤掉（不能变成「删除 → 未登记」假红），只剩 ROADMAP 一条修改",
          code1 == 0 and "项目内 新增 0 / 修改 1 / 删除 0" in out1, out1[-900:])
    check("X: E2 反向对照——认领前 ROADMAP.md 仍按「未登记」告警（不是把真孤儿一起静音）",
          code1 == 0 and "ROADMAP.md  — 未登记（越界嫌疑）" in out1, out1[-600:])

    run("X: freeze C001（--scope src + ROADMAP.md）", "freeze", *X, "--id", "C001",
        "--from", str(PROJ), "--scope", "src", "--scope", "ROADMAP.md")
    out2, code2 = capture("audit", *X)
    check("X: E2 ROADMAP.md 认领后「已登记且与候选一致」，不再报未登记",
          code2 == 0 and "ROADMAP.md  — 已登记且与候选一致" in out2
          and "ROADMAP.md  — 未登记" not in out2, out2[-900:])

    # E3：ops/ 不在声明写范围（scope 只有 src + 根级文档），lessons.md 由 lesson 子命令写
    write(PROJ / "ops" / "lessons.md",
          "| ID | 症状 | 根因 | 做法 | 适用角色 | 日期 |\n|---|---|---|---|---|---|\n"
          "| L001 | x | y | z | all | 2026-11-22 |\n")
    out3, code3 = capture("audit", *X)
    check("X: E3 lessons.md 豁免完整（「未登记」与「不在声明写范围内」一起免）",
          code3 == 0 and "ops/lessons.md  — 工具生成（lesson 子命令，预期）" in out3
          and "不在声明写范围内" not in out3, out3[-900:])
    check("X: E3 豁免不让 audit 变绿噪声（同轮无其它改动时整轮通过）",
          code3 == 0 and "✓ 所有改动都在当前候选清单内" in out3, out3[-600:])

    # 反向对照：同一轮里再改一个**真越界**文件，豁免不能连坐它
    write(PROJ / "roles" / "02-executor.md", "# executor（被另一个会话改过）\n")
    out4, code4 = capture("audit", *X)
    check("X: E3 反向对照——roles/02-executor.md 仍报「未登记；且不在声明写范围内」",
          code4 == 0 and "roles/02-executor.md  — 未登记（越界嫌疑）；且不在声明写范围内" in out4,
          out4[-900:])

    # E4：`current` 由 cmd_audit 现场 stat 出来，CLI 层构造不出「缺 mtime」的项，
    # 所以直接压判定函数 + 断言 audit 的调用点没绕开它（避免「单测绿、真实路径漂移」）。
    spec = importlib.util.spec_from_file_location("dsh_flow_hygiene_probe", FLOW)
    flow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(flow)          # 只导入函数，不触发 main()
    FT = 1_700_000_000.0
    e4_cases = (
        ("冻结前新增免报", {"sha256": "aa", "mtime": FT - 30}, "aa", FT, False,
         "开发期新增（已登记，冻结前）"),
        ("mtime 缺失按严格处理", {"sha256": "aa"}, "aa", FT, True, "mtime 缺失，按严格处理"),
        ("mtime 晚于冻结仍告警", {"sha256": "aa", "mtime": FT + 60}, "aa", FT, True, "mtime 晚于冻结"),
        ("内容不一致仍告警（真篡改口径不变）", {"sha256": "bb", "mtime": FT - 30}, "aa", FT, True,
         "主目录内容与候选冻结内容不一致"),
        ("无冻结时间戳不能证明冻结前", {"sha256": "aa", "mtime": FT - 30}, "aa", None, True,
         "无冻结时间戳"),
    )
    for label, cur, sha, ts, want_warn, want_text in e4_cases:
        got_text, got_warn = flow._artifact_new_state(cur, sha, ts)
        check(f"X: E4 {label}", got_warn is want_warn and want_text in got_text,
              f"warn={got_warn} state={got_text}")
    src_text = FLOW.read_text(encoding="utf-8")
    check("X: E4 audit 的「新增且已登记」分支确实调用 _artifact_new_state（单元断言不脱离真实代码路径）",
          "_artifact_new_state(current[rel], artifact_hash[rel], freeze_ts)" in src_text)

    # E5：重记基线后，同样的工作区必须一条项目内改动都不剩
    run("X: baseline 重记", "baseline", *X)
    out5, code5 = capture("audit", *X)
    check("X: E5 baseline 重记后 audit 干净（项目内 新增/修改/删除 = 0）",
          code5 == 0 and "项目内 新增 0 / 修改 0 / 删除 0" in out5
          and "✓ 所有改动都在当前候选清单内" in out5, out5[-900:])


# ---------------------------------------------------------------------------
# Y 组静态守卫（a-group-hardening）：`.ps1` 编码 + 危险删除形态
#
# 为什么放在 Python 侧而不是再写一个 PS 脚本：本组守的正是「.ps1 被改坏后连解析都过不了」——
# 守卫自己绝不能依赖「某个 .ps1 能跑起来」。所以判定逻辑全在 Python（纯函数、可单测），
# 只在需要**真实**解析器时批量调一次 `powershell.exe`。
# ---------------------------------------------------------------------------

# 排除的目录名（任意层级）：文档/生成物/历史备份副本，都不是「本仓可执行源」。
PS1_SKIP_DIR_NAMES = {"docs", "node_modules", "pack"}
# 排除的顶层目录名前缀：bundle 产物与历史备份（`dsh-bundle-dist` / `_attic*` / `_backup*`）。
PS1_SKIP_TOP_PREFIXES = ("dsh-bundle", "_attic", "_backup")

# 危险形态：「同一行里同时出现 cmd /c 与递归强删」——2026-11-20 一条 cmd 从 D 盘根递归删除、
# 丢失源仓库与多个项目的事故就是这种形态（ops/lessons.md L009）。
RE_PS_CMD_INVOKE = re.compile(r"cmd(?:\.exe)?\s+/c", re.IGNORECASE)
RE_PS_RECURSE_DELETE = re.compile(
    r"(?:\brd|\brmdir)\s+/s\b|\bdel\s+(?:/[a-z]\s+)*/s\b", re.IGNORECASE)


def ps1_files(root: Path = PKG) -> "list[Path]":
    """仓内（项目根递归）受静态守卫的 `*.ps1` 文件。

    排除清单与 DESIGN 一致：`docs/**`（已封存的候选副本，不可变）、`dsh-bundle*/**`（生成物）、
    `_attic*/**`、`_backup*/**`（历史备份）、`node_modules/**`、`pack/**`。
    排的是「目录段」不是子串：`tools/install.ps1` 里有个 `install` 不会被误伤，
    而 `dsh-bundle-dist/tools/install.ps1` 会因顶层前缀被排除。
    """
    out: "list[Path]" = []
    for p in sorted(root.rglob("*.ps1")):
        if not p.is_file():
            continue
        parts = p.relative_to(root).parts
        if any(part in PS1_SKIP_DIR_NAMES for part in parts[:-1]):
            continue
        if parts and parts[0].startswith(PS1_SKIP_TOP_PREFIXES):
            continue
        out.append(p)
    return out


def has_utf8_bom(path: Path) -> bool:
    """文件前三字节是否为 UTF-8 BOM（`EF BB BF`）。"""
    with Path(path).open("rb") as f:
        return f.read(3) == b"\xef\xbb\xbf"


def bom_missing(files) -> "list[str]":
    """**纯函数**：返回缺 UTF-8 BOM 的文件清单（尽量给项目根相对路径）。

    Y 组①与 Y 组④（反向断言）共用同一份判据——反向断言才能真正证明「判据不是恒真」。
    `files` 接受任意「文件路径序列」：真实仓文件与 TEMP 探针一视同仁。
    """
    missing: "list[str]" = []
    for p in files:
        p = Path(p)
        if has_utf8_bom(p):
            continue
        try:
            missing.append(p.relative_to(PKG).as_posix())
        except ValueError:
            missing.append(str(p))
    return missing


def danger_lines(text: str) -> "list[str]":
    """**纯函数**：返回「同一行里同时出现 `cmd /c` 与 `rd /s`/`rmdir /s`/`del /f /s`」的行。

    只报「同行组合」——`cmd /c` 单独出现（比如 `cmd /c ver`）或 `Remove-Item -Recurse` 都不算，
    否则守卫会变成满仓假红。
    """
    hits: "list[str]" = []
    for no, line in enumerate(text.splitlines(), 1):
        if RE_PS_CMD_INVOKE.search(line) and RE_PS_RECURSE_DELETE.search(line):
            hits.append(f"{no}: {line.strip()}")
    return hits


def suite_y():
    """a-group-hardening：`.ps1` 编码与危险删除形态的静态守卫（Y1–Y6）。

    A 组三类缺陷里有两条是「静态可查、但从来没人查」的：
      ① `.ps1` 丢 UTF-8 BOM → PS 5.1 按 ANSI(cp936) 解码 → 中文注释里的引号被吃掉 →
         `字符串缺少终止符`，脚本**连解析都过不了**（`tools/install.ps1` 实测 errors=1）；
      ② 递归强删前没有绝对路径/深度守卫（11-20 事故同族）。
    本套件把这两条变成每次 `selftest.py` 都跑得起的回归守卫，判据全在 Python 纯函数里
    （`ps1_files` / `has_utf8_bom` / `bom_missing` / `danger_lines`），只有 Y3 真调一次解析器。
    """
    files = ps1_files()
    rels = [p.relative_to(PKG).as_posix() for p in files]

    # Y1：扫描集非空 + 两个安装脚本在内（否则后面几条会「空转通过」）
    check("Y: Y1 仓内 .ps1 扫描集非空且含两个安装脚本（防空转）",
          len(files) >= 2 and "tools/install.ps1" in rels
          and "tools/install-git.ps1" in rels,
          f"扫描集 {len(files)} 个：{rels}")

    # Y2：全部带 UTF-8 BOM（缺就点名）
    missing = bom_missing(files)
    check("Y: Y2 仓内 .ps1 全部带 UTF-8 BOM（缺 BOM → PS 5.1 按 ANSI 解析必炸）",
          not missing, "缺 BOM：" + ", ".join(missing))

    # Y3：用真实 PS 解析器逐个判语法（一个进程批量判；不可用则 skip 并说明）
    ps_exe = shutil.which("powershell.exe") or shutil.which("powershell")
    if not ps_exe:
        print("\n=== Y: Y3 powershell.exe 不可用 → SKIP（无法验证解析器 0 error）===")
    else:
        listfile = ROOT / "ps1-parse-list.txt"
        write(listfile, "\n".join(str(p) for p in files))
        # 命令里只用单引号，避免与 subprocess 的参数层叠出转义问题。
        ps_cmd = (
            "$ErrorActionPreference = 'Stop';"
            "[Console]::OutputEncoding = [Text.Encoding]::UTF8;"
            f"$files = Get-Content -LiteralPath '{listfile}' -Encoding UTF8;"
            "$bad = 0;"
            "foreach ($f in $files) {"
            " if (-not $f) { continue }"
            " $errs = $null;"
            " [void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$null, [ref]$errs);"
            " if ($errs -and $errs.Count -gt 0) {"
            "  foreach ($e in $errs) { $bad++; Write-Output ('FAIL ' + $f + ' :: ' + $e.Message) }"
            " }"
            "}"
            "Write-Output ('PARSED ' + @($files | Where-Object { $_ }).Count);"
            "if ($bad -eq 0) { Write-Output 'OK' }"
        )
        p = _sp([ps_exe, "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        check("Y: Y3 每个 .ps1 用真实 PS 解析器判语法 → 0 error",
              p.returncode == 0 and "OK" in out and "FAIL " not in out
              and f"PARSED {len(files)}" in out,
              out[:1200])

    # Y4：全仓脚本无「cmd /c + 递归强删」同行组合（docs/** 已在扫描集排除，即文档豁免）
    bad = []
    for p in files:
        for hit in danger_lines(p.read_text(encoding="utf-8", errors="replace")):
            bad.append(f"{p.relative_to(PKG).as_posix()}:{hit}")
    check("Y: Y4 无「cmd /c 与 rd /s|rmdir /s|del /f /s 同行」的危险删除形态（docs/** 豁免）",
          not bad, "命中：" + " | ".join(bad[:10]))

    # Y5：Y4 的检测器正向对照（证明判据不是恒假）+ 反向对照（单独出现不报）
    pos = danger_lines("cmd /c rd /s /q D:\\")
    pos2 = danger_lines("cmd.exe /c del /f /s C:\\x")
    neg = danger_lines("Remove-Item -LiteralPath $x -Recurse -Force")
    neg2 = danger_lines("cmd /c ver")
    check("Y: Y5 危险形态检测器正反向对照（命中 2 例 / 不误伤 2 例）",
          len(pos) == 1 and len(pos2) == 1 and not neg and not neg2,
          f"pos={pos} pos2={pos2} neg={neg} neg2={neg2}")

    # Y6：反向断言——把某个 .ps1 复制到 TEMP 去掉 BOM，判据必须报缺；还原后必须通过。
    #     **不改真实文件**（探针只在 TEMP 里）；同时断言探针与源只差 BOM 三个字节。
    probe = ROOT / "probe-no-bom.ps1"
    src = PKG / "tools" / "install.ps1"
    data = src.read_bytes()
    body = data[3:] if data.startswith(b"\xef\xbb\xbf") else data
    probe.write_bytes(body)
    reject_ok = bom_missing([probe]) == [str(probe)]
    probe.write_bytes(b"\xef\xbb\xbf" + body)
    accept_ok = bom_missing([probe]) == []
    same_ok = probe.read_bytes()[3:] == body
    check("Y: Y6 反向断言——去 BOM 的副本被判缺 BOM、还原后通过（且只差 BOM 三字节）",
          reject_ok and accept_ok and same_ok,
          f"reject_ok={reject_ok} accept_ok={accept_ok} same_ok={same_ok}")


# ---------------------------------------------------------------------------
# 套件注册表（selftest-perf E1-2）
#
# 只做「登记」：**不改任何 suite 的用例与判据**。键是全小写字母（命令行用），值是对应函数。
# 顺序 = `main()` 历史上的执行顺序，因此不带参数跑全量时，执行顺序与总条数与改前逐条一致
# （DESIGN P6：total/failed 不变）。
# 为什么没有 F / O：本文件从建立起就没有 `suite_f` / `suite_o`，字母表是有洞的 A–Y。
# 单套跑（`--suite j`）只为了排障时省时间；**判据、条数、断言强度一条都没动**。
# ---------------------------------------------------------------------------
SUITES = {
    "a": suite_a,
    "b": suite_b,
    "c": suite_c,
    "d": suite_d,
    "e": suite_e,
    "g": suite_g,
    "h": suite_h,
    "i": suite_i,
    "j": suite_j,
    "k": suite_k,
    "l": suite_l,
    "m": suite_m,
    "n": suite_n,
    "p": suite_p,
    "q": suite_q,
    "r": suite_r,
    "s": suite_s,
    "t": suite_t,
    "u": suite_u,
    "v": suite_v,
    "w": suite_w,
    "x": suite_x,
    "y": suite_y,
}


def main(suites=None):
    """跑用例并汇总。`suites is None` → 全量（顺序由 `SUITES` 决定，与改前一致）。

    给了选择时**按 `SUITES` 的顺序**执行，不按命令行输入顺序（`--suite y,j` 与 `j,y` 输出完全
    相同）。汇总与退出码逻辑一个字没改：仍是 `total=/failed=` + 逐条 `FAIL:` + 失败即 1。
    """
    todo = SUITES if suites is None else [k for k in SUITES if k in suites]
    for key in todo:
        SUITES[key]()
    failed = [r for r in results if not r[1]]
    print("\n" + "=" * 60)
    print(f"total={len(results)} failed={len(failed)}")
    for label, ok, code in failed:
        print(f"  FAIL: {label} (exit={code})")
    return 1 if failed else 0


if __name__ == "__main__":
    # C003 / D-06：`--help` 与「跑全量」都由 `_run_cli` 分流；跑全量时它保证退出前清掉 TEMP 根。
    sys.exit(_run_cli(sys.argv[1:]))
