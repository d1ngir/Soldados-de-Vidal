import socket
import threading
import json
import pyodbc

HOST = '0.0.0.0'
PORT = 3052

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=db_soldados;"
    "UID=soldados_vidal;"
    "PWD=CBSITABB2026!;"
    "TrustServerCertificate=yes;"
)

clientes_conectados = {}
lock = threading.Lock()

def get_db():
    return pyodbc.connect(CONN_STR)

def enviar_json(conn, data):
    try:
        conn.sendall((json.dumps(data) + "\n").encode('utf-8'))
    except Exception as e:
        print(f"[ERROR ENVIO] {e}")

def enviar_a_usuario(id_destino, data):
    with lock:
        for conn, info in list(clientes_conectados.items()):
            if info["id_usuario"] == id_destino:
                enviar_json(conn, data)

def broadcast_todos(data):
    with lock:
        for conn in list(clientes_conectados.keys()):
            enviar_json(conn, data)

def obtener_ids_en_linea():
    with lock:
        return {info["id_usuario"] for info in clientes_conectados.values()}

def obtener_datos_iniciales(cursor, id_usr):
    en_linea_ids = obtener_ids_en_linea()

    cursor.execute("SELECT id_usuario, nombre_usuario, CAST(ISNULL(foto, '1') AS VARCHAR(10)) FROM Usuarios")
    usuarios = [{
        "id": r[0],
        "nombre": r[1],
        "foto": str(r[2]).strip() or "1",
        "activo": (r[0] in en_linea_ids)
    } for r in cursor.fetchall()]

    cursor.execute("""
        SELECT G.id_grupo, G.nombre_grupo, G.id_creador, U.nombre_usuario
        FROM Grupos G
        JOIN MiembrosGrupo MG ON G.id_grupo = MG.id_grupo
        JOIN Usuarios U ON G.id_creador = U.id_usuario
        WHERE MG.id_usuario = ?
    """, (id_usr,))
    mis_grupos = [{"id": r[0], "nombre": r[1], "creador_id": r[2], "creador_nombre": r[3]} for r in cursor.fetchall()]

    cursor.execute("""
        SELECT C.id_canal, C.nombre_canal, C.id_propietario, U.nombre_usuario,
               CASE WHEN SC.id_usuario IS NOT NULL THEN 1 ELSE 0 END AS suscrito
        FROM Canales C
        JOIN Usuarios U ON C.id_propietario = U.id_usuario
        LEFT JOIN SuscriptoresCanal SC ON C.id_canal = SC.id_canal AND SC.id_usuario = ?
    """, (id_usr,))
    canales = [{"id": r[0], "nombre": r[1], "propietario": r[2], "propietario_nombre": r[3], "suscrito": bool(r[4])} for r in cursor.fetchall()]

    return usuarios, mis_grupos, canales

def manejar_cliente(conn, addr):
    print(f"[CONEXIÓN] {addr}")
    buffer = ""
    try:
        while True:
            datos = conn.recv(4096).decode('utf-8')
            if not datos:
                break
            buffer += datos
            while "\n" in buffer:
                linea, buffer = buffer.split("\n", 1)
                if linea.strip():
                    procesar_peticion(conn, json.loads(linea))
    except Exception as e:
        print(f"[ERROR CLIENTE {addr}] {e}")
    finally:
        with lock:
            user_info = clientes_conectados.pop(conn, None)
        conn.close()
        if user_info:
            broadcast_todos({"accion": "actualizar_listas"})
