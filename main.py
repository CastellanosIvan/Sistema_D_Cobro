import sys
from decimal import Decimal

from db_manager import DBManager

from PyQt6.QtWidgets import (
    QApplication, QWidget, QComboBox, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QMessageBox, QGroupBox, QRadioButton, QHeaderView
)
from PyQt6.QtCore import Qt


# ----------------- Interfaz gráfica con PyQt6 ----------------- #

class POSBar(QWidget):
    def __init__(self):
        super().__init__()

        # Conexión a BD
        try:
            self.db = DBManager()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            sys.exit(1)

        self.setWindowTitle("Punto de Venta - Restaurante/Bar")
        self.resize(1000, 600)

        # Datos en memoria para el ticket actual
        # Lista de dicts: {producto_id, nombre, cantidad, precio_unitario, subtotal}
        self.items_ticket = []

        # Mapeos para categorías
        self.categorias = []  # lista de dicts de la BD
        self.mapa_categoria_index_id = {}  # index -> id

        # Crear UI
        self.crear_widgets()
        self.crear_layouts()
        self.conectar_senales()

        # Cargar datos iniciales
        self.cargar_categorias()

    # ---------- Creación de widgets ---------- #

    def crear_widgets(self):
        # Combobox de categorías
        self.combo_categorias = QComboBox()

        # Lista de productos
        self.lista_productos = QListWidget()

        # Tabla para el ticket
        self.tabla_ticket = QTableWidget(0, 4)
        self.tabla_ticket.setHorizontalHeaderLabels(["Producto", "Cant.", "P. Unitario", "Subtotal"])
        header = self.tabla_ticket.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        # Label de total
        self.label_total = QLabel("Total: $0.00")
        self.label_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.label_total.setStyleSheet("font-size: 18px; font-weight: bold;")

        # Botones de acciones
        self.boton_eliminar_linea = QPushButton("Eliminar línea")
        self.boton_vaciar = QPushButton("Vaciar ticket")
        self.boton_cobrar = QPushButton("Cobrar")

        # Grupo de método de pago
        self.grupo_pago = QGroupBox("Método de pago")
        self.radio_efectivo = QRadioButton("Efectivo")
        self.radio_tarjeta = QRadioButton("Tarjeta")
        self.radio_otro = QRadioButton("Otro")
        self.radio_efectivo.setChecked(True)

        layout_pago = QVBoxLayout()
        layout_pago.addWidget(self.radio_efectivo)
        layout_pago.addWidget(self.radio_tarjeta)
        layout_pago.addWidget(self.radio_otro)
        self.grupo_pago.setLayout(layout_pago)

    # ---------- Layouts ---------- #

    def crear_layouts(self):
        # Columna izquierda: categoría + productos
        layout_izquierdo = QVBoxLayout()
        layout_izquierdo.addWidget(QLabel("Categoría:"))
        layout_izquierdo.addWidget(self.combo_categorias)
        layout_izquierdo.addWidget(QLabel("Productos:"))
        layout_izquierdo.addWidget(self.lista_productos)

        # Columna derecha: ticket + total + botones + método de pago
        layout_derecho = QVBoxLayout()
        layout_derecho.addWidget(QLabel("Ticket actual:"))
        layout_derecho.addWidget(self.tabla_ticket)
        layout_derecho.addWidget(self.label_total)

        layout_botones = QHBoxLayout()
        layout_botones.addWidget(self.boton_eliminar_linea)
        layout_botones.addWidget(self.boton_vaciar)
        layout_botones.addWidget(self.boton_cobrar)

        layout_derecho.addLayout(layout_botones)
        layout_derecho.addWidget(self.grupo_pago)

        # Layout principal
        layout_principal = QHBoxLayout()
        layout_principal.addLayout(layout_izquierdo, 1)
        layout_principal.addLayout(layout_derecho, 2)

        self.setLayout(layout_principal)

    # ---------- Señales ---------- #

    def conectar_senales(self):
        self.combo_categorias.currentIndexChanged.connect(self.categoria_cambiada)
        self.lista_productos.itemDoubleClicked.connect(self.agregar_producto_al_ticket)
        self.boton_eliminar_linea.clicked.connect(self.eliminar_linea_seleccionada)
        self.boton_vaciar.clicked.connect(self.vaciar_ticket)
        self.boton_cobrar.clicked.connect(self.cobrar)

    # ---------- Lógica de negocio ---------- #

    def cargar_categorias(self):
        self.categorias = self.db.obtener_categorias()
        self.combo_categorias.clear()
        self.mapa_categoria_index_id.clear()

        for index, cat in enumerate(self.categorias):
            self.combo_categorias.addItem(cat["nombre"])
            self.mapa_categoria_index_id[index] = cat["id"]

        if self.categorias:
            self.combo_categorias.setCurrentIndex(0)
            self.cargar_productos()

    def categoria_cambiada(self, index):
        self.cargar_productos()

    def cargar_productos(self):
        index = self.combo_categorias.currentIndex()
        if index < 0:
            return

        categoria_id = self.mapa_categoria_index_id.get(index)
        productos = self.db.obtener_productos_por_categoria(categoria_id)

        self.lista_productos.clear()
        for prod in productos:
            texto = f"{prod['nombre']} - ${prod['precio']:.2f}"
            item = ProductListItem(texto, prod["id"], prod["nombre"], prod["precio"])
            self.lista_productos.addItem(item)

    def agregar_producto_al_ticket(self, item):
        """
        item: ProductListItem (QListWidgetItem extendido)
        """
        producto_id = item.producto_id
        nombre = item.nombre
        precio_unitario = Decimal(str(item.precio))

        # Buscar si ya está en el ticket
        for it in self.items_ticket:
            if it["producto_id"] == producto_id:
                it["cantidad"] += 1
                it["subtotal"] = it["cantidad"] * it["precio_unitario"]
                self.actualizar_tabla()
                self.actualizar_total()
                return

        # Si no está, lo agregamos nuevo
        nuevo = {
            "producto_id": producto_id,
            "nombre": nombre,
            "cantidad": 1,
            "precio_unitario": precio_unitario,
            "subtotal": precio_unitario
        }
        self.items_ticket.append(nuevo)
        self.actualizar_tabla()
        self.actualizar_total()

    def actualizar_tabla(self):
        self.tabla_ticket.setRowCount(0)
        for it in self.items_ticket:
            row = self.tabla_ticket.rowCount()
            self.tabla_ticket.insertRow(row)

            # Producto
            self.tabla_ticket.setItem(row, 0, QTableWidgetItem(it["nombre"]))
            # Cantidad
            self.tabla_ticket.setItem(row, 1, QTableWidgetItem(str(it["cantidad"])))
            # Precio unitario
            self.tabla_ticket.setItem(row, 2, QTableWidgetItem(f"{it['precio_unitario']:.2f}"))
            # Subtotal
            self.tabla_ticket.setItem(row, 3, QTableWidgetItem(f"{it['subtotal']:.2f}"))

    def actualizar_total(self):
        total = sum(it["subtotal"] for it in self.items_ticket)
        self.label_total.setText(f"Total: ${total:.2f}")

    def eliminar_linea_seleccionada(self):
        row = self.tabla_ticket.currentRow()
        if row < 0:
            QMessageBox.information(self, "Aviso", "Selecciona una línea del ticket para eliminar.")
            return

        if 0 <= row < len(self.items_ticket):
            self.items_ticket.pop(row)

        self.actualizar_tabla()
        self.actualizar_total()

    def vaciar_ticket(self):
        self.items_ticket = []
        self.actualizar_tabla()
        self.actualizar_total()

    def obtener_metodo_pago(self):
        if self.radio_efectivo.isChecked():
            return "EFECTIVO"
        elif self.radio_tarjeta.isChecked():
            return "TARJETA"
        else:
            return "OTRO"

    def cobrar(self):
        if not self.items_ticket:
            QMessageBox.information(self, "Sin productos", "Agrega productos al ticket antes de cobrar.")
            return

        metodo_pago = self.obtener_metodo_pago()
        total = sum(it["subtotal"] for it in self.items_ticket)

        respuesta = QMessageBox.question(
            self,
            "Confirmar cobro",
            f"Total a cobrar: ${total:.2f}\n\n¿Deseas continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta != QMessageBox.StandardButton.Yes:
            return

        try:
            pedido_id = self.db.insertar_pedido(self.items_ticket, metodo_pago)
            QMessageBox.information(
                self,
                "Cobro realizado",
                f"Pedido #{pedido_id} guardado correctamente.\nTotal: ${total:.2f}"
            )
            self.vaciar_ticket()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# Clase auxiliar para guardar info extra en cada item de la lista de productos
class ProductListItem(QListWidgetItem):
    def __init__(self, texto, producto_id, nombre, precio):
        super().__init__(texto)
        self.producto_id = producto_id
        self.nombre = nombre
        self.precio = Decimal(str(precio))


def main():
    app = QApplication(sys.argv)
    ventana = POSBar()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
