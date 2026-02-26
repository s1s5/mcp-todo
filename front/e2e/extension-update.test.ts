import { expect, test } from '@playwright/test';

test.describe('Extension Update Page', () => {
	const mockExtension = {
		id: 1,
		name: 'test-ext',
		type: 'stdio',
		cmd: 'echo',
		args: ['hello'],
		envs: { KEY: 'value' },
		timeout: 300,
		created_at: '2024-01-01T00:00:00Z',
		updated_at: '2024-01-01T00:00:00Z'
	};

	test.beforeEach(async ({ page }) => {
		// APIレスポンスをモック（delayを追加してLoading表示を確認可能にする）
		await page.route(`/api/extensions/1/`, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockExtension),
				delay: 100
			});
		});

		await page.goto('/extension/1/update');
	});

	test('1. ページ遷移: /extension/1/update へアクセス', async ({ page }) => {
		await expect(page).toHaveURL(/\/extension\/1\/update\/?/);
		await expect(page.locator('h1')).toHaveText('Update Extension');
	});

	test('2. 初期値表示: 現在の値が入力済みで表示ること', async ({ page }) => {
		// フォームが読み込まれるまで待機
		await expect(page.locator('#name')).toBeVisible();
		await expect(page.locator('#cmd')).toBeVisible();

		// 初期値が設定されていること
		await expect(page.locator('#name')).toHaveValue('test-ext');
		await expect(page.locator('#cmd')).toHaveValue('echo');
		await expect(page.locator('#type')).toHaveValue('stdio');
		await expect(page.locator('#args')).toHaveValue('["hello"]');
		await expect(page.locator('#envs')).toHaveValue('{"KEY":"value"}');
		await expect(page.locator('#timeout')).toHaveValue('300');

		// Updateボタンが存在すること
		await expect(page.locator('button[type="submit"]')).toBeVisible();
		await expect(page.locator('button[type="submit"]')).toHaveText('Update');

		// キャンセルボタンが存在すること（テキストで特定）
		await expect(page.locator('a:has-text("Cancel")')).toBeVisible();
	});

	test('3. 送信テスト: 値を変更してSubmitすると、詳細ページへリダイレクトされること', async ({ page }) => {
		// Mock both GET (with delay) and PUT requests
		await page.route(`/api/extensions/1/`, async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockExtension),
					delay: 100  // Small delay for loading state
				});
			} else if (route.request().method() === 'PUT') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ ...mockExtension, name: 'updated-ext' })
				});
			}
		});

		// フォームが読み込まれるまで待機
		await expect(page.locator('#name')).toBeVisible();

		// フォームの値を変更
		await page.locator('#name').fill('updated-ext');
		await page.locator('#cmd').fill('echo hello');

		// Submit
		await page.locator('button[type="submit"]').click();

		// 詳細ページへリダイレクトされること
		await expect(page).toHaveURL(/\/extension\/1\/?/);
	});

	test('4. キャンセルボタン: クリックで詳細ページへ戻ること', async ({ page }) => {
		await page.locator('a:has-text("Cancel")').click();
		await expect(page).toHaveURL(/\/extension\/1\/?/);
	});

	test('5. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		// Mock both GET (with delay) and PUT requests
		await page.route(`/api/extensions/1/`, async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockExtension),
					delay: 100
				});
			} else if (route.request().method() === 'PUT') {
				await route.fulfill({
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify({ detail: 'Internal server error' })
				});
			}
		});

		// フォームが読み込まれるまで待機
		await expect(page.locator('#name')).toBeVisible();

		// フォームの値を変更
		await page.locator('#name').fill('updated-ext');

		// Submit
		await page.locator('button[type="submit"]').click();

		// エラーメッセージが表示されること
		const errorMessage = page.locator('.bg-red-50');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Internal server error');

		// ボタンをクリック可能な状態であること
		await expect(page.locator('button[type="submit"]')).toBeEnabled();
	});

	test('6. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		// 表示が安定するまで待機
		await expect(page.locator('h1')).toBeVisible();
		await expect(page.locator('#name')).toBeVisible();
		await expect(page.locator('#cmd')).toBeVisible();
		await expect(page.locator('button[type="submit"]')).toBeVisible();

		// HTMLスナップショットを取得
		const html = await page.content();
		expect(html).toMatchSnapshot('extension-update-linux.html');
	});
});
