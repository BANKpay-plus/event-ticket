# Event Ticket API

Multi-organization ticket sales API for BMF/Bezirksmusikfest 2026 with BANKpay+/SEPA.digital integration.

## Base URL

```
https://api.event-ticket.at/v1
```

## Authentication

Currently public endpoints. Future versions will include API key authentication for organization management.

---

## Endpoints

### Health Check

#### GET /v1/heartbeat
Service health check.

**Response:**
```json
{
  "status": "up",
  "service": "event-ticket",
  "version": "2.0.0",
  "time": 1731945600
}
```

#### GET /v1/heartbeat/db
Database connectivity check.

---

### Organizations

#### GET /v1/organizations
List all active organizations.

**Response:**
```json
{
  "organizations": [
    {
      "id": 1,
      "slug": "mv-st-poelten",
      "name": "Musikverein St. Poelten",
      "description": "Traditionsreicher Musikverein...",
      "city": "St. Poelten",
      "logo_url": null,
      "primary_color": "#1976D2"
    }
  ]
}
```

#### GET /v1/organizations/:slug
Get organization details by slug.

**Parameters:**
- `slug` (path) - Organization slug (e.g., "mv-st-poelten")

**Response:**
```json
{
  "organization": {
    "id": 1,
    "slug": "mv-st-poelten",
    "name": "Musikverein St. Poelten",
    "description": "...",
    "email": "info@mv-stpoelten.at",
    "phone": "+43 2742 12345",
    "website": "https://mv-stpoelten.at",
    "street_address": "Rathausplatz 1",
    "postal_code": "3100",
    "city": "St. Poelten",
    "country": "AT",
    "logo_url": null,
    "primary_color": "#1976D2",
    "secondary_color": "#FFC107"
  }
}
```

#### GET /v1/organizations/:slug/payment-config
Get payment configuration for frontend integration.

**Response:**
```json
{
  "to": {
    "iban": "AT611904300234573201",
    "bic": "BKAUATWW",
    "recipient": {
      "name": "Musikverein St. Poelten",
      "alternateName": "Musikverein St. Poelten"
    },
    "referencePrefix": "BMF2026-STP"
  },
  "organization": {
    "name": "Musikverein St. Poelten",
    "email": "info@mv-stpoelten.at",
    "phone": "+43 2742 12345"
  }
}
```

---

### Events

#### GET /v1/organizations/:slug/events
List all events for an organization.

**Parameters:**
- `slug` (path) - Organization slug

**Response:**
```json
{
  "events": [
    {
      "id": 1,
      "slug": "bmf-2026-stpoelten",
      "name": "Bezirksmusikfest 2026 St. Poelten",
      "description": "Das grosse Bezirksmusikfest...",
      "event_type": "festival",
      "venue_name": "VAZ St. Poelten",
      "venue_address": "Kelsengasse 9, 3100 St. Poelten",
      "start_date": "2026-06-13T14:00:00",
      "end_date": "2026-06-14T02:00:00",
      "max_capacity": 8000,
      "current_sold": 0,
      "is_sold_out": false,
      "sales_start": "2025-12-01T00:00:00",
      "sales_end": "2026-06-12T23:59:59",
      "image_url": null
    }
  ]
}
```

#### GET /v1/organizations/:slug/events/:event_slug
Get event details with available tickets.

**Parameters:**
- `slug` (path) - Organization slug
- `event_slug` (path) - Event slug

**Response:**
```json
{
  "event": {
    "id": 1,
    "slug": "bmf-2026-stpoelten",
    "name": "Bezirksmusikfest 2026 St. Poelten",
    "description": "...",
    "event_type": "festival",
    "venue_name": "VAZ St. Poelten",
    "venue_address": "Kelsengasse 9, 3100 St. Poelten",
    "start_date": "2026-06-13T14:00:00",
    "end_date": "2026-06-14T02:00:00",
    "doors_open": null,
    "max_capacity": 8000,
    "current_sold": 0,
    "is_sold_out": false,
    "sales_start": "2025-12-01T00:00:00",
    "sales_end": "2026-06-12T23:59:59",
    "image_url": null
  },
  "tickets": [
    {
      "id": 1,
      "name": "Tageskarte Erwachsene",
      "description": "Tageseintritt zum Festgelaende",
      "price": 18.00,
      "currency": "EUR",
      "quantity_total": 3000,
      "quantity_sold": 0,
      "quantity_reserved": 0,
      "max_per_order": 10,
      "min_per_order": 1,
      "is_active": true,
      "available": 3000
    }
  ],
  "organization": {
    "id": 1,
    "name": "Musikverein St. Poelten"
  }
}
```

#### GET /v1/events/upcoming
List all upcoming events across all organizations.

**Query Parameters:**
- `limit` (optional) - Maximum number of events to return (default: 20)

---

### Orders

#### POST /v1/organizations/:slug/orders
Create a new ticket order.

**Parameters:**
- `slug` (path) - Organization slug

