import pymysql
from decimal import Decimal
from pymysql.cursors import DictCursor


# ----------------- Clase para manejar la base de datos ----------------- #
class DBManager:
    def __init__(self):
        # AJUSTA ESTOS DATOS CON LOS DE TU MARIADB
        self.host = "localhost"
        self.user = "root"
        self.password = "mysql"
        self.database = "bar_pos"

        self.conn = None
        self.conectar()

    def conectar(self):
        try:
            self.conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                cursorclass=DictCursor
            )
        except Exception as e:
            raise Exception(f"No se pudo conectar a la base de datos:\n{e}")

    def obtener_categorias(self):
        query = "SELECT id, nombre FROM categorias ORDER BY nombre;"
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def obtener_productos_por_categoria(self, categoria_id):
        query = """
            SELECT id, nombre, precio
            FROM productos
            WHERE categoria_id = %s AND activo = 1
            ORDER BY nombre;
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (categoria_id,))
            return cursor.fetchall()

    def insertar_pedido(self, items, metodo_pago, observaciones=None):
        """
        items: lista de dicts: {
            'producto_id': int,
            'cantidad': int,
            'precio_unitario': Decimal,
            'subtotal': Decimal
        }
        """
        if not items:
            raise ValueError("No hay items para guardar.")

        total = sum(Decimal(str(item["subtotal"])) for item in items)

        try:
            with self.conn.cursor() as cursor:
                # Insertar pedido
                sql_pedido = """
                    INSERT INTO pedidos (total, metodo_pago, observaciones)
                    VALUES (%s, %s, %s);
                """
                cursor.execute(sql_pedido, (str(total), metodo_pago, observaciones))
                pedido_id = cursor.lastrowid

                # Insertar detalle
                sql_detalle = """
                    INSERT INTO pedido_detalle
                        (pedido_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s);
                """
                for item in items:
                    cursor.execute(
                        sql_detalle,
                        (
                            pedido_id,
                            item["producto_id"],
                            item["cantidad"],
                            str(item["precio_unitario"]),
                            str(item["subtotal"])
                        )
                    )

            self.conn.commit()
            return pedido_id

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Error al guardar el pedido:\n{e}")
