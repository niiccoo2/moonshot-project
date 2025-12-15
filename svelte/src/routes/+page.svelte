<script lang="ts">
	import { onMount } from 'svelte';
	import Game from '$lib/Game.svelte';
	import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';

	const WIDTH: number = 640;
	const HEIGHT: number = 480;

	let video: HTMLVideoElement;
	let poseLandmarker: any;
	let lastProcessTime = 0;
	const PROCESS_INTERVAL = 33; // ~30fps for better responsiveness

	let input = {
		jumping: false,
		crouching: false,
		prevJumping: false,
		movingRight: false,
		movingLeft: false
	};

	// Baseline for crouch detection
	let baselineHipY: number | null = null;
	let prevHipY: number | null = null;
	const jumpThreshold = 0.05; // reduced for more sensitivity
	const crouchThreshold = 0.1; // distance below baseline
	const minConfidence = 0.5; // ignore weak detections
	let jumpHoldTime = 200; // ms to keep jump state
	let crouchHoldTime = 500; // ms to keep crouch state
	let jumpTimer: number | null = null;
	let crouchTimer: number | null = null;

	async function startVideo() {
		const stream = await navigator.mediaDevices.getUserMedia({
			video: { width: 320, height: 240 }
		});
		video.srcObject = stream;
		await video.play();
		requestFrame();
	}

	function requestFrame() {
		const now = performance.now();
		if (now - lastProcessTime > PROCESS_INTERVAL && poseLandmarker) {
			const result = poseLandmarker.detectForVideo(video, now);
			processResults(result);
			lastProcessTime = now;
		}
		requestAnimationFrame(requestFrame);
	}

	function processResults(result: any) {
		if (!result.landmarks || result.landmarks.length === 0) return;

		const pose = result.landmarks[0];

		// Check confidence on key landmarks (hips, knees)
		const leftHip = pose[23];
		const rightHip = pose[24];
		const leftKnee = pose[25];
		const rightKnee = pose[26];

		if (
			!leftHip.visibility ||
			!rightHip.visibility ||
			leftHip.visibility < minConfidence ||
			rightHip.visibility < minConfidence
		) {
			return;
		}

		// Average hip Y position
		const hipY = (leftHip.y + rightHip.y) / 2;
		const kneeY = (leftKnee.y + rightKnee.y) / 2;

		// Initialize baseline on first confident frame
		if (baselineHipY === null) {
			baselineHipY = hipY;
			prevHipY = hipY;
			return;
		}

		// Jump detection (sudden upward movement)
		// Jump detection (sudden upward movement)
		if (prevHipY !== null) {
			const deltaY = prevHipY - hipY; // positive = moving up
			if (deltaY > jumpThreshold) {
				input.jumping = true;
				if (jumpTimer) clearTimeout(jumpTimer);
				jumpTimer = window.setTimeout(() => {
					input.jumping = false;
				}, jumpHoldTime);
			}
		}

		// Crouch detection (hips significantly lower than baseline)
		const crouchDelta = hipY - baselineHipY; // positive = lower (crouch)
		if (crouchDelta > crouchThreshold) {
			input.crouching = true;
			if (crouchTimer) clearTimeout(crouchTimer);
		} else {
			// Only clear crouch when standing back up
			input.crouching = false;
			if (crouchTimer) clearTimeout(crouchTimer);
		}

		prevHipY = hipY;
	}
	onMount(async () => {
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
			numPoses: 1,
			minPoseDetectionConfidence: 0.5,
			minTrackingConfidence: 0.5
		});

		startVideo();
	});
</script>

<div id="game-root">
	<Game {input} />
	<video
		bind:this={video}
		autoplay
		playsinline
		muted
		style="transform: scaleX(-1);"
		class="video-overlay"
	></video>
</div>
