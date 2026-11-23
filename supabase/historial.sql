-- Buscador de conocimiento · Entrega final (Clase 12)
-- Ejecutar una vez en Supabase → SQL Editor, DESPUÉS de supabase/esquema.sql.
-- 1) Lectores autorizados del corpus: el corpus sigue perteneciendo a quien lo cargó,
--    y su propietario autoriza explícitamente a otras cuentas a leerlo.
-- 2) Función de búsqueda para la aplicación: la autorización la decide RLS.
-- 3) Historial de conversaciones y mensajes, privado para cada usuario.
-- No usa claves administrativas desde la aplicación ni desactiva RLS.

-- ---------------------------------------------------------------------------
-- 1. Lectores autorizados del corpus
-- ---------------------------------------------------------------------------
create table if not exists public.buscador_corpus_lectores (
  owner_id   uuid not null references auth.users (id) on delete cascade,
  corpus_id  text not null,
  usuario_id uuid not null references auth.users (id) on delete cascade,
  creado_en  timestamptz not null default now(),
  primary key (owner_id, corpus_id, usuario_id)
);

alter table public.buscador_corpus_lectores enable row level security;

-- Cada usuario solo ve sus propias autorizaciones. No hay política de inserción:
-- las autorizaciones se agregan desde el SQL Editor (paso 4 de este archivo).
drop policy if exists "ver mis autorizaciones" on public.buscador_corpus_lectores;
create policy "ver mis autorizaciones" on public.buscador_corpus_lectores
  for select to authenticated using (usuario_id = auth.uid());

-- Lectura adicional del corpus: además de su propietario (política de esquema.sql),
-- pueden leer las cuentas autorizadas para ese propietario y ese corpus.
drop policy if exists "leer corpus autorizado" on public.clase08_fragmentos;
create policy "leer corpus autorizado" on public.clase08_fragmentos
  for select to authenticated using (
    exists (
      select 1 from public.buscador_corpus_lectores l
      where l.owner_id = clase08_fragmentos.owner_id
        and l.corpus_id = clase08_fragmentos.corpus_id
        and l.usuario_id = auth.uid()
    )
  );

-- ---------------------------------------------------------------------------
-- 2. Búsqueda semántica para la aplicación
-- ---------------------------------------------------------------------------
-- Igual que clase08_buscar_fragmentos, pero sin "owner_id = auth.uid()": recibe el
-- propietario del corpus y deja que RLS decida si quien pregunta puede leerlo.
-- Es security invoker: se ejecuta con los permisos del usuario que inició sesión.
create or replace function public.buscador_buscar_fragmentos(
  query_embedding vector(384),
  p_owner_id      uuid,
  p_corpus_id     text,
  p_modelo        text,
  p_revision      text,
  match_count     int default 10
)
returns table (chunk_id text, content text, metadata jsonb, similitud double precision)
language sql stable security invoker
set search_path = public, extensions
as $$
  select f.chunk_id, f.content, f.metadata,
         1 - (f.embedding <=> query_embedding) as similitud
  from public.clase08_fragmentos f
  where f.owner_id = p_owner_id
    and f.corpus_id = p_corpus_id
    and f.configuracion ->> 'modelo' = p_modelo
    and f.configuracion ->> 'revision' = p_revision
  order by f.embedding <=> query_embedding, f.chunk_id
  limit least(greatest(match_count, 1), 10);
$$;

revoke execute on function public.buscador_buscar_fragmentos(vector, uuid, text, text, text, int) from public, anon;
grant execute on function public.buscador_buscar_fragmentos(vector, uuid, text, text, text, int) to authenticated;

-- ---------------------------------------------------------------------------
-- 3. Historial: conversaciones y mensajes
-- ---------------------------------------------------------------------------
create table if not exists public.buscador_conversaciones (
  id         uuid primary key default gen_random_uuid(),
  usuario_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  titulo     text not null check (char_length(titulo) between 1 and 120),
  creada_en  timestamptz not null default now()
);
create index if not exists buscador_conversaciones_usuario
  on public.buscador_conversaciones (usuario_id, creada_en desc);

