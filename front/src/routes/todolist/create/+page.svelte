<script lang="ts">
	import { goto } from '$app/navigation';

	let workdir = $state('');
	let error = $state('');
	let loading = $state(false);

	function getCSRFToken(): string {
		const name = 'csrftoken';
		let cookieValue = '';
		if (document.cookie && document.cookie !== '') {
			const cookies = document.cookie.split(';');
			for (let i = 0; i < cookies.length; i++) {
				const cookie = cookies[i].trim();
				if (cookie.substring(0, name.length + 1) === (name + '=')) {
					cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
					break;
				}
			}
		}
		return cookieValue;
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = '';
		loading = true;

		try {
			const res = await fetch('/api/todolists/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': getCSRFToken()
				},
				body: JSON.stringify({ workdir })
			});

			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || 'Failed to create TodoList');
			}

			await goto('/todolist/');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="flex items-center mb-6">
		<a
			href="/todolist/"
			class="text-blue-600 hover:text-blue-800 flex items-center gap-1"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
				<path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
			</svg>
			Back
		</a>
	</div>

	<h1 class="text-2xl font-bold mb-6">Create TodoList</h1>

	{#if error}
		<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
			{error}
		</div>
	{/if}

	<form onsubmit={handleSubmit} class="bg-white shadow rounded-lg p-6">
		<div class="mb-4">
			<label for="workdir" class="block text-sm font-medium text-gray-700 mb-2">
				Workdir
			</label>
			<input
				type="text"
				id="workdir"
				bind:value={workdir}
				required
				placeholder="/path/to/workdir"
				class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
			/>
		</div>

		<div class="flex justify-end gap-3">
			<a
				href="/todolist/"
				class="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition"
			>
				Cancel
			</a>
			<button
				type="submit"
				disabled={loading}
				class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{loading ? 'Creating...' : 'Create'}
			</button>
		</div>
	</form>
</div>
