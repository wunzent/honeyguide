param(
    [Parameter(Mandatory)][string]$Brief,
    [Parameter(Mandatory)][string]$Role,
    [Parameter(Mandatory)][ValidateSet('routine','standard','complex')][string]$Tier,
    [Parameter(Mandatory)][string]$Model,
    [Parameter(Mandatory)][string]$Effort,
    [Parameter(Mandatory)][string]$Reason,
    [string]$Escalation,
    [string]$Repo = (Split-Path $PSScriptRoot -Parent),
    [string]$OutDir,
    [string]$SessionsDir = (Join-Path $HOME '.codex\sessions'),
    [string]$Log
)
$ErrorActionPreference = 'Stop'
$hubRoot = Split-Path $PSScriptRoot -Parent
$python = Join-Path $hubRoot '.venv\Scripts\python.exe'
$delegation = Join-Path $hubRoot 'delegation.py'
$checkArgs = @($delegation, 'check', '--role', $Role, '--tier', $Tier,
    '--vendor', 'codex', '--model', $Model, '--effort', $Effort, '--reason', $Reason)
if ($Escalation) { $checkArgs += @('--escalation', $Escalation) }
$validation = & $python @checkArgs
if ($LASTEXITCODE -ne 0) {
    $validation | Write-Output
    exit 2
}
$route = $validation | ConvertFrom-Json
$briefPath = (Resolve-Path -LiteralPath $Brief).Path
if (-not $OutDir) { $OutDir = Split-Path $briefPath -Parent }
[void][IO.Directory]::CreateDirectory($OutDir)
$name = [IO.Path]::GetFileNameWithoutExtension($briefPath)
$events = Join-Path $OutDir "$name.jsonl"
$last = Join-Path $OutDir "$name.last.md"
$prompt = "Context budget: read only the files this step names, read each once, do not re-read unchanged files, and do not run the full test suite.`n" + [IO.File]::ReadAllText($briefPath)
$hash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($prompt))).ToLowerInvariant()
function Write-DelegationRecord($entry) {
    $recordArgs = @($delegation, 'record', '--json', ($entry | ConvertTo-Json -Depth 10 -Compress))
    if ($Log) { $recordArgs += @('--log', $Log) }
    & $python @recordArgs
    if ($LASTEXITCODE -ne 0) { throw 'Could not record delegation' }
}
Write-DelegationRecord @{
    type = 'delegation.start'; route = $route; reason = $Reason; escalation = $Escalation
    prompt_sha256 = $hash; prompt_length = $prompt.Length
}
$prompt | & codex exec -C $Repo -s workspace-write -m $Model -c "model_reasoning_effort=$Effort" --json -o $last - | Set-Content -LiteralPath $events -Encoding utf8
$codexExit = $LASTEXITCODE
$verification = & $python $delegation verify-codex --events $events --sessions-dir $SessionsDir
if ($LASTEXITCODE -ne 0) { throw 'Could not verify Codex session' }
$actual = $verification | ConvertFrom-Json
$matches = ($actual.actual_model -ceq $Model) -and ($actual.actual_effort -ceq $Effort)
Write-DelegationRecord @{
    type = 'delegation.end'; requested_model = $Model; requested_effort = $Effort
    actual_model = $actual.actual_model; actual_effort = $actual.actual_effort
    route_matches = $matches; total_tokens = $actual.total_tokens; exit_code = $codexExit
    evidence = $actual.evidence; thread = $actual.thread
}
if (-not $matches) { exit 3 }
exit $codexExit
