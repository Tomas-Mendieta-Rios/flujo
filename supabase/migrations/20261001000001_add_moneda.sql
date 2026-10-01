-- Agrega moneda a cajas (ARS o USD)
alter table cajas
  add column moneda text not null default 'ARS'
  check (moneda in ('ARS', 'USD'));
