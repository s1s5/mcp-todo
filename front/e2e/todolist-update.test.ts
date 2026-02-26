import { expect, test } from '@playwright/test';

const mockTodoList = {
	id: 1,
	name: 'Test TodoList',
	workdir: '/home/user/test',
	created_at: '2024-01-01T00:00:00Z',
	updated_at: '2024-01-01T00:00:00Z'
};

test.describe('TodoList Update Page', () => {
	test.beforeEach(async ({ page }) => {
		// Set CSRF token cookie
		await page.context().addCookies([
			{ name: 'csrftoken', value: 'test-csrf-token', domain: 'localhost', path: '/' }
		]);
	});

	test('1. ページ遷移: /todolist/1/update へアクセス', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/update');
		await expect(page).toHaveURL('/todolist/1/update');
	});

	test('2. 初期値表示: 現在のnameとworkdirが入力済みで表示ること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/update');

		// Wait for loading to complete
		await expect(page.locator('#name')).toBeVisible();
		await expect(page.locator('#workdir')).toBeVisible();

		// Check initial values
		await expect(page.locator('#name')).toHaveValue(mockTodoList.name);
		await expect(page.locator('#workdir')).toHaveValue(mockTodoList.workdir);
	});

	test('3. 送信テスト: 値を変更してSubmitすると、詳細ページへリダイレクトされること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			const url = route.request().url();
			if (route.request().method() === 'GET') {
				await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
			} else if (route.request().method() === 'PUT') {
				await route.fulfill({ status: 200, body: JSON.stringify({ ...mockTodoList, name: 'Updated Name' }) });
			}
		});

		await page.goto('/todolist/1/update');

		// Wait for form to load
		await expect(page.locator('#name')).toBeVisible();

		// Update values
		await page.locator('#name').fill('Updated Name');

		// Submit form
		await page.locator('button[type="submit"]').click();

		// Should redirect to detail page
		await expect(page).toHaveURL('/todolist/1/');
	});

	test('4. キャンセルボタン: クリックで詳細ページへ戻ること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/update');

		// Wait for loading to complete
		await expect(page.locator('#name')).toBeVisible();

		// Click cancel link
		await page.locator('a[href="/todolist/1/"]').click();

		// Should navigate to detail page
		await expect(page).toHaveURL('/todolist/1/');
	});

	test('5. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Server Error' }) });
			}
		});

		await page.goto('/todolist/1/update');

		// Wait for error message to appear
		const errorMessage = page.locator('.bg-red-100');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Server Error');
	});

	test('6. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		await page.route('/api/todolists/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockTodoList) });
		});

		await page.goto('/todolist/1/update');

		// Wait for form to be fully loaded
		const nameInput = page.locator('#name');
		const workdirInput = page.locator('#workdir');
		const submitButton = page.locator('button[type="submit"]');

		await expect(nameInput).toBeVisible();
		await expect(workdirInput).toBeVisible();
		await expect(submitButton).toBeVisible();

		// Wait for values to be populated
		await expect(nameInput).toHaveValue(mockTodoList.name);
		await expect(workdirInput).toHaveValue(mockTodoList.workdir);

		// Take HTML snapshot
		await expect(await page.locator('main').innerHTML()).toMatchSnapshot('todolist-update.html');
	});
});
