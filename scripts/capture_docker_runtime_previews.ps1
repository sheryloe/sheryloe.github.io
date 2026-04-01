param(
  [string[]]$Targets = @(
    "AI_BISEO",
    "AI_Writer_TISTORY",
    "Automethemoney",
    "BloManagent",
    "donggri_gagyeobu",
    "Vibe_Cowork_Thinking"
  ),
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runtimeDir = Join-Path $workspace ".docker-playwright-runtime"
$runtimeConfigDir = Join-Path $runtimeDir "configs"

function Ensure-Directory {
  param([Parameter(Mandatory = $true)][string]$Path)

  New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Write-Utf8NoBom {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Content
  )

  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Convert-ToContainerPath {
  param([Parameter(Mandatory = $true)][string]$Path)

  if (Test-Path $Path) {
    $resolved = (Resolve-Path $Path).Path
  }
  else {
    $leaf = Split-Path -Leaf $Path
    $parent = Split-Path -Parent $Path
    if (-not $parent) {
      throw "Path has no parent: $Path"
    }

    $missingSegments = New-Object System.Collections.Generic.List[string]
    while ($parent -and -not (Test-Path $parent)) {
      $missingSegments.Insert(0, (Split-Path -Leaf $parent))
      $parent = Split-Path -Parent $parent
    }

    if (-not $parent) {
      throw "Unable to resolve parent path for $Path"
    }

    $resolvedParent = (Resolve-Path $parent).Path
    foreach ($segment in $missingSegments) {
      $resolvedParent = Join-Path $resolvedParent $segment
    }
    $resolved = Join-Path $resolvedParent $leaf
  }

  if (-not $resolved.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Path is outside workspace: $resolved"
  }

  $relative = $resolved.Substring($workspace.Length).TrimStart("\", "/").Replace("\", "/")
  return "/workspace/$relative"
}

function Ensure-PlaywrightRuntime {
  Ensure-Directory -Path $runtimeDir
  Ensure-Directory -Path $runtimeConfigDir

  $captureJsPath = Join-Path $runtimeDir "capture.js"
  $js = @'
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const configPath = process.argv[2];
if (!configPath) {
  throw new Error("config path is required");
}

const config = JSON.parse(fs.readFileSync(configPath, "utf8"));

async function waitForProbe(url, attempts, delayMs) {
  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await fetch(url, { method: "GET" });
      if (response.ok || response.status < 500) {
        return;
      }
    } catch (error) {
      // retry
    }

    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }

  throw new Error(`Timed out waiting for ${url}`);
}

async function main() {
  await waitForProbe(config.probe_url, config.probe_attempts ?? 60, config.probe_delay_ms ?? 2000);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: {
      width: config.viewport?.width ?? 1440,
      height: config.viewport?.height ?? 1024,
    },
    locale: "ko-KR",
    colorScheme: "light",
  });

  for (const shot of config.shots) {
    const page = await context.newPage();
    await page.goto(shot.url, { waitUntil: "domcontentloaded" });
    if (shot.selector) {
      await page.waitForSelector(shot.selector, { timeout: shot.selector_timeout_ms ?? 15000 });
    }
    await page.waitForTimeout(shot.wait_ms ?? 3000);

    const targetDir = path.dirname(shot.output);
    fs.mkdirSync(targetDir, { recursive: true });
    await page.screenshot({
      path: shot.output,
      fullPage: shot.full_page ?? true,
    });
    await page.close();
  }

  await context.close();
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
'@
  Write-Utf8NoBom -Path $captureJsPath -Content $js

  $playwrightModulePath = Join-Path $runtimeDir "node_modules\playwright"
  if (Test-Path $playwrightModulePath) {
    return
  }

  docker run --rm `
    -v "${runtimeDir}:/work" `
    -w /work `
    node:20-bookworm `
    bash -lc "if [ ! -f package.json ]; then npm init -y >/dev/null 2>&1; fi; npm install playwright@1.51.1 >/dev/null 2>&1" | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to prepare Docker Playwright runtime"
  }
}

