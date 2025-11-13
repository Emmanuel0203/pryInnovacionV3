-- 1) Verificar columnas actuales de la tabla usuario (útil para depurar diferencias de esquema)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'usuario'
ORDER BY ordinal_position;

-- 2) Mostrar si existe la función (opcional, para depuración)
SELECT n.nspname AS schema_name,
       p.proname AS function_name,
       pg_get_functiondef(p.oid) AS definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE p.proname = 'crear_usuario_con_roles';

-- 3) (Opcional) eliminar versiones anteriores si necesitas recrearla exactamente
DROP FUNCTION IF EXISTS public.crear_usuario_con_roles(TEXT, TEXT, JSONB, BOOLEAN, BOOLEAN, BOOLEAN, JSONB);

-- 4) Crear la función crear_usuario_con_roles (ajusta columnas si tu esquema difiere)
CREATE OR REPLACE FUNCTION public.crear_usuario_con_roles(
    p_email TEXT,
    p_password TEXT,
    p_roles JSONB,
    p_is_active BOOLEAN DEFAULT TRUE,
    p_is_staff BOOLEAN DEFAULT FALSE,
    p_is_superuser BOOLEAN DEFAULT FALSE,
    p_perfil JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_exists INTEGER;
    v_inserted_usuario RECORD;
    v_role RECORD;
    v_first_role_name TEXT := NULL;
    v_result JSONB;
    -- dynamic perfil insert helpers
    -- include 'rol' so we can populate perfil.rol from the first inserted role if available
    v_candidate_cols TEXT[] := ARRAY['usuario_email','nombre','rol','fecha_nacimiento','direccion','descripcion','area_expertise','info_adicional'];
    v_col TEXT;
    v_exists BOOLEAN;
    v_existing_cols TEXT[] := ARRAY[]::TEXT[];
    v_vals_list TEXT[] := ARRAY[]::TEXT[];
    v_cols_sql TEXT;
    v_vals_sql TEXT;
    v_sql TEXT;
BEGIN
    -- Comprobar existencia
    SELECT COUNT(*) INTO v_user_exists FROM public.usuario WHERE email = p_email;
    IF v_user_exists > 0 THEN
        v_result := jsonb_build_object('status','exists','message','usuario ya existe');
        RETURN v_result;
    END IF;

    -- Insert usuario: ajustado para evitar referencia a columnas no existentes (p.e. fecha_creacion)
    INSERT INTO public.usuario (email, password, is_active, is_staff, is_superuser)
    VALUES (p_email, p_password, p_is_active, p_is_staff, p_is_superuser)
    RETURNING * INTO v_inserted_usuario;

    -- Insert roles si vienen como JSONB [{ "fkidrol":1, "fkidaplicacion":1 }, ...]
    IF p_roles IS NOT NULL THEN
        FOR v_role IN SELECT * FROM jsonb_to_recordset(p_roles) AS (fkidrol INT, fkidaplicacion INT)
        LOOP
            -- Table `usuariorolaplicacion` uses `fkemail` (varchar) referencing usuario.email
            INSERT INTO public.usuariorolaplicacion (fkemail, fkidrol, fkidaplicacion)
            VALUES (p_email, v_role.fkidrol, v_role.fkidaplicacion);

            -- Capture the name of the first role inserted so we can populate perfil.rol if that column exists
            IF v_first_role_name IS NULL THEN
                SELECT nombre INTO v_first_role_name FROM public.rol WHERE id = v_role.fkidrol LIMIT 1;
            END IF;
        END LOOP;
    END IF;

    -- Insert perfil si viene: build INSERT dinámico incluyendo sólo columnas existentes
    IF p_perfil IS NOT NULL THEN
        -- iterate candidate columns in order and check existence
        FOREACH v_col IN ARRAY v_candidate_cols LOOP
            SELECT EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'perfil' AND column_name = v_col
            ) INTO v_exists;

            IF v_exists THEN
                -- collect column name (unquoted) and corresponding value expression
                v_existing_cols := array_append(v_existing_cols, v_col);

                IF v_col = 'usuario_email' THEN
                    v_vals_list := array_append(v_vals_list, quote_literal(p_email));
                ELSIF v_col = 'rol' THEN
                    -- prefer a provided rol in p_perfil, otherwise use the first role name we inserted
                    IF p_perfil ? 'rol' THEN
                        v_vals_list := array_append(v_vals_list, quote_literal(p_perfil->>'rol'));
                    ELSE
                        v_vals_list := array_append(v_vals_list, quote_literal(v_first_role_name));
                    END IF;
                ELSIF v_col = 'fecha_nacimiento' THEN
                    -- cast provided string to date if present, else NULL
                    v_vals_list := array_append(v_vals_list, format('CASE WHEN %L IS NOT NULL AND %L <> '''' THEN %L::date ELSE NULL END',
                        p_perfil->>'fecha_nacimiento', p_perfil->>'fecha_nacimiento', p_perfil->>'fecha_nacimiento'));
                ELSE
                    v_vals_list := array_append(v_vals_list, format('NULLIF(%L, '''')', p_perfil->>v_col));
                END IF;
            END IF;
        END LOOP;

        IF array_length(v_existing_cols,1) IS NOT NULL THEN
            v_cols_sql := array_to_string(ARRAY(SELECT quote_ident(x) FROM unnest(v_existing_cols) AS x), ', ');
            v_vals_sql := array_to_string(v_vals_list, ', ');
            v_sql := format('INSERT INTO public.perfil (%s) VALUES (%s)', v_cols_sql, v_vals_sql);
            EXECUTE v_sql;
        END IF;
    END IF;

    v_result := jsonb_build_object('status','ok','usuario', to_jsonb(v_inserted_usuario));
    RETURN v_result;

