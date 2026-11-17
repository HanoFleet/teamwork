import { expect, test } from "@playwright/test";

test("学生从 /assignments 提交并轮询到 succeeded", async ({ page }) => {
  const password = process.env.E2E_STUDENT_PASSWORD ?? process.env.SEED_STUDENT_A_PASSWORD;
  test.skip(!password, "缺少 E2E_STUDENT_PASSWORD/SEED_STUDENT_A_PASSWORD");

  const login = await page.request.post("/api/login", {
    data: { username: "student_a1", password },
  });
  expect(login.ok()).toBeTruthy();

  await page.goto("/assignments");
  await expect(page.getByRole("heading", { name: /班作业/ })).toBeVisible();
  const select = page.getByLabel("已发布作业");
  await expect(select).toBeVisible();
  await select.selectOption({ index: 1 });
  await page.getByLabel("作答正文").fill(`函数单调性 证明 实验 结论 playwright-${Date.now()}`);
  await page.getByRole("button", { name: "提交并批改" }).click();

  await expect(page.getByText("批改完成")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/分数：/)).toBeVisible();
});
