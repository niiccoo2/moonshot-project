<script lang="ts">
	import { onMount } from 'svelte';
	import { io } from 'socket.io-client';

	let healthStatus = 'Checking...';
	let socketioStatus = 'Checking...';
	let connectionTest = 'Not started';
	let serverInfo: any = null;
	let socketInfo: any = null;
	let socket: any = null;

	async function testHealth() {
		try {
			const res = await fetch('/api/health');
			const data = await res.json();
			healthStatus = '✅ Server is running';
			serverInfo = data;
		} catch (e: any) {
			healthStatus = `❌ Failed: ${e.message}`;
		}
	}

	async function testSocketIO() {
		try {
			const res = await fetch('/api/socketio-status');
			const data = await res.json();
			socketioStatus = '✅ Socket.IO endpoint is accessible';
			socketInfo = data;
		} catch (e: any) {
			socketioStatus = `❌ Failed: ${e.message}`;
		}
	}

	function testConnection() {
		connectionTest = 'Connecting...';

		socket = io(window.location.origin, {
			path: '/socket.io',
			transports: ['polling']
		});

		socket.on('connect', () => {
			connectionTest = `✅ Connected! Socket ID: ${socket.id}`;
			socket.emit('join_session', { session_id: 'test', role: 'test' });
		});

		socket.on('connect_error', (error: any) => {
			connectionTest = `❌ Connection failed: ${error.message}`;
		});

		socket.on('disconnect', () => {
			connectionTest = '⚠️ Disconnected';
		});
	}

	onMount(() => {
		testHealth();
		testSocketIO();
	});
</script>

<div class="container">
	<h1>🔧 Server Diagnostic Test</h1>
	<p class="subtitle">
		Origin: <code>{typeof window !== 'undefined' ? window.location.origin : ''}</code>
	</p>

	<div class="test-section">
		<h2>1. Health Check Endpoint</h2>
		<p class="status">{healthStatus}</p>
		{#if serverInfo}
			<pre>{JSON.stringify(serverInfo, null, 2)}</pre>
		{/if}
		<button on:click={testHealth}>Retry Health Check</button>
	</div>

	<div class="test-section">
		<h2>2. Socket.IO Status Endpoint</h2>
		<p class="status">{socketioStatus}</p>
		{#if socketInfo}
			<pre>{JSON.stringify(socketInfo, null, 2)}</pre>
		{/if}
		<button on:click={testSocketIO}>Retry Socket.IO Status</button>
	</div>

	<div class="test-section">
		<h2>3. Socket.IO Connection Test</h2>
		<p class="status">{connectionTest}</p>
		<button on:click={testConnection}>Test Connection</button>
		{#if socket}
			<button on:click={() => socket.disconnect()}>Disconnect</button>
		{/if}
	</div>

	<div class="instructions">
		<h3>📋 What to check:</h3>
		<ul>
			<li>If test #1 fails: The server.js is not running (check Coolify start command)</li>
			<li>If test #2 fails: Socket.IO server is not initialized properly</li>
			<li>If test #3 fails: Socket.IO connection is blocked (check transports/CORS)</li>
		</ul>
	</div>

	<div class="links">
		<a href="/">← Back to Game</a>
		<a href="/camera">Camera Page →</a>
	</div>
</div>

<style>
	.container {
		max-width: 800px;
		margin: 0 auto;
		padding: 40px 20px;
		font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
	}

	h1 {
		text-align: center;
		color: #333;
		margin-bottom: 10px;
	}

	.subtitle {
		text-align: center;
		color: #666;
		margin-bottom: 40px;
	}

	code {
		background: #f4f4f4;
		padding: 2px 8px;
		border-radius: 4px;
		font-family: 'Courier New', monospace;
	}

	.test-section {
		background: white;
		border: 2px solid #e0e0e0;
		border-radius: 8px;
		padding: 20px;
		margin-bottom: 20px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.test-section h2 {
		margin-top: 0;
		color: #444;
	}

	.status {
		font-size: 18px;
		font-weight: bold;
		margin: 15px 0;
	}

	pre {
		background: #f8f8f8;
		padding: 15px;
		border-radius: 4px;
		overflow-x: auto;
		font-size: 12px;
		border: 1px solid #ddd;
	}

	button {
		background: #4caf50;
		color: white;
		border: none;
		padding: 10px 20px;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
		margin-right: 10px;
	}

	button:hover {
		background: #45a049;
	}

	button:active {
		transform: scale(0.98);
	}

	.instructions {
		background: #fff3cd;
		border: 2px solid #ffc107;
		border-radius: 8px;
		padding: 20px;
		margin-bottom: 20px;
	}

	.instructions h3 {
		margin-top: 0;
		color: #856404;
	}

	.instructions ul {
		margin: 0;
		padding-left: 20px;
	}

	.instructions li {
		margin: 10px 0;
		color: #856404;
	}

	.links {
		display: flex;
		justify-content: space-between;
		margin-top: 30px;
	}

	.links a {
		color: #007bff;
		text-decoration: none;
		font-weight: bold;
	}

	.links a:hover {
		text-decoration: underline;
	}
</style>
