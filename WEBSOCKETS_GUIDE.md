# WebSockets in MOTOBEE
## Complete Setup, Testing & Integration Guide

> WebSockets are already coded in the project (`notifications/consumers.py`).
> This guide covers how to enable them, test them, and connect from React Native.

---

## What WebSockets Do in MOTOBEE

```
Without WebSockets (Polling):
  App → "Any updates?" → Server → "No"   (every 5 seconds, wasteful)

With WebSockets (Push):
  Server → "Booking accepted!" → App     (instant, only when something happens)
```

Two WebSocket connections exist in the project:

| Connection | URL | Who Uses It | Purpose |
|---|---|---|---|
| `BookingConsumer` | `/ws/booking/<id>/` | Customer + Owner | Live status of one booking |
| `UserNotificationConsumer` | `/ws/notifications/` | Every user | All personal notifications |

---

## Part 1 — Backend Setup

### Step 1 — Check what's already in the project

These files are already written — just verify they exist:

```
notifications/
├── consumers.py     ← WebSocket consumers (already written)
├── tasks.py         ← Sends WS messages after booking events (already written)
motobee/
├── routing.py       ← Maps URLs to consumers (already written)
├── asgi.py          ← ASGI entry point (already written)
```

### Step 2 — Verify `routing.py`

Open `motobee/routing.py` — it should contain:

```python
from django.urls import re_path
from notifications.consumers import BookingConsumer, UserNotificationConsumer

websocket_urlpatterns = [
    re_path(r'^ws/booking/(?P<booking_id>[0-9a-f-]+)/$', BookingConsumer.as_asgi()),
    re_path(r'^ws/notifications/$', UserNotificationConsumer.as_asgi()),
]
```

### Step 3 — Verify `asgi.py`

Open `motobee/asgi.py` — it should contain:

```python
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from .routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

### Step 4 — Channel Layer (InMemory for dev, Redis for production)

In `settings.py`, this is already configured:

```python
# Dev — no Redis needed, works out of the box
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

> For production with Redis, set `REDIS_HOST` in your `.env` and it switches automatically.

### Step 5 — Install dependencies

```bash
pip install channels
```

For production Redis support:
```bash
pip install channels-redis redis
```

### Step 6 — Run with ASGI (not WSGI)

Standard `runserver` works fine for development — Django Channels patches it automatically:

```bash
python manage.py runserver
```

You should see in the console:
```
Django version 4.x, using settings 'motobee.settings'
Starting ASGI/Channels development server at http://127.0.0.1:8000/
```

---

## Part 2 — Testing WebSockets

### Method 1 — Browser Console (Quickest)

Open `http://127.0.0.1:8000/api/docs/` in Chrome, then open DevTools (`F12`) → Console tab.

**Step 1 — Login and get a token:**
```javascript
const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'your@email.com', password: 'yourpassword' })
});
const data = await res.json();
const token = data.access;
console.log('Token:', token);
```

**Step 2 — Connect to notification WebSocket:**
```javascript
const ws = new WebSocket(`ws://127.0.0.1:8000/ws/notifications/?token=${token}`);

ws.onopen = () => console.log('✅ Connected!');
ws.onmessage = (e) => console.log('📨 Message:', JSON.parse(e.data));
ws.onerror = (e) => console.log('❌ Error:', e);
ws.onclose = (e) => console.log('🔌 Closed, code:', e.code);
```

You should immediately see:
```
✅ Connected!
📨 Message: { type: 'connected', unread_count: 0 }
```

**Step 3 — Connect to a specific booking:**
```javascript
// Replace with a real booking UUID from your DB
const bookingId = 'paste-booking-uuid-here';
const bookingWs = new WebSocket(
  `ws://127.0.0.1:8000/ws/booking/${bookingId}/?token=${token}`
);

