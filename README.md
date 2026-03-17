# MOTOBEE Backend (No Tenants)

Simple setup — PostgreSQL + JWT + WebSockets. Tenants will be added later.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements-dev.txt

# 2. Create migrations and migrate
python manage.py makemigrations
python manage.py migrate

# 3. Create admin user
python manage.py createsuperuser

# 4. Run server
python manage.py runserver
```

## API Base URL
```
http://127.0.0.1:8000/api/v1/
```

## Swagger Docs
```
http://127.0.0.1:8000/api/docs/
```

## Admin Panel
```
http://127.0.0.1:8000/admin/
```

## Key Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/v1/auth/register/` | ❌ | Register |
| POST | `/api/v1/auth/login/` | ❌ | Login → JWT |
| POST | `/api/v1/auth/logout/` | ✅ | Logout |
| GET | `/api/v1/auth/me/` | ✅ | My profile |
| GET | `/api/v1/garages/` | ✅ | List garages |
| POST | `/api/v1/garages/` | ✅ Owner | Create garage |
| GET | `/api/v1/garages/mine/` | ✅ Owner | My garage |
| PUT | `/api/v1/garages/{id}/schedule/{date}/` | ✅ Owner | Set schedule |
| POST | `/api/v1/bookings/` | ✅ Customer | Book slot |
| PATCH | `/api/v1/bookings/{id}/accept/` | ✅ Owner | Accept booking |
| PATCH | `/api/v1/bookings/{id}/complete/` | ✅ Owner | Complete booking |
