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

	const statuses = ['', 'waiting', 'queued', 'running', 'completed', 'error', 'cancelled', 'timeout'];

	async function fetchTodos() {
		loading = true;
		error = '';
		try {
			let url = '/api/todos/';
			if (filterStatus) {
				url += `?status=${filterStatus}`;
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

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if error}
		<p class="text-red-500">{error}</p>
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
								Created
							</th>
						</tr>
					</thead>
					<tbody class="bg-white divide-y divide-gray-200">
						{#each todos as todo}
							<tr class="hover:bg-gray-50">
								<td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
									{todo.id}
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
								<td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
									{new Date(todo.created_at).toLocaleString()}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
