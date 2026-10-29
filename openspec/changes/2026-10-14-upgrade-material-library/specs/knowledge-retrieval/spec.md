# knowledge-retrieval Specification

## Purpose

规定迭代 2 的本班知识库检索：切片入库、三种检索模式、出处可回溯，以及没有依据时不得生成回答。本 change 修改索引时机、原文坐标、重建方式和引用版本；未列出的既有条款继续有效。

## MODIFIED Requirements

### Requirement: 上传后切分并建立索引

教师上传成功、材料行、版本 1 和 `knowledge_entries` 已提交之后，系统 MUST 在后台按本次切分策略把当前版本正文切成切片，写入 `knowledge_chunks`，再按每批 32 条调用嵌入服务，把向量写入 Qdrant。每次索引任务 MUST 绑定开始时的 `material_id`、`version` 和 generation；worker 完成时若 `materials.current_version` 已变化或材料行已不存在，MUST NOT 切换 `current_generation`，只清理本次新 generation，并把材料留给新版本的任务。上传接口 MUST 在索引完成前返回 201；材料 MUST 暴露 `pending`、`indexing`、`ready`、`failed` 状态和 `index_error`。向量主键 MUST 等于切片 id，并与 payload 中的 `chunk_id` 相同。Qdrant payload MUST 只含 `class_id`、`material_id`、`knowledge_entry_id`、`chunk_id`、`chunk_index`、`generation`，MUST NOT 含切片正文。未指定策略时 MUST 使用 `auto`：最大 800 字、重叠 80 字，优先在空行、换行、句号处断开。种子材料和重启时处于 `pending` 或 `indexing` 的材料 MUST 重新排队。`knowledge_entries.body` MUST 是当前版本的原文或抽取文本，预处理不得改写该字段。迁移前已存在的切片 MUST 保留 `generation=0` 作为 legacy，可继续检索，但不保证 `start/end` 可高亮。

#### Scenario: 上传后本班可按原文检索

- **GIVEN** `teacher_a` 持有有效会话，A 班已有可用的嵌入和 Qdrant
- **WHEN** 上传一份含「单调递增」的合法材料，等待 `index_status=ready`
- **THEN** 上传响应为 201，初始状态为 `pending` 或 `indexing`
- **AND** 以该教师会话调用 `keyword` 检索「单调递增」得到该材料命中
- **AND** 命中带材料标题、切片序号、`version=1` 和原文区间

#### Scenario: 嵌入失败时原文仍在

- **GIVEN** 嵌入服务对某条切片返回错误
- **WHEN** 教师上传该材料
- **THEN** 材料行、版本 1 和知识库正文仍然存在
- **AND** `index_status=failed`，`index_error` 非空
- **AND** Qdrant 中没有这条不完整向量，教师可以调用 reindex 重试

#### Scenario: 未指定策略按自动窗口切分

- **GIVEN** 教师上传或重建索引时不传策略，或策略为空
- **WHEN** 后台索引执行
- **THEN** 系统按 `auto` 切分：窗口最大 800 字、重叠 80 字
- **AND** 请求里另行填写的长度与预处理参数不生效

#### Scenario: 索引状态可观察

- **GIVEN** 教师上传一份合法材料
- **WHEN** 立即查询材料详情，随后每 2 秒查询一次
- **THEN** 第一次为 `pending` 或 `indexing`
- **AND** 完成后变为 `ready`；失败时为 `failed` 且带 `index_error`
- **AND** 状态变化不需要重新上传

#### Scenario: 重启补排未完成索引

- **GIVEN** 两份材料分别处于 `pending` 和 `indexing`，api 被停止
- **WHEN** api 重新启动
- **THEN** 两份材料重新进入队列
- **AND** 最终都变为 `ready`，或失败并记录原因
- **AND** 已 ready 的材料不重复索引，版本和切片 id 不变化

#### Scenario: 向量 payload 不含正文

- **GIVEN** 一份材料已完成索引
- **WHEN** 直接查询 Qdrant 的该材料点
- **THEN** payload 只含 `class_id`、`material_id`、`knowledge_entry_id`、`chunk_id`、`chunk_index`、`generation`
- **AND** payload 不含 `chunk_text`、正文摘录或密钥

#### Scenario: 旧 generation 在新索引就绪前可用

- **GIVEN** 材料已有 `generation=1` 的 ready 切片，教师触发重建
- **WHEN** 新 generation 尚未完成
- **THEN** 检索仍返回旧 generation 的命中
- **AND** 旧切片的 `start/end` 若为 legacy，则前端只显示摘录，不强行高亮

