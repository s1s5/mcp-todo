<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';

	interface TodoList {
		id: number;
		name: string;
		workdir: string;
		created_at: string;
		updated_at: string;
	}

	interface Todo {
		id: number;
		todo_list: number;
		agent: number | null;
		agent_name: string | null;
		prompt: string;
		status: string;
		created_at: string;
		updated_at: string;
		branch_name: string | null;
	}

	let todolist: TodoList | null = $state(null);
	let todos: Todo[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	// URLパラメータからtodolist IDを取得
	const todolistId = $derived($page.params.todolist);

	async function fetchTodoListDetail() {
		loading = true;
		error = '';
		try {
			// todolistの詳細を取得
			const res = await fetch(`/api/todolists/${todolistId}/`);
			if (!res.ok) throw new Error('Failed to fetch todolist');
			todolist = await res.json();

			// 関連するtodosを取得
			const todosRes = await fetch(`/api/todos/?todo_list=${todolistId}&order_by=-updated_at`);
			if (!todosRes.ok) throw new Error('Failed to fetch todos');
			todos = await todosRes.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'waiting': return 'bg-cyan-100 text-cyan-800';
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
		fetchTodoListDetail();
	});
</script>

<div class="p-6 max-w-4xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/todolist"
			id="back-link"
			aria-label="Back to todo list"
			class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		</a>
		<h1 class="text-2xl font-bold">TodoList Details</h1>
		{#if todolist}
			<a
				href="/todolist/{todolist.id}/update"
				id="update-link"
				class="px-3 py-1.5 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition"
			>
				Update
			</a>
			<a
				href="/todolist/{todolist.id}/delete"
				id="delete-link"
				class="px-3 py-1.5 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition"
			>
				Delete
			</a>
		{/if}
		<button
			onclick={fetchTodoListDetail}
			id="refresh-button"
			class="ml-auto px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
		>
			Refresh
		</button>
	</div>

	{#if loading}
		<p id="loading-indicator" class="text-gray-500">Loading...</p>
	{:else if error}
		<p class="text-red-500">{error}</p>
	{:else if !todolist}
		<p class="text-gray-500">TodoList not found.</p>
	{:else}
		<!-- TodoList Details Card -->
		<div class="bg-white shadow rounded-lg overflow-hidden mb-6">
			<div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
				<h2 class="text-lg font-semibold text-gray-900">Information</h2>
			</div>
			<div class="p-6">
				<dl class="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
					<div>
						<dt class="text-sm font-medium text-gray-500">ID</dt>
						<dd class="mt-1 text-sm text-gray-900">{todolist.id}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Name</dt>
						<dd class="mt-1 text-sm text-gray-900">{todolist.name || '-'}</dd>
					</div>
					<div class="sm:col-span-2">
						<dt class="text-sm font-medium text-gray-500">Workdir</dt>
						<dd class="mt-1 text-sm text-gray-900 font-mono">{todolist.workdir}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Created</dt>
						<dd class="mt-1 text-sm text-gray-900">{new Date(todolist.created_at).toLocaleString()}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Updated</dt>
						<dd class="mt-1 text-sm text-gray-900">{new Date(todolist.updated_at).toLocaleString()}</dd>
					</div>
				</dl>
			</div>
		</div>

		<!-- Related Todos -->
		<div class="bg-white shadow rounded-lg overflow-hidden">
			<div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
				<h2 class="text-lg font-semibold text-gray-900">Related Todos ({todos.length})</h2>
			</div>
			{#if todos.length === 0}
				<p class="p-6 text-gray-500">No todos found for this list.</p>
			{:else}
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
									Updated
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
										{new Date(todo.updated_at).toLocaleString()}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
	{/if}
</div>
