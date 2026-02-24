<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	interface TodoList {
		id: number;
		workdir: string;
	}

	interface Agent {
		id: number;
		name: string;
	}

	interface Todo {
		id: number;
		todo_list: number;
		todo_list_name: string | null;
		agent: number | null;
		agent_name: string | null;
		prompt: string;
		status: string;
		branch_name: string | null;
	}

	let todo: Todo | null = $state(null);
	let todoLists: TodoList[] = $state([]);
	let agents: Agent[] = $state([]);
	let loading = $state(true);
	let submitting = $state(false);
	let error = $state('');

	// フォームデータ
	let formPrompt = $state('');
	let formStatus = $state('waiting');
	let formTodoList = $state<number | null>(null);
	let formAgent = $state<number | null>(null);
	let formBranch = $state('');

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

			// フォームに初期値を設定
			if (todo) {
				formPrompt = todo.prompt || '';
				formStatus = todo.status;
				formTodoList = todo.todo_list;
				formAgent = todo.agent;
				formBranch = todo.branch_name || '';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function fetchOptions() {
		try {
			// TodoList一覧を取得
			const listsRes = await fetch('/api/todolists/');
			if (listsRes.ok) {
				todoLists = await listsRes.json();
			}

			// Agent一覧を取得
			const agentsRes = await fetch('/api/agents/');
			if (agentsRes.ok) {
				agents = await agentsRes.json();
			}
		} catch (e) {
			console.error('Failed to fetch options:', e);
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		submitting = true;
		error = '';

		try {
			const todoId = $page.params.todo;
			const csrfToken = getCSRFToken();

			const payload: Record<string, unknown> = {
				prompt: formPrompt,
				status: formStatus,
			};

			if (formTodoList !== null) {
				payload.todo_list = formTodoList;
			}

			if (formAgent !== null) {
				payload.agent = formAgent;
			}

			if (formBranch) {
				payload.branch_name = formBranch;
			} else {
				payload.branch_name = null;
			}

			const res = await fetch(`/api/todos/${todoId}/`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin',
				body: JSON.stringify(payload)
			});

			if (!res.ok) {
				const errData = await res.json().catch(() => ({}));
				throw new Error(errData.detail || JSON.stringify(errData) || 'Failed to update todo');
			}

			// 成功時は詳細ページにリダイレクト
			await goto(`/todo/${todoId}/`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update todo';
		} finally {
			submitting = false;
		}
	}

	onMount(() => {
		fetchTodo();
		fetchOptions();
	});
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/todo/{$page.params.todo}"
			class="p-2 hover:bg-gray-100 rounded-lg transition"
			title="Back to detail"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		</a>
		<h1 class="text-2xl font-bold">Todo更新</h1>
	</div>

	{#if error}
		<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
			{error}
		</div>
	{/if}

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if todo}
		<form onsubmit={handleSubmit} class="bg-white shadow rounded-lg p-6">
			<div class="space-y-6">
				<!-- Prompt (必須) -->
				<div>
					<label for="prompt" class="block text-sm font-medium text-gray-700 mb-2">
						Prompt <span class="text-red-500">*</span>
					</label>
					<textarea
						id="prompt"
						bind:value={formPrompt}
						required
						rows="6"
						placeholder="タスクの内容を入力してください"
						class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
					></textarea>
				</div>

				<!-- Status -->
				<div>
					<label for="status" class="block text-sm font-medium text-gray-700 mb-2">
						Status
					</label>
					<select
						id="status"
						bind:value={formStatus}
						class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value="waiting">waiting</option>
						<option value="queued">queued</option>
						<option value="running">running</option>
						<option value="completed">completed</option>
						<option value="error">error</option>
						<option value="cancelled">cancelled</option>
						<option value="timeout">timeout</option>
					</select>
				</div>

				<!-- TodoList -->
				<div>
					<label for="todo_list" class="block text-sm font-medium text-gray-700 mb-2">
						TodoList
					</label>
					<select
						id="todo_list"
						bind:value={formTodoList}
						class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value={null}>-- 選択してください --</option>
						{#each todoLists as list}
							<option value={list.id}>
								{list.workdir}
							</option>
						{/each}
					</select>
				</div>

				<!-- Branch -->
				<div>
					<label for="branch" class="block text-sm font-medium text-gray-700 mb-2">
						Branch
					</label>
					<input
						type="text"
						id="branch"
						bind:value={formBranch}
						placeholder="branch-name"
						class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>

				<!-- Agent -->
				<div>
					<label for="agent" class="block text-sm font-medium text-gray-700 mb-2">
						Agent
					</label>
					<select
						id="agent"
						bind:value={formAgent}
						class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value={null}>-- 選択してください --</option>
						{#each agents as agent}
							<option value={agent.id}>
								{agent.name}
							</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="mt-6 flex gap-4 justify-end">
				<a
					href="/todo/{$page.params.todo}"
					class="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition"
				>
					Cancel
				</a>
				<button
					type="submit"
					disabled={submitting || !formPrompt.trim()}
					class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{submitting ? 'Updating...' : 'Update'}
				</button>
			</div>
		</form>
	{:else}
		<p class="text-gray-500">Todoが見つかりません。</p>
	{/if}
</div>
