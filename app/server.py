#!/usr/bin/env python3
"""
Event Ticket API Server
Multi-organization ticket sales for BMF/Bezirksmusikfest 2026
Supports BANKpay+ / SEPA.digital payment integration
"""

import hashlib
import uuid
import time
import os
import requests
import datetime
import logging
import secrets
import string
import psycopg2
import psycopg2.extras

from json import dumps, loads
from sanic import Sanic
from sanic import response
from sanic.response import json
from sanic.exceptions import NotFound, InvalidUsage
from environs import Env
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

# Logging configuration
logging_format = "[%(asctime)s] %(process)d-%(levelname)s "
logging_format += "%(module)s::%(funcName)s():l%(lineno)d: "
logging_format += "%(message)s"

logging.basicConfig(
    format=logging_format,
    level=logging.INFO
)
log = logging.getLogger()

# Environment setup
env = Env()
env.read_env()

# App configuration
app = Sanic(name='event-ticket')

# Database configuration from environment
DB_HOST = env.str('DB_HOST', '51.158.130.90')
DB_PORT = env.int('DB_PORT', 25120)
DB_NAME = env.str('DB_NAME', 'abuch')
DB_USER = env.str('DB_USER', '')
DB_PASSWORD = env.str('DB_PASSWORD', '')

# SEPA.digital API configuration
SEPA_API_URL = env.str('SEPA_API_URL', 'https://api.sepa.digital')


def get_db_connection():
    """Create a new database connection with DictCursor"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"ORD-{timestamp}-{random_part}"


def generate_ticket_code():
    """Generate unique ticket code for entry"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


# Database setup
@app.listener('before_server_start')
async def setup_db(app, loop):
    """Initialize database connection pool"""
    try:
        app.db_pool = True
        log.info("Database configuration ready")
    except Exception as e:
        log.error(f"Database setup error: {e}")


# CORS middleware
@app.middleware('response')
async def add_cors_headers(request, response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"


@app.middleware('request')
async def handle_options(request):
    if request.method == "OPTIONS":
        return response.empty(status=204)


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.route('/')
def service_root(request):
    return response.redirect('/v1/heartbeat')


@app.route('/v1/heartbeat')
async def service_heartbeat(request):
    return json({
        "status": "up",
        "service": "event-ticket",
        "version": "2.0.0",
        "time": int(time.time())
    })


@app.route('/v1/heartbeat/db')
async def service_heartbeat_db(request):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        return json({
            "status": "up",
            "service": "database",
            "time": int(time.time())
        })
    except Exception as e:
        log.error(f"Database health check failed: {e}")
        return json({
            "status": "down",
            "service": "database",
            "error": str(e)
        }, status=503)


# =============================================================================
# Organization Endpoints
# =============================================================================

@app.route('/v1/organizations', methods=['GET'])
async def list_organizations(request):
    """List all active organizations"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, slug, name, description, city, logo_url, primary_color
            FROM organizations
            WHERE is_active = true
            ORDER BY name
        """)
        organizations = cur.fetchall()
        conn.close()
        return json({"organizations": organizations})
    except Exception as e:
        log.error(f"Error listing organizations: {e}")
        return json({"error": "Failed to retrieve organizations"}, status=500)


@app.route('/v1/organizations/<org_slug:str>', methods=['GET'])
async def get_organization(request, org_slug):
    """Get organization details by slug"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, slug, name, description, email, phone, website,
                   street_address, postal_code, city, country,
                   logo_url, primary_color, secondary_color
            FROM organizations
            WHERE slug = %s AND is_active = true
        """, (org_slug,))
        org = cur.fetchone()
        conn.close()

        if not org:
            return json({"error": "Organization not found"}, status=404)

        return json({"organization": org})
    except Exception as e:
        log.error(f"Error getting organization: {e}")
        return json({"error": "Failed to retrieve organization"}, status=500)


