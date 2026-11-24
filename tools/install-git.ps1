<#
.SYNOPSIS
  补装 git（MinGit，免管理员），让 DSH 的 create_worktree 可用。

.DESCRIPTION
  背景：本机原先没有 git，create_worktree 报 `command "git" was not found on PATH`，
  流程退化为「副本 + 哈希」。本脚本幂等地做四件事：
    1) 从 GitHub 下载 MinGit（默认最新 release），按 release 提供的 sha256 校验；
    2) 解压到 -InstallDir（默认 %LOCALAPPDATA%\Programs\Git）；
    3) 把 <InstallDir>\cmd 追加到「用户」PATH（不动机器级 PATH，不需要管理员）；
    4) 全局身份缺失时才写 user.name/user.email，并用临时仓库实测
       init / commit / worktree add / diff。
  装完必须重启 DSH Desktop：进程的 PATH 在启动时固定，重启后 create_worktree 才可见。

.PARAMETER InstallDir
  安装目录，默认 `$env:LOCALAPPDATA\Programs\Git`。

.PARAMETER Version
  MinGit 版本号，默认取 GitHub 最新 release，例如 `2.56.1`。

.PARAMETER Force
  目标目录已存在时重新下载并覆盖解压。

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install-git.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install-git.ps1 -Version 2.56.1 -Force
#>
param(
  [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'Programs\Git'),
  [string]$Version = '',
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# 删除守卫（L009 / 2026-11-20 事故同族）：$InstallDir 来自命令行参数，第 2 步会对它做
# `Remove-Item -Recurse -Force`。递归删除前必须先把目标解析成**绝对路径**并验**深度**：
#   - 字符串必须匹配 `^[A-Za-z]:\`（`X:\` 开头的绝对路径）；
#   - 按 `\` 分割后段数必须 ≥3（`X:\` 只有 1 段、`X:\<一级>` 只有 2 段，都是浅路径）；
# 任一条不满足就 throw 并且**不删**。原则「宁可拒绝，不可删除」：拒绝的代价是一次报错，
# 删除的代价是 2026-11-20 那样的全盘损失。
# 放在脚本开头（下载之前）而不是只放在删除那一行之前：浅路径在**任何**网络动作之前就拒，
# 既不做无用下载，也不给「先下载再报错」留窗口。
$resolvedDir = if (Test-Path -LiteralPath $InstallDir) {
  (Resolve-Path -LiteralPath $InstallDir).Path
} else {
  $InstallDir
}
$dirSegments = @($resolvedDir -split '\\' | Where-Object { $_ -ne '' })
if (($resolvedDir -notmatch '^[A-Za-z]:\\') -or ($dirSegments.Count -lt 3)) {
  throw "拒绝删除浅路径/非绝对路径：$resolvedDir"
}

function Get-MinGitAsset {
  param([string]$Ver)
  $api = if ($Ver) {
    "https://api.github.com/repos/git-for-windows/git/releases/tags/v$Ver.windows.1"
  } else {
    'https://api.github.com/repos/git-for-windows/git/releases/latest'
  }
  $rel = Invoke-RestMethod -Uri $api -Headers @{ 'User-Agent' = 'dsh-flow-install-git' } -TimeoutSec 30
  $asset = $rel.assets | Where-Object { $_.name -match '^MinGit-[\d.]+-64-bit\.zip$' } | Select-Object -First 1
  if (-not $asset) { throw "release $($rel.tag_name) 里找不到 MinGit-*-64-bit.zip" }
  [pscustomobject]@{
    Tag    = $rel.tag_name
    Name   = $asset.name
    Url    = $asset.browser_download_url
    Size   = [int64]$asset.size
    Digest = [string]$asset.digest
  }
}

Write-Host '== 1/4 下载 MinGit ==' -ForegroundColor Cyan
$asset = Get-MinGitAsset -Ver $Version
Write-Host ('release {0} / {1} / {2:N1} MB' -f $asset.Tag, $asset.Name, ($asset.Size / 1MB))
$zip = Join-Path $env:TEMP $asset.Name
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
  & curl.exe -L --fail --retry 3 -o $zip $asset.Url
  if ($LASTEXITCODE -ne 0) { throw "curl 下载失败（exit $LASTEXITCODE）" }
} else {
  Invoke-WebRequest -Uri $asset.Url -OutFile $zip -UseBasicParsing
}
$actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower()
if ($asset.Digest -and $asset.Digest.StartsWith('sha256:')) {
  $expect = $asset.Digest.Substring(7).ToLower()
  if ($actual -ne $expect) { throw "sha256 校验失败：期望 $expect，实际 $actual" }
  Write-Host "sha256 校验通过：$actual"
} else {
  Write-Host "警告：release 未提供 digest，仅记录 sha256 $actual" -ForegroundColor Yellow
}

