# 高风险三查 · 事务 · CampusClaw

- **用什么手段查：** 以A班学生A1身份提交作业并请求批改，暂停、恢复专用环境的worker；通过MySQL触发器模拟Outbox写入失败，核对数据库前后记录。

- **查了什么：** worker恢复后待处理任务能否完成；Outbox写入失败时，提交、任务和Outbox是否一并回滚，是否遗留孤儿任务。

- **判据：** worker恢复后任务应完成；按当前规约，Outbox写入失败后三表均无新增，且不存在缺少对应提交或Outbox的任务。

- **结果：**红。worker恢复后任务成功完成；故障场景中，创建提交返回201，批改请求返回503，提交、任务、Outbox记录数由3/2/2变为4/2/2。提交记录保留，任务及Outbox未新增，孤儿任务为0条。

- **复测命令：** 

```powershell
# PowerShell 7.3及以上。
$ErrorActionPreference = 'Stop'
$Outcome = '无法判定'
$TestError = $null
$CleanupFailures = [System.Collections.Generic.List[string]]::new()
$StartupCleanupStatus = '不需要（尚未启动）'
$TriggerCleanupStatus = '不需要（尚未注入）'
$WorkerRecoveryStatus = '不需要（尚未暂停）'
$TriggerNeedsCleanup = $false
$WorkerNeedsRecovery = $false
try {
# 仅适用于PowerShell 7.3及以上
if ($PSVersionTable.PSVersion -lt [version]'7.3') {
    throw '请使用PowerShell 7.3及以上版本（pwsh）运行。'
}
$ErrorActionPreference = 'Stop'
$PSNativeCommandArgumentPassing = 'Standard'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Set-Location 'E:\proj\teamwork-main-latest'
$Student = 'student_a1'
$StudentPassword = '<填写本次隔离环境的新密码，至少12位英文字母、数字或连字符>'
if ($StudentPassword -notmatch '^[A-Za-z0-9-]{12,}$') {
    throw '请替换专用种子密码占位符；此命令限定该字符集以避免.env插值。'
}
$Project = 'campusclaw-transaction-' + [guid]::NewGuid().ToString('N')
$RunDir = Join-Path $env:TEMP $Project
$null = New-Item -ItemType Directory -Path $RunDir
$EnvFile = Join-Path $RunDir '.env'
$OverrideFile = Join-Path $RunDir 'ports.yml'
$BrokerPassword = [guid]::NewGuid().ToString('N')
$values = @{
    WEB_PORT = '0'; GRADE_LOCAL_DELAY_MS = '2000'
    CHAT_URL = 'local'; EMBEDDING_URL = 'local'
    RABBITMQ_DEFAULT_USER = 'campusclaw'
    MYSQL_ROOT_PASSWORD = [guid]::NewGuid().ToString('N')
    DB_PASSWORD = [guid]::NewGuid().ToString('N')
    SESSION_SECRET = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    SEED_TEACHER_PASSWORD = [guid]::NewGuid().ToString('N')
    SEED_STUDENT_A_PASSWORD = $StudentPassword
    SEED_STUDENT_B_PASSWORD = [guid]::NewGuid().ToString('N')
    RABBITMQ_DEFAULT_PASS = $BrokerPassword
    RABBITMQ_URL = "amqp://campusclaw:${BrokerPassword}@rabbitmq:5672/"
}
$seenKeys = [System.Collections.Generic.HashSet[string]]::new()
$envLines = @(Get-Content -LiteralPath '.env.example' -Encoding UTF8 | ForEach-Object {
    $entry = [regex]::Match($_, '^([A-Z0-9_]+)=')
    if ($entry.Success) {
        $key = $entry.Groups[1].Value
        $null = $seenKeys.Add($key)
        if ([Environment]::GetEnvironmentVariable($key, 'Process')) {
            throw "进程环境已有同名变量$key；请在未设置这些变量的新pwsh窗口运行，避免覆盖专用.env。"
        }
        if ($values.ContainsKey($key)) { "$key=$($values[$key])" } else { $_ }
    } else { $_ }
})
foreach ($key in $values.Keys) {
    if (-not $seenKeys.Contains($key)) {
        if ([Environment]::GetEnvironmentVariable($key, 'Process')) {
            throw "进程环境已有同名变量$key，停止以避免覆盖隔离配置。"
        }
        $envLines += "$key=$($values[$key])"
    }
}
$envLines | Set-Content -LiteralPath $EnvFile -Encoding utf8NoBOM
@'
services:
  web:
    ports: !override
      - target: 80
        published: "0"
        host_ip: 127.0.0.1
'@ | Set-Content -LiteralPath $OverrideFile -Encoding utf8NoBOM
$Compose = @('compose', '-p', $Project, '--env-file', $EnvFile,
    '-f', (Join-Path (Get-Location).Path 'docker-compose.yml'), '-f', $OverrideFile)
function Dc {
    & docker @Compose @args
    if ($LASTEXITCODE -ne 0) { throw '专用环境的Docker Compose命令失败。' }
}
function Db([string]$Sql, [switch]$Root) {
    $command = if ($Root) {
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$MYSQL_DATABASE" -N -B'
    } else {
        'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" -N -B'
    }
    $rows = @($Sql | & docker @Compose exec -T db sh -c $command)
    if ($LASTEXITCODE -ne 0) { throw '专用数据库命令失败。' }
    # 零行查询合法；统一返回字符串，调用方用IsNullOrWhiteSpace判断空结果。
    return [string]::Join("`n", [string[]]$rows).Trim()
}
# 当前原Compose仅web发布宿主机端口，无container_name；四个数据卷均为项目内命名卷。
# 先校验最终合并配置，未来配置变化时拒绝固定端口、共享卷或固定容器名。
$config = (Dc config --format json | Out-String) | ConvertFrom-Json -AsHashtable
if ($config.name -ne $Project) { throw 'Compose项目名不是本次随机项目。' }
foreach ($serviceName in $config.services.Keys) {
    $service = $config.services[$serviceName]
    if ($service.container_name -or $service.network_mode -or $service.volumes_from -or $service.external_links) {
        throw "服务$serviceName使用固定容器名或跨容器共享配置，拒绝启动。"
    }
    foreach ($port in @($service.ports)) {
        if ($null -eq $port) { continue }
        if ($serviceName -ne 'web' -or $port.host_ip -ne '127.0.0.1' -or
            [string]$port.published -ne '0' -or [int]$port.target -ne 80 -or $port.protocol -ne 'tcp') {
            throw "服务$serviceName存在非本机随机web端口，拒绝启动。"
        }
    }
    foreach ($mount in @($service.volumes)) {
        if ($null -eq $mount) { continue }
        if ($mount.type -ne 'volume' -or -not $config.volumes.ContainsKey($mount.source)) {
            throw "服务$serviceName存在宿主机绑定目录或未声明的数据卷，拒绝共享业务数据。"
        }
    }
}
foreach ($volumeKey in $config.volumes.Keys) {
    $volume = $config.volumes[$volumeKey]
    if ($volume.external -or $volume.name -ne "${Project}_$volumeKey" -or
        ($volume.driver -and $volume.driver -ne 'local') -or $volume.driver_opts) {
        throw "数据卷$volumeKey不是本项目独立本地卷，拒绝启动。"
    }
}
foreach ($networkKey in $config.networks.Keys) {
    $network = $config.networks[$networkKey]
    if ($network.external -or $network.name -ne "${Project}_$networkKey" -or
        ($network.driver -and $network.driver -ne 'bridge')) {
        throw '存在外部网络或跨项目固定网络名，拒绝启动。'
    }
}
$existingContainers = @(& docker ps -aq --filter "label=com.docker.compose.project=$Project")
if ($LASTEXITCODE -ne 0 -or $existingContainers.Count -gt 0) { throw '随机项目已存在或无法确认，拒绝复用。' }
$existingVolumes = @(& docker volume ls --format '{{.Name}}')
if ($LASTEXITCODE -ne 0) { throw '无法核对已有数据卷。' }
foreach ($volume in $config.volumes.Values) {
    if ($volume.name -in $existingVolumes) { throw '目标卷已存在，拒绝复用旧数据。' }
}
$existingNetworks = @(& docker network ls --format '{{.Name}}')
if ($LASTEXITCODE -ne 0) { throw '无法核对已有网络。' }
foreach ($network in $config.networks.Values) {
    if ($network.name -in $existingNetworks) { throw '目标网络已存在，拒绝复用。' }
}
$CleanupCommand = 'docker compose -p "{0}" --env-file "{1}" -f "{2}" -f "{3}" down --remove-orphans' -f
    $Project, $EnvFile, (Join-Path (Get-Location).Path 'docker-compose.yml'), $OverrideFile
