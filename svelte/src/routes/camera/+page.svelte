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

	onMount(async () => {
		socket = io('http://localhost:3001');

		socket.on('connect', () => {
			console.log('Connected to server as camera:', cameraId);
			socket.emit('join_session', { session_id, role: 'camera', cameraId });
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
					(blob) => {
						if (blob && socket.connected) {
							socket.emit('frame', { cameraId, blob });
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
	<video bind:this={video} autoplay playsinline muted class="preview"></video>
	<p class="status">{streaming ? '🟢 Streaming' : '⚪ Waiting...'}</p>
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
	.status {
		font-size: 28px;
		margin: 10px 0;
		font-weight: bold;
	}
</style>
