<#
.SYNOPSIS
    Takes a Windows machine from "the content is unpacked" to "the car is driving".

.DESCRIPTION
    Every step of this bring-up used to be hand-typed, and every hand-typed step carried an
    assumption about the machine: that the engine sits under C:\Program Files\Epic Games\UE_5.4, that
    the drive root is writable, that a partial clone can serve any blob. Each of those was wrong on
    the first machine that tried them. This script asks the machine instead:

      1. Discover  -- find every installed Unreal Engine and read its real version from Build.version
      2. Check     -- the C++ toolchain, the free disk, and whether the city is actually on disk
      3. Gate      -- refuse to build against an engine the code was never written for, unless told to
      4. Build     -- project files, then NYCSimEditor, with the first compile error explained
      5. Import    -- restricted to the tiles present on disk, smoke run first
      6. Play      -- the editor on /Game/NYCSim/Maps/NYC, or the standalone window

    Nothing here is destructive: it builds, imports and launches. It writes only under
    unreal/NYCSim/{Binaries,Intermediate,Saved,Content}.

.PARAMETER EnginePath
    Skip discovery and use this engine root (the directory that contains Engine\Build\BatchFiles).

.PARAMETER DiscoverOnly
    Report every engine found and stop. Answers "where is my engine" and nothing else.

.PARAMETER AllowEngineVersion
    Build against an engine other than the 5.4 the project declares. The ten API signatures in
    unreal\COMPILE_CHECKLIST.md section 7 were reviewed against 5.4 only.

.PARAMETER SkipBuild
    Assume the editor target is already built.

.PARAMETER SkipSmoke
    Go straight to the full import without the two-tile proof.

.PARAMETER SkipImport
    Build only. Useful when the world is already imported.

.PARAMETER Play
    Launch the standalone game window instead of the editor.

.PARAMETER ResX
    Standalone window width. Default 2560.

.PARAMETER ResY
    Standalone window height. Default 1440.

.EXAMPLE
    .\unreal\tools\bring_up.ps1 -DiscoverOnly
    Lists the engines this machine has, with the version each one really is.

.EXAMPLE
    .\unreal\tools\bring_up.ps1
    The whole chain: build, smoke import, full import, open the editor.

.EXAMPLE
    .\unreal\tools\bring_up.ps1 -SkipBuild -SkipImport -Play
    Just start the game.
