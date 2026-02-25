import { expect, test } from '@playwright/test';

test.describe('Todo Update Page', () => {
	const todoId = '1';

	const mockTodo = {
		id: 1,
		todo_list: 1,
		todo_list_name: 'Test TodoList',
		agent: 1,
		agent_name: 'Test Agent',
		prompt: 'Original prompt text',
		status: 'waiting',
		branch_name: 'test-branch',
		created_at: '2024-01-01T00:00:00Z',
		updated_at: '2024-01-01T00:00:00Z'
	};

	const mockTodoLists = [
		{ id: 1, workdir: '/home/user/project1' },
		{ id: 2, workdir: '/home/user/project2' }
	];

	const mockAgents = [
		{ id: 1, name: 'Test Agent' },
		{ id: 2, name: 'Another Agent' }
	];

	test.beforeEach(async ({ page }) => {
		// Mock Todo fetch
		await page.route(`/api/todos/${todoId}/`, async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockTodo)
				});
			}
		});

		// Mock TodoList fetch
		await page.route('/api/todolists/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockTodoLists)
			});
		});

		// Mock Agent fetch
		await page.route('/api/agents/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAgents)
			});
		});
	});

	test('1. ページ遷移: /todo/1/update へアクセス', async ({ page }) => {
		await page.goto(`/todo/${todoId}/update`);
		await expect(page.locator('h1')).toHaveText('Todo更新');
	});

	test('2. 初期値表示: 現在の値が入力済みで表示ること', async ({ page }) => {
		await page.goto(`/todo/${todoId}/update`);

		// Wait for form to be loaded
		const promptInput = page.locator('#prompt');
		const statusSelect = page.locator('#status');
		const todoListSelect = page.locator('#todo_list');
		const branchInput = page.locator('#branch');
		const agentSelect = page.locator('#agent');

		await expect(promptInput).toBeVisible();
		await expect(statusSelect).toBeVisible();
		await expect(todoListSelect).toBeVisible();
		await expect(branchInput).toBeVisible();
		await expect(agentSelect).toBeVisible();

		// Check initial values
		await expect(promptInput).toHaveValue('Original prompt text');
		await expect(statusSelect).toHaveValue('waiting');
		await expect(branchInput).toHaveValue('test-branch');
	});

	test('3. 送信テスト: 値を変更してSubmitすると、詳細ページへリダイレクトされること', async ({ page }) => {
		// Mock PUT request for update
		await page.route(`/api/todos/${todoId}/`, async (route) => {
			if (route.request().method() === 'PUT') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						...mockTodo,
						prompt: 'Updated prompt text',
						status: 'queued'
					})
				});
			}
		});

		await page.goto(`/todo/${todoId}/update`);

		// Wait for form to load
		await page.locator('#prompt').waitFor();

		// Fill in new values
		await page.locator('#prompt').fill('Updated prompt text');
		await page.locator('#status').selectOption('queued');

		// Submit form
		await page.locator('button[type="submit"]').click();

		// Should redirect to detail page
		await expect(page).toHaveURL(`/todo/${todoId}/`);
	});

	test('4. キャンセルボタン: クリックで詳細ページへ戻ること', async ({ page }) => {
		await page.goto(`/todo/${todoId}/update`);

		// Wait for form to load
		await page.locator('#prompt').waitFor();

		// Click cancel button (link to detail page)
		await page.locator('a:has-text("Cancel")').click();

		// Should redirect to detail page
		await expect(page).toHaveURL(`/todo/${todoId}/`);
	});

	test('5. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		// Mock error response for PUT request
		await page.route(`/api/todos/${todoId}/`, async (route) => {
			if (route.request().method() === 'PUT') {
				await route.fulfill({
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify({
						detail: 'Internal Server Error'
					})
				});
			}
		});

		await page.goto(`/todo/${todoId}/update`);

		// Wait for form to load
		await page.locator('#prompt').waitFor();

		// Submit form
		await page.locator('button[type="submit"]').click();

		// Should show error message
		const errorMessage = page.locator('.bg-red-50');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Internal Server Error');
	});

	test('6. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		await page.goto(`/todo/${todoId}/update`);

		// Wait for form to be fully loaded and visible
		const promptInput = page.locator('#prompt');
		const submitButton = page.locator('button[type="submit"]');

		await expect(promptInput).toBeVisible();
		await expect(submitButton).toBeVisible();

		// Wait for loading to complete (prompt should have value after load)
		await expect(promptInput).toHaveValue('Original prompt text', { timeout: 10000 });

		// Take snapshot
		await expect(page).toHaveScreenshot();
	});
});
