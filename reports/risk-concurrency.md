# 高风险三查 · 并发 · CampusClaw

- **用什么手段查：**以A班学生A1身份，对同一作业提交及版本发送8个并发批改请求；任务成功后重新投递原消息，通过数据库及worker日志核验。

- **查了什么：** 并发请求是否重复生成任务、Outbox和批改结果；重复消息是否改变已有评分、评语及执行尝试次数。

- **判据：**8个请求均返回202并复用同一task_id，仅生成1条任务、1条Outbox和1条结果；成功后重复投递不改变结果及执行尝试次数。

- **结果：** 绿。8个请求均返回202且task_id相同；任务、Outbox及结果各1条；重复投递后评分、评语不变，attempts仍为1，记录到重复消息跳过日志。

- **复测命令：**

```powershell
# 仅适用于PowerShell 7.3及以上；
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
$Project = 'campusclaw-concurrency-' + [guid]::NewGuid().ToString('N')
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
function Db([string]$Sql) {
    $rows = $Sql | & docker @Compose exec -T db sh -c `
        'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" -N -B'
    if ($LASTEXITCODE -ne 0) { throw '专用数据库命令失败。' }
    return ($rows -join "`n").Trim()
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
$CleanupCommand = 'docker compose -p "{0}" --env-file "{1}" -f "{2}" -f "{3}" down --remove-orphans' -f
    $Project, $EnvFile, (Join-Path (Get-Location).Path 'docker-compose.yml'), $OverrideFile
try {
    Dc up -d --build --wait --wait-timeout 180
    $binding = (Dc port web 80 | Select-Object -First 1).Trim()
    if ($binding -notmatch '^127\.0\.0\.1:\d+$') { throw '未取得本机隔离端口。' }
    $BaseUrl = "http://$binding"
    Write-Host "专用项目：$Project；服务：$BaseUrl；配置与输出目录：$RunDir"
    Write-Host "本项目清理命令（保留数据卷）：$CleanupCommand"
} catch {
    $startupFailure = $_
    Write-Warning "启动失败；仅本项目的可复制清理命令：$CleanupCommand"
    try { Dc down --remove-orphans }
    catch { Write-Warning '自动清理失败，请执行上方本项目命令；不要使用全局清理命令。' }
    throw $startupFailure
}

