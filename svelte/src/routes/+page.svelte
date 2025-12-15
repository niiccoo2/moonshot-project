<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import Game from '$lib/Game.svelte';
	import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';
	import { io } from 'socket.io-client';
	import '$lib/main.css';

	let session_id = $page.url.searchParams.get('session') || randomLetters4();
	let video: HTMLVideoElement;
	let remoteCameras: Map<string, HTMLImageElement> = new Map();
	let cameraDisplayUrls: Map<string, string> = new Map();
	let poseLandmarker: any;
	let lastProcessTime = 0;
	const PROCESS_INTERVAL = 200;
	let socket: any;
	let useLocalCamera = true;
	let selectedCamera = 'local';
	let cameraList: string[] = [];

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

	// --- Leaderboard State (PRESERVED) ---
	type LeaderboardEntry = {
		id: number;
		score: number;
		level: number;
		date: string;
	};
	let leaderboard: LeaderboardEntry[] = [];
	const MAX_ENTRIES = 5;
	// -------------------------------------

	// --- Music State and Functions (NEW) ---
	let audio: HTMLAudioElement;
	let musicStarted = false;
	// IMPORTANT: Update this path to your actual audio file location.
	const MUSIC_FILE = '/audio/background-music.mp3'; 

	function startMusic() {
		if (!musicStarted && typeof audio !== 'undefined' && audio) {
			audio.loop = true;
			audio.volume = 0.5; 
			
			const playPromise = audio.play();

			if (playPromise !== undefined) {
				playPromise.then(_ => {
					musicStarted = true;
					log('Background music started.');
				})
				.catch(error => {
					log('Music playback blocked. Awaiting user interaction.');
				});
			}
		}
	}
	
	function tryStartMusic() {
		if (!musicStarted) {
			startMusic();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		// Try to start music on any keypress used to control the game (Space, S)
		if (!musicStarted && (e.code === 'Space' || e.code === 'ArrowDown' || e.code === 'KeyS')) {
			tryStartMusic();
		}
	}
	// ---------------------------------------

	function randomLetters4() {
		const letters = 'abcdefghijklmnopqrstuvwxyz';
		const result = new Array(4);
		const bytes = crypto.getRandomValues(new Uint8Array(4));
		for (let i = 0; i < 4; i++) {
			result[i] = letters[bytes[i] % letters.length];
		}
		return result.join('');
	}

	function log(msg: string) {
		if (debug) console.log(msg);
	}

	// --- Leaderboard Functions (PRESERVED) ---

	function loadLeaderboard() {
		if (typeof localStorage !== 'undefined') {
			const saved = localStorage.getItem('spaceCowLeaderboard');
			if (saved) {
				leaderboard = JSON.parse(saved);
			}
		}
	}

	function saveLeaderboard() {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('spaceCowLeaderboard', JSON.stringify(leaderboard));
		}
	}

	function addScoreToLeaderboard(newScore: number, newLevel: number) {
		const newEntry: LeaderboardEntry = {
			id: Date.now(),
			score: newScore,
			level: newLevel,
			date: new Date().toLocaleDateString()
		};

		leaderboard.push(newEntry);

		// Sort by score (descending), then by level (descending)
		leaderboard.sort((a, b) => {
			if (b.score !== a.score) {
				return b.score - a.score;
			}
			return b.level - a.level;
		});

		// Keep only the top MAX_ENTRIES
		leaderboard = leaderboard.slice(0, MAX_ENTRIES);

		saveLeaderboard();
	}
	// -----------------------------------------

	function processResults(poseLandmarkerResult: any) {
		// Trigger music on the first detected user movement
		if ((input.jumping || input.crouching) && !musicStarted) {
			tryStartMusic();
		}

		if (poseLandmarkerResult.landmarks && poseLandmarkerResult.landmarks.length > 0) {
			const pose = poseLandmarkerResult.landmarks[0];

			// Calculate shoulder position for debug
			if (pose[12]) {
				debugInfo.shoulderY = pose[12].y;
			}
            // 
            
			// Pose-to-Input Logic
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
		// 
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
		
		// Load the leaderboard from local storage
		loadLeaderboard(); 

		// Always start local camera
		if (useLocalCamera) {
			startLocalVideo();
		}

		setupRemoteCameras();
		
		// Attach the music start listener
		document.addEventListener('keydown', handleKeydown);
		
		// Attempt to start music immediately (will be blocked until user interaction)
		startMusic();
	});
	
	onDestroy(() => {
		if (typeof document !== 'undefined') {
			document.removeEventListener('keydown', handleKeydown);
		}
	});
