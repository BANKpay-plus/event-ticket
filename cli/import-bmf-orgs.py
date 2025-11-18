#!/usr/bin/env python3
"""
Import BMF Organizations into the Event Ticket Database

Usage:
    python cli/import-bmf-orgs.py

This script reads the BMF organizations configuration from
data/bmf-organizations.json and imports them into the database.
"""

import os
import sys
import json
import psycopg2
import psycopg2.extras
from environs import Env

# Setup environment
env = Env()
env.read_env()

# Database configuration
DB_HOST = env.str('DB_HOST', '51.158.130.90')
DB_PORT = env.int('DB_PORT', 25120)
DB_NAME = env.str('DB_NAME', 'abuch')
DB_USER = env.str('DB_USER', '')
DB_PASSWORD = env.str('DB_PASSWORD', '')


def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def import_organizations(conn, organizations):
    """Import organizations into database"""
    cur = conn.cursor()
    imported = 0

    for org in organizations:
        try:
            cur.execute("""
                INSERT INTO organizations (
                    slug, name, description, email, phone, website,
                    street_address, postal_code, city, country,
                    iban, bic, recipient_name, payment_reference_prefix,
                    primary_color, secondary_color
                ) VALUES (
                    %(slug)s, %(name)s, %(description)s, %(email)s, %(phone)s, %(website)s,
                    %(street_address)s, %(postal_code)s, %(city)s, %(country)s,
                    %(iban)s, %(bic)s, %(recipient_name)s, %(payment_reference_prefix)s,
                    %(primary_color)s, %(secondary_color)s
                )
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    website = EXCLUDED.website,
                    street_address = EXCLUDED.street_address,
                    postal_code = EXCLUDED.postal_code,
                    city = EXCLUDED.city,
                    iban = EXCLUDED.iban,
                    bic = EXCLUDED.bic,
                    recipient_name = EXCLUDED.recipient_name,
                    payment_reference_prefix = EXCLUDED.payment_reference_prefix,
                    primary_color = EXCLUDED.primary_color,
                    secondary_color = EXCLUDED.secondary_color,
                    updated_at = CURRENT_TIMESTAMP
            """, org)
            imported += 1
            print(f"  + {org['name']} ({org['slug']})")
        except Exception as e:
            print(f"  ! Error importing {org['slug']}: {e}")

    return imported


def import_events(conn, events):
    """Import events into database"""
    cur = conn.cursor()
    imported = 0

    for event in events:
        try:
            # Get organization ID
            cur.execute("SELECT id FROM organizations WHERE slug = %s", (event['organization_slug'],))
            org = cur.fetchone()
            if not org:
                print(f"  ! Organization not found: {event['organization_slug']}")
                continue

            cur.execute("""
                INSERT INTO events (
                    organization_id, slug, name, description, event_type,
                    venue_name, venue_address, start_date, end_date,
                    max_capacity, sales_start, sales_end
                ) VALUES (
                    %(org_id)s, %(slug)s, %(name)s, %(description)s, %(event_type)s,
                    %(venue_name)s, %(venue_address)s, %(start_date)s, %(end_date)s,
                    %(max_capacity)s, %(sales_start)s, %(sales_end)s
                )
                ON CONFLICT (organization_id, slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    venue_name = EXCLUDED.venue_name,
                    venue_address = EXCLUDED.venue_address,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    max_capacity = EXCLUDED.max_capacity,
                    sales_start = EXCLUDED.sales_start,
                    sales_end = EXCLUDED.sales_end,
                    updated_at = CURRENT_TIMESTAMP
            """, {
                'org_id': org['id'],
                'slug': event['slug'],
                'name': event['name'],
                'description': event['description'],
                'event_type': event['event_type'],
                'venue_name': event['venue_name'],
                'venue_address': event['venue_address'],
                'start_date': event['start_date'],
                'end_date': event['end_date'],
                'max_capacity': event['max_capacity'],
                'sales_start': event['sales_start'],
                'sales_end': event['sales_end']
            })
            imported += 1
            print(f"  + {event['name']} ({event['slug']})")
        except Exception as e:
            print(f"  ! Error importing event {event['slug']}: {e}")

    return imported


def import_default_tickets(conn, ticket_templates):
    """Import default tickets for all events"""
    cur = conn.cursor()
    imported = 0

    # Get all events
    cur.execute("SELECT id, name FROM events")
    events = cur.fetchall()

    for event in events:
        for ticket in ticket_templates:
            try:
                cur.execute("""
                    INSERT INTO tickets (
                        event_id, name, description, price,
                        quantity_total, max_per_order, sort_order
                    ) VALUES (
                        %(event_id)s, %(name)s, %(description)s, %(price)s,
                        %(quantity_total)s, %(max_per_order)s, %(sort_order)s
                    )
                    ON CONFLICT DO NOTHING
                """, {
                    'event_id': event['id'],
                    'name': ticket['name'],
                    'description': ticket['description'],
                    'price': ticket['price'],
                    'quantity_total': 1000,  # Default quantity
                    'max_per_order': ticket['max_per_order'],
                    'sort_order': ticket['sort_order']
                })
                imported += 1
            except Exception as e:
                print(f"  ! Error importing ticket {ticket['name']} for {event['name']}: {e}")

    return imported


def main():
    """Main import function"""
    print("BMF Organizations Import Script")
    print("=" * 50)

    # Load data file
    data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'bmf-organizations.json')

    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}")
        sys.exit(1)

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\nLoaded {len(data['organizations'])} organizations")
    print(f"Loaded {len(data['events'])} events")
    print(f"Loaded {len(data['ticket_templates'])} ticket templates")

    # Connect to database
    try:
        conn = get_db_connection()
        print("\nConnected to database")
    except Exception as e:
        print(f"\nError connecting to database: {e}")
        sys.exit(1)

    try:
        # Import organizations
        print("\nImporting organizations...")
        org_count = import_organizations(conn, data['organizations'])

        # Import events
        print("\nImporting events...")
        event_count = import_events(conn, data['events'])

        # Import default tickets
        print("\nImporting default tickets...")
        ticket_count = import_default_tickets(conn, data['ticket_templates'])

        # Commit changes
        conn.commit()

        print("\n" + "=" * 50)
        print(f"Import completed!")
        print(f"  Organizations: {org_count}")
        print(f"  Events: {event_count}")
        print(f"  Tickets: {ticket_count}")

    except Exception as e:
        conn.rollback()
        print(f"\nError during import: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
