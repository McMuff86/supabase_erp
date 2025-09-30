## SupaERP Agents

Zweck: Lebendes Dokument für Vision, Module, Datenmodell, Sicherheitsregeln (RLS), Entwicklungsrichtlinien und Roadmap des ERP-Systems auf Supabase.

### Konzept in Kürze
- **Ziel**: Ein modernes, modulares ERP (CRM, Projekte, Lager, Daten/Belege) mit intuitiver Bedienung und schönem UI.
- **Plattform**: Supabase (Postgres, Auth, Storage, Edge Functions). Strikte RLS, Multi-Tenancy, API-freundliche Views und RPCs.
- **Qualität**: Klare Namenskonventionen, nachvollziehbare Migrationen, testbare Businesslogik, Auditierbarkeit.

### Module (erste Iteration)
- **Kundenverwaltung (CRM)**: Leads, Kontakte, Firmen, Deals/Pipelines, Angebote, Aktivitäten.
- **Projektverwaltung**: Projekte, Aufgaben, Zeitbuchungen, Ausgaben, Dokumente.
- **Lagerverwaltung**: Produkte/Varianten, Bestände, Lagerorte, Warenein-/ausgänge, Chargen/Serien.
- **Daten-/Belegverwaltung**: Angebote, Aufträge, Rechnungen, Zahlungen, Lieferscheine, Rücksendungen.
- **Stammdaten & Einstellungen**: Organisationen (Mandanten), Benutzer/Rollen, Steuern, Währungen, Einheiten.

### Architekturbasis
- **Postgres Schema**: `public` für App-Tabellen; Nutzung von `auth.users` (Supabase). Optionale Hilfsschemata (`app`, `audit`).
- **Multi-Tenancy**: `organization_id` in allen fachlichen Tabellen, RLS erzwingt Isolation.
- **IDs & Zeit**: `uuid` Primärschlüssel, `created_at`/`updated_at` als `timestamptz` (UTC), Trigger auf `updated_at`.
- **Sicherheit**: RLS standardmäßig an, fein-granulare Policies (Owner-, Member-, Systemrollen).
- **APIs**: Materialized Views/Views für Lesefälle, RPCs für komplexe Transaktionen.
- **Suche**: `pg_trgm` für Volltext-/Fuzzy-Suche, Indizes pro häufigen Filterfeldern.

---

### Entitätenübersicht (Core)
- **Mandant & Nutzer**: `organizations`, `organization_members`, `profiles` (Verknüpfung zu `auth.users`).
- **CRM**: `customers`, `contacts`, `addresses`, `activities`, `pipelines`, `deals`.
- **Produkte & Lager**: `products`, `product_variants`, `units`, `inventory_locations`, `stock_items`, `stock_movements`, `batches`, `serial_numbers`.
- **Beschaffung & Verkauf**: `suppliers`, `purchase_orders`, `purchase_order_items`, `sales_orders`, `sales_order_items`, `shipments`, `returns`.
- **Projekte**: `projects`, `project_tasks`, `time_entries`, `expenses`.
- **Belege & Finanzen (Start)**: `quotes`, `invoices`, `invoice_items`, `payments`, `payment_methods`.
- **System**: `attachments`, `tags`, `comments`, `audit_logs`, `webhooks`, `integrations`, `notifications`.

Hinweis: Nicht alle Tabellen werden sofort angelegt; wir beginnen iterativ mit dem Kern.

---

### Datenmodell – erste Tabellen (DDL Vorschlag)
Die folgenden DDLs sind Startpunkte; Details (Constraints, Indizes, Policies) werden iterativ ergänzt.

