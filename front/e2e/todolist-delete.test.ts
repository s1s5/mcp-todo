import { expect, test } from '@playwright/test';

const mockTodoList = {
	id: 1,
	workdir: '/home/user/test',
	created_at: '2024-01-01T00:00:00.000Z',
	updated_at: '2024-01-01T00:00:00.000Z'
};

test.describe('TodoList Delete Page', () => {
	test.beforeEach(async ({ page }) => {
		// Set CSRF token cookie
		await page.context().addCookies([
			{ name: 'csrftoken', value: 'test-csrf-token', domain: 'localhost', path: '/' }
		]);
	});

	test('1. ページ遷移: /todolist/1/delete へアクセス', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/delete');
		// SvelteKit adds trailing slash
		await expect(page).toHaveURL(/\/todolist\/1\/delete\/?/);
	});

	test('2. Loading表示: データ取得中にLoadingメッセージが表示されること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			// Add delay to allow loading state to be visible
			await new Promise((resolve) => setTimeout(resolve, 100));
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/delete');

		// Loading message should be visible initially
		await expect(page.locator('text=Loading...')).toBeVisible();
		// Then content should load
		await expect(page.locator('text=削除するTodoList')).toBeVisible();
	});

	test('3. 確認画面表示: 削除対象の情報と警告メッセージが表示されること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/delete');

		// Wait for loading to complete
		const warningMessage = page.locator('.bg-red-50');
		await expect(warningMessage).toBeVisible();
		await expect(warningMessage).toContainText('このTodoListを削除しますか？');

		// Check todolist info is displayed
		await expect(page.locator('text=削除するTodoList')).toBeVisible();
		await expect(page.locator('text=ID')).toBeVisible();
		await expect(page.locator('text=Workdir')).toBeVisible();
		await expect(page.locator('text=作成日')).toBeVisible();
	});

	test('4. 削除実行: 削除ボタンクリックで一覧へリダイレクトされること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			const method = route.request().method();
			if (method === 'GET') {
				await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
			} else if (method === 'DELETE') {
				await route.fulfill({ status: 200, body: '' });
			}
		});

		await page.goto('/todolist/1/delete');

		// Wait for loading to complete
		await expect(page.locator('text=削除するTodoList')).toBeVisible();

		// Click delete button
		await page.locator('button:has-text("削除")').click();

		// Should redirect to list page
		await expect(page).toHaveURL('/todolist/');
	});

	test('5. キャンセルボタン: クリックで詳細ページへ戻ること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/delete');

		// Wait for loading to complete
		await expect(page.locator('text=削除するTodoList')).toBeVisible();

		// Click cancel button
		await page.locator('a:has-text("キャンセル")').click();

		// Should navigate to detail page
		await expect(page).toHaveURL('/todolist/1/');
	});

	test('6. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Server Error' }) });
			}
		});

		await page.goto('/todolist/1/delete');

		// Wait for error message to appear
		const errorMessage = page.locator('.text-red-500');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Failed to fetch');
	});

	test('7. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/delete');

		// Wait for content to be fully loaded
		const warningMessage = page.locator('.bg-red-50');
		const todolistInfo = page.locator('text=削除するTodoList');
		const deleteButton = page.locator('button:has-text("削除")');
		const cancelButton = page.locator('a:has-text("キャンセル")');

		await expect(warningMessage).toBeVisible();
		await expect(todolistInfo).toBeVisible();
		await expect(deleteButton).toBeVisible();
		await expect(cancelButton).toBeVisible();

		// Take HTML snapshot
		const html = await page.locator('div.p-6.max-w-2xl.mx-auto').innerHTML();
		expect(html).toMatchSnapshot('todolist-delete.html');
	});
});
