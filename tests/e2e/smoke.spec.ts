import { expect, test } from '@playwright/test';

test('landing page renders the staff dropzone', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Read');
  await expect(page.getByRole('button', { name: /drop/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /record/i })).toBeVisible();
});
