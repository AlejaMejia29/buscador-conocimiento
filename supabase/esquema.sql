-- Buscador de conocimiento · Base vectorial en Supabase (pgvector)
-- Ejecutar una vez en Supabase → SQL Editor. Crea la tabla, la seguridad por filas (RLS)
-- y la función de búsqueda que usa el notebook final.
-- Corresponde a la configuración de la Clase 08 (tabla clase08_fragmentos).

create extension if not exists vector with schema extensions;

create table if not exists public.clase08_fragmentos (
  owner_id      uuid        not null default auth.uid() references auth.users (id) on delete cascade,
  corpus_id     text        not null,
  chunk_id      text        not null,
  content       text        not null,
  metadata      jsonb       not null default '{}'::jsonb,
  configuracion jsonb       not null default '{}'::jsonb,
  embedding     vector(384) not null,
  creado_en     timestamptz not null default now(),
  primary key (owner_id, corpus_id, chunk_id)
);

-- Cada usuario de Supabase Auth solo ve y modifica sus propias filas.
alter table public.clase08_fragmentos enable row level security;

drop policy if exists "leer propias filas" on public.clase08_fragmentos;
create policy "leer propias filas" on public.clase08_fragmentos
  for select to authenticated using (owner_id = auth.uid());

drop policy if exists "insertar propias filas" on public.clase08_fragmentos;
create policy "insertar propias filas" on public.clase08_fragmentos
  for insert to authenticated with check (owner_id = auth.uid());

drop policy if exists "actualizar propias filas" on public.clase08_fragmentos;
create policy "actualizar propias filas" on public.clase08_fragmentos
  for update to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- Búsqueda semántica: similitud coseno (1 - distancia) entre la pregunta y los fragmentos
-- del mismo propietario, corpus, modelo y revisión de embeddings.
create or replace function public.clase08_buscar_fragmentos(
  query_embedding vector(384),
  p_corpus_id     text,
  p_modelo        text,
  p_revision      text,
  match_count     int default 3
)
returns table (chunk_id text, content text, metadata jsonb, similitud double precision)
language sql stable security invoker
set search_path = public, extensions
as $$
  select f.chunk_id, f.content, f.metadata,
         1 - (f.embedding <=> query_embedding) as similitud
  from public.clase08_fragmentos f
  where f.owner_id = auth.uid()
    and f.corpus_id = p_corpus_id
    and f.configuracion ->> 'modelo' = p_modelo
    and f.configuracion ->> 'revision' = p_revision
  order by f.embedding <=> query_embedding, f.chunk_id
  limit least(greatest(match_count, 1), 10);
$$;

grant execute on function public.clase08_buscar_fragmentos(vector, text, text, text, int) to authenticated;
