-- ── CAJAS ─────────────────────────────────────────────────────────────────────
create table cajas (
  id     bigserial primary key,
  nombre text    not null,
  activa boolean not null default true
);

-- ── RUBROS INGRESOS (3 niveles) ───────────────────────────────────────────────
create table rubros_ingresos (
  id     bigserial primary key,
  nombre text not null
);

create table subrubros_ingresos (
  id       bigserial primary key,
  nombre   text   not null,
  rubro_id bigint not null references rubros_ingresos(id) on delete cascade
);

create table items_ingresos (
  id          bigserial primary key,
  nombre      text    not null,
  subrubro_id bigint  not null references subrubros_ingresos(id) on delete cascade,
  activo      boolean not null default true
);

-- ── RUBROS EGRESOS (3 niveles) ────────────────────────────────────────────────
create table rubros_egresos (
  id     bigserial primary key,
  nombre text not null
);

create table subrubros_egresos (
  id       bigserial primary key,
  nombre   text   not null,
  rubro_id bigint not null references rubros_egresos(id) on delete cascade
);

create table items_egresos (
  id          bigserial primary key,
  nombre      text    not null,
  subrubro_id bigint  not null references subrubros_egresos(id) on delete cascade,
  activo      boolean not null default true
);

-- ── INGRESOS ──────────────────────────────────────────────────────────────────
create table ingresos (
  id          bigserial primary key,
  fecha       date          not null,
  rubro_id    bigint        references rubros_ingresos(id),
  subrubro_id bigint        references subrubros_ingresos(id),
  item_id     bigint        references items_ingresos(id),
  caja_id     bigint        references cajas(id),
  monto       numeric(12,2) not null,
  descripcion text,
  created_at  timestamptz   not null default now()
);

create index ingresos_fecha_idx   on ingresos(fecha);
create index ingresos_caja_idx    on ingresos(caja_id);

-- ── EGRESOS ───────────────────────────────────────────────────────────────────
create table egresos (
  id          bigserial primary key,
  fecha       date          not null,
  rubro_id    bigint        references rubros_egresos(id),
  subrubro_id bigint        references subrubros_egresos(id),
  item_id     bigint        references items_egresos(id),
  caja_id     bigint        references cajas(id),
  monto       numeric(12,2) not null,
  descripcion text,
  created_at  timestamptz   not null default now()
);

create index egresos_fecha_idx on egresos(fecha);
create index egresos_caja_idx  on egresos(caja_id);

-- ── TRANSFERENCIAS ────────────────────────────────────────────────────────────
create table transferencias (
  id         bigserial primary key,
  fecha      date          not null,
  origen_id  bigint        not null references cajas(id),
  destino_id bigint        not null references cajas(id),
  monto      numeric(12,2) not null,
  concepto   text,
  created_at timestamptz   not null default now()
);

create index transferencias_fecha_idx on transferencias(fecha);

-- ── AJUSTES DE CAJA ───────────────────────────────────────────────────────────
-- tipo: 'inicial' (saldo de arranque, uno por caja) | 'ajuste' (corrección libre)
create table ajustes (
  id         bigserial primary key,
  caja_id    bigint        not null references cajas(id),
  fecha      date          not null,
  monto      numeric(12,2) not null,
  nota       text,
  tipo       text          not null default 'ajuste'
                           check (tipo in ('inicial', 'ajuste')),
  created_at timestamptz   not null default now()
);
