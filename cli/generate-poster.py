#!/usr/bin/env python3
"""
BMF 2026 Event Poster Generator

Generates professional PDF posters for Bezirksmusikfest events.
Can create individual event posters or a tour poster series.

Usage:
    python cli/generate-poster.py                    # Generate all posters
    python cli/generate-poster.py --event bmf-demo   # Generate single poster
    python cli/generate-poster.py --tour             # Generate tour series poster
"""

import os
import sys
import json
import argparse
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Color schemes for different organizations
COLOR_SCHEMES = {
    'default': {
        'primary': colors.HexColor('#667eea'),
        'secondary': colors.HexColor('#764ba2'),
        'accent': colors.HexColor('#FFC107'),
        'text': colors.white,
        'text_dark': colors.HexColor('#333333')
    },
    'mv-st-poelten': {
        'primary': colors.HexColor('#1976D2'),
        'secondary': colors.HexColor('#0D47A1'),
        'accent': colors.HexColor('#FFC107'),
        'text': colors.white,
        'text_dark': colors.HexColor('#333333')
    },
    'tk-krems': {
        'primary': colors.HexColor('#2E7D32'),
        'secondary': colors.HexColor('#1B5E20'),
        'accent': colors.HexColor('#FFEB3B'),
        'text': colors.white,
        'text_dark': colors.HexColor('#333333')
    },
    'bmk-tulln': {
        'primary': colors.HexColor('#C62828'),
        'secondary': colors.HexColor('#B71C1C'),
        'accent': colors.HexColor('#FFFFFF'),
        'text': colors.white,
        'text_dark': colors.HexColor('#333333')
    }
}


def load_sample_data():
    """Load sample BMF organization data"""
    data_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'sample-data', 'bmf-organizations.json')

    if not os.path.exists(data_file):
        # Use embedded sample data if file not found
        return get_embedded_sample_data()

    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_embedded_sample_data():
    """Embedded sample data for poster generation"""
    return {
        "organizations": [
            {
                "slug": "mv-st-poelten",
                "name": "Musikverein St. Poelten",
                "city": "St. Poelten",
                "postal_code": "3100"
            },
            {
                "slug": "tk-krems",
                "name": "Trachtenkapelle Krems",
                "city": "Krems an der Donau",
                "postal_code": "3500"
            },
            {
                "slug": "bmk-tulln",
                "name": "Blasmusikkapelle Tulln",
                "city": "Tulln an der Donau",
                "postal_code": "3430"
            }
        ],
        "events": [
            {
                "organization_slug": "mv-st-poelten",
                "slug": "bmf-2026-stpoelten",
                "name": "Bezirksmusikfest 2026 St. Poelten",
                "venue_name": "VAZ St. Poelten",
                "venue_address": "Kelsengasse 9, 3100 St. Poelten",
                "start_date": "2026-06-13T14:00:00",
                "end_date": "2026-06-14T02:00:00"
            },
            {
                "organization_slug": "tk-krems",
                "slug": "bmf-2026-krems",
                "name": "Bezirksmusikfest Krems 2026",
                "venue_name": "Kremser Sandgrube",
                "venue_address": "Dr.-Karl-Dorrek-Strasse, 3500 Krems",
                "start_date": "2026-07-04T15:00:00",
                "end_date": "2026-07-05T01:00:00"
            },
            {
                "organization_slug": "bmk-tulln",
                "slug": "bmf-2026-tulln",
                "name": "BMF Tulln 2026 - Musik am Fluss",
                "venue_name": "Donaubuehne Tulln",
                "venue_address": "Donaulaende, 3430 Tulln",
                "start_date": "2026-08-15T16:00:00",
                "end_date": "2026-08-16T00:00:00"
            }
        ]
    }