@app.route('/v1/organizations/<org_slug:str>/payment-config', methods=['GET'])
async def get_organization_payment_config(request, org_slug):
    """Get payment configuration for an organization (for frontend)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT slug, name, iban, bic, recipient_name, payment_reference_prefix,
                   email, phone
            FROM organizations
            WHERE slug = %s AND is_active = true
        """, (org_slug,))
        org = cur.fetchone()
        conn.close()

        if not org:
            return json({"error": "Organization not found"}, status=404)

        # Return payment config in format expected by frontend
        return json({
            "to": {
                "iban": org['iban'],
                "bic": org['bic'],
                "recipient": {
                    "name": org['recipient_name'],
                    "alternateName": org['name']
                },
                "referencePrefix": org['payment_reference_prefix']
            },
            "organization": {
                "name": org['name'],
                "email": org['email'],
                "phone": org['phone']
            }
        })
    except Exception as e:
        log.error(f"Error getting payment config: {e}")
        return json({"error": "Failed to retrieve payment configuration"}, status=500)


# =============================================================================
# Event Endpoints
# =============================================================================

@app.route('/v1/organizations/<org_slug:str>/events', methods=['GET'])
async def list_organization_events(request, org_slug):
    """List all events for an organization"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # First get organization
        cur.execute("SELECT id FROM organizations WHERE slug = %s AND is_active = true", (org_slug,))
        org = cur.fetchone()
        if not org:
            conn.close()
            return json({"error": "Organization not found"}, status=404)

        # Get events
        cur.execute("""
            SELECT e.id, e.slug, e.name, e.description, e.event_type,
                   e.venue_name, e.venue_address, e.start_date, e.end_date,
                   e.max_capacity, e.current_sold, e.is_sold_out,
                   e.sales_start, e.sales_end, e.image_url
            FROM events e
            WHERE e.organization_id = %s AND e.is_active = true
            ORDER BY e.start_date
        """, (org['id'],))
        events = cur.fetchall()
        conn.close()

        # Convert datetime objects to strings
        for event in events:
            for key in ['start_date', 'end_date', 'sales_start', 'sales_end']:
                if event[key]:
                    event[key] = event[key].isoformat()

        return json({"events": events})
    except Exception as e:
        log.error(f"Error listing events: {e}")
        return json({"error": "Failed to retrieve events"}, status=500)


@app.route('/v1/organizations/<org_slug:str>/events/<event_slug:str>', methods=['GET'])
async def get_event(request, org_slug, event_slug):
    """Get event details with available tickets"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get organization
        cur.execute("SELECT id, name FROM organizations WHERE slug = %s AND is_active = true", (org_slug,))
        org = cur.fetchone()
        if not org:
            conn.close()
            return json({"error": "Organization not found"}, status=404)

        # Get event
        cur.execute("""
            SELECT e.id, e.slug, e.name, e.description, e.event_type,
                   e.venue_name, e.venue_address, e.start_date, e.end_date,
                   e.doors_open, e.max_capacity, e.current_sold, e.is_sold_out,
                   e.sales_start, e.sales_end, e.image_url
            FROM events e
            WHERE e.organization_id = %s AND e.slug = %s AND e.is_active = true
        """, (org['id'], event_slug))
        event = cur.fetchone()

        if not event:
            conn.close()
            return json({"error": "Event not found"}, status=404)

        # Get tickets for event
        cur.execute("""
            SELECT id, name, description, price, currency,
                   quantity_total, quantity_sold, quantity_reserved,
                   max_per_order, min_per_order, is_active
            FROM tickets
            WHERE event_id = %s AND is_active = true
            ORDER BY sort_order, price
        """, (event['id'],))
        tickets = cur.fetchall()
        conn.close()

        # Convert datetime objects and decimals
        for key in ['start_date', 'end_date', 'doors_open', 'sales_start', 'sales_end']:
            if event[key]:
                event[key] = event[key].isoformat()

        for ticket in tickets:
            ticket['price'] = float(ticket['price'])
            ticket['available'] = (ticket['quantity_total'] or 999999) - ticket['quantity_sold'] - ticket['quantity_reserved']

        return json({
            "event": event,
            "tickets": tickets,
            "organization": {"id": org['id'], "name": org['name']}
        })
    except Exception as e:
        log.error(f"Error getting event: {e}")
        return json({"error": "Failed to retrieve event"}, status=500)


# =============================================================================
# Order Endpoints
# =============================================================================

