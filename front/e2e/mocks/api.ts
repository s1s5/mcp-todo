import { type Page } from '@playwright/test';

/**
 * 共通APIモックユーティリティ
 * E2Eテストで必要なAPIリクエストをモック化する
 */

/**
 * TodoList詳細ページに必要な全APIをモックする
 */
export async function mockTodolistDetailApis(page: Page, todolistId: number = 1) {
  await page.route(`**/api/todolists/${todolistId}/`, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        id: todolistId,
        name: 'Test List',
        workdir: '/home/user/test',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z'
      }
    });
  });

  await page.route(`**/api/todolists/${todolistId}/branches/`, async (route) => {
    await route.fulfill({
      status: 200,
      json: { branches: [] }
    });
  });

  await page.route(`**/api/todolists/${todolistId}/worktrees/`, async (route) => {
    await route.fulfill({
      status: 200,
      json: { worktrees: [] }
    });
  });

  await page.route(`**/api/todos**`, async (route) => {
    await route.fulfill({
      status: 200,
      json: []
    });
  });
}

/**
 * Todo詳細ページに必要な全APIをモックする
 */
export async function mockTodoDetailApis(page: Page, todoId: number = 1) {
  await page.route(`**/api/todos/${todoId}/`, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        id: todoId,
        todo_list: 1,
        todo_list_name: 'Test TodoList',
        agent: 1,
        agent_name: 'Test Agent',
        prompt: 'Test prompt',
        title: 'Test Title',
        status: 'waiting',
        branch_name: 'test-branch',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z'
      }
    });
  });

  await page.route(`**/api/todos/${todoId}/branches/`, async (route) => {
    await route.fulfill({
      status: 200,
      json: { branches: [] }
    });
  });

  await page.route(`**/api/todos/${todoId}/worktrees/`, async (route) => {
    await route.fulfill({
      status: 200,
      json: { worktrees: [] }
    });
  });
}
