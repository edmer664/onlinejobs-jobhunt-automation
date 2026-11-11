<#
.SYNOPSIS
    Registers Windows Scheduled Tasks for multi-peak automated job scraping.
.DESCRIPTION
    Creates daily tasks in Windows Task Scheduler corresponding to:
    - AU Peak: 07:00 local time
    - UK Peak: 16:00 local time
    - US Peak: 22:00 local time
.PARAMETER Action
    Register (default), Unregister, or Status.
#>
[CmdletBinding()]
param (
    [ValidateSet("Register", "Unregister", "Status")]
    [string]$Action = "Register"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogsDir = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Resolve Python interpreter (prefer virtualenv)
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AltVenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} elseif (Test-Path $AltVenvPython) {
    $PythonExe = $AltVenvPython
} else {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Error "Python executable not found in PATH or .venv."
        exit 1
    }
}

$ScraperPath = Join-Path $ProjectRoot "src\scraper.py"

$Tasks = @(
    @{ Name = "JobHunt_Scrape_AU_Peak"; Time = "07:00"; Region = "AU"; Description = "JobHunt automated scrape at AU morning peak (07:00 local)" },
    @{ Name = "JobHunt_Scrape_UK_Peak"; Time = "16:00"; Region = "UK"; Description = "JobHunt automated scrape at UK morning peak (16:00 local)" },
    @{ Name = "JobHunt_Scrape_US_Peak"; Time = "22:00"; Region = "US"; Description = "JobHunt automated scrape at US morning peak (22:00 local)" }
)

switch ($Action) {
    "Status" {
        Write-Host "=== JobHunt Windows Scheduled Tasks Status ===" -ForegroundColor Cyan
        foreach ($t in $Tasks) {
            $task = Get-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue
            if ($task) {
                Write-Host " [INSTALLED] $($t.Name) - State: $($task.State) - Scheduled: $($t.Time)" -ForegroundColor Green
            } else {
                Write-Host " [NOT INSTALLED] $($t.Name)" -ForegroundColor Yellow
            }
        }
    }
    "Unregister" {
        Write-Host "Unregistering JobHunt Scheduled Tasks..." -ForegroundColor Cyan
        foreach ($t in $Tasks) {
            if (Get-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue) {
                Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false
                Write-Host "Unregistered: $($t.Name)" -ForegroundColor Yellow
            }
        }
        Write-Host "All JobHunt scheduled tasks removed." -ForegroundColor Green
    }
    "Register" {
        Write-Host "Registering JobHunt Scheduled Tasks in Windows Task Scheduler..." -ForegroundColor Cyan
        Write-Host "Project Root: $ProjectRoot"
        Write-Host "Python Path:  $PythonExe"

        foreach ($t in $Tasks) {
            $TaskAction = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScraperPath`" --pages 5 --region $($t.Region)" -WorkingDirectory $ProjectRoot
            $TaskTrigger = New-ScheduledTaskTrigger -Daily -At $t.Time
            $TaskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

            Register-ScheduledTask -TaskName $t.Name `
                -Action $TaskAction `
                -Trigger $TaskTrigger `
                -Settings $TaskSettings `
                -Description $t.Description `
                -Force | Out-Null

            Write-Host " Registered: $($t.Name) at $($t.Time) ($($t.Region) peak)" -ForegroundColor Green
        }
        Write-Host "All scheduled tasks registered successfully." -ForegroundColor Green
    }
}