bookingWs.onopen = () => console.log('✅ Watching booking', bookingId);
bookingWs.onmessage = (e) => console.log('📨 Booking update:', JSON.parse(e.data));
```

**Step 4 — Trigger a booking status change to see live update:**

In a second browser tab or Postman, accept the booking:
```
PATCH http://127.0.0.1:8000/api/v1/bookings/<booking_id>/accept/
Authorization: Bearer <owner_token>
```

Back in the browser console you should instantly see:
```
📨 Booking update: {
  type: "booking_update",
  event: "accepted",
  booking_id: "...",
  booking_status: "accepted",
  booking: { ... }
}
```

---

### Method 2 — Postman WebSocket (Visual)

Postman supports WebSockets natively (version 9.0+).

1. Click **New** → **WebSocket Request**
2. Enter URL:
   ```
   ws://127.0.0.1:8000/ws/notifications/?token=<your_jwt_token>
   ```
3. Click **Connect**
4. You'll see the connection established and the `connected` message appear in the **Messages** panel

To test booking updates:
- Open a second Postman tab
- PATCH `/bookings/<id>/accept/` as the owner
- Watch the WebSocket tab — the update appears instantly

---

### Method 3 — `wscat` CLI tool (Terminal)

Install:
```bash
npm install -g wscat
```

Connect:
```bash
wscat -c "ws://127.0.0.1:8000/ws/notifications/?token=<your_jwt_token>"
```

You'll see:
```
Connected (press CTRL+C to quit)
< {"type": "connected", "unread_count": 0}
```

Send a mark-as-read command:
```bash
> {"action": "mark_read", "notification_id": "paste-notification-uuid-here"}
< {"type": "marked_read", "notification_id": "..."}
```

---

### Method 4 — Python test script

Create `test_ws.py` in your project root:

```python
"""
test_ws.py — Quick WebSocket test script
Run: python test_ws.py
"""
import asyncio
import json
import httpx
import websockets

BASE_URL = 'http://127.0.0.1:8000/api/v1'
WS_URL   = 'ws://127.0.0.1:8000'

async def main():
    # 1. Login and get token
    async with httpx.AsyncClient() as client:
        res = await client.post(f'{BASE_URL}/auth/login/', json={
            'email': 'your@email.com',
            'password': 'yourpassword',
        })
        token = res.json()['access']
        print(f'✅ Logged in. Token: {token[:30]}...')

    # 2. Connect to notification WebSocket
    url = f'{WS_URL}/ws/notifications/?token={token}'
    async with websockets.connect(url) as ws:
        print('✅ WebSocket connected')

        # 3. Receive the initial connected message
        msg = await ws.recv()
        print(f'📨 Received: {json.loads(msg)}')

        # 4. Keep listening for 30 seconds
        # Trigger a booking change via Postman while this is running
        print('👂 Listening for 30 seconds... trigger a booking change in Postman')
        try:
            async with asyncio.timeout(30):
                while True:
                    msg = await ws.recv()
                    print(f'📨 Live update: {json.loads(msg)}')
        except asyncio.TimeoutError:
            print('⏰ Done listening')

asyncio.run(main())
```

Install deps and run:
```bash
pip install websockets httpx
python test_ws.py
```

---

## Part 3 — React Native Integration

### Step 1 — Install packages

```bash
npx expo install expo-secure-store
npm install axios
```

### Step 2 — Create `utils/websocketService.ts`

```typescript
import * as SecureStore from 'expo-secure-store';

const WS_BASE = 'ws://192.168.1.x:8000'; // ← Use your PC's local IP, NOT 127.0.0.1
                                           // Find it: ipconfig (Windows) → IPv4 Address

type MessageHandler = (data: Record<string, unknown>) => void;

// ─── Personal notification stream (open once at app start) ───
class NotificationSocketManager {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectDelay = 3000;

