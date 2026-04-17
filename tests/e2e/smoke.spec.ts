import { expect, test } from '@playwright/test';

test('landing page renders the staff dropzone', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await expect(page.getByText(/drop a clip/i)).toBeVisible();
  await expect(page.getByText(/links expire/i)).toBeVisible();
});

test('record with camera shows on touch devices only', async ({ page, isMobile }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  const record = page.getByText(/record with camera/i);
  if (isMobile) {
    await expect(record).toBeVisible();
  } else {
    await expect(record).toBeHidden();
  }
});
