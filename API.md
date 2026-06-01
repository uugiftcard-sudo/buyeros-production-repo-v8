# BuyerOS API Documentation

## Overview
BuyerOS Backend is a FastAPI microservice that provides AI-powered routing, financial reconciliation, and external integrations.

## Base URL
```
http://localhost:8000
```

## API Documentation
Interactive API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication
Most endpoints require an API key passed in the header:
```
X-API-Key: your-api-key
```

## Core Endpoints

### Health Check
```
GET /health
```
Returns the health status of the API.

### AI Router
```
POST /api/ai/route
```
Route prompts to AI models via OpenRouter.

**Request:**
```json
{
  "role": "supervisor",
  "prompt": "Your prompt here"
}
```

**Response:**
```json
{
  "reply": "AI response"
}
```

### Expense Claims
```
GET /api/expenses
POST /api/expenses
GET /api/expenses/{id}
PATCH /api/expenses/{id}
```

### Bank Reconciliation
```
POST /api/bank/import
GET /api/bank/reconciliations
GET /api/bank/reconciliations/{id}
```

### Task Management
```
POST /api/tasks/dispatch
GET /api/tasks/{id}
PATCH /api/tasks/{id}/cancel
```

## Error Responses
All errors return a standard JSON format:
```json
{
  "error": "ErrorType",
  "message": "Human readable message",
  "details": {}
}
```

## Rate Limiting
The API implements rate limiting to prevent abuse. Limits vary by endpoint.

## Environment Variables
See `.env.example` for required environment variables.
