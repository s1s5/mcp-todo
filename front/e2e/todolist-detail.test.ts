import { expect, test } from '@playwright/test';

test.describe('TodoList Detail Page', () => {
	test('should display todo list details', async ({ page }) => {
		// Mock todolist detail API
		await page.route('**/api/todolists/1/', async (route) => {
			await route.fulfill({
				status: 200,
				json: {
					id: 1,
					name: 'Test List',
					workdir: '/home/user/test',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		// Mock todos API with query params
		await page.route('**/api/todos/**', async (route) => {
			const url = route.request().url();
			if (url.includes('todo_list=1')) {
				await route.fulfill({
					status: 200,
					json: [
						{
							id: 1,
							todo_list: 1,
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
			} else {
				await route.fulfill({ status: 200, json: [] });
			}
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for loading to complete - use OR selector
		await expect(page.locator('.loading')).not.toBeVisible({ timeout: 10000 }).catch(() => {});
		await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 10000 }).catch(() => {});

		// Verify TodoList information is displayed
		await expect(page.locator('text=Test List')).toBeVisible();
		await expect(page.getByText('/home/user/test')).toBeVisible();

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
		await page.route('**/api/todolists/1/', async (route) => {
			await route.fulfill({
				status: 200,
				json: {
					id: 1,
					name: 'Test List',
					workdir: '/home/user/test',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		await page.route('**/api/todos/**', async (route) => {
			await route.fulfill({ status: 200, json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for loading to complete
		await expect(page.locator('.loading')).not.toBeVisible({ timeout: 10000 }).catch(() => {});
		await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 10000 }).catch(() => {});

		// Click update link
		const updateLink = page.locator('#update-link');
		await expect(updateLink).toBeVisible();
		await updateLink.click();

		// Verify navigation to update page
		await expect(page).toHaveURL(/\/todolist\/1\/update\/?/);
	});

	test('should navigate to delete page on delete link click', async ({ page }) => {
		// Mock responses
		await page.route('**/api/todolists/1/', async (route) => {
			await route.fulfill({
				status: 200,
				json: {
					id: 1,
					name: 'Test List',
					workdir: '/home/user/test',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		await page.route('**/api/todos/**', async (route) => {
			await route.fulfill({ status: 200, json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for loading to complete
		await expect(page.locator('.loading')).not.toBeVisible({ timeout: 10000 }).catch(() => {});
		await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 10000 }).catch(() => {});

		// Click delete link
		const deleteLink = page.locator('#delete-link');
		await expect(deleteLink).toBeVisible();
		await deleteLink.click();

		// Verify navigation to delete page
		await expect(page).toHaveURL(/\/todolist\/1\/delete\/?/);
	});

	test('should refresh data on refresh button click', async ({ page }) => {
		let requestCount = 0;

		// Mock responses that track request count
		await page.route('**/api/todolists/1/', async (route) => {
			requestCount++;
			if (requestCount === 1) {
				await route.fulfill({
					status: 200,
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
					status: 200,
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

		await page.route('**/api/todos/**', async (route) => {
			await route.fulfill({ status: 200, json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for initial load to complete
		await expect(page.locator('.loading')).not.toBeVisible({ timeout: 10000 }).catch(() => {});
		await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 10000 }).catch(() => {});

		// Verify initial data is displayed
		await expect(page.locator('text=Initial List')).toBeVisible();

		// Click refresh button
		const refreshButton = page.locator('#refresh-button');
		await expect(refreshButton).toBeVisible();
		await refreshButton.click();

		// Wait for loading indicator to appear and disappear
		await expect(page.locator('.loading')).toBeVisible().catch(() => {});
		await expect(page.getByText('Loading...')).toBeVisible().catch(() => {});
		await expect(page.locator('.loading')).not.toBeVisible({ timeout: 10000 }).catch(() => {});
		await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 10000 }).catch(() => {});

		// Verify updated data is displayed
		await expect(page.locator('text=Refreshed List')).toBeVisible();
	});

	test('should display empty todos message when no todos exist', async ({ page }) => {
		// Mock responses
		await page.route('**/api/todolists/1/', async (route) => {
			await route.fulfill({
				status: 200,
				json: {
					id: 1,
					name: 'Empty List',
					workdir: '/home/user/empty',
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-02T00:00:00Z'
				}
			});
		});

		await page.route('**/api/todos/**', async (route) => {
			await route.fulfill({ status: 200, json: [] });
		});

		// Navigate to the page
		await page.goto('/todolist/1');

		// Wait for loading to complete
		await expect(page.locator('.loading')).not.toBeVisible({ timeout: 10000 }).catch(() => {});
		await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 10000 }).catch(() => {});

		// Verify empty message is displayed
		await expect(page.getByText('No todos found for this list.')).toBeVisible();
	});
});
