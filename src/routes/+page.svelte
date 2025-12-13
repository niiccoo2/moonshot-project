<script lang="ts">
	import * as tf from '@tensorflow/tfjs';
	import * as mobilenet from '@tensorflow-models/mobilenet';
	import { onMount } from 'svelte';

	let video: HTMLVideoElement;

	onMount(async () => {
		const stream = await navigator.mediaDevices.getUserMedia({
			video: {
				width: 640,
				height: 480
			}
		});

		video.srcObject = stream;
		await video.play();
	});
</script>

<video bind:this={video} autoplay playsinline style="transform: scaleX(-1);"></video>
