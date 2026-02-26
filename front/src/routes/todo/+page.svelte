<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { toast } from '@zerodevx/svelte-toast';
    import { browser } from "$app/environment";

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
	let pollInterval: ReturnType<typeof setInterval> | null = $state(null);
	
	// タイトル通知用
	let originalTitle = 'Todos';
	let hasNotification = $state(false);
	
	// ページネーション用
	let totalCount = $state(0);
	let currentPage = $state(1);
	let totalPages = $state(1);
	let pageSize = $state(50);  // 初期値、画面サイズに基づいて動的に計算

	// 画面サイズに基づいてpageSizeを計算する関数
	function calculatePageSize(): number {
		const headerHeight = 200;  // ヘッダー+Pagination部分
		const rowHeight = 57;       // 1行の高さ（固定）
		const availableHeight = window.innerHeight - headerHeight;
		const calculated = Math.floor(availableHeight / rowHeight);
		
		// 最低10件、最高50件
		return Math.max(10, Math.min(50, calculated));
	}

	// Waiting状態のタスク数を監視
	let waitingTodosCount = $derived(todos.filter(t => t.status === 'waiting').length);

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

	// ステータスフィルタをURLから取得
	function getStatusFromURL(): string {
		return $page.url.searchParams.get('status') || '';
	}

	// ページ移動関数
	function goToPage(pageNum: number) {
		const url = new URL($page.url);
		if (filterStatus) {
			url.searchParams.set('status', filterStatus);
		} else {
			url.searchParams.delete('status');
		}
		if (pageNum <= 1) {
			url.searchParams.delete('page');
		} else {
			url.searchParams.set('page', String(pageNum));
		}
		window.location.href = url.toString();
	}

	async function fetchTodos(updateUrl: boolean = false) {
		loading = true;
		error = '';
		newTodosDetected = false;
		try {
			let url = `/api/todos/?order_by=-updated_at&limit=${pageSize}&offset=${(currentPage - 1) * pageSize}`;
			if (filterStatus) {
				url += `&status=${filterStatus}`;
			}
			// Update URL without reload
			if (updateUrl) {
				const urlObj = new URL($page.url);
				if (filterStatus) {
					urlObj.searchParams.set('status', filterStatus);
				} else {
					urlObj.searchParams.delete('status');
				}
				history.pushState({}, '', urlObj.toString());
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

	// Silent fetch for polling - updates existing todos and adds new ones if they fit on current page
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
				// 新しいtodoが検出された場合は常にタイトル通知を表示
				hasNotification = true;
				updateTitleNotification();
			}

			// Update existing todos by ID, preserve current order
			const existingTodos = todos.map(todo => {
				const fetched = fetchedTodos.find(t => t.id === todo.id);
				return fetched || todo;
			});

			// Add new todos that fit on the current page (up to pageSize)
			// Only add new todos if tab is hidden (document.hidden === true)
			const existingIds = existingTodos.map(t => t.id);
			let newTodosToAdd: Todo[] = [];
			if (document.hidden) {
				newTodosToAdd = fetchedTodos
					.filter(t => !existingIds.includes(t.id))
					.slice(0, pageSize - existingTodos.length);
			}

			// Merge existing and new todos, sorted by updated_at
			const mergedTodos = [...existingTodos, ...newTodosToAdd].sort((a, b) =>
				new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
			);

			todos = mergedTodos;
			currentTodoIds = mergedTodos.map(t => t.id);
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
			toast.push('Failed to start todo');
		}
	}

	async function cancelTodo(id: number) {
		// 楽観的UI更新: ローカルstateを即座に更新
		const previousStatus = todos.find(t => t.id === id)?.status;
		todos = todos.map(todo => 
			todo.id === id ? { ...todo, status: todo.status === 'queued' ? 'waiting' : 'cancelled' } : todo
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
			toast.push('Failed to cancel todo');
		}
	}

	// 全てのwaiting状態のタスクを順番にstartする
	async function startAllWaiting() {
		const waitingTodos = todos.filter(t => t.status === 'waiting');
		for (const todo of waitingTodos) {
			await startTodo(todo.id);
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

	// タイトル通知を更新する関数
	function updateTitleNotification() {
		if (hasNotification) {
			document.title = '● 未確認の変更 - Todos';
		} else {
			document.title = originalTitle;
		}
	}

	onMount(() => {
		pageSize = calculatePageSize();  // 画面サイズに基づいてpageSizeを計算
		currentPage = getPageFromURL();
		filterStatus = getStatusFromURL();
		fetchTodos();
		// Start polling every 5 seconds
		pollInterval = setInterval(fetchTodosSilent, 5000);
		// タブの可視状態変更を監視
		document.addEventListener('visibilitychange', () => {
			if (!document.hidden) {
				// タブが前面に表示された → タイトルをリセットして最新データを取得
				hasNotification = false;
				updateTitleNotification();
				fetchTodos();
			}
		});
	});

	onDestroy(() => {
		if (pollInterval) {
			clearInterval(pollInterval);
		}
        if (browser) {
		  document.removeEventListener('visibilitychange', () => {});
        }
	});
</script>

<div class="p-6 max-w-6xl mx-auto" id="todo-page">
	<a href="/" class="text-blue-600 hover:text-blue-800 mb-4 inline-block" id="back-link">← 戻る</a>
	
	<div class="flex justify-between items-center mb-6">
		<h1 class="text-2xl font-bold" id="todo-title">Todos</h1>
		<div class="flex gap-4 items-center">
			<select
				bind:value={filterStatus}
				onchange={() => { currentPage = 1; fetchTodos(true); }}
				class="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
			>
				<option value="">All Status</option>
				{#each statuses.slice(1) as status}
					<option value={status}>{status}</option>
				{/each}
			</select>
			{#if waitingTodosCount > 0}
				<button
					onclick={startAllWaiting}
					class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition"
				>
					全WaitingをStart ({waitingTodosCount})
				</button>
			{/if}
			<button
				onclick={() => fetchTodos()}
				aria-label="Refresh todo list"
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
		<p class="text-gray-500" id="loading">Loading...</p>
	{:else if todos.length === 0}
		<p class="text-gray-500" id="no-todos">No Todos found.</p>
	{:else}
		<div class="bg-white shadow rounded-lg overflow-hidden" id="todo-table">
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
								List
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Title
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
									{#if todo.todo_list_name}
										{todo.todo_list_name}
									{:else if todo.workdir}
										{todo.workdir.split('/').pop()}
									{:else}-{/if}
								</td>
							<td class="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title={todo.prompt}>
									{todo.title && todo.title.trim() !== '' ? todo.title : (todo.prompt ? todo.prompt.substring(0, 50) + (todo.prompt.length > 50 ? '...' : '') : '-')}
								</td>
								<td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
									{todo.branch_name || '-'}
								</td>
								<td class="px-4 py-4 whitespace-nowrap text-sm">
									<div class="flex gap-2" role="presentation" onclick={(e) => e.stopPropagation()}>
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
