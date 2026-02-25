import { expect, test } from '@playwright/test';

test.describe('Agent List Page', () => {
	test('should display loading then empty message', async ({ page }) => {
		// Mock empty response
		await page.route('/api/agents/', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/agent/');

		// Verify loading indicator is shown
		const loading = page.locator('text=Loading...');
		await expect(loading).toBeVisible();

		// Wait for loading to complete
		await expect(loading).not.toBeVisible();

		// Verify empty message is displayed
		const emptyMessage = page.locator('text=No Agents found.');
		await expect(emptyMessage).toBeVisible();

		// Take snapshot after display is stable
		await expect(emptyMessage).toBeVisible();
		await expect(page).toHaveScreenshot();
	});

	test('should display table with data', async ({ page }) => {
		// Mock response with data
		await page.route('/api/agents/', async (route) => {
			await route.fulfill({
				json: [
					{
						id: 1,
						name: 'Test Agent',
						system_message: 'You are a helpful assistant.',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-01T00:00:00Z'
					}
				]
			});
		});

		// Navigate to the page
		await page.goto('/agent/');

		// Wait for loading to complete
		const loading = page.locator('text=Loading...');
		await expect(loading).not.toBeVisible();

		// Verify table is displayed
		const table = page.locator('table');
		await expect(table).toBeVisible();

		// Verify table contains expected data
		await expect(table).toContainText('Test Agent');
		await expect(table).toContainText('You are a helpful assistant.');

		// Take snapshot after display is stable
		await expect(table).toBeVisible();
		await expect(page).toHaveScreenshot();
	});

	test('should navigate back to home on back link click', async ({ page }) => {
		// Mock empty response
		await page.route('/api/agents/', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/agent/');

		// Wait for loading to complete
		const loading = page.locator('text=Loading...');
		await expect(loading).not.toBeVisible();

		// Click back link
		const backLink = page.locator('a:has-text("← 戻る")');
		await expect(backLink).toBeVisible();
		await backLink.click();

		// Verify navigation to home page
		await expect(page).toHaveURL('/');
	});
});
