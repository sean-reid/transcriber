import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const fixture = resolve(here, '..', 'fixtures', 'sample.mp4');

test.describe('upload to share', () => {
  test('user uploads a clip and reaches the share page with a playable video', async ({
    page
  }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const input = page.locator('input[type="file"]').first();
    await input.setInputFiles(fixture);

    await page.waitForURL(/\/(jobs|share)\//, { timeout: 20_000 });
    await page.waitForURL(/\/share\//, { timeout: 45_000 });

    const video = page.locator('video').first();
    await expect(video).toBeVisible();
    await expect(video).toHaveAttribute('src', /\/api\/storage\/output\//);

    const download = page.getByRole('link', { name: /download mp4/i });
    await expect(download).toBeVisible();
    await expect(download).toHaveAttribute('download', '');
  });
});
