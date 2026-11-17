# XSS 列表页源码

- 执行时间：2026-11-17
- 页面：`/materials`
- 方式：Vite 页面 + 材料接口返回该标题
- 判定：页面源码包含转义后的标题，不包含可执行的 `<script>alert(1)</script>`，也没有弹出对话框。

源码摘录：

```html
/button><button type="button">提问</button></div></div><div class="cards list"><button type="button" class="card"><strong>&lt;script&gt;alert(1)&lt;/script&gt;.md</strong><time datetime="2026-11-17T0
```