@app.route('/v1/organizations/<org_slug:str>/orders', methods=['POST'])
async def create_order(request, org_slug):
    """Create a new ticket order"""
    try:
        data = request.json
        if not data:
            return json({"error": "No data provided"}, status=400)

        # Validate required fields
        required_fields = ['customer_name', 'customer_email', 'items']
        for field in required_fields:
            if field not in data:
                return json({"error": f"Missing required field: {field}"}, status=400)

        if not data['items'] or len(data['items']) == 0:
            return json({"error": "Order must contain at least one item"}, status=400)

        conn = get_db_connection()
        cur = conn.cursor()

        # Get organization
        cur.execute("""
            SELECT id, iban, bic, recipient_name, payment_reference_prefix, name
            FROM organizations WHERE slug = %s AND is_active = true
        """, (org_slug,))
        org = cur.fetchone()
        if not org:
            conn.close()
            return json({"error": "Organization not found"}, status=404)

        # Calculate total and validate tickets
        total_amount = Decimal('0')
        order_items = []

        for item in data['items']:
            ticket_id = item.get('ticket_id')
            quantity = item.get('quantity', 1)

            if not ticket_id or quantity < 1:
                conn.close()
                return json({"error": "Invalid item in order"}, status=400)

            # Get ticket details
            cur.execute("""
                SELECT t.id, t.name, t.price, t.event_id, t.quantity_total,
                       t.quantity_sold, t.quantity_reserved, t.max_per_order, t.min_per_order,
                       e.name as event_name
                FROM tickets t
                JOIN events e ON t.event_id = e.id
                WHERE t.id = %s AND t.is_active = true
            """, (ticket_id,))
            ticket = cur.fetchone()

            if not ticket:
                conn.close()
                return json({"error": f"Ticket {ticket_id} not found"}, status=404)

            # Check availability
            available = (ticket['quantity_total'] or 999999) - ticket['quantity_sold'] - ticket['quantity_reserved']
            if quantity > available:
                conn.close()
                return json({"error": f"Not enough tickets available for {ticket['name']}"}, status=400)

            # Check quantity limits
            if quantity > ticket['max_per_order']:
                conn.close()
                return json({"error": f"Maximum {ticket['max_per_order']} tickets allowed for {ticket['name']}"}, status=400)

            if quantity < ticket['min_per_order']:
                conn.close()
                return json({"error": f"Minimum {ticket['min_per_order']} tickets required for {ticket['name']}"}, status=400)

            subtotal = Decimal(str(ticket['price'])) * quantity
            total_amount += subtotal

            # Generate ticket codes
            ticket_codes = [generate_ticket_code() for _ in range(quantity)]

            order_items.append({
                'ticket_id': ticket['id'],
                'event_id': ticket['event_id'],
                'ticket_name': ticket['name'],
                'unit_price': float(ticket['price']),
                'quantity': quantity,
                'subtotal': float(subtotal),
                'ticket_codes': ticket_codes
            })

        # Create order
        order_number = generate_order_number()
        payment_reference = f"{org['payment_reference_prefix']}-{order_number}"

        cur.execute("""
            INSERT INTO orders (organization_id, order_number, customer_name, customer_email,
                              customer_phone, customer_address, total_amount, payment_reference,
                              ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            org['id'],
            order_number,
            data['customer_name'],
            data['customer_email'],
            data.get('customer_phone'),
            data.get('customer_address'),
            float(total_amount),
            payment_reference,
            request.ip,
            request.headers.get('User-Agent')
        ))
        order_id = cur.fetchone()['id']

        # Create order items
        for item in order_items:
            cur.execute("""
                INSERT INTO order_items (order_id, ticket_id, event_id, ticket_name,
                                        unit_price, quantity, subtotal, ticket_codes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                order_id,
                item['ticket_id'],
                item['event_id'],
                item['ticket_name'],
                item['unit_price'],
                item['quantity'],
                item['subtotal'],
                item['ticket_codes']
            ))

            # Reserve tickets
            cur.execute("""
                UPDATE tickets SET quantity_reserved = quantity_reserved + %s
                WHERE id = %s
            """, (item['quantity'], item['ticket_id']))

        conn.commit()

        # Initiate SEPA.digital payment
        sepa_payload = {
            'correlationId': f"event-ticket-{org_slug}-{order_number}",
            'iban': org['iban'],
            'bic': org['bic'],
            'amount': float(total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'name': org['recipient_name'],
            'reference': payment_reference,
            'customerId': data['customer_email']
        }

        try:
            sepa_response = requests.post(
                f"{SEPA_API_URL}/credit-transfer",
                json=sepa_payload,
                timeout=10
            )
            sepa_data = sepa_response.json()

            # Update order with SEPA data
            if sepa_data.get('uuid'):
                cur.execute("""
                    UPDATE orders
                    SET sepa_uuid = %s, sepa_short_url = %s, sepa_qr_code_url = %s
                    WHERE id = %s
                """, (
                    sepa_data['uuid'],
                    sepa_data.get('_links', {}).get('shortUrl'),
                    sepa_data.get('_links', {}).get('qrcode'),
                    order_id
                ))
                conn.commit()

        except Exception as e:
            log.error(f"SEPA.digital API error: {e}")
            sepa_data = None

        conn.close()

        return json({
            "order": {
                "id": order_id,
                "order_number": order_number,
                "total_amount": float(total_amount),
                "payment_reference": payment_reference,
                "items": order_items
            },
            "payment": {
                "uuid": sepa_data.get('uuid') if sepa_data else None,
                "qrcode_url": sepa_data.get('_links', {}).get('qrcode') if sepa_data else None,
                "short_url": sepa_data.get('_links', {}).get('shortUrl') if sepa_data else None,
                "iban": org['iban'],
                "bic": org['bic'],
                "recipient": org['recipient_name'],
                "reference": payment_reference,
                "amount": float(total_amount)
            }
        }, status=201)

    except Exception as e:
        log.error(f"Error creating order: {e}")
        return json({"error": "Failed to create order"}, status=500)


@app.route('/v1/orders/<order_number:str>', methods=['GET'])
async def get_order(request, order_number):
    """Get order details by order number"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT o.*, org.name as organization_name, org.slug as organization_slug
            FROM orders o
            JOIN organizations org ON o.organization_id = org.id
            WHERE o.order_number = %s
        """, (order_number,))
        order = cur.fetchone()

        if not order:
            conn.close()
            return json({"error": "Order not found"}, status=404)

        # Get order items
        cur.execute("""
            SELECT oi.*, e.name as event_name, e.start_date
            FROM order_items oi
            JOIN events e ON oi.event_id = e.id
            WHERE oi.order_id = %s
        """, (order['id'],))
        items = cur.fetchall()
        conn.close()

        # Convert types
        order['total_amount'] = float(order['total_amount'])
        for key in ['created_at', 'updated_at', 'paid_at']:
            if order[key]:
                order[key] = order[key].isoformat()

        for item in items:
            item['unit_price'] = float(item['unit_price'])
            item['subtotal'] = float(item['subtotal'])
            if item['start_date']:
                item['start_date'] = item['start_date'].isoformat()

        order['items'] = items

        return json({"order": order})
    except Exception as e:
        log.error(f"Error getting order: {e}")
        return json({"error": "Failed to retrieve order"}, status=500)


