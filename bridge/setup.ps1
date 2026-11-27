# Run on the Live Lab PC:  iwr -useb <raw url of this file> | iex
# Creates Infineon's PDM microphone example, builds it, flashes the board, and downloads bridge.py.
$ErrorActionPreference = 'Stop'
$raw = 'https://raw.githubusercontent.com/gleebmat/hackathon-2026/tom/board/bridge'
$tools = Join-Path $HOME 'ModusToolbox\tools_3.9'
$ws = Join-Path $HOME 'mtw'
$app = Join-Path $ws 'room_noise'

Invoke-WebRequest "$raw/bridge.py" -OutFile (Join-Path $HOME 'bridge.py')

if (-not (Test-Path $app)) {
    & (Join-Path $tools 'project-creator\project-creator-cli.exe') `
        --board-id KIT_PSE84_EVAL_EPC2 --app-id mtb-example-psoc-edge-pdm-pcm `
        --user-app-name room_noise --target-dir $ws
}

$bash = Join-Path $tools 'modus-shell\bin\bash.exe'
$unix = $app -replace '\\', '/'
& $bash --login -c "cd '$unix' && make build -j8 && make program"
Write-Host 'Flashed. Now run:  python $HOME\bridge.py COM3'