#>
[CmdletBinding()]
param(
    [string] $EnginePath,
    [switch] $DiscoverOnly,
    [switch] $AllowEngineVersion,
    [switch] $SkipBuild,
    [switch] $SkipSmoke,
    [switch] $SkipImport,
    [switch] $Play,
    [int]    $ResX = 2560,
    [int]    $ResY = 1440
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------------------------------

# The engine version the project declares and the only one COMPILE_CHECKLIST section 7 was reviewed
# against. Keep in step with EngineAssociation in NYCSim.uproject.
$script:WantedMajor = 5
$script:WantedMinor = 4

# Build plus derived data cache. Measured on a full city import; a smoke run needs far less, but the
# script cannot know in advance which one the caller is about to do.
$script:NeedFreeGigabytes = 30

# Which section of unreal\COMPILE_CHECKLIST.md covers a first-build error in which file. The checklist
# names the function and the handful of lines involved, so a compile error in a listed file is a
# local edit rather than a design problem.
$script:ChecklistSections = [ordered]@{
    'NYCWaterActor.cpp'          = '7.1 and 7.2 -- FRectangleMeshGenerator member names, UDynamicMeshComponent::SetMesh'
    'NYCSkyTimeSubsystem.cpp'    = '7.3 and 7.4 -- UVolumetricCloudComponent::Material, ExponentialHeightFog setters'
    'NYCWeatherSubsystem.cpp'    = '7.5 -- UNiagaraComponent::SetVariableFloat vs SetFloatParameter'
    'NYCTerrainImport.cpp'       = '7.6 to 7.8 -- ALandscape::Import argument order, FImageUtils::LoadImage, CreateTransient'
    'NYCImportCommandlet.cpp'    = '7.9 -- FPythonCommandEx field names'
    'import_assets.py'           = '7.10 -- the unreal.* Python API surface'
    'build_levels.py'            = '7.10 -- the unreal.* Python API surface'
    'import_world.py'            = '7.10 -- the unreal.* Python API surface'
}

# ---------------------------------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------------------------------

$script:PhaseNumber = 0

function Write-Phase {
    param([Parameter(Mandatory)][string] $Title)
    $script:PhaseNumber++
    Write-Host ''
    Write-Host ("=== {0}. {1} " -f $script:PhaseNumber, $Title).PadRight(99, '=') -ForegroundColor Cyan
}

function Write-Detail {
    param([Parameter(Mandatory)][string] $Message)
    Write-Host "    $Message"
}

function Write-Good {
    param([Parameter(Mandatory)][string] $Message)
    Write-Host "    $Message" -ForegroundColor Green
}

function Write-Warn {
    param([Parameter(Mandatory)][string] $Message)
    Write-Host "    $Message" -ForegroundColor Yellow
}

# Every abort goes through here, so every abort states the reason and the next step.
function Stop-WithReason {
    param(
        [Parameter(Mandatory)][string] $Reason,
        [string[]] $NextSteps = @()
    )
    Write-Host ''
    Write-Host "STOPPED: $Reason" -ForegroundColor Red
    foreach ($step in $NextSteps) {
        Write-Host "  -> $step" -ForegroundColor Yellow
    }
    Write-Host ''
    exit 1
}

# ---------------------------------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------------------------------

function Get-RepositoryRoot {
    # This script lives at <repo>\unreal\tools\bring_up.ps1.
    $toolsDir = Split-Path -Parent $PSCommandPath
    $root = Resolve-Path (Join-Path $toolsDir '..\..')
    $marker = Join-Path $root 'unreal\NYCSim\NYCSim.uproject'
    if (-not (Test-Path -LiteralPath $marker)) {
        Stop-WithReason -Reason "this script is not inside the NYCSim repository (no $marker)" -NextSteps @(
            'Run it from the clone: .\unreal\tools\bring_up.ps1',
            'Do not copy the script elsewhere -- it locates the project relative to itself.'
        )
    }
    return $root.Path
}

# ---------------------------------------------------------------------------------------------------
# Phase 1: find every engine, and read what version it really is
# ---------------------------------------------------------------------------------------------------

function Get-EngineVersion {
    <#
      The folder name lies. An Epic install directory called UE_5.4 can hold 5.5 after an in-place
      upgrade, and a source build's directory is named whatever the person cloning it chose. The only
      answer is Engine\Build\Build.version.
    #>
    param([Parameter(Mandatory)][string] $Root)

    $versionFile = Join-Path $Root 'Engine\Build\Build.version'
    if (-not (Test-Path -LiteralPath $versionFile)) { return $null }

    try {
        $doc = Get-Content -LiteralPath $versionFile -Raw | ConvertFrom-Json
    } catch {
        Write-Verbose "unreadable Build.version at ${versionFile}: $($_.Exception.Message)"
        return $null
    }

    $names = $doc.PSObject.Properties.Name
    if (-not ($names -contains 'MajorVersion' -and $names -contains 'MinorVersion')) { return $null }

    $patch = 0
    if ($names -contains 'PatchVersion' -and $null -ne $doc.PatchVersion) { $patch = [int] $doc.PatchVersion }

    return [pscustomobject]@{
        Major = [int] $doc.MajorVersion
        Minor = [int] $doc.MinorVersion
        Patch = $patch
        Text  = ('{0}.{1}.{2}' -f [int] $doc.MajorVersion, [int] $doc.MinorVersion, $patch)
    }
}

function Test-EngineRoot {
    param([Parameter(Mandatory)][string] $Root)
    return (Test-Path -LiteralPath (Join-Path $Root 'Engine\Build\BatchFiles\Build.bat'))
}

function Add-EngineCandidate {
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()][System.Collections.ArrayList] $Into,
        [AllowNull()][AllowEmptyString()][string] $Root = '',
        [Parameter(Mandatory)][string] $Source
    )
    if ([string]::IsNullOrWhiteSpace($Root)) { return }

    try { $full = (Resolve-Path -LiteralPath $Root).Path } catch { return }
    if (-not (Test-EngineRoot -Root $full)) { return }
    if ($Into | Where-Object { $_.Root -eq $full }) { return }

    $version = Get-EngineVersion -Root $full
    [void] $Into.Add([pscustomobject]@{
        Root    = $full
        Version = $version
        Source  = $Source
    })
}

