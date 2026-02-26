import { test, expect } from '@playwright/test';

const mockTodo = {
	id: 1,
	todo_list: 1,
	todo_list_name: 'Test TodoList',
	agent: 1,
	agent_name: 'Test Agent',
	ref_files: ['file1.ts', 'file2.ts'],
	edit_files: ['src/app.ts'],
	prompt: 'Test prompt for deletion',
	context: '',
	status: 'waiting',
	output: null,
	error: null,
	validation_command: null,
	timeout: 300,
	created_at: '2024-01-01T00:00:00Z',
	updated_at: '2024-01-01T00:00:00Z',
	branch_name: 'test-branch'
};

test.describe('Todo削除ページ', () => {
	test.beforeEach(async ({ page }) => {
		// APIリクエストをモックして、遅延を追加する
		await page.route('/api/todos/1/', async (route) => {
			// 500msの遅延を追加してLoadingを表示させる
			await new Promise((resolve) => setTimeout(resolve, 500));
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockTodo)
			});
		});
	});

	test('ページ遷移: 削除ページにアクセスできる', async ({ page }) => {
		await page.goto('/todo/1/delete');
		await expect(page).toHaveURL(/\/todo\/1\/delete/);
		await expect(page.locator('h1')).toContainText('Todo削除');
	});

	test('確認画面: 警告メッセージと削除ボタンが表示される', async ({ page }) => {
		await page.goto('/todo/1/delete');

		// Loading が表示されてからデータが表示されるまで待つ
		await expect(page.locator('#loading-message')).toBeVisible();
		await expect(page.locator('#warning-message')).toBeVisible();
		await expect(page.locator('#warning-text')).toContainText('このTodoを削除しますか？');
		await expect(page.locator('#delete-button')).toBeVisible();
		await expect(page.locator('#cancel-button')).toBeVisible();
	});

	test('Loadingテスト: API応答遅延時にLoading表示される', async ({ page }) => {
		await page.goto('/todo/1/delete');

		// 最初にLoadingが表示される
		await expect(page.locator('#loading-message')).toBeVisible();
		await expect(page.locator('#loading-message')).toContainText('Loading...');

		// 遅延の後、データが表示される
		await expect(page.locator('#warning-message')).toBeVisible({ timeout: 5000 });
		await expect(page.locator('#loading-message')).not.toBeVisible();
	});

	test('削除実行: 削除ボタンクリック後にリダイレクトされる', async ({ page }) => {
		// DELETE APIもモック
		await page.route('/api/todos/1/', async (route) => {
			const method = route.request().method();
			if (method === 'DELETE') {
				await route.fulfill({
					status: 204,
					body: ''
				});
			} else {
				await new Promise((resolve) => setTimeout(resolve, 500));
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockTodo)
				});
			}
		});

		await page.goto('/todo/1/delete');
		await expect(page.locator('#warning-message')).toBeVisible({ timeout: 5000 });

		// 削除ボタンをクリック
		await page.click('#delete-button');

		// /todo/ にリダイレクトされる
		await expect(page).toHaveURL(/\/todo\/$/, { timeout: 10000 });
	});

	test('キャンセルボタン: クリックで元のページに戻る', async ({ page }) => {
		await page.goto('/todo/1/delete');
		await expect(page.locator('#warning-message')).toBeVisible({ timeout: 5000 });

		// キャンセルボタンをクリック（hrefが/todo/1 のリンクをクリック）
		await page.click('#cancel-button');

		// 元のTodo詳細ページに遷移（trailing slashあり）
		await expect(page).toHaveURL(/\/todo\/1\/$/, { timeout: 5000 });
	});

	test('エラーハンドリング: サーバーエラー時にエラーメッセージを表示', async ({ page }) => {
		// エラー状態をモック
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 500,
				contentType: 'application/json',
				body: JSON.stringify({ error: 'Server error' })
			});
		});

		await page.goto('/todo/1/delete');

		// エラーメッセージが表示される
		await expect(page.locator('.text-red-500')).toBeVisible({ timeout: 5000 });
		await expect(page.locator('.text-red-500')).toContainText(/Failed|error|失敗/i);
	});
});
