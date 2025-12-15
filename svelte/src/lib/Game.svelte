<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { io } from 'socket.io-client';

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let animationFrame: number;
	let socket: any;
	let video: HTMLVideoElement;
	let cameraCanvas: HTMLCanvasElement;
	let cameraCtx: CanvasRenderingContext2D;
	let cameraInterval: ReturnType<typeof setInterval>;
	let inputInterval: ReturnType<typeof setInterval>;

	const GROUND_RATIO = 0.75;

	// Game state
	type Obstacle = {
		x: number;
		y: number;
		width: number;
		height: number;
		type: string;
	};
	type Meteor = {
		x: number;
		y: number;
		size: number;
		speedY: number;
		speedX: number;
	};

	let game = {
		state: 'waiting',
		level: 1,
		score: 0,
		speed: 6,
		countdown: 3,
		player: {
			x: 0,
			y: 0,
			width: 120,
			height: 100,
			velocityY: 0,
			grounded: true,
			crouching: false
		},
		obstacles: [] as Obstacle[],
		meteors: [] as Meteor[],
		obstacleTimer: 0,
		levelProgress: 0,
		levelGoal: 10
	};

	export let input = {
		jumping: false,
		crouching: false,
		prevJumping: false,
		movingRight: false,
		movingLeft: false
	};

	let debugInfo = {
		baseline: 0,
		current: 0,
		diff: 0,
		bodyDetected: false,
		baselineReady: false
	};

	let shoulderYHistory: number[] = [];
	const BASELINE_SIZE = 45;
	const DETECTION_SIZE = 3;
	let currentShoulderY: number[] = [];
	let baselineEstablished = false;
	let lastBodyData: any = null;

	let showCountdown = false;
	let countdownText = '';
	let showGameOver = false;
	let finalScore = '';
	let finalLevel = '';

	function resizeCanvas() {
		if (canvas) {
			canvas.width = window.innerWidth;
			canvas.height = window.innerHeight;
		}
	}

	// Audio synthesis
	function playSound(freq: number, duration: number, type: OscillatorType = 'sine') {
		const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
		const osc = audioCtx.createOscillator();
		const gain = audioCtx.createGain();
		osc.connect(gain);
		gain.connect(audioCtx.destination);
		osc.frequency.value = freq;
		osc.type = type;
		gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
		gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
		osc.start();
		osc.stop(audioCtx.currentTime + duration);
	}

	function playJump() {
		playSound(400, 0.1, 'square');
	}

	function playCrouch() {
		playSound(200, 0.1, 'square');
	}

	function playLevelUp() {
		playSound(523, 0.1);
		setTimeout(() => playSound(659, 0.1), 100);
		setTimeout(() => playSound(784, 0.2), 200);
	}

	function playDeath() {
		playSound(200, 0.3, 'sawtooth');
		setTimeout(() => playSound(100, 0.5, 'sawtooth'), 200);
	}

	function speak(text: string) {
		const utterance = new window.SpeechSynthesisUtterance(text);
		utterance.rate = 1.2;
		utterance.pitch = 0.8;
		utterance.volume = 1;
		window.speechSynthesis.speak(utterance);
	}

	function resetGame() {
		const GROUND = canvas.height * GROUND_RATIO;
		game = {
			state: 'waiting',
			level: 1,
			score: 0,
			speed: 6,
			countdown: 3,
			player: {
				x: canvas.width * 0.15,
				y: GROUND - 100,
				width: 120,
				height: 100,
				velocityY: 0,
				grounded: true,
				crouching: false
			},
			obstacles: [],
			meteors: [],
			obstacleTimer: 0,
			levelProgress: 0,
			levelGoal: 10
		};
		showGameOver = false;
	}

	function spawnObstacle() {
		const GROUND = canvas.height * GROUND_RATIO;
		const type = Math.random() > 0.5 ? 'bug-high' : 'bug-low';
		game.obstacles.push({
			x: canvas.width,
			y: type === 'bug-low' ? GROUND - 60 : GROUND - 140,
			width: 80,
			height: 60,
			type
		});
	}

	function nextLevel() {
		game.level++;
		game.speed *= 1.1;
		game.levelProgress = 0;
		playLevelUp();
		speak(`Level ${game.level}`);
		startMeteorShower();
	}

	function startMeteorShower() {
		game.state = 'meteor';
		game.meteors = [];
		for (let i = 0; i < 20; i++) {
			setTimeout(() => {
				game.meteors.push({
					x: Math.random() * canvas.width,
					y: -50,
					size: 50 + Math.random() * 40,
					speedY: 4 + Math.random() * 5,
					speedX: (Math.random() - 0.5) * 3
				});
			}, i * 200);
		}
		setTimeout(() => {
			game.state = 'playing';
			game.meteors = [];
		}, 5000);
	}

	function gameOver() {
		game.state = 'gameOver';
		playDeath();
		finalScore = `Score: ${game.score}`;
		finalLevel = `Level: ${game.level}`;
		showGameOver = true;
	}

	function checkCollision(rect1: any, rect2: any) {
		return (
			rect1.x < rect2.x + rect2.width &&
			rect1.x + rect1.width > rect2.x &&
			rect1.y < rect2.y + rect2.height &&
			rect1.y + rect1.height > rect2.y
		);
	}

	function drawCow() {
		const x = game.player.x;
		const y = game.player.y;
		const w = game.player.width;
		const h = game.player.height;

		// Body (white)
		ctx.fillStyle = '#fff';
		ctx.fillRect(x + w * 0.2, y + h * 0.3, w * 0.6, h * 0.5);

		// Head
		ctx.fillRect(x + w * 0.6, y + h * 0.1, w * 0.35, h * 0.4);

		// Spots (black)
		ctx.fillStyle = '#000';
		ctx.beginPath();
		ctx.arc(x + w * 0.35, y + h * 0.45, w * 0.12, 0, Math.PI * 2);
		ctx.fill();
		ctx.beginPath();
		ctx.arc(x + w * 0.55, y + h * 0.6, w * 0.1, 0, Math.PI * 2);
		ctx.fill();

		// Eyes
		ctx.fillStyle = '#000';
		ctx.fillRect(x + w * 0.75, y + h * 0.2, w * 0.08, h * 0.08);

		// Snout
		ctx.fillStyle = '#FFB6C1';
		ctx.fillRect(x + w * 0.88, y + h * 0.3, w * 0.1, h * 0.15);
		ctx.fillStyle = '#000';
		ctx.fillRect(x + w * 0.9, y + h * 0.35, w * 0.03, h * 0.03);
		ctx.fillRect(x + w * 0.95, y + h * 0.35, w * 0.03, h * 0.03);

		if (!game.player.crouching) {
			// Horns (brown)
			ctx.fillStyle = '#8B4513';
			ctx.beginPath();
			ctx.moveTo(x + w * 0.65, y + h * 0.1);
			ctx.lineTo(x + w * 0.6, y);
			ctx.lineTo(x + w * 0.7, y + h * 0.05);
			ctx.fill();

			ctx.beginPath();
			ctx.moveTo(x + w * 0.85, y + h * 0.1);
			ctx.lineTo(x + w * 0.9, y);
			ctx.lineTo(x + w * 0.8, y + h * 0.05);
			ctx.fill();

			// Legs
			ctx.fillStyle = '#fff';
			ctx.fillRect(x + w * 0.25, y + h * 0.8, w * 0.12, h * 0.2);
			ctx.fillRect(x + w * 0.45, y + h * 0.8, w * 0.12, h * 0.2);
			ctx.fillRect(x + w * 0.55, y + h * 0.8, w * 0.12, h * 0.2);

			// Tail
			ctx.strokeStyle = '#fff';
			ctx.lineWidth = 4;
			ctx.beginPath();
			ctx.moveTo(x + w * 0.2, y + h * 0.5);
			ctx.quadraticCurveTo(x + w * 0.1, y + h * 0.4, x + w * 0.05, y + h * 0.6);
			ctx.stroke();
		}
	}

	function drawBug(obs: Obstacle) {
		const x = obs.x;
		const y = obs.y;
		const w = obs.width;
		const h = obs.height;

		// Body segments (green/brown bug)
		ctx.fillStyle = '#6B8E23';
		ctx.beginPath();
		ctx.ellipse(x + w * 0.3, y + h * 0.5, w * 0.25, h * 0.35, 0, 0, Math.PI * 2);
		ctx.fill();
		ctx.beginPath();
		ctx.ellipse(x + w * 0.6, y + h * 0.5, w * 0.3, h * 0.4, 0, 0, Math.PI * 2);
		ctx.fill();

		// Head
		ctx.fillStyle = '#556B2F';
		ctx.beginPath();
		ctx.arc(x + w * 0.85, y + h * 0.4, w * 0.2, 0, Math.PI * 2);
		ctx.fill();

		// Wings
		ctx.fillStyle = 'rgba(139, 69, 19, 0.5)';
		ctx.beginPath();
		ctx.ellipse(x + w * 0.5, y + h * 0.3, w * 0.3, h * 0.5, -0.5, 0, Math.PI * 2);
		ctx.fill();
		ctx.beginPath();
		ctx.ellipse(x + w * 0.5, y + h * 0.7, w * 0.3, h * 0.5, 0.5, 0, Math.PI * 2);
		ctx.fill();

		// Antennae
		ctx.strokeStyle = '#556B2F';
		ctx.lineWidth = 3;
		ctx.beginPath();
		ctx.moveTo(x + w * 0.85, y + h * 0.3);
		ctx.lineTo(x + w * 0.95, y + h * 0.1);
		ctx.stroke();
		ctx.beginPath();
		ctx.moveTo(x + w * 0.85, y + h * 0.3);
		ctx.lineTo(x + w * 0.95, y + h * 0.15);
		ctx.stroke();

		// Eyes
		ctx.fillStyle = '#000';
		ctx.beginPath();
		ctx.arc(x + w * 0.9, y + h * 0.35, w * 0.05, 0, Math.PI * 2);
		ctx.fill();
	}

	function drawMeteor(meteor: Meteor) {
		const size = meteor.size;

		// Main meteor body
		ctx.fillStyle = '#8B0000';
		ctx.beginPath();
		ctx.arc(meteor.x, meteor.y, size / 2, 0, Math.PI * 2);
		ctx.fill();

		// Crater details
		ctx.fillStyle = '#660000';
		ctx.beginPath();
		ctx.arc(meteor.x - size * 0.15, meteor.y - size * 0.15, size * 0.15, 0, Math.PI * 2);
		ctx.fill();
		ctx.beginPath();
		ctx.arc(meteor.x + size * 0.2, meteor.y + size * 0.1, size * 0.1, 0, Math.PI * 2);
		ctx.fill();

		// Flame trail (larger)
		ctx.fillStyle = '#FF4500';
		ctx.beginPath();
		ctx.arc(meteor.x - size * 0.4, meteor.y - size * 0.4, size * 0.35, 0, Math.PI * 2);
		ctx.fill();

		ctx.fillStyle = '#FFA500';
		ctx.beginPath();
		ctx.arc(meteor.x - size * 0.6, meteor.y - size * 0.6, size * 0.25, 0, Math.PI * 2);
		ctx.fill();
	}

	function drawEnvironment() {
		const GROUND = canvas.height * GROUND_RATIO;

		// ---- SPACE SKY ----
		const spaceGradient = ctx.createLinearGradient(0, 0, 0, GROUND);
		spaceGradient.addColorStop(0, '#050012');
		spaceGradient.addColorStop(0.6, '#12002a');
		spaceGradient.addColorStop(1, '#1a0033');

		ctx.fillStyle = spaceGradient;
		ctx.fillRect(0, 0, canvas.width, GROUND);

		// Stars
		ctx.fillStyle = 'white';
		for (let i = 0; i < 150; i++) {
			const x = Math.random() * canvas.width;
			const y = Math.random() * GROUND;
			const r = Math.random() * 2;
			ctx.beginPath();
			ctx.arc(x, y, r, 0, Math.PI * 2);
			ctx.fill();
		}

		// ---- MOON SURFACE ----
		ctx.fillStyle = '#bdbdbd';
		ctx.fillRect(0, GROUND, canvas.width, canvas.height - GROUND);

		// Shading gradient
		const moonShade = ctx.createLinearGradient(0, GROUND, 0, canvas.height);
		moonShade.addColorStop(0, 'rgba(255,255,255,0.2)');
		moonShade.addColorStop(1, 'rgba(0,0,0,0.3)');
		ctx.fillStyle = moonShade;
		ctx.fillRect(0, GROUND, canvas.width, canvas.height - GROUND);

		// Craters
		for (let i = 0; i < 12; i++) {
			const cx = Math.random() * canvas.width;
			const cy = GROUND + Math.random() * (canvas.height - GROUND);
			const radius = 20 + Math.random() * 40;

			ctx.fillStyle = '#a9a9a9';
			ctx.beginPath();
			ctx.arc(cx, cy, radius, 0, Math.PI * 2);
			ctx.fill();

			// Inner shadow
			ctx.strokeStyle = 'rgba(0,0,0,0.3)';
			ctx.lineWidth = 4;
			ctx.beginPath();
			ctx.arc(cx - radius * 0.2, cy - radius * 0.2, radius * 0.8, 0, Math.PI * 2);
			ctx.stroke();
		}

		// Horizon line
		ctx.strokeStyle = '#888';
		ctx.lineWidth = 4;
		ctx.beginPath();
		ctx.moveTo(0, GROUND);
		ctx.lineTo(canvas.width, GROUND);
		ctx.stroke();
	}

	function drawBodyKeypoints() {
		if (!lastBodyData || !lastBodyData.body) return;

		const body = lastBodyData.body;
		const scale = canvas.width;

		function drawPoint(
			x: number | null,
			y: number | null,
			label: string,
			color: string = '#FF0000'
		) {
			if (x === null || y === null) return;

			const px = (1 - x) * scale;
			const py = y * canvas.height;

			ctx.fillStyle = color;
			ctx.beginPath();
			ctx.arc(px, py, 10, 0, Math.PI * 2);
			ctx.fill();

			ctx.fillStyle = '#FFFFFF';
			ctx.strokeStyle = '#000000';
			ctx.lineWidth = 3;
			ctx.font = 'bold 16px Arial';
			ctx.strokeText(label, px + 15, py + 5);
			ctx.fillText(label, px + 15, py + 5);
		}

		drawPoint(body.head.x, body.head.y, 'HEAD', '#FF00FF');
		drawPoint(body.left_shoulder.x, body.left_shoulder.y, 'L_SHOULDER', '#00FF00');
		drawPoint(body.right_shoulder.x, body.right_shoulder.y, 'R_SHOULDER', '#00FF00');
		drawPoint(body.left_elbow.x, body.left_elbow.y, 'L_ELBOW', '#0000FF');
		drawPoint(body.right_elbow.x, body.right_elbow.y, 'R_ELBOW', '#0000FF');

		ctx.strokeStyle = '#FFFF00';
		ctx.lineWidth = 3;

		ctx.beginPath();
		ctx.moveTo((1 - body.left_shoulder.x) * scale, body.left_shoulder.y * canvas.height);
		ctx.lineTo((1 - body.right_shoulder.x) * scale, body.right_shoulder.y * canvas.height);
		ctx.stroke();

		ctx.beginPath();
		ctx.moveTo((1 - body.left_shoulder.x) * scale, body.left_shoulder.y * canvas.height);
		ctx.lineTo((1 - body.left_elbow.x) * scale, body.left_elbow.y * canvas.height);
		ctx.stroke();

		ctx.beginPath();
		ctx.moveTo((1 - body.right_shoulder.x) * scale, body.right_shoulder.y * canvas.height);
		ctx.lineTo((1 - body.right_elbow.x) * scale, body.right_elbow.y * canvas.height);
		ctx.stroke();
	}

	function drawDebugInfo() {
		const GROUND = canvas.height * GROUND_RATIO;
		const debugY = GROUND + 30;

		// Background for debug info
		ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
		ctx.fillRect(10, debugY, 500, 180);

		// Debug text
		ctx.fillStyle = '#FFFFFF';
		ctx.font = 'bold 20px Arial';

		ctx.fillText(`Body Detected: ${debugInfo.bodyDetected ? 'YES' : 'NO'}`, 20, debugY + 30);
		ctx.fillText(`Baseline Ready: ${debugInfo.baselineReady ? 'YES' : 'NO'}`, 20, debugY + 60);
		ctx.fillText(`Baseline Y: ${debugInfo.baseline.toFixed(3)}`, 20, debugY + 90);
		ctx.fillText(`Current Y: ${debugInfo.current.toFixed(3)}`, 20, debugY + 120);
		ctx.fillText(`Diff: ${debugInfo.diff.toFixed(3)}`, 20, debugY + 150);

		// Status indicators
		if (input.jumping) {
			ctx.fillStyle = '#00FF00';
			ctx.fillText('🔼 JUMPING! ', 300, debugY + 30);
		}
		if (input.crouching) {
			ctx.fillStyle = '#FF6600';
			ctx.fillText('🔽 CROUCHING!', 300, debugY + 60);
		}
	}

	function drawUI() {
		ctx.fillStyle = '#000';
		ctx.font = 'bold 32px Arial';
		ctx.fillText(`Level: ${game.level}`, 20, 50);
		ctx.fillText(`Score: ${game.score}`, 20, 90);
		ctx.fillText(`Speed: ${game.speed.toFixed(1)}x`, 20, 130);
	}

	function jump() {
		if (game.player.grounded && !game.player.crouching) {
			game.player.velocityY = -28;
			game.player.grounded = false;
			playJump();
		}
	}

	function crouch() {
		if (game.player.grounded) {
			game.player.crouching = true;
			game.player.height = 50;
			playCrouch();
		}
	}

	function unCrouch() {
		game.player.crouching = false;
		game.player.height = 100;
	}

	function startCountdown() {
		game.state = 'countdown';
		game.countdown = 3;
		showCountdown = true;
		countdownText = '3';

		function count() {
			if (game.countdown > 0) {
				countdownText = game.countdown.toString();
				speak(game.countdown.toString());
				game.countdown--;
				setTimeout(count, 1000);
			} else {
				countdownText = 'GO!';
				speak('GO');
				setTimeout(() => {
					showCountdown = false;
					game.state = 'playing';
				}, 1000);
			}
		}
		count();
	}

	function update() {
		const GROUND = canvas.height * GROUND_RATIO;

		if (game.state === 'playing') {
			// Camera input handling
			if (input.jumping && !input.prevJumping) {
				jump();
			}
			if (input.crouching && !game.player.crouching) {
				crouch();
			} else if (!input.crouching && game.player.crouching) {
				unCrouch();
			}

			// Physics
			game.player.velocityY += 1;
			game.player.y += game.player.velocityY;

			if (game.player.y >= GROUND - game.player.height) {
				game.player.y = GROUND - game.player.height;
				game.player.velocityY = 0;
				game.player.grounded = true;
			}

			// Spawn obstacles
			game.obstacleTimer++;
			if (game.obstacleTimer > 800 / game.speed) {
				spawnObstacle();
				game.obstacleTimer = 0;
			}

			// Update obstacles
			for (let i = game.obstacles.length - 1; i >= 0; i--) {
				game.obstacles[i].x -= game.speed;

				if (checkCollision(game.player, game.obstacles[i])) {
					gameOver();
					return;
				}

				if (game.obstacles[i].x + game.obstacles[i].width < 0) {
					game.obstacles.splice(i, 1);
					game.score++;
					game.levelProgress++;

					if (game.levelProgress >= game.levelGoal) {
						nextLevel();
					}
				}
			}
		}

		if (game.state === 'meteor') {
			// Player can move left/right during meteors
			if (input.movingRight) {
				game.player.x = Math.min(canvas.width - game.player.width, game.player.x + 10);
			}
			if (input.movingLeft) {
				game.player.x = Math.max(0, game.player.x - 10);
			}

			// Update meteors
			for (let i = game.meteors.length - 1; i >= 0; i--) {
				const m = game.meteors[i];
				m.y += m.speedY;
				m.x += m.speedX;

				if (
					checkCollision(game.player, {
						x: m.x - m.size / 2,
						y: m.y - m.size / 2,
						width: m.size,
						height: m.size
					})
				) {
					gameOver();
					return;
				}

				if (m.y > canvas.height) {
					game.meteors.splice(i, 1);
				}
			}
		}
	}

	function draw() {
		drawEnvironment();

		// Draw body keypoints overlay
		drawBodyKeypoints();

		// Game objects
		if (game.state === 'playing' || game.state === 'meteor') {
			drawCow();

			if (game.state === 'playing') {
				game.obstacles.forEach(drawBug);
			}

			if (game.state === 'meteor') {
				game.meteors.forEach(drawMeteor);

				// Instruction
				ctx.fillStyle = '#fff';
				ctx.strokeStyle = '#000';
				ctx.lineWidth = 4;
				ctx.font = 'bold 48px Arial';
				const textX = canvas.width / 2 - 200;
				ctx.strokeText('METEOR SHOWER! ', textX, 80);
				ctx.fillText('METEOR SHOWER!', textX, 80);
				ctx.font = 'bold 32px Arial';
				ctx.strokeText('Move left/right to dodge!', textX + 20, 130);
				ctx.fillText('Move left/right to dodge!', textX + 20, 130);
			}

			drawUI();
			drawDebugInfo();
		}

		if (game.state === 'waiting') {
			drawCow();
			drawDebugInfo();
			ctx.fillStyle = '#fff';
			ctx.strokeStyle = '#000';
			ctx.lineWidth = 4;
			ctx.font = 'bold 72px Arial';
			const titleX = canvas.width / 2 - 320;
			const titleY = canvas.height / 2 - 80;
			ctx.strokeText('SPACE COW RUNNER', titleX, titleY);
			ctx.fillText('SPACE COW RUNNER', titleX, titleY);
			ctx.font = 'bold 36px Arial';
			ctx.strokeText('Jump to start', canvas.width / 2 - 120, titleY + 60);
			ctx.fillText('Jump to start', canvas.width / 2 - 120, titleY + 60);
			ctx.font = '24px Arial';
			ctx.fillText('Jump IRL to jump | Crouch IRL to crouch', canvas.width / 2 - 240, titleY + 110);
		}

		if (game.state === 'countdown') {
			drawDebugInfo();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.code === 'Space') {
			e.preventDefault();
			if (game.state === 'waiting') startCountdown();
			if (game.state === 'playing' && game.player.grounded) jump();
			if (game.state === 'gameOver') {
				resetGame();
				startCountdown();
			}
		}
		if (e.code === 'ArrowDown' || e.code === 'KeyS') {
			if (game.state === 'playing') crouch();
		}
	}

	function handleKeyup(e: KeyboardEvent) {
		if (e.code === 'ArrowDown' || e.code === 'KeyS') {
			unCrouch();
		}
	}

	onMount(() => {
		ctx = canvas.getContext('2d')!;
		resizeCanvas();
		window.addEventListener('resize', resizeCanvas);

		// Camera setup
		video = document.createElement('video');
		video.autoplay = true;
		video.playsInline = true;
		cameraCanvas = document.createElement('canvas');
		cameraCanvas.width = 320;
		cameraCanvas.height = 240;
		cameraCtx = cameraCanvas.getContext('2d')!;

		navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
			video.srcObject = stream;
		});

		// Socket setup
		socket = io();

		cameraInterval = setInterval(() => {
			cameraCtx.drawImage(video, 0, 0, 320, 240);
			cameraCanvas.toBlob(
				(blob) => {
					socket.emit('frame', blob);
				},
				'image/jpeg',
				0.5
			);
		}, 66);

		socket.on('result', (data: any) => {
			const body = data.body;
			lastBodyData = data;

			if (body && body.left_shoulder && body.right_shoulder) {
				debugInfo.bodyDetected = true;
				const avgShoulderY = (body.left_shoulder.y + body.right_shoulder.y) / 2;

				// Only update baseline when standing still (game not playing or in waiting)
				if (game.state === 'waiting' || game.state === 'countdown') {
					shoulderYHistory.push(avgShoulderY);
					if (shoulderYHistory.length > BASELINE_SIZE) {
						shoulderYHistory.shift();
					}
					if (shoulderYHistory.length >= 20) {
						baselineEstablished = true;
						debugInfo.baselineReady = true;
					}
				}

				// Track current position with smoothing
				currentShoulderY.push(avgShoulderY);
				if (currentShoulderY.length > DETECTION_SIZE) {
					currentShoulderY.shift();
				}

				if (baselineEstablished && currentShoulderY.length === DETECTION_SIZE) {
					// Calculate baseline and current averages
					const baseline = shoulderYHistory.reduce((a, b) => a + b) / shoulderYHistory.length;
					const current = currentShoulderY.reduce((a, b) => a + b) / currentShoulderY.length;

					// Calculate difference
					const diff = current - baseline;

					debugInfo.baseline = baseline;
					debugInfo.current = current;
					debugInfo.diff = diff;

					// Detect jump - shoulders moved UP (lower Y value)
					const jumpThreshold = -0.04;
					input.jumping = diff < jumpThreshold;

					// Detect crouch - shoulders moved DOWN (higher Y value)
					const crouchThreshold = 0.04;
					input.crouching = diff > crouchThreshold;

					// Debug output
					if (input.jumping || input.crouching) {
						console.log(
							`Baseline: ${baseline.toFixed(3)}, Current: ${current.toFixed(3)}, Diff: ${diff.toFixed(3)}, Jump: ${input.jumping}, Crouch: ${input.crouching}`
						);
					}
				}
			} else {
				debugInfo.bodyDetected = false;
				input.jumping = false;
				input.crouching = false;
			}

			// Detect side-to-side movement using body center
			if (body && body.left_shoulder && body.right_shoulder) {
				const bodyX = (body.left_shoulder.x + body.right_shoulder.x) / 2;
				input.movingRight = bodyX > 0.6;
				input.movingLeft = bodyX < 0.4;
			} else {
				input.movingRight = false;
				input.movingLeft = false;
			}
		});

		inputInterval = setInterval(() => {
			if (game.state === 'waiting' && input.jumping && !input.prevJumping) {
				startCountdown();
			}
			if (game.state === 'gameOver' && input.jumping && !input.prevJumping) {
				resetGame();
				startCountdown();
			}
			input.prevJumping = input.jumping;
		}, 100);

		document.addEventListener('keydown', handleKeydown);
		document.addEventListener('keyup', handleKeyup);

		resetGame();

		function loop() {
			update();
			draw();
			animationFrame = requestAnimationFrame(loop);
		}
		loop();
	});

	onDestroy(() => {
		if (typeof window !== 'undefined') {
			window.removeEventListener('resize', resizeCanvas);
			document.removeEventListener('keydown', handleKeydown);
			document.removeEventListener('keyup', handleKeyup);
			cancelAnimationFrame(animationFrame);
			clearInterval(cameraInterval);
			clearInterval(inputInterval);
		}
		socket?.disconnect();
	});
</script>

<canvas bind:this={canvas} id="gameCanvas"></canvas>
{#if showCountdown}
	<div id="countdown">
		{countdownText}
	</div>
{/if}
{#if showGameOver}
	<div id="gameOver">
		<h1>GAME OVER</h1>
		<p class="score">{finalScore}</p>
		<p class="score">{finalLevel}</p>
		<p class="hint">Jump to play again</p>
	</div>
{/if}

<style>
	#gameCanvas {
		display: block;
		width: 100vw;
		height: 100vh;
	}

	#countdown {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		font-size: 150px;
		font-weight: bold;
		color: white;
		text-shadow: 5px 5px 10px rgba(0, 0, 0, 0.9);
		z-index: 10;
	}

	#gameOver {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		background: rgba(0, 0, 0, 0.95);
		padding: 60px;
		border-radius: 20px;
		text-align: center;
		color: white;
		z-index: 10;
	}

	#gameOver h1 {
		margin: 0 0 30px 0;
		font-size: 64px;
		color: #ff4444;
	}

	#gameOver .score {
		margin: 15px 0;
		font-size: 32px;
	}

	#gameOver .hint {
		font-size: 24px;
		margin-top: 30px;
	}
</style>
