param(
  [switch]$DryRun,
  [string[]]$Repositories
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$configPath = Join-Path $root "site-config.json"
$config = Get-Content -Path $configPath -Raw -Encoding utf8 | ConvertFrom-Json

function Get-RepositoryMetadata {
  param(
    [string]$Name,
    [object]$Override
  )

  $defaultHomepage = if ($Name -eq "sheryloe.github.io") {
    $config.site_url
  } else {
    "$($config.site_url)$([uri]::EscapeDataString($Name))/"
  }

  [pscustomobject]@{
    name = $Name
    description = $Override.description
    homepage = if ($Override.live_url) { $Override.live_url } else { $defaultHomepage }
    topics = @($Override.repo_topics)
  }
}

$entries = @()
foreach ($property in $config.repository_overrides.PSObject.Properties) {
  $entry = Get-RepositoryMetadata -Name $property.Name -Override $property.Value
  if ($Repositories.Count -gt 0 -and $entry.name -notin $Repositories) {
    continue
  }
  $entries += $entry
}

if (-not $entries) {
  throw "No repositories matched the requested filter."
}

if ($DryRun) {
  $entries |
    Select-Object name, description, homepage, @{ Name = "topics"; Expression = { $_.topics -join "," } } |
    Format-Table -AutoSize
  return
}

if (-not $env:GITHUB_TOKEN) {
  throw "GITHUB_TOKEN environment variable is required. Run with -DryRun to preview only."
}

$headers = @{
  Authorization = "Bearer $($env:GITHUB_TOKEN)"
  Accept = "application/vnd.github+json"
  "X-GitHub-Api-Version" = "2022-11-28"
  "User-Agent" = "sheryloe-repository-metadata-sync"
}

foreach ($entry in $entries) {
  $repoApi = "https://api.github.com/repos/$($config.username)/$($entry.name)"
  $repoBody = @{
    description = $entry.description
    homepage = $entry.homepage
  } | ConvertTo-Json

  Invoke-RestMethod -Method Patch -Uri $repoApi -Headers $headers -Body $repoBody -ContentType "application/json" | Out-Null

  if ($entry.topics.Count -gt 0) {
    $topicsApi = "https://api.github.com/repos/$($config.username)/$($entry.name)/topics"
    $topicsBody = @{
      names = @($entry.topics)
    } | ConvertTo-Json

    Invoke-RestMethod -Method Put -Uri $topicsApi -Headers $headers -Body $topicsBody -ContentType "application/json" | Out-Null
  }

  Write-Output "Updated $($entry.name)"
}

Write-Output "Repository description, homepage, and topics sync complete."