def create_event_poster(event, organization, output_dir):
    """Generate a single event poster PDF"""

    # Get color scheme
    scheme = COLOR_SCHEMES.get(organization['slug'], COLOR_SCHEMES['default'])

    # Parse dates
    start_date = datetime.fromisoformat(event['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(event['end_date'].replace('Z', '+00:00')) if event.get('end_date') else None

    # Format date string
    date_str = start_date.strftime('%d. %B %Y')
    time_str = start_date.strftime('%H:%M Uhr')

    # Output filename
    filename = f"poster-{event['slug']}.pdf"
    filepath = os.path.join(output_dir, filename)

    # Create PDF
    c = canvas.Canvas(filepath, pagesize=A3)
    width, height = A3

    # Background gradient (simulated with rectangles)
    steps = 50
    for i in range(steps):
        ratio = i / steps
        r = scheme['primary'].red * (1 - ratio) + scheme['secondary'].red * ratio
        g = scheme['primary'].green * (1 - ratio) + scheme['secondary'].green * ratio
        b = scheme['primary'].blue * (1 - ratio) + scheme['secondary'].blue * ratio
        c.setFillColorRGB(r, g, b)
        c.rect(0, height - (height / steps) * (i + 1), width, height / steps, fill=1, stroke=0)

    # Header - Year badge
    c.setFillColor(scheme['accent'])
    c.roundRect(width/2 - 3*cm, height - 4*cm, 6*cm, 2*cm, 10, fill=1, stroke=0)
    c.setFillColor(scheme['text_dark'])
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height - 3.3*cm, "2026")

    # Main title
    c.setFillColor(scheme['text'])
    c.setFont("Helvetica-Bold", 48)

    # Word wrap title
    title = event['name']
    if len(title) > 25:
        words = title.split()
        mid = len(words) // 2
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
        c.drawCentredString(width/2, height - 8*cm, line1)
        c.drawCentredString(width/2, height - 10*cm, line2)
    else:
        c.drawCentredString(width/2, height - 9*cm, title)

    # Decorative line
    c.setStrokeColor(scheme['accent'])
    c.setLineWidth(3)
    c.line(width/2 - 8*cm, height - 12*cm, width/2 + 8*cm, height - 12*cm)

    # Event details box
    box_y = height - 22*cm
    box_height = 8*cm
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.15))
    c.roundRect(2*cm, box_y, width - 4*cm, box_height, 15, fill=1, stroke=0)

    # Date and time
    c.setFillColor(scheme['text'])
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width/2, box_y + 6*cm, date_str)

    c.setFont("Helvetica", 24)
    c.drawCentredString(width/2, box_y + 4*cm, f"Einlass: {time_str}")

    # Venue
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, box_y + 2*cm, event.get('venue_name', ''))

    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, box_y + 1*cm, event.get('venue_address', ''))

    # Ticket info box
    c.setFillColor(scheme['accent'])
    c.roundRect(width/2 - 6*cm, 6*cm, 12*cm, 3*cm, 10, fill=1, stroke=0)

    c.setFillColor(scheme['text_dark'])
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, 7.8*cm, "TICKETS ONLINE")
    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, 6.8*cm, "event-ticket.at/ticket-shop.html")

    # Organization name
    c.setFillColor(scheme['text'])
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, 3*cm, f"Veranstalter: {organization['name']}")

    # Footer
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, 1.5*cm, "Bezahlung mit BANKpay+ | SEPA Sofortueberweisung")

    c.save()
    print(f"  + Created: {filename}")
    return filepath


