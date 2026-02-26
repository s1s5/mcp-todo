import { expect, test } from '@playwright/test';

test.describe('Agent Update Page', () => {
	const agentId = '1';

	test.beforeEach(async ({ page }) => {
		// Mock initial agent data fetch with delay to make loading visible
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						id: 1,
						name: 'Test Agent',
						system_message: 'You are a helpful assistant.',
						command: 'goose run --recipe',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-01T00:00:00Z'
					}),
					delay: 500  // Add delay to make loading state visible
				});
			}
		});
	});

	test('1. ページ遷移: /agent/1/update へアクセス', async ({ page }) => {
		await page.goto(`/agent/${agentId}/update`);
		await expect(page.locator('h1')).toHaveText('Update Agent');
	});

	test('2. 初期値表示: 現在のnameとcommandが入力済みで表示ること', async ({ page }) => {
		await page.goto(`/agent/${agentId}/update`);

		// Wait for form to be loaded
		const nameInput = page.locator('#name');
		const systemMessageInput = page.locator('#systemMessage');
		const commandInput = page.locator('#command');

		await expect(nameInput).toBeVisible();
		await expect(systemMessageInput).toBeVisible();
		await expect(commandInput).toBeVisible();

		// Check initial values
		await expect(nameInput).toHaveValue('Test Agent');
		await expect(systemMessageInput).toHaveValue('You are a helpful assistant.');
		await expect(commandInput).toHaveValue('goose run --recipe');
	});

	test('3. 送信テスト: 値を変更してSubmitすると、詳細ページへリダイレクトされること', async ({ page }) => {
		// Mock both GET (with delay) and PUT requests
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						id: 1,
						name: 'Test Agent',
						system_message: 'You are a helpful assistant.',
						command: 'goose run --recipe',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-01T00:00:00Z'
					}),
					delay: 100  // Small delay for loading state
				});
			} else if (route.request().method() === 'PUT') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						id: 1,
						name: 'Updated Agent',
						system_message: 'You are a helpful assistant.',
						command: 'goose run --custom',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-02T00:00:00Z'
					})
				});
			}
		});

		await page.goto(`/agent/${agentId}/update`);

		// Wait for form to load
		await page.locator('#name').waitFor();

		// Fill in new values
		await page.locator('#name').fill('Updated Agent');
		await page.locator('#command').fill('goose run --custom');

		// Submit form
		await page.locator('button[type="submit"]').click();

		// Should redirect to detail page
		await expect(page).toHaveURL(`/agent/${agentId}/`);
	});

	test('4. キャンセルボタン: クリックで詳細ページへ戻ること', async ({ page }) => {
		await page.goto(`/agent/${agentId}/update`);

		// Wait for form to load
		await page.locator('#name').waitFor();

		// Click cancel button (link to detail page)
		await page.locator('a:has-text("Cancel")').click();

		// Should redirect to detail page
		await expect(page).toHaveURL(`/agent/${agentId}/`);
	});

	test('5. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		// Mock both GET (with delay) and PUT error requests
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						id: 1,
						name: 'Test Agent',
						system_message: 'You are a helpful assistant.',
						command: 'goose run --recipe',
						created_at: '2024-01-01T00:00:00Z',
						updated_at: '2024-01-01T00:00:00Z'
					}),
					delay: 100  // Small delay for loading state
				});
			} else if (route.request().method() === 'PUT') {
				await route.fulfill({
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify({
						detail: 'Internal Server Error'
					})
				});
			}
		});

		await page.goto(`/agent/${agentId}/update`);

		// Wait for form to load
		await page.locator('#name').waitFor();

		// Submit form
		await page.locator('button[type="submit"]').click();

		// Should show error message
		const errorMessage = page.locator('.bg-red-50');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Internal Server Error');
	});

	test('6. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		await page.goto(`/agent/${agentId}/update`);

		// Wait for form to be fully loaded and visible
		const nameInput = page.locator('#name');
		const submitButton = page.locator('button[type="submit"]');

		await expect(nameInput).toBeVisible();
		await expect(submitButton).toBeVisible();

		// Wait for loading to complete (name should have value after load)
		await expect(nameInput).toHaveValue('Test Agent', { timeout: 10000 });

		// Take HTML snapshot
		const html = await page.locator('div.p-6.max-w-2xl.mx-auto').innerHTML();
		expect(html).toMatchSnapshot('agent-update.html');
	});
});
