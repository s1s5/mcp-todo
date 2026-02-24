<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { toast } from '@zerodevx/svelte-toast';

	interface Todo {
		id: number;
		todo_list: number;
		agent: number | null;
		agent_name: string | null;
		ref_files: string[];
		edit_files: string[];
		todo_list_name: string | null;
		workdir: string | null;
		prompt: string;
		title: string;
		context: string;
		status: string;
		output: string | null;
		validation_command: string | null;
		timeout: number;
		created_at: string;
		updated_at: string;
		branch_name: string | null;
	}

	interface TodoResponse {
		count: number;
		next: string | null;
		previous: string | null;
		results: Todo[];
	}

	let todos: Todo[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let filterStatus = $state('');
	let newTodosDetected = $state(false);
	let currentTodoIds: number[] = $state([]);
	let pollInterval: ReturnType<typeof setInterval> | null = null;
	
	// ページネーション用
	let totalCount = $state(0);
	let currentPage = $state(1);
	let totalPages = $state(1);
	const pageSize = 50;

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

	// ページ番号をURLから取得（初期化のみ）
	function getPageFromURL(): number {
		return Number($page.url.searchParams.get('page')) || 1;
	}

	// ページ移動関数
	function goToPage(pageNum: number) {
		const url = new URL($page.url);
		if (pageNum <= 1) {
			url.searchParams.delete('page');
		} else {
			url.searchParams.set('page', String(pageNum));
		}
		window.location.href = url.toString();
	}

	async function fetchTodos() {
		loading = true;
		error = '';
		newTodosDetected = false;
		try {
			let url = `/api/todos/?order_by=-updated_at&limit=${pageSize}&offset=${(currentPage - 1) * pageSize}`;
			if (filterStatus) {
				url += `&status=${filterStatus}`;
			}
			const res = await fetch(url);
			if (!res.ok) throw new Error('Failed to fetch');
			const data: TodoResponse = await res.json();
			todos = data.results;
			totalCount = data.count;
			totalPages = Math.ceil(totalCount / pageSize);
			// Update current todo IDs
			currentTodoIds = todos.map(t => t.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	// Silent fetch for polling - updates existing todos without adding new ones
	async function fetchTodosSilent() {
		if (loading) return; // Don't poll during initial load
		try {
			// ポーリング時は現在表示中のページのデータを取得
			let url = `/api/todos/?order_by=-updated_at&limit=${pageSize}&offset=${(currentPage - 1) * pageSize}`;
			if (filterStatus) {
				url += `&status=${filterStatus}`;
			}
			const res = await fetch(url);
			if (!res.ok) return;
			const data: TodoResponse = await res.json();
			const fetchedTodos = data.results;
			const fetchedIds = fetchedTodos.map(t => t.id);

			// Check for new todos
			const newIds = fetchedIds.filter(id => !currentTodoIds.includes(id));
			if (newIds.length > 0) {
				newTodosDetected = true;
			}

			// Update existing todos by ID, preserve current order
			const updatedTodos = todos.map(todo => {
				const fetched = fetchedTodos.find(t => t.id === todo.id);
				return fetched || todo;
			});
			todos = updatedTodos;
			currentTodoIds = updatedTodos.map(t => t.id);
		} catch (e) {
			// Silent fail - don't show error for background polling
		}
	}

	async function startTodo(id: number) {
		// 楽観的UI更新: ローカルstateを即座に更新
		const previousStatus = todos.find(t => t.id === id)?.status;
		todos = todos.map(todo => 
			todo.id === id ? { ...todo, status: 'queued' } : todo
		);
		
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
		} catch (e) {
			// 失敗時は元のステータスに戻す
			if (previousStatus) {
				todos = todos.map(todo => 
					todo.id === id ? { ...todo, status: previousStatus } : todo
				);
			}
			toast.push('Failed to start todo', { type: 'error' });
		}
	}

	async function cancelTodo(id: number) {
		// 楽観的UI更新: ローカルstateを即座に更新
		const previousStatus = todos.find(t => t.id === id)?.status;
		todos = todos.map(todo => 
			todo.id === id ? { ...todo, status: 'cancelled' } : todo
		);
		
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
		} catch (e) {
			// 失敗時は元のステータスに戻す
			if (previousStatus) {
				todos = todos.map(todo => 
					todo.id === id ? { ...todo, status: previousStatus } : todo
				);
			}
			toast.push('Failed to cancel todo', { type: 'error' });
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
		// URLからページ番号を初期化
		currentPage = getPageFromURL();
		fetchTodos();
		// Start polling every 5 seconds
		pollInterval = setInterval(fetchTodosSilent, 5000);
	});

	onDestroy(() => {
		if (pollInterval) {
			clearInterval(pollInterval);
		}
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
				class="px-4 py-2 rounded transition {newTodosDetected ? 'bg-yellow-400 text-black animate-pulse' : 'bg-blue-600 text-white hover:bg-blue-700'}"
			>
				Refresh
			</button>
		</div>
	</div>

	{#if error}
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
								Title
							</th>
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
								List
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
								<td class="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title={todo.title}>
									{todo.title || '-'}
								</td>
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
								<td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
									{#if todo.todo_list_name}
										{todo.todo_list_name}
									{:else if todo.workdir}
										{todo.workdir.split('/').pop()}
									{:else}-{/if}
								</td>
								<td class="px-4 py-4 text-sm text-gray-500 max-w-xs truncate" title={todo.prompt}>
									{todo.prompt || '-'}
								</td>
								<td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
									{todo.branch_name || '-'}
								</td>
								<td class="px-4 py-4 whitespace-nowrap text-sm">
									<div class="flex gap-2" onclick={(e) => e.stopPropagation()}>
										{#if todo.status === 'waiting' || todo.status === 'error'}
											<button
												onclick={() => startTodo(todo.id)}
												class="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition cursor-pointer"
											>
												{todo.status === 'error' ? 'Retry' : 'Start'}
											</button>
										{/if}
										{#if todo.status === 'waiting' || todo.status === 'queued' || todo.status === 'running'}
											<button
												onclick={() => cancelTodo(todo.id)}
												class="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 transition cursor-pointer"
											>
												Cancel
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
	
		<!-- ページネーション -->
		<div class="mt-4 flex items-center justify-between">
			<p class="text-sm text-gray-600">
				Total: {totalCount} items
			</p>
			<div class="flex items-center gap-2">
				<button
					onclick={() => goToPage(currentPage - 1)}
					disabled={currentPage <= 1}
					class="px-3 py-1 rounded border bg-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
				>
					← Prev
				</button>
				<span class="text-sm text-gray-600">
					{currentPage} / {totalPages}
				</span>
				<button
					onclick={() => goToPage(currentPage + 1)}
					disabled={currentPage >= totalPages}
					class="px-3 py-1 rounded border bg-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
				>
					Next →
				</button>
			</div>
		</div>
	{/if}
</div>