@app.route('/v1/orders/<order_number:str>/status', methods=['GET'])
async def check_order_payment_status(request, order_number):
    """Check payment status for an order (polls SEPA.digital)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, sepa_uuid, payment_status, total_amount
            FROM orders WHERE order_number = %s
        """, (order_number,))
        order = cur.fetchone()

        if not order:
            conn.close()
            return json({"error": "Order not found"}, status=404)

        # If already paid, return status
        if order['payment_status'] in ['paid', 'payment_settled', 'payment_signed']:
            conn.close()
            return json({
                "status": order['payment_status'],
                "paid": True
            })

        # Check with SEPA.digital
        if order['sepa_uuid']:
            try:
                sepa_response = requests.get(
                    f"{SEPA_API_URL}/v1/tx/{order['sepa_uuid']}",
                    timeout=5
                )
                sepa_data = sepa_response.json()

                if sepa_data.get('status') in ['payment_settled', 'payment_signed']:
                    # Update order status
                    cur.execute("""
                        UPDATE orders
                        SET payment_status = %s, paid_at = CURRENT_TIMESTAMP, status = 'confirmed'
                        WHERE id = %s
                    """, (sepa_data['status'], order['id']))

                    # Convert reserved tickets to sold
                    cur.execute("""
                        UPDATE tickets t
                        SET quantity_sold = quantity_sold + oi.quantity,
                            quantity_reserved = quantity_reserved - oi.quantity
                        FROM order_items oi
                        WHERE oi.order_id = %s AND t.id = oi.ticket_id
                    """, (order['id'],))

                    conn.commit()
                    conn.close()

                    return json({
                        "status": sepa_data['status'],
                        "paid": True
                    })

                conn.close()
                return json({
                    "status": sepa_data.get('status', 'pending'),
                    "paid": False
                })

            except Exception as e:
                log.error(f"SEPA.digital status check error: {e}")

        conn.close()
        return json({
            "status": order['payment_status'],
            "paid": False
        })

    except Exception as e:
        log.error(f"Error checking order status: {e}")
        return json({"error": "Failed to check order status"}, status=500)


