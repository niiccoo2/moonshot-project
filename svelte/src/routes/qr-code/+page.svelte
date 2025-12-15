<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	let session_id = '';
	let qrCodeUrl = '';
	let cameraUrl = '';

	onMount(() => {
		session_id = crypto.randomUUID().slice(0, 8);
		cameraUrl = `${window.location.origin}/camera?session=${session_id}`;
		qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(cameraUrl)}`;
	});

	function startGame() {
		goto(`/?session=${session_id}&remote=true`);
	}
</script>

<div class="setup">
	<h1>Setup Remote Camera</h1>
	<p class="subtitle">Scan this QR code with your phone to use it as a camera</p>

	{#if qrCodeUrl}
		<div class="qr-container">
			<img src={qrCodeUrl} alt="QR Code" />
		</div>
	{/if}

	<div class="info-box">
		<p><strong>Session ID:</strong> {session_id}</p>
		<p class="small">Or manually visit: <code>{cameraUrl}</code></p>
	</div>

	<button on:click={startGame} class="start-btn">Start Game 🎮</button>
</div>

<style>
	.setup {
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
		font-size: 56px;
		margin-bottom: 10px;
	}
	.subtitle {
		font-size: 20px;
		margin-bottom: 30px;
		opacity: 0.9;
	}
	.qr-container {
		background: white;
		padding: 20px;
		border-radius: 16px;
		box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
		margin: 20px 0;
	}
	img {
		display: block;
		max-width: 100%;
	}
	.info-box {
		background: rgba(255, 255, 255, 0.1);
		padding: 20px 40px;
		border-radius: 12px;
		margin: 20px 0;
		backdrop-filter: blur(10px);
	}
	.small {
		font-size: 14px;
		opacity: 0.8;
		margin-top: 10px;
	}
	code {
		background: rgba(0, 0, 0, 0.3);
		padding: 4px 8px;
		border-radius: 4px;
		font-family: monospace;
	}
	.start-btn {
		margin-top: 30px;
		padding: 20px 60px;
		font-size: 28px;
		background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
		color: white;
		border: none;
		border-radius: 50px;
		cursor: pointer;
		font-weight: bold;
		box-shadow: 0 10px 30px rgba(245, 87, 108, 0.4);
		transition: transform 0.2s;
	}
	.start-btn:hover {
		transform: scale(1.05);
	}
</style>
