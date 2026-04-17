import { expect, test } from '@playwright/test';

test('landing page renders the staff dropzone', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await expect(page.getByText(/drop a clip/i)).toBeVisible();
  await expect(page.getByText(/record with camera/i)).toBeVisible();
  await expect(page.getByText(/links expire/i)).toBeVisible();
});
