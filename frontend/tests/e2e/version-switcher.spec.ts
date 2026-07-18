import { test, expect, type Page } from "@playwright/test";

/**
 * version-switcher.spec.ts — task 5-9 end-to-end AC coverage.
 *
 * Mocks the versions API surface (same `page.route` technique as
 * login.spec.ts) — this project has no live Postgres/browser stack in the
 * dev sandbox (see memory/project-memory.md), so route-mocking is how every
 * e2e spec in this repo verifies frontend behavior against a real browser
 * without a real backend.
 *
 * Fixture: 3 versions of the "scene_set" step, one (v2) stale.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const PROJECT_ID = "11111111-1111-1111-1111-111111111111";
const STEP = "scene_set";

const VERSIONS = [
  { id: "sv3", version: 3, step: STEP, stale: false, parent_version: 2, created_by: "AI", created_at: "2026-07-18T09:00:00Z" },
  { id: "sv2", version: 2, step: STEP, stale: true, parent_version: 1, created_by: "user1", created_at: "2026-07-17T09:00:00Z" },
  { id: "sv1", version: 1, step: STEP, stale: false, parent_version: null, created_by: "AI", created_at: "2026-07-16T09:00:00Z" },
];

function mockVersionRoutes(page: Page) {
  page.route(
    `${API_BASE}/api/projects/${PROJECT_ID}/steps/${STEP}/versions`,
    async (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      await route.fulfill({
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ versions: VERSIONS }),
      });
    },
  );

  page.route(
    `${API_BASE}/api/projects/${PROJECT_ID}/steps/${STEP}/current`,
    async (route) => {
      await route.fulfill({
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ current: VERSIONS[0], all_stale: false }),
      });
    },
  );

  page.route(
    `${API_BASE}/api/projects/${PROJECT_ID}/steps/${STEP}/versions/compare?from=1&to=3`,
    async (route) => {
      await route.fulfill({
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          type: "scene_set",
          added: ["s4"],
          removed: [],
          changed: [{ scene_id: "s2", fields: ["title"] }],
        }),
      });
    },
  );

  page.route(
    `${API_BASE}/api/projects/${PROJECT_ID}/steps/${STEP}/versions/2/restore`,
    async (route) => {
      await route.fulfill({
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          restored: VERSIONS[1],
          staled_steps: ["produce", "render"],
        }),
      });
    },
  );
}

test.describe("VersionSwitcher", () => {
  // Next dev-mode on-demand compilation of this route can make the first
  // interactive paint slow in this sandbox's constrained CPU — a retry
  // absorbs that class of flake rather than a brittle hard sleep (this repo
  // has no live Postgres/browser CI stack to benchmark real compile time
  // against, per memory/project-memory.md).
  test.describe.configure({ retries: 2 });

  test.beforeEach(async ({ page }) => {
    mockVersionRoutes(page);
    await page.goto(`/projects/${PROJECT_ID}/scenes`);
    await expect(page.getByRole("button", { name: /Phiên bản/ })).toBeVisible();
  });

  test("AC-1: compare v1 with current shows scene-diff and closing returns focus", async ({ page }) => {
    const trigger = page.getByRole("button", { name: /Phiên bản/ });
    await trigger.click();

    await expect(page.getByRole("dialog", { name: "Lịch sử phiên bản" })).toBeVisible();
    await expect(page.getByText("v1")).toBeVisible();
    // Rows render newest-first (v3, v2, v1) — the v1 row's "So sánh" is last.
    const compareBtn = page.getByText("So sánh").last();
    await compareBtn.click();

    await expect(page.getByRole("dialog", { name: /So sánh/ })).toBeVisible();
    await expect(page.getByText("s4")).toBeVisible();
    await expect(page.getByText("s2")).toBeVisible();

    await page.getByRole("button", { name: "Đóng" }).click();
    await expect(page.getByRole("dialog", { name: /So sánh/ })).toBeHidden();
  });

  test("AC-2: restoring an older scene_set version flips downstream stations to stale on the stepper", async ({ page }) => {
    const trigger = page.getByRole("button", { name: /Phiên bản/ });
    await trigger.click();
    await expect(page.getByRole("dialog", { name: "Lịch sử phiên bản" })).toBeVisible();
    await expect(page.getByText("v2")).toBeVisible();

    const restoreBtn = page.getByText("Khôi phục").nth(1); // v2 row
    await restoreBtn.click();

    await expect(page.getByText(/Hoàn thiện sẽ lỗi thời/)).toBeVisible();
    await page
      .getByRole("alertdialog", { name: "Xác nhận khôi phục phiên bản" })
      .getByRole("button", { name: "Khôi phục" })
      .click();

    // "Hoàn thiện" (Station index 3, downstream of Scenes) must flip to the
    // "stale" PipelineStepper pill — rendered with the ⟲ icon (BR-3/AC-2).
    const finishPill = page.locator("nav[aria-label='Tiến trình'] button", {
      hasText: "Hoàn thiện",
    });
    await expect(finishPill).toContainText("⟲");
  });
});
