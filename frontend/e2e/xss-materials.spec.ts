import { expect, test } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// DisplayTitle 用 path.Base，闭合标签里的 / 会把标题切成 script>.md。
const title = "<script>alert(1).md";
const escaped = "&lt;script&gt;alert(1).md";
const reportPath = resolve(dirname(fileURLToPath(import.meta.url)), "../../reports/xss-page-source.md");

test("材料列表页源码转义脚本标题", async ({ page }) => {
  page.on("dialog", async (dialog) => {
    await dialog.dismiss();
    throw new Error("列表页执行了脚本对话框");
  });

  if (process.env.E2E_XSS_MOCK === "1") {
    await page.route("**/api/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          username: "teacher_a",
          role: "teacher",
          class_id: 1,
          class_name: "A",
          csrf_token: "csrf-page-source",
        }),
      }),
    );
    await page.route("**/api/materials", (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          materials: [{ id: 1, title, created_at: "2026-11-17T07:00:00Z" }],
        }),
      });
    });
    await page.route("**/api/materials/1", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          title,
          class_id: 1,
          created_at: "2026-11-17T07:00:00Z",
          body: "# xss\n\n<script>alert(1)</script>\n",
        }),
      }),
    );
  } else {
    const password = process.env.E2E_TEACHER_PASSWORD ?? process.env.SEED_TEACHER_PASSWORD;
    test.skip(!password, "缺少 E2E_TEACHER_PASSWORD/SEED_TEACHER_PASSWORD");
    const login = await page.request.post("/api/login", {
      data: { username: "teacher_a", password },
    });
    expect(login.ok()).toBeTruthy();
    const csrf = String((await login.json()).csrf_token ?? "");
    const uploaded = await page.request.post("/api/materials", {
      multipart: {
        file: {
          name: title,
          mimeType: "text/markdown",
          buffer: Buffer.from("# xss\n\n<script>alert(1)</script>\n"),
        },
      },
      headers: csrf ? { "X-CSRF-Token": csrf } : undefined,
    });
    expect(uploaded.status()).toBe(201);
  }

  await page.goto("/materials");
  await expect(page.getByText(title, { exact: true }).first()).toBeVisible();
  const html = await page.content();
  expect(html).not.toContain(title);
  expect(html).not.toContain("<script>alert(1)</script>");
  expect(html).toContain(escaped);
  const at = html.indexOf(escaped);
  const excerpt = html.slice(Math.max(0, at - 120), at + escaped.length + 40).replaceAll("`", "'");
  const mode = process.env.E2E_XSS_MOCK === "1" ? "Vite 页面 + 材料接口返回该标题" : "登录后上传该标题再打开列表";
  writeFileSync(
    reportPath,
    [
      "# XSS 列表页源码",
      "",
      "- 执行时间：2026-11-17",
      "- 页面：`/materials`",
      `- 方式：${mode}`,
      "- 判定：页面源码包含转义后的标题，不包含原始 `<script>` 文本，也没有弹出对话框。",
      "",
      "源码摘录：",
      "",
      "```html",
      excerpt,
      "```",
      "",
    ].join("\n"),
    "utf8",
  );
});
