<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import Game from '$lib/Game.svelte';
	import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';
	import { io } from 'socket.io-client';
	import '$lib/main.css';
	import QRCode from '$lib/QR-Code.svelte';

	let session_id = $page.url.searchParams.get('session1') || randomLetters4();
	let video: HTMLVideoElement;
    // --- New Audio Variable ---
	let backgroundMusic: HTMLAudioElement; 
    // --------------------------
	let remoteCameras: Map<string, boolean> = new Map();
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
    
    // --- Audio Control Function ---
    function startMusic() {
        if (backgroundMusic) {
            // Find the element if not already bound
            if (!backgroundMusic.src) {
                 backgroundMusic = document.getElementById('bgm') as HTMLAudioElement;
            }
            
            // Check if music is already playing to avoid restarting the loop unnecessarily
            if (backgroundMusic.paused) {
                backgroundMusic.volume = 0.5; // Set volume (adjust as needed)
                backgroundMusic.play().catch(e => {
                    console.warn("Autoplay prevented, waiting for user interaction.", e);
                });
            }
        }
    }
    // ------------------------------

	// Logic for LOCAL camera (MediaPipe running in this browser)
	function processResults(poseLandmarkerResult: any) {
		if (poseLandmarkerResult.landmarks && poseLandmarkerResult.landmarks.length > 0) {
			const pose = poseLandmarkerResult.landmarks[0];

			// Calculate shoulder position for debug
			if (pose[12]) {
				debugInfo.shoulderY = pose[12].y;
			}
            
            // --- JUMP/CROUCH LOGIC ---
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
            // --- END JUMP/CROUCH LOGIC ---

			// Update debug info
			debugInfo.jumping = input.jumping;
			debugInfo.crouching = input.crouching;
			debugInfo.remoteCameras = remoteCameras.size;
            
            // NOTE: If the game starts based purely on the first input,
            // this is the place where you could call startMusic() if Game.svelte
            // doesn't dispatch an event. However, using the event is cleaner.
		}
	}

	function setupRemoteCameras() {
		const origin = window.location.origin;
		log(`Setting up remote cameras`);

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

		// Listen for processed results instead of raw frames
		socket.on('result', (data: { cameraId: string; result: any }) => {
			const { cameraId, result } = data;

			// Register new camera if not seen before
			if (!remoteCameras.has(cameraId)) {
				log(`✓ New camera connected: ${cameraId}`);
				remoteCameras.set(cameraId, true);
				debugInfo.remoteCameras = remoteCameras.size;
				cameraList = Array.from(remoteCameras.keys());
				// Auto-select first remote camera if local camera is disabled or default
				if (!useLocalCamera && selectedCamera === 'local' && cameraList.length === 1) {
					selectedCamera = cameraId;
					log(`Auto-selected camera: ${cameraId}`);
				}
			}

			// Only process data from the selected camera
			if (selectedCamera !== 'local' && cameraId !== selectedCamera) {
				return;
			}

			// Map the received JSON data to game inputs
			if (result && result.body) {
				const shoulder = result.body.right_shoulder; // Using right shoulder as in local logic

				if (shoulder) {
					debugInfo.shoulderY = shoulder.y;

					// Same logic as processResults: < 0.33 jump, > 0.66 crouch
					if (shoulder.y < 0.33) {
						input.jumping = true;
						input.crouching = false;
					} else if (shoulder.y > 0.66) {
						input.crouching = true;
						input.jumping = false;
					} else {
						input.jumping = false;
						input.crouching = false;
					}

					// Update debug info
					debugInfo.jumping = input.jumping;
					debugInfo.crouching = input.crouching;
				}
			}
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
        
        // --- Get Audio Reference ---
        // We get the reference here, but defer calling startMusic() until gameStart event.
        backgroundMusic = document.getElementById('bgm') as HTMLAudioElement;
        // ----------------------------------------------------
	});

    onDestroy(() => {
        if (socket) {
            socket.disconnect();
        }
        if (backgroundMusic) {
            backgroundMusic.pause();
        }
    });
</script>

{#if showQRModal}
	<QRCode {session_id} onClose={() => (showQRModal = false)}></QRCode>
{/if}

<div id="game-root">
    <Game {input} on:gameStart={startMusic} />
    
        <audio id="bgm" loop preload="auto" src="/audio/background-music.mp3"></audio>

	<!-- Local camera preview (only visible if local is selected) -->
	{#if selectedCamera === 'local' && useLocalCamera}
		<video
			bind:this={video}
			autoplay
			playsinline
			style="transform: scaleX(-1);"
			class="video-overlay camera-preview"
		></video>
	{/if}

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


<style>
	/* NOTE: Ensure all other necessary styles are included in your actual main.css */

	.video-overlay {
        position: absolute;
        bottom: 20px;
        right: 20px;
        width: 160px;
        height: 120px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        z-index: 5;
    }

	.camera-preview {
        /* ensures the video content is visible */
	}
	
	.camera-selector {
        position: absolute;
        bottom: 145px;
        right: 20px;
        background: rgba(0, 0, 0, 0.7);
        color: white;
        padding: 8px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 5;
	}

	.bottom-left-info {
        position: absolute;
        bottom: 20px;
        left: 20px;
        color: white;
        z-index: 5;
        font-family: Arial, sans-serif;
	}

	.remote-indicator {
        background: rgba(0, 0, 0, 0.7);
        padding: 8px;
        border-radius: 8px;
        font-size: 14px;
        line-height: 1.4;
	}

    .session-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 15px; /* Spacing between info and button */
    }

    .connect-btn {
        background-color: #ffcc00;
        color: #000;
        border: none;
        padding: 8px 12px;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
        transition: background-color 0.2s;
    }

    .connect-btn:hover {
        background-color: #ffda5a;
    }

	.debug-overlay {
        margin-top: 10px;
        background: rgba(0, 0, 0, 0.9);
        padding: 10px;
        border-radius: 8px;
        font-size: 12px;
	}
    .debug-overlay h3 {
        margin-top: 0;
        font-size: 14px;
        color: #ffcc00;
    }
    .debug-overlay p {
        margin: 4px 0;
    }
</style>