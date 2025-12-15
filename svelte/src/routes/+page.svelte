<script lang="ts">
	import { onMount } from 'svelte';
	import Game from '$lib/Game.svelte';
	import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';

	const WIDTH: number = 640;
	const HEIGHT: number = 480;

	let video: HTMLVideoElement;
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null = null;
	let debug: boolean = false;
	let poseLandmarker: any;
	let lastProcessTime = 0;
	const PROCESS_INTERVAL = 200; // Process every 200ms (5 fps) for better performance

	let input = {
		jumping: false,
		crouching: false,
		prevJumping: false,
		movingRight: false,
		movingLeft: false
	};

	async function startVideo() {
		console.log('Starting video');
		const stream = await navigator.mediaDevices.getUserMedia({
			video: { width: 320, height: 240 } // Lower resolution for better performance
		});
		video.srcObject = stream;
		await video.play();
		console.log('Video is playing');
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

	function processResults(poseLandmarkerResult: any) {
		if (poseLandmarkerResult.landmarks && poseLandmarkerResult.landmarks.length > 0) {
			const pose = poseLandmarkerResult.landmarks[0];
			if (pose[12].y < 0.33) {
				input.jumping = true;
				input.crouching = false;
			} else if (pose[12].y > 0.66) {
				input.crouching = true;
				input.jumping = false;
			} else {
				input.jumping = false;
				input.crouching = false;
			}
		}
	}

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
		startVideo();
	});
</script>

<div id="game-root">
	<Game {input} />
	<video bind:this={video} autoplay playsinline style="transform: scaleX(-1);" class="video-overlay"
	></video>
</div>

<style>
	.video-overlay {
		position: absolute;
		top: 16px;
		right: 16px;
		width: 240px;
		height: 180px;
		border: 2px solid #fff;
		border-radius: 8px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
		z-index: 10;
		background: #000;
		object-fit: cover;
	}
	#game-root {
		position: relative;
		width: 100vw;
		height: 100vh;
		overflow: hidden;
	}
</style>
