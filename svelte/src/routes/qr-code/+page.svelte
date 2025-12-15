<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { io, type Socket } from 'socket.io-client';

	let session_id_1 = '';
	let qrCodeUrl1 = '';
	let cameraUrl1 = '';

	let socket: Socket;

	// Player 1 State
	let p1Connected = false;
	let p1Latency = -1;
	let p1ResultText = 'Waiting for data …';

	let globalStatus = 'Waiting for camera to connect…';
	let allConnected = false;

	onMount(() => {
		session_id_1 = crypto.randomUUID().slice(0, 8);

		cameraUrl1 = `${window.location.origin}/camera?session=${session_id_1}`;

		qrCodeUrl1 = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(cameraUrl1)}`;

		socket = io();

		socket.on('connect', () => {
			console.log('Game connected to socket');
			// Join sessions
			socket.emit('join_session', { session_id: session_id_1, role: 'game' });
		});

		socket.on('result', (payload: any) => {
			const { session_id, result, timestamp } = payload;
			const latency = timestamp ? Math.max(Date.now() - timestamp, 0) : -1;
			const text = describeResult(result);

			if (session_id === session_id_1) {
				p1ResultText = text;
				p1Latency = latency;
				if (!p1Connected) {
					p1Connected = true;
					updateGlobalStatus();
				}
			}
		});

		socket.on('disconnect', () => {
			p1Connected = false;
			p1Latency = -1;
			updateGlobalStatus();
		});
	});

	onDestroy(() => {
		if (socket) socket.disconnect();
	});

	function startGame() {
		goto(`/?session1=${session_id_1}&remote=true`);
	}

	function updateGlobalStatus() {
		if (p1Connected) {
			globalStatus = 'Camera connected.';
			allConnected = true;
		} else {
			globalStatus = 'Waiting for camera to connect…';
			allConnected = false;
		}
	}

	const describeResult = (result: any) => {
		if (!result) {
			return 'No keypoints yet.';
		}
		const lines = [];
		if (result.body?.head) {
			lines.push(`Head: (${result.body.head.x.toFixed(3)}, ${result.body.head.y.toFixed(3)})`);
		}
		['left', 'right'].forEach((side) => {
			const hand = result.hands?.[side];
			if (hand) {
				lines.push(
					`${side} hand: ${hand.gesture} (${hand.fingers} fingers) wrist=(${hand.wrist.x.toFixed(3)}, ${hand.wrist.y.toFixed(3)})`
				);
			}
		});
		if (!lines.length) {
			lines.push('No body or hand landmarks detected.');
		}
		lines.push(`raw JSON: ${JSON.stringify(result)}`);
		return lines.join('\n');
	};
</script>

<h1>Connect Camera</h1>
<p>
	Scan the QR code with your mobile device. The stream stays on the phone and only the keypoint data
	is forwarded to this control view.
</p>
<p id="connectionStatus" class="statusLabel" class:connected={allConnected} class:disconnected={!allConnected}>
	{globalStatus}
</p>

<section id="playerGrid">
	<!-- Player 1 -->
	<article class="playerCard" data-session={session_id_1}>
		<p class="statusLabel" class:connected={p1Connected} class:disconnected={!p1Connected}>
			{p1Connected ? 'Connected' : 'Disconnected'}
		</p>
		<h2>Player 1</h2>
		<div>
			<img src={qrCodeUrl1} alt="QR Code 1" />
			<p><a href={cameraUrl1} target="_blank">Open camera 1 link</a></p>
			<p class="latencyLabel">Latency: {p1Latency >= 0 ? p1Latency + ' ms' : '-- ms'}</p>
		</div>
		<h2>Live Keypoints</h2>
		<div class="resultBox">{p1ResultText}</div>
	</article>
</section>

{#if allConnected}
	<button id="startGameBtn" onclick={startGame}>Start Game</button>
{/if}

<style>
	:global(body) {
		font-family: "Segoe UI", system-ui, sans-serif;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		align-items: center;
		margin: 1.5rem;
		min-height: 100vh;
		background: radial-gradient(circle at top, #1a1a2e, #09090f 80%);
		color: #fff;
	}
	h1 {
		margin: 0.2rem 0;
	}
	#playerGrid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
		gap: 1rem;
		width: 100%;
		max-width: 1100px;
	}
	.playerCard {
		border-radius: 20px;
		padding: 1.25rem;
		background: rgba(17, 17, 17, 0.85);
		border: 1px solid rgba(255, 255, 255, 0.1);
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		position: relative;
		overflow: hidden;
	}
	.playerCard::after {
		content: "";
		position: absolute;
		inset: 0;
		border-radius: inherit;
		pointer-events: none;
		box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.35);
	}
	.playerCard h2 {
		margin: 0;
	}
	.playerCard img {
		width: min(280px, 100%);
		border-radius: 12px;
		box-shadow: 0 20px 30px rgba(0, 0, 0, 0.4);
	}
	.playerCard a {
		color: inherit;
		text-decoration: none;
		font-weight: 600;
		background: rgba(255, 255, 255, 0.1);
		padding: 0.25rem 0.5rem;
		border-radius: 999px;
		display: inline-block;
		transition: transform 0.2s;
	}
	.playerCard a:hover {
		transform: translateY(-2px);
	}
	.resultBox {
		background: rgba(0, 0, 0, 0.35);
		border-radius: 12px;
		padding: 0.85rem;
		font-size: 0.9rem;
		line-height: 1.4;
		white-space: pre-wrap;
		min-height: 140px;
		border: 1px solid rgba(255, 255, 255, 0.15);
	}
	.statusLabel {
		font-size: 0.9rem;
		padding: 0.35rem 0.8rem;
		border-radius: 999px;
		text-align: center;
		width: fit-content;
		background: rgba(255, 255, 255, 0.12);
		color: #fff;
		transition: background 0.2s, color 0.2s;
	}
	.statusLabel.connected {
		background: linear-gradient(135deg, #00c853, #b2ff59);
		color: #000;
	}
	.statusLabel.disconnected {
		background: rgba(255, 75, 43, 0.15);
		color: #ff8a65;
	}
	.latencyLabel {
		font-size: 0.85rem;
		color: #9aceff;
		margin-top: 0.25rem;
	}
	#startGameBtn {
		font-size: 1.1rem;
		border: none;
		border-radius: 999px;
		padding: 0.9rem 2.5rem;
		cursor: pointer;
		color: #fff;
		background: linear-gradient(135deg, #ff416c, #ff4b2b);
		box-shadow: 0 12px 35px rgba(255, 75, 43, 0.45);
		animation: pulseBtn 2.6s ease-in-out infinite;
		display: inline-flex;
		margin-top: 1rem;
	}
	@keyframes pulseBtn {
		0% { transform: translateY(0); box-shadow: 0 10px 30px rgba(255, 75, 43, 0.35); }
		50% { transform: translateY(-6px); box-shadow: 0 20px 45px rgba(255, 75, 43, 0.45); }
		100% { transform: translateY(0); box-shadow: 0 10px 30px rgba(255, 75, 43, 0.35); }
	}
</style>

<!--






-->