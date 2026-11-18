# XSS 列表页源码

- 执行时间：2026-11-17
- 页面：`/materials`
- 方式：登录后上传该标题再打开列表
- 判定：页面源码包含转义后的标题，不包含原始 `<script>` 文本，也没有弹出对话框。

源码摘录：

```html
/button><button type="button">提问</button></div></div><div class="cards list"><button type="button" class="card"><strong>&lt;script&gt;alert(1).md</strong><time datetime="2026-11-18T09:1
```