def create_tour_poster(events, organizations, output_dir):
    """Generate a tour series poster with all events"""

    filename = "poster-bmf-2026-tour.pdf"
    filepath = os.path.join(output_dir, filename)

    # Create PDF
    c = canvas.Canvas(filepath, pagesize=A3)
    width, height = A3

    # Background
    scheme = COLOR_SCHEMES['default']
    steps = 50
    for i in range(steps):
        ratio = i / steps
        r = scheme['primary'].red * (1 - ratio) + scheme['secondary'].red * ratio
        g = scheme['primary'].green * (1 - ratio) + scheme['secondary'].green * ratio
        b = scheme['primary'].blue * (1 - ratio) + scheme['secondary'].blue * ratio
        c.setFillColorRGB(r, g, b)
        c.rect(0, height - (height / steps) * (i + 1), width, height / steps, fill=1, stroke=0)

    # Header
    c.setFillColor(scheme['accent'])
    c.roundRect(width/2 - 4*cm, height - 4*cm, 8*cm, 2.5*cm, 10, fill=1, stroke=0)
    c.setFillColor(scheme['text_dark'])
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, height - 3.2*cm, "BMF 2026")

    # Main title
    c.setFillColor(scheme['text'])
    c.setFont("Helvetica-Bold", 42)
    c.drawCentredString(width/2, height - 7*cm, "BEZIRKSMUSIKFEST")
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width/2, height - 9*cm, "TOUR 2026")

    # Subtitle
    c.setFont("Helvetica", 18)
    c.drawCentredString(width/2, height - 11*cm, "Niederoesterreich feiert Blasmusik!")

    # Decorative line
    c.setStrokeColor(scheme['accent'])
    c.setLineWidth(3)
    c.line(width/2 - 8*cm, height - 12.5*cm, width/2 + 8*cm, height - 12.5*cm)

    # Event list
    y_pos = height - 15*cm
    event_height = 4*cm

    # Sort events by date
    sorted_events = sorted(events, key=lambda e: e['start_date'])

    for event in sorted_events:
        # Find organization
        org = next((o for o in organizations if o['slug'] == event['organization_slug']), None)
        if not org:
            continue

        # Parse date
        start_date = datetime.fromisoformat(event['start_date'].replace('Z', '+00:00'))

        # Event box
        c.setFillColor(colors.Color(1, 1, 1, alpha=0.1))
        c.roundRect(2*cm, y_pos - event_height + 0.5*cm, width - 4*cm, event_height - 0.5*cm, 10, fill=1, stroke=0)

        # Date badge
        org_scheme = COLOR_SCHEMES.get(org['slug'], COLOR_SCHEMES['default'])
        c.setFillColor(org_scheme['primary'])
        c.roundRect(2.5*cm, y_pos - 2.8*cm, 3*cm, 2.5*cm, 5, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(4*cm, y_pos - 1.5*cm, start_date.strftime('%d'))
        c.setFont("Helvetica", 12)
        c.drawCentredString(4*cm, y_pos - 2.3*cm, start_date.strftime('%b').upper())

        # Event details
        c.setFillColor(scheme['text'])
        c.setFont("Helvetica-Bold", 16)
        c.drawString(6.5*cm, y_pos - 1.3*cm, event['name'][:35])

        c.setFont("Helvetica", 12)
        c.drawString(6.5*cm, y_pos - 2.3*cm, f"{event.get('venue_name', '')} - {org['city']}")

        y_pos -= event_height

    # Ticket info
    c.setFillColor(scheme['accent'])
    c.roundRect(width/2 - 6*cm, 5*cm, 12*cm, 3*cm, 10, fill=1, stroke=0)

    c.setFillColor(scheme['text_dark'])
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, 6.8*cm, "TICKETS FUER ALLE EVENTS")
    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, 5.8*cm, "event-ticket.at")

    # Footer
    c.setFillColor(scheme['text'])
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, 2*cm, "Powered by BANKpay+ | Sichere SEPA-Sofortueberweisungen")

    c.save()
    print(f"  + Created: {filename}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description='Generate BMF 2026 Event Posters')
    parser.add_argument('--event', help='Generate poster for specific event slug')
    parser.add_argument('--tour', action='store_true', help='Generate tour series poster')
    parser.add_argument('--output', default='./posters', help='Output directory')
    args = parser.parse_args()

    print("BMF 2026 Event Poster Generator")
    print("=" * 50)

    # Load data
    data = load_sample_data()
    events = data['events']
    organizations = data['organizations']

    # Create output directory
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    generated = []

    if args.event:
        # Generate single event poster
        event = next((e for e in events if e['slug'] == args.event or e['organization_slug'] == args.event), None)
        if not event:
            print(f"Error: Event '{args.event}' not found")
            sys.exit(1)

        org = next((o for o in organizations if o['slug'] == event['organization_slug']), None)
        if not org:
            print(f"Error: Organization for event not found")
            sys.exit(1)

        print(f"\nGenerating poster for: {event['name']}")
        filepath = create_event_poster(event, org, output_dir)
        generated.append(filepath)

    elif args.tour:
        # Generate tour poster
        print("\nGenerating tour series poster...")
        filepath = create_tour_poster(events, organizations, output_dir)
        generated.append(filepath)

    else:
        # Generate all posters
        print("\nGenerating all event posters...")

        for event in events:
            org = next((o for o in organizations if o['slug'] == event['organization_slug']), None)
            if org:
                filepath = create_event_poster(event, org, output_dir)
                generated.append(filepath)

        # Also generate tour poster
        print("\nGenerating tour series poster...")
        filepath = create_tour_poster(events, organizations, output_dir)
        generated.append(filepath)

    print("\n" + "=" * 50)
    print(f"Generated {len(generated)} poster(s)")
    print(f"Location: {output_dir}")

    return generated


if __name__ == '__main__':
    main()
