param(
  [string[]]$Targets = @(
    "AI_BISEO",
    "donggri_gagyeobu",
    "Automethemoney",
    "BloManagent",
    "Vibe_Cowork_Thinking"
  ),
  [string]$BrowserPath
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$workspace = $root.Path
$captureLogDir = Join-Path $workspace ".capture-logs"
New-Item -ItemType Directory -Force -Path $captureLogDir | Out-Null

function Resolve-BrowserPath {
  param([string]$Candidate)

  if ($Candidate) {
    return $Candidate
  }

  $knownPaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
  )

  foreach ($path in $knownPaths) {
    if (Test-Path $path) {
      return $path
    }
  }

  throw "Headless browser executable not found. Pass -BrowserPath explicitly."
}

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][scriptblock]$Action
  )

  Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Label)
  & $Action
}

function Invoke-InDirectory {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][scriptblock]$Action
  )

  Push-Location $Path
  try {
    & $Action
  }
  finally {
    Pop-Location
  }
}

function Ensure-Directory {
  param([Parameter(Mandatory = $true)][string]$Path)
  New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Wait-ForUrl {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$Attempts = 80,
    [int]$DelaySeconds = 2
  )

  for ($i = 0; $i -lt $Attempts; $i++) {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return
      }
    }
    catch {
    }

    Start-Sleep -Seconds $DelaySeconds
  }

  throw "Timed out waiting for $Url"
}

function Stop-ProcessTree {
  param([System.Diagnostics.Process]$Process)

  if (-not $Process) {
    return
  }

  try {
    if (-not $Process.HasExited) {
      & taskkill /PID $Process.Id /T /F | Out-Null
    }
  }
  catch {
  }
}

function Start-BackgroundShell {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][string]$Command,
    [hashtable]$Environment = @{}
  )

  $prolog = @()
  foreach ($key in $Environment.Keys) {
    $value = [string]$Environment[$key]
    $escaped = $value.Replace("'", "''")
    $prolog += "`$env:$key = '$escaped'"
  }

  $script = if ($prolog.Count -gt 0) {
    ($prolog + $Command) -join "; "
  }
  else {
    $Command
  }

  $stdout = Join-Path $captureLogDir ("{0}.out.log" -f $Name)
  $stderr = Join-Path $captureLogDir ("{0}.err.log" -f $Name)

  return Start-Process powershell.exe `
    -ArgumentList @("-NoLogo", "-NoProfile", "-Command", $script) `
    -WorkingDirectory $WorkingDirectory `
    -PassThru `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr
}