function Initialize-BootstrapArtifacts {
  param([Parameter(Mandatory = $true)][hashtable]$Config)

  $created = New-Object System.Collections.Generic.List[string]
  $repoPath = $Config.repo_path

  if ($Config.bootstrap_env_example) {
    $envPath = Join-Path $repoPath ".env"
    $examplePath = Join-Path $repoPath ".env.example"
    if (-not (Test-Path $envPath) -and (Test-Path $examplePath)) {
      Copy-Item -Path $examplePath -Destination $envPath
      $created.Add($envPath)
    }
  }

  foreach ($item in @($Config.bootstrap_files)) {
    if (-not $item) {
      continue
    }

    $targetPath = Join-Path $repoPath $item.path
    if (Test-Path $targetPath) {
      continue
    }

    if ($item.type -eq "directory") {
      Ensure-Directory -Path $targetPath
      $created.Add($targetPath)
      continue
    }

    Ensure-Directory -Path (Split-Path -Parent $targetPath)

    if ($item.source) {
      Copy-Item -Path (Join-Path $repoPath $item.source) -Destination $targetPath
    }
    else {
      Write-Utf8NoBom -Path $targetPath -Content ([string]$item.content)
    }

    $created.Add($targetPath)
  }

  return $created
}

function Remove-BootstrapArtifacts {
  param([System.Collections.Generic.List[string]]$Paths)

  if (-not $Paths) {
    return
  }

  for ($index = $Paths.Count - 1; $index -ge 0; $index -= 1) {
    $path = $Paths[$index]
    if (Test-Path $path) {
      Remove-Item -Path $path -Force -Recurse
    }
  }
}

function Get-Targets {
  $base = $workspace
  return @{
    "AI_BISEO" = @{
      repo_path = Join-Path $base "AI_BISEO"
      compose_file = Join-Path $base "AI_BISEO\docker-compose.yml"
      project_name = "codex-ai-biseo"
      probe_url = "http://ai_biseo_server:3000/health"
      shots = @(
        @{
          url = "http://ai_biseo_server:3000/dashboard/"
          output = Join-Path $base "AI_BISEO\docs\assets\screenshots\ai-biseo-overview.png"
          wait_ms = 4500
          selector = ".shell"
        },
        @{
          url = "http://ai_biseo_server:3000/dashboard/assistant.html"
          output = Join-Path $base "AI_BISEO\docs\assets\screenshots\ai-biseo-assistant.png"
          wait_ms = 4500
          selector = ".shell"
        },
        @{
          url = "http://ai_biseo_server:3000/dashboard/pipeline.html"
          output = Join-Path $base "AI_BISEO\docs\assets\screenshots\ai-biseo-pipeline.png"
          wait_ms = 4500
          selector = ".shell"
        }
      )
    }
    "AI_Writer_TISTORY" = @{
      repo_path = Join-Path $base "AI_Writer_TISTORY"
      compose_file = Join-Path $base "AI_Writer_TISTORY\docker-compose.yml"
      project_name = "codex-ai-writer"
      probe_url = "http://ai_biseo_server:3000/health"
      bootstrap_env_example = $true
      shots = @(
        @{
          url = "http://ai_biseo_server:3000/dashboard/"
          output = Join-Path $base "AI_Writer_TISTORY\docs\assets\screenshots\ai-writer-overview.png"
          wait_ms = 4500
          selector = ".shell"
        },
        @{
          url = "http://ai_biseo_server:3000/dashboard/pipeline.html"
          output = Join-Path $base "AI_Writer_TISTORY\docs\assets\screenshots\ai-writer-pipeline.png"
          wait_ms = 4500
          selector = ".shell"
        }
      )
    }
    "Automethemoney" = @{
      repo_path = Join-Path $base "Automethemoney"
      compose_file = Join-Path $base "Automethemoney\docker-compose.yml"
      project_name = "codex-auto-trading"
      probe_url = "http://app:8099/health"
      bootstrap_env_example = $true
      bootstrap_files = @(
        @{
          path = "reports"
          type = "directory"
        },
        @{
          path = "state.json"
          content = "{}"
        },
        @{
          path = "model_online.json"
          content = "{}"
        },
        @{
          path = "runtime_settings.local.json"
          source = "runtime_settings.example.json"
        }
      )
      shots = @(
        @{
          url = "http://app:8099/"
          output = Join-Path $base "Automethemoney\docs\assets\screenshots\auto-trading-dashboard.png"
          wait_ms = 4500
          selector = "body"
        }
      )
    }
    "BloManagent" = @{
      repo_path = Join-Path $base "BloManagent"
      compose_file = Join-Path $base "BloManagent\docker-compose.yml"
      project_name = "codex-blo-managent"
      probe_url = "http://app:8787/api/dashboard"
      shots = @(
        @{
          url = "http://app:8787/"
          output = Join-Path $base "BloManagent\docs\assets\screenshots\blo-managent-dashboard.png"
          wait_ms = 4000
          selector = "body"
        }
      )
    }
    "donggri_gagyeobu" = @{
      repo_path = Join-Path $base "donggri_gagyeobu"
      compose_file = Join-Path $base "donggri_gagyeobu\docker-compose.yml"
      project_name = "codex-donggri-ledger"
      probe_url = "http://app:8000/health"
      shots = @(
        @{
          url = "http://app:8000/ui/"
          output = Join-Path $base "donggri_gagyeobu\docs\assets\screenshots\donggri-ledger-ui.png"
          wait_ms = 4000
          selector = "body"
        }
      )
    }
    "Vibe_Cowork_Thinking" = @{
      repo_path = Join-Path $base "Vibe_Cowork_Thinking\orchestrator"
      compose_file = Join-Path $base "Vibe_Cowork_Thinking\orchestrator\docker-compose.yml"
      project_name = "codex-vibe-orchestrator"
      probe_url = "http://orchestrator:8080/health"
      shots = @(
        @{
          url = "http://orchestrator:8080/"
          output = Join-Path $base "Vibe_Cowork_Thinking\docs\assets\screenshots\vibe-orchestrator-home.png"
          wait_ms = 4000
          selector = "body"
        }
      )
    }
  }
}