def procesar_peticion(conn, req):
    accion = req.get("accion")
    db = get_db()
    cursor = db.cursor()
    with lock:
        yo = clientes_conectados.get(conn)

    try:
        if accion == "registro":
            u, p, f = req.get("nombre_usuario"), req.get("contrasena"), str(req.get("foto", "1"))
            try:
                cursor.execute("INSERT INTO Usuarios (nombre_usuario, contrasena, foto) VALUES (?, ?, ?)", (u, p, f))
                db.commit()
                enviar_json(conn, {"accion": "registro_resp", "ok": True, "msg": "Usuario registrado con éxito. Ya puedes iniciar sesión."})
            except pyodbc.IntegrityError:
                enviar_json(conn, {"accion": "registro_resp", "ok": False, "msg": "Ese nombre de usuario ya existe."})

        elif accion == "login":
            u, p = req.get("nombre_usuario"), req.get("contrasena")
            cursor.execute("SELECT id_usuario, nombre_usuario, CAST(ISNULL(foto, '1') AS VARCHAR(10)) FROM Usuarios WHERE nombre_usuario=? AND contrasena=?", (u, p))
            row = cursor.fetchone()
            if row:
                id_u, nom_u, foto_u = row[0], row[1], (str(row[2]).strip() or "1")
                with lock:
                    clientes_conectados[conn] = {"id_usuario": id_u, "nombre_usuario": nom_u, "foto": foto_u}
                usuarios, grupos, canales = obtener_datos_iniciales(cursor, id_u)
                enviar_json(conn, {
                    "accion": "login_resp", "ok": True,
                    "id_usuario": id_u, "nombre_usuario": nom_u, "foto": foto_u,
                    "usuarios": usuarios, "grupos": grupos, "canales": canales
                })
                broadcast_todos({"accion": "actualizar_listas"})
            else:
                enviar_json(conn, {"accion": "login_resp", "ok": False, "msg": "Usuario o contraseña incorrectos."})

        elif accion == "refrescar_listas" and yo:
            usuarios, grupos, canales = obtener_datos_iniciales(cursor, yo["id_usuario"])
            enviar_json(conn, {"accion": "listas_resp", "usuarios": usuarios, "grupos": grupos, "canales": canales})

        elif accion == "cargar_chat" and yo:
            tipo = req.get("tipo")
            id_obj = req.get("id_objetivo")
            mensajes = []

            if tipo == "general":
                cursor.execute("""
                    SELECT U.nombre_usuario, CAST(ISNULL(U.foto,'1') AS VARCHAR(10)), C.contenido, FORMAT(DATEADD(HOUR, -6, C.fecha), 'HH:mm')
                    FROM ChatGeneral C JOIN Usuarios U ON C.id_emisor = U.id_usuario
                    ORDER BY C.id_mensaje ASC
                """)
                mensajes = [{"emisor": r[0], "foto": str(r[1]).strip() or "1", "contenido": r[2], "fecha": r[3]} for r in cursor.fetchall()]

            elif tipo == "directo":
                cursor.execute("""
                    SELECT U.nombre_usuario, CAST(ISNULL(U.foto,'1') AS VARCHAR(10)), M.contenido, FORMAT(DATEADD(HOUR, -6, M.fecha), 'HH:mm')
                    FROM MensajesDirectos M JOIN Usuarios U ON M.id_emisor = U.id_usuario
                    WHERE (M.id_emisor=? AND M.id_receptor=?) OR (M.id_emisor=? AND M.id_receptor=?)
                    ORDER BY M.id_mensaje ASC
                """, (yo["id_usuario"], id_obj, id_obj, yo["id_usuario"]))
                mensajes = [{"emisor": r[0], "foto": str(r[1]).strip() or "1", "contenido": r[2], "fecha": r[3]} for r in cursor.fetchall()]

            elif tipo == "grupo":
                cursor.execute("""
                    SELECT U.nombre_usuario, CAST(ISNULL(U.foto,'1') AS VARCHAR(10)), M.contenido, FORMAT(DATEADD(HOUR, -6, M.fecha), 'HH:mm')
                    FROM MensajesGrupo M JOIN Usuarios U ON M.id_emisor = U.id_usuario
                    WHERE M.id_grupo=? ORDER BY M.id_mensaje ASC
                """, (id_obj,))
                mensajes = [{"emisor": r[0], "foto": str(r[1]).strip() or "1", "contenido": r[2], "fecha": r[3]} for r in cursor.fetchall()]

            elif tipo == "canal":
                cursor.execute("""
                    SELECT C.nombre_canal, CAST(ISNULL(U.foto,'1') AS VARCHAR(10)), M.contenido, FORMAT(DATEADD(HOUR, -6, M.fecha), 'HH:mm')
                    FROM MensajesCanal M
                    JOIN Canales C ON M.id_canal = C.id_canal
                    JOIN Usuarios U ON C.id_propietario = U.id_usuario
                    WHERE M.id_canal=? ORDER BY M.id_mensaje ASC
                """, (id_obj,))
                mensajes = [{"emisor": r[0], "foto": str(r[1]).strip() or "1", "contenido": r[2], "fecha": r[3]} for r in cursor.fetchall()]

            enviar_json(conn, {"accion": "historial_resp", "tipo": tipo, "id_objetivo": id_obj, "mensajes": mensajes})

        elif accion == "enviar_mensaje" and yo:
            tipo = req.get("tipo")
            id_obj = req.get("id_objetivo")
            txt = req.get("contenido")

            if tipo == "general":
                cursor.execute("INSERT INTO ChatGeneral (id_emisor, contenido) OUTPUT FORMAT(DATEADD(HOUR, -6, INSERTED.fecha), 'HH:mm') VALUES (?, ?)", (yo["id_usuario"], txt))
                hora = cursor.fetchone()[0]
                db.commit()
                broadcast_todos({"accion": "nuevo_mensaje", "tipo": "general", "id_objetivo": 0, "emisor": yo["nombre_usuario"], "foto": yo["foto"], "contenido": txt, "fecha": hora})

            elif tipo == "directo":
                cursor.execute("INSERT INTO MensajesDirectos (id_emisor, id_receptor, contenido) OUTPUT FORMAT(DATEADD(HOUR, -6, INSERTED.fecha), 'HH:mm') VALUES (?, ?, ?)", (yo["id_usuario"], id_obj, txt))
                hora = cursor.fetchone()[0]
                db.commit()
                paquete_yo = {"accion": "nuevo_mensaje", "tipo": "directo", "id_objetivo": id_obj, "emisor": yo["nombre_usuario"], "foto": yo["foto"], "contenido": txt, "fecha": hora}
                paquete_el = {"accion": "nuevo_mensaje", "tipo": "directo", "id_objetivo": yo["id_usuario"], "emisor": yo["nombre_usuario"], "foto": yo["foto"], "contenido": txt, "fecha": hora}
                enviar_json(conn, paquete_yo)
                if id_obj != yo["id_usuario"]:
                    enviar_a_usuario(id_obj, paquete_el)

            elif tipo == "grupo":
                cursor.execute("INSERT INTO MensajesGrupo (id_grupo, id_emisor, contenido) OUTPUT FORMAT(DATEADD(HOUR, -6, INSERTED.fecha), 'HH:mm') VALUES (?, ?, ?)", (id_obj, yo["id_usuario"], txt))
                hora = cursor.fetchone()[0]
                db.commit()
                cursor.execute("SELECT id_usuario FROM MiembrosGrupo WHERE id_grupo=?", (id_obj,))
                miembros = [r[0] for r in cursor.fetchall()]
                paquete = {"accion": "nuevo_mensaje", "tipo": "grupo", "id_objetivo": id_obj, "emisor": yo["nombre_usuario"], "foto": yo["foto"], "contenido": txt, "fecha": hora}
                for m_id in miembros:
                    enviar_a_usuario(m_id, paquete)

            elif tipo == "canal":
                cursor.execute("SELECT id_propietario, nombre_canal FROM Canales WHERE id_canal=?", (id_obj,))
                c_row = cursor.fetchone()
                if c_row and c_row[0] == yo["id_usuario"]:
                    cursor.execute("INSERT INTO MensajesCanal (id_canal, contenido) OUTPUT FORMAT(DATEADD(HOUR, -6, INSERTED.fecha), 'HH:mm') VALUES (?, ?)", (id_obj, txt))
                    hora = cursor.fetchone()[0]
                    db.commit()
                    cursor.execute("SELECT id_usuario FROM SuscriptoresCanal WHERE id_canal=?", (id_obj,))
                    subs = [r[0] for r in cursor.fetchall()]
                    paquete = {"accion": "nuevo_mensaje", "tipo": "canal", "id_objetivo": id_obj, "emisor": c_row[1], "foto": yo["foto"], "contenido": txt, "fecha": hora}
                    for s_id in subs:
                        enviar_a_usuario(s_id, paquete)

        elif accion == "crear_grupo" and yo:
            nombre = req.get("nombre")
            miembros_nombres = req.get("miembros", [])
            cursor.execute("INSERT INTO Grupos (nombre_grupo, id_creador) OUTPUT INSERTED.id_grupo VALUES (?, ?)", (nombre, yo["id_usuario"]))
            id_g = cursor.fetchone()[0]
            cursor.execute("INSERT INTO MiembrosGrupo (id_grupo, id_usuario) VALUES (?, ?)", (id_g, yo["id_usuario"]))
            for nom in miembros_nombres:
                cursor.execute("SELECT id_usuario FROM Usuarios WHERE nombre_usuario=?", (nom.strip(),))
                u_row = cursor.fetchone()
                if u_row and u_row[0] != yo["id_usuario"]:
                    cursor.execute("INSERT INTO MiembrosGrupo (id_grupo, id_usuario) VALUES (?, ?)", (id_g, u_row[0]))
            db.commit()
            broadcast_todos({"accion": "actualizar_listas"})

        elif accion == "obtener_candidatos_grupo" and yo:
            id_g = req.get("id_grupo")
            modo = req.get("modo") # "agregar" o "eliminar"
            if modo == "agregar":
                cursor.execute("""
                    SELECT nombre_usuario FROM Usuarios
                    WHERE id_usuario NOT IN (SELECT id_usuario FROM MiembrosGrupo WHERE id_grupo=?)
                """, (id_g,))
            else:
                cursor.execute("""
                    SELECT U.nombre_usuario FROM MiembrosGrupo MG
                    JOIN Usuarios U ON MG.id_usuario = U.id_usuario
                    WHERE MG.id_grupo=? AND MG.id_usuario != ?
                """, (id_g, yo["id_usuario"]))
            lista = [r[0] for r in cursor.fetchall()]
            enviar_json(conn, {"accion": "candidatos_grupo_resp", "id_grupo": id_g, "modo": modo, "usuarios": lista})

        elif accion == "agregar_miembros_grupo" and yo:
            id_g = req.get("id_grupo")
            nombres = req.get("nombres_usuarios", [])
            cursor.execute("SELECT id_creador FROM Grupos WHERE id_grupo=?", (id_g,))
            g_row = cursor.fetchone()
            if g_row and g_row[0] == yo["id_usuario"]:
                agregados = 0
                for nom in nombres:
                    cursor.execute("SELECT id_usuario FROM Usuarios WHERE nombre_usuario=?", (nom.strip(),))
                    u_row = cursor.fetchone()
                    if u_row:
                        try:
                            cursor.execute("INSERT INTO MiembrosGrupo (id_grupo, id_usuario) VALUES (?, ?)", (id_g, u_row[0]))
                            agregados += 1
                        except pyodbc.IntegrityError:
                            pass
                db.commit()
                if agregados > 0:
                    enviar_json(conn, {"accion": "aviso_resp", "ok": True, "msg": f"Se agregaron {agregados} miembro(s) al grupo."})
                    broadcast_todos({"accion": "actualizar_listas"})

        elif accion == "eliminar_miembros_grupo" and yo:
            id_g = req.get("id_grupo")
            nombres = req.get("nombres_usuarios", [])
            cursor.execute("SELECT id_creador FROM Grupos WHERE id_grupo=?", (id_g,))
            g_row = cursor.fetchone()
            if g_row and g_row[0] == yo["id_usuario"]:
                eliminados = 0
                for nom in nombres:
                    cursor.execute("SELECT id_usuario FROM Usuarios WHERE nombre_usuario=?", (nom.strip(),))
                    u_row = cursor.fetchone()
                    if u_row and u_row[0] != yo["id_usuario"]:
                        cursor.execute("DELETE FROM MiembrosGrupo WHERE id_grupo=? AND id_usuario=?", (id_g, u_row[0]))
                        eliminados += 1
                db.commit()
                if eliminados > 0:
                    enviar_json(conn, {"accion": "aviso_resp", "ok": True, "msg": f"Se eliminaron {eliminados} miembro(s) del grupo."})
                    broadcast_todos({"accion": "actualizar_listas"})

        elif accion == "ver_miembros_grupo" and yo:
            id_g = req.get("id_grupo")
            en_linea_ids = obtener_ids_en_linea()
            cursor.execute("""
                SELECT U.id_usuario, U.nombre_usuario, G.id_creador
                FROM MiembrosGrupo MG
                JOIN Usuarios U ON MG.id_usuario = U.id_usuario
                JOIN Grupos G ON MG.id_grupo = G.id_grupo
                WHERE MG.id_grupo = ?
            """, (id_g,))
            miembros = []
            for r in cursor.fetchall():
                miembros.append({
                    "nombre": r[1],
                    "es_creador": (r[0] == r[2]),
                    "activo": (r[0] in en_linea_ids)
                })
            enviar_json(conn, {"accion": "miembros_grupo_resp", "miembros": miembros})

        elif accion == "salir_grupo" and yo:
            id_g = req.get("id_grupo")
            cursor.execute("DELETE FROM MiembrosGrupo WHERE id_grupo=? AND id_usuario=?", (id_g, yo["id_usuario"]))
            db.commit()
            broadcast_todos({"accion": "actualizar_listas"})

        elif accion == "crear_canal" and yo:
            nombre = req.get("nombre")
            cursor.execute("INSERT INTO Canales (nombre_canal, id_propietario) OUTPUT INSERTED.id_canal VALUES (?, ?)", (nombre, yo["id_usuario"]))
            id_c = cursor.fetchone()[0]
            cursor.execute("INSERT INTO SuscriptoresCanal (id_canal, id_usuario) VALUES (?, ?)", (id_c, yo["id_usuario"]))
            db.commit()
            broadcast_todos({"accion": "actualizar_listas"})

        elif accion == "eliminar_canal" and yo:
            id_c = req.get("id_canal")
            cursor.execute("SELECT id_propietario FROM Canales WHERE id_canal=?", (id_c,))
            c_row = cursor.fetchone()
            if c_row and c_row[0] == yo["id_usuario"]:
                cursor.execute("DELETE FROM MensajesCanal WHERE id_canal=?", (id_c,))
                cursor.execute("DELETE FROM SuscriptoresCanal WHERE id_canal=?", (id_c,))
                cursor.execute("DELETE FROM Canales WHERE id_canal=?", (id_c,))
                db.commit()
                broadcast_todos({"accion": "actualizar_listas"})

        elif accion == "suscribir_canal" and yo:
            id_c = req.get("id_canal")
            try:
                cursor.execute("INSERT INTO SuscriptoresCanal (id_canal, id_usuario) VALUES (?, ?)", (id_c, yo["id_usuario"]))
                db.commit()
            except:
                pass
            broadcast_todos({"accion": "actualizar_listas"})

        elif accion == "desuscribir_canal" and yo:
            id_c = req.get("id_canal")
            cursor.execute("SELECT id_propietario FROM Canales WHERE id_canal=?", (id_c,))
            c_row = cursor.fetchone()
            if c_row and c_row[0] != yo["id_usuario"]:
                cursor.execute("DELETE FROM SuscriptoresCanal WHERE id_canal=? AND id_usuario=?", (id_c, yo["id_usuario"]))
                db.commit()
                broadcast_todos({"accion": "actualizar_listas"})

    except Exception as e:
        print(f"[ERROR SQL/PETICION {accion}] {e}")
    finally:
        cursor.close()
        db.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVIDOR COMPLETO ACTIVO] Puerto {PORT}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
