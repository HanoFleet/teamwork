# 前端工具链（第9课依赖整改）

React/ReactDOM、ReactMarkdown、路由及页面源码保持原功能。Vite 和 React 插件实际用于构建，但共同引入了尚无官方安全发布版的 picomatch 链；因此替换构建工具，而不是删除运行时能力或省略开发依赖审计。替代工具为官方 MIT 许可证的 esbuild 0.28.2，要求 Node >=18；本轮安装/审计/构建用 CI 同版 Node 24.22.2、npm 11.19.1，原 Dockerfile 的 Node22 也实际构建通过。

```text
npm ci
npm audit --audit-level=high
npm run build
npm run dev -- --host 127.0.0.1 --port 5173
npm run preview -- --host 127.0.0.1 --port 4173
```

build 保留 `tsc --noEmit`，将 TSX/JS/CSS 编译成 dist/index.html 及带内容哈希的 JS/CSS；原 Nginx Dockerfile 继续部署 dist。`assets.d.ts` 仅声明项目现有 CSS 副作用导入。`index.html` 中的主入口模板仍为 `/src/main.tsx`，构建时替换为实际产物路径。

dev/preview 的 `/api` 和 `/health` 仍转发到 `http://127.0.0.1:8080`，保留方法、请求体、Cookie 和 CSRF 头。默认只监听 loopback，未知 Host 拒绝；后端不可达返回 503，不输出内部错误。开发源码修改使用 esbuild watch + 整页刷新，不保留 Vite React Fast Refresh 的组件状态保留体验。后端仍执行全部授权检查。

工具链 HTTP 回归：仓库根目录运行 `node --test tests/regression/frontend_toolchain.test.mjs`。实际作业提交和 XSS 仍使用 `frontend/e2e/` 的原 Playwright 用例。开发/预览服务仅用于本地测试；生产继续使用原 Nginx。

依据：[esbuild JSX/CSS](https://esbuild.github.io/content-types/)、[build/watch/serve](https://esbuild.github.io/api/)。候选与最终审计、功能回归见 `reports/lesson9-20261118/retest-02/fix-round/round-02/`。
