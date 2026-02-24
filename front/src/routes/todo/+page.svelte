<script lang="ts">
	import { onMount } from 'svelte';

	interface Todo {
		id: number;
		todo_list: number;
		agent: number | null;
		agent_name: string | null;
		ref_files: string[];
		edit_files: string[];
		prompt: string;
		context: string;
		status: string;
		output: string | null;
		validation_command: string | null;
		timeout: number;
		created_at: string;
		updated_at: string;
		branch_name: string | null;
	}

	let todos: Todo[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let filterStatus = $state('');
	let processingId = $state<number | null>(null);

	const statuses = ['', 'waiting', 'queued', 'running', 'completed', 'error', 'cancelled', 'timeout'];

	// CSRFトークンを取得する関数
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

	async function fetchTodos() {
		loading = true;
		error = '';
		try {
			let url = '/api/todos/?order_by=-updated_at';
			if (filterStatus) {
				url += `&status=${filterStatus}`;
			}
			const res = await fetch(url);
			if (!res.ok) throw new Error('Failed to fetch');
			todos = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function startTodo(id: number) {
		processingId = id;
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todos/${id}/start/`, {
				method: 'POST',
				headers: {
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin'
			});
			if (!res.ok) throw new Error('Failed to start');
			await fetchTodos();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start todo';
		} finally {
			processingId = null;
		}
	}

	async function cancelTodo(id: number) {
		processingId = id;
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todos/${id}/cancel/`, {
				method: 'POST',
				headers: {
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin'
			});
			if (!res.ok) throw new Error('Failed to cancel');
			await fetchTodos();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to cancel todo';
		} finally {
			processingId = null;
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'waiting': return 'bg-gray-100 text-gray-800';
			case 'queued': return 'bg-blue-100 text-blue-800';
			case 'running': return 'bg-yellow-100 text-yellow-800';
			case 'completed': return 'bg-green-100 text-green-800';
			case 'error': return 'bg-red-100 text-red-800';
			case 'cancelled': return 'bg-gray-100 text-gray-600';
			case 'timeout': return 'bg-orange-100 text-orange-800';
			default: return 'bg-gray-100 text-gray-800';
		}
	}

	onMount(() => {
		fetchTodos();
	});
</script>

<div class="p-6 max-w-6xl mx-auto">
	<a href="/" class="text-blue-600 hover:text-blue-800 mb-4 inline-block">← Back to Home</a>
	
	<div class="flex justify-between items-center mb-6">
		<h1 class="text-2xl font-bold">Todos</h1>
		<div class="flex gap-4 items-center">
			<select
				bind:value={filterStatus}
				onchange={fetchTodos}
				class="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
			>
				<option value="">All Status</option>
				{#each statuses.slice(1) as status}
					<option value={status}>{status}</option>
				{/each}
			</select>
			<button
				onclick={fetchTodos}
				class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
			>
				Refresh
			</button>
		</div>
	</div>

	{#if error && !processingId}
		<p class="text-red-500 mb-4">{error}</p>
	{/if}

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if todos.length === 0}
		<p class="text-gray-500">No Todos found.</p>
	{:else}
		<div class="bg-white shadow rounded-lg overflow-hidden">
			<div class="overflow-x-auto">
				<table class="min-w-full divide-y divide-gray-200">
					<thead class="bg-gray-50">
						<tr>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								ID
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Status
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Agent
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Prompt
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Branch
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Actions
							</th>
						</tr>
					</thead>
					<tbody class="bg-white divide-y divide-gray-200">
						{#each todos as todo}
							<tr
								class="hover:bg-gray-50 cursor-pointer"
								onclick={() => window.location.href = `/todo/${todo.id}`}
							>
								<td class="px-4 py-4 whitespace-nowrap text-sm">
									<a href="/todo/{todo.id}" class="text-blue-600 hover:text-blue-800 font-medium" onclick={(e) => e.stopPropagation()}>
										{todo.id}
									</a>
								</td>
								<td class="px-4 py-4 whitespace-nowrap">
									<span class="px-2 py-1 text-xs font-medium rounded-full {getStatusColor(todo.status)}">
										{todo.status}
									</span>
								</td>
								<td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
									{todo.agent_name || '-'}
								</td>
								<td class="px-4 py-4 text-sm text-gray-500 max-w-xs truncate" title={todo.prompt}>
									{todo.prompt || '-'}
								</td>
								<td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
									{todo.branch_name || '-'}
								</td>
								<td class="px-4 py-4 whitespace-nowrap text-sm">
									<div class="flex gap-2" onclick={(e) => e.stopPropagation()}>
										{#if todo.status === 'waiting'}
											<button
												onclick={() => startTodo(todo.id)}
												disabled={processingId === todo.id}
												class="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition disabled:opacity-50"
											>
												{processingId === todo.id ? 'Starting...' : 'Start'}
											</button>
										{/if}
										{#if todo.status === 'waiting' || todo.status === 'queued'}
											<button
												onclick={() => cancelTodo(todo.id)}
												disabled={processingId === todo.id}
												class="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 transition disabled:opacity-50"
											>
												{processingId === todo.id ? 'Cancelling...' : 'Cancel'}
											</button>
										{/if}
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
