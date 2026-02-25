import { expect, test } from '@playwright/test';

const mockTodo = {
	id: 1,
	todo_list: 1,
	todo_list_name: 'Test TodoList',
	agent: 1,
	agent_name: 'Test Agent',
	ref_files: ['file1.txt', 'file2.txt'],
	edit_files: ['file3.txt'],
	prompt: 'Test prompt',
	context: 'Test context',
	status: 'waiting',
	output: null,
	error: null,
	validation_command: null,
	timeout: 300,
	created_at: '2024-01-01T00:00:00Z',
	updated_at: '2024-01-01T00:00:00Z',
	branch_name: 'test-branch'
};

test.describe('Todo Delete Page', () => {
	test.beforeEach(async ({ page }) => {
		// Set CSRF token cookie
		await page.context().addCookies([
			{ name: 'csrftoken', value: 'test-csrf-token', domain: 'localhost', path: '/' }
		]);
	});

	test('1. ページ遷移: /todo/1/delete へアクセス', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodo) });
		});

		await page.goto('/todo/1/delete');
		await expect(page).toHaveURL('/todo/1/delete');
	});

	test('2. 確認画面表示: 削除対象の情報と警告メッセージが表示されること', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodo) });
		});

		await page.goto('/todo/1/delete');

		// Wait for loading to complete
		const warningMessage = page.locator('#warning-message');
		await expect(warningMessage).toBeVisible();
		await expect(warningMessage).toContainText('このTodoを削除しますか？');

		// Check warning text is displayed
		const warningText = page.locator('#warning-text');
		await expect(warningText).toBeVisible();
		await expect(warningText).toContainText('この操作は取り消せません');

		// Check todo info is displayed
		await expect(page.locator('#todo-id')).toBeVisible();
		await expect(page.locator('#todo-status')).toBeVisible();
		await expect(page.locator('#todo-prompt')).toBeVisible();
	});

	test('3. 削除実行: 削除ボタンクリックで一覧へリダイレクトされること', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			const method = route.request().method();
			if (method === 'GET') {
				await route.fulfill({ status: 200, body: JSON.stringify(mockTodo) });
			} else if (method === 'DELETE') {
				await route.fulfill({ status: 200, body: '' });
			}
		});

		await page.goto('/todo/1/delete');

		// Wait for loading to complete
		await expect(page.locator('#delete-button')).toBeVisible();

		// Click delete button
		await page.locator('#delete-button').click();

		// Should redirect to list page
		await expect(page).toHaveURL('/todo/');
	});

	test('4. キャンセルボタン: クリックで詳細ページへ戻ること', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodo) });
		});

		await page.goto('/todo/1/delete');

		// Wait for loading to complete
		await expect(page.locator('#cancel-button')).toBeVisible();

		// Click cancel button
		await page.locator('#cancel-button').click();

		// Should navigate to detail page
		await expect(page).toHaveURL('/todo/1/');
	});

	test('5. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Server Error' }) });
			}
		});

		await page.goto('/todo/1/delete');

		// Wait for error message to appear
		const errorMessage = page.locator('#error-message');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Server Error');
	});

	test('6. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodo) });
		});

		await page.goto('/todo/1/delete');

		// Wait for content to be fully loaded
		const warningMessage = page.locator('#warning-message');
		const todoInfo = page.locator('#todo-id');
		const deleteButton = page.locator('#delete-button');
		const cancelButton = page.locator('#cancel-button');

		await expect(warningMessage).toBeVisible();
		await expect(todoInfo).toBeVisible();
		await expect(deleteButton).toBeVisible();
		await expect(cancelButton).toBeVisible();

		// Take snapshot
		await expect(page).toMatchSnapshot('todo-delete-1.html');
	});
});
