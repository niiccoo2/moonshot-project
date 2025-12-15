import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { Server } from 'socket.io';

export default defineConfig({
	plugins: [
		sveltekit(),
		{
			name: 'sveltekit-socket-io',
			configureServer(server) {
				if (!server.httpServer) return;
				const io = new Server(server.httpServer);
				const sessions = new Map();

				io.on('connection', (socket) => {
					console.log('='.repeat(40));
					console.log('NEW SOCKET.IO CONNECTION');
					console.log('Socket ID:', socket.id);
					console.log('Time:', new Date().toISOString());
					console.log('Transport:', socket.conn.transport.name);
					console.log('='.repeat(40));

					socket.on('join_session', ({ session_id, role, cameraId }) => {
						console.log(
							`[JOIN] ${socket.id} -> session: ${session_id}, role: ${role}${cameraId ? `, camera: ${cameraId}` : ''}`
						);
						socket.join(session_id);

						if (!sessions.has(session_id)) {
							sessions.set(session_id, { cameras: new Map(), game: null });
						}

						const session = sessions.get(session_id);
						if (role === 'camera') {
							session.cameras.set(cameraId, socket.id);
							console.log(`Session ${session_id} now has ${session.cameras.size} cameras`);
						} else if (role === 'game') {
							session.game = socket.id;
							console.log(`Game connected to session ${session_id}`);
						}
					});

					socket.on('frame', ({ cameraId, blob }) => {
						for (const [, session] of sessions.entries()) {
							if (session.cameras.has(cameraId) && session.game) {
								io.to(session.game).emit('frame', { cameraId, blob });
							}
						}
					});

					socket.on('result', ({ cameraId, result, timestamp }) => {
						// console.log(`[RESULT] Received from camera ${cameraId}`);
						let found = false;
						for (const [session_id, session] of sessions.entries()) {
							if (session.cameras.has(cameraId)) {
								found = true;
								if (session.game) {
									// console.log(`[RESULT] Relaying to game ${session.game} in session ${session_id}`);
									io.to(session.game).emit('result', { session_id, result, timestamp });
								} else {
									console.log(`[RESULT] Session ${session_id} has camera ${cameraId} but NO GAME connected`);
								}
							}
						}
						if (!found) {
							console.log(`[RESULT] Camera ${cameraId} not found in any session`);
						}
					});

					socket.on('disconnect', () => {
						console.log('Client disconnected:', socket.id);
						for (const [session_id, session] of sessions.entries()) {
							for (const [cameraId, socketId] of session.cameras.entries()) {
								if (socketId === socket.id) {
									session.cameras.delete(cameraId);
									console.log(`Camera ${cameraId} disconnected from session ${session_id}`);
									if (session.game) {
										io.to(session.game).emit('camera_disconnected', cameraId);
									}
								}
							}
							if (session.game === socket.id) {
								session.game = null;
							}
						}
					});
				});
			}
		}
	],
	server: {
		fs: {
			allow: ['./src', './node_modules', '../node_modules']
		}
	}
});
