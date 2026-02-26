<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { marked } from 'marked';
	import { page } from '$app/stores';

	interface Todo {
		id: number;
		todo_list: number;
		todo_list_name: string | null;
		agent: number | null;
		agent_name: string | null;
		ref_files: string[];
		edit_files: string[];
		prompt: string;
		title: string | null;
		system_prompt: string | null;
		auto_stash: boolean;
		keep_branch: boolean;
		context: string;
		status: string;
		output: string | null;
		error: string | null;
		validation_command: string | null;
		timeout: number;
		priority: number;
		created_at: string;
		updated_at: string;
		branch_name: string | null;
		started_at: string | null;
		finished_at: string | null;
	}

	let todo: Todo | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let pollInterval: ReturnType<typeof setInterval> | null = null;
	let processingId = $state<number | null>(null);
	let updatingPriority = $state(false);

	// ブランチ選択用 state
	let branches: string[] = $state([]);
	let loadingBranches = $state(false);
	let updatingBranch = $state(false);
	let branchError = $state('');
	let showBranchSelect = $state(false);

	// 新しいブランチ作成用 state
	let newBranchName = $state('');
	let creatingBranch = $state(false);
	let showNewBranchInput = $state(false);

	// worktree選択用 state
	let worktrees: { path: string; branch: string }[] = $state([]);
	let loadingWorktrees = $state(false);
	let worktreeError = $state('');
	let selectedWorktreePath = $state('');
	let changeBranch = $state(false);

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

	async function fetchTodo() {
		loading = true;
		error = '';
		try {
			const todoId = $page.params.todo;
			const res = await fetch(`/api/todos/${todoId}/`);
			if (!res.ok) throw new Error('Failed to fetch');
			todo = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function fetchTodoSilent() {
		if (loading) return;
		try {
			const todoId = $page.params.todo;
			const res = await fetch(`/api/todos/${todoId}/`);
			if (!res.ok) return;
			const data: Todo = await res.json();
			todo = data;
		} catch (e) {
			// Silent fail
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
			await fetchTodo();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start todo';
		} finally {
			processingId = null;
		}
	}

	async function cancelTodo(id: number) {
		// 楽観的UI更新: ローカルstateを即座に更新
		if (todo && todo.id === id) {
			todo.status = todo.status === 'queued' ? 'waiting' : 'cancelled';
		}
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
			await fetchTodo();
		} catch (e) {
			// 失敗時は再取得して元に戻す
			await fetchTodo();
			error = e instanceof Error ? e.message : 'Failed to cancel todo';
		} finally {
			processingId = null;
		}
	}

	async function updatePriority(priority: number) {
		if (!todo) return;
		updatingPriority = true;
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todos/${todo.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin',
				body: JSON.stringify({ priority })
			});
			if (!res.ok) throw new Error('Failed to update priority');
			await fetchTodo();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update priority';
		} finally {
			updatingPriority = false;
		}
	}

	async function fetchBranches() {
		if (!todo) return;
		loadingBranches = true;
		branchError = '';
		try {
			const res = await fetch(`/api/todos/${todo.id}/branches/`);
			if (!res.ok) throw new Error('Failed to fetch branches');
			const data: string[] = await res.json();
			branches = data;
		} catch (e) {
			branchError = e instanceof Error ? e.message : 'Failed to load branches';
			// エラー時はブランチ一覧を空にする（従来通り現在値のみ表示）
			branches = [];
		} finally {
			loadingBranches = false;
		}
	}

	async function updateBranch(newBranch: string) {
		if (!todo) return;
		updatingBranch = true;
		branchError = '';
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todos/${todo.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin',
				body: JSON.stringify({ branch_name: newBranch })
			});
			if (!res.ok) throw new Error('Failed to update branch');
			await fetchTodo();
			showBranchSelect = false;
		} catch (e) {
			branchError = e instanceof Error ? e.message : 'Failed to update branch';
		} finally {
			updatingBranch = false;
		}
	}

	async function createBranch() {
		if (!todo || !newBranchName.trim()) return;
		
		// ブランチ名のバリデーション
		const branchNameRegex = /^[a-zA-Z0-9_-]+$/;
		if (!branchNameRegex.test(newBranchName)) {
			branchError = 'ブランチ名は英数字、ハイフン、アンダースコアのみ使用できます';
			return;
		}
		
		creatingBranch = true;
		branchError = '';
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todos/${todo.id}/create-branch/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin',
				body: JSON.stringify({ new_branch_name: newBranchName.trim() })
			});
			
			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.error || 'Failed to create branch');
			}
			
			const data = await res.json();
			// 正常に作成されたら、ブランチ一覧を更新して新しいブランチを選択状態にする
			await fetchBranches();
			await fetchTodo();
			
			// 新しいブランチ名が返ってきていれば選択状態にする
			if (data.branch_name) {
				// ブランチ選択UIを閉じる
				showBranchSelect = false;
				showNewBranchInput = false;
				newBranchName = '';
			}
		} catch (e) {
			branchError = e instanceof Error ? e.message : 'Failed to create branch';
		} finally {
			creatingBranch = false;
		}
	}

	function handleSelectNewBranch() {
		showNewBranchInput = true;
	}

	function cancelNewBranch() {
		showNewBranchInput = false;
		newBranchName = '';
		branchError = '';
	}

	function toggleBranchSelect() {
		if (!showBranchSelect && branches.length === 0 && !loadingBranches) {
			fetchBranches();
		}
		showBranchSelect = !showBranchSelect;
	}

	async function fetchWorktrees() {
		if (!todo) return;
		loadingWorktrees = true;
		worktreeError = '';
		try {
			const res = await fetch(`/api/todos/${todo.id}/worktrees/`);
			if (!res.ok) throw new Error('Failed to fetch worktrees');
			const data: { workdir: string; worktrees: { path: string; branch: string }[] } = await res.json();
			worktrees = data.worktrees;
			// 現在のtodoのworkdirに該当するworktreeを初期選択
			const currentWorkdir = todo.todo_list_name;
			if (currentWorkdir) {
				const matching = worktrees.find(w => w.path === currentWorkdir);
				if (matching) {
					selectedWorktreePath = matching.path;
				} else if (worktrees.length > 0) {
					selectedWorktreePath = worktrees[0].path;
				}
			} else if (worktrees.length > 0) {
				selectedWorktreePath = worktrees[0].path;
			}
		} catch (e) {
			worktreeError = e instanceof Error ? e.message : 'Failed to load worktrees';
			worktrees = [];
		} finally {
			loadingWorktrees = false;
		}
	}

	async function updateWorktree() {
		if (!todo || !selectedWorktreePath) return;
		const selectedWorktree = worktrees.find(w => w.path === selectedWorktreePath);
		if (!selectedWorktree) return;

		loadingWorktrees = true;
		worktreeError = '';
		try {
			const csrfToken = getCSRFToken();
			// TodoListのworkdirを選択したworktreeのpathに更新
			const todoListRes = await fetch(`/api/todo-lists/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin',
				body: JSON.stringify({ workdir: selectedWorktreePath })
			});
			if (!todoListRes.ok) throw new Error('Failed to update workdir');

			// ブランチ変更チェックボックスがオンの場合、branch_nameも更新
			if (changeBranch) {
				const branchRes = await fetch(`/api/todos/${todo.id}/`, {
					method: 'PATCH',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': csrfToken
					},
					credentials: 'same-origin',
					body: JSON.stringify({ branch_name: selectedWorktree.branch })
				});
				if (!branchRes.ok) throw new Error('Failed to update branch');
			}

			// 更新成功后、画面を再読み込み
			await fetchTodo();
		} catch (e) {
			worktreeError = e instanceof Error ? e.message : 'Failed to update worktree';
		} finally {
			loadingWorktrees = false;
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

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleString('ja-JP', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		});
	}

	function formatDuration(startedAt: string | null, finishedAt: string | null): string | null {
		if (!startedAt || !finishedAt) return null;
		const start = new Date(startedAt);
		const end = new Date(finishedAt);
		const diffMs = end.getTime() - start.getTime();
		if (diffMs < 0) return null;
		const totalSeconds = Math.floor(diffMs / 1000);
		const minutes = Math.floor(totalSeconds / 60);
		const seconds = totalSeconds % 60;
		return `${minutes}分${seconds}秒`;
	}

	const terminalStatuses = ['completed', 'error', 'cancelled', 'timeout'];

	function getProcessingTime(todo: Todo): string | null {
		if (!terminalStatuses.includes(todo.status)) return null;
		return formatDuration(todo.started_at, todo.finished_at);
	}

	function getPriorityColor(priority: number): string {
		if (priority <= -5) {
			// 低緊急性 - 薄い青色
			return 'bg-blue-100 text-blue-800';
		} else if (priority > 5) {
			// 高緊急性 - 赤色
			return 'bg-red-100 text-red-800';
		} else {
			// 通常 - 灰色
			return 'bg-gray-100 text-gray-800';
		}
	}

	onMount(async () => {
		await fetchTodo();
		await fetchWorktrees();
		// statusがrunningのときは5秒ごとにポーリング
		pollInterval = setInterval(() => {
			if (todo?.status === 'running' || todo?.status === 'queued') {
				fetchTodoSilent();
			}
		}, 5000);
	});

	onDestroy(() => {
		if (pollInterval) {
			clearInterval(pollInterval);
		}
	});
</script>

<div class="p-6 max-w-4xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/todo"
			class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
		>
			← 戻る
		</a>
		<h1 class="text-2xl font-bold">Todo詳細</h1>
		<div class="flex items-center gap-2 ml-auto">
			{#if todo}
				<a
					href="/todo/{todo.id}/update/"
					class="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition"
				>
					編集
				</a>
				<a
					href="/todo/{todo.id}/delete/"
					class="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition"
				>
					削除
				</a>
			{/if}
		</div>
	</div>

	{#if error}
		<p class="text-red-500 mb-4">{error}</p>
	{/if}

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if todo}
		<div class="bg-white shadow rounded-lg overflow-hidden">
			<div class="px-6 py-4 border-b border-gray-200">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<span class="text-lg font-semibold text-gray-900">ID: {todo.id}</span>
						{#if todo.title}
							<span class="text-lg font-semibold text-gray-700">{todo.title}</span>
						{/if}
					</div>
					<div class="flex items-center gap-2">
						{#if todo.status === 'waiting' || todo.status === 'error'}
							<button
								onclick={() => todo && startTodo(todo.id)}
								disabled={processingId === todo.id}
								class="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition disabled:opacity-50 cursor-pointer"
							>
								{processingId === todo.id ? 'Starting...' : (todo.status === 'error' ? 'Retry' : 'Start')}
							</button>
						{/if}
						{#if todo.status === 'waiting' || todo.status === 'queued' || todo.status === 'running'}
							<button
								onclick={() => todo && cancelTodo(todo.id)}
								disabled={processingId === todo.id}
								class="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition disabled:opacity-50 cursor-pointer"
							>
								{processingId === todo.id ? 'Cancelling...' : 'Cancel'}
							</button>
						{/if}
						<span class="px-3 py-1 text-sm font-medium rounded-full {getStatusColor(todo.status)}">
							{todo.status}
						</span>
						{#if getProcessingTime(todo)}
							<span class="text-sm text-gray-600">
								処理時間: {getProcessingTime(todo)}
							</span>
						{/if}
					</div>
				</div>
			</div>
			<div class="px-6 py-4 space-y-4">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">TodoList</span>
						<p id="todo-list" class="text-gray-900">{todo.todo_list_name || `ID: ${todo.todo_list}`}</p>
					</div>
					{#if todo.status === 'waiting' || todo.status === 'queued'}
						<div>
							<span class="block text-sm font-medium text-gray-500 mb-1">Worktree</span>
							{#if worktreeError}
								<p class="text-red-500 text-sm">{worktreeError}</p>
							{:else if loadingWorktrees && worktrees.length === 0}
								<p class="text-gray-500 text-sm">Loading...</p>
							{:else if worktrees.length > 0}
								<div class="flex flex-col gap-2">
									<select
										bind:value={selectedWorktreePath}
										disabled={loadingWorktrees}
										class="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
									>
										{#each worktrees as wt}
											<option value={wt.path}>{wt.path} ({wt.branch})</option>
										{/each}
									</select>
									<label class="flex items-center gap-1 text-sm text-gray-600">
										<input
											type="checkbox"
											bind:checked={changeBranch}
											class="rounded border-gray-300"
										/>
										ブランチも変更する
									</label>
									<button
										onclick={updateWorktree}
										disabled={loadingWorktrees || !selectedWorktreePath}
										class="w-24 px-2 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50"
									>
										{loadingWorktrees ? '更新中...' : '適用'}
									</button>
								</div>
							{:else}
								<p class="text-gray-500 text-sm">利用可能なworktreeがありません</p>
							{/if}
						</div>
					{/if}
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">Agent</span>
						<p id="agent" class="text-gray-900">{todo.agent_name || (todo.agent ? `ID: ${todo.agent}` : '-')}</p>
					</div>
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">Branch</span>
						<div class="flex items-center gap-2">
							<span id="branch" class="text-gray-900 font-mono">{todo.branch_name || '-'}</span>
							{#if todo.status === 'waiting' || todo.status === 'queued'}
								{#if showBranchSelect}
									{#if showNewBranchInput}
										<div class="flex items-center gap-2">
											<input
												type="text"
												bind:value={newBranchName}
												placeholder="新しいブランチ名"
												disabled={creatingBranch}
												class="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50 font-mono"
											/>
											<button
												onclick={createBranch}
												disabled={creatingBranch || !newBranchName.trim()}
												class="px-2 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition disabled:opacity-50"
											>
												{creatingBranch ? '作成中...' : '作成'}
											</button>
											<button
												onclick={cancelNewBranch}
												disabled={creatingBranch}
												class="px-2 py-1 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
											>
												キャンセル
											</button>
										</div>
									{:else}
										<select
											value={todo.branch_name || ''}
											onchange={(e) => {
												const value = (e.target as HTMLSelectElement).value;
												if (value === '__new_branch__') {
													handleSelectNewBranch();
												} else {
													updateBranch(value);
												}
											}}
											disabled={updatingBranch || loadingBranches}
											class="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
										>
											{#if loadingBranches}
												<option value="">Loading...</option>
											{:else if branches.length > 0}
												{#each branches as branch}
													<option value={branch}>{branch}</option>
												{/each}
												<option value="__new_branch__">新しいブランチを作成...</option>
											{:else}
												<option value="">{todo.branch_name || '-'}</option>
											{/if}
										</select>
										<button
											onclick={() => showBranchSelect = false}
											disabled={updatingBranch}
											class="px-2 py-1 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
										>
											キャンセル
										</button>
									{/if}
								{:else}
									<button
										onclick={toggleBranchSelect}
										class="px-2 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition"
									>
										ブランチ変更
									</button>
								{/if}
							{/if}
						</div>
						{#if branchError}
							<p class="text-red-500 text-sm mt-1">{branchError}</p>
						{/if}
					</div>
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">Timeout</span>
						<p id="timeout" class="text-gray-900">{todo.timeout}秒</p>
					</div>
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">自動スタッシュ</span>
						<p id="auto-stash" class="text-gray-900">{todo.auto_stash ? 'はい' : 'いいえ'}</p>
					</div>
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">ブランチ保持</span>
						<p id="keep-branch" class="text-gray-900">{todo.keep_branch ? 'はい' : 'いいえ'}</p>
					</div>
					<div class="md:col-span-2">
						<span class="block text-sm font-medium text-gray-500 mb-1">優先度</span>
						<div role="group" class="flex items-center gap-2">
							<span class="px-3 py-1 text-sm font-medium rounded-full {getPriorityColor(todo.priority)}">
								{todo.priority}
							</span>
							{#if todo.status === 'waiting' || todo.status === 'queued'}
								<button
									onclick={() => updatePriority(-10)}
									disabled={updatingPriority || (todo.status !== 'waiting' && todo.status !== 'queued')}
									class="px-3 py-1 rounded text-sm font-medium transition cursor-pointer {todo.priority === -10 ? 'bg-gray-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'} disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Low
								</button>
								<button
									onclick={() => updatePriority(0)}
									disabled={updatingPriority || (todo.status !== 'waiting' && todo.status !== 'queued')}
									class="px-3 py-1 rounded text-sm font-medium transition cursor-pointer {todo.priority === 0 ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-700 hover:bg-blue-200'} disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Middle
								</button>
								<button
									onclick={() => updatePriority(10)}
									disabled={updatingPriority || (todo.status !== 'waiting' && todo.status !== 'queued')}
									class="px-3 py-1 rounded text-sm font-medium transition cursor-pointer {todo.priority === 10 ? 'bg-red-600 text-white' : 'bg-red-100 text-red-700 hover:bg-red-200'} disabled:opacity-50 disabled:cursor-not-allowed"
								>
									High
								</button>
							{/if}
						</div>
					</div>
				</div>

				<div>
					<span class="block text-sm font-medium text-gray-500 mb-1">Prompt</span>
					<div class="p-3 bg-gray-50 rounded text-gray-900 prose prose-sm max-w-none">
						{#if todo.prompt}
							{@html marked(todo.prompt)}
						{:else}
							-
						{/if}
					</div>
				</div>

				{#if todo.validation_command}
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">完了判断コマンド</span>
						<div class="p-3 bg-gray-50 rounded text-gray-900 font-mono text-sm whitespace-pre-wrap">{todo.validation_command}</div>
					</div>
				{/if}

				{#if todo.context}
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">Context</span>
						<div class="p-3 bg-gray-50 rounded text-gray-900 whitespace-pre-wrap text-sm">
							{todo.context}
						</div>
					</div>
				{/if}

				{#if todo.system_prompt}
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">システムプロンプト</span>
						<div class="p-3 bg-gray-50 rounded text-gray-900 whitespace-pre-wrap text-sm">{todo.system_prompt}</div>
					</div>
				{/if}

				{#if todo.error}
					<div>
						<span class="block text-sm font-medium text-red-600 mb-1">Error</span>
						<div class="p-3 bg-red-50 border border-red-200 rounded text-red-800 whitespace-pre-wrap">
							{todo.error}
						</div>
					</div>
				{/if}

				{#if todo.output}
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">Output</span>
						<div class="p-3 bg-gray-50 rounded text-gray-900 whitespace-pre-wrap text-sm max-h-64 overflow-y-auto">
							{todo.output}
						</div>
					</div>
				{/if}

				{#if todo.ref_files && todo.ref_files.length > 0}
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">参照ファイル</span>
						<ul role="list" class="list-disc list-inside text-gray-900">
							{#each todo.ref_files as file}
								<li class="font-mono text-sm">{file}</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if todo.edit_files && todo.edit_files.length > 0}
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">編集ファイル</span>
						<ul role="list" class="list-disc list-inside text-gray-900">
							{#each todo.edit_files as file}
								<li class="font-mono text-sm">{file}</li>
							{/each}
						</ul>
					</div>
				{/if}

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-200">
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">作成日</span>
						<p class="text-gray-900">{formatDate(todo.created_at)}</p>
					</div>
					<div>
						<span class="block text-sm font-medium text-gray-500 mb-1">更新日</span>
						<p class="text-gray-900">{formatDate(todo.updated_at)}</p>
					</div>
				</div>
			</div>
		</div>
	{:else}
		<p class="text-gray-500">Todoが見つかりません。</p>
	{/if}
</div>
