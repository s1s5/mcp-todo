<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	interface TodoList {
		id: number;
		name: string;
		workdir: string;
		created_at: string;
		updated_at: string;
	}

	let todolist: TodoList | null = $state(null);
	let name = $state('');
	let workdir = $state('');
	let loading = $state(true);
	let submitting = $state(false);
	let error = $state('');

	// URLパラメータからtodolist IDを取得
	const todolistId = $derived($page.params.todolist);

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

	async function fetchTodoList() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`/api/todolists/${todolistId}/`);
			if (!res.ok) throw new Error('Failed to fetch TodoList');
			const data = await res.json();
			todolist = data;
			name = data.name;
			workdir = data.workdir;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = '';
		submitting = true;

		try {
			const res = await fetch(`/api/todolists/${todolistId}/`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': getCSRFToken()
				},
				body: JSON.stringify({ name, workdir })
			});

			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || 'Failed to update TodoList');
			}

			await goto(`/todolist/${todolistId}/`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			submitting = false;
		}
	}

	onMount(() => {
		fetchTodoList();
	});
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="flex items-center mb-6">
		<a
			href="/todolist/{todolistId}/"
			class="text-blue-600 hover:text-blue-800 flex items-center gap-1"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
				<path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
			</svg>
			Back
		</a>
	</div>

	<h1 class="text-2xl font-bold mb-6">Edit TodoList</h1>

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if error && !todolist}
		<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
			{error}
		</div>
	{:else if error}
		<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
			{error}
		</div>
	{/if}

	{#if todolist}
		<form onsubmit={handleSubmit} class="bg-white shadow rounded-lg p-6">
			<div class="mb-4">
				<label for="name" class="block text-sm font-medium text-gray-700 mb-2">
					Name
				</label>
				<input
					type="text"
					id="name"
					bind:value={name}
					placeholder="TodoList name"
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

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
					href="/todolist/{todolistId}/"
					class="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition"
				>
					Cancel
				</a>
				<button
					type="submit"
					disabled={submitting}
					class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{submitting ? 'Saving...' : 'Save'}
				</button>
			</div>
		</form>
	{/if}
</div>
