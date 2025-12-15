<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Game from '$lib/Game.svelte';
	import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';
	import { io } from 'socket.io-client';
	import '$lib/main.css';
	import QRCode from '$lib/QR-Code.svelte';

	let session_id = $page.url.searchParams.get('session') || randomLetters4();
	let video: HTMLVideoElement;
	let remoteCameras: Map<string, HTMLImageElement> = new Map();
	let cameraDisplayUrls: Map<string, string> = new Map(); // Track URLs for display
	let poseLandmarker: any;
	let lastProcessTime = 0;
	const PROCESS_INTERVAL = 200;
	let socket: any;
	let useLocalCamera = true;
	let selectedCamera = 'local';
	let cameraList: string[] = [];
	let showQRModal: boolean = false;

	let input = {
		jumping: false,
		crouching: false,
		prevJumping: false,
		movingRight: false,
		movingLeft: false
	};

	let debug = false;
	let debugInfo = {
		jumping: false,
		crouching: false,
		shoulderY: 0,
		remoteCameras: 0,
		connectionStatus: 'Not connected',
		connectionColor: 'gray'
	};

	function randomLetters4() {
		const letters = 'abcdefghijklmnopqrstuvwxyz';
		const result = new Array(4);
		const bytes = crypto.getRandomValues(new Uint8Array(4)); // browser
		for (let i = 0; i < 4; i++) {
			result[i] = letters[bytes[i] % letters.length];
		}
		return result.join('');
	}

	function log(msg: string) {
		if (debug) console.log(msg);
	}

	function processResults(poseLandmarkerResult: any) {
		if (poseLandmarkerResult.landmarks && poseLandmarkerResult.landmarks.length > 0) {
			const pose = poseLandmarkerResult.landmarks[0];

			// Calculate shoulder position for debug
			if (pose[12]) {
				debugInfo.shoulderY = pose[12].y;
			}

			if (pose[12] && pose[12].y < 0.33) {
				input.jumping = true;
				input.crouching = false;
			} else if (pose[12] && pose[12].y > 0.66) {
				input.crouching = true;
				input.jumping = false;
			} else {
				input.jumping = false;
				input.crouching = false;
			}

			// Update debug info
			debugInfo.jumping = input.jumping;
			debugInfo.crouching = input.crouching;
			debugInfo.remoteCameras = remoteCameras.size;
		}
	}

	function setupRemoteCameras() {
		const origin = window.location.origin;
		log(`Setting up remote cameras`);
		log(`Session: ${session_id}`);
		log(`Origin: ${origin}`);

		// Test health endpoint
		fetch(`${origin}/api/health`)
			.then((res) => res.json())
			.then((health) => log(`Health check: ${JSON.stringify(health)}`))
			.catch((e) => log(`Health check failed: ${e.message}`));

		log('Creating Socket.IO connection...');
		socket = io(origin, {
			path: '/socket.io',
			transports: ['polling'],
			reconnection: true,
			reconnectionDelay: 1000,
			timeout: 10000
		});

		socket.on('connect', () => {
			log(`✓ Game connected! Socket ID: ${socket.id}`);
			debugInfo.connectionStatus = 'Connected ✓';
			debugInfo.connectionColor = 'lime';
			socket.emit('join_session', { session_id, role: 'game' });
			log('Sent join_session as game');
		});

		socket.on('connect_error', (error: any) => {
			log(`✗ Connection error: ${error.message}`);
			debugInfo.connectionStatus = `Error: ${error.message}`;
			debugInfo.connectionColor = 'red';
		});

		socket.on('disconnect', (reason: string) => {
			log(`✗ Disconnected: ${reason}`);
			debugInfo.connectionStatus = `Disconnected: ${reason}`;
			debugInfo.connectionColor = 'orange';
		});

		socket.on('reconnect_attempt', () => {
			log('Attempting to reconnect...');
			debugInfo.connectionStatus = 'Reconnecting...';
			debugInfo.connectionColor = 'yellow';
		});

		socket.on('frame', (data: { cameraId: string; blob: any }) => {
			const { cameraId, blob } = data;

			if (!remoteCameras.has(cameraId)) {
				log(`✓ New camera connected: ${cameraId}`);
				remoteCameras.set(cameraId, new Image());
				debugInfo.remoteCameras = remoteCameras.size;
				cameraList = Array.from(remoteCameras.keys());
				// Auto-select first remote camera if local camera is disabled
				if (!useLocalCamera && selectedCamera === 'local' && cameraList.length === 1) {
					selectedCamera = cameraId;
					log(`Auto-selected camera: ${cameraId}`);
				}
			}

			// Only process frames from selected camera
			if (selectedCamera !== 'local' && cameraId !== selectedCamera) {
				return;
			}

			log(`✓ Processing frame from ${cameraId}`);

			// Convert ArrayBuffer back to Blob
			const blobData = new Blob([blob], { type: 'image/jpeg' });
			const img = remoteCameras.get(cameraId)!;
			const url = URL.createObjectURL(blobData);

			// Clean up old display URL
			if (cameraDisplayUrls.has(cameraId)) {
				URL.revokeObjectURL(cameraDisplayUrls.get(cameraId)!);
			}
			cameraDisplayUrls.set(cameraId, url);

			img.onload = () => {
				const now = performance.now();
				if (now - lastProcessTime > PROCESS_INTERVAL && poseLandmarker) {
					// Use detectForVideo for both video and image sources
					const result = poseLandmarker.detectForVideo(img, now);
					processResults(result);
					lastProcessTime = now;
				}
				URL.revokeObjectURL(url);
			};
			img.src = url;
		});

		socket.on('camera_disconnected', (cameraId: string) => {
			log(`✗ Camera disconnected: ${cameraId}`);
			remoteCameras.delete(cameraId);
			// Clean up display URL
			if (cameraDisplayUrls.has(cameraId)) {
				URL.revokeObjectURL(cameraDisplayUrls.get(cameraId)!);
				cameraDisplayUrls.delete(cameraId);
			}
			debugInfo.remoteCameras = remoteCameras.size;
			cameraList = Array.from(remoteCameras.keys());
			// Switch to local if selected camera disconnected
			if (selectedCamera === cameraId) {
				selectedCamera = 'local';
				log('Selected camera disconnected, switching to local');
			}
		});
	}

	async function startLocalVideo() {
		log('Starting local video');
		const stream = await navigator.mediaDevices.getUserMedia({
			video: { width: 320, height: 240 }
		});
		video.srcObject = stream;
		await video.play();
		log('Local video playing');
		requestFrame();
	}

	function requestFrame() {
		const now = performance.now();
		// Only process local camera if it's selected
		if (
			selectedCamera === 'local' &&
			now - lastProcessTime > PROCESS_INTERVAL &&
			poseLandmarker &&
			video
		) {
			const result = poseLandmarker.detectForVideo(video, now);
			processResults(result);
			lastProcessTime = now;
		}
		requestAnimationFrame(requestFrame);
	}

	onMount(async () => {
		log('Initializing MediaPipe');
		const vision = await FilesetResolver.forVisionTasks(
			'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
		);

		poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
			baseOptions: {
				modelAssetPath:
					'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
				delegate: 'GPU'
			},
			runningMode: 'VIDEO',
			numPoses: 1
		});

		log('MediaPipe ready');

		// Always start local camera
		if (useLocalCamera) {
			startLocalVideo();
		}

		setupRemoteCameras();
	});
