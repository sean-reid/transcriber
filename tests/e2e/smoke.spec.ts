import { expect, test } from '@playwright/test';

test('landing page responds', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'transcriber' })).toBeVisible();
});
