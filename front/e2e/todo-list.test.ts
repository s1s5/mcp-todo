import { expect, test } from '@playwright/test';

test.describe('Todo List Page', () => {
	test('should display loading then table or empty message', async ({ page }) => {
		// Mock response with data - use wildcard to match query params
		// Add delay to allow loading indicator to be visible
		await page.route('**/api/todos/**', async (route) => {
			await new Promise(resolve => setTimeout(resolve, 200));
			await route.fulfill({
				status: 200,
				json: {
					count: 1,
					next: null,
					previous: null,
					results: [
						{
							id: 1,
							todo_list: 1,
							agent: null,
							agent_name: null,
							ref_files: [],
							edit_files: [],
							todo_list_name: 'Test List',
							workdir: '/home/user/test',
							prompt: 'Test prompt',
							title: 'Test Todo',
							context: '',
							status: 'waiting',
							output: null,
							validation_command: null,
							timeout: 3600,
							created_at: '2024-01-01T00:00:00Z',
							updated_at: '2024-01-01T00:00:00Z',
							branch_name: 'test-branch'
						}
					]
				}
			});
		});

		// Navigate to the page
		await page.goto('/todo/');

		// Verify loading indicator is shown
		const loading = page.locator('#loading');
		await expect(loading).toBeVisible();
		await expect(loading).toHaveText('Loading...');

		// Wait for loading to complete
		await expect(loading).not.toBeVisible();

		// Verify table is displayed
		const table = page.locator('#todo-table');
		await expect(table).toBeVisible();

		// Verify table contains expected data
		await expect(table).toContainText('Test Todo');
		await expect(table).toContainText('waiting');
		await expect(table).toContainText('test-branch');
	});

	test('should display loading then empty message when no todos', async ({ page }) => {
		// Mock empty response - use wildcard to match query params
		// Add delay to allow loading indicator to be visible
		await page.route('**/api/todos/**', async (route) => {
			await new Promise(resolve => setTimeout(resolve, 200));
			await route.fulfill({
				status: 200,
				json: {
					count: 0,
					next: null,
					previous: null,
					results: []
				}
			});
		});

		// Navigate to the page
		await page.goto('/todo/');

		// Verify loading indicator is shown
		const loading = page.locator('#loading');
		await expect(loading).toBeVisible();
		await expect(loading).toHaveText('Loading...');

		// Wait for loading to complete
		await expect(loading).not.toBeVisible();

		// Verify empty message is displayed
		const noTodos = page.locator('#no-todos');
		await expect(noTodos).toBeVisible();
		await expect(noTodos).toHaveText('No Todos found.');
	});

	test('should navigate back to home on back link click', async ({ page }) => {
		// Mock empty response - use wildcard to match query params
		await page.route('**/api/todos/**', async (route) => {
			await route.fulfill({
				json: {
					count: 0,
					next: null,
					previous: null,
					results: []
				}
			});
		});

		// Navigate to the page
		await page.goto('/todo/');

		// Wait for loading to complete
		const loading = page.locator('#loading');
		await expect(loading).not.toBeVisible();

		// Click back link
		const backLink = page.locator('#back-link');
		await expect(backLink).toBeVisible();
		await backLink.click();

		// Verify navigation to home page
		await expect(page).toHaveURL('/');
	});

	test('should take snapshot after page is stabilized', async ({ page }) => {
		// Mock response with data - use wildcard to match query params
		await page.route('**/api/todos/**', async (route) => {
			await route.fulfill({
				json: {
					count: 1,
					next: null,
					previous: null,
					results: [
						{
							id: 1,
							todo_list: 1,
							agent: null,
							agent_name: null,
							ref_files: [],
							edit_files: [],
							todo_list_name: 'Test List',
							workdir: '/home/user/test',
							prompt: 'Test prompt',
							title: 'Test Todo',
							context: '',
							status: 'waiting',
							output: null,
							validation_command: null,
							timeout: 3600,
							created_at: '2024-01-01T00:00:00Z',
							updated_at: '2024-01-01T00:00:00Z',
							branch_name: 'test-branch'
						}
					]
				}
			});
		});

		// Navigate to the page
		await page.goto('/todo/');

		// Wait for loading to complete
		const table = page.locator('#todo-table');
		await expect(table).toBeVisible();

		// Take snapshot after page is stabilized (using main element's innerHTML)
		await expect(await page.locator('main').innerHTML()).toMatchSnapshot('todo-list.html');
	});
});