</script>

<div id="game-root">
	<audio bind:this={audio} src={MUSIC_FILE} preload="auto"></audio>
	
	<Game {input} onGameOver={addScoreToLeaderboard} />

	<div class="leaderboard-overlay">
		<h3>🏆 Leaderboard</h3>
		{#if leaderboard.length > 0}
			<table>
				<thead>
					<tr>
						<th>#</th>
						<th>Score</th>
						<th>Level</th>
						<th>Date</th>
					</tr>
				</thead>
				<tbody>
					{#each leaderboard as entry, i}
						<tr>
							<td>{i + 1}</td>
							<td>{entry.score}</td>
							<td>{entry.level}</td>
							<td>{entry.date}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			<p>No scores yet. Be the first!</p>
		{/if}
	</div>

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
				on:change={() => log(`Switched to camera: ${selectedCamera}`)}
			>
				<option value="local">Local Camera</option>
				{#each cameraList as camId}
					<option value={camId}>Remote: {camId}</option>
				{/each}
			</select>
		</div>
	{/if}

	<div class="bottom-left-info">
		<div class="remote-indicator">
			<strong>Session:</strong>
			{session_id}
			<br />
			<strong>Remote Cameras:</strong>
			{remoteCameras.size}
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
	/* ... (Existing styles for #game-root, .video-overlay, etc. remain here) ... */
	
	.video-overlay {
		position: absolute;
		top: 10px;
		right: 10px;
		width: 160px; /* Smaller size for preview */
		height: 120px;
		border: 3px solid #fff;
		border-radius: 8px;
		object-fit: cover;
		z-index: 5;
		box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
	}

	.camera-preview {
		/* Specific styles for the video element */
	}
	
	.camera-selector {
		position: absolute;
		top: 140px;
		right: 10px;
		padding: 5px;
		background: rgba(0, 0, 0, 0.7);
		color: white;
		border-radius: 5px;
		z-index: 5;
		font-size: 12px;
	}

	.bottom-left-info {
		position: absolute;
		bottom: 10px;
		left: 10px;
		z-index: 5;
	}

	.remote-indicator {
		background: rgba(0, 0, 0, 0.7);
		color: white;
		padding: 10px;
		border-radius: 5px;
		font-size: 14px;
	}

	.debug-overlay {
		background: rgba(0, 0, 0, 0.85);
		color: white;
		padding: 10px;
		border-radius: 5px;
		margin-top: 10px;
		font-family: monospace;
		font-size: 12px;
	}

	.debug-overlay h3 {
		margin-top: 0;
		font-size: 14px;
		border-bottom: 1px solid #333;
		padding-bottom: 5px;
		margin-bottom: 5px;
	}
	
	/* --- LEADERBOARD STYLES --- */
	.leaderboard-overlay {
		position: absolute;
		top: 20px;
		left: 20px;
		background: rgba(0, 0, 0, 0.7);
		color: white;
		padding: 15px;
		border-radius: 10px;
		max-width: 300px;
		z-index: 5;
		box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
	}

	.leaderboard-overlay h3 {
		margin-top: 0;
		font-size: 20px;
		color: #ffcc00;
	}

	.leaderboard-overlay table {
		width: 100%;
		border-collapse: collapse;
		font-size: 14px;
	}

	.leaderboard-overlay th, .leaderboard-overlay td {
		padding: 5px 10px;
		text-align: left;
		border-bottom: 1px solid rgba(255, 255, 255, 0.2);
	}

	.leaderboard-overlay th {
		color: #aaa;
		font-weight: bold;
	}

	.leaderboard-overlay p {
		font-style: italic;
	}
</style>