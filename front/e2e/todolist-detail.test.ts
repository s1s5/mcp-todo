import { expect, test } from '@playwright/test';

test.describe('TodoList Detail Page', () => {
	test('should display loading then todo list details', async ({ page }) => {
		// Mock responses with data
		await page.route('/api/todolists/1', async (route) => {
			await route.fulfill({
				json: {
					id: 1,
					name: 'Test List',
					workdir: '/home/user/test',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		await page.route('/api/todos/?todolist=1', async (route) => {
			await route.fulfill({
				json: [
					{
						id: 1,
						todolist: 1,
						agent: 1,
						agent_name: 'Test Agent',
						prompt: 'Test prompt',
						branch_name: 'feature/test',
						status: 'waiting',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-02T00:00:00Z'
					}
				]
			});
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Verify loading indicator is shown
		const loading = page.locator('#loading-indicator');
		await expect(loading).toBeVisible();
		await expect(loading).toHaveText('Loading...');

		// Wait for loading to complete
		await expect(loading).not.toBeVisible();

		// Verify TodoList information is displayed
		await expect(page.locator('text=Test List')).toBeVisible();
		await expect(page.locator('text=/home/user/test')).toBeVisible();

		// Verify related todos table is displayed
		const table = page.locator('table');
		await expect(table).toBeVisible();
		await expect(table).toContainText('Test Agent');
		await expect(table).toContainText('Test prompt');
		await expect(table).toContainText('feature/test');
		await expect(table).toContainText('waiting');
	});

	test('should navigate to update page on update link click', async ({ page }) => {
		// Mock responses
		await page.route('/api/todolists/1', async (route) => {
			await route.fulfill({
				json: {
					id: 1,
					name: 'Test List',
					workdir: '/home/user/test',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		await page.route('/api/todos/?todolist=1', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for loading to complete
		const loading = page.locator('#loading-indicator');
		await expect(loading).not.toBeVisible();

		// Click update link
		const updateLink = page.locator('#update-link');
		await expect(updateLink).toBeVisible();
		await updateLink.click();

		// Verify navigation to update page
		await expect(page).toHaveURL('/todolist/1/update');
	});

	test('should navigate to delete page on delete link click', async ({ page }) => {
		// Mock responses
		await page.route('/api/todolists/1', async (route) => {
			await route.fulfill({
				json: {
					id: 1,
					name: 'Test List',
					workdir: '/home/user/test',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		await page.route('/api/todos/?todolist=1', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for loading to complete
		const loading = page.locator('#loading-indicator');
		await expect(loading).not.toBeVisible();

		// Click delete link
		const deleteLink = page.locator('#delete-link');
		await expect(deleteLink).toBeVisible();
		await deleteLink.click();

		// Verify navigation to delete page
		await expect(page).toHaveURL('/todolist/1/delete');
	});

	test('should refresh data on refresh button click', async ({ page }) => {
		let requestCount = 0;

		// Mock responses that track request count
		await page.route('/api/todolists/1', async (route) => {
			requestCount++;
			if (requestCount === 1) {
				await route.fulfill({
					json: {
						id: 1,
						name: 'Initial List',
						workdir: '/home/user/test',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-02T00:00:00Z'
					}
				});
			} else {
				await route.fulfill({
					json: {
						id: 1,
						name: 'Refreshed List',
						workdir: '/home/user/refreshed',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-03T00:00:00Z'
					}
				});
			}
		});

		await page.route('/api/todos/?todolist=1', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for initial load to complete
		const loading = page.locator('#loading-indicator');
		await expect(loading).not.toBeVisible();

		// Verify initial data is displayed
		await expect(page.locator('text=Initial List')).toBeVisible();

		// Click refresh button
		const refreshButton = page.locator('#refresh-button');
		await expect(refreshButton).toBeVisible();
		await refreshButton.click();

		// Wait for loading indicator to appear and disappear
		await expect(loading).toBeVisible();
		await expect(loading).not.toBeVisible();

		// Verify updated data is displayed
		await expect(page.locator('text=Refreshed List')).toBeVisible();
	});

	test('should take snapshot after page is stable', async ({ page }) => {
		// Mock responses with data
		await page.route('/api/todolists/1', async (route) => {
			await route.fulfill({
				json: {
					id: 1,
					name: 'Snapshot Test List',
					workdir: '/home/user/snapshot',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		await page.route('/api/todos/?todolist=1', async (route) => {
			await route.fulfill({
				json: [
					{
						id: 1,
						todolist: 1,
						agent: 1,
						agent_name: 'Test Agent',
						prompt: 'Test prompt',
						branch_name: 'feature/test',
						status: 'waiting',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-02T00:00:00Z'
					},
					{
						id: 2,
						todolist: 1,
						agent: 2,
						agent_name: 'Another Agent',
						prompt: 'Another prompt',
						branch_name: 'feature/another',
						status: 'completed',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-02T00:00:00Z'
					}
				]
			});
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for loading to complete and content to be stable
		const loading = page.locator('#loading-indicator');
		await expect(loading).not.toBeVisible();

		// Wait for the table to be visible and stable
		const table = page.locator('table');
		await expect(table).toBeVisible();

		// Take snapshot
		await expect(page).toHaveScreenshot();
	});

	test('should display empty todos message when no todos exist', async ({ page }) => {
		// Mock responses
		await page.route('/api/todolists/1', async (route) => {
			await route.fulfill({
				json: {
					id: 1,
					name: 'Empty List',
					workdir: '/home/user/empty',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		await page.route('/api/todos/?todolist=1', async (route) => {
			await route.fulfill({ json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for loading to complete
		const loading = page.locator('#loading-indicator');
		await expect(loading).not.toBeVisible();

		// Verify empty message is displayed
		await expect(page.locator('text=No todos found for this list.')).toBeVisible();
	});
});
