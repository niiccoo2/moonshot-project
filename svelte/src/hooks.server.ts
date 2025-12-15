import type { Handle } from '@sveltejs/kit';
import { Server } from 'socket.io';

const io = new Server();

const sessions = new Map();

io.on('connection', (socket) => {
	console.log('Client connected:', socket.id);

	socket.on('join_session', ({ session_id, role }) => {
		console.log(`${socket.id} joining ${session_id} as ${role}`);
		socket.join(session_id);

		if (!sessions.has(session_id)) {
			sessions.set(session_id, { camera: null, game: null });
		}

		const session = sessions.get(session_id);
		if (role === 'camera') {
			session.camera = socket.id;
		} else if (role === 'game') {
			session.game = socket.id;
		}
	});

	socket.on('frame', (data) => {
		// Find which session this camera belongs to
		for (const [session_id, session] of sessions.entries()) {
			if (session.camera === socket.id && session.game) {
				// Forward frame to the game client
				io.to(session.game).emit('frame', data);
			}
		}
	});

	socket.on('disconnect', () => {
		console.log('Client disconnected:', socket.id);
		// Clean up sessions
		for (const [session_id, session] of sessions.entries()) {
			if (session.camera === socket.id) session.camera = null;
			if (session.game === socket.id) session.game = null;
		}
	});
});

export const handle: Handle = async ({ event, resolve }) => {
	if (event.url.pathname.startsWith('/socket.io')) {
		// Handle Socket.IO upgrade
		return new Response(null, { status: 101 });
	}
	return resolve(event);
};

// Start Socket.IO server
const PORT = 3001;
io.listen(PORT);
console.log(`Socket.IO server running on port ${PORT}`);
