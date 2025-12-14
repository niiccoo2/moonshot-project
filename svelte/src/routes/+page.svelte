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

	let leftHandPos = { x: 0.5, y: 0.5 };
	let rightHandPos = { x: 0.5, y: 0.5 };

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

		const handLandmarker = await HandLandmarker.createFromOptions(vision, {
			baseOptions: { modelAssetPath: '/models/hand_landmarker.task' },
			numHands: 2
		});

		const poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
			baseOptions: {
				modelAssetPath: '/models/pose_landmarker_lite.task'
			},
			runningMode: 'VIDEO'
		});

		// Set running mode to VIDEO
		handLandmarker.setOptions({ runningMode: 'VIDEO' });
		poseLandmarker.setOptions({ runningMode: 'VIDEO' });

		// Start webcam
		const stream = await navigator.mediaDevices.getUserMedia({ video: true });
		video.srcObject = stream;

		await video.play();

		function countFingers(handLandmarks: any, handedness: string) {
			let fingers = [];

			// Thumb
			if (handedness == 'Right') {
				fingers.push(handLandmarks.landmark[4].x > handLandmarks.landmark[3].x);
			} else {
				fingers.push(handLandmarks.landmark[4].x < handLandmarks.landmark[3].x);
			}

			for (const tip of [8, 12, 16, 20]) {
				fingers.push(handLandmarks.landmark[tip].y < handLandmarks.landmark[Number(tip) - 2].y);
			}

			const sum = fingers.reduce((acc, b) => acc + (b ? 1 : 0), 0);

			return sum;
		}

		function detectGesture(fingerCount: number) {
			if (fingerCount === 0) {
				return 'closed';
			} else if (fingerCount === 5) {
				return 'open';
			} else {
				return 'unknown';
			}
		}

		function processResults(poseLandmarkerResult: any) {
			if (!ctx) return;

			// Clear canvas
			ctx.clearRect(0, 0, canvas.width, canvas.height);

			// Draw video (mirrored like OpenCV)
			ctx.save();
			ctx.scale(-1, 1);
			ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
			ctx.restore();

			// Check if landmarks exist
			// if (handLandmarkerResult.landmarks) {
			// 	handLandmarkerResult.landmarks.forEach((hand: any, index: number) => {
			// 		if (debug) {
			// 			console.log(`Hand ${index + 1}:`);
			// 			console.log('Landmarks:', hand); // raw x, y, z
			// 			if (handLandmarkerResult.handedness) {
			// 				console.log('Handedness:', handLandmarkerResult.handedness[index]); // e.g., Right or Left
			// 			}
			// 		}
			// 		if (ctx == null) {
			// 			return;
			// 		}
			// 		// Draw landmarks on canvas
			// 		ctx.fillStyle = 'red';
			// 		for (const point of hand) {
			// 			// ctx.scale(-1, 1);
			// 			const px = (1 - point.x) * canvas.width; // flip horizontally
			// 			const py = point.y * canvas.height;
			// 			ctx.beginPath();
			// 			ctx.arc(px, py, 5, 0, 2 * Math.PI);
			// 			ctx.fill();
			// 		}
			// 	});
			// } else {
			// 	if (debug) {
			// 		console.log('No hands detected');
			// 	}
			// }
			if (poseLandmarkerResult.landmarks) {
				poseLandmarkerResult.landmarks.forEach((pose: any, index: number) => {
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
					// const handLandmarkerResult = handLandmarker.detectForVideo(video, now);
					const poseLandmarkerResult = poseLandmarker.detectForVideo(video, now);
					processResults(poseLandmarkerResult);

					// handLandmarkerResult.landmarks.forEach((hand, index) => {
					// 	const handedness = handLandmarkerResult.handedness[index][0].categoryName; // "Left" or "Right"
					// 	if (handedness === 'Left') {
					// 		leftHandPos = { x: -hand[0].x, y: hand[0].y }; // did - because we flip it
					// 	} else if (handedness === 'Right') {
					// 		rightHandPos = { x: -hand[0].x, y: hand[0].y }; // idk if this is the best place to do the flip tho
					// 	}
					// });
					// if (handLandmarkerResult.landmarks && handLandmarkerResult.handedness) {
					// 	handLandmarkerResult.landmarks.forEach((hand: any, index: number) => {
					// 		const handedness =
					// 			handLandmarkerResult.handedness[index]?.[0]?.categoryName || 'Right';
					// 		console.log(countFingers({ landmark: hand }, handedness));
					// 	});
					// }
					lastProcessTime = now;
				}
				video.requestVideoFrameCallback(process);
			};
			video.requestVideoFrameCallback(process);
		}

		renderLoop();
	});
</script>

<video bind:this={video} autoplay playsinline style="transform: scaleX(-1);" class="video-bg" hidden
></video>
<canvas bind:this={canvas} width={WIDTH} height={HEIGHT} class="canvas-overlay" hidden></canvas>
<Game {input} />
