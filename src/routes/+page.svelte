<script lang="ts">
	import * as tf from '@tensorflow/tfjs';
	import * as mobilenet from '@tensorflow-models/mobilenet';
	import { onMount } from 'svelte';
	import { draw } from 'svelte/transition';

	let video: HTMLVideoElement;
	let model: mobilenet.MobileNet | undefined;
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null;

	async function loadModel() {
		model = await mobilenet.load();
	}

	function drawFlippedVideo() {
		if (!ctx) return;
		ctx.save();
		ctx.scale(-1, 1); // mirror horizontally
		ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
		ctx.restore();
	}

	let prediction = '';

	async function predict() {
		if (!model) return;
		const predictions = await model.classify(canvas);
		if (predictions.length > 0) {
			prediction = `${predictions[0].className} (${predictions[0].probability.toFixed(2)})`;
		}
	}

	function loop() {
		drawFlippedVideo();
		if (model) predict();
		requestAnimationFrame(loop);
	}

	onMount(async () => {
		const stream = await navigator.mediaDevices.getUserMedia({
			video: { width: 640, height: 480 }
		});
		video.srcObject = stream;
		await video.play(); // make sure video is showing ASAP
		ctx = canvas.getContext('2d');
		requestAnimationFrame(loop);

		await loadModel(); // load model in background
	});
</script>

<canvas bind:this={canvas} width="640" height="480"></canvas>
<video bind:this={video} autoplay playsinline style="transform: scaleX(-1);" hidden></video>
<p>Prediction: {prediction}</p>