**Request Body:**
```json
{
  "customer_name": "Max Mustermann",
  "customer_email": "max@beispiel.at",
  "customer_phone": "+43 664 1234567",
  "customer_address": "Musterstrasse 1, 1010 Wien",
  "items": [
    {
      "ticket_id": 1,
      "quantity": 2
    },
    {
      "ticket_id": 3,
      "quantity": 1
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "order": {
    "id": 42,
    "order_number": "ORD-20251118143022-ABC123",
    "total_amount": 101.00,
    "payment_reference": "BMF2026-STP-ORD-20251118143022-ABC123",
    "items": [
      {
        "ticket_id": 1,
        "event_id": 1,
        "ticket_name": "Tageskarte Erwachsene",
        "unit_price": 18.00,
        "quantity": 2,
        "subtotal": 36.00,
        "ticket_codes": ["A1B2C3D4", "E5F6G7H8"]
      },
      {
        "ticket_id": 3,
        "event_id": 1,
        "ticket_name": "VIP-Ticket",
        "unit_price": 65.00,
        "quantity": 1,
        "subtotal": 65.00,
        "ticket_codes": ["I9J0K1L2"]
      }
    ]
  },
  "payment": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "qrcode_url": "https://api.sepa.digital/qr/...",
    "short_url": "https://sepa.id/ABC123",
    "iban": "AT611904300234573201",
    "bic": "BKAUATWW",
    "recipient": "Musikverein St. Poelten",
    "reference": "BMF2026-STP-ORD-20251118143022-ABC123",
    "amount": 101.00
  }
}
```

#### GET /v1/orders/:order_number
Get order details by order number.

**Parameters:**
- `order_number` (path) - Order number (e.g., "ORD-20251118143022-ABC123")

**Response:**
```json
{
  "order": {
    "id": 42,
    "organization_id": 1,
    "order_number": "ORD-20251118143022-ABC123",
    "customer_name": "Max Mustermann",
    "customer_email": "max@beispiel.at",
    "customer_phone": "+43 664 1234567",
    "customer_address": "Musterstrasse 1, 1010 Wien",
    "total_amount": 101.00,
    "currency": "EUR",
    "payment_status": "paid",
    "payment_reference": "BMF2026-STP-ORD-20251118143022-ABC123",
    "sepa_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "status": "confirmed",
    "created_at": "2025-11-18T14:30:22",
    "paid_at": "2025-11-18T14:31:45",
    "organization_name": "Musikverein St. Poelten",
    "organization_slug": "mv-st-poelten",
    "items": [
      {
        "id": 1,
        "ticket_name": "Tageskarte Erwachsene",
        "unit_price": 18.00,
        "quantity": 2,
        "subtotal": 36.00,
        "ticket_codes": ["A1B2C3D4", "E5F6G7H8"],
        "event_name": "Bezirksmusikfest 2026 St. Poelten",
        "start_date": "2026-06-13T14:00:00"
      }
    ]
  }
}
```

#### GET /v1/orders/:order_number/status
Check payment status for an order (polls SEPA.digital).

**Parameters:**
- `order_number` (path) - Order number

**Response:**
```json
{
  "status": "payment_settled",
  "paid": true
}
```

**Possible status values:**
- `pending` - Payment not yet received
- `created` - Order created, awaiting payment
- `payment_signed` - Payment initiated by customer
- `payment_settled` - Payment completed
- `paid` - Payment confirmed
- `failed` - Payment failed
- `refunded` - Payment refunded

---

## Payment Flow

### SEPA Instant Payment with BANKpay+

1. **Create Order** - POST to `/v1/organizations/:slug/orders`
2. **Display QR Code** - Show the returned `payment.qrcode_url` to customer
3. **Poll for Payment** - Check `/v1/orders/:order_number/status` every 1-2 seconds
4. **Payment Complete** - When `paid: true`, display success and ticket codes

### Manual Bank Transfer

Customers can also pay manually using the IBAN and reference from the order response. Payment will be detected within seconds via SEPA Instant Credit Transfer.

---

## Error Responses

All errors return appropriate HTTP status codes with a JSON body:

```json
{
  "error": "Error message description"
}
```

**Common Status Codes:**
- `400` - Bad Request (invalid input)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

---

## Frontend Integration

### Ticket Shop URL

```
/ticket-shop.html?org={org-slug}&event={event-slug}
```

Example:
```
https://event-ticket.at/ticket-shop.html?org=mv-st-poelten&event=bmf-2026-stpoelten
```

### Loading Payment Configuration

```javascript
const response = await fetch(`/v1/organizations/${orgSlug}/payment-config`);
const config = await response.json();

window.SEPAdigital = {
  to: config.to
};
```

---

## Rate Limits

Currently no rate limits. Future versions will implement:
- 100 requests/minute for public endpoints
- 1000 requests/minute for authenticated organization endpoints

---

## Changelog

### Version 2.0.0 (2025-11-18)
- Multi-organization support
- Event and ticket management
- Order and payment processing
- SEPA.digital integration
- Security fixes (SQL injection prevention)

### Version 1.0.0
- Initial A-bu.ch library subscription system
