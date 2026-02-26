import { expect, test } from '@playwright/test';

test.describe('Todo Create Page', () => {
	test('should navigate to create page', async ({ page }) => {
		await page.goto('/todo/create');
		await expect(page).toHaveURL(/\/todo\/create\/?/);
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

		// Click cancel button (use specific locator for Cancel link with .px-4 class)
		const cancelButton = page.locator('a[href="/todo/"].px-4');
		await expect(cancelButton).toBeVisible();
		await expect(cancelButton).toHaveText('Cancel');
		await cancelButton.click();

		// Verify navigation to list page
		await expect(page).toHaveURL('/todo/');
	});

	test('should display loading state during creation', async ({ page }) => {
		// Mock slow API response to verify loading state
		await page.route('/api/todos/', async (route) => {
			await route.fulfill({
				status: 201,
				json: { id: 1, prompt: 'Test prompt', status: 'waiting' },
				delay: 500 // Add delay to ensure loading state is visible
			});
		});

		await page.goto('/todo/create');

		// Enter prompt
		const promptInput = page.locator('#prompt');
		await promptInput.fill('Test prompt');

		// Click Create button
		const createButton = page.locator('button[type="submit"]');
		await createButton.click();

		// Verify loading state is displayed - wait for the loading state to appear
		await expect(createButton).toHaveText('Creating...', { timeout: 2000 });
		await expect(createButton).toBeDisabled();

		// Wait for loading to complete and verify redirect
		await expect(page).toHaveURL('/todo/', { timeout: 10000 });
	});

	test('should take snapshot after page is stable', async ({ page }) => {
		await page.goto('/todo/create');

		// Wait for all elements to be visible and stable
		const promptInput = page.locator('#prompt');
		const workdirInput = page.locator('#workdir');
		const agentInput = page.locator('#agent');
		const statusSelect = page.locator('#status');
		const createButton = page.locator('button[type="submit"]');
		const cancelButton = page.locator('a[href="/todo/"].px-4');

		await expect(promptInput).toBeVisible();
		await expect(workdirInput).toBeVisible();
		await expect(agentInput).toBeVisible();
		await expect(statusSelect).toBeVisible();
		await expect(createButton).toBeVisible();
		await expect(cancelButton).toBeVisible();

		// Take HTML snapshot
		const main = page.locator('main');
		await expect(main).toBeVisible();
		const html = await main.innerHTML();
		expect(html).toMatchSnapshot('todo-create.html');
	});
});
