import os
import subprocess
import sys
import locale
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, PhotoImage, ttk
import sqlite3
import logging
from tkinter import scrolledtext
from tkcalendar import DateEntry
import pandas as pd
from PIL import Image, ImageTk
from dateutil.relativedelta import relativedelta

# Configurar el registro de errores
logging.basicConfig(filename='AplicacionDeGastos_error.log', level=logging.ERROR, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)

# Configurar el locale a español
locale.setlocale(locale.LC_ALL, 'es_ES.utf8')

class Transaccion:
    def __init__(self, categoria, cantidad, hora):
        self.categoria = categoria
        self.cantidad = cantidad
        self.hora = hora

class RecordatorioPago:
    def __init__(self, nombre, monto, cuotas, fecha_primer_vencimiento, repite_mensualmente=False):
        self.nombre = nombre
        self.monto = monto
        self.cuotas = cuotas
        self.fecha_primer_vencimiento = fecha_primer_vencimiento
        self.fechas_vencimiento = [self.fecha_primer_vencimiento + relativedelta(months=i) for i in range(self.cuotas)]
        self.cuotas_pagadas = 0
        self.repite_mensualmente = repite_mensualmente

class AplicacionDeGastos:
    def __init__(self, root):
        logger.info("Iniciando la aplicación de gastos...")
        self.transacciones = []
        self.recordatorios = []
        self.root = root
        self.root.geometry('600x600')  # Ajusta el tamaño de la ventana
        self.root.configure(bg='#2c3e50')  # Color de fondo
        self.root.title("Aplicación de Gastos")  # Título de la ventana
        self.categoria_var = tk.StringVar()
        self.cantidad_var = tk.StringVar()
        self.saldo_var = tk.StringVar()
        self.saldo_var.set("Saldo: 0")
        self.log_var = tk.StringVar()
        self.fecha_limite = None
        try:
            self.crear_interfaz()
            self.crear_base_de_datos()
            self.cargar_transacciones()
            self.cargar_recordatorios()
        except Exception as e:
            logger.error("Error en __init__: " + str(e))

    def balance(self):
        # Calcula el balance sumando todas las cantidades de las transacciones
        try:
            balance = sum(t.cantidad for t in self.transacciones)
            return balance
        except Exception as e:
            logger.error("Error en balance: " + str(e))

    def saldo(self):
        try:
            return sum(t.cantidad for t in self.transacciones)
        except Exception as e:
            logger.error("Error en saldo: " + str(e))

    def crear_interfaz(self):
        try:
            logger.info("Creando la interfaz...")
            # Crear la barra de herramientas
            toolbar = tk.Menu(self.root)
            self.root.config(menu=toolbar)

            tk.Button(self.root, text="Corregir saldo inicial", command=self.corregir_saldo_inicial, bg='light green').grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky='ew')  # Botón de color verde claro
            tk.Label(self.root, text="Categoría:", bg='#2c3e50', fg='#ecf0f1').grid(row=1, column=0, padx=10, sticky='w')  # Etiqueta de color azul claro
            tk.Entry(self.root, textvariable=self.categoria_var).grid(row=1, column=1, padx=10, sticky='ew')
            tk.Button(self.root, text="Agregar gasto", command=self.agregar_gasto, bg='red').grid(row=3, column=0, pady=10, padx=10, sticky='ew')  # Botón de color rojo
            tk.Button(self.root, text="Agregar ingreso", command=self.agregar_ingreso, bg='light green').grid(row=3, column=1, pady=10, padx=10, sticky='ew')  # Botón de color verde claro
            tk.Label(self.root, textvariable=self.saldo_var, bg='#2c3e50', fg='#ecf0f1').grid(row=4, column=0, columnspan=3, padx=10)  # Etiqueta de color azul claro
            tk.Button(self.root, text="Ver gastos por categoría", command=self.ver_gastos_por_categoria, bg='light green').grid(row=5, column=0, pady=10, padx=10, sticky='ew')  # Botón de color verde claro
            tk.Button(self.root, text="Recordatorios de pago", command=self.ver_recordatorios_de_pago, bg='light green').grid(row=5, column=1, pady=10, padx=10, sticky='ew')  # Botón de color verde claro
            tk.Button(self.root, text="Objetivos de ahorro", command=self.ver_objetivos_de_ahorro, bg='light green').grid(row=5, column=2, pady=10, padx=10, sticky='ew')  # Botón de color verde claro
            tk.Button(self.root, text="Exportar a Excel", command=self.exportar_a_excel, bg='light green').grid(row=6, column=0, pady=10, padx=10, sticky='ew')  # Botón de color verde claro
            tk.Button(self.root, text="Calcular gasto diario", command=self.calcular_gasto_diario, bg='light green').grid(row=6, column=1, pady=10, padx=10, sticky='ew')  # Botón de color verde claro
            self.gasto_diario_var = tk.StringVar()  # Variable para almacenar el gasto diario
            self.gasto_diario_var.set("Gasto diario: ")  # Inicializa la variable con un valor por defecto
            tk.Label(self.root, textvariable=self.gasto_diario_var, bg='green', fg='#ecf0f1').grid(row=6, column=2, padx=10)  # Etiqueta con fondo verde

            tk.Label(self.root, text="Registro de transacciones:", bg='#2c3e50', fg='#ecf0f1').grid(row=8, column=0, columnspan=3, padx=10)  # Etiqueta de color azul claro
            self.log = scrolledtext.ScrolledText(self.root, width=60, height=20)
            self.log.grid(row=9, column=0, columnspan=3, padx=10)  # Texto desplazable
            tk.Button(self.root, text="Objetivos de ahorro", command=self.ver_objetivos_de_ahorro, bg='light green').grid(row=5, column=2, pady=10, padx=10, sticky='ew')  # Botón de color verde claro

            # Ajusta el tamaño de las columnas para que se expandan con la ventana
            self.root.grid_columnconfigure(0, weight=1)
            self.root.grid_columnconfigure(1, weight=1)
            self.root.grid_columnconfigure(2, weight=1)
            logger.info("Interfaz creada exitosamente.")
        except Exception as e:
            logger.error("Error en crear_interfaz: " + str(e))

    def crear_base_de_datos(self):
        try:
            logger.info("Creando la base de datos...")
            self.conn = sqlite3.connect('gastos.db')
            self.c = self.conn.cursor()
            self.c.execute('''CREATE TABLE IF NOT EXISTS transacciones
            (
            hora text, categoria text, cantidad real)''')
            self.c.execute('''CREATE TABLE IF NOT EXISTS fecha_limite
            (
            fecha text)''')
            # Crea la tabla de recordatorios si no existe
            self.c.execute('''CREATE TABLE IF NOT EXISTS recordatorios
            (
            nombre text, monto real, cuotas integer, fecha_primer_vencimiento text, repite_mensualmente integer)''')
            logger.info("Base de datos creada exitosamente.")
        except Exception as e:
            logger.error("Error en crear_base_de_datos: " + str(e))

    def cargar_transacciones(self):
        try:
            logger.info("Cargando transacciones...")
            for row in self.c.execute('SELECT * FROM transacciones ORDER BY hora'):
                hora, categoria, cantidad = row
                transaccion = Transaccion(categoria, cantidad, datetime.strptime(hora, "%Y-%m-%d %H:%M"))
                self.transacciones.append(transaccion)
                self.log.insert(tk.END, transaccion.hora.strftime("%Y-%m-%d %H:%M") + " - " + ("Ingreso" if cantidad >= 0 else "Gasto") + " en " + categoria + ": " + "{:,.0f}".format(cantidad).replace(",", ".") + "\n")
                self.saldo_var.set("Saldo: " + "{:,.0f}".format(self.saldo()).replace(",", "."))
                if self.fecha_limite is not None:
                    self.gasto_diario_var.set("Gasto diario hasta " + self.fecha_limite.strftime("%Y-%m-%d") + ": " + "{:,.0f}".format(int(self.calcular_gasto_diario())).replace(",", ".") + " | Días restantes: " + str((self.fecha_limite.date() - datetime.today().date()).days))
            logger.info("Transacciones cargadas exitosamente.")
        except Exception as e:
            logger.error("Error en cargar_transacciones: " + str(e))

    def cargar_recordatorios(self):
        try:
            logger.info("Cargando recordatorios...")
            self.recordatorios = []  # Vacía la lista de recordatorios antes de cargarlos de la base de datos
            for row in self.c.execute('SELECT * FROM recordatorios'):
                nombre, monto, cuotas, fecha_primer_vencimiento_str, repite_mensualmente = row
                fecha_primer_vencimiento = datetime.strptime(fecha_primer_vencimiento_str, "%Y-%m-%d")
                recordatorio = RecordatorioPago(nombre, monto, cuotas, fecha_primer_vencimiento, bool(repite_mensualmente))
                self.recordatorios.append(recordatorio)
            logger.info("Recordatorios cargados exitosamente.")
        except Exception as e:
            logger.error("Error en cargar_recordatorios: " + str(e))

    def agregar_gasto(self):
        try:
            logger.info("Agregando gasto...")
            categoria = self.categoria_var.get()
            cantidad = -float(self.cantidad_var.get())
            transaccion = Transaccion(categoria, cantidad, datetime.now())
            self.transacciones.append(transaccion)
            self.saldo_var.set("Saldo: " + "{:,.0f}".format(self.saldo()).replace(",", "."))
            self.log.insert(tk.END, transaccion.hora.strftime("%Y-%m-%d %H:%M") + " - Gasto en " + categoria + ": " + "{:,.0f}".format(cantidad).replace(",", ".") + "\n")
            self.c.execute("INSERT INTO transacciones VALUES (?, ?, ?)", (transaccion.hora.strftime("%Y-%m-%d %H:%M"), categoria, cantidad))
            self.conn.commit()
            self.actualizar_gasto_diario()
            self.mostrar_notificacion("Gasto agregado", "Se ha agregado un gasto en la categoría " + categoria)
            logger.info("Gasto agregado exitosamente.")
        except Exception as e:
            logger.error("Error en agregar_gasto: " + str(e))

    def agregar_ingreso(self):
        try:
            logger.info("Agregando ingreso...")
            categoria = self.categoria_var.get()
            cantidad = float(self.cantidad_var.get())
            transaccion = Transaccion(categoria, cantidad, datetime.now())
            self.transacciones.append(transaccion)
            self.saldo_var.set("Saldo: " + "{:,.0f}".format(self.saldo()).replace(",", "."))
            self.log.insert(tk.END, transaccion.hora.strftime("%Y-%m-%d %H:%M") + " - Ingreso en " + categoria + ": " + "{:,.0f}".format(cantidad).replace(",", ".") + "\n")
            self.c.execute("INSERT INTO transacciones VALUES (?, ?, ?)", (transaccion.hora.strftime("%Y-%m-%d %H:%M"), categoria, cantidad))
            self.conn.commit()
            self.actualizar_gasto_diario()
            self.mostrar_notificacion("Ingreso agregado", "Se ha agregado un ingreso en la categoría " + categoria)
            logger.info("Ingreso agregado exitosamente.")
        except Exception as e:
            logger.error("Error en agregar_ingreso: " + str(e))

    def corregir_saldo_inicial(self):
        try:
            logger.info("Corrigiendo saldo inicial...")
            saldo_inicial = simpledialog.askfloat("Saldo inicial", "Ingresa el nuevo saldo inicial:")
            self.transacciones = [Transaccion("Saldo inicial", saldo_inicial, datetime.now())]
            self.saldo_var.set("Saldo: " + "{:,.0f}".format(self.saldo()).replace(",", "."))
            self.log.delete('1.0', tk.END)
            self.log.insert(tk.END, "Saldo inicial corregido a: " + "{:,.0f}".format(saldo_inicial).replace(",", ".") + "\n")
            self.c.execute("DELETE FROM transacciones")
            self.c.execute("INSERT INTO transacciones VALUES (?, ?, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), "Saldo inicial", saldo_inicial))
            self.conn.commit()
            self.actualizar_gasto_diario()
            self.mostrar_notificacion("Saldo inicial corregido", "El saldo inicial ha sido corregido a " + "{:,.0f}".format(saldo_inicial).replace(",", "."))
            logger.info("Saldo inicial corregido exitosamente.")
        except Exception as e:
            logger.error("Error en corregir_saldo_inicial: " + str(e))

    def ver_gastos_por_categoria(self):
        try:
            logger.info("Mostrando gastos por categoría...")
            categorias = list(set([transaccion.categoria for transaccion in self.transacciones]))

            # Crea una nueva ventana para mostrar los gastos por categoría
            new_window = Toplevel(self.root)
            new_window.title("Ver gastos por categoría")
            new_window.geometry('300x300')  # Hace la ventana más grande
            new_window.configure(bg='#2c3e50')  # Color de fondo

            # Crea un marco con una barra de desplazamiento
            frame = tk.Frame(new_window)
            frame.pack(fill='both', expand=True)
            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side='right', fill='y')

            # Crea un widget Text dentro del marco para mostrar los gastos por categoría
            text = tk.Text(frame, wrap='word', yscrollcommand=scrollbar.set)
            text.pack(fill='both', expand=True)
            scrollbar.config(command=text.yview)

            # Agrega los gastos por categoría al widget Text
            for categoria in categorias:
                gastos = [t.cantidad for t in self.transacciones if t.categoria == categoria and t.cantidad < 0]
                total = sum(gastos)
                total_formateado = "{:,.0f}".format(total).replace(",", ".")  # Formatea el total sin decimales y con separador de miles
                text.insert('end', f"Categoría: {categoria}\nTotal gastado: {total_formateado}\n\n")

            # Agrega los botones
            tk.Button(new_window, text="Recordatorios de pago", command=self.ver_recordatorios_de_pago, bg='light green').pack(side='left')  # Botón de color verde claro
            tk.Button(new_window, text="Objetivos de ahorro", command=self.ver_objetivos_de_ahorro, bg='light green').pack(side='left')  # Botón de color verde claro
            tk.Button(new_window, text="Exit", command=new_window.destroy, bg='light green').pack(side='right')  # Botón de color verde claro
            logger.info("Gastos por categoría mostrados exitosamente.")
        except Exception as e:
            logger.error("Error en ver_gastos_por_categoria: " + str(e))

    def ver_recordatorios_de_pago(self):
        # Recarga los recordatorios de la base de datos
        self.cargar_recordatorios()

        new_window = Toplevel(self.root)
        new_window.title("Recordatorios de pago")
        new_window.geometry('500x300')
        new_window.configure(bg='#2c3e50')

        tabla = ttk.Treeview(new_window, columns=('Nombre del pago', 'Monto', 'Cuotas', 'Cuotas pagadas', 'Próximo vencimiento'), show='headings')
        tabla.column('Nombre del pago', width=100)
        tabla.column('Monto', width=100)
        tabla.column('Cuotas', width=100)
        tabla.column('Cuotas pagadas', width=100)
        tabla.column('Próximo vencimiento', width=100)
        tabla.heading('Nombre del pago', text='Nombre del pago')
        tabla.heading('Monto', text='Monto')
        tabla.heading('Cuotas', text='Cuotas')
        tabla.heading('Cuotas pagadas', text='Cuotas pagadas')
        tabla.heading('Próximo vencimiento', text='Próximo vencimiento')
        tabla.pack()

        # Llena la tabla con los datos de los recordatorios de pago
        for recordatorio in self.recordatorios:
            proximo_vencimiento = recordatorio.fechas_vencimiento[recordatorio.cuotas_pagadas] if recordatorio.cuotas_pagadas < recordatorio.cuotas else 'N/A'
            tabla.insert('', 'end', values=(recordatorio.nombre, recordatorio.monto, recordatorio.cuotas, recordatorio.cuotas_pagadas, proximo_vencimiento))

        # Agrega un botón para agregar un nuevo recordatorio de pago
        tk.Button(new_window, text="Agregar recordatorio", command=self.agregar_recordatorio, bg='light green').pack(side='left')

        # Agrega un botón para agregar un nuevo recordatorio de pago
        tk.Button(new_window, text="Agregar recordatorio", command=self.agregar_recordatorio, bg='light green').pack(side='left')

        # Agrega un botón para eliminar un recordatorio de pago
        tk.Button(new_window, text="Eliminar recordatorio", command=lambda: self.eliminar_recordatorio(tabla.item(tabla.selection())['values'][0], tabla), bg='light green').pack(side='left')

        # Agrega un botón para editar un recordatorio de pago
        tk.Button(new_window, text="Editar recordatorio", command=lambda: self.editar_recordatorio(tabla.item(tabla.selection())['values'][0]), bg='light green').pack(side='left')

        # Agrega un botón para registrar un pago
        tk.Button(new_window, text="Registrar pago", command=lambda: self.registrar_pago(tabla.item(tabla.selection())['values'][0]), bg='light green').pack(side='left')

    def ver_objetivos_de_ahorro(self):
        # Abre una nueva ventana y muestra los objetivos de ahorro
        new_window = Toplevel(self.root)
        new_window.title("Objetivos de ahorro")
        new_window.geometry('300x300')
        new_window.configure(bg='#2c3e50')  # Color de fondo

        # Aquí puedes agregar el código para mostrar los objetivos de ahorro
        # Por ejemplo, podrías mostrar una lista de los objetivos de ahorro y el progreso hacia cada uno

    def calcular_gasto_diario(self):
        try:
            logger.info("Calculando el gasto diario...")
            # Solicitar la fecha límite al usuario
            fecha_limite_str = simpledialog.askstring("Fecha límite", "Ingresa la fecha límite (dd-mm-yyyy o dd/mm/yyyy):")

            # Reemplazar "/" por "-" en la fecha límite
            fecha_limite_str = fecha_limite_str.replace("/", "-")

            # Convertir la fecha límite a un objeto datetime
            self.fecha_limite = datetime.strptime(fecha_limite_str, "%d-%m-%Y")

            # Guardar la fecha límite en la base de datos
            self.c.execute("DELETE FROM fecha_limite")
            self.c.execute("INSERT INTO fecha_limite VALUES (?)", (self.fecha_limite.strftime("%Y-%m-%d"),))
            self.conn.commit()

            # Calcular el número de días hasta la fecha límite
            dias_hasta_fecha_limite = (self.fecha_limite.date() - datetime.today().date()).days

            # Calcular el gasto diario
            gasto_diario = self.saldo() / dias_hasta_fecha_limite

            # Actualizar la etiqueta con el gasto diario y los días restantes
            self.gasto_diario_var.set("Gasto diario hasta " + self.fecha_limite.strftime("%Y-%m-%d") + ": " + "{:,.0f}".format(int(gasto_diario)).replace(",", ".") + " | Días restantes: " + str(dias_hasta_fecha_limite))
            tk.Label(self.root, textvariable=self.gasto_diario_var, bg='green', fg='#ecf0f1').grid(row=6, column=2, padx=10)  # Etiqueta con fondo verde

            logger.info("Gasto diario actualizado exitosamente.")
        except Exception as e:
            logger.error("Error en actualizar_gasto_diario: " + str(e))

    def eliminar_recordatorio(self, nombre, tabla):
        # Muestra un cuadro de diálogo de confirmación antes de eliminar
        if messagebox.askokcancel("Confirmar eliminación", "¿Estás seguro de que quieres eliminar este recordatorio?"):
            # Encuentra el recordatorio con el nombre dado y lo elimina
            self.recordatorios = [r for r in self.recordatorios if r.nombre != nombre]
            # También debes eliminar el recordatorio de la base de datos
            self.c.execute("DELETE FROM recordatorios WHERE nombre = ?", (nombre,))
            self.conn.commit()

            # Actualiza la tabla
            self.actualizar_tabla(tabla)

    def actualizar_tabla(self, tabla):
        # Limpia la tabla
        for i in tabla.get_children():
            tabla.delete(i)

        # Llena la tabla con los datos de los recordatorios de pago
        for recordatorio in self.recordatorios:
            proximo_vencimiento = recordatorio.fechas_vencimiento[recordatorio.cuotas_pagadas] if recordatorio.cuotas_pagadas < recordatorio.cuotas else 'N/A'
            tabla.insert('', 'end', values=(recordatorio.nombre, recordatorio.monto, recordatorio.cuotas, recordatorio.cuotas_pagadas, proximo_vencimiento))

    def editar_recordatorio(self, nombre, nuevo_nombre=None, nuevo_monto=None, nuevas_cuotas=None, nueva_fecha_primer_vencimiento=None):
        # Encuentra el recordatorio con el nombre dado
        for r in self.recordatorios:
            if r.nombre == nombre:
                # Actualiza los campos del recordatorio
                if nuevo_nombre is not None:
                    r.nombre = nuevo_nombre
                if nuevo_monto is not None:
                    r.monto = nuevo_monto
                if nuevas_cuotas is not None:
                    r.cuotas = nuevas_cuotas
                if nueva_fecha_primer_vencimiento is not None:
                    r.fecha_primer_vencimiento = nueva_fecha_primer_vencimiento
                    r.fechas_vencimiento = [r.fecha_primer_vencimiento + relativedelta(months=i) for i in range(r.cuotas)]
                # Actualiza el recordatorio en la base de datos
                self.c.execute("UPDATE recordatorios SET nombre = ?, monto = ?, cuotas = ?, fecha_primer_vencimiento = ? WHERE nombre = ?",
                           (r.nombre, r.monto, r.cuotas, r.fecha_primer_vencimiento.strftime("%Y-%m-%d"), nombre))
                self.conn.commit()
                break

    def registrar_pago(self, nombre):
        # Encuentra el recordatorio con el nombre dado
        for r in self.recordatorios:
            if r.nombre == nombre:
                # Incrementa el número de cuotas pagadas
                r.cuotas_pagadas += 1
                # También debes actualizar el recordatorio en la base de datos
                self.c.execute("UPDATE recordatorios SET cuotas_pagadas = ? WHERE nombre = ?", (r.cuotas_pagadas, nombre))
                self.conn.commit()
                break

    def exportar_a_excel(self):
        try:
            logger.info("Exportando a Excel...")
            # Crear un DataFrame de pandas a partir de las transacciones
            df = pd.DataFrame([(t.categoria, t.cantidad, t.hora) for t in self.transacciones], columns=['Categoria', 'Cantidad', 'Hora'])

            # Exportar el DataFrame a un archivo de Excel
            df.to_excel('Transacciones.xlsx', index=False)
            
            # Mostrar un mensaje de éxito
            messagebox.showinfo("Exportación a Excel", "Exportación a Excel realizada exitosamente.")
            
            logger.info("Exportación a Excel realizada exitosamente.")
        except Exception as e:
            logger.error("Error en exportar_a_excel: " + str(e))

# Iniciar la interfaz gráfica de usuario
try:
    logger.info("Iniciando la interfaz gráfica de usuario...")
    root = tk.Tk()
    app = AplicacionDeGastos(root)
    root.mainloop()
    logger.info("Interfaz gráfica de usuario iniciada exitosamente.")
except Exception as e:
    logger.error("Error al iniciar la interfaz gráfica de usuario: " + str(e))
