import { expect, test } from '@playwright/test';

test.describe('Todo Detail Page', () => {
	const mockTodo = {
		id: 1,
		todo_list: 1,
		todo_list_name: 'Test TodoList',
		agent: 1,
		agent_name: 'Test Agent',
		ref_files: ['src/file1.ts', 'src/file2.ts'],
		edit_files: ['src/edit1.ts'],
		prompt: 'This is a test prompt',
		context: 'Test context',
		status: 'waiting',
		output: null,
		error: null,
		validation_command: 'npm run check',
		timeout: 300,
		created_at: '2024-01-01T00:00:00Z',
		updated_at: '2024-01-01T00:00:00Z',
		branch_name: 'test-branch'
	};

	test('should display loading then todo details', async ({ page }) => {
		// APIをモック
		await page.route('/api/todos/1/', async (route) => {
			await route.continue();
		});

		// ページへアクセス
		await page.goto('/todo/1');

		// Loading表示の確認
		const loadingLocator = page.getByText('Loading...');
		await expect(loadingLocator).toBeVisible();

		// Todo情報が表示されるまで待機
		const todoDetails = page.getByText('Todo詳細');
		await expect(todoDetails).toBeVisible();

		// 表示安定化後にスナップショットを取得
		await expect(page.locator('h1')).toBeVisible();
		await expect(page.locator('text=Test TodoList')).toBeVisible();
		await expect(page.locator('text=Test Agent')).toBeVisible();
		await expect(page.locator('text=waiting')).toBeVisible();

		// スナップショットテスト
		await expect(page).toHaveScreenshot();
	});

	test('should navigate to update page', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockTodo)
			});
		});

		await page.goto('/todo/1');

		// Todo情報が表示されるまで待機
		await expect(page.getByText('Test TodoList')).toBeVisible();

		// 編集リンクをクリック
		const updateLink = page.getByRole('link', { name: '編集' });
		await expect(updateLink).toBeVisible();
		await updateLink.click();

		// 更新ページへ遷移することを確認
		await expect(page).toHaveURL('/todo/1/update/');
	});

	test('should navigate to delete page', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockTodo)
			});
		});

		await page.goto('/todo/1');

		// Todo情報が表示されるまで待機
		await expect(page.getByText('Test TodoList')).toBeVisible();

		// 削除リンクをクリック
		const deleteLink = page.getByRole('link', { name: '削除' });
		await expect(deleteLink).toBeVisible();
		await deleteLink.click();

		// 削除ページへ遷移することを確認
		await expect(page).toHaveURL('/todo/1/delete/');
	});
});
