# Run on the Live Lab PC:  iwr -useb <raw url of this file> | iex
# Builds Infineon's person-segmentation example (YOLACT, runs on the NPU) with our presence-printing
# inference_task.c, flashes the board, and downloads bridge.py. The board then prints "PRESENCE 0|1 n/m" each second.
$ErrorActionPreference = 'Stop'
$raw = 'https://raw.githubusercontent.com/gleebmat/hackathon-2026/tom/board-session2/bridge'
$tools = Join-Path $HOME 'ModusToolbox\tools_3.9'
$ws = Join-Path $HOME 'mtw'
$app = Join-Path $ws 'room_person'

Invoke-WebRequest "$raw/bridge.py" -OutFile (Join-Path $HOME 'bridge.py')
if (-not (Test-Path $app)) {
    & (Join-Path $tools 'project-creator\project-creator-cli.exe') `
        --board-id KIT_PSE84_EVAL_EPC2 --app-id mtb-example-psoc-edge-ml-aihub-deploy-vision `
        --user-app-name room_person --target-dir $ws
}
Invoke-WebRequest "$raw/firmware/inference_task.c" -OutFile (Join-Path $app 'proj_cm55\source\inference_task.c')

$bash = Join-Path $tools 'modus-shell\bin\bash.exe'
$unix = $app -replace '\\', '/'
$toolsUnix = $tools -replace '\\', '/'
& $bash --login -c "export CY_TOOLS_PATHS='$toolsUnix'; cd '$unix' && make build -j8 && make program"
Write-Host 'Flashed. Now run:  python $HOME\bridge.py COM3'