function Invoke-Capture {
  param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [int]$Width = 1440,
    [int]$Height = 1024,
    [int]$WaitMs = 7000
  )

  Ensure-Directory -Path (Split-Path -Parent $OutputPath)

  & $Executable `
    --headless `
    --disable-gpu `
    --hide-scrollbars `
    --window-size="$Width,$Height" `
    --virtual-time-budget=$WaitMs `
    --screenshot="$OutputPath" `
    "$Url" | Out-Null

  if (-not (Test-Path $OutputPath)) {
    throw "Screenshot not created for $Url"
  }
}

function Invoke-JsonRequest {
  param(
    [ValidateSet("Get", "Post", "Put", "Patch", "Delete")][string]$Method,
    [Parameter(Mandatory = $true)][string]$Url,
    [object]$Body
  )

  $params = @{
    Method      = $Method
    Uri         = $Url
    ContentType = "application/json"
    UseBasicParsing = $true
  }

  if ($null -ne $Body) {
    $params["Body"] = ($Body | ConvertTo-Json -Depth 8)
  }

  return Invoke-RestMethod @params
}

function Ensure-NodeModules {
  param([Parameter(Mandatory = $true)][string]$RepoPath)

  if (Test-Path (Join-Path $RepoPath "node_modules")) {
    return
  }

  Invoke-Step -Label "npm install :: $RepoPath" -Action {
    Invoke-InDirectory -Path $RepoPath -Action {
      & npm.cmd install
      if ($LASTEXITCODE -ne 0) {
        throw "npm install failed in $RepoPath"
      }
    }
  }
}

function Ensure-PythonVenv {
  param(
    [Parameter(Mandatory = $true)][string]$RepoPath,
    [string]$VenvName = ".venv-docs",
    [Parameter(Mandatory = $true)][string]$RequirementsPath,
    [string[]]$FallbackPackages = @()
  )

  $venvPath = Join-Path $RepoPath $VenvName
  $pythonExe = Join-Path $venvPath "Scripts\python.exe"

  if (-not (Test-Path $pythonExe)) {
    Invoke-Step -Label "create venv :: $RepoPath\$VenvName" -Action {
      Invoke-InDirectory -Path $RepoPath -Action {
        & py -m venv $VenvName
        if ($LASTEXITCODE -ne 0) {
          throw "venv creation failed in $RepoPath"
        }
      }
    }
  }

  $installed = $false
  try {
    Invoke-Step -Label "pip install :: $RequirementsPath" -Action {
      & $pythonExe -m pip install -r $RequirementsPath
      if ($LASTEXITCODE -ne 0) {
        throw "pip install failed for $RequirementsPath"
      }
    }
    $installed = $true
  }
  catch {
    if ($FallbackPackages.Count -eq 0) {
      throw
    }

    Write-Warning ("requirements install failed for {0}. Falling back to compatible package set." -f $RepoPath)
    Invoke-Step -Label "pip install fallback :: $RepoPath" -Action {
      & $pythonExe -m pip install @FallbackPackages
      if ($LASTEXITCODE -ne 0) {
        throw "fallback pip install failed for $RepoPath"
      }
    }
    $installed = $true
  }

  if (-not $installed) {
    throw "python environment setup failed for $RepoPath"
  }

  return $pythonExe
}

function Capture-AIBiseo {
  param([string]$Executable)

  $repo = Join-Path $workspace "AI_BISEO"
  $shotDir = Join-Path $repo "docs\assets\screenshots"

  Ensure-NodeModules -RepoPath $repo

  $process = Start-BackgroundShell `
    -Name "ai-biseo" `
    -WorkingDirectory $repo `
    -Environment @{ APP_PORT = "3010" } `
    -Command "& npm.cmd run dev"

  try {
    Wait-ForUrl -Url "http://127.0.0.1:3010/health"

    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:3010/dashboard/" -OutputPath (Join-Path $shotDir "ai-biseo-overview.png")
    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:3010/dashboard/assistant.html" -OutputPath (Join-Path $shotDir "ai-biseo-assistant.png")
    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:3010/dashboard/pipeline.html" -OutputPath (Join-Path $shotDir "ai-biseo-pipeline.png")
  }
  finally {
    Stop-ProcessTree -Process $process
  }
}

function Seed-DonggriLedger {
  param([string]$BaseUrl)

  $bank = Invoke-JsonRequest -Method Post -Url "$BaseUrl/api/assets" -Body @{
    name    = "Main Bank"
    type    = "bank"
    balance = 3250000
  }

  $card = Invoke-JsonRequest -Method Post -Url "$BaseUrl/api/assets" -Body @{
    name                   = "Daily Card"
    type                   = "card"
    balance                = 0
    card_settlement_day    = 25
    card_settlement_asset_id = $bank.id
  }

  Invoke-JsonRequest -Method Post -Url "$BaseUrl/api/budgets" -Body @{
    category = "Food"
    amount   = 550000
  } | Out-Null

  Invoke-JsonRequest -Method Post -Url "$BaseUrl/api/transactions" -Body @{
    date            = "2026-03-05"
    type            = "expense"
    asset_id        = $card.id
    payment_method  = "card"
    card_asset_id   = $card.id
    settlement_date = "2026-03-25"
    category        = "Food"
    description     = "Weekly groceries"
    amount          = 84200
  } | Out-Null

  Invoke-JsonRequest -Method Post -Url "$BaseUrl/api/transactions" -Body @{
    date           = "2026-03-07"
    type           = "expense"
    asset_id       = $bank.id
    payment_method = "asset"
    category       = "Transport"
    description    = "Fuel"
    amount         = 67000
  } | Out-Null

  Invoke-JsonRequest -Method Post -Url "$BaseUrl/api/transactions" -Body @{
    date           = "2026-03-10"
    type           = "income"
    asset_id       = $bank.id
    payment_method = "asset"
    category       = "Salary"
    description    = "Monthly salary"
    amount         = 4200000
  } | Out-Null
}

function Capture-DonggriLedger {
  param([string]$Executable)

  $repo = Join-Path $workspace "donggri_gagyeobu"
  $shotDir = Join-Path $repo "docs\assets\screenshots"
  $pythonExe = Ensure-PythonVenv `
    -RepoPath $repo `
    -RequirementsPath (Join-Path $repo "requirements.txt") `
    -FallbackPackages @(
      "fastapi>=0.115.0",
      "uvicorn[standard]>=0.34.0",
      "sqlalchemy>=2.0.25",
      "pydantic>=2.10.0",
      "python-multipart>=0.0.9",
      "aiofiles>=24.1.0"
    )
  $captureDataDir = Join-Path $repo ".capture\donggri-data"
  Ensure-Directory -Path $captureDataDir

  $process = Start-BackgroundShell `
    -Name "donggri-ledger" `
    -WorkingDirectory $repo `
    -Environment @{ DONGGRI_LEDGER_DATA_DIR = $captureDataDir } `
    -Command "& '$pythonExe' launcher.py"

  try {
    Wait-ForUrl -Url "http://127.0.0.1:8000/health"
    Seed-DonggriLedger -BaseUrl "http://127.0.0.1:8000"

    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:8000/ui/" -OutputPath (Join-Path $shotDir "donggri-ledger-dashboard.png") -Width 1440 -Height 1120 -WaitMs 9000
    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:8000/ui/" -OutputPath (Join-Path $shotDir "donggri-ledger-mobile.png") -Width 430 -Height 932 -WaitMs 9000
  }
  finally {
    Stop-ProcessTree -Process $process
  }
}