function Get-EnginesFromLauncher {
    param([Parameter(Mandatory)][AllowEmptyCollection()][System.Collections.ArrayList] $Into)

    if ([string]::IsNullOrWhiteSpace($env:ProgramData)) { return }
    $dat = Join-Path $env:ProgramData 'Epic\UnrealEngineLauncher\LauncherInstalled.dat'
    if (-not (Test-Path -LiteralPath $dat)) { return }

    try {
        $doc = Get-Content -LiteralPath $dat -Raw | ConvertFrom-Json
    } catch {
        Write-Warn "LauncherInstalled.dat is not readable JSON: $($_.Exception.Message)"
        return
    }
    if (-not ($doc.PSObject.Properties.Name -contains 'InstallationList')) { return }

    foreach ($entry in $doc.InstallationList) {
        $names = $entry.PSObject.Properties.Name
        if (-not ($names -contains 'InstallLocation')) { continue }
        # AppName is UE_5.4 for engines and a long id for marketplace content; the Build.version check
        # in Add-EngineCandidate rejects anything that is not an engine, so no name filter is needed.
        Add-EngineCandidate -Into $Into -Root $entry.InstallLocation -Source 'Epic launcher'
    }
}

function Get-EnginesFromRegistry {
    param([Parameter(Mandatory)][AllowEmptyCollection()][System.Collections.ArrayList] $Into)

    # Binary installs register here, one subkey per version, with InstalledDirectory.
    $machineKey = 'HKLM:\SOFTWARE\EpicGames\Unreal Engine'
    if (Test-Path -LiteralPath $machineKey) {
        foreach ($sub in (Get-ChildItem -LiteralPath $machineKey -ErrorAction SilentlyContinue)) {
            $value = (Get-ItemProperty -LiteralPath $sub.PSPath -ErrorAction SilentlyContinue)
            if ($null -ne $value -and ($value.PSObject.Properties.Name -contains 'InstalledDirectory')) {
                Add-EngineCandidate -Into $Into -Root $value.InstalledDirectory -Source "registry $($sub.PSChildName)"
            }
        }
    }

    # Source builds register here instead: value name is the .uproject GUID, value data is the path.
    $userKey = 'HKCU:\Software\Epic Games\Unreal Engine\Builds'
    if (Test-Path -LiteralPath $userKey) {
        $props = Get-ItemProperty -LiteralPath $userKey -ErrorAction SilentlyContinue
        if ($null -ne $props) {
            foreach ($prop in $props.PSObject.Properties) {
                if ($prop.Name -like 'PS*') { continue }
                Add-EngineCandidate -Into $Into -Root ([string] $prop.Value) -Source 'source build'
            }
        }
    }
}

function Get-EnginesFromDriveScan {
    param([Parameter(Mandatory)][AllowEmptyCollection()][System.Collections.ArrayList] $Into)

    # Last resort, and the reason this script exists: an engine somewhere neither the launcher nor the
    # registry admits to. Depth is bounded so this stays seconds rather than minutes.
    if (-not (Get-Command Get-CimInstance -ErrorAction SilentlyContinue)) { return }
    $drives = Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType = 3' -ErrorAction SilentlyContinue
    if ($null -eq $drives) { return }

    foreach ($drive in $drives) {
        foreach ($prefix in @('', 'Program Files\Epic Games', 'Epic Games', 'UnrealEngine', 'UE')) {
            $base = if ($prefix -eq '') { "$($drive.DeviceID)\" } else { Join-Path "$($drive.DeviceID)\" $prefix }
            if (-not (Test-Path -LiteralPath $base)) { continue }
            $found = Get-ChildItem -LiteralPath $base -Directory -Recurse -Depth 1 -ErrorAction SilentlyContinue |
                     Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'Engine\Build\BatchFiles\Build.bat') }
            foreach ($dir in $found) {
                Add-EngineCandidate -Into $Into -Root $dir.FullName -Source "found on $($drive.DeviceID)"
            }
        }
    }
}

function Find-Engines {
    $found = New-Object System.Collections.ArrayList
    Get-EnginesFromLauncher  -Into $found
    Get-EnginesFromRegistry  -Into $found
    Get-EnginesFromDriveScan -Into $found
    return $found
}

