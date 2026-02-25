import { expect, test } from '@playwright/test';

test.describe('Extension List Page', () => {
	test('should display loading then table or empty message', async ({ page }) => {
		// Mock response with data
		await page.route('/api/extensions/', async (route) => {
			await route.fulfill({
				json: [
					{
						id: 1,
						name: 'Test Extension',
						type: 'command',
						cmd: 'echo "test"',
						args: [],
						envs: {},
						timeout: 60,
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-01T00:00:00Z'
					}
				]
			});
		});

		// Navigate to the page
		await page.goto('/extension/');

		// Verify loading indicator is shown
		const loading = page.locator('#loading-indicator');
		await expect(loading).toBeVisible();
		await expect(loading).toHaveText('Loading...');

		// Wait for loading to complete
		await expect(loading).not.toBeVisible();

		// Verify table is displayed
		const table = page.locator('#extensions-table');
		await expect(table).toBeVisible();

		// Verify table contains expected data
		await expect(table).toContainText('Test Extension');
		await expect(table).toContainText('command');
		await expect(table).toContainText('60s');
	});

	test('should display loading then empty message when no extensions', async ({ page }) => {
		// Mock empty response
		await page.route('/api/extensions/', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/extension/');

		// Verify loading indicator is shown
		const loading = page.locator('#loading-indicator');
		await expect(loading).toBeVisible();
		await expect(loading).toHaveText('Loading...');

		// Wait for loading to complete
		await expect(loading).not.toBeVisible();

		// Verify empty message is displayed
		const noExtensions = page.locator('#no-extensions');
		await expect(noExtensions).toBeVisible();
		await expect(noExtensions).toHaveText('No Extensions found.');
	});

	test('should navigate back to home on back link click', async ({ page }) => {
		// Mock empty response
		await page.route('/api/extensions/', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/extension/');

		// Wait for loading to complete
		const loading = page.locator('#loading-indicator');
		await expect(loading).not.toBeVisible();

		// Click back link
		const backLink = page.locator('#back-link');
		await expect(backLink).toBeVisible();
		await backLink.click();

		// Verify navigation to home page
		await expect(page).toHaveURL('/');
	});

	test('should take snapshot after page is stabilized', async ({ page }) => {
		// Mock response with data
		await page.route('/api/extensions/', async (route) => {
			await route.fulfill({
				json: [
					{
						id: 1,
						name: 'Test Extension',
						type: 'command',
						cmd: 'echo "test"',
						args: [],
						envs: {},
						timeout: 60,
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-01T00:00:00Z'
					}
				]
			});
		});

		// Navigate to the page
		await page.goto('/extension/');

		// Wait for loading to complete
		const table = page.locator('#extensions-table');
		await expect(table).toBeVisible();

		// Take snapshot after page is stabilized
		await expect(page).toHaveScreenshot();
	});
});