try {
    Dc up -d --build --wait --wait-timeout 180
    $binding = (Dc port web 80 | Select-Object -First 1).Trim()
    if ($binding -notmatch '^127\.0\.0\.1:\d+$') { throw '未取得本机隔离端口。' }
    $BaseUrl = "http://$binding"
    $StartupCleanupStatus = '不需要（启动成功）'
    Write-Host "专用项目：$Project；服务：$BaseUrl；配置与输出目录：$RunDir"
    Write-Host "本项目清理命令（保留数据卷）：$CleanupCommand"
} catch {
    $startupFailure = $_
    Write-Warning "启动失败；仅本项目的可复制清理命令：$CleanupCommand"
    try {
        Dc down --remove-orphans
        $StartupCleanupStatus = '成功（仅清理本项目容器/网络，保留卷）'
    } catch {
        $StartupCleanupStatus = '失败：' + $_.Exception.Message
        $CleanupFailures.Add('启动清理：' + $_.Exception.Message)
        Write-Warning '自动清理失败，请执行上方本项目命令；不要使用全局清理命令。'
    }
    throw $startupFailure
}


function Api([string]$Method, [string]$Path, $Body = $null) {
    $options = @{
        Uri = "$BaseUrl$Path"; Method = $Method
        Headers = $Headers; SkipHttpErrorCheck = $true; TimeoutSec = 60
    }
    if ($null -ne $Body) {
        $options.ContentType = 'application/json'
        $options.Body = [System.Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Compress))
    }
    $response = Invoke-WebRequest @options
    $rawBody = if ($response.Content -is [byte[]]) {
        [System.Text.Encoding]::UTF8.GetString($response.Content)
    } else { [string]$response.Content }
    $data = $null
    $jsonError = $null
    try { $data = ConvertFrom-Json -InputObject $rawBody -ErrorAction Stop }
    catch { $jsonError = $_.Exception.Message }
    $reply = [pscustomobject]@{
        Status = [int]$response.StatusCode; RawBody = $rawBody
        Data = $data; JsonParseError = $jsonError
    }
    Write-Host "$Method $Path -> HTTP $($reply.Status)"
    # 保存原始状态及正文，包括非JSON的503；不保存含token的登录响应。
    if ($Path -ne '/api/login') {
        $ApiRecords.Add([pscustomobject]@{
            Method = $Method; Path = $Path; Status = $reply.Status
            RawBody = $rawBody; JsonParseError = $jsonError
        })
        $ApiRecords | ConvertTo-Json -Depth 8 |
            Set-Content -LiteralPath (Join-Path $RunDir 'http-responses.json')
    }
    return $reply
}
function Require-Status($Reply, [int]$Expected) {
    if ($Reply.Status -ne $Expected) { throw "期望HTTP $Expected，实际HTTP $($Reply.Status)；原始正文已保留。" }
}
function Read-ThreeCounts([AllowNull()][string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { throw '三表计数为空，无法判定。' }
    $parts = $Text.Split("`t")
    if ($parts.Count -ne 3) { throw '三表计数必须恰好包含3列，无法判定。' }
    $numbers = [long[]]::new(3)
    for ($i = 0; $i -lt 3; $i++) {
        $value = [long]0
        if ($parts[$i] -notmatch '^[0-9]+$' -or
            -not [long]::TryParse($parts[$i], [ref]$value) -or $value -lt 0) {
            throw '三表计数必须是3个有效非负整数，无法判定。'
        }
        $numbers[$i] = $value
    }
    return ,$numbers
}
$ApiRecords = [System.Collections.Generic.List[object]]::new()
$Headers = @{}
$login = Api POST '/api/login' @{ username = $Student; password = $StudentPassword }
Require-Status $login 200
$Token = [string]$login.Data.token
if (-not $Token) { throw '登录响应缺少token。' }
$Headers = @{ Authorization = "Bearer $Token" }
$assignments = Api GET '/api/assignments'
Require-Status $assignments 200
$AssignmentId = [long](@($assignments.Data.assignments)[0].id)
if ($AssignmentId -le 0) { throw '缺少本班已发布作业。' }

# 场景一：先停止worker，再创建提交并入队；异常时由最外层finally恢复worker。
$WorkerNeedsRecovery = $true
$WorkerRecoveryStatus = '待恢复'
Dc stop worker
$submission = Api POST "/api/assignments/$AssignmentId/submissions" @{
    body = "SEC transaction $Project"
}
Require-Status $submission 201
$SubmissionId = $submission.Data.submission_id
$SubmissionVersion = $submission.Data.version
if (($SubmissionId -isnot [int] -and $SubmissionId -isnot [long]) -or $SubmissionId -le 0 -or
    ($SubmissionVersion -isnot [int] -and $SubmissionVersion -isnot [long]) -or $SubmissionVersion -le 0) {
    throw '提交ID或版本缺失、类型错误或不是正整数。'
}
$queued = Api POST "/api/submissions/$SubmissionId/grade" @{}
Require-Status $queued 202
$TaskId = [string]$queued.Data.task_id
if ($queued.Data.status -ne 'pending' -or $queued.Data.PSObject.Properties['score'] -or
    $TaskId -notmatch '^[0-9A-HJKMNP-TV-Z]{26}$') { throw '入队响应不符合pending契约。' }
$pending = Db "SELECT status,attempts FROM grade_tasks WHERE task_id='$TaskId';"
Write-Host "停worker时状态/尝试次数：$pending（预期pending/0）"
if ($pending -ne "pending`t0") { throw 'worker停止期间任务状态不符合预期。' }
Dc start worker
$WorkerNeedsRecovery = $false
$WorkerRecoveryStatus = '成功（场景一已恢复）'
$deadline = [DateTime]::UtcNow.AddSeconds(60)
do {
    $task = Api GET "/api/tasks/$TaskId"
    Require-Status $task 200
    Write-Host "恢复后状态：$($task.Data.status)"
    if ($task.Data.status -in @('succeeded', 'failed', 'dead')) { break }
    Start-Sleep -Milliseconds 500
} while ([DateTime]::UtcNow -lt $deadline)
if ($task.Data.status -ne 'succeeded') { throw '恢复worker后未在期限内完成。' }
$completed = Db "SELECT status,attempts FROM grade_tasks WHERE task_id='$TaskId';"
$resultCount = Db "SELECT COUNT(*) FROM grade_results WHERE submission_id=$SubmissionId AND version=$SubmissionVersion;"
Write-Host "完成状态/尝试次数：$completed；该提交版本的结果条数：$resultCount"
if ($completed -ne "succeeded`t1" -or $resultCount -ne '1') { throw '恢复完成核验不符合预期。' }

# 场景二：基线在创建故障提交之前；本专用环境不得有其他并发业务写入。
$countSql = 'SELECT (SELECT COUNT(*) FROM submissions),(SELECT COUNT(*) FROM grade_tasks),(SELECT COUNT(*) FROM outbox_messages);'
$before = Db $countSql
$beforeCounts = Read-ThreeCounts $before
$TriggerNeedsCleanup = $true
$TriggerCleanupStatus = '待撤销'
$null = Db "CREATE TRIGGER sec_fail_outbox BEFORE INSERT ON outbox_messages FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='security-test-injected';" -Root
# 请求一：提交接口独立提交；请求二：批改事务因Outbox失败应返回503。
$created = Api POST "/api/assignments/$AssignmentId/submissions" @{
    body = "SEC rollback $Project"
}
Require-Status $created 201
$FaultSubmissionId = $created.Data.submission_id
$FaultVersion = $created.Data.version
if (($FaultSubmissionId -isnot [int] -and $FaultSubmissionId -isnot [long]) -or $FaultSubmissionId -le 0 -or
    ($FaultVersion -isnot [int] -and $FaultVersion -isnot [long]) -or $FaultVersion -le 0) {
    throw '故障场景提交ID或版本不是有效正整数。'
}
$FaultKey = "grade:${FaultSubmissionId}:$FaultVersion"
$failed = Api POST "/api/submissions/$FaultSubmissionId/grade" @{}
Require-Status $failed 503
Write-Host "故障HTTP状态：$($failed.Status)；原始正文：$($failed.RawBody)"
$after = Db $countSql
$afterCounts = Read-ThreeCounts $after
$retained = Db "SELECT id,version,status FROM submissions WHERE id=$FaultSubmissionId;"
$targetCounts = Db "SELECT (SELECT COUNT(*) FROM grade_tasks WHERE submission_id=$FaultSubmissionId),(SELECT COUNT(*) FROM outbox_messages WHERE idempotency_key='$FaultKey');"
Write-Host "三表顺序为submissions / grade_tasks / outbox_messages：前=$before；后=$after"
Write-Host "保留提交ID/版本/状态：$retained；目标任务/Outbox数量：$targetCounts"
[pscustomobject]@{
    Before = $before; After = $after; HTTP = $failed.Status; RawBody = $failed.RawBody
    RetainedSubmission = $retained; TargetTaskAndOutbox = $targetCounts
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $RunDir 'transaction-observed.json')
# 正常路径先撤销触发器；如果这里失败，finally仍会重试并单独报告。
$null = Db 'DROP TRIGGER IF EXISTS sec_fail_outbox;' -Root
$TriggerNeedsCleanup = $false
$TriggerCleanupStatus = '成功（故障后已撤销）'
$orphans = Db 'SELECT (SELECT COUNT(*) FROM grade_tasks t LEFT JOIN submissions s ON t.submission_id=s.id WHERE s.id IS NULL),(SELECT COUNT(*) FROM grade_tasks t LEFT JOIN outbox_messages o ON t.idempotency_key=o.idempotency_key WHERE o.id IS NULL);'
Write-Host "没有对应提交的任务数/没有对应Outbox的任务数：$orphans（预期0/0）"
if ($targetCounts -ne "0`t0" -or $orphans -ne "0`t0") {
    $Outcome = '检查失败：存在故障后遗留任务、Outbox或孤儿任务'
    throw $Outcome
}
$noRetainedSubmission = [string]::IsNullOrWhiteSpace($retained)
if ($beforeCounts[0] -eq $afterCounts[0] -and $beforeCounts[1] -eq $afterCounts[1] -and
    $beforeCounts[2] -eq $afterCounts[2] -and $noRetainedSubmission) {
    $Outcome = '检查通过：满足三表无新增的原子性判据'
} elseif ($afterCounts[0] -eq ($beforeCounts[0] + 1) -and
    $afterCounts[1] -eq $beforeCounts[1] -and $afterCounts[2] -eq $beforeCounts[2] -and
    -not $noRetainedSubmission -and $retained -eq "$FaultSubmissionId`t$FaultVersion`tsubmitted") {
    $Outcome = '检查失败：submission保留，已复现历史红项'
} else {
    throw '观察结果与已定义判据或历史模式不同，无法判定；请保留输出。'
}

} catch {
    $TestError = $_  # 保留首个测试/执行错误，后续清理错误不覆盖它。
} finally {
    if ($TriggerNeedsCleanup) {
        try {
            $null = Db 'DROP TRIGGER IF EXISTS sec_fail_outbox;' -Root
            $TriggerCleanupStatus = '成功（finally已撤销）'
        } catch {
            $TriggerCleanupStatus = '失败：' + $_.Exception.Message
            $CleanupFailures.Add('触发器撤销：' + $_.Exception.Message)
        }
    }
    if ($WorkerNeedsRecovery) {
        try {
            Dc start worker
            $WorkerRecoveryStatus = '成功（finally已恢复）'
        } catch {
            $WorkerRecoveryStatus = '失败：' + $_.Exception.Message
            $CleanupFailures.Add('worker恢复：' + $_.Exception.Message)
        }
    }
    Write-Host "测试结果：$Outcome"
    if ($null -ne $TestError) { Write-Host "原始测试/执行错误：$($TestError.Exception.Message)" }
    Write-Host "触发器撤销：$TriggerCleanupStatus"
    Write-Host "worker恢复：$WorkerRecoveryStatus"
    Write-Host "启动失败清理：$StartupCleanupStatus"
    foreach ($cleanupFailure in $CleanupFailures) { Write-Warning $cleanupFailure }
    Remove-Variable StudentPassword, Token, Headers, login, BrokerPassword, values -ErrorAction SilentlyContinue
}
# 先完成恢复并报告，再以异常表示失败；不要捕获此异常后当作成功。
if ($null -ne $TestError) { throw $TestError }
if ($CleanupFailures.Count -gt 0) { throw '测试结果已单列，但清理未全部成功；请按单列错误手动恢复。' }
if ($Outcome -like '检查失败*') { throw [System.InvalidOperationException]::new($Outcome) }
if ($Outcome -notlike '检查通过*') { throw '执行异常：无法判定。' }
Write-Host '本次检查通过；不回写历史红项，也未覆盖撤销故障后重试场景。'
# 可手动执行上方$CleanupCommand，仅清理本随机项目的容器/网络，不删除卷或保留提交。
```


