// Playwright skeleton. Enable after Playwright is installed in the project.
const { test, expect } = require('@playwright/test');

test.skip('Detector V2 remains isolated and visible from Home', async ({ page }) => {
  await page.goto('/home.html');
  await expect(page.getByText('Detector V2')).toBeVisible();
  await page.getByText('Detector V2').click();
  await expect(page).toHaveURL(/detector-v2\.html/);
  await expect(page.getByText(/R&D.*EXPERIMENTAL/i)).toBeVisible();
});
