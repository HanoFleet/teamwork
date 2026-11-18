# 当日安全基线

版本 bd42a6149e975c1ed217fb9349621443a3be53d5。密钥扫描退出0（logs/secret.txt）；npm官方审计high=5、critical=0，未清零。涉及 @vitejs/plugin-react, fdir, picomatch, tinyglobby, vite。完整漏洞编号、影响范围、修复建议见qa/lesson9/logs/npm-audit-retry.json。未执行当日govulncheck；历史快照不算当日扫描。