### Requirement: 三种检索模式

系统 MUST 提供 `keyword`、`vector`、`hybrid` 三种模式，未指定时 MUST 使用 `hybrid`。空查询 MUST 返回 400。`POST /api/search` MAY 接受 `scope` 对象 `{material_ids?: number[], tag?: string}`，两者同时出现时取交集；`material_ids` 中每个 id MUST 存在于会话班级，跨班、已删除或不存在的 id MUST 返回同形 404；省略 `material_ids` 等于不限，空数组等于无结果；`tag` MUST 为 1 至 32 个字符；省略 `scope` 等于本班全部材料。`keyword` MUST 只查 MySQL 全文索引（`FULLTEXT ... WITH PARSER ngram`，token 长度 2），只查 `materials.current_generation` 中 `index_status='ready'` 的切片，MUST NOT 调用嵌入，MUST NOT 访问 Qdrant。`vector` MUST 先把问句做成向量，在 Qdrant 里按会话班级和当前 generation 过滤，丢弃余弦相似度低于 0.35 的候选，再用向量主键回 MySQL 取正文。`hybrid` MUST 同时走两路，各路先按自己的规则过滤，再用 RRF（`k = 60`）按名次融合；缺席的一路 MUST NOT 贡献分数。摘录 MUST 取自 MySQL 的 `chunk_text`。Qdrant 不可用时，`keyword` MUST 仍能返回结果；`vector` 与 `hybrid` MUST 返回 503，MUST NOT 编造相似度。

#### Scenario: 原文用词走关键字路径

- **GIVEN** A 班用户持有有效会话，预置讲义已 ready
- **WHEN** 以模式 `keyword` 检索预置讲义中出现的「单调递增」
- **THEN** 响应为 200，`hits` 含 A 班该讲义的切片
- **AND** 本次请求不产生问句向量，也不访问 Qdrant

#### Scenario: 同义改写走向量路径

- **GIVEN** A 班材料已 ready，问句未在原文中出现
- **WHEN** 以模式 `vector` 检索「自变量变大时函数值跟着变大」
- **THEN** 若存在余弦相似度不低于 0.35 的本班切片，`hits` 非空，并按相似度从高到低
- **AND** 摘录仍来自 MySQL 切片正文，响应不含向量分量

#### Scenario: 混合按名次融合而不是加分

- **GIVEN** 同一问句在关键字和向量两路都有命中
- **WHEN** 分别以 `keyword`、`vector`、`hybrid` 检索
- **THEN** `hybrid` 的排序由 RRF（`k = 60`）决定，两路都出现的切片更靠前
- **AND** 响应可对照两路的 `score` 与 `rank`，不得把全文相关度与余弦相似度直接相加

#### Scenario: Qdrant 停止时关键字仍可用

- **GIVEN** Qdrant 容器已停止
- **WHEN** A 班用户分别用 `keyword`、`vector` 和 `hybrid` 检索本班原文用词
- **THEN** `keyword` 仍返回 200 且能给出本班摘录
- **AND** `vector` 与 `hybrid` 返回 503，`error=unavailable`

#### Scenario: 空查询被拒绝

- **GIVEN** 已登录用户
- **WHEN** 提交空白或只含空白的检索问句
- **THEN** 响应状态为 400，`error=invalid_query`
- **AND** 不调用嵌入，不查询 Qdrant

#### Scenario: 非当前 generation 不参与检索

- **GIVEN** 材料同时存在 generation 0 和 generation 2 的切片，当前 generation 为 2
- **WHEN** 以 `keyword` 和 `vector` 检索该材料独有词
- **THEN** 只返回 generation 2 的切片
- **AND** generation 0 的切片不进入结果

#### Scenario: 未 ready 切片不参与检索

- **GIVEN** 材料的当前版本有 `pending`、`failed` 和 `ready` 三种切片
- **WHEN** 用户检索当前版本独有词
- **THEN** 只有 `ready` 切片进入结果
- **AND** `pending` 和 `failed` 切片不贡献分数，也不触发嵌入

#### Scenario: scope 限定材料与标签

- **GIVEN** A 班材料 m1 标签为「第一章」，m2 无标签；B 班材料 m3
- **WHEN** A 班用户以 `keyword` 检索并在 `scope` 中分别指定 `{material_ids:[m1]}`、`{tag:"第一章"}`、`{material_ids:[m3]}`
- **THEN** 前两次只返回 m1 的命中
- **AND** 第三次因为 m3 不属于本班而返回同形 404
- **AND** 空 `scope` 与不传 `scope` 结果相同

