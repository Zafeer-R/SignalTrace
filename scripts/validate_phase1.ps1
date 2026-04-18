param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
if ($null -ne (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue)) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Pass($Message) {
    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Fail($Message) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    $script:HadFailure = $true
}

function Check-PathExists($Path, $Description) {
    $fullPath = Join-Path $RepoRoot $Path
    if (Test-Path -LiteralPath $fullPath) {
        Pass $Description
    }
    else {
        Fail "$Description ($Path missing)"
    }
}

function Invoke-ExternalCommand($Command, $Arguments) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Command
    $quotedArgs = foreach ($arg in $Arguments) {
        if ($arg -match '[\s"]') {
            '"' + ($arg -replace '"', '\"') + '"'
        }
        else {
            $arg
        }
    }
    $psi.Arguments = ($quotedArgs -join ' ')
    $psi.WorkingDirectory = $RepoRoot
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut   = $stdout
        StdErr   = $stderr
    }
}

function Check-CommandSucceeds($Description, $Command, $Arguments) {
    $result = Invoke-ExternalCommand -Command $Command -Arguments $Arguments
    if ($result.ExitCode -eq 0) {
        Pass $Description
        return $result
    }

    $details = ($result.StdOut + [Environment]::NewLine + $result.StdErr).Trim()
    Fail "$Description`n$details"
    return $result
}

function Check-ContainerRunning($ContainerName) {
    $result = Invoke-ExternalCommand -Command "docker" -Arguments @("inspect", "-f", "{{.State.Running}}", $ContainerName)
    if ($result.ExitCode -eq 0 -and $result.StdOut.Trim() -eq "true") {
        Pass "Container '$ContainerName' is running"
    }
    else {
        Fail "Container '$ContainerName' is not running"
    }
}

$script:HadFailure = $false

Write-Host "Validating Phase 1 in $RepoRoot"

$requiredPaths = @(
    @{ Path = "producer"; Description = "Producer directory exists" },
    @{ Path = "spark"; Description = "Spark directory exists" },
    @{ Path = "logstash"; Description = "Logstash directory exists" },
    @{ Path = "kibana"; Description = "Kibana directory exists" },
    @{ Path = "schemas"; Description = "Schemas directory exists" },
    @{ Path = "docker-compose.yml"; Description = "docker-compose.yml exists" },
    @{ Path = ".env.example"; Description = ".env.example exists" },
    @{ Path = "requirements.txt"; Description = "requirements.txt exists" },
    @{ Path = "logstash\pipeline.conf"; Description = "Logstash pipeline config exists" },
    @{ Path = ".venv\Scripts\python.exe"; Description = "Virtual environment exists" }
)

foreach ($entry in $requiredPaths) {
    Check-PathExists -Path $entry.Path -Description $entry.Description
}

Check-CommandSucceeds -Description "docker compose config parses successfully" -Command "docker" -Arguments @("compose", "config") | Out-Null
Check-CommandSucceeds -Description "docker compose ps executes successfully" -Command "docker" -Arguments @("compose", "ps") | Out-Null

$containers = @("zookeeper", "kafka", "elasticsearch", "logstash", "kibana")
foreach ($container in $containers) {
    Check-ContainerRunning -ContainerName $container
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5601" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
        Pass "Kibana is reachable at http://localhost:5601"
    }
    else {
        Fail "Kibana returned unexpected status code $($response.StatusCode)"
    }
}
catch {
    Fail "Kibana is not reachable at http://localhost:5601`n$($_.Exception.Message)"
}

$pythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$requiredImports = @("kafka", "requests", "pyspark", "spacy", "dotenv")                                                                                    
$pythonList = "['" + ($requiredImports -join "','") + "']"                                                                                                 
                                                                                                                                                           
$importResult = Invoke-ExternalCommand -Command $pythonExe -Arguments @(                                                                                   
    "-c",                                                                                                                                                  
    "import importlib.util, sys; missing=[name for name in $pythonList if importlib.util.find_spec(name) is None]; print(','.join(missing)); sys.exit(1 if 
missing else 0)"
) 
if ($importResult.ExitCode -eq 0) {
    Pass "Required Python packages are importable in .venv"
}
else {
    $missing = ($importResult.StdOut + [Environment]::NewLine + $importResult.StdErr).Trim()
    if ([string]::IsNullOrWhiteSpace($missing)) {
        $missing = "unknown import failure"
    }
    Fail "Required Python packages are missing from .venv: $missing"
}

$spacyResult = Invoke-ExternalCommand -Command $pythonExe -Arguments @("-m", "spacy", "validate")
if ($spacyResult.ExitCode -eq 0 -and (($spacyResult.StdOut + $spacyResult.StdErr) -match "en_core_web_sm")) {
    Pass "spaCy model 'en_core_web_sm' is installed"
}
else {
    Fail "spaCy model 'en_core_web_sm' is not confirmed by 'python -m spacy validate'"
}

if ($script:HadFailure) {
    Write-Host "Phase 1 validation failed." -ForegroundColor Red
    exit 1
}

Write-Host "Phase 1 validation passed." -ForegroundColor Green
