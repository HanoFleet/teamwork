# 门禁证据

版本 bd42a6149e975c1ed217fb9349621443a3be53d5。自测红退出1、清理后绿退出0，整体退出0：qa/lesson9/logs/gate-selftest-retry.txt。当前实际依赖审计退出非0，高危5；不能满足“修复后正常make check-security绿”。make入口缺失阻塞。