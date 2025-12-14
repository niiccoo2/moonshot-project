<script lang="ts">
	import { onMount } from 'svelte';
	import { FilesetResolver, HandLandmarker, PoseLandmarker } from '@mediapipe/tasks-vision';
	import Game from '$lib/Game.svelte';

	const WIDTH: number = 640;
	const HEIGHT: number = 480;

	let video: HTMLVideoElement;
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null = null;
	let debug: boolean = false;
	let lastProcessTime = 0;
	const PROCESS_INTERVAL = 1000 / 15; // 15 fps

	let input = {
		jumping: false,
		crouching: false,
		prevJumping: false,
		movingRight: false,
		movingLeft: false
	};

	onMount(async () => {
		ctx = canvas.getContext('2d');

		// Load MediaPipe vision tasks
		const vision = await FilesetResolver.forVisionTasks(
			'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
		);

		const poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
			baseOptions: {
				modelAssetPath: '/models/pose_landmarker_lite.task'
			},
			runningMode: 'VIDEO'
		});

		poseLandmarker.setOptions({ runningMode: 'VIDEO' });

		// Start webcam
		const stream = await navigator.mediaDevices.getUserMedia({ video: true });
		video.srcObject = stream;

		await video.play();

		function processResults(poseLandmarkerResult: any) {
			if (!ctx) return;

			// Clear canvas
			ctx.clearRect(0, 0, canvas.width, canvas.height);

			// Draw video (mirrored like OpenCV)
			ctx.save();
			ctx.scale(-1, 1);
			ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
			ctx.restore();

			if (poseLandmarkerResult.landmarks) {
				poseLandmarkerResult.landmarks.forEach((pose: any, index: number) => {
					// console.log('Left shoulder:', pose[12].y); // so laggy
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
					if (debug) {
						console.log(`Pose ${index + 1}:`);
						console.log('Landmarks:', pose);
					}
					if (ctx == null) {
						return;
					}
					ctx.fillStyle = 'blue';
					for (const point of pose) {
						const px = (1 - point.x) * canvas.width; // flip horizontally
						const py = point.y * canvas.height;
						ctx.beginPath();
						ctx.arc(px, py, 5, 0, 2 * Math.PI);
						ctx.fill();
					}
				});
			} else {
				if (debug) {
					console.log('No pose detected');
				}
			}
		}

		function renderLoop() {
			const process = () => {
				const now = performance.now();
				if (now - lastProcessTime > PROCESS_INTERVAL) {
					const poseLandmarkerResult = poseLandmarker.detectForVideo(video, now);
					processResults(poseLandmarkerResult);

					lastProcessTime = now;
				}
				video.requestVideoFrameCallback(process);
			};
			video.requestVideoFrameCallback(process);
		}

		renderLoop();
	});
</script>

<canvas bind:this={canvas} width={WIDTH} height={HEIGHT} class="canvas-overlay" hidden></canvas>

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
