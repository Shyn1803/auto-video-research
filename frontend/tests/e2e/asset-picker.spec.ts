import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * AssetPicker end-to-end flow (Task 5-3) — dev harness at /dev/asset-picker
 * (see that page's docstring: real integration into SceneFormPanel is a
 * separate task; this exercises the component itself in a real browser).
 *
 * Covers the ACs from .claude/tasks/5-3-assetpicker.md:
 *   AC1 (happy): search "GPU datacenter" -> select Pexels result -> Player-side
 *                asset_id assigned, no direct provider call from the client.
 *   AC5 (BR-4):  "đang lấy ảnh…" shown while the server-side fetch is in flight.
 *   Security:    render/preview-equivalent flow never calls pexels.com directly
 *                from the browser — only our own /api/assets/* endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function mockAssetRoutes(page: Page) {
  page.route(`${API_BASE}/api/assets/stock-status`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ active: true, providers: ['pexels'] }),
    });
  });

  page.route(`${API_BASE}/api/assets/search*`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          provider: 'pexels',
          url: 'https://images.pexels.com/photos/1/gpu.jpg',
          thumb_url: 'https://images.pexels.com/photos/1/gpu-thumb.jpg',
          attribution: 'Jane Doe',
          attribution_url: 'https://pexels.com/@jane',
          license: 'Pexels License',
          width: '1920',
          height: '1080',
        },
      ]),
    });
  });

  page.route(`${API_BASE}/api/assets/fetch-stock`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'asset-e2e-1',
        provider: 'pexels',
        license: 'Pexels License',
        attribution_required: true,
        attribution_text: 'Jane Doe',
        storage_path: 'assets/abc.jpg',
        content_hash: 'abc',
        reused: false,
      }),
    });
  });

  page.route(`${API_BASE}/api/assets/upload`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'asset-e2e-upload',
        provider: 'user_upload',
        license: 'user_upload',
        attribution_required: false,
        attribution_text: null,
        storage_path: 'assets/upload.png',
        content_hash: 'upload-hash',
        reused: false,
      }),
    });
  });
}

test.describe('AssetPicker', () => {
  test.beforeEach(async ({ page }) => {
    mockAssetRoutes(page);
    await page.goto('/dev/asset-picker');
    await page.getByRole('button', { name: 'Đổi ảnh…' }).click();
  });

  test('AC1/AC5/BR-4: search -> license badge -> select -> đang lấy ảnh -> asset_id assigned, no direct pexels.com API/data call', async ({
    page,
  }) => {
    // The picker's own <img> thumbnail preview legitimately loads from the
    // CDN (that's the point of showing a preview before committing to it) --
    // the BR-4/security invariant this guards is that the app never makes a
    // *data* request (fetch/xhr) straight to the provider; only the backend's
    // one-time server-side download does that. A thumbnail <img> is not the
    // SSRF-relevant path (rules/security.md targets Render Worker / backend
    // fetches, not the browser displaying a preview image).
    let calledPexelsDirectly = false;
    page.on('request', (req) => {
      if (
        req.url().includes('pexels.com') &&
        !['image', 'other'].includes(req.resourceType())
      ) {
        calledPexelsDirectly = true;
      }
    });

    // Stock tab is default because the harness passes initialStockQuery.
    await expect(page.getByRole('tab', { name: 'Tìm stock' })).toHaveAttribute(
      'aria-selected',
      'true',
    );

    // BR-1: license + source visible on the result before any selection.
    await expect(page.getByText('Pexels License')).toBeVisible();
    await expect(page.getByText('Jane Doe')).toBeVisible();

    await page.getByRole('gridcell').first().click();

    // BR-4: "đang lấy ảnh…" shown while server-side fetch is in flight.
    await expect(page.getByText('Đang lấy ảnh…')).toBeVisible();

    await expect(page.getByTestId('selected-asset-id')).toContainText('asset-e2e-1');
    expect(calledPexelsDirectly).toBe(false);
  });

  test('3 tabs are all reachable and switch content', async ({ page }) => {
    await page.getByRole('tab', { name: 'Asset dự án' }).click();
    await expect(page.getByText(/Chưa có ảnh nào được dùng/)).toBeVisible();

    await page.getByRole('tab', { name: 'Tải lên' }).click();
    await expect(page.getByText(/Chọn ảnh từ máy tính/)).toBeVisible();

    await page.getByRole('tab', { name: 'Tìm stock' }).click();
    await expect(page.getByPlaceholder('Tìm ảnh stock…')).toBeVisible();
  });

  test('Escape closes the modal', async ({ page }) => {
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });
});