function Prepare-AutoTradingFiles {
  param([string]$RepoPath)

  $envPath = Join-Path $RepoPath ".env"
  if (-not (Test-Path $envPath)) {
    Copy-Item (Join-Path $RepoPath ".env.example") $envPath -Force
  }

  $runtimeLocal = Join-Path $RepoPath "runtime_settings.local.json"
  if (-not (Test-Path $runtimeLocal)) {
    Copy-Item (Join-Path $RepoPath "runtime_settings.example.json") $runtimeLocal -Force
  }

  $stateFile = Join-Path $RepoPath "state.json"
  if (-not (Test-Path $stateFile)) {
    '{}' | Set-Content -Encoding utf8 -Path $stateFile
  }

  $modelFile = Join-Path $RepoPath "model_online.json"
  if (-not (Test-Path $modelFile)) {
    '{}' | Set-Content -Encoding utf8 -Path $modelFile
  }

  Ensure-Directory -Path (Join-Path $RepoPath "reports")
}

function Capture-AutoTrading {
  param([string]$Executable)

  $repo = Join-Path $workspace "Automethemoney"
  $shotDir = Join-Path $repo "docs\assets\screenshots"
  $pythonExe = Ensure-PythonVenv -RepoPath $repo -VenvName ".venv-docs" -RequirementsPath (Join-Path $repo "requirements.txt")
  Prepare-AutoTradingFiles -RepoPath $repo

  $process = Start-BackgroundShell `
    -Name "auto-trading" `
    -WorkingDirectory $repo `
    -Environment @{
      APP_HOST                = "127.0.0.1"
      APP_PORT                = "8099"
      ENABLE_AUTOTRADE        = "false"
      ENABLE_LIVE_EXECUTION   = "false"
      DEMO_ENABLE_MACRO       = "false"
      GOOGLE_TREND_ENABLED    = "false"
      PUMPFUN_ENABLED         = "false"
      SOCIAL_4CHAN_ENABLED    = "false"
      TELEGRAM_REPORT_ENABLED = "false"
      TELEGRAM_POLLING_ENABLED = "false"
    } `
    -Command "& '$pythonExe' web_app.py"

  try {
    Wait-ForUrl -Url "http://127.0.0.1:8099/health"

    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:8099/" -OutputPath (Join-Path $shotDir "strategy-studio-dashboard.png") -Width 1440 -Height 1100 -WaitMs 9000
    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:8099/" -OutputPath (Join-Path $shotDir "strategy-studio-mobile.png") -Width 430 -Height 932 -WaitMs 9000
  }
  finally {
    Stop-ProcessTree -Process $process
  }
}

