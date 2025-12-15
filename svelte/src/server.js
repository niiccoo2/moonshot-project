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
	console.log('Client connected:', socket.id);

	socket.on('join_session', ({ session_id, role, cameraId }) => {
		console.log(`${socket.id} joining ${session_id} as ${role}`, cameraId || '');
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
		}
	});

	socket.on('frame', ({ cameraId, blob }) => {
		for (const [session_id, session] of sessions.entries()) {
			if (session.cameras.has(cameraId) && session.game) {
				io.to(session.game).emit('frame', { cameraId, blob });
			}
		}
	});

	socket.on('disconnect', () => {
		console.log('Client disconnected:', socket.id);
		for (const [session_id, session] of sessions.entries()) {
			for (const [cameraId, socketId] of session.cameras.entries()) {
				if (socketId === socket.id) {
					session.cameras.delete(cameraId);
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

// Use SvelteKit handler for all routes
app.use(handler);

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
	console.log(`Server running on port ${PORT}`);
});
