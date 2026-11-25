<#
VSEKit setup — makes a fresh Windows machine ready. Safe to re-run: every step skips what already exists.

    powershell -ExecutionPolicy Bypass -File setup.ps1            # everything
    powershell -ExecutionPolicy Bypass -File setup.ps1 -SkipML    # no torch/whisper/kokoro/deepfilternet

What it does:
  1. VSEKIT_ROOT user env var -> this folder
  2. winget: ffmpeg (Gyan.FFmpeg), deno (yt-dlp JS runtime), uv; Blender only if none is found
  3. .venv (Python 3.12): torch (CUDA if nvidia-smi exists, else CPU) + requirements.txt
  4. .venv-df (Python 3.11): DeepFilterNet with its old torch/numpy pins
  5. Real-ESRGAN ncnn-vulkan -> tools\realesrgan
  6. Pillow + edge-tts into Blender's user modules (for scripts run with Blender's own Python)
  7. Claude Code skill: junction %USERPROFILE%\.claude\skills\video-editing -> skill\video-editing
  8. tools\doctor.py report
#>
param([switch]$SkipML)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
function Step($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Need-Winget($id, $exe) {
    if (Get-Command $exe -ErrorAction SilentlyContinue) { Write-Host "$exe found"; return }
    Write-Host "installing $id"
    winget install --id $id -e --accept-source-agreements --accept-package-agreements --silent | Out-Host
    Refresh-Path
}

Step "1. VSEKIT_ROOT"
[Environment]::SetEnvironmentVariable('VSEKIT_ROOT', $Root, 'User')
$env:VSEKIT_ROOT = $Root
Write-Host $Root

Step "2. winget tools"
Need-Winget 'Gyan.FFmpeg' 'ffmpeg'
Need-Winget 'DenoLand.Deno' 'deno'
Need-Winget 'astral-sh.uv' 'uv'
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { throw "uv not on PATH after install - open a new terminal and re-run setup.ps1" }

Step "3. .venv (Python 3.12)"
if (-not (Test-Path '.venv\Scripts\python.exe')) { & $uv venv --python 3.12 .venv; if ($LASTEXITCODE) { throw 'venv failed' } }
$py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not $SkipML) {
    $hasNvidia = [bool](Get-Command nvidia-smi -ErrorAction SilentlyContinue)
    $index = if ($hasNvidia) { 'https://download.pytorch.org/whl/cu128' } else { 'https://download.pytorch.org/whl/cpu' }
    Write-Host "torch from $index"
    & $uv pip install --python $py torch torchaudio --index-url $index; if ($LASTEXITCODE) { throw 'torch failed' }
}
& $uv pip install --python $py -r requirements.txt; if ($LASTEXITCODE) { throw 'requirements failed' }
# headless Chromium for vsekit.html_motion (~250 MB, %LOCALAPPDATA%\ms-playwright; no-op when present)
& $py -m playwright install chromium --only-shell; if ($LASTEXITCODE) { Write-Warning 'playwright chromium install failed (html_motion unavailable)' }

Step "Blender"
$blender = (& $py -m vsekit.env blender).Trim()
if (-not $blender) {
    Write-Host "Blender not found - installing BlenderFoundation.Blender"
    winget install --id BlenderFoundation.Blender -e --accept-source-agreements --accept-package-agreements --silent | Out-Host
    $blender = (& $py -m vsekit.env blender).Trim()
}
Write-Host "blender: $blender"

Step "4. .venv-df (DeepFilterNet)"
if (-not $SkipML) {
    if (-not (Test-Path '.venv-df\Scripts\python.exe')) { & $uv venv --python 3.11 .venv-df; if ($LASTEXITCODE) { throw 'venv-df failed' } }
    $pydf = Join-Path $Root '.venv-df\Scripts\python.exe'
    & $uv pip install --python $pydf 'torch==2.0.1' 'torchaudio==2.0.2' --index-url https://download.pytorch.org/whl/cpu
    & $uv pip install --python $pydf -r requirements-df.txt; if ($LASTEXITCODE) { throw 'deepfilternet failed' }
}

Step "5. Real-ESRGAN"
$esr = 'tools\realesrgan\realesrgan-ncnn-vulkan.exe'
if (-not (Test-Path $esr)) {
    $zip = Join-Path $env:TEMP 'realesrgan.zip'
    Invoke-WebRequest 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip' -OutFile $zip
    Expand-Archive -Force $zip 'tools\realesrgan'
    Remove-Item $zip
} else { Write-Host 'present' }

Step "6. Blender user modules (Pillow, edge-tts)"
$bpy = (& $py -m vsekit.env blender_py).Trim()
$mods = (& $py -m vsekit.env blender_modules).Trim()
if ($bpy -and $mods) {
    New-Item -ItemType Directory -Force $mods | Out-Null
    & $bpy -m pip install --quiet --target $mods --upgrade pillow edge-tts
} else { Write-Host 'skipped (Blender Python not found)' }

Step "7. Claude Code skill"
$skills = Join-Path $env:USERPROFILE '.claude\skills'
$link = Join-Path $skills 'video-editing'
$target = Join-Path $Root 'skill\video-editing'
New-Item -ItemType Directory -Force $skills | Out-Null
if (Test-Path $link) {
    $item = Get-Item $link -Force
    if ($item.LinkType -ne 'Junction') {
        $bak = "$link.bak-$(Get-Date -Format yyyyMMddHHmmss)"
        Rename-Item $link $bak
        Write-Host "existing non-linked skill moved to $bak"
        cmd /c mklink /J "$link" "$target" | Out-Host
    } else { Write-Host "junction exists -> $($item.Target)" }
} else { cmd /c mklink /J "$link" "$target" | Out-Host }

Step "8. doctor"
& $py tools\doctor.py
Write-Host "`nManual steps (not scriptable): Blender MCP extension in Blender + its Claude Code MCP connection;"
Write-Host "Unity MCP + com.unity.recorder in the Unity project if you record gameplay."
