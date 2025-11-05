import { test, expect } from '@playwright/test';
test('dashboard mostra 4 cards e valores', async ({ page }) => {
  await page.goto('http://localhost:5173');
  await expect(page.getByText('RPM')).toBeVisible();
  await expect(page.getByText('Feed (mm/min)')).toBeVisible();
  await expect(page.getByText('Status')).toBeVisible();
  await expect(page.getByText('Tempo usinagem (s)')).toBeVisible();
  // aguarda primeira amostra
  await page.waitForTimeout(2500);
  const rpm = await page.locator('text=RPM').locator('xpath=..').textContent();
  expect(rpm || '').not.toContain('—');
});
