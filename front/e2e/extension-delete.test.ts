import { expect, test } from '@playwright/test';

const mockExtension = {
	id: 1,
	name: 'Test Extension',
	type: 'command',
	cmd: 'echo "test"',
	args: [],
	envs: {},
	timeout: 60,
	created_at: '2024-01-01T00:00:00Z',
	updated_at: '2024-01-01T00:00:00Z'
};

test.describe('Extension Delete Page', () => {
	test.beforeEach(async ({ page }) => {
		// Set CSRF token cookie
		await page.context().addCookies([
			{ name: 'csrftoken', value: 'test-csrf-token', domain: 'localhost', path: '/' }
		]);
	});

	test('1. ページ遷移: /extension/1/delete へアクセス', async ({ page }) => {
		await page.route('/api/extensions/1/', async (route) => {
			await new Promise((resolve) => setTimeout(resolve, 200));
			await route.fulfill({ status: 200, body: JSON.stringify(mockExtension) });
		});

		await page.goto('/extension/1/delete');
		
		// Loading 表示を確認（APIが遅延応答するため）
		await expect(page.locator('#loading-indicator')).toBeVisible({ timeout: 1000 });
		
		// 読み込み完了後にURLを確認（末尾のスラッシュを許容）
		await expect(page).toHaveURL(/\/extension\/1\/delete\/?$/);
	});

	test('2. 確認画面表示: 削除対象の情報と警告メッセージが表示されること', async ({ page }) => {
		await page.route('/api/extensions/1/', async (route) => {
			await new Promise((resolve) => setTimeout(resolve, 200));
			await route.fulfill({ status: 200, body: JSON.stringify(mockExtension) });
		});

		await page.goto('/extension/1/delete');

		// Loading 表示を確認（APIが遅延応答するため）
		await expect(page.locator('#loading-indicator')).toBeVisible({ timeout: 1000 });
		
		// 読み込み完了後に警告メッセージを確認
		const warningMessage = page.locator('#warning-message');
		await expect(warningMessage).toBeVisible();
		await expect(warningMessage).toContainText('このExtensionを削除しますか？');

		// Check warning text is displayed
		const warningText = page.locator('#warning-text');
		await expect(warningText).toBeVisible();
		await expect(warningText).toContainText('この操作は取り消せません');

		// Check extension info is displayed (ID, Name, Type, Command, etc.)
		await expect(page.locator('text=ID')).toBeVisible();
		await expect(page.locator('text=Name')).toBeVisible();
		await expect(page.locator('text=Type')).toBeVisible();
		await expect(page.locator('dt:has-text("Command")')).toBeVisible();
		await expect(page.locator('text=Timeout')).toBeVisible();
	});

	test('3. 削除実行: 削除ボタンクリックで一覧へリダイレクトされること', async ({ page }) => {
		await page.route('/api/extensions/1/', async (route) => {
			const method = route.request().method();
			if (method === 'GET') {
				await route.fulfill({ status: 200, body: JSON.stringify(mockExtension) });
			} else if (method === 'DELETE') {
				await route.fulfill({ status: 200, body: '' });
			}
		});

		await page.goto('/extension/1/delete');

		// Wait for loading to complete
		await expect(page.locator('#delete-button')).toBeVisible();

		// Click delete button
		await page.locator('#delete-button').click();

		// Should redirect to list page
		await expect(page).toHaveURL('/extension/');
	});

	test('4. キャンセルボタン: クリックで詳細ページへ戻ること', async ({ page }) => {
		await page.route('/api/extensions/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockExtension) });
		});

		await page.goto('/extension/1/delete');

		// Wait for loading to complete
		await expect(page.locator('#cancel-button')).toBeVisible();

		// Click cancel button
		await page.locator('#cancel-button').click();

		// Should navigate to detail page
		await expect(page).toHaveURL('/extension/1/');
	});

	test('5. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		await page.route('/api/extensions/1/', async (route) => {
			await new Promise((resolve) => setTimeout(resolve, 100));
			if (route.request().method() === 'GET') {
				await route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Server Error' }) });
			}
		});

		await page.goto('/extension/1/delete');

		// Loading 表示を確認
		await expect(page.locator('#loading-indicator')).toBeVisible();
		
		// エラーメッセージを確認（コンポーネント側のcatchブロックで設定される）
		const errorMessage = page.locator('#error-message');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Failed to fetch extension');
	});

	test('6. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		await page.route('/api/extensions/1/', async (route) => {
			await route.fulfill({ status: 200, body: JSON.stringify(mockExtension) });
		});

		await page.goto('/extension/1/delete');

		// Wait for content to be fully loaded
		const warningMessage = page.locator('#warning-message');
		const deleteButton = page.locator('#delete-button');
		const cancelButton = page.locator('#cancel-button');

		await expect(warningMessage).toBeVisible();
		await expect(deleteButton).toBeVisible();
		await expect(cancelButton).toBeVisible();

		// Get HTML and normalize SvelteKit-generated hashes for consistent snapshot comparison
		let html = await page.content();
		
		// Normalize SvelteKit hashes: replace dynamic hash patterns with fixed values
		// Pattern: __sveltekit_\w+ -> __sveltekit_HASH
		html = html.replace(/__sveltekit_\w+/g, '__sveltekit_HASH');
		// Pattern: /build/start.[A-Za-z0-9]+.js -> /build/start.HASH.js
		html = html.replace(/\/build\/start\.[A-Za-z0-9]+\.js/g, '/build/start.HASH.js');
		html = html.replace(/\/build\/layout\.[A-Za-z0-9]+\.js/g, '/build/layout.HASH.js');
		html = html.replace(/\/build\/page\.[A-Za-z0-9]+\.js/g, '/build/page.HASH.js');
		
		// Take snapshot
		expect(html).toMatchSnapshot('extension-delete.html');
	});
});
