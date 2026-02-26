import { expect, test } from '@playwright/test';

const mockExtensionData = {
	id: 1,
	name: 'Test Extension',
	type: 'command',
	cmd: 'echo "hello"',
	args: ['arg1', 'arg2'],
	envs: { KEY: 'value' },
	timeout: 30,
	created_at: '2024-01-01T00:00:00Z',
	updated_at: '2024-01-02T00:00:00Z'
};

test('extension detail page displays loading then shows extension info', async ({ page }) => {
	// API呼び出しをモック（ページ遷移前に設定） - delayを追加してLoading表示を確認
	await page.route('**/api/extensions/1/', async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				id: 1,
				name: 'Test Extension',
				type: 'stdio',
				cmd: 'command',
				args: ['arg1'],
				envs: { KEY: 'value' },
				timeout: 30,
				created_at: '2024-01-01T00:00:00Z',
				updated_at: '2024-01-02T00:00:00Z'
			})
		});
	}, { delay: 100 });

	// 1. ページ遷移: `/extension/1` へアクセス（動的ID）
	// waitUntil: 'domcontentloaded' でHTML読み込み完了時点でテスト開始
	await page.goto('/extension/1', { waitUntil: 'domcontentloaded' });

	// 2. Loading表示: 初期状態で「Loading...」が表示されること
	const loadingText = page.locator('text=Loading...');
	await expect(loadingText).toBeVisible();

	// Loadingが完了し、extension情報が表示されるまで待機
	const nameLabel = page.locator('dt:has-text("Name")');
	await expect(nameLabel).toBeVisible();

	// 各情報が正しく表示されていることを確認
	await expect(page.locator('dd:has-text("Test Extension")')).toBeVisible();
	// type は dd 要素内で確認
	await expect(page.locator('dd:has-text("stdio")')).toBeVisible();
	await expect(page.locator('dd:has-text("30 seconds")')).toBeVisible();

	// 4. Updateリンク: クリックで更新ページへ遷移すること
	const updateLink = page.locator('a:has-text("編集")');
	await expect(updateLink).toBeVisible();
	await updateLink.click();
	await expect(page).toHaveURL(/\/extension\/1\/update\/?$/);

	// 5. Deleteリンク: クリックで削除ページへ遷移すること
	// 詳細ページに戻る
	await page.goto('/extension/1');
	
	// Deleteリンクを確認
	const deleteLink = page.locator('a:has-text("削除")');
	await expect(deleteLink).toBeVisible();
	await deleteLink.click();
	await expect(page).toHaveURL(/\/extension\/1\/delete\/?$/);

	// 6. スナップショットテスト: 詳細ページに戻る
	await page.goto('/extension/1');
	
	// モックを再設定（ページignacigationでクリアされるため）
	await page.route('**/api/extensions/1/', async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				id: 1,
				name: 'Test Extension',
				type: 'stdio',
				cmd: 'command',
				args: ['arg1'],
				envs: { KEY: 'value' },
				timeout: 30,
				created_at: '2024-01-01T00:00:00Z',
				updated_at: '2024-01-02T00:00:00Z'
			})
		});
	}, { delay: 100 });

	// 全ての情報が表示されるまで待機
	const detailsCard = page.locator('h2:has-text("Information")');
	await expect(detailsCard).toBeVisible();

	// HTMLスナップショットテスト
	await expect(page.locator('body')).toMatchAriaSnapshot();
});