function Select-Engine {
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]] $Candidates,
        [switch] $AllowAnyVersion
    )

    $wanted = $Candidates | Where-Object {
        $null -ne $_.Version -and $_.Version.Major -eq $script:WantedMajor -and $_.Version.Minor -eq $script:WantedMinor
    }
    if ($wanted) { return @($wanted)[0] }

    if (-not $AllowAnyVersion) {
        $have = ($Candidates | ForEach-Object {
            $v = if ($null -eq $_.Version) { 'unknown version' } else { $_.Version.Text }
            "$v at $($_.Root)"
        }) -join '; '
        Stop-WithReason -Reason ("no Unreal {0}.{1} on this machine (found: {2})" -f $script:WantedMajor, $script:WantedMinor, $have) -NextSteps @(
            "Install $($script:WantedMajor).$($script:WantedMinor) from the Epic Games Launcher: Unreal Engine -> Library -> + -> pick $($script:WantedMajor).$($script:WantedMinor).",
            "NYCSim.uproject declares EngineAssociation $($script:WantedMajor).$($script:WantedMinor), and unreal\COMPILE_CHECKLIST.md section 7 reviewed the ten risky API signatures against that version only.",
            'To build against what you have anyway: re-run with -AllowEngineVersion (expect compile errors the checklist does not cover).'
        )
    }

    $newest = $Candidates |
        Where-Object { $null -ne $_.Version } |
        Sort-Object { $_.Version.Major * 10000 + $_.Version.Minor * 100 + $_.Version.Patch } -Descending |
        Select-Object -First 1
    if (-not $newest) {
        Stop-WithReason -Reason 'every engine found has an unreadable Engine\Build\Build.version' -NextSteps @(
            'Pass the engine root explicitly: -EnginePath "D:\UE_5.4"'
        )
    }
    Write-Warn "building against $($newest.Version.Text) because -AllowEngineVersion was given; the code was written for $($script:WantedMajor).$($script:WantedMinor)."
    return $newest
}

# ---------------------------------------------------------------------------------------------------
# Phase 2: toolchain, disk, and whether the city is on disk at all
# ---------------------------------------------------------------------------------------------------

function Test-Toolchain {
    # vswhere ships in the 32-bit Program Files on every Visual Studio 2017 and later install.
    $vswhere = $null
    foreach ($base in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
        if ([string]::IsNullOrWhiteSpace($base)) { continue }
        $candidate = Join-Path $base 'Microsoft Visual Studio\Installer\vswhere.exe'
        if (Test-Path -LiteralPath $candidate) { $vswhere = $candidate; break }
    }
    if ($null -eq $vswhere) {
        Stop-WithReason -Reason 'Visual Studio 2022 is not installed (no vswhere.exe)' -NextSteps @(
            'Install the Visual Studio 2022 Build Tools from https://visualstudio.microsoft.com/downloads/',
            'Select the workload "Desktop development with C++" (Microsoft.VisualStudio.Workload.NativeDesktop).',
            'Unreal also wants the "Game development with C++" workload for its own tooling; the C++ tools alone are enough to compile this project.'
        )
    }

    $install = & $vswhere @(
        '-latest', '-products', '*',
        '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
        '-property', 'installationPath') 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($install)) {
        Stop-WithReason -Reason 'Visual Studio is installed but the C++ toolset (VC.Tools.x86.x64) is missing' -NextSteps @(
            'Open the Visual Studio Installer, Modify, and tick "Desktop development with C++".',
            'The MSVC v143 toolset and the Windows 10/11 SDK are the two parts that matter.'
        )
    }
    Write-Good "C++ toolset: $(@($install)[0])"
}