function Invoke-TargetCapture {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][hashtable]$Config
  )

  Write-Host ("[{0}] docker capture :: {1}" -f (Get-Date -Format "HH:mm:ss"), $Name)

  $composeArgs = @("-p", $Config.project_name, "-f", $Config.compose_file)
  $networkName = "{0}_default" -f $Config.project_name
  $containerConfigPath = "/runtime/configs/{0}.json" -f $Config.project_name
  $configPath = Join-Path $runtimeConfigDir ("{0}.json" -f $Config.project_name)

  $captureConfig = @{
    probe_url = $Config.probe_url
    probe_attempts = 60
    probe_delay_ms = 2000
    viewport = @{
      width = 1440
      height = 1024
    }
    shots = @()
  }

  foreach ($shot in $Config.shots) {
    $captureConfig.shots += @{
      url = $shot.url
      output = (Convert-ToContainerPath -Path $shot.output)
      wait_ms = $shot.wait_ms
      full_page = $true
      selector = $shot.selector
    }
  }

  Write-Utf8NoBom -Path $configPath -Content ($captureConfig | ConvertTo-Json -Depth 8)

  $bootstrapPaths = Initialize-BootstrapArtifacts -Config $Config

  Push-Location $Config.repo_path
  try {
    if ($SkipBuild) {
      docker compose @composeArgs up -d | Out-Null
    }
    else {
      docker compose @composeArgs up -d --build | Out-Null
    }
    if ($LASTEXITCODE -ne 0) {
      throw "docker compose up failed for $Name"
    }

    docker run --rm `
      --network $networkName `
      -v "${workspace}:/workspace" `
      -v "${runtimeDir}:/runtime" `
      -w /runtime `
      mcr.microsoft.com/playwright:v1.51.1-noble `
      bash -lc "node capture.js $containerConfigPath" | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "docker runtime capture failed for $Name"
    }
  }
  finally {
    docker compose @composeArgs down | Out-Null
    Pop-Location
    Remove-BootstrapArtifacts -Paths $bootstrapPaths
  }
}

Ensure-PlaywrightRuntime
$allTargets = Get-Targets

foreach ($target in $Targets) {
  if (-not $allTargets.ContainsKey($target)) {
    throw "Unknown target: $target"
  }

  Invoke-TargetCapture -Name $target -Config $allTargets[$target]
}