function Seed-BloManagent {
  param([string]$ApiBase)

  $samples = @(
    @{
      name        = "Shery Tech Notes"
      mainUrl     = "https://example.tistory.com"
      platformOverride = "tistory"
      rssUrl      = "https://example.tistory.com/rss"
      description = "AI workflow and publishing notes"
    },
    @{
      name        = "Growth Memo"
      mainUrl     = "https://sample.blogspot.com"
      platformOverride = "blogger"
      rssUrl      = "https://sample.blogspot.com/feeds/posts/default"
      description = "Weekly review and analytics experiments"
    },
    @{
      name        = "Local Ops Lab"
      mainUrl     = "https://blog.naver.com/sampleops"
      platformOverride = "naver"
      rssUrl      = ""
      description = "Local-first blog ops tracking"
    }
  )

  foreach ($sample in $samples) {
    Invoke-JsonRequest -Method Post -Url "$ApiBase/api/blogs" -Body $sample | Out-Null
  }
}

function Capture-BloManagent {
  param([string]$Executable)

  $repo = Join-Path $workspace "BloManagent"
  $shotDir = Join-Path $repo "docs\assets\screenshots"

  Ensure-NodeModules -RepoPath $repo

  $process = Start-BackgroundShell `
    -Name "blo-managent" `
    -WorkingDirectory $repo `
    -Environment @{
      APP_PORT = "8787"
      WEB_PORT = "5173"
      DATA_DIR = (Join-Path $repo ".capture\blo-data")
    } `
    -Command "& npm.cmd run dev"

  try {
    Wait-ForUrl -Url "http://127.0.0.1:8787/api/dashboard"
    Wait-ForUrl -Url "http://127.0.0.1:5173/"
    Seed-BloManagent -ApiBase "http://127.0.0.1:8787"
    Start-Sleep -Seconds 3

    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:5173/blogs" -OutputPath (Join-Path $shotDir "blo-managent-blogs.png") -Width 1440 -Height 1100 -WaitMs 9000
    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:5173/settings" -OutputPath (Join-Path $shotDir "blo-managent-settings.png") -Width 1440 -Height 1100 -WaitMs 9000
  }
  finally {
    Stop-ProcessTree -Process $process
  }
}

function Capture-VibeOrchestrator {
  param([string]$Executable)

  $repo = Join-Path $workspace "Vibe_Cowork_Thinking\orchestrator"
  $shotDir = Join-Path $workspace "Vibe_Cowork_Thinking\docs\assets\screenshots"
  $pythonExe = Ensure-PythonVenv -RepoPath $repo -VenvName ".venv-docs" -RequirementsPath (Join-Path $repo "requirements.txt")

  $process = Start-BackgroundShell `
    -Name "vibe-orchestrator" `
    -WorkingDirectory $repo `
    -Environment @{
      RUNNER_BASE_URL = "http://127.0.0.1:8765"
      ORCH_ROOT_DIR   = (Join-Path $workspace "Vibe_Cowork_Thinking")
      ORCH_DATA_DIR   = (Join-Path $repo ".capture\data")
    } `
    -Command "& '$pythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8080"

  try {
    Wait-ForUrl -Url "http://127.0.0.1:8080/health"

    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:8080/" -OutputPath (Join-Path $shotDir "vibe-orchestrator-desktop.png") -Width 1440 -Height 1080 -WaitMs 9000
    Invoke-Capture -Executable $Executable -Url "http://127.0.0.1:8080/" -OutputPath (Join-Path $shotDir "vibe-orchestrator-mobile.png") -Width 430 -Height 932 -WaitMs 9000
  }
  finally {
    Stop-ProcessTree -Process $process
  }
}

$BrowserPath = Resolve-BrowserPath -Candidate $BrowserPath

$captureMap = @{
  "AI_BISEO"              = { Capture-AIBiseo -Executable $BrowserPath }
  "donggri_gagyeobu"      = { Capture-DonggriLedger -Executable $BrowserPath }
  "Automethemoney"        = { Capture-AutoTrading -Executable $BrowserPath }
  "BloManagent"           = { Capture-BloManagent -Executable $BrowserPath }
  "Vibe_Cowork_Thinking"  = { Capture-VibeOrchestrator -Executable $BrowserPath }
}

foreach ($target in $Targets) {
  if (-not $captureMap.ContainsKey($target)) {
    Write-Warning "Unsupported target: $target"
    continue
  }

  Invoke-Step -Label "capture :: $target" -Action $captureMap[$target]
}