function Test-FreeDisk {
    param([Parameter(Mandatory)][string] $RepoRoot)

    if (-not (Get-Command Get-CimInstance -ErrorAction SilentlyContinue)) {
        Write-Warn 'no Get-CimInstance on this host; skipping the free-space check'
        return
    }
    $qualifier = (Split-Path -Qualifier (Resolve-Path -LiteralPath $RepoRoot).Path)
    $drive = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID = '$qualifier'" -ErrorAction SilentlyContinue
    if ($null -eq $drive) {
        Write-Warn "could not measure free space on $qualifier; skipping the check"
        return
    }
    $freeGb = [math]::Round($drive.FreeSpace / 1GB, 1)
    if ($freeGb -lt $script:NeedFreeGigabytes) {
        Stop-WithReason -Reason "$freeGb GB free on $qualifier, and the build plus derived data cache wants about $($script:NeedFreeGigabytes) GB" -NextSteps @(
            'Free space, or move the clone to a roomier drive and re-run from there.',
            'A -maxtiles smoke import needs far less, but the compile alone is around 15 GB with the intermediates.'
        )
    }
    Write-Good "$freeGb GB free on $qualifier"
}

function Get-PresentTiles {
    <#
      The manifest describes the whole city. A machine that unpacked one region has a fraction of it,
      and a bare -run=NYCImport then reports thousands of missing sources. The tiles that are actually
      on disk are the ones to import, and the directory names are exactly the manifest's tile ids.
    #>
    param([Parameter(Mandatory)][string] $RepoRoot)

    $tilesDir = Join-Path $RepoRoot 'data\processed\tiles'
    if (-not (Test-Path -LiteralPath $tilesDir)) { return @() }
    return @(Get-ChildItem -LiteralPath $tilesDir -Directory -ErrorAction SilentlyContinue |
             Select-Object -ExpandProperty Name |
             Sort-Object)
}

function Test-Content {
    param([Parameter(Mandatory)][string] $RepoRoot)

    $manifest = Join-Path $RepoRoot 'data\processed\unreal_manifest.json'
    if (-not (Test-Path -LiteralPath $manifest)) {
        Stop-WithReason -Reason 'data\processed\unreal_manifest.json is missing, so there is nothing to import' -NextSteps @(
            'Unpack the content package: see section 9b of unreal\README.md.',
            'Or regenerate the manifest from a full pipeline run: python -m nycsim_pipeline.unreal.manifest'
        )
    }

    $tiles = @(Get-PresentTiles -RepoRoot $RepoRoot)
    if ($tiles.Count -eq 0) {
        Stop-WithReason -Reason 'data\processed\tiles is empty, so the city is not on this machine' -NextSteps @(
            'Unpack the content package: see section 9b of unreal\README.md.'
        )
    }

    $meshes = Join-Path $RepoRoot 'blender_out\tiles'
    $meshCount = 0
    if (Test-Path -LiteralPath $meshes) {
        $meshCount = @(Get-ChildItem -LiteralPath $meshes -Directory -ErrorAction SilentlyContinue).Count
    }
    if ($meshCount -eq 0) {
        Stop-WithReason -Reason 'blender_out\tiles is empty, so the tile meshes are not on this machine' -NextSteps @(
            'The content package carries both data\processed and blender_out; unpack all of its parts.'
        )
    }

    Write-Good "$($tiles.Count) tile(s) of pipeline data, $meshCount tile(s) of meshes"
    return $tiles
}

# ---------------------------------------------------------------------------------------------------
# Phase 4: build, with the first compile error explained
# ---------------------------------------------------------------------------------------------------

function Get-FirstCompileError {
    param([Parameter(Mandatory)][string] $LogPath)

    if (-not (Test-Path -LiteralPath $LogPath)) { return $null }
    # MSVC writes "path(line): error C2664: ...", UBT writes "ERROR: ..." and "error :".
    return Select-String -LiteralPath $LogPath -Pattern '(: error [A-Z]?[0-9]*)|(^ERROR: )' -List |
           Select-Object -First 1
}

function Show-CompileErrorHelp {
    param([Parameter(Mandatory)][string] $LogPath)

    $hit = Get-FirstCompileError -LogPath $LogPath
    if ($null -eq $hit) {
        Write-Warn "no 'error' line in $LogPath; read the tail of it by hand"
        return
    }

    Write-Host ''
    Write-Host '    First error in the build log:' -ForegroundColor Yellow
    Write-Host "      $($hit.Line.Trim())"

    foreach ($file in $script:ChecklistSections.Keys) {
        if ($hit.Line -like "*$file*") {
            Write-Host ''
            Write-Host "    unreal\COMPILE_CHECKLIST.md section $($script:ChecklistSections[$file])" -ForegroundColor Yellow
            Write-Host '    That section names the function and the handful of lines involved. It is a local edit.'
            return
        }
    }
    Write-Host ''
    Write-Host '    This file is not in COMPILE_CHECKLIST.md section 7. Read the log around that line.' -ForegroundColor Yellow
}