### Requirement: 命中必须可回溯至原文

每条命中 MUST 包含材料 id、材料标题、`version`、切片序号、`start`、`end`、`excerpt`，PDF 或 PPT 另带 `page` 或 `slide`；跨页切片 MUST 报告 `start_page`/`start_slide`（切片起始页）。`start` 含、`end` 不含，单位是当前版本正文的 Unicode 码点。调用方 MUST 能用材料 id 打开本班材料详情。摘录 MUST 来自 MySQL，MUST NOT 来自 Qdrant payload。所选模式过滤后没有候选时，响应 MUST 为 200，`hits` 为空，并给出文案「资料中未找到相关内容」。系统 MUST NOT 用低于阈值的切片凑数。

#### Scenario: 命中带出处字段

- **GIVEN** 本班检索返回至少一条 `hits`
- **WHEN** 检查响应
- **THEN** 每条都有材料 id、标题、`version`、切片序号、字符区间和摘录
- **AND** 用其中的材料 id 调用本班详情接口可以打开该材料

#### Scenario: 本班没有依据时不凑数

- **GIVEN** A 班用户，本班材料不含天气或比分内容
- **WHEN** 以模式 `hybrid` 检索「今日天气」或「比赛比分」
- **THEN** 响应为 200，`hits` 为空
- **AND** 文案为「资料中未找到相关内容」

#### Scenario: 引用带版本和页码

- **GIVEN** 一份 PDF 材料已 ready，当前版本为 2
- **WHEN** 检索命中第 5 页的一段
- **THEN** 命中含 `version=2` 和 `page=5`
- **AND** `start`、`end` 指向版本 2 原文的码点，而不是预处理后的文本

#### Scenario: 码点区间可高亮

- **GIVEN** 材料正文在命中位置之前含 emoji
- **WHEN** 前端按 `start` 和 `end` 截取正文
- **THEN** 截取出的文本与 `excerpt` 一致
- **AND** 不会因为 UTF-16 长度差异而偏移

#### Scenario: 旧版本引用仍可解释

- **GIVEN** 一条引用保存了 `version=1`，材料当前版本为 3
- **WHEN** 用户打开该引用
- **THEN** 响应仍返回引用当时的 `excerpt` 和 `version=1`
- **AND** 前端显示「原文已更新」，不把 v1 的偏移直接套到 v3

### Requirement: 检索侧的班级隔离

检索接口 MUST 只使用会话中的 `class_id`。查询参数、JSON 正文和请求头里的 `class_id` MUST 在解析后丢弃。关键字路径的 SQL MUST 带 `class_id = 会话班级`，且只检索当前 generation 中 `index_status='ready'` 的切片。向量路径的 Qdrant 查询 MUST 带同一 `class_id` 和 `generation` 过滤；回 MySQL 取正文时 MUST 再次核对班级。payload 中的编号 MUST NOT 单独作为正文来源。跨班检索 MUST 返回 200 且 `hits` 为空（或同一句「资料中未找到相关内容」），MUST NOT 用 403 或 404 暗示该词属于其他班。按材料 id 打开详情仍遵守 `auth-upload`：跨班与不存在都是同形 404。

#### Scenario: 请求里的班级字段不改变过滤

- **GIVEN** `teacher_a` 属于 A 班，B 班正文只出现「牛顿定律」
- **WHEN** 检索「牛顿定律」，并在请求体或查询参数中写入 B 班的 `class_id`
- **THEN** 两次结果都是 200，`hits` 为空
- **AND** 结果中不出现「B班-牛顿定律笔记」的标题或摘录

#### Scenario: 关键字与向量都按会话班级过滤

- **GIVEN** A 班用户持有有效会话
- **WHEN** 分别用 `keyword` 和 `vector` 检索 B 班独有用词
- **THEN** 两路都没有 B 班切片
- **AND** 回表查询使用的班级仍是会话中的 A 班

#### Scenario: 本班学生可以检索

- **GIVEN** `student_a1` 持有有效会话
- **WHEN** 以模式 `keyword` 检索本班讲义中的「单调递增」
- **THEN** 响应为 200，`hits` 含该讲义的切片
- **AND** 摘录可打开对应材料详情

#### Scenario: 跨班打开材料详情仍是 404

- **GIVEN** A 班用户，B 班存在材料 id=99
- **WHEN** 用 id=99 请求材料详情
- **THEN** 响应为 404，与请求不存在的 id 相同
- **AND** 这与检索接口返回空 `hits` 的 200 不是同一种响应

