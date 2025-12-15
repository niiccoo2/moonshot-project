import type { Handle } from '@sveltejs/kit';
import { Server } from 'socket.io';

const io = new Server({
	cors: {
		origin: '*', // Allow all origins (or specify your domain)
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

export const handle: Handle = async ({ event, resolve }) => {
	return resolve(event);
};

const PORT = 3001;
io.listen(PORT);
console.log(`Socket.IO server running on port ${PORT}`);