create table if not exists public.buscador_mensajes (
  id              bigint generated always as identity primary key,
  conversacion_id uuid not null references public.buscador_conversaciones (id) on delete cascade,
  usuario_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  rol             text not null check (rol in ('usuario', 'asistente')),
  contenido       text not null check (char_length(contenido) between 1 and 6000),
  estado          text,
  fuentes         jsonb not null default '[]'::jsonb,
  creado_en       timestamptz not null default now()
);
create index if not exists buscador_mensajes_conversacion
  on public.buscador_mensajes (conversacion_id, id);

alter table public.buscador_conversaciones enable row level security;
alter table public.buscador_mensajes enable row level security;

-- Conversaciones: solo su propietario las ve, crea o renombra.
drop policy if exists "ver mis conversaciones" on public.buscador_conversaciones;
create policy "ver mis conversaciones" on public.buscador_conversaciones
  for select to authenticated using (usuario_id = auth.uid());

drop policy if exists "crear mis conversaciones" on public.buscador_conversaciones;
create policy "crear mis conversaciones" on public.buscador_conversaciones
  for insert to authenticated with check (usuario_id = auth.uid());

drop policy if exists "renombrar mis conversaciones" on public.buscador_conversaciones;
create policy "renombrar mis conversaciones" on public.buscador_conversaciones
  for update to authenticated using (usuario_id = auth.uid()) with check (usuario_id = auth.uid());

-- Mensajes: solo se leen o insertan dentro de una conversación propia.
-- Conocer el UUID de una conversación ajena no concede acceso.
drop policy if exists "ver mensajes de mis conversaciones" on public.buscador_mensajes;
create policy "ver mensajes de mis conversaciones" on public.buscador_mensajes
  for select to authenticated using (
    usuario_id = auth.uid()
    and exists (select 1 from public.buscador_conversaciones c
                where c.id = buscador_mensajes.conversacion_id and c.usuario_id = auth.uid())
  );

drop policy if exists "insertar mensajes en mis conversaciones" on public.buscador_mensajes;
create policy "insertar mensajes en mis conversaciones" on public.buscador_mensajes
  for insert to authenticated with check (
    usuario_id = auth.uid()
    and exists (select 1 from public.buscador_conversaciones c
                where c.id = buscador_mensajes.conversacion_id and c.usuario_id = auth.uid())
  );

-- Sin políticas de update/delete en mensajes: el historial no se edita desde la aplicación.
-- Supabase concede por defecto todos los privilegios a anon y authenticated en tablas nuevas:
-- los retiramos y dejamos solo lo que usa la aplicación (RLS filtra además cada fila).
revoke all on public.buscador_conversaciones, public.buscador_mensajes, public.buscador_corpus_lectores
  from anon, authenticated;
grant select, insert, update on public.buscador_conversaciones to authenticated;
grant select, insert on public.buscador_mensajes to authenticated;
grant select on public.buscador_corpus_lectores to authenticated;

-- ---------------------------------------------------------------------------
-- 4. Autorizar a otra cuenta a leer el corpus (ejecutar aparte, una vez por cuenta)
-- ---------------------------------------------------------------------------
-- Reemplazar los correos y el corpus_id. El primer correo es el de la cuenta que cargó
-- el corpus con el notebook; el segundo, el de la cuenta que se autoriza.
--
-- insert into public.buscador_corpus_lectores (owner_id, corpus_id, usuario_id)
-- select p.id, 'buscador_conocimiento-29dccc23ac01', l.id
-- from auth.users p, auth.users l
-- where p.email = 'propietario@correo.com' and l.email = 'lector@correo.com'
-- on conflict do nothing;
--
-- Para conocer el owner_id que va en CORPUS_PROPIETARIO_ID del .env:
-- select distinct owner_id, corpus_id, count(*) from public.clase08_fragmentos group by 1, 2;
