# 本轮缺陷 L9-DEP-001

- 类别：资产/依赖；严重程度：高；关联用例：SEC-06。
- 发现版本：bd42a6149e975c1ed217fb9349621443a3be53d5；环境：Windows，npm官方registry；时间见原始JSON及执行记录。
- 前置：使用该提交 frontend/package-lock.json，网络可访问 registry.npmjs.org。
- 操作：在 frontend 执行 `npm audit --json --audit-level=high --package-lock-only --registry=https://registry.npmjs.org`。
- 预期：high=0、critical=0，退出0；或提供逐漏洞可检查的处置登记。
- 实际：退出1，high=5、critical=0；涉及 @vitejs/plugin-react、fdir、picomatch、tinyglobby、vite。条目包括传递影响，不等于5个不同漏洞。
- 证据：[原始JSON](../../qa/lesson9/logs/npm-audit-retry.json)、[退出码](../../qa/lesson9/logs/npm-audit-retry.exit.txt)。漏洞编号、URL、影响范围、修复建议逐项见JSON；未推断生产可利用性。
- 状态：待开发处理，待复测；没有可验证的修复提交。未修改依赖或业务代码。
- 复测：开发提供修复提交后，用同一命令重跑，再验证前端构建、单元与相关业务流程；保留本轮失败JSON。

环境阻塞不作为功能缺陷：Docker daemon不可连接，缺make/sh，独立工作树没有.env。需要恢复隔离Compose和测试凭据。历史SEC-03/04/07的复测状态详见缺陷复测表，不能因修复已合并就关闭。
