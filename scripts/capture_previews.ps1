param(
  [string]$BrowserPath,
  [int]$Width = 1280,
  [int]$Height = 900,
  [int]$WaitMs = 5000
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$projectsPath = Join-Path $root "projects.json"
$previewDir = Join-Path $root "assets\previews"
$metaDir = Join-Path $root "assets\meta"

function Resolve-BrowserPath {
  param([string]$Candidate)

  if ($Candidate) {
    return $Candidate
  }

  $knownPaths = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe"
  )

  foreach ($path in $knownPaths) {
    if (Test-Path $path) {
      return $path
    }
  }

  throw "Headless browser executable not found. Pass -BrowserPath explicitly."
}

function Get-Slug {
  param([string]$Value)

  $slug = $Value.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
  $slug = $slug.Trim("-")
  if ([string]::IsNullOrWhiteSpace($slug)) {
    return "project"
  }
  return $slug
}

function Invoke-Capture {
  param(
    [string]$Executable,
    [string]$Url,
    [string]$OutputPath,
    [int]$ShotWidth = $Width,
    [int]$ShotHeight = $Height
  )

  & $Executable --headless --disable-gpu --hide-scrollbars --window-size=$ShotWidth,$ShotHeight --virtual-time-budget=$WaitMs --screenshot=$OutputPath $Url | Out-Null
  if (-not (Test-Path $OutputPath)) {
    throw "Screenshot not created for $Url"
  }
}

if (-not (Test-Path $projectsPath)) {
  throw "projects.json not found. Run python generate_site.py first."
}

$BrowserPath = Resolve-BrowserPath -Candidate $BrowserPath
New-Item -ItemType Directory -Force -Path $previewDir | Out-Null
New-Item -ItemType Directory -Force -Path $metaDir | Out-Null

$projects = Get-Content -Path $projectsPath -Raw -Encoding utf8 | ConvertFrom-Json
$liveProjects = @($projects.repositories | Where-Object { $_.has_pages -and $_.live_url })

foreach ($project in $liveProjects) {
  $outputPath = Join-Path $previewDir ("{0}.png" -f (Get-Slug -Value $project.name))
  Invoke-Capture -Executable $BrowserPath -Url $project.live_url -OutputPath $outputPath
  Write-Host ("Captured {0} -> {1}" -f $project.name, $outputPath)
}

$rootIndex = (Resolve-Path (Join-Path $root "index.html")).Path.Replace("\", "/")
$rootUrl = "file:///$rootIndex"
$rootPreview = Join-Path $metaDir "root-hub-social.png"
Invoke-Capture -Executable $BrowserPath -Url $rootUrl -OutputPath $rootPreview -ShotWidth 1200 -ShotHeight 630
Write-Host ("Captured root hub -> {0}" -f $rootPreview)