</script>

{#if showQRModal}
	<QRCode {session_id} onClose={() => (showQRModal = false)}></QRCode>
{/if}

<div id="game-root">
	<Game {input} />

	<!-- Camera preview - shows selected camera -->
	{#if selectedCamera === 'local' && useLocalCamera}
		<!-- Local camera preview -->
		<video
			bind:this={video}
			autoplay
			playsinline
			style="transform: scaleX(-1);"
			class="video-overlay camera-preview"
		></video>
	{/if}

	<!-- Camera Selector -->
	{#if useLocalCamera && cameraList.length > 0}
		<div class="camera-selector">
			<strong>Active Camera:</strong>
			<select
				bind:value={selectedCamera}
				onchange={() => log(`Switched to camera: ${selectedCamera}`)}
			>
				<option value="local">Local Camera</option>
				{#each cameraList as camId}
					<option value={camId}>Remote: {camId}</option>
				{/each}
			</select>
		</div>
	{/if}

	<!-- Bottom Left - Info Container -->
	<div class="bottom-left-info">
		<!-- Session Info - Split into left and right -->
		<div class="remote-indicator">
			<div class="session-content">
				<div class="session-left">
					<strong>Session:</strong>
					{session_id}
					<br />
					<strong>Remote Cameras:</strong>
					{remoteCameras.size}
				</div>
				<div class="session-right">
					<button class="connect-btn" onclick={() => (showQRModal = true)}> Connect Camera </button>
				</div>
			</div>
		</div>

		<!-- Debug info -->
		{#if debug}
			<div class="debug-overlay">
				<h3>Debug Info</h3>
				<p><strong>Shoulder Y:</strong> {debugInfo.shoulderY.toFixed(2)}</p>
				<p><strong>Jumping:</strong> {debugInfo.jumping ? '✅' : '❌'}</p>
				<p><strong>Crouching:</strong> {debugInfo.crouching ? '✅' : '❌'}</p>
				<p><strong>Remote Cameras:</strong> {debugInfo.remoteCameras}</p>
				<p><strong>Active Camera:</strong> {selectedCamera}</p>
				<p>
					<strong>Socket:</strong>
					<span style="color: {debugInfo.connectionColor}">{debugInfo.connectionStatus}</span>
				</p>
			</div>
		{/if}
	</div>
</div>
