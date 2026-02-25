import { expect, test } from '@playwright/test';

test.describe('Todo Create Page', () => {
	test('should navigate to create page', async ({ page }) => {
		await page.goto('/todo/create');
		await expect(page).toHaveURL('/todo/create');
	});

	test('should display empty fields and Create button', async ({ page }) => {
		await page.goto('/todo/create');

		// Verify prompt input is empty
		const promptInput = page.locator('#prompt');
		await expect(promptInput).toBeVisible();
		await expect(promptInput).toHaveValue('');

		// Verify workdir input is empty
		const workdirInput = page.locator('#workdir');
		await expect(workdirInput).toBeVisible();
		await expect(workdirInput).toHaveValue('');

		// Verify agent input is empty
		const agentInput = page.locator('#agent');
		await expect(agentInput).toBeVisible();
		await expect(agentInput).toHaveValue('');

		// Verify Create button exists
		const createButton = page.locator('button[type="submit"]');
		await expect(createButton).toBeVisible();
		await expect(createButton).toHaveText('Create');
	});

	test('should redirect to list after successful creation', async ({ page }) => {
		// Mock successful API response
		await page.route('/api/todos/', async (route) => {
			await route.fulfill({
				status: 201,
				json: { id: 1, prompt: 'Test prompt', status: 'waiting' }
			});
		});

		await page.goto('/todo/create');

		// Enter prompt (required field)
		const promptInput = page.locator('#prompt');
		await promptInput.fill('Test prompt');

		// Click Create button
		const createButton = page.locator('button[type="submit"]');
		await createButton.click();

		// Verify redirect to list page
		await expect(page).toHaveURL('/todo/');
	});

	test('should navigate to list on cancel button click', async ({ page }) => {
		await page.goto('/todo/create');

		// Click cancel button
		const cancelButton = page.locator('a[href="/todo/"]');
		await expect(cancelButton).toBeVisible();
		await cancelButton.click();

		// Verify navigation to list page
		await expect(page).toHaveURL('/todo/');
	});

	test('should display error message on server error', async ({ page }) => {
		// Mock error response
		await page.route('/api/todos/', async (route) => {
			await route.fulfill({
				status: 500,
				json: { detail: 'Internal server error' }
			});
		});

		await page.goto('/todo/create');

		// Enter prompt
		const promptInput = page.locator('#prompt');
		await promptInput.fill('Test prompt');

		// Click Create button
		const createButton = page.locator('button[type="submit"]');
		await createButton.click();

		// Wait for loading to complete
		await expect(createButton).toHaveText('Create');

		// Verify error message is displayed (by checking for error class on form)
		const errorDiv = page.locator('.bg-red-50');
		await expect(errorDiv).toBeVisible();
		await expect(errorDiv).toContainText('Internal server error');
	});

	test('should take snapshot after page is stable', async ({ page }) => {
		await page.goto('/todo/create');

		// Wait for all elements to be visible and stable
		const promptInput = page.locator('#prompt');
		const workdirInput = page.locator('#workdir');
		const agentInput = page.locator('#agent');
		const statusSelect = page.locator('#status');
		const createButton = page.locator('button[type="submit"]');
		const cancelButton = page.locator('a[href="/todo/"]');

		await expect(promptInput).toBeVisible();
		await expect(workdirInput).toBeVisible();
		await expect(agentInput).toBeVisible();
		await expect(statusSelect).toBeVisible();
		await expect(createButton).toBeVisible();
		await expect(cancelButton).toBeVisible();

		// Take snapshot
		await expect(page).toHaveScreenshot();
	});
});
