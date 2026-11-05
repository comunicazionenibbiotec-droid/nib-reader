const { test, expect } = require('@playwright/test');
const { expectNoHorizontalOverflow, collectPageErrors } = require('../helpers/network');

async function prepareReader(page) {
  await page.addInitScript(() => {
    sessionStorage.setItem('reader_mode', 'research');
    localStorage.setItem('reader_mode', 'research');
    const canvas = document.createElement('canvas'); canvas.width = 1280; canvas.height = 720;
    canvas.getContext('2d').fillRect(0, 0, 1280, 720);
    const stream = canvas.captureStream(30);
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: async () => stream } });
  });
}

test.describe('Reader V1 protected regression checks', () => {
  test.beforeEach(async ({ page }) => { await prepareReader(page); });

  test('Reader V1 page loads without importing Detector V2 modules', async ({ page }) => {
    const requested = [];
    page.on('request', request => requested.push(request.url()));
    await page.goto('/index.html');
    const detectorV2Requests = requested.filter(url => /detectorV2|detector-v2/i.test(url));
    expect(detectorV2Requests).toEqual([]);
    await expect(page.locator('body')).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test('Reader V1 keeps the original analyze route and never calls Detector V2', async ({ page }) => {
    let v1Analyze = 0, v2Analyze = 0;
    await page.route('**/detector-v2/analyze', route => { v2Analyze++; return route.abort(); });
    await page.route('**/analyze', route => { v1Analyze++; return route.fulfill({ json: { ok: false, error: 'synthetic_test_stop' } }); });
    await page.goto('/index.html');
    expect(v2Analyze).toBe(0);
    // The test intentionally does not force a clinical capture. It proves page load creates no V2 dependency.
    expect(v1Analyze).toBe(0);
  });

  test('Protected Reader V1 scripts remain referenced by index.html', async ({ page }) => {
    const response = await page.request.get('/index.html');
    expect(response.ok()).toBeTruthy();
    const html = await response.text();
    for (const script of ['camera.js', 'imageQuality.js', 'overlay.js', 'alignment.js', 'quality.js', 'roiEditor.js', 'archiveCrop.js', 'app.js']) {
      expect(html, `missing protected script ${script}`).toContain(script);
    }
    expect(html).not.toContain('detectorV2');
  });

  test('Reader V1 keeps cassette mask asset reference', async ({ page }) => {
    const response = await page.request.get('/index.html');
    const html = await response.text();
    expect(html).toMatch(/test-outline\.svg/);
  });

  test('Reader V1 has no critical page errors on desktop and mobile', async ({ page }) => {
    const errors = collectPageErrors(page);
    await page.goto('/index.html');
    await page.waitForTimeout(1500);
    const filtered = errors.filter(error => !/camera|permission|notallowed|device/i.test(error));
    expect(filtered).toEqual([]);
  });
});