$Http = [System.Net.Http.HttpClient]::new()
$Http.Timeout = [TimeSpan]::FromSeconds(60)
function New-Request([string]$Method, [string]$Path, $Body = $null) {
  $request = [System.Net.Http.HttpRequestMessage]::new(
        [System.Net.Http.HttpMethod]::new($Method), "$BaseUrl$Path")
    if ($null -ne $Body) {
        $request.Content = [System.Net.Http.StringContent]::new(
            ($Body | ConvertTo-Json -Compress), [System.Text.Encoding]::UTF8, 'application/json')
    }
    return $request
}
function Read-Reply($Response) {
    try {
        $text = $Response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        return [pscustomobject]@{
            Status = [int]$Response.StatusCode
            Data = ConvertFrom-Json -InputObject $text
        }
    } finally { $Response.Dispose() }
}
function Api([string]$Method, [string]$Path, $Body = $null) {
    $request = New-Request $Method $Path $Body
    try { return Read-Reply ($Http.SendAsync($request).GetAwaiter().GetResult()) }
    finally { $request.Dispose() }
}
function Require-Status($Reply, [int]$Expected) {
    if ($Reply.Status -ne $Expected) {
        throw "期望HTTP $Expected，实际HTTP $($Reply.Status)"
    }
}
try {
    $login = Api POST '/api/login' @{ username = $Student; password = $StudentPassword }
    Require-Status $login 200
    $Token = [string]$login.Data.token
    if (-not $Token) { throw '登录响应缺少token。' }
    $Http.DefaultRequestHeaders.Authorization =
        [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $Token)
    $assignments = Api GET '/api/assignments'
    Require-Status $assignments 200
    $AssignmentId = [long](@($assignments.Data.assignments)[0].id)
    if ($AssignmentId -le 0) { throw '缺少本班已发布作业。' }

    # worker停止期间，新建唯一正文的提交，并同时发出8个请求。
    Dc stop worker
    try {
      $submission = Api POST "/api/assignments/$AssignmentId/submissions" @{
            body = "SEC concurrent $Project"
        }
        Require-Status $submission 201
        $SubmissionId = [long]$submission.Data.submission_id
        $Version = [int]$submission.Data.version
        if ($SubmissionId -le 0 -or $Version -le 0) { throw '提交标识或版本无效。' }
        $Key = "grade:${SubmissionId}:$Version"
        $pending = @(1..8 | ForEach-Object {
            $request = New-Request POST "/api/submissions/$SubmissionId/grade" @{}
            [pscustomobject]@{ Request = $request; Future = $Http.SendAsync($request) }
        })
        $replies = @($pending | ForEach-Object {
            try { Read-Reply ($_.Future.GetAwaiter().GetResult()) }
            finally { $_.Request.Dispose() }
        })
        $replies | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $RunDir 'requests.json')
        $replies | ForEach-Object {
            [pscustomobject]@{ HTTP = $_.Status; TaskId = $_.Data.task_id }
        } | Format-Table
        foreach ($reply in $replies) { Require-Status $reply 202 }
        $taskIds = @($replies | ForEach-Object { [string]$_.Data.task_id } | Select-Object -Unique)
        if ($replies.Count -ne 8 -or $taskIds.Count -ne 1 -or
            $taskIds[0] -notmatch '^[0-9A-HJKMNP-TV-Z]{26}$') {
            throw '8个响应未复用同一有效task_id。'
        }
        $TaskId = $taskIds[0]
        $counts = Db "SELECT (SELECT COUNT(*) FROM grade_tasks WHERE submission_id=$SubmissionId),(SELECT COUNT(*) FROM outbox_messages WHERE idempotency_key='$Key');"
        Write-Host "待处理任务数/Outbox数：$counts（预期1/1）"
        if ($counts -ne "1`t1") { throw '并发请求产生的任务或Outbox数量不符合预期。' }
    } finally { Dc start worker }

    # 轮询真实任务状态；最多等待60秒，不能把超时当作成功。
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
      $task = Api GET "/api/tasks/$TaskId"
        Require-Status $task 200
        Write-Host "任务状态：$($task.Data.status)"
        if ($task.Data.status -in @('succeeded', 'failed', 'dead')) { break }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    if ($task.Data.status -ne 'succeeded') { throw '任务未在期限内成功。' }
    $resultSql = "SELECT COUNT(*),MIN(score),MIN(SHA2(feedback,256)) FROM grade_results WHERE submission_id=$SubmissionId AND version=$Version;"
    $before = Db $resultSql
    if ($before.Split("`t")[0] -ne '1') { throw '首次完成后的结果不是1条。' }
    $attemptsBefore = Db "SELECT attempts,status FROM grade_tasks WHERE task_id='$TaskId';"
    Write-Host "首次结果数/评分/评语摘要：$before；任务尝试次数/状态：$attemptsBefore"
    if ($attemptsBefore -ne "1`tsucceeded") { throw '首次尝试次数或状态不符合本地无失败场景。' }

    # 读出实际payload；只重置本次提交版本的Outbox，不创建其他消息。
    $payload = Db "SELECT payload FROM outbox_messages WHERE idempotency_key='$Key';"
    $message = ConvertFrom-Json -InputObject $payload
  if ($message.task_id -ne $TaskId -or $message.submission_id -ne $SubmissionId -or
        $message.submission_version -ne $Version) { throw 'Outbox消息与目标任务不一致。' }
    # 先记录目标任务的跳过日志基线，后续只能用新增日志证明本次重投被处理。
    $baselineLogLines = @(Dc logs --no-log-prefix worker)
    $baselineEvents = @($baselineLogLines | ForEach-Object {
        try { ConvertFrom-Json -InputObject $_ } catch { }
    })
    $SkipBaseline = @($baselineEvents | Where-Object {
        $_.task_id -eq $TaskId -and $_.msg -eq 'worker_skip_terminal'
    }).Count
    $baselineLogLines | Set-Content (Join-Path $RunDir 'worker-before-redelivery.log')
    Write-Host "重投前目标任务终态跳过日志基线：$SkipBaseline"
    $changed = Db "UPDATE outbox_messages SET status='pending',next_attempt_at=NULL WHERE idempotency_key='$Key'; SELECT ROW_COUNT();"
    if ($changed -ne '1') { throw '未重置唯一的目标Outbox记录。' }
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 250
        $logLines = @(Dc logs --no-log-prefix worker)
        $events = @($logLines | ForEach-Object {
            try { ConvertFrom-Json -InputObject $_ } catch { }
        })
        $skips = @($events | Where-Object {
            $_.task_id -eq $TaskId -and $_.msg -eq 'worker_skip_terminal'
        })
    } while ($skips.Count -le $SkipBaseline -and [DateTime]::UtcNow -lt $deadline)
    if ($skips.Count -le $SkipBaseline) { throw '未观察到目标任务新增终态跳过日志，不能判通过。' }
    $NewSkipLogCount = $skips.Count - $SkipBaseline
    $logLines | Set-Content (Join-Path $RunDir 'worker.log')
    $after = Db $resultSql
    $attemptsAfter = Db "SELECT attempts,status FROM grade_tasks WHERE task_id='$TaskId';"
    Write-Host "重投后结果数/评分/评语摘要：$after；任务尝试次数/状态：$attemptsAfter"
    Write-Host "重投前基线：$SkipBaseline；重投后总数：$($skips.Count)；新增：$NewSkipLogCount（不是全部投递次数）"
    if ($before -ne $after -or $attemptsBefore -ne $attemptsAfter) {
        throw '重复消息改变了结果、评分、评语或任务执行次数/状态。'
    }
    Write-Host '本次并发入队和成功终态后重复消息断言满足。'
} finally {
    $Http.Dispose()
    Remove-Variable StudentPassword, Token, login, BrokerPassword, values -ErrorAction SilentlyContinue
}
# 保留专用环境及输出供检查；检查后可手动执行 Dc down，仅停止并移除本项目容器和网络。
# 不自动删除卷，不对其他项目执行stop/down，不把临时.env或登录响应交入报告。
```