```sql
-- Extension prerequisites (once per database)
create extension if not exists pgcrypto;          -- for gen_random_uuid()
create extension if not exists pg_trgm;           -- for search

-- Timestamps trigger helper
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end; $$;

-- Organizations (tenants)
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger organizations_set_updated
before update on public.organizations
for each row execute function set_updated_at();

-- Application profiles linked to auth.users
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger profiles_set_updated
before update on public.profiles
for each row execute function set_updated_at();

-- Memberships connecting users to organizations with roles
create table if not exists public.organization_members (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  role text not null check (role in ('owner','admin','member','viewer')),
  created_at timestamptz not null default now(),
  unique (organization_id, user_id)
);

-- Customers & Contacts
create table if not exists public.customers (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  name text not null,
  vat_number text,
  default_billing_address_id uuid,
  default_shipping_address_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger customers_set_updated
before update on public.customers
for each row execute function set_updated_at();

create table if not exists public.addresses (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  customer_id uuid references public.customers (id) on delete set null,
  name text,
  line1 text not null,
  line2 text,
  postal_code text not null,
  city text not null,
  state text,
  country_code char(2) not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger addresses_set_updated
before update on public.addresses
for each row execute function set_updated_at();

create table if not exists public.contacts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  customer_id uuid references public.customers (id) on delete cascade,
  first_name text,
  last_name text,
  email text,
  phone text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger contacts_set_updated
before update on public.contacts
for each row execute function set_updated_at();

-- Products & Inventory
create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  name text not null,
  sku text unique,
  description text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger products_set_updated
before update on public.products
for each row execute function set_updated_at();

create table if not exists public.product_variants (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  product_id uuid not null references public.products (id) on delete cascade,
  variant_sku text unique,
  attributes jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger product_variants_set_updated
before update on public.product_variants
for each row execute function set_updated_at();

create table if not exists public.inventory_locations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  code text not null,
  name text not null,
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, code)
);
create trigger inventory_locations_set_updated
before update on public.inventory_locations
for each row execute function set_updated_at();

create table if not exists public.stock_items (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  product_variant_id uuid not null references public.product_variants (id) on delete cascade,
  location_id uuid not null references public.inventory_locations (id) on delete cascade,
  quantity numeric not null default 0,
  reserved numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, product_variant_id, location_id)
);
create trigger stock_items_set_updated
before update on public.stock_items
for each row execute function set_updated_at();

create table if not exists public.stock_movements (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  product_variant_id uuid not null references public.product_variants (id) on delete cascade,
  from_location_id uuid references public.inventory_locations (id) on delete set null,
  to_location_id uuid references public.inventory_locations (id) on delete set null,
  quantity numeric not null,
  movement_type text not null check (movement_type in ('inbound','outbound','transfer','adjustment')),
  reference_type text,
  reference_id uuid,
  created_by uuid references public.profiles (id) on delete set null,
  created_at timestamptz not null default now()
);

-- Projects & Tasks
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  name text not null,
  customer_id uuid references public.customers (id) on delete set null,
  status text not null default 'active' check (status in ('active','on_hold','completed','cancelled')),
  start_date date,
  end_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger projects_set_updated
before update on public.projects
for each row execute function set_updated_at();

create table if not exists public.project_tasks (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  title text not null,
  description text,
  status text not null default 'todo' check (status in ('todo','in_progress','done','blocked')),
  assignee_id uuid references public.profiles (id) on delete set null,
  due_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger project_tasks_set_updated
before update on public.project_tasks
for each row execute function set_updated_at();

create table if not exists public.time_entries (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  project_id uuid references public.projects (id) on delete cascade,
  task_id uuid references public.project_tasks (id) on delete set null,
  user_id uuid not null references public.profiles (id) on delete set null,
  started_at timestamptz not null,
  ended_at timestamptz,
  duration_minutes integer generated always as (
    case when ended_at is not null then extract(epoch from (ended_at - started_at))::int / 60 else null end
  ) stored,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger time_entries_set_updated
before update on public.time_entries
for each row execute function set_updated_at();
```

RLS wird nach Anlage der Tabellen aktiviert. Beispiel (Konzept):

```sql
alter table public.organizations enable row level security;
alter table public.customers enable row level security;
-- ... für alle fachlichen Tabellen

-- Policy-Idee: JWT enthält claim org_id; Zugriff nur innerhalb der Organisation
create policy "org members can read"
on public.customers
for select
using (
  (auth.jwt() ->> 'org_id') is not null and
  organization_id::text = auth.jwt() ->> 'org_id'
);

create policy "org members can modify"
on public.customers
for all
using (
  (auth.jwt() ->> 'org_id') is not null and
  organization_id::text = auth.jwt() ->> 'org_id'
)
with check (
  organization_id::text = auth.jwt() ->> 'org_id'
);
```

