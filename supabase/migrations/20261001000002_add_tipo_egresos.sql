alter table egresos
  add column tipo text not null default 'gasto'
  check (tipo in ('gasto', 'inversion'));
