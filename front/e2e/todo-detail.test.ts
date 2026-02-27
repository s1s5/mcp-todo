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
		title: 'Test Title',
		auto_stash: false,
		keep_branch: true,
		context: 'Test context',
		status: 'waiting',
		output: null,
		error: null,
		validation_command: 'npm run check',
		timeout: 300,
		priority: 0,
		started_at: null,
		finished_at: null,
		created_at: '2024-01-01T00:00:00.000Z',
		updated_at: '2024-01-01T00:00:00.000Z',
		branch_name: 'test-branch'
	};

	test('should display todo details', async ({ page }) => {
		// APIをモック
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockTodo)
			});
		});

		// ページへアクセス
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.goto('/todo/1');

		// Todo情報が表示されるまで待機
		const todoDetails = page.getByText('Todo詳細');
		await expect(todoDetails).toBeVisible();

		// 表示安定化後にスナップショットを取得
		await expect(page.locator('h1')).toBeVisible();
		await expect(page.locator('text=Test TodoList')).toBeVisible();
		await expect(page.locator('text=Test Agent')).toBeVisible();
		await expect(page.locator('text=waiting')).toBeVisible();

		// スナップショットテスト
		// 明示的にLinux用のスナップショットファイルを指定
		await expect(page.locator('.max-w-4xl')).toMatchSnapshot('todo-detail.html');
	});

	test('should navigate to update page', async ({ page }) => {
		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockTodo)
			});
		});
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
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
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
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

	// ===== Priority機能テスト =====

	test('should display priority with buttons in waiting status', async ({ page }) => {
		const waitingTodo = { ...mockTodo, status: 'waiting', priority: 0 };

		// GETとPATCH両方のリクエストをモック
		let patchRequestBody: unknown = null;
		await page.route('/api/todos/1/', async (route) => {
			if (route.request().method() === 'PATCH') {
				patchRequestBody = JSON.parse(route.request().postData() || '{}');
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ ...waitingTodo, priority: patchRequestBody.priority })
				});
			} else {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(waitingTodo)
				});
			}
		});
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});

		await page.goto('/todo/1');

		// 優先度ラベルが表示されている
		const priorityLabel = page.getByText('優先度');
		await expect(priorityLabel).toBeVisible();

		// priority値が表示されている（priority=0 の場合は灰色のバッジ）
		// priority値は label の兄弟要素の div 内の最初の span
		const priorityValue = priorityLabel.locator('..').locator('div').locator('span').first();
		await expect(priorityValue).toBeVisible();
		await expect(priorityValue).toHaveText('0');

		// Low/Middle/Highボタンがすべて表示されている
		const lowButton = page.getByRole('button', { name: 'Low' });
		const middleButton = page.getByRole('button', { name: 'Middle' });
		const highButton = page.getByRole('button', { name: 'High' });
		await expect(lowButton).toBeVisible();
		await expect(middleButton).toBeVisible();
		await expect(highButton).toBeVisible();

		// 選択中のMiddleボタンに適切な背景色クラスが適用されている
		await expect(middleButton).toHaveClass(/bg-blue-600/);
	});

	test('should display priority with buttons in queued status', async ({ page }) => {
		const queuedTodo = { ...mockTodo, status: 'queued', priority: -10 };

		await page.route('/api/todos/1/', async (route) => {
			if (route.request().method() === 'PATCH') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(queuedTodo)
				});
			} else {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(queuedTodo)
				});
			}
		});
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});

		await page.goto('/todo/1');

		// 優先度ラベルが表示されている
		const priorityLabel = page.getByText('優先度');
		await expect(priorityLabel).toBeVisible();

		// priority値が表示されている
		// priority値は label の兄弟要素の div 内の最初の span
		const priorityValue = priorityLabel.locator('..').locator('div').locator('span').first();
		await expect(priorityValue).toBeVisible();
		await expect(priorityValue).toHaveText('-10');

		// Low/Middle/Highボタンがすべて表示されている
		const lowButton = page.getByRole('button', { name: 'Low' });
		const middleButton = page.getByRole('button', { name: 'Middle' });
		const highButton = page.getByRole('button', { name: 'High' });
		await expect(lowButton).toBeVisible();
		await expect(middleButton).toBeVisible();
		await expect(highButton).toBeVisible();

		// 選択中のLowボタンに適切な背景色クラスが適用されている
		await expect(lowButton).toHaveClass(/bg-gray-600/);
	});

	test('should hide priority buttons in running status', async ({ page }) => {
		const runningTodo = { ...mockTodo, status: 'running', priority: 10 };

		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(runningTodo)
			});
		});

		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.goto('/todo/1');

		// 優先度ラベルが表示されている
		const priorityLabel = page.getByText('優先度');
		await expect(priorityLabel).toBeVisible();

		// priority値が表示されている
		// priority値は label の兄弟要素の div 内の最初の span
		const priorityValue = priorityLabel.locator('..').locator('div').locator('span').first();
		await expect(priorityValue).toBeVisible();
		await expect(priorityValue).toHaveText('10');

		// Low/Middle/High選択ボタンが非表示
		const lowButton = page.getByRole('button', { name: 'Low' });
		const middleButton = page.getByRole('button', { name: 'Middle' });
		const highButton = page.getByRole('button', { name: 'High' });
		await expect(lowButton).not.toBeVisible();
		await expect(middleButton).not.toBeVisible();
		await expect(highButton).not.toBeVisible();
	});

	test('should update priority when clicking Low button', async ({ page }) => {
		const waitingTodo = { ...mockTodo, status: 'waiting', priority: 0 };

		const patchPromise = page.waitForRequest((req) => req.url().includes('/api/todos/1/') && req.method() === 'PATCH');

		await page.route('/api/todos/1/', async (route) => {
			if (route.request().method() === 'PATCH') {
				const body = JSON.parse(route.request().postData() || '{}');
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ ...waitingTodo, priority: body.priority })
				});
			} else {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(waitingTodo)
				});
			}
		});

		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.goto('/todo/1');

		// Lowボタンをクリック
		const lowButton = page.getByRole('button', { name: 'Low' });
		await expect(lowButton).toBeVisible();
		await lowButton.click();

		// PATCHリクエストが発生することを確認
		const patchRequest = await patchPromise;
		const patchBody = JSON.parse(patchRequest.postData() || '{}');
		expect(patchBody).toEqual({ priority: -10 });
	});

	test('should update priority when clicking Middle button', async ({ page }) => {
		const waitingTodo = { ...mockTodo, status: 'waiting', priority: -10 };

		const patchPromise = page.waitForRequest((req) => req.url().includes('/api/todos/1/') && req.method() === 'PATCH');

		await page.route('/api/todos/1/', async (route) => {
			if (route.request().method() === 'PATCH') {
				const body = JSON.parse(route.request().postData() || '{}');
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ ...waitingTodo, priority: body.priority })
				});
			} else {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(waitingTodo)
				});
			}
		});

		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.goto('/todo/1');

		// Middleボタンをクリック
		const middleButton = page.getByRole('button', { name: 'Middle' });
		await expect(middleButton).toBeVisible();
		await middleButton.click();

		// PATCHリクエストが発生することを確認
		const patchRequest = await patchPromise;
		const patchBody = JSON.parse(patchRequest.postData() || '{}');
		expect(patchBody).toEqual({ priority: 0 });
	});

	test('should update priority when clicking High button', async ({ page }) => {
		const waitingTodo = { ...mockTodo, status: 'waiting', priority: 0 };

		const patchPromise = page.waitForRequest((req) => req.url().includes('/api/todos/1/') && req.method() === 'PATCH');

		await page.route('/api/todos/1/', async (route) => {
			if (route.request().method() === 'PATCH') {
				const body = JSON.parse(route.request().postData() || '{}');
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ ...waitingTodo, priority: body.priority })
				});
			} else {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(waitingTodo)
				});
			}
		});

		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.goto('/todo/1');

		// Highボタンをクリック
		const highButton = page.getByRole('button', { name: 'High' });
		await expect(highButton).toBeVisible();
		await highButton.click();

		// PATCHリクエストが発生することを確認
		const patchRequest = await patchPromise;
		const patchBody = JSON.parse(patchRequest.postData() || '{}');
		expect(patchBody).toEqual({ priority: 10 });
	});

	// ===== 処理時間表示テスト =====

	test('should display processing time in completed status', async ({ page }) => {
		const completedTodo = {
			...mockTodo,
			status: 'completed',
			started_at: '2024-01-01T00:00:00.000Z',
			finished_at: '2024-01-01T00:10:30.000Z'
		};

		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(completedTodo)
			});
		});
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});

		await page.goto('/todo/1');

		// 処理時間が表示されている
		const processingTime = page.locator('text=処理時間:');
		await expect(processingTime).toBeVisible();
		await expect(processingTime).toContainText('10分30秒');
	});

	test('should display processing time in error status', async ({ page }) => {
		const errorTodo = {
			...mockTodo,
			status: 'error',
			started_at: '2024-01-01T00:00:00.000Z',
			finished_at: '2024-01-01T00:05:15.000Z'
		};

		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(errorTodo)
			});
		});
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});

		await page.goto('/todo/1');

		// 処理時間が表示されている
		const processingTime = page.locator('text=処理時間:');
		await expect(processingTime).toBeVisible();
		await expect(processingTime).toContainText('5分15秒');
	});

	test('should not display processing time in running status', async ({ page }) => {
		const runningTodo = {
			...mockTodo,
			status: 'running',
			started_at: '2024-01-01T00:00:00.000Z',
			finished_at: null
		};

		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(runningTodo)
			});
		});
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});

		await page.goto('/todo/1');
		const processingTime = page.locator('text=処理時間:');
		await expect(processingTime).not.toBeVisible();
	});

	// ===== スナップショットテスト =====

	test('should take snapshot after todo detail page is stabilized', async ({ page }) => {
		const waitingTodo = { ...mockTodo, status: 'waiting', priority: 0 };

		await page.route('/api/todos/1/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(waitingTodo)
			});
		});
		await page.route('/api/todos/1/worktrees/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('/api/todos/1/branches/', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});

		await page.goto('/todo/1');

		// Todo情報が表示されるまで待機
		await expect(page.getByText('Test TodoList')).toBeVisible();
		await expect(page.getByText('waiting')).toBeVisible();

		// メインコンテンツのHTMLスナップショットを取得
		// 明示的にLinux用のスナップショットファイルを指定
		await expect(page.locator('.max-w-4xl')).toMatchSnapshot('todo-detail.html');
	});
});
