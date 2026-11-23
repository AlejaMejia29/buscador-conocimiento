-- Prueba local de las políticas RLS de esquema.sql e historial.sql, sin Supabase.
-- Se ejecutó en PostgreSQL 16 con pgvector. El bloque inicial imita lo que Supabase ya trae:
-- roles anon/authenticated, esquema auth con auth.uid() y privilegios por defecto.
-- Uso:
--   createdb prueba && psql -d prueba -c "alter database prueba set search_path = public, extensions"
--   psql -d prueba -f supabase/prueba_rls_local.sql   (como superusuario, en una base vacía)
-- NO ejecutar en el proyecto real de Supabase.

do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
end $$;
create schema if not exists auth;
create schema if not exists extensions;
create table if not exists auth.users (id uuid primary key, email text);
create or replace function auth.uid() returns uuid language sql stable
  as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema auth, extensions, public to authenticated, anon;
grant execute on function auth.uid() to authenticated, anon;
alter default privileges in schema public grant all on tables to anon, authenticated;
alter default privileges in schema public grant all on functions to anon, authenticated;

\ir esquema.sql
\ir historial.sql

\set ON_ERROR_STOP 0
insert into auth.users values ('aaaaaaaa-0000-0000-0000-000000000001','joan@x.co'),('bbbbbbbb-0000-0000-0000-000000000002','aleja@x.co'),('cccccccc-0000-0000-0000-000000000003','otro@x.co');
insert into clase08_fragmentos (owner_id,corpus_id,chunk_id,content,metadata,configuracion,embedding)
select 'aaaaaaaa-0000-0000-0000-000000000001','c1','f'||i,'texto '||i,'{}','{"modelo":"m","revision":"r"}', array_fill(i::real, array[384])::vector from generate_series(1,3) i;
-- autorizar a aleja (como en el paso 4)
insert into buscador_corpus_lectores (owner_id, corpus_id, usuario_id)
select p.id, 'c1', l.id from auth.users p, auth.users l where p.email='joan@x.co' and l.email='aleja@x.co';

set role authenticated;
select set_config('request.jwt.claim.sub','bbbbbbbb-0000-0000-0000-000000000002',false);
\echo '--- aleja (autorizada): busqueda debe dar 3'
select count(*) from buscador_buscar_fragmentos(array_fill(1::real, array[384])::vector,'aaaaaaaa-0000-0000-0000-000000000001','c1','m','r',10);
\echo '--- aleja intenta insertar en el corpus de joan: debe fallar'
insert into clase08_fragmentos (owner_id,corpus_id,chunk_id,content,embedding) values ('aaaaaaaa-0000-0000-0000-000000000001','c1','x','x',array_fill(1::real, array[384])::vector);
\echo '--- aleja se autoriza a si misma a otro: debe fallar'
insert into buscador_corpus_lectores values ('aaaaaaaa-0000-0000-0000-000000000001','c1','cccccccc-0000-0000-0000-000000000003');
\echo '--- aleja crea 2 conversaciones y mensajes'
insert into buscador_conversaciones (id, titulo) values ('11111111-1111-1111-1111-111111111111','A1'),('11111111-1111-1111-1111-111111111112','A2');
insert into buscador_mensajes (conversacion_id, rol, contenido) values ('11111111-1111-1111-1111-111111111111','usuario','hola'),('11111111-1111-1111-1111-111111111111','asistente','resp');
\echo '--- aleja intenta crear conversacion a nombre de otro: debe fallar'
insert into buscador_conversaciones (usuario_id, titulo) values ('cccccccc-0000-0000-0000-000000000003','falsa');

select set_config('request.jwt.claim.sub','cccccccc-0000-0000-0000-000000000003',false);
\echo '--- otro (no autorizado): busqueda debe dar 0'
select count(*) from buscador_buscar_fragmentos(array_fill(1::real, array[384])::vector,'aaaaaaaa-0000-0000-0000-000000000001','c1','m','r',10);
\echo '--- otro lee conversaciones/mensajes de aleja conociendo el uuid: debe dar 0 y 0'
select count(*) from buscador_conversaciones where id='11111111-1111-1111-1111-111111111111';
select count(*) from buscador_mensajes where conversacion_id='11111111-1111-1111-1111-111111111111';
\echo '--- otro escribe en la conversacion de aleja: debe fallar'
insert into buscador_mensajes (conversacion_id, rol, contenido) values ('11111111-1111-1111-1111-111111111111','usuario','intruso');
\echo '--- otro renombra la conversacion de aleja: debe actualizar 0'
update buscador_conversaciones set titulo='hack' where id='11111111-1111-1111-1111-111111111111';
\echo '--- otro borra mensajes de aleja: debe borrar 0 o fallar'
delete from buscador_mensajes;

select set_config('request.jwt.claim.sub','bbbbbbbb-0000-0000-0000-000000000002',false);
\echo '--- aleja ve sus 2 conversaciones y 2 mensajes, titulo intacto'
select titulo from buscador_conversaciones order by titulo;
select count(*) from buscador_mensajes;
reset role;
set role anon;
\echo '--- anon no puede leer nada'
select count(*) from buscador_conversaciones;
select count(*) from buscador_buscar_fragmentos(array_fill(1::real, array[384])::vector,'aaaaaaaa-0000-0000-0000-000000000001','c1','m','r',10);
