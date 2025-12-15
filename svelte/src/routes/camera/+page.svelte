<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { io } from 'socket.io-client';

	let session_id = $page.url.searchParams.get('session') || 'default';
	let cameraId = crypto.randomUUID().slice(0, 8);
	let video: HTMLVideoElement;
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let socket: any;
	let streaming = false;
	let connectionStatus = 'Connecting...';
	let connectionColor = 'yellow';
	let debugLog: string[] = [];

	function log(msg: string) {
		const timestamp = new Date().toLocaleTimeString();
		const logMsg = `[${timestamp}] ${msg}`;
		console.log(logMsg);
		debugLog = [logMsg, ...debugLog].slice(0, 10);
	}

	onMount(async () => {
		const origin = window.location.origin;
		log(`Page loaded, origin: ${origin}`);
		log(`Session: ${session_id}, Camera: ${cameraId}`);

		// Test health endpoint
		try {
			const healthRes = await fetch(`${origin}/api/health`);
			const health = await healthRes.json();
			log(`Health check: ${JSON.stringify(health)}`);
		} catch (e: any) {
			log(`Health check failed: ${e.message}`);
		}

		log('Creating Socket.IO connection...');
		socket = io(origin, {
			path: '/socket.io',
			transports: ['polling'],
			reconnection: true,
			reconnectionDelay: 1000,
			timeout: 10000
		});

		socket.on('connect', () => {
			log(`✓ Connected! Socket ID: ${socket.id}`);
			connectionStatus = 'Connected ✓';
			connectionColor = 'lime';
			socket.emit('join_session', { session_id, role: 'camera', cameraId });
			log('Sent join_session event');
		});

		socket.on('connect_error', (error: any) => {
			log(`✗ Connection error: ${error.message}`);
			connectionStatus = `Error: ${error.message}`;
			connectionColor = 'red';
		});

		socket.on('disconnect', (reason: string) => {
			log(`✗ Disconnected: ${reason}`);
			connectionStatus = `Disconnected: ${reason}`;
			connectionColor = 'orange';
		});

		socket.on('reconnect_attempt', () => {
			log('Attempting to reconnect...');
			connectionStatus = 'Reconnecting...';
			connectionColor = 'yellow';
		});

		canvas = document.createElement('canvas');
		canvas.width = 320;
		canvas.height = 240;
		ctx = canvas.getContext('2d')!;

		const stream = await navigator.mediaDevices.getUserMedia({
			video: { width: 320, height: 240, facingMode: 'user' }
		});
		video.srcObject = stream;
		await video.play();
		streaming = true;

		setInterval(() => {
			if (streaming && ctx) {
				ctx.drawImage(video, 0, 0, 320, 240);
				canvas.toBlob(
					async (blob) => {
						if (blob && socket.connected) {
							// Convert Blob to ArrayBuffer for Socket.IO transmission
							const arrayBuffer = await blob.arrayBuffer();
							socket.emit('frame', { cameraId, blob: arrayBuffer });
						}
					},
					'image/jpeg',
					0.7
				);
			}
		}, 66);
	});
</script>

<div class="container">
	<h1>📹 Camera Connected</h1>
	<p class="session-id">Session: <strong>{session_id}</strong></p>
	<p class="camera-id">Camera ID: <strong>{cameraId}</strong></p>
	<p class="connection" style="color: {connectionColor}; font-weight: bold;">{connectionStatus}</p>
	<video bind:this={video} autoplay playsinline muted class="preview"></video>
	<p class="status">{streaming ? '🟢 Streaming' : '⚪ Waiting...'}</p>

	<div class="debug-log">
		<strong>Debug Log:</strong>
		{#each debugLog as log}
			<div class="log-entry">{log}</div>
		{/each}
	</div>
</div>

<style>
	.container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		padding: 20px;
		font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
	}
	h1 {
		font-size: 48px;
		margin-bottom: 10px;
	}
	.session-id,
	.camera-id {
		font-size: 18px;
		margin-bottom: 10px;
		opacity: 0.9;
	}
	.preview {
		width: 90%;
		max-width: 640px;
		border: 4px solid rgba(255, 255, 255, 0.3);
		border-radius: 16px;
		margin: 20px 0;
		box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
		transform: scaleX(-1);
	}
	.connection {
		font-size: 18px;
		margin: 10px 0;
	}
	.status {
		font-size: 28px;
	}
	.debug-log {
		margin-top: 20px;
		background: rgba(0, 0, 0, 0.3);
		padding: 15px;
		border-radius: 8px;
		width: 90%;
		max-width: 600px;
		max-height: 300px;
		overflow-y: auto;
		text-align: left;
		font-size: 12px;
		font-family: 'Courier New', monospace;
	}
	.log-entry {
		margin: 4px 0;
		opacity: 0.9;
		margin: 10px 0;
		font-weight: bold;
	}
</style>
