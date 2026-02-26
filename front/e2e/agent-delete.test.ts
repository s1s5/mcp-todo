import { expect, test } from '@playwright/test';

const mockAgent = {
	id: 1,
	name: 'Test Agent',
	system_message: 'You are a helpful assistant.',
	command: 'goose run --recipe',
	created_at: '2024-01-01T00:00:00Z',
	updated_at: '2024-01-01T00:00:00Z'
};

test.describe('Agent Delete Page', () => {
	const agentId = '1';

	test.beforeEach(async ({ page }) => {
		// Set CSRF token cookie
		await page.context().addCookies([
			{ name: 'csrftoken', value: 'test-csrf-token', domain: 'localhost', path: '/' }
		]);
	});

	test('1. ページ遷移: /agent/1/delete へアクセス', async ({ page }) => {
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAgent)
			});
		});

		await page.goto(`/agent/${agentId}/delete`);
		await expect(page).toHaveURL(`/agent/${agentId}/delete/`);
	});

	test('2. 確認画面表示: 削除対象の情報と警告メッセージが表示されること', async ({ page }) => {
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAgent)
			});
		});

		await page.goto(`/agent/${agentId}/delete`);

		// Wait for loading to complete
		const warningMessage = page.locator('.text-red-600');
		await expect(warningMessage).toBeVisible();
		await expect(warningMessage).toContainText('このAgentを削除しますか？');

		// Check agent info is displayed
		await expect(page.locator('text=ID')).toBeVisible();
		await expect(page.locator('text=Name')).toBeVisible();
		await expect(page.locator('text=Test Agent')).toBeVisible();
		await expect(page.locator('text=System Message')).toBeVisible();
		await expect(page.locator('text=Command')).toBeVisible();
		await expect(page.locator('text=Created')).toBeVisible();
	});

	test('3. 削除実行: 削除ボタンクリックで一覧へリダイレクトされること', async ({ page }) => {
		// Add delay to make loading state visible
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			const method = route.request().method();
			if (method === 'GET') {
				// Add delay to simulate network latency for loading visibility
				await new Promise((resolve) => setTimeout(resolve, 300));
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockAgent)
				});
			} else if (method === 'DELETE') {
				await route.fulfill({ status: 200, body: '' });
			}
		});

		await page.goto(`/agent/${agentId}/delete`);

		// Test loading state is displayed initially
		const loadingElement = page.locator('text=Loading...');
		await expect(loadingElement).toBeVisible();

		// Wait for loading to complete
		await expect(page.locator('.text-red-600')).toBeVisible();

		// Click delete button
		await page.locator('button:has-text("Delete")').click();

		// Should redirect to list page
		await expect(page).toHaveURL('/agent/');
	});

	test('4. キャンセルボタン: クリックで詳細ページへ戻ること', async ({ page }) => {
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAgent)
			});
		});

		await page.goto(`/agent/${agentId}/delete`);

		// Wait for loading to complete
		await expect(page.locator('.text-red-600')).toBeVisible();

		// Click cancel button
		await page.locator('a:has-text("Cancel")').click();

		// Should navigate to detail page (SvelteKit adds trailing slash)
		await expect(page).toHaveURL(`/agent/${agentId}/`);
	});

	test('5. エラー表示: サーバーエラー時にエラーメッセージが表示されること', async ({ page }) => {
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			if (route.request().method() === 'GET') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockAgent)
				});
			} else if (route.request().method() === 'DELETE') {
				await route.fulfill({
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify({ detail: 'Failed to delete agent' })
				});
			}
		});

		await page.goto(`/agent/${agentId}/delete`);

		// Wait for loading to complete
		await expect(page.locator('.text-red-600')).toBeVisible();

		// Click delete button
		await page.locator('button:has-text("Delete")').click();

		// Should show error message
		const errorMessage = page.locator('.bg-red-50');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Failed to delete agent');
	});

	test('6. スナップショットテスト: 表示安定化後にスナップショットを取得', async ({ page }) => {
		await page.route(`/api/agents/${agentId}/`, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAgent)
			});
		});

		await page.goto(`/agent/${agentId}/delete`);

		// Wait for content to be fully loaded
		const container = page.locator('.max-w-2xl');
		await expect(container).toBeVisible();

		// Wait for content to be fully loaded
		const warningMessage = page.locator('.text-red-600');
		const deleteButton = page.locator('button:has-text("Delete")');
		const cancelButton = page.locator('a:has-text("Cancel")');

		await expect(warningMessage).toBeVisible();
		await expect(deleteButton).toBeVisible();
		await expect(cancelButton).toBeVisible();

		// Take HTML snapshot of form element
		const formElement = page.locator('form');
		await expect(formElement).toBeVisible();
		expect(await formElement.innerHTML()).toMatchSnapshot('agent-delete-form.html');
	});
});
