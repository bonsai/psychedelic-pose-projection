# Psychedelic Pose Projection — Windows 用単一 EXE ビルドスクリプト
# PowerShell で実行してください

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. モデルファイルがなければダウンロード
$modelFile = Join-Path $scriptDir "pose_landmarker_lite.task"
if (-not (Test-Path $modelFile)) {
    Write-Host "モデルをダウンロード中..." -ForegroundColor Cyan
    $modelUrl = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    Invoke-WebRequest -Uri $modelUrl -OutFile $modelFile
}

# 2. ビルド用 venv
$venvDir = Join-Path $scriptDir ".venv-build"
if (-not (Test-Path $venvDir)) {
    python -m venv $venvDir
}

& (Join-Path $venvDir "Scripts\python.exe") -m pip install --upgrade pip
& (Join-Path $venvDir "Scripts\pip.exe") install -r requirements.txt pyinstaller

# 3. 古いビルド成果物を削除
@("build", "dist", "*.spec") | ForEach-Object {
    $target = Join-Path $scriptDir $_
    if (Test-Path $target) {
        Remove-Item -Recurse -Force $target
    }
}

# 4. PyInstaller で単一 EXE をビルド
& (Join-Path $venvDir "Scripts\pyinstaller.exe") `
    --onefile `
    --name PsychedelicPoseProjection `
    --add-data "pose_landmarker_lite.task;." `
    --collect-data mediapipe `
    --collect-binaries mediapipe `
    --noconfirm `
    main_tasks.py

Write-Host ""
Write-Host "ビルド完了: $scriptDir\dist\PsychedelicPoseProjection.exe" -ForegroundColor Green