Write-Host "== 2/4 解压到 $InstallDir ==" -ForegroundColor Cyan
$gitExe = Join-Path $InstallDir 'cmd\git.exe'
if ((Test-Path -LiteralPath $gitExe) -and -not $Force) {
  Write-Host "已存在，跳过解压（要覆盖请加 -Force）：$gitExe"
  & $gitExe --version
} else {
  # 删除前已在脚本开头校验过 $InstallDir（`X:\` 绝对路径 + 段数≥3，见「删除守卫」段）：
  # 校验不通过时脚本早已 throw 退出，走不到这里——所以这一行不需要（也不应该）再复制一份判据。
  if (Test-Path -LiteralPath $InstallDir) { Remove-Item -LiteralPath $InstallDir -Recurse -Force }
  New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $InstallDir)
  if (-not (Test-Path -LiteralPath $gitExe)) { throw "解压后找不到 $gitExe" }
  & $gitExe --version
}

Write-Host '== 3/4 写入用户 PATH 与全局身份 ==' -ForegroundColor Cyan
$cmdDir = Join-Path $InstallDir 'cmd'
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notlike ('*' + $cmdDir + '*')) {
  $newPath = if ([string]::IsNullOrWhiteSpace($userPath)) { $cmdDir } else { $userPath.TrimEnd(';') + ';' + $cmdDir }
  [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
  Write-Host "已追加用户 PATH：$cmdDir"
} else {
  Write-Host "用户 PATH 已包含：$cmdDir"
}
if (-not (& $gitExe config --global user.name)) {
  & $gitExe config --global user.name 'DSH Agent'
}
if (-not (& $gitExe config --global user.email)) {
  & $gitExe config --global user.email 'agent@dsh.local'
}
if (-not (& $gitExe config --global init.defaultBranch)) {
  & $gitExe config --global init.defaultBranch main
}
Write-Host ('身份：{0} <{1}>' -f (& $gitExe config --global user.name), (& $gitExe config --global user.email))

Write-Host '== 4/4 实测 init / commit / worktree / diff ==' -ForegroundColor Cyan
$stamp = [guid]::NewGuid().ToString('N').Substring(0, 8)
$tmp = Join-Path $env:TEMP ("dsh-git-selftest-$stamp")
$wt = Join-Path $env:TEMP ("dsh-git-wt-$stamp")
try {
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  & $gitExe -C $tmp init -q
  'a' | Set-Content -LiteralPath (Join-Path $tmp 'a.txt')
  & $gitExe -C $tmp add a.txt
  & $gitExe -C $tmp commit -q -m 'init'
  $head = (& $gitExe -C $tmp rev-parse --short HEAD)
  & $gitExe -C $tmp worktree add -q $wt -b selftest-branch
  'b' | Add-Content -LiteralPath (Join-Path $wt 'a.txt')
  $diff = (& $gitExe -C $wt diff --stat)
  Write-Host "commit=$head  worktree=ok  diff=$diff"
  Write-Host 'SELFTEST: PASS' -ForegroundColor Green
} finally {
  if (Test-Path -LiteralPath $wt) { Remove-Item -LiteralPath $wt -Recurse -Force -ErrorAction SilentlyContinue }
  if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }
}

Write-Host ''
Write-Host '完成。DSH Desktop 的进程 PATH 在启动时固定：' -ForegroundColor Green
Write-Host '请重启 DSH Desktop，重启后 create_worktree 才能找到 git。' -ForegroundColor Green
Write-Host "未重启前，脚本仍可用绝对路径调用：$gitExe"
