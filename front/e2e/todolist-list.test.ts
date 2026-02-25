import { expect, test } from '@playwright/test';

test.describe('TodoList List Page', () => {
	test('should display loading then empty message', async ({ page }) => {
		// Mock empty response
		await page.route('/api/todolists/', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/');

		// Verify loading indicator is shown
		const loading = page.locator('#loading-indicator');
		await expect(loading).toBeVisible();
		await expect(loading).toHaveText('Loading...');

		// Wait for loading to complete
		await expect(loading).not.toBeVisible();

		// Verify empty message is displayed
		const emptyMessage = page.locator('#empty-message');
		await expect(emptyMessage).toBeVisible();
		await expect(emptyMessage).toHaveText('No TodoLists found.');
	});

	test('should display table with data', async ({ page }) => {
		// Mock response with data
		await page.route('/api/todolists/', async (route) => {
			await route.fulfill({
				json: [
					{
						id: 1,
						name: 'Test List',
						workdir: '/home/user/test',
						created_at: '2024-01-01T00:00:00Z'
					}
				]
			});
		});

		// Navigate to the page
		await page.goto('/todolist/');

		// Wait for loading to complete
		const loading = page.locator('#loading-indicator');
		await expect(loading).not.toBeVisible();

		// Verify table is displayed
		const table = page.locator('#todolist-table');
		await expect(table).toBeVisible();

		// Verify table contains expected data
		await expect(page.locator('table')).toContainText('Test List');
		await expect(page.locator('table')).toContainText('/home/user/test');
	});

	test('should refresh data on button click', async ({ page }) => {
		let requestCount = 0;

		// Mock response that tracks request count
		await page.route('/api/todolists/', async (route) => {
			requestCount++;
			if (requestCount === 1) {
				await route.fulfill({ json: [] });
			} else {
				await route.fulfill({
					json: [
						{
							id: 1,
							name: 'Refreshed List',
							workdir: '/home/user/refreshed',
							created_at: '2024-01-02T00:00:00Z'
						}
					]
				});
			}
		});

		// Navigate to the page
		await page.goto('/todolist/');

		// Wait for initial load to complete
		const loading = page.locator('#loading-indicator');
		await expect(loading).not.toBeVisible();

		// Click refresh button
		const refreshButton = page.locator('#refresh-button');
		await expect(refreshButton).toBeVisible();
		await refreshButton.click();

		// Wait for loading indicator to appear and disappear
		await expect(loading).toBeVisible();
		await expect(loading).not.toBeVisible();

		// Verify updated data is displayed
		const table = page.locator('#todolist-table');
		await expect(table).toBeVisible();
		await expect(page.locator('table')).toContainText('Refreshed List');
	});

	test('should navigate back to home on back link click', async ({ page }) => {
		// Mock empty response
		await page.route('/api/todolists/', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/');

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
});
