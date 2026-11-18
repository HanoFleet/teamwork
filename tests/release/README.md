## 2026-11-18 archive revision

The default verifier now uses `lesson9-v2-archive.json`. The prior `lesson9-v2-publication.json` remains tied to commit `5b2a8f51ee295771c11248d1e3be1bc12919ebeb`. The archive revision records the two OpenSpec moves, checked tasks, and canonical spec updates. Historical manifests and evidence retain their original bytes.

# 第9课发布索引

`lesson9-v2-publication.json`记录以2d2900bf34b52d8df21513c6ef2ebc873df9f345为基线的选定工作树增量。files逐项包含worktree_sha256和git_blob_sha256。普通源码可按根属性转换LF；不可变历史证据必须两个值相同。索引不包含自身，验证输出与最终报告另有独立证据索引，避免自引用。

运行`python scripts/qa/lesson9/verify_release.py`校验工作树发布文件、历史manifest和别名；在隔离检出副本运行相同入口时校验Git blob字节。不存在、路径越界、内容不匹配、收录.last-run.json或其他运行文件均退出1。

`tests/manifest.json`原SHA256为3ff95248c2089532f04d6ea0a1023c2f0aeca3bb8be9f4c8979d18b80304d05a，对应2d2900b基线加round-02未提交修订，不能归属于单一已提交Git版本。其8项旧路径保留原哈希，其中7项由round-02/code-fingerprint.json直接印证；README属于同轮说明文件，原记录保留，未伪造缺失旧源文件。现行路径由新索引校验，历史索引由显式版本和文件自身哈希校验。

历史gate manifest对browser-results/.last-run.json的引用通过history-context.json解析到history/browser-run-state.json，副本字节及SHA256与旧条目相同。原.last-run.json留在本地，被Git忽略且不进入发布索引；原manifest不修改。使用本目录验证入口解析历史别名。

旧docs内的current-source-sha256和preservation记录标识各自采样时刻，后续规约、说明和配置变化应查阅当前发布索引，不追溯覆盖旧哈希。

历史gate manifest还包含1个CPython缓存条目，在history-context.json中明确列为excluded_runtime。它不进入Git，工作树存在时核对旧哈希，隔离检出时只记录其历史非发布状态。98项旧gate条目中97项可解析验证，1项为明确保留的非发布缓存，不能宣称98项均随发布检出。

`tests/release/lesson9-v2.json`为首次验证草稿，隔离检出因旧manifest中的缓存引用失败，原样保留在本地但不纳入发布。现行入口与提交清单均使用`lesson9-v2-archive.json`。
