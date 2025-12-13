<script lang="ts">
	import { onMount } from 'svelte';
	import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision';

	let video: HTMLVideoElement;
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null = null;
	let debug: boolean = false;

	onMount(async () => {
		ctx = canvas.getContext('2d');

		// Load MediaPipe vision tasks
		const vision = await FilesetResolver.forVisionTasks(
			'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
		);

		const handLandmarker = await HandLandmarker.createFromOptions(vision, {
			baseOptions: { modelAssetPath: '/models/hand_landmarker.task' },
			numHands: 2
		});

		// Set running mode to VIDEO
		handLandmarker.setOptions({ runningMode: 'VIDEO' });

		// Start webcam
		const stream = await navigator.mediaDevices.getUserMedia({ video: true });
		video.srcObject = stream;

		await video.play();

		let lastVideoTime = -1;

		function processResults(results: any) {
			if (!ctx) return;

			// Clear canvas
			ctx.clearRect(0, 0, canvas.width, canvas.height);

			// Draw video (mirrored like OpenCV)
			ctx.save();
			ctx.scale(-1, 1);
			ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
			ctx.restore();

			// Check if landmarks exist
			if (results.landmarks) {
				results.landmarks.forEach((hand: any, index: number) => {
					if (debug) {
						console.log(`Hand ${index + 1}:`);
						console.log('Landmarks:', hand); // raw x, y, z
						if (results.handedness) {
							console.log('Handedness:', results.handedness[index]); // e.g., Right or Left
						}
					}

					// Draw landmarks on canvas
					ctx.fillStyle = 'red';
					for (const point of hand) {
						ctx.beginPath();
						ctx.arc(point.x * canvas.width, point.y * canvas.height, 5, 0, 2 * Math.PI);
						ctx.fill();
					}
				});
			} else {
				if (debug) {
					console.log('No hands detected');
				}
			}
		}

		function renderLoop() {
			if (video.currentTime !== lastVideoTime) {
				const results = handLandmarker.detectForVideo(video, performance.now());
				processResults(results);
				lastVideoTime = video.currentTime;
			}
			requestAnimationFrame(renderLoop);
		}

		renderLoop();
	});
</script>

<canvas bind:this={canvas} width="640" height="480"></canvas>
<video bind:this={video} autoplay playsinline hidden></video>
