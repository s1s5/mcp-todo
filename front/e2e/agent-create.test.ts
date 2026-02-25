import { expect, test } from '@playwright/test';

test.describe('Agent Create Page', () => {
	test('should navigate to create page', async ({ page }) => {
		await page.goto('/agent/create');
		await expect(page).toHaveURL('/agent/create');
	});

	test('should display empty name and command fields and Create button', async ({ page }) => {
		await page.goto('/agent/create');

		// Verify name input is empty
		const nameInput = page.locator('#name');
		await expect(nameInput).toBeVisible();
		await expect(nameInput).toHaveValue('');

		// Verify command input has default value
		const commandInput = page.locator('#command');
		await expect(commandInput).toBeVisible();
		await expect(commandInput).toHaveValue('goose run --recipe');

		// Verify Create button exists
		const createButton = page.locator('button[type="submit"]');
		await expect(createButton).toBeVisible();
		await expect(createButton).toHaveText('Create');
	});

	test('should redirect to list after successful creation', async ({ page }) => {
		// Mock successful API response
		await page.route('/api/agents/', async (route) => {
			await route.fulfill({
				status: 201,
				json: {
					id: 1,
					name: 'Test Agent',
					system_message: 'You are a helpful assistant.',
					command: 'goose run --recipe'
				}
			});
		});

		await page.goto('/agent/create');

		// Enter name
		const nameInput = page.locator('#name');
		await nameInput.fill('Test Agent');

		// Enter system message
		const systemMessageInput = page.locator('#systemMessage');
		await systemMessageInput.fill('You are a helpful assistant.');

		// Click Create button
		const createButton = page.locator('button[type="submit"]');
		await createButton.click();

		// Verify redirect to list page
		await expect(page).toHaveURL('/agent/');
	});

	test('should navigate to list on cancel button click', async ({ page }) => {
		await page.goto('/agent/create');

		// Click cancel button
		const cancelButton = page.locator('a[href="/agent/"]');
		await expect(cancelButton).toBeVisible();
		await cancelButton.click();

		// Verify navigation to list page
		await expect(page).toHaveURL('/agent/');
	});

	test('should display error message on server error', async ({ page }) => {
		// Mock error response
		await page.route('/api/agents/', async (route) => {
			await route.fulfill({
				status: 500,
				json: { detail: 'Internal server error' }
			});
		});

		await page.goto('/agent/create');

		// Enter name
		const nameInput = page.locator('#name');
		await nameInput.fill('Test Agent');

		// Enter system message
		const systemMessageInput = page.locator('#systemMessage');
		await systemMessageInput.fill('You are a helpful assistant.');

		// Click Create button
		const createButton = page.locator('button[type="submit"]');
		await createButton.click();

		// Wait for loading to complete
		await expect(createButton).toHaveText('Create');

		// Verify error message is displayed
		const errorMessage = page.locator('.text-red-700');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Internal server error');
	});

	test('should take snapshot after display is stable', async ({ page }) => {
		await page.goto('/agent/create');

		// Wait for form to be visible and stable
		const form = page.locator('form');
		await expect(form).toBeVisible();

		// Wait for input fields to be visible
		const nameInput = page.locator('#name');
		await expect(nameInput).toBeVisible();

		const systemMessageInput = page.locator('#systemMessage');
		await expect(systemMessageInput).toBeVisible();

		const commandInput = page.locator('#command');
		await expect(commandInput).toBeVisible();

		// Wait for Create button to be visible
		const createButton = page.locator('button[type="submit"]');
		await expect(createButton).toBeVisible();

		// Take snapshot
		await expect(page).toHaveScreenshot();
	});
});
