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

	// worktree一覧取得用
	let worktrees: { path: string; branch: string }[] = $state([]);
	let loadingWorktrees = $state(false);
	let worktreeError = $state('');

	// 追加フォーム用
	let showBranchAddForm = $state(false);
	let newBranchName = $state('');
	let newBranchBranch = $state('');
	let creatingBranch = $state(false);
	let branchError = $state('');

	let newWorktreeName = $state('');
	let newWorktreeBranch = $state('');
	let creatingWorktree = $state(false);
	let showAddForm = $state(false);

	// ブランチ選択用
	let branches: string[] = $state([]);
	let loadingBranches = $state(false);

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
		fetchWorktrees();
		fetchBranches();
	});

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

	// ブランチを作成
	async function createBranch() {
		if (!newBranchName.trim() || !newBranchBranch.trim()) return;
		creatingBranch = true;
		branchError = '';
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todolists/${todolistId}/create_branch/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				body: JSON.stringify({
					name: newBranchName.trim(),
					base_branch: newBranchBranch.trim()
				})
			});
			if (!res.ok) throw new Error('Failed to create branch');
			// 成功后、ブランチ一覧を再取得
			await fetchBranches();
			// フォームをリセット
			newBranchName = '';
			newBranchBranch = '';
			showBranchAddForm = false;
		} catch (e) {
			branchError = e instanceof Error ? e.message : 'Failed to create branch';
		} finally {
			creatingBranch = false;
		}
	}

	// ブランチ一覧を取得
	async function fetchBranches() {
		loadingBranches = true;
		try {
			const res = await fetch(`/api/todolists/${todolistId}/branches/`);
			if (!res.ok) throw new Error('Failed to fetch branches');
			branches = await res.json();
		} catch (e) {
			console.error('Failed to fetch branches:', e);
			branches = [];
		} finally {
			loadingBranches = false;
		}
	}

	// worktree一覧を取得
	async function fetchWorktrees() {
		loadingWorktrees = true;
		worktreeError = '';
		try {
			const res = await fetch(`/api/todolists/${todolistId}/worktrees/`);
			if (!res.ok) throw new Error('Failed to fetch worktrees');
			const data = await res.json();
			worktrees = data.worktrees || [];
		} catch (e) {
			worktreeError = e instanceof Error ? e.message : 'Failed to load worktrees';
			worktrees = [];
		} finally {
			loadingWorktrees = false;
		}
	}

	// worktreeを作成
	async function createWorktree() {
		if (!newWorktreeName.trim() || !newWorktreeBranch.trim()) return;
		creatingWorktree = true;
		worktreeError = '';
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todolists/${todolistId}/worktrees/add/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				body: JSON.stringify({
					name: newWorktreeName.trim(),
					branch: newWorktreeBranch.trim()
				})
			});
			if (!res.ok) throw new Error('Failed to create worktree');
			// 成功后、worktreesを再取得
			await fetchWorktrees();
			// フォームをリセット
			newWorktreeName = '';
			newWorktreeBranch = '';
			showAddForm = false;
		} catch (e) {
			worktreeError = e instanceof Error ? e.message : 'Failed to create worktree';
		} finally {
			creatingWorktree = false;
		}
	}

	// worktreeを削除
	async function deleteWorktree(name: string) {
		if (!name) return;
		worktreeError = '';
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todolists/${todolistId}/worktrees/${name}/`, {
				method: 'DELETE',
				headers: {
					'X-CSRFToken': csrfToken
				}
			});
			if (!res.ok) throw new Error('Failed to delete worktree');
			// 成功后、worktreesを再取得
			await fetchWorktrees();
		} catch (e) {
			worktreeError = e instanceof Error ? e.message : 'Failed to delete worktree';
		}
	}
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
					<div class="sm:col-span-2">
						<dt class="text-sm font-medium text-gray-500">Branches</dt>
						<dd class="mt-1 text-sm text-gray-900 mb-4">
							{#if branchError}
								<p class="text-red-500 mb-2">{branchError}</p>
							{/if}

							{#if showBranchAddForm}
								<div class="flex gap-2 items-center mb-2">
									<input
										type="text"
										bind:value={newBranchName}
										placeholder="新しいブランチ名"
										disabled={creatingBranch}
										class="px-2 py-1 text-sm border border-gray-300 rounded font-mono"
									/>
									<input
										type="text"
										bind:value={newBranchBranch}
										placeholder="ベースのブランチ"
										disabled={creatingBranch}
										list="branch-list-for-create"
										class="px-2 py-1 text-sm border border-gray-300 rounded font-mono"
									/>
									<datalist id="branch-list-for-create">
										{#each branches as branch}
											<option value={branch}>{branch}</option>
										{/each}
									</datalist>
									<button
										onclick={createBranch}
										disabled={creatingBranch || !newBranchName.trim() || !newBranchBranch.trim()}
										class="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
									>
										{creatingBranch ? '作成中...' : '作成'}
									</button>
									<button
										onclick={() => showBranchAddForm = false}
										class="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
									>
										キャンセル
									</button>
								</div>
							{:else}
								<button
									onclick={() => showBranchAddForm = true}
									class="mb-2 px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
								>
									+ 新規作成
								</button>
							{/if}

							{#if loadingBranches}
								<p class="text-gray-500">Loading...</p>
							{:else if branches.length > 0}
								<ul class="space-y-1">
									{#each branches as branch}
										<li class="bg-gray-50 px-2 py-1 rounded font-mono">
											{branch}
										</li>
									{/each}
								</ul>
							{:else}
								<p class="text-gray-500">ブランチがありません</p>
							{/if}
						</dd>
					</div>
					<div class="sm:col-span-2">
						<dt class="text-sm font-medium text-gray-500">Worktrees</dt>
						<dd class="mt-1 text-sm text-gray-900">
							{#if worktreeError}
								<p class="text-red-500">{worktreeError}</p>
							{:else if loadingWorktrees && worktrees.length === 0}
								<p class="text-gray-500">Loading...</p>
							{:else if worktrees.length > 0}
								<ul class="space-y-1 mb-2">
									{#each worktrees as wt}
										<li class="flex items-center justify-between bg-gray-50 px-2 py-1 rounded">
											<span class="font-mono">{wt.path} ({wt.branch})</span>
											{#if todolist && wt.path !== todolist.workdir}
												<button
													onclick={() => deleteWorktree(wt.path.split('/').pop() || '')}
													class="text-red-600 hover:text-red-800 text-xs"
												>
													削除
												</button>
											{/if}
										</li>
									{/each}
								</ul>
							{:else}
								<p class="text-gray-500 mb-2">worktreeがありません</p>
							{/if}
							
							{#if showAddForm}
								<div class="flex gap-2 items-center mt-2">
									<input
										type="text"
										bind:value={newWorktreeName}
										placeholder="ディレクトリ名"
										disabled={creatingWorktree}
										class="px-2 py-1 text-sm border border-gray-300 rounded font-mono"
									/>
									<input
										type="text"
										bind:value={newWorktreeBranch}
										placeholder="ブランチ名"
										disabled={creatingWorktree}
										list="branch-list"
										class="px-2 py-1 text-sm border border-gray-300 rounded font-mono"
									/>
									<datalist id="branch-list">
										{#each branches as branch}
											<option value={branch}>{branch}</option>
										{/each}
									</datalist>
									<button
										onclick={createWorktree}
										disabled={creatingWorktree || !newWorktreeName.trim() || !newWorktreeBranch.trim()}
										class="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
									>
										{creatingWorktree ? '作成中...' : '作成'}
									</button>
									<button
										onclick={() => showAddForm = false}
										class="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
									>
										キャンセル
									</button>
								</div>
							{:else}
								<button
									onclick={() => showAddForm = true}
									class="mt-2 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
								>
									+ 追加
								</button>
							{/if}
						</dd>
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