function Invoke-Build {
    param(
        [Parameter(Mandatory)][string] $RepoRoot,
        [Parameter(Mandatory)][string] $EngineRoot
    )

    $buildBat = Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
    $uproject = Join-Path $RepoRoot 'unreal\NYCSim\NYCSim.uproject'
    $logDir   = Join-Path $RepoRoot 'unreal\NYCSim\Saved\Logs'
    $logPath  = Join-Path $logDir 'bring_up_build.log'

    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    Write-Detail 'generating project files'
    & $buildBat @('-projectfiles', "-project=$uproject", '-game', '-rocket', '-progress') 2>&1 |
        Tee-Object -FilePath $logPath | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Show-CompileErrorHelp -LogPath $logPath
        Stop-WithReason -Reason "project file generation failed (exit $LASTEXITCODE)" -NextSteps @(
            "Full log: $logPath"
        )
    }

    Write-Detail 'compiling NYCSimEditor Win64 Development -- 25 to 60 minutes cold, 5 to 10 against a binary engine'
    & $buildBat @('NYCSimEditor', 'Win64', 'Development', "-project=$uproject", '-waitmutex') 2>&1 |
        Tee-Object -FilePath $logPath -Append | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Show-CompileErrorHelp -LogPath $logPath
        Stop-WithReason -Reason "the compile failed (exit $LASTEXITCODE)" -NextSteps @(
            "Full log: $logPath",
            'unreal\COMPILE_CHECKLIST.md section 7 lists the ten API signatures most likely to break on a first build.'
        )
    }
    Write-Good 'NYCSimEditor built'
}

# ---------------------------------------------------------------------------------------------------
# Phase 5: import, restricted to what is on disk
# ---------------------------------------------------------------------------------------------------

function Show-ImportReport {
    <#
      The schema is the one import_world.py writes: counts and warnings at the top, a "stages" object
      keyed by stage name, and the staging stage's "missing" list -- which is where a partial unpack
      shows up as a source the manifest names and the disk does not have.
    #>
    param([Parameter(Mandatory)][string] $RepoRoot)

    $report = Join-Path $RepoRoot 'unreal\NYCSim\Saved\NYCSim\import_report.json'
    if (-not (Test-Path -LiteralPath $report)) {
        Write-Warn "no import_report.json at $report"
        return
    }

    try {
        $doc = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    } catch {
        Write-Warn "import_report.json is not readable JSON: $($_.Exception.Message)"
        return
    }
    $top = $doc.PSObject.Properties.Name

    if ($top -contains 'seconds' -and $null -ne $doc.seconds) {
        Write-Detail ("took {0:N1} s" -f [double] $doc.seconds)
    }
    if ($top -contains 'manifest_git_commit' -and -not [string]::IsNullOrWhiteSpace([string] $doc.manifest_git_commit)) {
        Write-Detail "manifest from commit $($doc.manifest_git_commit)"
    }

    # entries is the manifest's per-kind counts.
    if ($top -contains 'entries' -and $null -ne $doc.entries) {
        $counts = @($doc.entries.PSObject.Properties | ForEach-Object { "$($_.Name) $($_.Value)" })
        if ($counts.Count -gt 0) { Write-Detail ("manifest entries: " + ($counts -join ', ')) }
    }

    if ($top -contains 'manifest_warnings' -and $null -ne $doc.manifest_warnings) {
        $warnings = @($doc.manifest_warnings)
        foreach ($warning in ($warnings | Select-Object -First 10)) { Write-Warn "manifest: $warning" }
        if ($warnings.Count -gt 10) { Write-Warn "... $($warnings.Count - 10) more manifest warnings" }
    }

    if ($top -contains 'stages' -and $null -ne $doc.stages) {
        foreach ($stage in $doc.stages.PSObject.Properties) {
            $value = $stage.Value
            $fields = if ($null -eq $value) { @() } else { $value.PSObject.Properties.Name }

            if ($fields -contains 'exit') {
                $mark = if ([int] $value.exit -eq 0) { 'ok  ' } else { 'FAIL' }
                Write-Detail ("{0} {1}  exit {2}" -f $mark, $stage.Name.PadRight(8), [int] $value.exit)
                continue
            }

            $copied  = if ($fields -contains 'copied') { [int] $value.copied } else { 0 }
            $missing = if ($fields -contains 'missing' -and $null -ne $value.missing) { @($value.missing) } else { @() }
            $mark    = if ($missing.Count -eq 0) { 'ok  ' } else { 'WARN' }
            Write-Detail ("{0} {1}  {2} file(s) staged, {3} source(s) missing" -f
                          $mark, $stage.Name.PadRight(8), $copied, $missing.Count)

            # A missing source is silent otherwise, and a silent skip is how a missing asset becomes a
            # missing building.
            foreach ($item in ($missing | Select-Object -First 25)) {
                Write-Host "         missing: $item" -ForegroundColor Yellow
            }
            if ($missing.Count -gt 25) {
                Write-Host "         ... $($missing.Count - 25) more, all listed in $report" -ForegroundColor Yellow
            }
            if ($missing.Count -gt 0) {
                Write-Warn 'A missing source usually means the content package was unpacked in part.'
                Write-Warn 'This script imports only the tiles on disk, so a missing source here is not a tile filter.'
            }
        }
    }

    if ($top -contains 'exit' -and $null -ne $doc.exit -and [int] $doc.exit -ne 0) {
        Write-Warn "the report's own exit status is $([int] $doc.exit)"
    }
}

