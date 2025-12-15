<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { io } from 'socket.io-client';
	import { FilesetResolver, HandLandmarker, PoseLandmarker } from '@mediapipe/tasks-vision';

	let session_id = $page.url.searchParams.get('session') || 'default';
	let cameraId = crypto.randomUUID().slice(0, 8);
	let video: HTMLVideoElement;
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let overlayCanvas: HTMLCanvasElement;
	let overlayCtx: CanvasRenderingContext2D;
	let resultText = 'Waiting for keypoints...';
	let socket: any;
	let streaming = false;
	let connectionStatus = 'Connecting...';
	let connectionColor = 'yellow';
	let debugLog: string[] = [];

	let handLandmarker: HandLandmarker;
	let poseLandmarker: PoseLandmarker;
	let lastVideoTime = -1;

	let availableCameras: MediaDeviceInfo[] = [];
	let selectedCameraId: string = '';
	let currentStream: MediaStream | null = null;

	function log(msg: string) {
		const timestamp = new Date().toLocaleTimeString();
		const logMsg = `[${timestamp}] ${msg}`;
		console.log(logMsg);
		debugLog = [logMsg, ...debugLog].slice(0, 10);
	}

	function drawPoint(
		ctx: CanvasRenderingContext2D,
		x: number,
		y: number,
		color: string,
		label?: string
	) {
		ctx.strokeStyle = color;
		ctx.fillStyle = color;
		ctx.beginPath();
		ctx.arc(x, y, 6, 0, Math.PI * 2);
		ctx.fill();
		ctx.stroke();
		if (label) {
			ctx.font = '12px sans-serif';
			ctx.fillText(label, x + 8, y - 6);
		}
	}

	function drawKeypoints(result: any) {
		if (!overlayCanvas || !video) return;

		// Match overlay size to video size
		if (overlayCanvas.width !== video.videoWidth || overlayCanvas.height !== video.videoHeight) {
			overlayCanvas.width = video.videoWidth;
			overlayCanvas.height = video.videoHeight;
		}

		const width = overlayCanvas.width;
		const height = overlayCanvas.height;
		overlayCtx.clearRect(0, 0, width, height);

		if (!result) return;

		const toPx = (value: number, dimension: number) => value * dimension;

		if (result.body) {
			Object.entries(result.body).forEach(([key, point]: [string, any]) => {
				if (point && point.x != null && point.y != null) {
					const px = toPx(point.x, width);
					const py = toPx(point.y, height);
					drawPoint(overlayCtx, px, py, 'lime', key);
				}
			});
		}

		['left', 'right'].forEach((side) => {
			const hand = result.hands?.[side];
			if (hand?.wrist) {
				const px = toPx(hand.wrist.x, width);
				const py = toPx(hand.wrist.y, height);
				const color = side === 'left' ? 'cyan' : 'orange';
				drawPoint(overlayCtx, px, py, color, `${side} wrist`);
			}
		});
	}

	function describeResult(result: any) {
		if (!result) {
			return 'No keypoints detected.';
		}
		const lines: string[] = [];
		if (result.body?.head) {
			lines.push(`Head: (${result.body.head.x.toFixed(2)}, ${result.body.head.y.toFixed(2)})`);
		}
		['left', 'right'].forEach((side) => {
			const hand = result.hands?.[side];
			if (hand) {
				lines.push(`${side} hand: ${hand.gesture} (${hand.fingers} fingers)`);
			}
		});
		return lines.length ? lines.join(' | ') : 'No hands detected.';
	}

	async function enumerateCameras() {
		try {
			const devices = await navigator.mediaDevices.enumerateDevices();
			availableCameras = devices.filter((device) => device.kind === 'videoinput');
			log(`Found ${availableCameras.length} cameras`);
			if (availableCameras.length > 0 && !selectedCameraId) {
				selectedCameraId = availableCameras[0].deviceId;
			}
		} catch (e: any) {
			log(`Failed to enumerate cameras: ${e.message}`);
		}
	}

	async function startCamera(deviceId?: string) {
		try {
			// Stop existing stream
			if (currentStream) {
				currentStream.getTracks().forEach((track) => track.stop());
			}

			const constraints: MediaStreamConstraints = {
				video: deviceId ? { deviceId: { exact: deviceId } } : { facingMode: 'user' }
			};

			currentStream = await navigator.mediaDevices.getUserMedia(constraints);
			video.srcObject = currentStream;
			await video.play();
			streaming = true;
			log(`Camera started: ${deviceId || 'default'}`);
		} catch (e: any) {
			log(`Failed to start camera: ${e.message}`);
		}
	}

	async function switchCamera() {
		if (selectedCameraId) {
			await startCamera(selectedCameraId);
		}
	}

	onMount(async () => {
		const origin = window.location.origin;
		log(`Page loaded, origin: ${origin}`);
		log(`Session: ${session_id}, Camera: ${cameraId}`);

		// Initialize MediaPipe
		try {
			const vision = await FilesetResolver.forVisionTasks(
				'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm'
			);
			handLandmarker = await HandLandmarker.createFromOptions(vision, {
				baseOptions: {
					modelAssetPath: '/models/hand_landmarker.task',
					delegate: 'GPU'
				},
				runningMode: 'VIDEO',
				numHands: 2
			});
			poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
				baseOptions: {
					modelAssetPath: '/models/pose_landmarker_lite.task',
					delegate: 'GPU'
				},
				runningMode: 'VIDEO'
			});
			log('MediaPipe initialized');
		} catch (e: any) {
			log(`MediaPipe init failed: ${e.message}`);
		}

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

		socket.on('result', (result: any) => {
			drawKeypoints(result);
			resultText = describeResult(result);
		});

		// Removed canvas creation for frame sending as we process locally now
		if (overlayCanvas) {
			overlayCtx = overlayCanvas.getContext('2d')!;
		}

		// Enumerate cameras first
		await enumerateCameras();

		// Start camera with selected device
		await startCamera(selectedCameraId || undefined);
		streaming = true;

		const processLoop = async () => {
			if (streaming && video && video.readyState >= video.HAVE_CURRENT_DATA) {
				const timestamp = performance.now();
				if (timestamp !== lastVideoTime) {
					lastVideoTime = timestamp;

					let result: any = { body: null, hands: { left: null, right: null } };

					if (poseLandmarker) {
						const poseResult = poseLandmarker.detectForVideo(video, timestamp);
						if (poseResult.landmarks && poseResult.landmarks.length > 0) {
							// Send the full landmark array (this is what the game expects)
							result.body = poseResult.landmarks[0];
						}
					}

					if (handLandmarker) {
						const handResult = handLandmarker.detectForVideo(video, timestamp);
						if (handResult.landmarks && handResult.handedness) {
							for (let i = 0; i < handResult.handedness.length; i++) {
								const handedness = handResult.handedness[i][0];
								const landmarks = handResult.landmarks[i];
								const side = handedness.categoryName.toLowerCase(); // "Left" or "Right" -> "left" or "right"

								// Simple gesture detection (count extended fingers)
								// Tips: 4 (Thumb), 8 (Index), 12 (Middle), 16 (Ring), 20 (Pinky)
								// PIPs: 2, 6, 10, 14, 18
								let fingers = 0;
								// Thumb is tricky, check x distance for now or skip
								if (landmarks[4].y < landmarks[3].y) fingers++; // Very rough
								if (landmarks[8].y < landmarks[6].y) fingers++;
								if (landmarks[12].y < landmarks[10].y) fingers++;
								if (landmarks[16].y < landmarks[14].y) fingers++;
								if (landmarks[20].y < landmarks[18].y) fingers++;

								result.hands[side] = {
									fingers: fingers,
									gesture: fingers > 0 ? 'open' : 'closed', // Placeholder
									wrist: { x: landmarks[0].x, y: landmarks[0].y }
								};
							}
						}
					}

					// Draw locally using the landmark array
					if (result.body) {
						const lm = result.body;
						const width = overlayCanvas.width;
						const height = overlayCanvas.height;
						overlayCtx.clearRect(0, 0, width, height);

						// Draw key pose points
						const keyPoints = [
							{ idx: 0, label: 'nose', color: 'yellow' },
							{ idx: 11, label: 'L_shoulder', color: 'lime' },
							{ idx: 12, label: 'R_shoulder', color: 'lime' },
							{ idx: 13, label: 'L_elbow', color: 'cyan' },
							{ idx: 14, label: 'R_elbow', color: 'cyan' }
						];

						keyPoints.forEach(({ idx, label, color }) => {
							if (lm[idx]) {
								const px = lm[idx].x * width;
								const py = lm[idx].y * height;
								drawPoint(overlayCtx, px, py, color, label);
							}
						});

						// Update result text with shoulder Y position
						resultText = `Shoulder Y: ${lm[12]?.y.toFixed(2) || 'N/A'}`;
					}

					// Draw hands
					['left', 'right'].forEach((side) => {
						const hand = result.hands?.[side];
						if (hand?.wrist) {
							const px = hand.wrist.x * overlayCanvas.width;
							const py = hand.wrist.y * overlayCanvas.height;
							const color = side === 'left' ? 'cyan' : 'orange';
							drawPoint(overlayCtx, px, py, color, `${side} wrist`);
						}
					});

					// Send result to server with full body landmark array
					if (socket && socket.connected) {
						socket.emit('result', { cameraId, result, timestamp: Date.now() });
					}
				}
			}
			requestAnimationFrame(processLoop);
		};
		requestAnimationFrame(processLoop);
	});
