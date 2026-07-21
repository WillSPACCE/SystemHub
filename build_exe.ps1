param(
    [string]$Name = "SystemUtilityHub"
)

$ErrorActionPreference = "Stop"

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
    $py = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $py) {
    Write-Error "Python não encontrado no PATH. Instale o Python 3.10+ e tente novamente."
    exit 1
}

& $py.Source -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $py.Source -m PyInstaller --noconsole --onefile --name $Name --distpath .\dist --workpath .\build --specpath .\build main.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Executável gerado em .\dist\$Name.exe"