function Invoke-Import {
    param(
        [Parameter(Mandatory)][string] $RepoRoot,
        [Parameter(Mandatory)][string] $EngineRoot,
        [Parameter(Mandatory)][AllowEmptyCollection()][string[]] $Tiles,
        [switch] $Smoke
    )

    $cmd      = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
    $uproject = Join-Path $RepoRoot 'unreal\NYCSim\NYCSim.uproject'
    if (-not (Test-Path -LiteralPath $cmd)) {
        Stop-WithReason -Reason "no UnrealEditor-Cmd.exe at $cmd" -NextSteps @(
            'The engine root is wrong or the install is incomplete. Re-run with -DiscoverOnly to see what was found.'
        )
    }

    $subset = if ($Smoke) { @($Tiles | Select-Object -First 2) } else { $Tiles }
    $label  = if ($Smoke) { "smoke run over $($subset.Count) tile(s)" } else { "full import over $($subset.Count) tile(s)" }
    Write-Detail $label

    $arguments = @(
        $uproject,
        '-run=NYCImport',
        ('-tiles=' + ($subset -join ',')),
        '-unattended',
        '-nosplash',
        '-nopause',
        '-stdout'
    )

    # Run from the repository root: the commandlet resolves the manifest's relative source paths there.
    Push-Location -LiteralPath $RepoRoot
    try {
        & $cmd @arguments 2>&1 | Out-Host
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    Show-ImportReport -RepoRoot $RepoRoot

    if ($code -ne 0) {
        Stop-WithReason -Reason "$label failed (exit $code)" -NextSteps @(
            "The report above names the failing stage. Full log: $(Join-Path $RepoRoot 'unreal\NYCSim\Saved\Logs\NYCSim.log')",
            'To narrow it down: add -stages=validate to import nothing and only check the manifest against the files on disk.'
        )
    }
    Write-Good "$label finished"
}

# ---------------------------------------------------------------------------------------------------
# Phase 6: run it
# ---------------------------------------------------------------------------------------------------

function Start-Game {
    param(
        [Parameter(Mandatory)][string] $RepoRoot,
        [Parameter(Mandatory)][string] $EngineRoot,
        [switch] $Standalone,
        [int] $Width = 2560,
        [int] $Height = 1440
    )

    $editor   = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
    $uproject = Join-Path $RepoRoot 'unreal\NYCSim\NYCSim.uproject'
    if (-not (Test-Path -LiteralPath $editor)) {
        Stop-WithReason -Reason "no UnrealEditor.exe at $editor" -NextSteps @(
            'Re-run with -DiscoverOnly to see which engine roots were found.'
        )
    }

    if ($Standalone) {
        Write-Detail "standalone window at ${Width}x${Height}"
        Start-Process -FilePath $editor -ArgumentList @(
            $uproject, '/Game/NYCSim/Maps/NYC', '-game', '-windowed', "-resx=$Width", "-resy=$Height"
        )
    } else {
        Write-Detail 'opening the editor -- load /Game/NYCSim/Maps/NYC and press Play'
        Start-Process -FilePath $editor -ArgumentList @($uproject)
    }

    Write-Host ''
    Write-Good 'Driving: W throttle, S brake, A/D steer, Space handbrake, R reverse, F exit the car.'
    Write-Detail 'Q/E indicators, Z hazards, L headlights, Shift+L fog, K wipers, H horn, C camera, P photo mode.'
    Write-Detail 'M map, Tab search, Esc menu. F1 weather overlay, F2 streaming HUD, F3 sun. Console on ^ or ~.'
    Write-Detail 'The four Niagara particle systems are the one thing no script can author: rain and snow drive'
    Write-Detail 'the roads, puddles, wipers and tyre friction without them, only the particles are absent.'
}

# ---------------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------------

$repoRoot = Get-RepositoryRoot
Write-Host ''
Write-Host 'NYCSim bring-up' -ForegroundColor Cyan
Write-Detail "repository: $repoRoot"

Write-Phase 'Finding the engine'
if ($EnginePath) {
    if (-not (Test-EngineRoot -Root $EnginePath)) {
        Stop-WithReason -Reason "no Engine\Build\BatchFiles\Build.bat under $EnginePath" -NextSteps @(
            'Pass the directory that contains the Engine folder, not the Engine folder itself.',
            'Run with -DiscoverOnly to have the engines found for you.'
        )
    }
    $version = Get-EngineVersion -Root $EnginePath
    $engine = [pscustomobject]@{
        Root    = (Resolve-Path -LiteralPath $EnginePath).Path
        Version = $version
        Source  = '-EnginePath'
    }
    Write-Good "using $(if ($null -eq $version) { 'unknown version' } else { $version.Text }) at $($engine.Root)"
} else {
    $candidates = @(Find-Engines)
    if ($candidates.Count -eq 0) {
        Stop-WithReason -Reason 'no Unreal Engine found in the launcher manifest, the registry, or on any fixed drive' -NextSteps @(
            'Install Unreal Engine 5.4 from the Epic Games Launcher.',
            'If it is installed somewhere unusual, name it: -EnginePath "D:\SomeWhere\UE_5.4"'
        )
    }
    foreach ($candidate in $candidates) {
        $shown = if ($null -eq $candidate.Version) { 'unknown version' } else { $candidate.Version.Text }
        Write-Detail ("{0,-12} {1,-32} {2}" -f $shown, $candidate.Source, $candidate.Root)
    }
    $engine = Select-Engine -Candidates $candidates -AllowAnyVersion:$AllowEngineVersion
    Write-Good "using $(if ($null -eq $engine.Version) { 'unknown version' } else { $engine.Version.Text }) at $($engine.Root)"
}

if ($DiscoverOnly) {
    Write-Host ''
    Write-Detail 'discovery only; nothing was built. Drop -DiscoverOnly to go on.'
    Write-Host ''
    exit 0
}

Write-Phase 'Checking the machine'
Test-Toolchain
Test-FreeDisk -RepoRoot $repoRoot
$tiles = @(Test-Content -RepoRoot $repoRoot)

if (-not $SkipBuild) {
    Write-Phase 'Building'
    Invoke-Build -RepoRoot $repoRoot -EngineRoot $engine.Root
} else {
    Write-Phase 'Building (skipped)'
    Write-Detail '-SkipBuild was given'
}

if (-not $SkipImport) {
    if (-not $SkipSmoke) {
        Write-Phase 'Smoke import'
        Invoke-Import -RepoRoot $repoRoot -EngineRoot $engine.Root -Tiles $tiles -Smoke
    }
    Write-Phase 'Importing the world'
    Invoke-Import -RepoRoot $repoRoot -EngineRoot $engine.Root -Tiles $tiles
} else {
    Write-Phase 'Importing (skipped)'
    Write-Detail '-SkipImport was given'
}

Write-Phase 'Starting'
Start-Game -RepoRoot $repoRoot -EngineRoot $engine.Root -Standalone:$Play -Width $ResX -Height $ResY
Write-Host ''
exit 0
