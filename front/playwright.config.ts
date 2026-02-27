import { defineConfig } from '@playwright/test';
import dotenv from 'dotenv';
import getPort from 'get-port';
dotenv.config({ path: '.env.test' });
const port = await getPort();

export default defineConfig({
	webServer: { command: `npm run build && npm run preview -- --port ${port}`, port },
	testDir: 'e2e',
	/* Use fixed timezone to ensure consistent datetime formatting in snapshots */
	use: {
		timezoneId: 'Asia/Tokyo',
	},
});
