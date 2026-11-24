<#
.SYNOPSIS
  把 DSH 多角色协作流程安装到某个项目（项目级生效，不动全局 DSH 配置）。

.DESCRIPTION
  做两件事，都是幂等的：
    1) 复制技能到 <项目>\.dsh\skills\dsh-multi-role-flow\SKILL.md（DSH 会自动发现并热加载）
    2) 在 <项目>\AGENTS.md 里维护流程约定段（始终用 begin/end 标记包裹；已有标记段则整段替换，可重复执行）

.PARAMETER Project
  目标项目根目录。DSH 打开会话时的工作目录应当就是这里（无 .git 时按 cwd 识别项目根）。

.PARAMETER Package
  流程包目录，默认是本脚本上一级。

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install.ps1 -Project "D:\我的项目"
#>
param(
  [Parameter(Mandatory = $true)][string]$Project,
  [string]$Package = ''
)

if (-not $Package) { $Package = Split-Path -Parent (Split-Path -Parent $PSCommandPath) }

$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Write-Utf8([string]$Path, [string]$Text) {
  $dir = Split-Path -Parent $Path
  if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}

if (-not (Test-Path -LiteralPath $Project)) { throw "项目目录不存在: $Project" }
if (-not (Test-Path -LiteralPath (Join-Path $Package 'tools\dsh_flow.py'))) { throw "流程包不完整，找不到 tools\dsh_flow.py: $Package" }

$proj = (Resolve-Path -LiteralPath $Project).Path
$pkg = (Resolve-Path -LiteralPath $Package).Path

# 1) 安装技能
$skillSrc = Join-Path $pkg 'skills\dsh-multi-role-flow\SKILL.md'
$skillDst = Join-Path $proj '.dsh\skills\dsh-multi-role-flow\SKILL.md'
$skillText = [System.IO.File]::ReadAllText($skillSrc, [System.Text.Encoding]::UTF8)
$skillText = $skillText.Replace('{{PACKAGE}}', $pkg)
Write-Utf8 $skillDst $skillText
Write-Host "[1/2] 技能已安装: $skillDst"

# 2) 安装 AGENTS.md 约定（幂等：内容一律用 begin/end 标记包裹；已有标记段则整段替换）
$agentsPath = Join-Path $proj 'AGENTS.md'
$markerBegin = '<!-- dsh-multi-role-flow:begin -->'
$markerEnd = '<!-- dsh-multi-role-flow:end -->'
$tpl = [System.IO.File]::ReadAllText((Join-Path $pkg 'templates\AGENTS.md'), [System.Text.Encoding]::UTF8).Replace('{{PACKAGE}}', $pkg)
$existing = ''
if (Test-Path -LiteralPath $agentsPath) {
  $existing = [System.IO.File]::ReadAllText($agentsPath, [System.Text.Encoding]::UTF8)
}
$block = "$markerBegin`r`n$($tpl.TrimEnd([char]13, [char]10))`r`n$markerEnd"
$iBegin = $existing.IndexOf($markerBegin, [System.StringComparison]::Ordinal)
$iEnd = -1
if ($iBegin -ge 0) { $iEnd = $existing.IndexOf($markerEnd, $iBegin, [System.StringComparison]::Ordinal) }
if ($existing.Trim().Length -eq 0) {
  $merged = "$block`r`n"
  $mode = 'created'
} elseif ($iBegin -ge 0 -and $iEnd -ge 0) {
  $merged = $existing.Substring(0, $iBegin) + $block + $existing.Substring($iEnd + $markerEnd.Length)
  $mode = 'updated'
} elseif ($iBegin -ge 0) {
  # 历史损坏：有 begin 没有 end —— 把 begin 至文件末尾当作标记段替换，前面内容原样保留
  $merged = $existing.Substring(0, $iBegin) + $block + "`r`n"
  $mode = 'repaired'
} else {
  $merged = $existing.TrimEnd() + "`r`n`r`n" + $block + "`r`n"
  $mode = 'appended'
}
if ($merged -ceq $existing) {
  Write-Host "[2/2] AGENTS.md 里已有流程约定，已存在（幂等，未改动）: $agentsPath"
} else {
  Write-Utf8 $agentsPath $merged
  switch ($mode) {
    'created'  { Write-Host "[2/2] 流程约定已写入（带 begin/end 标记）: $agentsPath" }
    'appended' { Write-Host "[2/2] 流程约定已写入（原有内容保留，带 begin/end 标记）: $agentsPath" }
    default    { Write-Host "[2/2] 流程约定已更新（幂等，整段替换标记段）: $agentsPath" }
  }
}

$py = 'python'
$candidate = Join-Path $env:USERPROFILE '.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $candidate) { $py = "`"$candidate`"" }

Write-Host ""
Write-Host "安装完成。下一步（在 DSH 里把会话工作目录设为 $proj）："
Write-Host ""
Write-Host "  $py `"$pkg\tools\dsh_flow.py`" doctor   -p `"$proj`" -f <feature>"
Write-Host "  $py `"$pkg\tools\dsh_flow.py`" init     -p `"$proj`" -f <feature> --scope src"
Write-Host "  $py `"$pkg\tools\dsh_flow.py`" baseline -p `"$proj`" -f <feature>"
Write-Host "  $py `"$pkg\tools\dsh_flow.py`" next     -p `"$proj`" -f <feature>"
Write-Host ""
Write-Host "技能会在 DSH 技能目录里出现（名称 dsh-multi-role-flow），也可以直接说「按多角色流程开始」。"
