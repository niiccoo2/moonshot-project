import { handler } from './build/handler.js';
import express from 'express';
import { Server } from 'socket.io';
import { createServer } from 'http';

const app = express();
const server = createServer(app);

// Socket.IO setup
const io = new Server(server, {
	cors: {
		origin: '*',
		methods: ['GET', 'POST']
	}
});

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
		for (const [session_id, session] of sessions.entries()) {
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

// Health check endpoint BEFORE SvelteKit handler
app.get('/api/health', (req, res) => {
	console.log('Health check hit');
	res.json({
		status: 'ok',
		socketio: 'running',
		sessions: sessions.size,
		time: new Date().toISOString()
	});
});

// Socket.IO status endpoint
app.get('/api/socketio-status', (req, res) => {
	console.log('Socket.IO status check hit');
	const sessionDetails = [];
	for (const [id, session] of sessions.entries()) {
		sessionDetails.push({
			id,
			cameras: session.cameras.size,
			hasGame: !!session.game
		});
	}
	res.json({
		status: 'running',
		sessions: sessionDetails
	});
});

// Use SvelteKit handler for all routes
app.use(handler);

const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
	console.log('='.repeat(60));
	console.log('SERVER STARTED');
	console.log(`Time: ${new Date().toISOString()}`);
	console.log(`Port: ${PORT}`);
	console.log(`Socket.IO: ENABLED`);
	console.log(`Health check: http://localhost:${PORT}/api/health`);
	console.log('='.repeat(60));
});
