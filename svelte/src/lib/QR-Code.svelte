<script lang="ts">
	import { onMount } from 'svelte';

	export let session_id: string;
	export let onClose: () => void;

	let cameraUrl: string;
	let qrCodeUrl: string;

	onMount(() => {
		cameraUrl = `${window.location.origin}/camera?session=${session_id}`;
		qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(cameraUrl)}`;
	});

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			onClose();
		}
	}
</script>

<div
	class="modal-backdrop"
	on:click={handleBackdropClick}
	role="dialog"
	aria-modal="true"
	tabindex="0"
	on:keydown={(e) => {
		if (e.key === 'Escape' || e.key === 'Enter') {
			onClose();
		}
	}}
>
	<div class="modal-content">
		<button class="close-btn" on:click={onClose}>×</button>
		<img src={qrCodeUrl} alt="QR Code" />
		<code>{cameraUrl}</code>
	</div>
</div>

<style>
	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		width: 100vw;
		height: 100vh;
		background: rgba(0, 0, 0, 0.7);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal-content {
		position: relative;
		background: white;
		padding: 30px;
		border-radius: 8px;
		text-align: center;
	}

	.close-btn {
		position: absolute;
		top: 10px;
		right: 10px;
		background: none;
		border: none;
		font-size: 24px;
		cursor: pointer;
		color: #666;
	}

	.close-btn:hover {
		color: #000;
	}

	img {
		display: block;
		margin: 0 auto 15px;
		max-width: 300px;
	}

	code {
		display: block;
		background: #f5f5f5;
		padding: 10px;
		border-radius: 4px;
		font-size: 12px;
		word-break: break-all;
	}
</style>
