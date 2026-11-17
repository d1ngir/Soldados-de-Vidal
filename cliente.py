import os
import socket
import threading
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog

SERVER_IP = '3.149.102.2'
PORT = 3052

class WasapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wasap - Acceso")
        self.root.geometry("360x230")

        self.id_usuario = None
        self.nombre_usuario = None
        self.foto_id = "1"
        self.avatares_tk = {}

        self.chat_actual = ("general", 0)
        self.usuarios = []
        self.grupos = []
        self.canales = []
        self.no_leidos_dm = {}

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_IP, PORT))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar al servidor:\n{e}")
            root.destroy()
            return

        self.cargar_avatares()
        threading.Thread(target=self.escuchar_servidor, daemon=True).start()
        self.construir_login()

    def cargar_avatares(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for i in range(1, 7):
            ruta = os.path.join(base_dir, "avatares", f"{i}.png")
            if os.path.exists(ruta):
                try:
                    img = tk.PhotoImage(file=ruta)
                    factor = max(1, img.width() // 48)
                    self.avatares_tk[str(i)] = img.subsample(factor, factor)
                except:
                    pass

    def enviar_json(self, data):
        try:
            self.sock.sendall((json.dumps(data) + "\n").encode('utf-8'))
        except:
            messagebox.showerror("Error", "Conexión perdida con el servidor.")

    # ---------------- PANTALLA LOGIN Y REGISTRO ----------------
    def construir_login(self):
        self.frame_login = tk.Frame(self.root, padx=25, pady=20)
        self.frame_login.pack(expand=True, fill=tk.BOTH)

        tk.Label(self.frame_login, text="Usuario:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.entry_user = tk.Entry(self.frame_login, width=35)
        self.entry_user.pack(pady=(2, 10))

        tk.Label(self.frame_login, text="Contraseña:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.entry_pass = tk.Entry(self.frame_login, show="*", width=35)
        self.entry_pass.pack(pady=(2, 15))
        self.entry_pass.bind("<Return>", lambda e: self.hacer_login())

        btn_frame = tk.Frame(self.frame_login)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Iniciar Sesión", command=self.hacer_login, width=14, bg="#25D366", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Registrarse", command=self.iniciar_flujo_registro, width=14, font=("Arial", 9)).pack(side=tk.RIGHT, padx=6)

    def hacer_login(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        if not u or not p:
            messagebox.showwarning("Campos vacíos", "Ingresa tu usuario y contraseña.")
            return
        self.enviar_json({"accion": "login", "nombre_usuario": u, "contrasena": p})

    def iniciar_flujo_registro(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        if not u or not p:
            messagebox.showwarning("Campos vacíos", "Primero escribe el usuario y la contraseña con los que deseas registrarte.")
            return

        modal_pwd = tk.Toplevel(self.root)
        modal_pwd.title("Confirmar Contraseña")
        modal_pwd.geometry("320x150")
        modal_pwd.resizable(False, False)
        modal_pwd.grab_set()

        tk.Label(modal_pwd, text="Introduce nuevamente tu contraseña:", font=("Arial", 9, "bold")).pack(pady=(15, 5))
        entry_confirm = tk.Entry(modal_pwd, show="*", width=30)
        entry_confirm.pack(pady=5)
        entry_confirm.focus_set()

        def verificar_pwd():
            if entry_confirm.get().strip() != p:
                messagebox.showerror("Error", "Las contraseñas no coinciden.", parent=modal_pwd)
                return
            modal_pwd.destroy()
            self.abrir_selector_avatar(u, p)

        entry_confirm.bind("<Return>", lambda e: verificar_pwd())
        tk.Button(modal_pwd, text="Continuar", command=verificar_pwd, bg="#25D366", fg="white", width=14).pack(pady=10)

    def abrir_selector_avatar(self, u, p):
        modal = tk.Toplevel(self.root)
        modal.title("Elige tu foto de perfil")
        modal.geometry("460x190")
        modal.resizable(False, False)
        modal.grab_set()

        tk.Label(modal, text=f"Selecciona una foto de perfil para '{u}':", font=("Arial", 10, "bold")).pack(pady=(12, 8))

        avatar_var = tk.StringVar(value="1")
        av_frame = tk.Frame(modal)
        av_frame.pack(pady=5)

        for i in range(1, 7):
            sid = str(i)
            rb = tk.Radiobutton(
                av_frame, text="", variable=avatar_var, value=sid,
                image=self.avatares_tk.get(sid), indicatoron=0, width=58, height=58
            )
            rb.pack(side=tk.LEFT, padx=4)

        def confirmar():
            self.enviar_json({
                "accion": "registro",
                "nombre_usuario": u,
                "contrasena": p,
                "foto": avatar_var.get()
            })
            modal.destroy()

        tk.Button(modal, text="Confirmar Registro", command=confirmar, bg="#25D366", fg="white", font=("Arial", 9, "bold"), width=18).pack(pady=12)

    # ---------------- INTERFAZ PRINCIPAL ----------------
    def construir_principal(self):
        self.frame_login.destroy()
        self.root.title(f"Wasap - {self.nombre_usuario}")
        self.root.geometry("900x540")

        left_panel = tk.Frame(self.root, width=265, bg="#f0f2f5", padx=8, pady=8)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)

        perfil_frame = tk.Frame(left_panel, bg="#f0f2f5")
        perfil_frame.pack(fill=tk.X, pady=(0, 8))
        if self.foto_id in self.avatares_tk:
            tk.Label(perfil_frame, image=self.avatares_tk[self.foto_id], bg="#f0f2f5").pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(perfil_frame, text=f"{self.nombre_usuario}\n🟢 En línea", font=("Arial", 10, "bold"), bg="#f0f2f5", justify=tk.LEFT).pack(side=tk.LEFT)

        tk.Button(left_panel, text="🌐 Chat General", command=lambda: self.seleccionar_chat("general", 0, "🌐 Chat General"), anchor="w", bg="#d9fdd3").pack(fill=tk.X, pady=3)

        tk.Label(left_panel, text="💬 Mensajes Directos", font=("Arial", 9, "bold"), bg="#f0f2f5").pack(anchor="w", pady=(8, 2))
        self.list_usuarios = tk.Listbox(left_panel, height=6, font=("Consolas", 9))
        self.list_usuarios.pack(fill=tk.X)
        self.list_usuarios.bind("<<ListboxSelect>>", self.al_elegir_usuario)

        grp_hdr = tk.Frame(left_panel, bg="#f0f2f5")
        grp_hdr.pack(fill=tk.X, pady=(8, 2))
        tk.Label(grp_hdr, text="👥 Grupos", font=("Arial", 9, "bold"), bg="#f0f2f5").pack(side=tk.LEFT)
        tk.Button(grp_hdr, text="+ Crear", font=("Arial", 8), command=self.dialogo_crear_grupo).pack(side=tk.RIGHT)

        self.list_grupos = tk.Listbox(left_panel, height=4)
        self.list_grupos.pack(fill=tk.X)
        self.list_grupos.bind("<<ListboxSelect>>", self.al_elegir_grupo)

        can_hdr = tk.Frame(left_panel, bg="#f0f2f5")
        can_hdr.pack(fill=tk.X, pady=(8, 2))
        tk.Label(can_hdr, text="📢 Canales", font=("Arial", 9, "bold"), bg="#f0f2f5").pack(side=tk.LEFT)
        tk.Button(can_hdr, text="+ Crear", font=("Arial", 8), command=self.dialogo_crear_canal).pack(side=tk.RIGHT)

        self.list_canales = tk.Listbox(left_panel, height=4)
        self.list_canales.pack(fill=tk.X)
        self.list_canales.bind("<<ListboxSelect>>", self.al_elegir_canal)

        right_panel = tk.Frame(self.root, padx=10, pady=10)
        right_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        header_chat = tk.Frame(right_panel)
        header_chat.pack(fill=tk.X, pady=(0, 5))

        title_box = tk.Frame(header_chat)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lbl_titulo_chat = tk.Label(title_box, text="🌐 Chat General", font=("Arial", 12, "bold"), anchor="w")
        self.lbl_titulo_chat.pack(anchor="w")
        self.lbl_subtitulo_chat = tk.Label(title_box, text="", font=("Arial", 8, "italic"), fg="#555555", anchor="w")
        self.lbl_subtitulo_chat.pack(anchor="w")

        self.acciones_chat_frame = tk.Frame(header_chat)
        self.acciones_chat_frame.pack(side=tk.RIGHT)

        self.chat_area = scrolledtext.ScrolledText(right_panel, wrap=tk.WORD, state='disabled')
        self.chat_area.pack(expand=True, fill=tk.BOTH)

        bottom = tk.Frame(right_panel)
        bottom.pack(fill=tk.X, pady=(8, 0))
        self.msg_entry = tk.Entry(bottom)
        self.msg_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.msg_entry.bind("<Return>", lambda e: self.enviar_mensaje())
        self.btn_enviar = tk.Button(bottom, text="Enviar", command=self.enviar_mensaje, width=10, bg="#25D366", fg="white")
        self.btn_enviar.pack(side=tk.RIGHT)

        self.actualizar_listboxes()
        self.seleccionar_chat("general", 0, "🌐 Chat General")

    def actualizar_listboxes(self):
        self.list_usuarios.delete(0, tk.END)
        for u in self.usuarios:
            if u["id"] != self.id_usuario:
                estado_ico = "🟢" if u.get("activo") else "⚪"
                pendientes = self.no_leidos_dm.get(u["id"], 0)
                if pendientes > 0:
                    nombre_fmt = f"{estado_ico} @{u['nombre']:<14} {pendientes}"
                else:
                    nombre_fmt = f"{estado_ico} @{u['nombre']}"
                self.list_usuarios.insert(tk.END, nombre_fmt)

        self.list_grupos.delete(0, tk.END)
        for g in self.grupos:
            self.list_grupos.insert(tk.END, f"# {g['nombre']}")

        self.list_canales.delete(0, tk.END)
        for c in self.canales:
            estado = "✓" if c["suscrito"] else "+ Unirse:"
            self.list_canales.insert(tk.END, f"{estado} {c['nombre']}")

    def limpiar_botones_contextuales(self):
        for w in self.acciones_chat_frame.winfo_children():
            w.destroy()

    def seleccionar_chat(self, tipo, id_obj, titulo, subtitulo="", solo_lectura=False):
        self.chat_actual = (tipo, id_obj)
        self.lbl_titulo_chat.config(text=titulo)
        self.lbl_subtitulo_chat.config(text=subtitulo)
        self.limpiar_botones_contextuales()

        if tipo == "directo" and id_obj in self.no_leidos_dm:
            self.no_leidos_dm.pop(id_obj, None)
            self.actualizar_listboxes()

        elif tipo == "grupo":
            g = next((x for x in self.grupos if x["id"] == id_obj), None)
            if g:
                tk.Button(self.acciones_chat_frame, text="Ver miembros", font=("Arial", 8), bg="#e7f3ff",
                          command=lambda: self.enviar_json({"accion": "ver_miembros_grupo", "id_grupo": id_obj})).pack(side=tk.LEFT, padx=2)
                if g["creador_id"] == self.id_usuario:
                    tk.Button(self.acciones_chat_frame, text="+ Agregar", font=("Arial", 8), bg="#d9fdd3",
                              command=lambda: self.enviar_json({"accion": "obtener_candidatos_grupo", "id_grupo": id_obj, "modo": "agregar"})).pack(side=tk.LEFT, padx=2)
                    tk.Button(self.acciones_chat_frame, text="Eliminar", font=("Arial", 8), bg="#ffdddd",
                              command=lambda: self.enviar_json({"accion": "obtener_candidatos_grupo", "id_grupo": id_obj, "modo": "eliminar"})).pack(side=tk.LEFT, padx=2)
                tk.Button(self.acciones_chat_frame, text="Salir", font=("Arial", 8), bg="#eeeeee",
                          command=lambda: self.salir_de_grupo(id_obj)).pack(side=tk.LEFT, padx=2)

        elif tipo == "canal":
            c = next((x for x in self.canales if x["id"] == id_obj), None)
            if c:
                if c["propietario"] == self.id_usuario:
                    tk.Button(self.acciones_chat_frame, text="Eliminar canal", font=("Arial", 8), bg="#ffdddd",
                              command=lambda: self.eliminar_canal(id_obj)).pack(side=tk.LEFT, padx=2)
                else:
                    tk.Button(self.acciones_chat_frame, text="Dejar de seguir", font=("Arial", 8), bg="#ffdddd",
                              command=lambda: self.dejar_de_seguir_canal(id_obj)).pack(side=tk.LEFT, padx=2)

        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        self.chat_area.config(state='disabled')

        estado_input = 'disabled' if solo_lectura else 'normal'
        self.msg_entry.config(state=estado_input)
        self.btn_enviar.config(state=estado_input)

        self.enviar_json({"accion": "cargar_chat", "tipo": tipo, "id_objetivo": id_obj})

    def al_elegir_usuario(self, event):
        sel = self.list_usuarios.curselection()
        if not sel: return
        otros = [u for u in self.usuarios if u["id"] != self.id_usuario]
        u = otros[sel[0]]
        estado = "En línea" if u.get("activo") else "Desconectado"
        self.seleccionar_chat("directo", u["id"], f"💬 Privado con {u['nombre']}", subtitulo=estado)

    def al_elegir_grupo(self, event):
        sel = self.list_grupos.curselection()
        if not sel: return
        g = self.grupos[sel[0]]
        self.seleccionar_chat("grupo", g["id"], f"👥 {g['nombre']}", subtitulo=f"Grupo de {g['creador_nombre']}")

    def al_elegir_canal(self, event):
        sel = self.list_canales.curselection()
        if not sel: return
        c = self.canales[sel[0]]
        if not c["suscrito"]:
            if messagebox.askyesno("Canal", f"¿Deseas suscribirte al canal '{c['nombre']}' (Canal de {c['propietario_nombre']})?"):
                self.enviar_json({"accion": "suscribir_canal", "id_canal": c["id"]})
            return
        es_dueno = (c["propietario"] == self.id_usuario)
        self.seleccionar_chat("canal", c["id"], f"📢 {c['nombre']}", subtitulo=f"Canal de {c['propietario_nombre']}", solo_lectura=not es_dueno)

    # ---------------- MODALES CON SELECCIÓN MÚLTIPLE ----------------
    def dialogo_crear_grupo(self):
        otros = [u["nombre"] for u in self.usuarios if u["id"] != self.id_usuario]

        modal = tk.Toplevel(self.root)
        modal.title("Nuevo Grupo")
        modal.geometry("320x320")
        modal.grab_set()

        tk.Label(modal, text="Nombre del grupo:", font=("Arial", 9, "bold")).pack(anchor="w", padx=15, pady=(12, 2))
        entry_nom = tk.Entry(modal, width=36)
        entry_nom.pack(padx=15, pady=(0, 8))
        entry_nom.focus_set()

        tk.Label(modal, text="Selecciona miembros (clic para marcar varios):", font=("Arial", 9)).pack(anchor="w", padx=15)
        lb = tk.Listbox(modal, selectmode=tk.MULTIPLE, height=9)
        lb.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        for nom in otros:
            lb.insert(tk.END, nom)

        def confirmar():
            nombre = entry_nom.get().strip()
            if not nombre:
                messagebox.showwarning("Aviso", "Escribe un nombre para el grupo.", parent=modal)
                return
            seleccionados = [lb.get(i) for i in lb.curselection()]
            self.enviar_json({"accion": "crear_grupo", "nombre": nombre, "miembros": seleccionados})
            modal.destroy()

        tk.Button(modal, text="Crear Grupo", command=confirmar, bg="#25D366", fg="white", font=("Arial", 9, "bold"), width=15).pack(pady=10)

    def abrir_selector_miembros_grupo(self, id_grupo, modo, lista_usuarios):
        if not lista_usuarios:
            msg = "Todos los usuarios registrados ya pertenecen a este grupo." if modo == "agregar" else "No hay otros miembros en este grupo para eliminar."
            messagebox.showinfo("Grupo", msg)
            return

        modal = tk.Toplevel(self.root)
        titulo = "Agregar miembros al grupo" if modo == "agregar" else "Eliminar miembros del grupo"
        modal.title(titulo)
        modal.geometry("310x290")
        modal.grab_set()

        instruccion = "Selecciona uno o más usuarios:"
        tk.Label(modal, text=instruccion, font=("Arial", 9, "bold")).pack(anchor="w", padx=15, pady=(12, 5))

        lb = tk.Listbox(modal, selectmode=tk.MULTIPLE, height=10)
        lb.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        for nom in lista_usuarios:
            lb.insert(tk.END, nom)

        def confirmar():
            seleccionados = [lb.get(i) for i in lb.curselection()]
            if not seleccionados:
                messagebox.showwarning("Aviso", "Selecciona al menos un usuario de la lista.", parent=modal)
                return
            accion = "agregar_miembros_grupo" if modo == "agregar" else "eliminar_miembros_grupo"
            self.enviar_json({"accion": accion, "id_grupo": id_grupo, "nombres_usuarios": seleccionados})
            modal.destroy()

        btn_txt = "Agregar seleccionados" if modo == "agregar" else "Eliminar seleccionados"
        btn_col = "#25D366" if modo == "agregar" else "#d9534f"
        tk.Button(modal, text=btn_txt, command=confirmar, bg=btn_col, fg="white", font=("Arial", 9, "bold"), width=20).pack(pady=10)

    def salir_de_grupo(self, id_grupo):
        if messagebox.askyesno("Salir", "¿Seguro que quieres salir de este grupo?"):
            self.enviar_json({"accion": "salir_grupo", "id_grupo": id_grupo})
            self.seleccionar_chat("general", 0, "🌐 Chat General")

    def dialogo_crear_canal(self):
        nombre = simpledialog.askstring("Nuevo Canal", "Nombre del canal de difusión:")
        if nombre:
            self.enviar_json({"accion": "crear_canal", "nombre": nombre.strip()})

    def eliminar_canal(self, id_canal):
        if messagebox.askyesno("Eliminar Canal", "¿Seguro que deseas eliminar este canal permanentemente para todos?"):
            self.enviar_json({"accion": "eliminar_canal", "id_canal": id_canal})
            self.seleccionar_chat("general", 0, "🌐 Chat General")

    def dejar_de_seguir_canal(self, id_canal):
        if messagebox.askyesno("Canal", "¿Deseas dejar de seguir este canal?"):
            self.enviar_json({"accion": "desuscribir_canal", "id_canal": id_canal})
            self.seleccionar_chat("general", 0, "🌐 Chat General")

    def mostrar_modal_miembros(self, miembros):
        modal = tk.Toplevel(self.root)
        modal.title("Miembros del Grupo")
        modal.geometry("300x260")
        modal.grab_set()

        tk.Label(modal, text="Integrantes del grupo:", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        lb = tk.Listbox(modal, width=38, height=10)
        lb.pack(padx=12, pady=5, expand=True, fill=tk.BOTH)

        for m in miembros:
            ico = "🟢" if m["activo"] else "⚪"
            rol = " (Creador)" if m["es_creador"] else ""
            lb.insert(tk.END, f"{ico} {m['nombre']}{rol}")

        tk.Button(modal, text="Cerrar", command=modal.destroy, width=12).pack(pady=8)

    def enviar_mensaje(self):
        txt = self.msg_entry.get().strip()
        if txt:
            tipo, id_obj = self.chat_actual
            self.enviar_json({"accion": "enviar_mensaje", "tipo": tipo, "id_objetivo": id_obj, "contenido": txt})
            self.msg_entry.delete(0, tk.END)

    def insertar_mensaje_ui(self, m):
        self.chat_area.config(state='normal')
        foto_id = str(m.get("foto", "1")).strip()
        if foto_id in self.avatares_tk:
            self.chat_area.image_create(tk.END, image=self.avatares_tk[foto_id])
            self.chat_area.insert(tk.END, " ")
        self.chat_area.insert(tk.END, f"[{m['fecha']}] {m['emisor']}: {m['contenido']}\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

    # ---------------- RECEPCIÓN DE RED ----------------
    def escuchar_servidor(self):
        buffer = ""
        while True:
            try:
                datos = self.sock.recv(4096).decode('utf-8')
                if not datos: break
                buffer += datos
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    if linea.strip():
                        self.procesar_respuesta(json.loads(linea))
            except Exception as e:
                print(f"[ERROR RED] {e}")
                break

    def procesar_respuesta(self, res):
        acc = res.get("accion")
        if acc == "registro_resp":
            fn = messagebox.showinfo if res["ok"] else messagebox.showerror
            self.root.after(0, lambda: fn("Registro", res["msg"]))

        elif acc == "aviso_resp":
            fn = messagebox.showinfo if res["ok"] else messagebox.showerror
            self.root.after(0, lambda: fn("Aviso", res["msg"]))

        elif acc == "miembros_grupo_resp":
            self.root.after(0, lambda: self.mostrar_modal_miembros(res["miembros"]))

        elif acc == "candidatos_grupo_resp":
            self.root.after(0, lambda: self.abrir_selector_miembros_grupo(res["id_grupo"], res["modo"], res["usuarios"]))

        elif acc == "login_resp":
            if res["ok"]:
                self.id_usuario = res["id_usuario"]
                self.nombre_usuario = res["nombre_usuario"]
                self.foto_id = str(res["foto"]).strip() or "1"
                self.usuarios = res["usuarios"]
                self.grupos = res["grupos"]
                self.canales = res["canales"]
                self.root.after(0, self.construir_principal)
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", res["msg"]))

        elif acc == "actualizar_listas":
            self.enviar_json({"accion": "refrescar_listas"})

        elif acc == "listas_resp":
            self.usuarios = res["usuarios"]
            self.grupos = res["grupos"]
            self.canales = res["canales"]
            def refrescar_vista():
                self.actualizar_listboxes()
                tipo, id_obj = self.chat_actual
                if tipo == "grupo" and not any(g["id"] == id_obj for g in self.grupos):
                    self.seleccionar_chat("general", 0, "🌐 Chat General")
                elif tipo == "canal" and not any(c["id"] == id_obj for c in self.canales):
                    self.seleccionar_chat("general", 0, "🌐 Chat General")
                elif tipo == "directo":
                    u = next((x for x in self.usuarios if x["id"] == id_obj), None)
                    if u:
                        self.lbl_subtitulo_chat.config(text=("En línea" if u.get("activo") else "Desconectado"))
            self.root.after(0, refrescar_vista)

        elif acc == "historial_resp":
            if (res["tipo"], res["id_objetivo"]) == self.chat_actual:
                def pintar():
                    for m in res["mensajes"]:
                        self.insertar_mensaje_ui(m)
                self.root.after(0, pintar)

        elif acc == "nuevo_mensaje":
            if (res["tipo"], res["id_objetivo"]) == self.chat_actual:
                self.root.after(0, lambda: self.insertar_mensaje_ui(res))
            elif res["tipo"] == "directo":
                remitente_id = res["id_objetivo"]
                self.no_leidos_dm[remitente_id] = self.no_leidos_dm.get(remitente_id, 0) + 1
                self.root.after(0, self.actualizar_listboxes)

if __name__ == "__main__":
    root = tk.Tk()
    app = WasapApp(root)
    root.mainloop()