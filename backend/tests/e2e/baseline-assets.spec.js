const { test, expect } = require('@playwright/test');
const crypto = require('crypto');

const protectedAssets = [
  '/index.html',
  '/js/camera.js',
  '/js/imageQuality.js',
  '/js/overlay.js',
  '/js/alignment.js',
  '/js/quality.js',
  '/js/roiEditor.js',
  '/js/archiveCrop.js',
  '/js/app.js'
];

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

test('Reader V1 protected assets are reachable and can be fingerprinted', async ({ request }, testInfo) => {
  const manifest = {};
  for (const path of protectedAssets) {
    const response = await request.get(path);
    expect(response.ok(), `missing protected Reader V1 asset: ${path}`).toBeTruthy();
    const body = await response.body();
    manifest[path] = { bytes: body.length, sha256: sha256(body) };
  }
  await testInfo.attach('reader-v1-baseline.json', {
    body: Buffer.from(JSON.stringify(manifest, null, 2)),
    contentType: 'application/json'
  });
});

test('Detector V2 remains in separate assets and routes', async ({ request }) => {
  for (const path of ['/detector-v2.html', '/js/detectorV2Camera.js', '/js/detectorV2Overlay.js', '/js/detectorV2Quality.js', '/js/detectorV2Api.js', '/js/detectorV2.js']) {
    const response = await request.get(path);
    expect(response.ok(), `missing Detector V2 asset: ${path}`).toBeTruthy();
  }
  const index = await (await request.get('/index.html')).text();
  expect(index).not.toMatch(/detector-v2|detectorV2/i);
});