</script>

<div class="container">
	<h2>Camera Streaming</h2>

	{#if availableCameras.length > 1}
		<div class="camera-picker">
			<label for="cameraSelect">Select Camera:</label>
			<select id="cameraSelect" bind:value={selectedCameraId} on:change={switchCamera}>
				{#each availableCameras as camera}
					<option value={camera.deviceId}>
						{camera.label || `Camera ${availableCameras.indexOf(camera) + 1}`}
					</option>
				{/each}
			</select>
		</div>
	{/if}

	<div id="streamContainer">
		<video bind:this={video} id="localVideo" autoplay muted playsinline></video>
		<canvas bind:this={overlayCanvas} id="overlayCanvas"></canvas>
	</div>
	<div id="resultInfo">{resultText}</div>
</div>

<style>
	:global(body) {
		font-family: 'Segoe UI', system-ui, sans-serif;
		margin: 0;
		background: #f0f0f0;
		color: #333;
	}

	.container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		padding: 1rem;
	}

	h2 {
		margin: 0 0 1rem 0;
	}

	.camera-picker {
		margin-bottom: 1rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.camera-picker label {
		font-weight: 600;
	}

	.camera-picker select {
		padding: 0.5rem 1rem;
		font-size: 14px;
		border-radius: 4px;
		border: 2px solid #4caf50;
		background: #fff;
		color: #333;
		cursor: pointer;
	}

	.camera-picker select:hover {
		border-color: #66ff66;
	}

	#streamContainer {
		position: relative;
		width: 100vw;
		max-width: 640px;
		aspect-ratio: 4/3;
		background: #000;
		overflow: hidden;
		margin-bottom: 1rem;
	}

	#localVideo,
	#overlayCanvas {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		object-fit: contain;
		/* transform: scaleX(-1); Flip horizontally */
	}

	#overlayCanvas {
		pointer-events: none;
	}

	#resultInfo {
		max-width: 640px;
		width: 100%;
		font-family: 'Segoe UI', system-ui, sans-serif;
		line-height: 1.4;
		background: #fff;
		padding: 1rem;
		border-radius: 8px;
		box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
	}
</style>
