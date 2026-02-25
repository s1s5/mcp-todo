import { expect, test } from '@playwright/test';

test.describe('Extension Create Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/extension/create');
	});

	test('1. ページ遷移: /extension/create へアクセス', async ({ page }) => {
		await expect(page).toHaveURL('/extension/create');
		await expect(page.locator('h1')).toHaveText('Create Extension');
	});

	test('2. 初期表示: nameとcode入力フィールドが空で表示、Createボタンが存在すること', async ({ page }) => {
		// name入力フィールドが空
		await expect(page.locator('#name')).toHaveValue('');
		
		// cmd入力フィールドが空
		await expect(page.locator('#cmd')).toHaveValue('');
		
		// Createボタンが存在すること
		await expect(page.locator('button[type="submit"]')).toBeVisible();
		await expect(page.locator('button[type="submit"]')).toHaveText('Create');
		
		// キャンセルボタンが存在すること
		await expect(page.locator('a[href="/extension/"]')).toBeVisible();
		await expect(page.locator('a[href="/extension/"]')).toHaveText('Cancel');
	});

	test('3. 送信テスト: 有効な値を入力してSubmitすると、一覧へリダイレクトされること', async ({ page }) => {
		// APIリクエストをモック
		await page.route('/api/extensions/', async (route) => {
			await route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify({ id: 1, name: 'test-ext', type: 'stdio', cmd: 'echo' })
			});
		});

		// フォームに入力
		await page.locator('#name').fill('test-extension');
		await page.locator('#cmd').fill('echo');
		await page.locator('#args').fill('["hello"]');
		await page.locator('#envs').fill('{"KEY": "value"}');

		// Submit
		await page.locator('button[type="submit"]').click();

		// 一覧へリダイレクトされること
		await expect(page).toHaveURL('/extension/');
	});

	test('4. キャンセルボタン: クリックで一覧へ戻ること', async ({ page }) => {
		await page.locator('a[href="/extension/"]').click();
		await expect(page).toHaveURL('/extension/');
	});

	test('5. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		// APIリクエストをモックしてエラーを返す
		await page.route('/api/extensions/', async (route) => {
			await route.fulfill({
				status: 500,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Internal server error' })
			});
		});

		// フォームに入力
		await page.locator('#name').fill('test-extension');
		await page.locator('#cmd').fill('echo');

		// Submit
		await page.locator('button[type="submit"]').click();

		// エラーメッセージが表示されること
		const errorMessage = page.locator('.bg-red-50');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Internal server error');

		// ボタンをクリック可能在 комплекс
		await expect(page.locator('button[type="submit"]')).toBeEnabled();
	});

	test('6. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		// 表示が安定するまで待機
		await expect(page.locator('h1')).toBeVisible();
		await expect(page.locator('#name')).toBeVisible();
		await expect(page.locator('#cmd')).toBeVisible();
		await expect(page.locator('button[type="submit"]')).toBeVisible();

		// HTMLスナップショットを取得して比較
		const html = await page.content();
		expect(html).toMatchSnapshot('extension-create.html');
	});
});