# =============================================================================
# Public Event Listing (for homepage)
# =============================================================================

@app.route('/v1/events/upcoming', methods=['GET'])
async def list_upcoming_events(request):
    """List all upcoming events across all organizations"""
    try:
        limit = request.args.get('limit', 20)
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT e.id, e.slug, e.name, e.description, e.event_type,
                   e.venue_name, e.start_date, e.end_date, e.image_url,
                   e.is_sold_out,
                   o.slug as organization_slug, o.name as organization_name
            FROM events e
            JOIN organizations o ON e.organization_id = o.id
            WHERE e.is_active = true
              AND e.start_date > CURRENT_TIMESTAMP
              AND o.is_active = true
            ORDER BY e.start_date
            LIMIT %s
        """, (int(limit),))
        events = cur.fetchall()
        conn.close()

        for event in events:
            for key in ['start_date', 'end_date']:
                if event[key]:
                    event[key] = event[key].isoformat()

        return json({"events": events})
    except Exception as e:
        log.error(f"Error listing upcoming events: {e}")
        return json({"error": "Failed to retrieve events"}, status=500)


# =============================================================================
# Legacy IBAN endpoint (secured)
# =============================================================================

@app.route('/v1/iban/<iban_id:str>', methods=['GET', 'OPTIONS'])
async def iban_details(request, iban_id):
    """Get IBAN details (legacy endpoint, secured with parameterized query)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # FIXED: Using parameterized query to prevent SQL injection
        cur.execute("SELECT * FROM iban WHERE uuid = %s", (iban_id,))
        result = cur.fetchone()
        conn.close()

        if not result:
            return json({"status": "error", "message": "IBAN not found"}, status=404)

        return json({"status": "success", "data": result})
    except Exception as e:
        log.error(f"Error getting IBAN: {e}")
        return json({"status": "error", "message": "Database error"}, status=500)


# =============================================================================
# Inbox endpoint (legacy)
# =============================================================================

@app.route("/inbox", methods=["POST", "GET", "OPTIONS"])
async def post_inbox(request):
    """Generic message inbox"""
    pwd = os.path.dirname(os.path.abspath(__file__))
    inbox_file = os.path.join(pwd, "..", "data", "inbox.json")

    try:
        os.makedirs(os.path.dirname(inbox_file), exist_ok=True)

        if os.path.exists(inbox_file):
            with open(inbox_file, 'r') as f:
                inbox = loads(f.read() or '[]')
        else:
            inbox = []

        if request.json:
            inbox.append(request.json)
            with open(inbox_file, 'w') as f:
                f.write(dumps(inbox))

        if request.json and 'email' in request.json:
            msg = f"Thanks for your message -- we'll reply to {request.json['email']}"
        elif request.json and 'tel' in request.json:
            msg = f"Thanks for your message -- we'll call you at {request.json['tel']}"
        else:
            msg = "Message received"

        return json({"status": "success", "message": msg})
    except Exception as e:
        log.error(f"Inbox error: {e}")
        return json({"status": "error", "message": str(e)}, status=500)


# =============================================================================
# Run server
# =============================================================================

if __name__ == '__main__':
    port = env.int('PORT', 8010)
    debug = env.bool('DEBUG', True)
    workers = env.int('WORKERS', 1)

    log.info(f"Starting Event Ticket API on port {port}")
    app.run(
        host='0.0.0.0',
        port=port,
        workers=workers,
        debug=debug,
        access_log=debug
    )
