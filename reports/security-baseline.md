# 资产类安全基线

- **密钥扫描（SEC-05）：** 于Git版本基准`292eaaff`执行，测试时包含未提交修改。扫描提交历史、前端产物及本轮API/worker运行日志，共检查403个历史文本blob、7个前端文件，发现0个密钥候选。实际命令如下：

  ```powershell
  Set-Location 'E:\proj\teamwork-main-latest'
  & 'F:\Anaconda\python.exe' scripts/secret_scan.py
  git rev-list --objects --all
  ```

  扫描器输出原文如下：

  ```text
密钥边界检查通过：工作树和提交历史都没有非空密钥赋值。
  ```

  原扫描器secret_scan.py的退出码为`0`。补充扫描由`week8_security.py`内部执行，保存的结果字段摘录如下：
  
  ```json
{
    "all_refs": true,
  "git_text_blobs": 403,
    "excluded_binary_blobs": 3,
    "frontend_files": 7,
    "runtime_logs_present": true,
  "candidate_count": 0,
    "confirmed_live_count": null
}
  ```
  
  说明：0候选限于已扫描范围；3个二进制blob、压缩包内部及此前和其他服务日志未覆盖。补充扫描没有独立进程退出码，不与原扫描器退出码混用。
  
- **依赖审计（SEC-06）：**于同日执行npm audit及govulncheck审计。npm高危0、严重0；Go源码检出46个通报，其中20个具有多帧调用路径；部署二进制检出45个通报。实际执行命令如下：

  ```powershell
  # 前端依赖
  Set-Location 'E:\proj\teamwork-main-latest\frontend'
  & 'E:\npm.cmd' audit --json --audit-level=high --package-lock-only --registry=https://registry.npmjs.org
  
  # Go源码
  Set-Location 'E:\proj\teamwork-main-latest\backend'
  go run golang.org/x/vuln/cmd/govulncheck@v1.1.4 -json ./...
  
  # 实际部署二进制
  $BinaryPath = '<填写从API容器复制出的实际后端二进制文件路径>'
  go run golang.org/x/vuln/cmd/govulncheck@v1.1.4 -json -mode=binary "$BinaryPath"
  ```

  npm原始输出中的漏洞统计：

  ```json
  {
    "info": 0,
    "low": 0,
    "moderate": 0,
    "high": 0,
    "critical": 0,
    "total": 0
  }
  ```

  三项命令的历史退出码均为0；govulncheck退出0不代表没有漏洞。

- **一键入口：** `make check-security`调用`python3 scripts/week8_security.py --baseline-only`，覆盖SEC-05的Git文本及已有前端产物扫描，以及SEC-06的npm、Go源码审计，入口已在`README.md`注明。Windows未安装make时，可使用等价命令：

  ```powershell
  Set-Location 'E:\proj\teamwork-main-latest'
  python scripts/week8_security.py --baseline-only
  ```

  说明：历史环境因未安装make，未执行原生入口；该入口尚不包含运行日志、部署前端产物的采集及部署二进制审计。运行会重新生成六份报告，复跑前需备份手工修改稿。
## 第 9 课修正与复测

- 上文提到的 `scripts/week8_security.py` **不存在于本仓库**；第 9 课已把入口改为 `scripts/security_gate.py`，由 `make check-security` 调用。
- 当前实际命令：

```bash
make check-security
# 等价：python3 scripts/security_gate.py
```

- 实际输出：
  - `python3 scripts/secret_scan.py`：工作树和提交历史 0 个非空密钥赋值；
  - `npm audit --audit-level=high`：0 vulnerabilities；
  - 假密钥 self-test：退出 1；干净临时仓库：退出 0。
- 详见 `reports/gate-red-green.md`。
- Go `govulncheck` 历史基线仍保留在上文（46 条通报、20 条多帧路径、部署二进制 45 条）。2026-11-17 已用升级清零，不再把这组数字当作当前风险。

## 2026-11-17 复扫

- 工具链：Go 1.26.11。命令：`GOTOOLCHAIN=go1.26.11 go run golang.org/x/vuln/cmd/govulncheck@v1.9.0 ./...`
- 实际输出：`No vulnerabilities found.`，退出码 0。
- 升级记录和升级前的 47 个编号见 `reports/govuln-disposition.md`。
- 门禁：`python3 scripts/govuln_check.py`。有 Go 或 Docker 时现场重扫；否则核对 `reports/govuln-snapshot.txt` 与 `backend/go.sum`。
