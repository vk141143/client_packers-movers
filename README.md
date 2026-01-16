# Emergency Property Clearance API

FastAPI backend for UK-based Emergency Property Clearance & Operations platform.

## Project Structure

```
packers and movers/
├── app/
│   ├── core/
│   │   └── security.py          # JWT & password hashing
│   ├── database/
│   │   └── db.py                # Database connection
│   ├── models/
│   │   └── user.py              # User model
│   ├── routers/
│   │   └── auth.py              # Authentication endpoints
│   └── schemas/
│       └── auth.py              # Pydantic schemas
├── main.py                      # Application entry point
├── pyproject.toml               # Poetry dependencies
└── .env.example                 # Environment variables template
```

## Setup

1. Install dependencies:
```bash
poetry install
```

2. Run the application:
```bash
poetry run python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Client Registration
**POST** `/api/auth/register/client`

Request body:
```json
{
  "email": "client@example.com",
  "password": "securepassword",
  "full_name": "John Doe",
  "company_name": "ABC Council",
  "phone_number": "+44 7700 900000",
  "client_type": "Council",
  "address": "123 Main Street, London, UK"
}
```

Client type options: `Council`, `Housing Association`, `Landlord`, `Insurance Company`

### Client Login
**POST** `/api/auth/login/client`

Request body:
```json
{
  "email": "client@example.com",
  "password": "securepassword"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
