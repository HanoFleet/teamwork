> 性能条款由活动change `2026-11-18-observe-enqueue-latency` 替代。下文100ms阻断为旧规则决策记录，现行规则为100ms警告、20次P95 < 500ms硬断言。历史失败完整保留。

# 设计

## Context
本轮授权修复L9-DEP-001及复测性能，不扩大业务范围。五项任务构成一组整改；spec_check登记min_tasks=5，保留其他change原门槛及全部结构/失败路径检查。

## Decisions
### D1: 兼容依赖
选了什么：显式安装经审计的兼容版本。放弃了什么：force、隐藏传递告警。代价由谁承担：测试负责人保留无法清零证据，开发后续等待安全发布或另提工具链迁移。
### D2: 如实性能门禁
选了什么：保持20次及100ms，不改业务直到定位根因。放弃了什么：删除慢样本。代价由谁承担：负责人保留失败结果及根因调查范围。

## Interfaces
接口与角色不变；复用现有400、403、404、503路径。

## Data Model
无业务表变化；新增JSON样本、源码档案与CSV历史行。

## Migration Plan
锁文件重装；回退仅恢复package.json及lock，不涉及数据库迁移。

## Risks / Trade-offs
上游无安全picomatch发布，升级仍可能high5；不发布。Windows/Docker时序及I/O影响单次延迟，严格保留100ms失败。

## 依赖
修复前官方npm audit为high5/critical0，根公告GHSA-fc5q-39xc-vjpf影响picomatch<=4.0.7。当前registry的latest仍为4.0.7，简单升级Vite8不能证明消除风险。验证audit建议的Vite6.2.7与React插件5.2.0组合：官方peer范围相容，Vite6.2.7不依赖tinyglobby链。先验证再决定；不用audit fix --force、不用未经验证的override、不降低审计等级。该工具链调整为开发依赖，不改变产品路由与业务行为。若出现其他通报则继续按实际审计处置。

## 性能
依赖试验结果：Vite6.2.7组合仍有其他Vite高危，已拒绝并保留audit-rejected-vite6.json。最终采用同主版本兼容补丁Vite8.3.8和React插件6.3.0；官方picomatch没有已发布安全版本，最终审计仍high5，不声称缺陷修复完成，不绕过门禁。记录这5条的同根依赖与处置限制，后续须等待上游安全发布或另起明确的构建工具迁移change。

先在同一隔离Compose、相同20次顺序提交/202计时口径重放，保留每次样本。区分客户端耗时、API日志耗时与数据库等待；没有可复现根因不修改业务实现。不得通过预热删除首样本或提高100ms阈值宣称通过。

## 测试与证据
历史原脚本只读快照放scripts/qa/lesson9/history；最终包装器存在但早期被覆盖的版本标为原脚本缺失。新入口放scripts/qa/lesson9，使用随机临时凭据及专属Compose项目，不写凭据到证据；仅清理本次专属资源。LF独立工作树解决Windows检出换行影响，不修改格式门槛。真人签字、正式录像仍由组员完成。

## 第二轮：移除实际引入漏洞的开发工具链

实际源码只有 React/TSX/CSS 和客户端路由；没有 import.meta.env、Vite 插件扩展或静态资源 glob。Vite 与 React 插件是实际使用的构建工具，不能当作未使用依赖简单删除。单纯升级和 audit 建议降级已验证失败；Rsbuild 2.3.3 虽 audit=0，但 dist/tinyglobby.js 内嵌同类组件，拒绝仅以审计消失作为修复。

选择 MIT 许可证、活跃维护的官方 esbuild 0.28.2（Node>=18）替换两项构建开发依赖；TypeScript noEmit、React 和所有产品运行时依赖保持原范围。使用 esbuild 官方 JSX/CSS/serve/watch API，薄包装只负责现有 HTML 入口、开发 API/health 代理和 preview；开发更新使用整页刷新，明确不保留 Vite 专属 React Fast Refresh 的组件状态保留。这是开发工具体验变化，不改变页面、HTTP 授权或生产数据。生产只输出静态 dist，继续由原 Nginx 镜像部署。

必须验证 npm ci、全量原阈值 audit、Docker 构建、开发/预览深链接与代理、作业页及 XSS 浏览器回归。新测试统一放 tests/，原历史脚本保留。无 overrides、audit omit 或公告豁免。回退恢复此前记录的 package/lock、Vite 配置及 HTML，不涉及数据库。

第二轮性能先用原 20 次 fresh submission/grade 计时，关联现有 request_id 访问日志、MySQL performance_schema 的规范化 SQL/等待和容器资源。数据库观测仅在本轮专属测试实例启用，对比两侧保持相同设置。不得关闭持久化、跳过提交、预热删样本或改变计时边界。

### D3: 只收窄 dispatcher 锁定读取的隔离范围

选了什么：仅 dispatcher 批次事务使用 READ COMMITTED。放弃了什么：全局降低隔离级别、关闭刷盘或删除慢样本。代价由谁承担：开发维护者评审批次事务快照假设，测试负责人复现补投/幂等及全部单次样本。

修改前 round-02/before-lock-fix 的 data_lock_waits 捕获插入 outbox_messages 被 PRIMARY supremum 的 X 记录锁阻塞；访问日志与语句 LOCK_TIME 对应慢请求。默认 REPEATABLE READ 的下一键/间隙锁随 dispatcher 的批量发布和 confirm 等待保持，阻止本来没有共享业务行的新 outbox 插入。

仅 dispatcher.flush 的 BeginTx 指定 READ COMMITTED；保留相同 FOR UPDATE SKIP LOCKED、批次20、发布确认及事务提交。唯一约束、API/worker 事务隔离、InnoDB/binlog 刷盘和至少一次语义不变。风险是读取不再具有可重复读快照，但该事务只锁取一次 pending 批次并按 id 更新；不依赖重复快照。验证跨班/幂等/事务回滚/停 broker 补投与20次严格门槛。若同条件仍出现单次>100ms，整项性能仍不通过，不以锁等待下降代替验收。

构建恢复：本轮两次 proxy.golang.org 模块下载 EOF，原 make check 已采用 goproxy.cn,direct。后端 Dockerfile 仅开放同名 GOPROXY build arg，默认保持 proxy.golang.org,direct；本地隔离构建显式传仓库既有 goproxy.cn,direct，并保留 go.sum 校验，不关闭 sumdb。此配置不进入应用运行环境，不修改业务行为。