  async connect() {
    const token = await SecureStore.getItemAsync('access_token');
    if (!token) return;

    const url = `${WS_BASE}/ws/notifications/?token=${token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('[WS] Notification socket connected');
      this.reconnectDelay = 3000;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handlers.forEach(h => h(data));
    };

    this.ws.onclose = async (event) => {
      if (event.code === 4001) return; // Auth failed — wait for login
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 60000);
    };
  }

  subscribe(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler); // returns unsubscribe fn
  }

  markRead(notificationId: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'mark_read',
        notification_id: notificationId
      }));
    }
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }
}

export const notificationSocket = new NotificationSocketManager();

// ─── Per-booking watcher (open per booking detail screen) ────
export class BookingSocket {
  private ws: WebSocket | null = null;

  constructor(
    private bookingId: string,
    private token: string,
    private onMessage: MessageHandler
  ) {}

  connect() {
    const url = `${WS_BASE}/ws/booking/${this.bookingId}/?token=${this.token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => console.log('[WS] Watching booking', this.bookingId);
    this.ws.onmessage = (e) => this.onMessage(JSON.parse(e.data));
    this.ws.onclose = (e) => {
      if (e.code !== 4001 && e.code !== 4003) {
        setTimeout(() => this.connect(), 3000);
      }
    };
  }

  disconnect() {
    this.ws?.close();
  }
}
```

> ⚠️ **Important for React Native on a real device or emulator:**
> Use your PC's local IP address (e.g. `192.168.1.5`) instead of `127.0.0.1`.
> `127.0.0.1` refers to the phone itself, not your PC.
> Find your IP: run `ipconfig` on Windows → look for **IPv4 Address**.

### Step 3 — Open socket in `app/_layout.tsx`

```typescript
import { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { useBookingStore } from '../store/bookingStore';
import { notificationSocket } from '../utils/websocketService';

export default function RootLayout() {
  const user = useAuthStore(s => s.user);
  const updateBooking = useBookingStore(s => s.updateBooking);

  useEffect(() => {
    if (!user) return;

    // Open personal notification stream
    notificationSocket.connect();

    // Handle incoming messages globally
    const unsub = notificationSocket.subscribe((msg) => {
      if (msg.type === 'booking_update') {
        // Live-update the booking in your Zustand store
        updateBooking(msg.booking_id as string, msg.booking as object);
      }
    });

    return () => {
      unsub();
      notificationSocket.disconnect();
    };
  }, [user]);

  // ... rest of layout
}
```

### Step 4 — Watch a specific booking in the detail screen

```typescript
import { useEffect, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import { BookingSocket } from '../utils/websocketService';

export default function BookingDetailScreen({ bookingId }) {
  const [status, setStatus] = useState('pending');

  useEffect(() => {
    let socket: BookingSocket;

    SecureStore.getItemAsync('access_token').then(token => {
      if (!token) return;
      socket = new BookingSocket(bookingId, token, (msg) => {
        if (msg.type === 'booking_update') {
          setStatus(msg.booking_status as string); // updates UI instantly
        }
      });
      socket.connect();
    });

    return () => socket?.disconnect(); // cleanup on unmount
  }, [bookingId]);

  return (
    // Your booking UI — status updates in real time
  );
}
```

---

## Part 4 — Moving to Redis (Production)

InMemoryChannelLayer works for development but has one limitation — it only works within a single process. When you deploy with multiple workers, WebSockets need Redis so all workers share the same message bus.

### Step 1 — Install Redis on your server

```bash
# Ubuntu
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Verify
redis-cli ping  # → PONG
```

### Step 2 — Install Python client

```bash
pip install channels-redis redis
```

### Step 3 — Set environment variable

In your `.env` or server environment:
```
REDIS_HOST=localhost
REDIS_PORT=6379
```

The `settings.py` already switches automatically when `REDIS_HOST` is set:
```python
if os.environ.get('REDIS_HOST'):
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [('localhost', 6379)],
            },
        },
    }
```

### Step 4 — Run with Daphne (production ASGI server)

```bash
pip install daphne
daphne -b 0.0.0.0 -p 8000 motobee.asgi:application
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `Connection refused` | Server not running or wrong port | Run `python manage.py runserver` |
| `4001 close code` | JWT token invalid or expired | Get a fresh token via `/auth/login/` |
| `4003 close code` | User not allowed to see this booking | Check customer/owner relationship |
| `WebSocket is not defined` | React Native version issue | Expo includes WebSocket — no package needed |
| Phone can't connect | Using `127.0.0.1` on device | Use your PC's LAN IP e.g. `192.168.1.5` |
| Messages not received | Using `runserver` with multiple tabs | Fine for dev — use Redis + Daphne for multi-worker |
| `No module named channels` | Not installed | `pip install channels` |
| Connection drops immediately | Token in wrong format | Pass as query param: `?token=<jwt>` not in headers |

---

## WebSocket Message Reference

### On connect (`/ws/notifications/`)
```json
{ "type": "connected", "unread_count": 2 }
```

### Booking status update (both consumers)
```json
{
  "type": "booking_update",
  "event": "accepted",
  "booking_id": "uuid-here",
  "booking_status": "accepted",
  "booking": {
    "id": "uuid",
    "garage_name": "Amit Motors",
    "date": "2026-03-20",
    "time": "10:00",
    "status": "accepted",
    "vehicle_type": "bike"
  }
}
```

### Mark as read (send from client)
```json
{ "action": "mark_read", "notification_id": "uuid-here" }
```

### Mark as read confirmation (received from server)
```json
{ "type": "marked_read", "notification_id": "uuid-here" }
```

### All possible `event` values
| Event | Triggered by | Who receives it |
|---|---|---|
| `new_booking` | Customer books | Owner |
| `accepted` | Owner accepts | Customer |
| `rejected` | Owner rejects | Customer |
| `in_progress` | Owner starts service | Customer |
| `completed` | Owner completes | Customer |
| `cancelled` | Customer cancels | Owner |

---

## Quick Test Checklist

- [ ] `python manage.py runserver` shows `ASGI/Channels`
- [ ] Browser console WebSocket connects without error
- [ ] `connected` message received on connect
- [ ] Booking accept in Postman → instant message in browser console
- [ ] Close code is not `4001` (would mean bad token)
- [ ] React Native connects using LAN IP not `127.0.0.1`
