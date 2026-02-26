import { expect, test } from '@playwright/test';

test.describe('TodoList Create Page', () => {
	test('should navigate to create page', async ({ page }) => {
		await page.goto('/todolist/create');
		await expect(page).toHaveURL('/todolist/create/');
	});

	test('should display empty workdir field and Create button', async ({ page }) => {
		await page.goto('/todolist/create');

		// Verify workdir input is empty
		const workdirInput = page.locator('#workdir');
		await expect(workdirInput).toBeVisible();
		await expect(workdirInput).toHaveValue('');

		// Verify Create button exists
		const createButton = page.locator('button[type="submit"]');
		await expect(createButton).toBeVisible();
		await expect(createButton).toHaveText('Create');
	});

	test('should redirect to list after successful creation', async ({ page }) => {
		// Mock successful API response
		await page.route('/api/todolists/', async (route) => {
			await route.fulfill({
				status: 201,
				json: { id: 1, workdir: '/home/user/test', name: 'test' }
			});
		});

		await page.goto('/todolist/create');

		// Enter workdir
		const workdirInput = page.locator('#workdir');
		await workdirInput.fill('/home/user/test');

		// Click Create button
		const createButton = page.locator('button[type="submit"]');
		await createButton.click();

		// Verify redirect to list page
		await expect(page).toHaveURL('/todolist/');
	});

	test('should navigate to list on cancel button click', async ({ page }) => {
		await page.goto('/todolist/create');

		// Click cancel button
		const cancelButton = page.getByRole('link', { name: 'Cancel' });
		await expect(cancelButton).toBeVisible();
		await cancelButton.click();

		// Verify navigation to list page
		await expect(page).toHaveURL('/todolist/');
	});

	test('should display error message on server error', async ({ page }) => {
		// Mock error response
		await page.route('/api/todolists/', async (route) => {
			await route.fulfill({
				status: 500,
				json: { detail: 'Internal server error' }
			});
		});

		await page.goto('/todolist/create');

		// Enter workdir
		const workdirInput = page.locator('#workdir');
		await workdirInput.fill('/home/user/test');

		// Click Create button
		const createButton = page.locator('button[type="submit"]');
		await createButton.click();

		// Wait for loading to complete
		await expect(createButton).toHaveText('Create');

		// Verify error message is displayed
		const errorMessage = page.locator('#error-message');
		await expect(errorMessage).toBeVisible();
		await expect(errorMessage).toContainText('Internal server error');
	});
});
