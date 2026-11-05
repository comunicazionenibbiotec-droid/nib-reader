const { test, expect } = require('@playwright/test');
const { expectNoHorizontalOverflow, collectPageErrors } = require('../helpers/network');

const API_BASE = 'https://nib-reader-api.onrender.com';

async function mockCamera(page) {
  await page.addInitScript(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 1280; canvas.height = 720;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#111'; ctx.fillRect(0, 0, 1280, 720);
    const stream = canvas.captureStream(30);
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => stream,
        enumerateDevices: async () => [{ kind: 'videoinput', deviceId: 'synthetic', label: 'Synthetic Camera' }]
      }
    });
  });
}

test.describe('Detector V2 isolated workflow', () => {
  test.beforeEach(async ({ page }) => { await mockCamera(page); });

  test('Home exposes the experimental Detector V2 entry without changing Reader links', async ({ page }) => {
    const errors = collectPageErrors(page);
    await page.goto('/home.html');
    await expect(page.getByRole('link', { name: /Detector V2/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Detector V2/i })).toHaveAttribute('href', 'detector-v2.html');
    await expect(page.locator('a[href*="reader-clinical-data.html"]')).toHaveCount(2);
    await expectNoHorizontalOverflow(page);
    expect(errors).toEqual([]);
  });

  test('Page is explicitly experimental and does not expose clinical persistence controls', async ({ page }) => {
    await page.goto('/detector-v2.html');
    await expect(page.getByText(/R&D.*EXPERIMENTAL/i)).toBeVisible();
    await expect(page.getByText(/Non usare Detector V2/i)).toBeVisible();
    await expect(page.getByText(/Backend V2/i)).toBeVisible();
    await expect(page.locator('text=/Salva.*record|Codice soggetto|Lotto ZenPSA Pro/i')).toHaveCount(0);
    await expectNoHorizontalOverflow(page);
  });

  test('Mask contains transparent A/B/C windows without visible letter labels', async ({ page }) => {
    await page.goto('/detector-v2.html');
    const maskResponse = await page.request.get('/assets/detector-v2-mask.svg');
    expect(maskResponse.ok()).toBeTruthy();
    const svg = await maskResponse.text();
    expect(svg).toContain('window-a');
    expect(svg).toContain('window-b');
    expect(svg).toContain('window-c');
    expect(svg).not.toMatch(/>\s*[ABC]\s*<\/text>/);
  });

  test('Camera starts and local capture becomes available', async ({ page }) => {
    await page.goto('/detector-v2.html');
    await page.getByRole('button', { name: /Avvia fotocamera/i }).click();
    await expect(page.locator('#metricCamera')).toHaveText('Attiva');
    await expect(page.locator('#captureImage')).toBeEnabled();
    await expect(page.locator('#cameraPlaceholder')).toHaveClass(/hidden/);
  });

  test('Backend health route is online and non-clinical', async ({ request }) => {
    const response = await request.get(`${API_BASE}/detector-v2/health`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBe('online');
    expect(body.persistence).toBe(false);
    expect(body.clinical).toBe(false);
  });

  test('A successful mocked analysis renders canonical crop and metrics', async ({ page }) => {
    await page.route(`${API_BASE}/detector-v2/health`, route => route.fulfill({ json: { status: 'online', persistence: false, clinical: false } }));
    await page.route(`${API_BASE}/detector-v2/analyze`, route => route.fulfill({
      json: {
        ok: true, persistence: false, used_for_clinical_result: false,
        detector_v2: {
          detected: true, geometry_score: 0.91, outer_geometry_score: 0.95, internal_geometry_score: 0.82,
          rotation_deg: 0.7, canonical: { width: 1200, height: 2340 },
          source_quad: { aspect_ratio: 1.95, vertical_stretch_ratio: 1.0 },
          canonical_preview: 'data:image/svg+xml;base64,' + Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="195"><rect width="100" height="195" fill="white"/></svg>').toString('base64'),
          windows: {
            A: { regional_quality: { valid: true, glare_fraction: 0.001, focus_laplacian: 120 } },
            B: { regional_quality: { valid: true, glare_fraction: 0.002, focus_laplacian: 110 } },
            C: { regional_quality: { valid: true, glare_fraction: 0.0, focus_laplacian: 140 } }
          }
        }
      }
    }));
    await page.goto('/detector-v2.html');
    await page.getByRole('button', { name: /Avvia fotocamera/i }).click();
    await page.getByRole('button', { name: /Acquisisci immagine/i }).click();
    await expect(page.locator('#backendResults')).not.toHaveClass(/hidden/);
    await expect(page.locator('#resultDetected')).toHaveText('RILEVATA');
    await expect(page.locator('#resultCanonical')).toHaveText('1200 × 2340');
    await expect(page.locator('#resultStretch')).toHaveText('1.0000×');
    await expect(page.locator('#canonicalPreview')).not.toHaveClass(/hidden/);
  });

  test('API 404 is handled without losing the locally captured image', async ({ page }) => {
    await page.route(`${API_BASE}/detector-v2/analyze`, route => route.fulfill({ status: 404, json: { detail: 'Not Found' } }));
    await page.goto('/detector-v2.html');
    await page.getByRole('button', { name: /Avvia fotocamera/i }).click();
    await page.getByRole('button', { name: /Acquisisci immagine/i }).click();
    await expect(page.locator('#capturePreview')).toBeVisible();
    await expect(page.locator('#metricBackend')).toHaveText('ERRORE');
    await expect(page.locator('#canonicalPlaceholder')).toContainText(/404|non disponibile/i);
  });
});
