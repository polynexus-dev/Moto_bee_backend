# Adding Multi-Tenancy to MOTOBEE
## Step-by-Step Migration Guide (No Tenants → django-tenants)

> **When to do this:** Only after your core features (auth, garages, bookings) are fully working and tested.
> This is a one-way change — plan carefully before starting.

---

## What Will Change

| | Before (Now) | After (Tenants) |
|---|---|---|
| Database | Single PostgreSQL schema | Multiple schemas (one per city) |
| URL routing | `127.0.0.1:8000` | `nagpur.motobee.in`, `mumbai.motobee.in` |
| Migrations | `python manage.py migrate` | `python manage.py migrate_schemas` |
| App list | Flat `INSTALLED_APPS` | Split into `SHARED_APPS` + `TENANT_APPS` |
| Middleware | Standard Django | `TenantMainMiddleware` as first middleware |
| DB Engine | `django.db.backends.postgresql` | `django_tenants.postgresql_backend` |

---

## Prerequisites

- [ ] PostgreSQL is running
- [ ] Core features fully tested without tenants
- [ ] You have a fresh database (or are okay wiping existing data)
- [ ] `django-tenants` requires **PostgreSQL only** — SQLite will not work

---

## Step 1 — Install django-tenants

```bash
pip install django-tenants
```

Add to `requirements.txt`:
```
django-tenants>=3.5
```

---

## Step 2 — Create the `tenants` app

```bash
python manage.py startapp tenants
```

Create `tenants/models.py`:
```python
from django_tenants.models import TenantMixin, DomainMixin
from django.db import models


class Client(TenantMixin):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    admin_email = models.EmailField(blank=True)
    auto_create_schema = True  # Required — auto runs migrations per tenant


class Domain(DomainMixin):
    """Maps subdomain → tenant. e.g. nagpur.motobee.in → nagpur schema"""
    pass
```

Create `tenants/admin.py`:
```python
from django.contrib import admin
from .models import Client, Domain

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'schema_name', 'city', 'is_active', 'created_at']

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
```

---

## Step 3 — Update `settings.py`

### 3a — Replace `INSTALLED_APPS` with split `SHARED_APPS` + `TENANT_APPS`

**Remove this:**
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'channels',
    'drf_spectacular',
    'accounts',
    'garages',
    'bookings',
    'notifications',
]
```

**Add this:**
```python
SHARED_APPS = [
    'django_tenants',               # MUST be first
    'tenants',                      # Your tenant model
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'channels',
    'drf_spectacular',
    'accounts',                     # Users are SHARED across all tenants
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'garages',                      # Each city has its own garages
    'bookings',                     # Each city has its own bookings
    'notifications',                # Each city has its own notifications
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]
```

### 3b — Add tenant config below INSTALLED_APPS

```python
TENANT_MODEL = 'tenants.Client'
TENANT_DOMAIN_MODEL = 'tenants.Domain'
PUBLIC_SCHEMA_NAME = 'public'
PUBLIC_SCHEMA_URLCONF = 'motobee.urls_public'
```

### 3c — Replace middleware

**Remove this:**
```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...
]
```

**Add this:**
```python
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # MUST be first
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### 3d — Replace database engine

**Remove this:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        ...
    }
}
```

**Add this:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',  # Only change is ENGINE
        'NAME': os.environ.get('DB_NAME', 'motobee'),
        'USER': os.environ.get('DB_USER', 'admin'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'admin'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']
```

### 3e — Update ROOT_URLCONF

```python
ROOT_URLCONF = 'motobee.urls'           # tenant schemas use this
PUBLIC_SCHEMA_URLCONF = 'motobee.urls_public'  # public schema uses this
```

---

## Step 4 — Create `urls_public.py`

Create `motobee/urls_public.py`:
```python
"""
URLs only available on the public schema (tenant management).
Accessed via the base domain e.g. motobee.in
"""
from django.urls import path, include

urlpatterns = [
    path('api/v1/auth/', include('accounts.urls')),
]
```

---

## Step 5 — Create the `create_tenant` management command

Create `tenants/management/__init__.py` (empty)
Create `tenants/management/commands/__init__.py` (empty)
Create `tenants/management/commands/create_tenant.py`:

