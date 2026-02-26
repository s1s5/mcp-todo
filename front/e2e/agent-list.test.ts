import { expect, test } from '@playwright/test';

test.describe('Agent List Page', () => {
	test('should display table with data', async ({ page }) => {
		// Mock response with data
		await page.route('/api/agents/', async (route) => {
			await route.fulfill({
				json: [
					{
						id: 1,
						name: 'Test Agent',
						system_message: 'You are a helpful assistant.',
						created_at: '2024-01-01T09:00:00Z',
						updated_at: '2024-01-01T09:00:00Z'
					}
				],
				delay: 100
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
		const html = await page.locator('div.p-6.max-w-4xl.mx-auto').innerHTML();
		expect(html).toMatchSnapshot('agent-list-data.html');
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
