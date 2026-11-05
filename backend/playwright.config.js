const { defineConfig, devices } = require('@playwright/test');

const baseURL = process.env.ZENPSA_BASE_URL || 'http://127.0.0.1:8080';

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    permissions: ['camera'],
    launchOptions: {
      args: [
        '--use-fake-device-for-media-stream',
        '--use-fake-ui-for-media-stream'
      ]
    }
  },
  projects: [
    { name: 'desktop-chrome', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 7'], viewport: { width: 412, height: 915 }, isMobile: true, hasTouch: true } },
    { name: 'mobile-375', use: { ...devices['iPhone 13 mini'], viewport: { width: 375, height: 812 } } },
    { name: 'mobile-390', use: { ...devices['iPhone 13'], viewport: { width: 390, height: 844 } } },
    { name: 'mobile-430', use: { ...devices['iPhone 14 Pro Max'], viewport: { width: 430, height: 932 } } }
  ],
  webServer: process.env.ZENPSA_USE_LOCAL_SERVER === '0' ? undefined : {
    command: process.env.ZENPSA_SERVER_COMMAND || 'python3 -m http.server 8080',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000
  }
});
