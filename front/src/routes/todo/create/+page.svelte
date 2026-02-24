<script lang="ts">
	import { goto } from '$app/navigation';

	let prompt = $state('');
	let workdir = $state('');
	let agent = $state('');
	let status = $state('waiting');
	let loading = $state(false);
	let error = $state('');

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

	async function handleSubmit(event: Event) {
		event.preventDefault();
		loading = true;
		error = '';

		try {
			const csrfToken = getCSRFToken();
			const payload: Record<string, unknown> = {
				prompt,
				status
			};

			// workdirが指定されていれば追加（APIが自動処理）
			if (workdir.trim()) {
				payload.workdir = workdir.trim();
			}

			// agentが指定されていれば追加
			if (agent.trim()) {
				// 数値または文字列としてそのまま送信
				payload.agent = agent.trim();
			}

			const res = await fetch('/api/todos/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin',
				body: JSON.stringify(payload)
			});

			if (!res.ok) {
				const errData = await res.json().catch(() => ({}));
				throw new Error(errData.detail || JSON.stringify(errData) || 'Failed to create todo');
			}

			// 成功時はリストページにリダイレクト
			await goto('/todo/');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create todo';
		} finally {
			loading = false;
		}
	}
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/todo/"
			class="p-2 hover:bg-gray-100 rounded-lg transition"
			title="Back to list"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		</a>
		<h1 class="text-2xl font-bold">New Todo</h1>
	</div>

	{#if error}
		<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
			{error}
		</div>
	{/if}

	<form onsubmit={handleSubmit} class="bg-white shadow rounded-lg p-6">
		<div class="space-y-6">
			<!-- Prompt (必須) -->
			<div>
				<label for="prompt" class="block text-sm font-medium text-gray-700 mb-2">
					Prompt <span class="text-red-500">*</span>
				</label>
				<textarea
					id="prompt"
					bind:value={prompt}
					required
					rows="6"
					placeholder="タスクの内容を入力してください"
					class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
				></textarea>
			</div>

			<!-- Workdir -->
			<div>
				<label for="workdir" class="block text-sm font-medium text-gray-700 mb-2">
					Workdir
				</label>
				<input
					type="text"
					id="workdir"
					bind:value={workdir}
					placeholder="/path/to/repository"
					class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
				<p class="mt-1 text-sm text-gray-500">
					作業ディレクトリ。指定すると自動的にtodo_listに関連付けられます。
				</p>
			</div>

			<!-- Agent -->
			<div>
				<label for="agent" class="block text-sm font-medium text-gray-700 mb-2">
					Agent
				</label>
				<input
					type="text"
					id="agent"
					bind:value={agent}
					placeholder="Agent ID または agent name"
					class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
				<p class="mt-1 text-sm text-gray-500">
					使用するエージェントのIDまたは名前。
				</p>
			</div>

			<!-- Status -->
			<div>
				<label for="status" class="block text-sm font-medium text-gray-700 mb-2">
					Status
				</label>
				<select
					id="status"
					bind:value={status}
					class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					<option value="waiting">waiting</option>
					<option value="queued">queued</option>
				</select>
			</div>
		</div>

		<div class="mt-6 flex gap-4 justify-end">
			<a
				href="/todo/"
				class="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition"
			>
				Cancel
			</a>
			<button
				type="submit"
				disabled={loading || !prompt.trim()}
				class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{loading ? 'Creating...' : 'Create'}
			</button>
		</div>
	</form>
</div>