EXCEPTION WHEN OTHERS THEN
    -- Allow exception propagate with context
    RAISE;
END;
$$;

-- 5) Crear/asegurar función de limpieza (opcional)
DROP FUNCTION IF EXISTS public.eliminar_usuario_completo(TEXT);

CREATE OR REPLACE FUNCTION public.eliminar_usuario_completo(p_email TEXT)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted BOOLEAN := FALSE;
BEGIN
    DELETE FROM public.perfil WHERE usuario_email = p_email;
    -- Delete roles using fkemail (schema uses fkemail -> usuario.email)
    DELETE FROM public.usuariorolaplicacion WHERE fkemail = p_email;
    DELETE FROM public.usuario WHERE email = p_email;
    v_deleted := TRUE;
    RETURN jsonb_build_object('status','ok','deleted',v_deleted);
EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$;

-- 6) Prueba: invocar la función con datos de ejemplo (cambia email si ya existe)
SELECT public.crear_usuario_con_roles(
    'testapi@example.com',
    'Secreto123',
    '[{"fkidrol":1,"fkidaplicacion":1}]'::jsonb,
    TRUE,
    FALSE,
    FALSE,
    '{
        "nombre":"Test API",
        "fecha_nacimiento":"1990-01-01",
        "direccion":"Calle Ejemplo 123",
        "descripcion":"Prueba desde SQL",
        "area_expertise":"Ingeniería",
        "info_adicional":"Ninguna"
    }'::jsonb
) AS resultado_sp;

-- 7) Verificar contenido creado en tablas (usuario, perfil, usuariorolaplicacion)
SELECT * FROM public.usuario WHERE email = 'testapi@example.com';
SELECT * FROM public.perfil WHERE usuario_email = 'testapi@example.com';
-- usuariorolaplicacion uses fkemail -> usuario.email in this schema
SELECT * FROM public.usuariorolaplicacion WHERE fkemail = 'testapi@example.com';

-- 8) Limpieza (ejecuta si quieres eliminar lo creado en la prueba)
SELECT public.eliminar_usuario_completo('testapi@example.com') AS limpieza_result;

-- 9) Verificar que la función está registrada en el catálogo (opcional)
SELECT n.nspname AS schema,
       p.proname AS function_name,
       pg_get_function_arguments(p.oid) AS arguments,
       pg_get_function_result(p.oid) AS returns
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE p.proname = 'crear_usuario_con_roles';