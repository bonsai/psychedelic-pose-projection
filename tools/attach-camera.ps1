# カメラを WSL2 にアタッチするスクリプト（Windows PowerShell 管理者権限で実行）

$ErrorActionPreference = "Stop"

# usbipd が入っているか確認
try {
    $null = Get-Command usbipd -ErrorAction Stop
} catch {
    Write-Host "usbipd が見つかりません。 winget でインストールしてください：" -ForegroundColor Red
    Write-Host "  winget install --interactive --exact dorssel.usbipd-win" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "接続されている USB デバイス一覧：" -ForegroundColor Cyan
usbipd list

Write-Host ""
Write-Host "カメラと思われるデバイスの BUSID を入力してください（例：2-3）：" -NoNewline
$busId = Read-Host

if ([string]::IsNullOrWhiteSpace($busId)) {
    Write-Host "BUSID が入力されませんでした。終了します。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[$busId] を Shared にバインドします..." -ForegroundColor Cyan
usbipd bind --busid $busId

Write-Host "[$busId] を WSL2 にアタッチします..." -ForegroundColor Cyan
usbipd attach --wsl --busid $busId

Write-Host ""
Write-Host "完了しました。" -ForegroundColor Green
Write-Host "WSL2 側で以下を実行して /dev/video0 ができているか確認してください：" -ForegroundColor Yellow
Write-Host "  ls /dev/video*" -ForegroundColor Yellow
Write-Host ""
Write-Host "カメラが見えたら psychedelic-pose-projection を実行してください：" -ForegroundColor Yellow
Write-Host "  cd /home/bons/bons && ./psychedelic-pose-projection" -ForegroundColor Yellow
