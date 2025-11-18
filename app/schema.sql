-- Event Ticket Multi-Organization Database Schema
-- For BMF/Bezirksmusikfest 2026 Ticket Sales
-- Created: 2025-11-18

-- Drop existing tables if they exist (for development)
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS tickets CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Organizations table (music associations planning BMF 2026)
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Contact information
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    website VARCHAR(255),

    -- Address
    street_address VARCHAR(255),
    postal_code VARCHAR(20),
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'AT',

    -- Payment configuration (BANKpay+ / SEPA)
    iban VARCHAR(34) NOT NULL,
    bic VARCHAR(11),
    recipient_name VARCHAR(255) NOT NULL,
    payment_reference_prefix VARCHAR(50),

    -- Branding
    logo_url VARCHAR(500),
    primary_color VARCHAR(7) DEFAULT '#1976D2',
    secondary_color VARCHAR(7) DEFAULT '#424242',

    -- Status and metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events table (BMF 2026 events and sub-events)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    slug VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Event details
    event_type VARCHAR(50) DEFAULT 'festival', -- festival, concert, parade, etc.
    venue_name VARCHAR(255),
    venue_address VARCHAR(500),

    -- Timing
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    doors_open TIMESTAMP,

    -- Capacity
    max_capacity INTEGER,
    current_sold INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_sold_out BOOLEAN DEFAULT false,
    sales_start TIMESTAMP,
    sales_end TIMESTAMP,

    -- Metadata
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(organization_id, slug)
);

-- Ticket types for events
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- e.g., "Tageskarte", "Festzelt VIP", "Jugendkarte"
    description TEXT,

    -- Pricing
    price DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',

    -- Availability
    quantity_total INTEGER,
    quantity_sold INTEGER DEFAULT 0,
    quantity_reserved INTEGER DEFAULT 0,

    -- Constraints
    max_per_order INTEGER DEFAULT 10,
    min_per_order INTEGER DEFAULT 1,

    -- Validity
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,

    -- Status
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders (purchases)
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    order_number VARCHAR(50) UNIQUE NOT NULL,

    -- Customer information
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50),
    customer_address TEXT,

    -- Payment
    total_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    payment_status VARCHAR(50) DEFAULT 'pending', -- pending, paid, failed, refunded
    payment_reference VARCHAR(255),
    payment_provider VARCHAR(50) DEFAULT 'sepa_digital',
    transaction_id VARCHAR(255),

    -- SEPA.digital specific
    sepa_uuid VARCHAR(100),
    sepa_short_url VARCHAR(255),
    sepa_qr_code_url VARCHAR(500),

    -- Status
    status VARCHAR(50) DEFAULT 'created', -- created, confirmed, cancelled

    -- Metadata
    ip_address VARCHAR(45),
    user_agent TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP
);

-- Order items (individual tickets in an order)
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    event_id INTEGER NOT NULL REFERENCES events(id),

    -- Ticket details at time of purchase
    ticket_name VARCHAR(100) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    subtotal DECIMAL(10, 2) NOT NULL,

    -- Ticket codes for entry
    ticket_codes TEXT[], -- Array of unique codes for each ticket

    -- Status
    is_redeemed BOOLEAN DEFAULT false,
    redeemed_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table for organization admins
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'admin', -- admin, manager, staff
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX idx_events_organization ON events(organization_id);
CREATE INDEX idx_events_slug ON events(slug);
CREATE INDEX idx_events_start_date ON events(start_date);
CREATE INDEX idx_tickets_event ON tickets(event_id);
CREATE INDEX idx_orders_organization ON orders(organization_id);
CREATE INDEX idx_orders_status ON orders(payment_status);
CREATE INDEX idx_orders_customer_email ON orders(customer_email);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_ticket ON order_items(ticket_id);
CREATE INDEX idx_organizations_slug ON organizations(slug);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample BMF organization
INSERT INTO organizations (slug, name, description, email, phone, street_address, postal_code, city, iban, bic, recipient_name, payment_reference_prefix)
VALUES
    ('bmf-demo', 'Bezirksmusikfest Demo', 'Demo-Organisation für BMF 2026 Tickets', 'info@bmf-demo.at', '+43 1234 56789', 'Hauptstraße 1', '3100', 'St. Pölten', 'AT611904300234573201', 'BKAUATWW', 'BMF Demo Organisation', 'BMF2026');

-- Insert sample event
INSERT INTO events (organization_id, slug, name, description, event_type, venue_name, venue_address, start_date, end_date, max_capacity, sales_start, sales_end)
VALUES
    (1, 'bmf-2026-hauptfest', 'Bezirksmusikfest 2026 - Hauptfest', 'Das große Bezirksmusikfest 2026 mit Festzelt, Konzerten und Umzug', 'festival', 'Festgelände', 'Festplatz 1, 3100 St. Pölten', '2026-06-20 14:00:00', '2026-06-21 02:00:00', 5000, '2025-12-01 00:00:00', '2026-06-19 23:59:59');

-- Insert sample tickets
INSERT INTO tickets (event_id, name, description, price, quantity_total, max_per_order, sort_order)
VALUES
    (1, 'Tageskarte Erwachsene', 'Eintritt zum Festgelände für einen Tag', 15.00, 3000, 10, 1),
    (1, 'Tageskarte Jugend (14-18)', 'Ermäßigter Eintritt für Jugendliche', 8.00, 1000, 10, 2),
    (1, 'VIP Ticket', 'Zugang zum VIP-Bereich inkl. Getränke', 50.00, 200, 4, 3),
    (1, 'Familienkarte (2+2)', 'Eintritt für 2 Erwachsene und 2 Kinder', 35.00, 500, 2, 4);

COMMENT ON TABLE organizations IS 'Organizations hosting BMF/Bezirksmusikfest events and selling tickets via BANKpay+';
COMMENT ON TABLE events IS 'Events organized by music associations (concerts, festivals, parades)';
COMMENT ON TABLE tickets IS 'Ticket types available for each event with pricing and availability';
COMMENT ON TABLE orders IS 'Customer orders with payment tracking via SEPA.digital/BANKpay+';
COMMENT ON TABLE order_items IS 'Individual tickets within an order';
