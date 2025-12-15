<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Game from '$lib/Game.svelte';
	import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';
	import { io } from 'socket.io-client';

	let session_id = $page.url.searchParams.get('session') || crypto.randomUUID();
	let video: HTMLVideoElement;
	let remoteCameras: Map<string, HTMLImageElement> = new Map();
	let poseLandmarker: any;
	let lastProcessTime = 0;
	const PROCESS_INTERVAL = 200;
	let socket: any;
	let useLocalCamera = true; // Always use local camera by default
	let useRemoteCameras = $page.url.searchParams.get('remote') === 'true';
	let selectedCamera = 'local'; // 'local' or a specific cameraId
	let cameraList: string[] = []; // List of available camera IDs

	let input = {
		jumping: false,
		crouching: false,
		prevJumping: false,
		movingRight: false,
		movingLeft: false
	};

	let debug = true;
	let debugInfo = {
		jumping: false,
		crouching: false,
		shoulderY: 0,
		remoteCameras: 0,
		fps: 0,
		connectionStatus: 'Not connected',
		connectionColor: 'gray'
	};

	let lastFrameTime = 0;
	let frameCount = 0;
	let debugLog: string[] = [];

	function log(msg: string) {
		const timestamp = new Date().toLocaleTimeString();
		const logMsg = `[${timestamp}] ${msg}`;
		console.log(logMsg);
		debugLog = [logMsg, ...debugLog].slice(0, 15);
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

			// Calculate FPS
			const now = performance.now();
			if (now - lastFrameTime > 1000) {
				debugInfo.fps = frameCount;
				frameCount = 0;
				lastFrameTime = now;
			}
			frameCount++;
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

		socket.on('frame', (data: { cameraId: string; blob: Blob }) => {
			const { cameraId, blob } = data;
			log(`📸 Frame received from ${cameraId} (size: ${blob.size} bytes)`);

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
				log(`⏭️ Skipping frame from ${cameraId} (selected: ${selectedCamera})`);
				return;
			}

			log(`✅ Processing frame from ${cameraId}`);
			const img = remoteCameras.get(cameraId)!;
			const url = URL.createObjectURL(blob);

			img.onload = () => {
				const now = performance.now();
				if (now - lastProcessTime > PROCESS_INTERVAL && poseLandmarker) {
					const result = poseLandmarker.detect(img);
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
		console.log('Starting local video');
		const stream = await navigator.mediaDevices.getUserMedia({
			video: { width: 320, height: 240 }
		});
		video.srcObject = stream;
		await video.play();
		console.log('Local video playing');
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

	// function processResults(poseLandmarkerResult: any) {
	// 	if (poseLandmarkerResult.landmarks && poseLandmarkerResult.landmarks.length > 0) {
	// 		const pose = poseLandmarkerResult.landmarks[0];
	// 		if (pose[12] && pose[12].y < 0.33) {
	// 			input.jumping = true;
	// 			input.crouching = false;
	// 		} else if (pose[12] && pose[12].y > 0.66) {
	// 			input.crouching = true;
	// 			input.jumping = false;
	// 		} else {
	// 			input.jumping = false;
	// 			input.crouching = false;
	// 		}
	// 	}
	// }

	onMount(async () => {
		console.log('Initializing MediaPipe');
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

		console.log('MediaPipe ready');

		// Always start local camera
		if (useLocalCamera) {
			startLocalVideo();
		}

		// Also setup remote cameras if requested
		if (useRemoteCameras) {
			setupRemoteCameras();
		}
	});
</script>

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
	{:else if selectedCamera !== 'local' && remoteCameras.has(selectedCamera)}
		<!-- Remote camera preview -->
		<div class="video-overlay camera-preview remote-preview">
			<img
				src={remoteCameras.get(selectedCamera)?.src || ''}
				alt="Remote camera"
				style="transform: scaleX(-1); width: 100%; height: 100%; object-fit: cover;"
			/>
			<div class="remote-label">Remote: {selectedCamera}</div>
		</div>
	{/if}

	<!-- Remote camera indicator -->
	{#if useRemoteCameras}
		<div class="remote-indicator">
			📱 Session: {session_id}
			<br />
			🎥 Remote Cameras: {remoteCameras.size}
		</div>
	{/if}

	<!-- Camera Selector -->
	{#if useLocalCamera && useRemoteCameras && cameraList.length > 0}
		<div class="camera-selector">
			<strong>🎮 Active Camera:</strong>
			<select
				bind:value={selectedCamera}
				on:change={() => log(`Switched to camera: ${selectedCamera}`)}
			>
				<option value="local">Local Camera</option>
				{#each cameraList as camId}
					<option value={camId}>Remote: {camId}</option>
				{/each}
			</select>
		</div>
	{/if}

	<!-- Debug info -->
	{#if debug}
		<div class="debug-overlay">
			<h3>🐛 Debug Info</h3>
			<p>FPS: {debugInfo.fps}</p>
			<p>Shoulder Y: {debugInfo.shoulderY.toFixed(2)}</p>
			<p>Jumping: {debugInfo.jumping ? '✅' : '❌'}</p>
			<p>Crouching: {debugInfo.crouching ? '✅' : '❌'}</p>
			<p>Remote Cameras: {debugInfo.remoteCameras}</p>
			<p>Active Camera: <strong>{selectedCamera}</strong></p>
			{#if useRemoteCameras}
				<p style="color: {debugInfo.connectionColor}">Socket: {debugInfo.connectionStatus}</p>
			{/if}
		</div>

		<!-- Debug log -->
		{#if debugLog.length > 0}
			<div class="debug-log">
				<strong>🔍 Connection Log:</strong>
				{#each debugLog as log}
					<div class="log-entry">{log}</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.video-overlay {
		position: absolute;
		border: 2px solid #fff;
		border-radius: 8px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
		z-index: 10;
		background: #000;
		object-fit: cover;
	}

	.camera-preview {
		top: 16px;
		right: 16px;
		width: 240px;
		height: 180px;
	}

	.remote-preview {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.remote-label {
		position: absolute;
		bottom: 8px;
		left: 8px;
		background: rgba(0, 0, 0, 0.8);
		color: #0ff;
		padding: 4px 8px;
		border-radius: 4px;
		font-size: 11px;
		font-family: monospace;
	}

	.remote-indicator {
		position: absolute;
		top: 16px;
		left: 16px;
		padding: 12px 20px;
		background: rgba(0, 0, 0, 0.7);
		color: white;
		border-radius: 8px;
		font-size: 14px;
		z-index: 100; /* Increased */
		line-height: 1.5;
	}

	.camera-selector {
		position: absolute;
		top: 16px;
		left: 50%;
		transform: translateX(-50%);
		padding: 12px 20px;
		background: rgba(0, 0, 0, 0.85);
		color: white;
		border-radius: 8px;
		font-size: 14px;
		z-index: 100;
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.camera-selector select {
		padding: 6px 12px;
		font-size: 14px;
		border-radius: 4px;
		border: 2px solid #4caf50;
		background: #222;
		color: white;
		cursor: pointer;
	}

	.camera-selector select:hover {
		border-color: #66ff66;
	}

	.debug-overlay {
		position: absolute;
		bottom: 16px;
		left: 16px;
		padding: 16px;
		background: rgba(0, 0, 0, 0.9); /* More opaque */
		color: #0f0;
		border: 2px solid #0f0;
		border-radius: 8px;
		font-family: monospace;
		font-size: 14px;
		z-index: 100; /* Increased from 10 to 100 */
		min-width: 200px;
		pointer-events: none; /* Allow clicks to pass through */
	}

	.debug-overlay h3 {
		margin: 0 0 10px 0;
		font-size: 16px;
		color: #0ff;
	}

	.debug-overlay p {
		margin: 4px 0;
		line-height: 1.5;
	}

	.debug-log {
		position: absolute;
		bottom: 16px;
		right: 16px;
		padding: 12px;
		background: rgba(0, 0, 0, 0.9);
		color: #0ff;
		border: 2px solid #0ff;
		border-radius: 8px;
		font-family: 'Courier New', monospace;
		font-size: 11px;
		z-index: 100;
		max-width: 400px;
		max-height: 400px;
		overflow-y: auto;
		pointer-events: none;
	}

	.debug-log strong {
		display: block;
		margin-bottom: 8px;
		color: #ff0;
	}

	.log-entry {
		margin: 3px 0;
		opacity: 0.9;
		word-break: break-all;
	}

	#game-root {
		position: relative;
		width: 100vw;
		height: 100vh;
		overflow: hidden;
	}
</style>
