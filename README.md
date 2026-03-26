# NestChat

NestChat is a real-time chat application similar to a community messenger.

Users can register, join servers, use text channels, send direct messages, manage friends, react to messages, and join voice channels. The app also includes authentication, user presence, and real-time updates over WebSocket connections.

The stack is:

- `Svelte + Vite` for the frontend
- `Django` for the API
- `PostgreSQL`, `Redis`, `RabbitMQ`, and `LiveKit` for supporting services

## Requirements

- `Docker` and `Docker Compose`
- `Node.js` and `npm`

## Run locally

### 1. Start backend and services

From the project root:

```bash
docker compose up --build
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

If you want to run migrations and collect static files after startup, you can use:

```bash
make up-build
```

### 2. Start frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available by default at:

```text
http://127.0.0.1:5173
```

## Useful commands

```bash
make migrate
make superuser
make test
```
