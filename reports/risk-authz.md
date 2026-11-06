# 高风险三查 · 权限 · CampusClaw

**用什么手段查：** 以已登录学生身份调用真实HTTP接口，检查跨班材料详情、文件访问和知识库检索；同时比较不存在材料的响应，并进行同班访问、检索对照。

**查了什么：** A班学生A1访问B班材料详情及文件；B班学生B1检索A班独有内容，覆盖keyword、vector、hybrid三种模式，且请求中附带A班class_id。已有同班对照为B1读取B班材料详情、A1检索A班内容

**判据：** 跨班材料详情及文件均返回404，与访问不存在材料时的响应状态、正文和Content-Type一致，避免暴露资源是否存在；B1跨班检索返回200，hits为空、命中数为0；B班学生可正常读取B班材料详情，A班学生可检索到A班内容。

**结果：** 绿。限本次跨班访问与跨班检索检查。A1访问B班材料详情、文件均返回404，与不存在材料的两组响应一致；B1三种检索模式均返回200、各命中0条；B1读取B班材料详情返回200，A1三种模式均返回200、各命中1条。

**复测命令：** 

```powershell
$ErrorActionPreference = 'Stop'
$BaseUrl = 'http://127.0.0.1:18080' # 可替换为已确认的服务地址
$StudentA = 'student_a1'
$StudentB = 'student_b1'
$PasswordA = '<填写A1现有密码>'
$PasswordB = '<填写B1现有密码>'
$BMaterialTitle = 'B班-牛顿定律笔记'
$AOnlyQuery = '单调递增'
if ($PasswordA.StartsWith('<') -or $PasswordB.StartsWith('<')) {
    throw '请先填写两个账号的现有密码，不要使用占位符登录。'
}
$NonexistentMaterialId = [long](Read-Host '输入经数据库或管理员确认全库不存在的正整数材料ID')
if ($NonexistentMaterialId -le 0) { throw '材料ID必须为正整数。' }

Add-Type -AssemblyName System.Net.Http
$Http = [System.Net.Http.HttpClient]::new()
$Http.Timeout = [TimeSpan]::FromSeconds(60)

function Invoke-ProjectApi {
    param([string]$Method, [string]$Path, [string]$Token = '', $Body = $null)
    $request = [System.Net.Http.HttpRequestMessage]::new(
        [System.Net.Http.HttpMethod]::new($Method), "$($BaseUrl.TrimEnd('/'))$Path")
    $response = $null
    try {
        if ($Token) {
            $request.Headers.Authorization =
                [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $Token)
        }
        if ($null -ne $Body) {
            $json = ConvertTo-Json -InputObject $Body -Depth 8 -Compress
            $request.Content = [System.Net.Http.StringContent]::new(
                $json, [System.Text.Encoding]::UTF8, 'application/json')
        }
        $response = $Http.SendAsync($request).GetAwaiter().GetResult()
        $text = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $parsed = $null
        if ($text) {
            try { $parsed = ConvertFrom-Json -InputObject $text }
            catch { $parsed = $null }
        }
        $status = [int]$response.StatusCode
        Write-Host "$Method $Path -> HTTP $status"
        [pscustomobject]@{
            Status = $status
            Text = $text
            ContentType = [string]$response.Content.Headers.ContentType
            Json = $parsed
        }
    }
    finally {
        if ($null -ne $response) { $response.Dispose() }
        $request.Dispose()
    }
}
function Assert-Status {
    param($Response, [int]$Expected, [string]$Step)
    if ($Response.Status -ne $Expected) {
        throw "$Step：期望HTTP $Expected，实际HTTP $($Response.Status)"
    }
}

function Get-PositiveClassId {
    param($Response, [string]$Step)
    if ($null -eq $Response.Json -or
        $null -eq $Response.Json.PSObject.Properties['class_id']) {
        throw "${Step}：响应缺少class_id字段。"
    }
    $classId = $Response.Json.class_id
    if (($classId -isnot [int] -and $classId -isnot [long]) -or $classId -le 0) {
        throw "${Step}：class_id必须为有效正整数。"
    }
    return [long]$classId
}

try {
    # 两次登录应为200，并从真实token字段取得凭据。
    $loginA = Invoke-ProjectApi -Method POST -Path '/api/login' -Body @{
        username = $StudentA; password = $PasswordA
    }
    Assert-Status $loginA 200 'A1登录'
    $TokenA = [string]$loginA.Json.token
    $loginB = Invoke-ProjectApi -Method POST -Path '/api/login' -Body @{
        username = $StudentB; password = $PasswordB
    }
    Assert-Status $loginB 200 'B1登录'
    $TokenB = [string]$loginB.Json.token
    if (-not $TokenA -or -not $TokenB) { throw '登录响应缺少token字段。' }

    $meA = Invoke-ProjectApi -Method GET -Path '/api/me' -Token $TokenA
    $meB = Invoke-ProjectApi -Method GET -Path '/api/me' -Token $TokenB
    Assert-Status $meA 200 'A1身份确认'
    Assert-Status $meB 200 'B1身份确认'
    if ($meA.Json.role -ne 'student' -or $meA.Json.class_name -ne 'A' -or
        $meB.Json.role -ne 'student' -or $meB.Json.class_name -ne 'B') {
        throw '账号身份或班级不符合前提，停止检查。'
    }
    $AClassId = Get-PositiveClassId $meA 'A1身份响应'
    $BClassId = Get-PositiveClassId $meB 'B1身份响应'

    $listB = Invoke-ProjectApi -Method GET -Path '/api/materials' -Token $TokenB
    Assert-Status $listB 200 'B1材料列表'
    $matchesB = @($listB.Json.materials | Where-Object { $_.title -eq $BMaterialTitle })
    if ($matchesB.Count -ne 1) { throw '未找到唯一的B班目标讲义，请核对标题。' }
    $BMaterialId = [long]$matchesB[0].id
    if ($NonexistentMaterialId -eq $BMaterialId) { throw '不存在材料ID不能是目标讲义ID。' }
    $owner = Invoke-ProjectApi -Method GET -Path "/api/materials/$BMaterialId" -Token $TokenB
    Assert-Status $owner 200 'B1读取本班材料详情'
    $MaterialClassId = Get-PositiveClassId $owner '目标材料响应'
    if ($MaterialClassId -ne $BClassId) {
        throw '目标材料不属于B1所在班级。'
    }

    # A1读取B班详情、文件：均应404；与不存在材料的对应响应逐项比较。
    foreach ($suffix in @('', '/file')) {
        $cross = Invoke-ProjectApi -Method GET -Token $TokenA `
            -Path "/api/materials/$BMaterialId$suffix"
        $missing = Invoke-ProjectApi -Method GET -Token $TokenA `
            -Path "/api/materials/$NonexistentMaterialId$suffix"
        Assert-Status $cross 404 "A1跨班材料访问$suffix"
        Assert-Status $missing 404 "不存在材料对照$suffix"
        if ($cross.Text -cne $missing.Text -or $cross.ContentType -cne $missing.ContentType) {
            throw "材料访问$suffix：跨班与不存在材料的正文或Content-Type不一致。"
        }
        Write-Host "材料访问$suffix：两请求均404，正文及Content-Type一致。"
    }

    # 三种模式：A1应200且至少1条；B1即使指定A班class_id仍应200且0条。
    foreach ($mode in @('keyword', 'vector', 'hybrid')) {
        $positive = Invoke-ProjectApi -Method POST -Path '/api/search' -Token $TokenA -Body @{
            query = $AOnlyQuery; mode = $mode
        }
        Assert-Status $positive 200 "A1同班检索$mode"
        $cross = Invoke-ProjectApi -Method POST -Path '/api/search' -Token $TokenB -Body @{
            query = $AOnlyQuery; mode = $mode; class_id = $AClassId
        }
        Assert-Status $cross 200 "B1跨班检索$mode"
        if ($null -eq $positive.Json -or $null -eq $cross.Json -or
            -not $positive.Json.PSObject.Properties['hits'] -or
            -not $cross.Json.PSObject.Properties['hits'] -or
            $positive.Json.hits -isnot [array] -or $cross.Json.hits -isnot [array]) {
            throw '两份检索响应的hits均必须为数组；缺失、null或其他类型不能作为空结果。'
        }
        $positiveCount = @($positive.Json.hits).Count
        $crossCount = @($cross.Json.hits).Count
        Write-Host "$mode：A1 HTTP 200，命中$positiveCount 条；B1 HTTP 200，命中$crossCount 条。"
        if ($positiveCount -lt 1) { throw "$mode：A1没有命中，无法据此判定跨班隔离。" }
        if ($crossCount -ne 0) { throw "$mode：B1跨班检索出现命中，检查不通过。" }
    }
    Write-Host '上述跨班访问与检索断言均满足；本输出仅代表本次手动运行。'
}
finally {
    $Http.Dispose()
    Remove-Variable PasswordA, PasswordB, TokenA, TokenB, loginA, loginB -ErrorAction SilentlyContinue
}
```