```python
from django.core.management.base import BaseCommand
from tenants.models import Client, Domain


class Command(BaseCommand):
    help = 'Create a new MOTOBEE tenant zone'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Zone name e.g. Nagpur')
        parser.add_argument('--schema', required=True, help='Schema name e.g. nagpur')
        parser.add_argument('--subdomain', required=True, help='e.g. nagpur.motobee.in')
        parser.add_argument('--city', default='')
        parser.add_argument('--state', default='Maharashtra')

    def handle(self, *args, **options):
        schema = options['schema'].lower().replace(' ', '_')

        if Client.objects.filter(schema_name=schema).exists():
            self.stdout.write(self.style.WARNING(f"Tenant '{schema}' already exists."))
            return

        tenant = Client(
            schema_name=schema,
            name=options['name'],
            city=options['city'] or options['name'],
            state=options['state'],
        )
        tenant.save()  # auto_create_schema=True handles migrations

        Domain.objects.create(
            domain=options['subdomain'],
            tenant=tenant,
            is_primary=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Tenant '{options['name']}' created!\n"
            f"   Schema:    {schema}\n"
            f"   Domain:    {options['subdomain']}\n"
        ))
```

---

## Step 6 — Reset the database

> ⚠️ This wipes all existing data. Back up anything important first.

In **pgAdmin** or **psql**:
```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO admin;
```

---

## Step 7 — Run migrations

```bash
# Migrate shared apps into public schema (users, tenants table, admin, etc.)
python manage.py migrate_schemas --shared

# Verify tenants table exists — should return empty list, no error
python manage.py shell -c "from tenants.models import Client; print(Client.objects.all())"
```

---

## Step 8 — Create your tenants

```bash
# Create Nagpur
python manage.py create_tenant \
  --name Nagpur \
  --schema nagpur \
  --subdomain nagpur.localhost

# Create Mumbai
python manage.py create_tenant \
  --name Mumbai \
  --schema mumbai \
  --subdomain mumbai.localhost

# Migrate all tenant schemas
python manage.py migrate_schemas --tenant
```

---

## Step 9 — Update Windows hosts file

Open Notepad **as Administrator**, edit:
```
C:\Windows\System32\drivers\etc\hosts
```

Add:
```
127.0.0.1   nagpur.localhost
127.0.0.1   mumbai.localhost
127.0.0.1   public.localhost
```

---

## Step 10 — Test tenant isolation

Start server:
```bash
python manage.py runserver
```

**Register on Nagpur:**
```
POST http://nagpur.localhost:8000/api/v1/auth/register/
{
  "name": "Rahul",
  "email": "rahul@test.com",
  "phone": "9876543210",
  "password": "testpass123",
  "role": "owner"
}
```

**Create a garage on Nagpur:**
```
POST http://nagpur.localhost:8000/api/v1/garages/
Authorization: Bearer <token>
{
  "name": "Nagpur Motors",
  "address": "Ring Road, Nagpur",
  ...
}
```

**Verify Mumbai sees nothing:**
```
GET http://mumbai.localhost:8000/api/v1/garages/
→ Should return []   ✅ Isolation working
```

**Verify in pgAdmin:**
```sql
SELECT * FROM nagpur.garages_garage;   -- Has Nagpur Motors
SELECT * FROM mumbai.garages_garage;   -- Empty
SELECT * FROM public.accounts_user;    -- Has Rahul (shared)
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `relation "tenants_client" does not exist` | Forgot `migrate_schemas --shared` | Run `python manage.py migrate_schemas --shared` |
| `ambiguous option --domain` | Using wrong flag | Use `--subdomain` not `--domain` |
| `No installed app with label 'admin'` | `admin` missing from `SHARED_APPS` | Add `django.contrib.admin` to `SHARED_APPS` |
| `auth.E003 email must be unique` | `email` field not set `unique=True` | Add `email = models.EmailField(unique=True)` to User model |
| `migrate_schemas --tenant` fails | No tenants created yet | Create at least one tenant first |
| Admin panel crashes | `django_admin_log` table missing | Run `migrate_schemas --shared` |

---

## File Checklist

When adding tenants, these are the files you touch:

```
✏️  motobee/settings.py          — INSTALLED_APPS, MIDDLEWARE, DATABASES, TENANT_MODEL
✏️  motobee/urls.py              — No change needed
➕  motobee/urls_public.py       — New file for public schema URLs
➕  tenants/__init__.py
➕  tenants/models.py            — Client + Domain models
➕  tenants/admin.py
➕  tenants/apps.py
➕  tenants/management/commands/create_tenant.py
🗑️  (wipe DB and re-migrate)
```

Everything else — `accounts`, `garages`, `bookings`, `notifications`, `utils` — stays exactly the same.

---

## Production DNS Setup

Once deployed, instead of editing hosts files, set real DNS:

```
nagpur.motobee.in  →  A  <your_server_ip>
mumbai.motobee.in  →  A  <your_server_ip>
pune.motobee.in    →  A  <your_server_ip>
```

Nginx handles subdomain routing and forwards all to the same Django process. Django-tenants reads the `Host` header and switches schemas automatically.
