<script lang="ts">
	import { onMount } from 'svelte';

	let gameContainer: HTMLDivElement;
	let game: any;

	let player: Phaser.Physics.Arcade.Sprite | undefined;
	let cursors: Phaser.Types.Input.Keyboard.CursorKeys;
	let score = 0;
	let fallingObjects: Phaser.Physics.Arcade.Group;
	let lastSpawnTime = 0;
	let gameOver = false;

	export let leftHandPos = { x: 0.5, y: 0.5 };
	export let rightHandPos = { x: 0.5, y: 0.5 };
	let leftGesture = 'unknown';
	let rightGesture = 'unknown';
	let bodyKeypoints = null;

	onMount(() => {
		let destroyed = false;

		(async () => {
			while (!gameContainer) {
				await new Promise((resolve) => setTimeout(resolve, 10));
			}

			const Phaser = (await import('phaser')).default;

			const config = {
				type: Phaser.AUTO,
				width: 800,
				height: 600,
				parent: gameContainer,
				physics: {
					default: 'arcade',
					arcade: {
						gravity: { y: 300, x: 0 },
						debug: false
					}
				},
				scene: {
					preload: preload,
					create: create,
					update: update
				}
			};

			function createSprites(scene: any) {
				// Create Bug Sprite
				const bugGraphics = scene.make.graphics({ x: 0, y: 0, add: false });
				bugGraphics.fillStyle(0x00ff00, 1);
				bugGraphics.fillEllipse(20, 20, 30, 40);
				bugGraphics.fillStyle(0x88ff88, 1);
				bugGraphics.fillEllipse(20, 15, 20, 25);
				bugGraphics.fillStyle(0x000000, 1);
				bugGraphics.fillCircle(15, 12, 3);
				bugGraphics.fillCircle(25, 12, 3);
				bugGraphics.lineStyle(2, 0x006600);
				bugGraphics.strokeCircle(20, 20, 20);
				bugGraphics.generateTexture('bug', 40, 40);
				bugGraphics.destroy();

				// Create Space Cow Sprite
				const cowGraphics = scene.make.graphics({ x: 0, y: 0, add: false });
				cowGraphics.fillStyle(0xffffff, 1);
				cowGraphics.fillEllipse(25, 25, 40, 35);
				cowGraphics.fillEllipse(25, 35, 30, 25);
				cowGraphics.fillStyle(0x000000, 1);
				cowGraphics.fillCircle(35, 25, 8);
				cowGraphics.fillCircle(38, 22, 10);
				cowGraphics.fillCircle(15, 25, 8);
				cowGraphics.fillCircle(12, 22, 10);
				cowGraphics.fillStyle(0xff69b4, 1);
				cowGraphics.fillCircle(20, 30, 3);
				cowGraphics.fillCircle(30, 30, 3);
				cowGraphics.fillStyle(0xffaa00, 1);
				cowGraphics.fillCircle(25, 10, 4);
				cowGraphics.generateTexture('spaceCow', 50, 50);
				cowGraphics.destroy();

				// Create Meteor Sprite
				const meteorGraphics = scene.make.graphics({ x: 0, y: 0, add: false });
				meteorGraphics.fillStyle(0x8b4513, 1);
				meteorGraphics.fillCircle(20, 20, 18);
				meteorGraphics.fillStyle(0x654321, 1);
				meteorGraphics.fillCircle(15, 18, 5);
				meteorGraphics.fillCircle(25, 22, 4);
				meteorGraphics.fillCircle(18, 25, 3);
				meteorGraphics.fillStyle(0xff6600, 0.5);
				meteorGraphics.fillCircle(20, 20, 22);
				meteorGraphics.generateTexture('meteor', 40, 40);
				meteorGraphics.destroy();

				// Create Player Basket
				const basketGraphics = scene.make.graphics({ x: 0, y: 0, add: false });
				basketGraphics.fillStyle(0x8b4513, 1);
				basketGraphics.fillRect(0, 10, 60, 30);
				basketGraphics.fillStyle(0xd2691e, 1);
				basketGraphics.fillRect(5, 15, 50, 20);
				basketGraphics.lineStyle(3, 0x654321);
				for (let i = 10; i < 55; i += 10) {
					basketGraphics.lineBetween(i, 15, i, 35);
				}
				basketGraphics.generateTexture('basket', 60, 40);
				basketGraphics.destroy();
			}

			function spawnObject(scene: any) {
				const x = Phaser.Math.Between(50, 750);
				const types = [
					{ key: 'bug', points: 10, speed: 150 },
					{ key: 'spaceCow', points: 50, speed: 100 },
					{ key: 'meteor', points: -20, speed: 200 }
				];

				const type = Phaser.Utils.Array.GetRandom(types);
				const obj = fallingObjects.create(x, -50, type.key);
				obj.setVelocityY(type.speed);
				obj.points = type.points;
				obj.objectType = type.key;
			}

			function collectObject(this: Phaser.Scene, object: any) {
				score += object.points;
				const scoreDisplay = document.getElementById('score-display');
				if (scoreDisplay) {
					scoreDisplay.textContent = 'Score: ' + score;
				}

				const color = object.points > 0 ? 0x00ff00 : 0xff0000;
				const circle = this.add.circle(object.x, object.y, 30, color, 0.5);
				this.tweens.add({
					targets: circle,
					alpha: 0,
					scale: 2,
					duration: 300,
					onComplete: () => circle.destroy()
				});

				object.destroy();
			}

			if (!destroyed) {
				game = new Phaser.Game(config);
			}

			function preload(this: any) {
				createSprites(this);
			}

			function create(this: any) {
				player = this.physics.add.sprite(400, 550, 'basket');
				if (player == null) return;
				player.setCollideWorldBounds(true);

				fallingObjects = this.physics.add.group();

				this.physics.add.overlap(player, fallingObjects, collectObject, null, this);

				cursors = this.input.keyboard.createCursorKeys();

				this.add.text(10, 10, 'Move your hands left/right to control!', {
					fontSize: '18px',
					fill: '#fff',
					stroke: '#000',
					strokeThickness: 4
				});
			}

			function update(this: any, time: number) {
				if (gameOver) return;
				if (player == null) return;

				// Average both hands for player position
				const handX = (leftHandPos.x + rightHandPos.x) / 2;

				// Check if hands are detected (not at default position)
				const handsDetected = leftHandPos.x !== 0.5 || rightHandPos.x !== 0.5;

				if (handsDetected && handX > 0.05 && handX < 0.95) {
					// Use hand tracking - map normalized coordinates to screen
					player.x = handX * 800;
				} else {
					// Keyboard fallback
					if (cursors.left.isDown) {
						player.x -= 8;
					} else if (cursors.right.isDown) {
						player.x += 8;
					}
				}

				// Spawn falling objects
				if (time > lastSpawnTime + 1500) {
					spawnObject(this);
					lastSpawnTime = time;
				}

				// Remove objects that fall off screen
				fallingObjects.children.entries.forEach((obj) => {
					const sprite = obj as Phaser.Physics.Arcade.Sprite;
					if (sprite.y > 620) {
						sprite.destroy();
					}
				});
			}
		})();

		return () => {
			destroyed = true;
			game?.destroy(true);
		};
	});
</script>

<div bind:this={gameContainer}></div>

<style>
	div {
		width: 800px;
		height: 600px;
	}
</style>