Hinweis: Rollen/Claims-Strategie wird pro Tabelle verfeinert (Owner/Admin/Member/Viewer, Feature-Flags).

---

### Konventionen & Standards
- **Benennung**: `snake_case` Tabellen/Spalten; FK `xxx_id`; Zeit mit `*_at`.
- **IDs**: `uuid` über `gen_random_uuid()`; Domain-Keys (z. B. `sku`) zusätzlich unique.
- **Zeit & Zone**: `timestamptz` UTC; Anzeigen lokalisiert im UI.
- **Soft-Delete**: Optional via `deleted_at timestamptz` (später, falls nötig).
- **Indizes**: Für alle FKs + häufige Filter; `gin` für `jsonb`, `gist`/`btree` je nach Bedarf.
- **Migrationen**: Ein Skript pro Änderung; reversible; explizite Versionierung; Seed-Daten minimal.
- **Auditing**: `audit_logs` für relevante Ereignisse; Trigger-basiert oder via RPC.

---

### Workflows (End-to-End, grob)
1. Lead → Kunde → Angebot → Auftrag → Lieferung → Rechnung → Zahlung.
2. Projektstart → Aufgabenplanung → Zeit/Material buchen → Abnahme → Abrechnung.
3. Beschaffung: Bedarf → Bestellung → Wareneingang → Bestandserhöhung.

Diese Flüsse definieren spätere Constraints, Statusmaschinen und Automatisierungen.

---

### UI/UX Leitlinien (kurz)
- Klare Navigationshierarchie nach Modulen; konsistente Listen/Detail-Layouts.
- Schnelle Suche/Filterung, Tastaturkürzel, Tabellen mit Spaltenauswahl und Speichern von Views.
- Inline-Validierung, verständliche Fehlermeldungen, Undo/Redo wo möglich.

---

### Agents & Verantwortlichkeiten
- **DB Architect Agent**: Datenmodellierung, Migrationen, Indizes, Performance.
- **Security/RLS Agent**: Policies, Rollen/Claims, Zugriffstests.
- **Domain Agent CRM/Projects/Inventory**: Fachlogik, Statusmaschinen, Integrationen.
- **API/Edge Agent**: RPCs, Webhooks, Integrationspunkte.
- **Docs Agent**: Hält dieses Dokument aktuell (Änderungslog), ERDs.
- **UI Agent**: UI-Flows, Komponentenbibliothek, Zugänglichkeit.

Arbeitsweise: Kleine, nachvollziehbare PRs, jede Änderung ergänzt Changelog und ggf. Roadmap-Status.

---

### Offene Punkte (Backlog, Auswahl)
- RLS-Detailierung je Tabelle (bes. `stock_movements`, `projects`).
- Statusmaschinen je Belegtyp (Quote/Order/Invoice/Shipment).
- Steuern, Mehrwährungen, Einheitenkonvertierung.
- Chargen/Seriennummern-Handling und Rückverfolgbarkeit.
- Volltextsuche über Kunden/Kontakte/Produkte.

---

### Roadmap (Kurz)
- [ ] Kern-Tabellen anlegen (oben) und RLS aktivieren
- [ ] Seed-Skripte für Demo-Daten (Org, User, Kunden, Produkte)
- [ ] Views/RPCs für häufige Anwendungsfälle (z. B. Projektübersicht)
- [ ] Indizes & Leistungscheck mit realistischen Datenmengen
- [ ] Erste UI-Listen/Details (Kunden, Produkte, Projekte)
- [ ] End-to-End-Durchstich: Angebot → Auftrag → Lieferung → Rechnung

---

### Changelog
- 2025-09-30: Initiale Struktur angelegt (Vision, Module, Kern-DDL, RLS-Konzept, Roadmap).


