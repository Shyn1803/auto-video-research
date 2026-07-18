import { test, expect, type Page, type Route } from "@playwright/test";

/**
 * Task 5-2 e2e — Playwright coverage for the layout change dry-run dialog
 * flow (BR-1/AC-2), per the task's Test Notes ("Playwright cho dialog dry-run").
 *
 * No auth guard exists yet on /projects/{id}/scenes (same gap 5-1 shipped
 * with — nothing to mock here), so this navigates directly. The scenes PUT
 * endpoint is mocked to a 200 no-op so the autosave debounce doesn't surface
 * a network error banner during the test (no backend runs in CI/sandbox).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function mockScenePut(page: Page) {
  page.route(`${API_BASE}/api/projects/*/scenes/*`, async (route: Route) => {
    if (route.request().method() === "PUT") {
      await route.fulfill({
        status: 200,
        headers: { "content-type": "application/json" },
        body: route.request().postData() ?? "{}",
      });
      return;
    }
    await route.continue();
  });
}

test.describe("Edit controls — layout dry-run dialog (BR-1/AC-2)", () => {
  test.beforeEach(async ({ page }) => {
    mockScenePut(page);
    await page.goto("/projects/p1/scenes");
  });

  test("AC-2: changing scene 2 (MediaText, 3 texts) to MediaFull warns about the dropped 3rd text", async ({
    page,
  }) => {
    // Scene #2 ("Ảnh+chữ", fixture id "2") is MediaText with 3 texts (t1/t2/t3).
    await page.getByText("Ảnh+chữ").click();

    const layoutSelect = page.locator("#scene-detail-layout");
    await expect(layoutSelect).toHaveValue("MediaText");

    await layoutSelect.selectOption("MediaFull");

    const dialog = page.getByRole("alertdialog", { name: "Xác nhận đổi bố cục" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("chữ 't3' sẽ bị bỏ");

    // BR-1: huỷ = nguyên trạng — layout select must not have changed.
    await dialog.getByText("Hủy").click();
    await expect(dialog).toBeHidden();
    await expect(layoutSelect).toHaveValue("MediaText");
  });

  test("BR-1: confirming the dry-run dialog commits the new layout", async ({ page }) => {
    await page.getByText("Ảnh+chữ").click();
    const layoutSelect = page.locator("#scene-detail-layout");
    await layoutSelect.selectOption("MediaFull");

    const dialog = page.getByRole("alertdialog", { name: "Xác nhận đổi bố cục" });
    await expect(dialog).toBeVisible();
    await dialog.getByText("Vẫn đổi").click();

    await expect(dialog).toBeHidden();
    await expect(layoutSelect).toHaveValue("MediaFull");
  });

  test("AC-1: editing the voice text is reflected immediately in the debug Scene JSON preview", async ({
    page,
  }) => {
    await page.getByText("Ảnh+chữ").click();

    const voiceText = page.getByLabel("Lời đọc (voice-over)");
    await voiceText.fill("Nội dung lời đọc mới cho cảnh này");

    await page.getByText("Xem Scene JSON đang chỉnh (debug)").click();
    const debugJson = page.getByTestId("scene-draft-debug");
    await expect(debugJson).toContainText("Nội dung lời đọc mới cho cảnh này");
  });

  test("BR-4: the B button wraps the selected content in ** markers, reflected in the debug preview", async ({
    page,
  }) => {
    await page.getByText("Ảnh+chữ").click();

    const content = page.getByLabel("Nội dung");
    await content.click();
    await page.keyboard.press("Control+A");
    await page.getByRole("button", { name: /in đậm/i }).click();

    await page.getByText("Xem Scene JSON đang chỉnh (debug)").click();
    await expect(page.getByTestId("scene-draft-debug")).toContainText("**Bức ảnh minh hoạ**");
  });

  test("AC-5: ArrowRight on the animation delay slider increases the value", async ({ page }) => {
    await page.getByText("Ảnh+chữ").click();

    const slider = page.getByLabel("Độ trễ (delay)");
    await slider.focus();
    await expect(slider).toHaveValue("0");
    await page.keyboard.press("ArrowRight");
    await expect(slider).toHaveValue("100");
  });
});
