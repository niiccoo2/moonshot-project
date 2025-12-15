<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { io } from 'socket.io-client';

	const session_id = $page.params.session_id;
	let video: HTMLVideoElement;
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let socket: any;
	let streaming = false;

	onMount(async () => {
		// Connect to your Flask backend
		socket = io('http://127.0.0.1:7000');

		socket.emit('join_session', { session_id });

		canvas = document.createElement('canvas');
		canvas.width = 320;
		canvas.height = 240;
		ctx = canvas.getContext('2d')!;

		const stream = await navigator.mediaDevices.getUserMedia({
			video: { width: 320, height: 240 }
		});
		video.srcObject = stream;
		await video.play();
		streaming = true;

		// Send frames to server
		setInterval(() => {
			if (streaming) {
				ctx.drawImage(video, 0, 0, 320, 240);
				canvas.toBlob(
					(blob) => {
						if (blob) socket.emit('frame', blob);
					},
					'image/jpeg',
					0.5
				);
			}
		}, 66); // ~15fps
	});
</script>

<div class="container">
	<h1>Camera Connected</h1>
	<p>Session: {session_id}</p>
	<video bind:this={video} autoplay playsinline class="preview"></video>
	<p class="status">{streaming ? '🟢 Streaming' : '⚪ Waiting...'}</p>
</div>

<style>
	.container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		background: #1a1a1a;
		color: white;
		padding: 20px;
	}
	.preview {
		width: 80%;
		max-width: 640px;
		border: 2px solid #fff;
		border-radius: 8px;
		margin: 20px 0;
	}
	.status {
		font-size: 24px;
		margin: 10px 0;
	}
</style>