#### Scenario: 只检索当前 generation 的本班切片

- **GIVEN** A 班材料有旧 generation 和当前 generation 的切片
- **WHEN** A 班用户检索该材料独有词
- **THEN** 只返回当前 generation 中属于 A 班的切片
- **AND** 旧 generation 和 B 班切片都不出现

#### Scenario: 索引中编辑不切换旧版本

- **GIVEN** 材料 v1 正在 `indexing`，教师随后保存 v2
- **WHEN** v1 的 worker 完成
- **THEN** `current_generation` 不切换，v1 新 generation 被清理
- **AND** 材料保持 pending 等待 v2；v2 ready 后检索只使用 v2

### Requirement: 三种切分策略与重建索引

系统 MUST 支持 `auto`、`custom`、`hierarchy`。`custom` 的最大长度 MUST 在 100 至 2000 字，重叠比例 MUST 在 0% 至 50%；`hierarchy` MUST 按 Markdown 标题分章，过长时再套 `auto`。已入库材料 MUST NOT 自动改切分。教师重建索引 MUST 接受 JSON `{strategy?, max_len?, overlap_ratio?}`，`strategy` 默认 `auto`；`custom` MUST 同时提供 `max_len`（100–2000）和 `overlap_ratio`（0–0.5），缺失或越界 MUST 返回 400 `invalid_query`。材料已 `pending`/`indexing` 时，reindex MUST 返回 202 并用本次参数替换排队任务；在途 run 完成后按最新参数重排，MUST NOT 并行两个 worker。上传、编辑、替换、恢复默认复用 `materials.index_strategy` 保存的最近显式策略；reindex 显式传 `strategy` 时更新该列。重建 MUST 返回 202 并使用新的 generation 先写入；全部成功后 MUST 在一个事务里切换 `materials.current_generation`、删除旧切片，事务提交后再删除旧向量（MUST NOT 在事务内调用 Qdrant）。重建期间旧索引 MUST 照常可检索；失败时 MUST 只清理新 generation，旧 generation 保持 ready。启动时 MUST 把 `pending` 或 `indexing` 的材料重新排队。学生调用重建 MUST 返回 403，且切片与向量不变。

#### Scenario: 更换策略必须显式重建

- **GIVEN** 同一份带标题的材料先用 `auto` 建好索引
- **WHEN** 教师用 `hierarchy` 重建并等待 ready
- **THEN** 重建成功后只保留 hierarchy generation 的切片和向量
- **AND** 原 auto 切片和向量已删除
- **AND** `knowledge_entries.body` 仍是当前版本原文

#### Scenario: 重建参数非法

- **GIVEN** 本班教师和一份已有索引的材料
- **WHEN** 调用 reindex，`strategy` 为 `unknown`，或 `custom` 的 `max_len=99`，或 `overlap_ratio=0.6`
- **THEN** 每次响应都是 400，`error=invalid_query`
- **AND** `current_generation`、切片和向量都不变

#### Scenario: 学生不得重建索引

- **GIVEN** `student_a1` 持有有效会话，本班材料 id=1
- **WHEN** 调用 `POST /api/materials/1/reindex`
- **THEN** 响应状态为 403，`error=forbidden`
- **AND** 该材料的切片行和向量记录都不变化

#### Scenario: 不重建则旧切片保留

- **GIVEN** 材料已经按 `auto` 建好索引
- **WHEN** 教师没有调用重建，只修改标题或标签
- **THEN** 旧切片和向量主键仍在
- **AND** 检索仍使用这些切片

#### Scenario: 重建返回 202 且期间旧索引可用

- **GIVEN** 材料当前 generation 为 1，已 ready
- **WHEN** 教师调用 reindex
- **THEN** 响应状态为 202，`index_status=pending`
- **AND** 在新 generation 完成前，检索仍返回 generation 1 的命中
- **AND** 完成后 `current_generation` 变为新值，旧切片和向量被删除

#### Scenario: 重建失败保留旧索引

- **GIVEN** 材料当前 generation 为 1，已 ready
- **WHEN** 重建过程中嵌入服务返回错误
- **THEN** 材料状态为 `failed`，`index_error` 非空
- **AND** 只清理新 generation 的切片和向量，generation 1 仍 ready 并可检索

#### Scenario: 重启补排未完成重建

- **GIVEN** 材料在重建过程中 api 被停止，状态为 `indexing`
- **WHEN** api 重新启动
- **THEN** 该材料重新排队
- **AND** 旧 generation 在重排完成前仍可检索
- **AND** 新 generation 成功后完成切换，失败则保留旧 generation
