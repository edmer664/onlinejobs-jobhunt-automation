# Registers Windows Scheduled Tasks for US, UK, and AU Peak Client Hours (Philippine Time)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$PythonExe = (Get-Command python).Source
$ScraperPath = Join-Path $ProjectRoot "src\scraper.py"

$PeakTimes = @(
    @{ Name = "JobHunt_Peak_AU_0700"; Time = "07:00"; Region = "AU" },
    @{ Name = "JobHunt_Peak_AU_0930"; Time = "09:30"; Region = "AU" },
    @{ Name = "JobHunt_Peak_UK_1700"; Time = "17:00"; Region = "UK" },
    @{ Name = "JobHunt_Peak_UK_1930"; Time = "19:30"; Region = "UK" },
    @{ Name = "JobHunt_Peak_US_2100"; Time = "21:00"; Region = "US" },
    @{ Name = "JobHunt_Peak_US_2330"; Time = "23:30"; Region = "US" },
    @{ Name = "JobHunt_Peak_US_0100"; Time = "01:00"; Region = "US" },
    @{ Name = "JobHunt_Peak_US_0330"; Time = "03:30"; Region = "US" }
)

foreach ($pt in $PeakTimes) {
    $Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScraperPath`" --pages 10 --region $($pt.Region)" -WorkingDirectory $ProjectRoot
    $Trigger = New-ScheduledTaskTrigger -Daily -At $pt.Time
    Register-ScheduledTask -TaskName $pt.Name -Action $Action -Trigger $Trigger -Description "JobHunt automated scrape at $($pt.Region) peak hour ($($pt.Time) PHT)" -Force | Out-Null
    Write-Host "Registered scheduled task: $($pt.Name) at $($pt.Time) PHT ($($pt.Region) Peak)"
}
