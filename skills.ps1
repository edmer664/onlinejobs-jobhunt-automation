#!/usr/bin/env pwsh
# skills.ps1 - Windows PowerShell runner for skill packaging and execution
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = "help",

    [Parameter(Position = 1)]
    [string]$TargetOrSkill = "",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs = @()
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Determine repo root (if executed from root or from scripts/)
if (Test-Path (Join-Path $scriptDir "skills")) {
    $rootDir = $scriptDir
} elseif (Test-Path (Join-Path (Split-Path -Parent $scriptDir) "skills")) {
    $rootDir = Split-Path -Parent $scriptDir
} else {
    $rootDir = $scriptDir
}

# Find python
$pythonBin = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonBin) {
    $pythonBin = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}
if (-not $pythonBin) {
    Write-Error "Python 3 is required but was not found in PATH."
    exit 1
}

function Show-Help {
    Write-Host @"
skills.ps1 - Cross-platform skill packager and runner

Usage:
  .\skills.ps1 install [target_dir]
      Install onlinejobs-proposal-generator skill to target directory
      (auto-detects .agents/skills, .cursor/skills, .claude/skills)

  .\skills.ps1 test
      Run automated regression tests for packaged skills (0 connects, 0 PII, secret codes)

  .\skills.ps1 run onlinejobs-proposal-generator [--jd "<text>"] [--config <path>]
      Evaluate job description and generate tailored proposal to stdout

  .\skills.ps1 --help | -h | help
      Show this help message
"@
}

switch ($Command) {
    "install" {
        $targetDir = if ($TargetOrSkill) { $TargetOrSkill } else { $null }
        if (-not $targetDir) {
            if (Test-Path (Join-Path $rootDir ".agents\skills")) {
                $targetDir = Join-Path $rootDir ".agents\skills"
            } elseif (Test-Path (Join-Path $rootDir ".cursor\skills")) {
                $targetDir = Join-Path $rootDir ".cursor\skills"
            } elseif (Test-Path (Join-Path $rootDir ".claude\skills")) {
                $targetDir = Join-Path $rootDir ".claude\skills"
            } else {
                $targetDir = Join-Path $rootDir ".agents\skills"
            }
        }
        $destDir = Join-Path $targetDir "onlinejobs-proposal-generator"
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }
        $sourceDir = Join-Path $rootDir "skills\onlinejobs-proposal-generator"
        Copy-Item -Path (Join-Path $sourceDir "*") -Destination $destDir -Recurse -Force
        Write-Host "[SUCCESS] Installed onlinejobs-proposal-generator to $destDir"
        exit 0
    }
    "test" {
        $enginePath = Join-Path $rootDir "src\proposal_engine.py"
        & $pythonBin $enginePath test
        exit $LASTEXITCODE
    }
    "run" {
        $enginePath = Join-Path $rootDir "src\proposal_engine.py"
        $runArgs = @("run")
        if ($TargetOrSkill) {
            $runArgs += $TargetOrSkill
        }
        if ($RemainingArgs) {
            foreach ($arg in $RemainingArgs) {
                if ($arg -eq "") {
                    $runArgs += '""'
                } else {
                    $runArgs += $arg
                }
            }
        }
        & $pythonBin $enginePath @runArgs
        exit $LASTEXITCODE
    }
    { $_ -in @("--help", "-h", "help", "") } {
        Show-Help
        exit 0
    }
    default {
        Write-Error "Unknown command: $Command"
        Show-Help
        exit 1
    }
}
