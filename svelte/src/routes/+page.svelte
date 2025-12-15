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
		fps: 0
	};

	let lastFrameTime = 0;
	let frameCount = 0;

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
		console.log('Setting up remote cameras, session:', session_id);
		socket = io('http://localhost:3001');

		socket.on('connect', () => {
			console.log('Game connected to server');
			socket.emit('join_session', { session_id, role: 'game' });
		});

		socket.on('frame', (data: { cameraId: string; blob: Blob }) => {
			const { cameraId, blob } = data;

			if (!remoteCameras.has(cameraId)) {
				remoteCameras.set(cameraId, new Image());
			}

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
			console.log('Camera disconnected:', cameraId);
			remoteCameras.delete(cameraId);
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
		if (now - lastProcessTime > PROCESS_INTERVAL && poseLandmarker && video) {
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

	<!-- Local camera preview -->
	{#if useLocalCamera}
		<video
			bind:this={video}
			autoplay
			playsinline
			style="transform: scaleX(-1);"
			class="video-overlay local-camera"
		></video>
	{/if}

	<!-- Remote camera indicator -->
	{#if useRemoteCameras}
		<div class="remote-indicator">
			📱 Session: {session_id}
			<br />
			🎥 Remote Cameras: {remoteCameras.size}
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
		</div>
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

	.local-camera {
		top: 16px;
		right: 16px;
		width: 240px;
		height: 180px;
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

	#game-root {
		position: relative;
		width: 100vw;
		height: 100vh;
		overflow: hidden;
	}
</style>
