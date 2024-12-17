import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from datetime import datetime


class WarehouseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Система управления складом")
        self.root.geometry("1200x800")

        # Подключение к базе данных
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="12345678",
            database="warehouse_db"
        )
        self.cursor = self.db.cursor()

        # Создание таблицы, если она не существует
        self.create_table()

        # Авторизация
        self.show_login()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS warehouse_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_name VARCHAR(100),
                supplier_name VARCHAR(100),
                quantity INT,
                price DECIMAL(10, 2),
                last_delivery DATE,
                last_operation VARCHAR(20),
                last_operation_date DATETIME,
                status VARCHAR(20)
            )
        """)
        self.db.commit()

    def show_login(self):
        self.login_frame = ttk.Frame(self.root)
        self.login_frame.pack(pady=20)

        ttk.Label(self.login_frame, text="Выберите роль:").pack()
        self.role_var = tk.StringVar()
        ttk.Radiobutton(self.login_frame, text="Кладовщик", variable=self.role_var, value="warehouse").pack()
        ttk.Radiobutton(self.login_frame, text="Менеджер", variable=self.role_var, value="manager").pack()
        ttk.Button(self.login_frame, text="Войти", command=self.login).pack(pady=10)

    def login(self):
        role = self.role_var.get()
        if not role:
            messagebox.showerror("Ошибка", "Выберите роль!")
            return

        self.current_role = role
        self.login_frame.destroy()
        self.create_main_interface()

    def create_main_interface(self):
        # Основной фрейм
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Форма ввода
        input_frame = ttk.LabelFrame(main_frame, text="Информация о товаре")
        input_frame.pack(padx=10, pady=5, fill="x")

        # Поля ввода
        ttk.Label(input_frame, text="Название товара:").grid(row=0, column=0, padx=5, pady=5)
        self.product_name = ttk.Entry(input_frame)
        self.product_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Поставщик:").grid(row=0, column=2, padx=5, pady=5)
        self.supplier_name = ttk.Entry(input_frame)
        self.supplier_name.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(input_frame, text="Количество:").grid(row=1, column=0, padx=5, pady=5)
        self.quantity = ttk.Entry(input_frame)
        self.quantity.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Цена:").grid(row=1, column=2, padx=5, pady=5)
        self.price = ttk.Entry(input_frame)
        self.price.grid(row=1, column=3, padx=5, pady=5)

        # Кнопки операций
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=10)

        ttk.Button(btn_frame, text="Добавить товар", command=self.add_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Приход товара", command=lambda: self.update_quantity("in")).pack(side="left",
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Расход товара", command=lambda: self.update_quantity("out")).pack(side="left",
                                                                                                      padx=5)

        if self.current_role == "manager":
            ttk.Button(btn_frame, text="Изменить", command=self.edit_product).pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Удалить", command=self.delete_product).pack(side="left", padx=5)

        # Таблица товаров
        self.tree = ttk.Treeview(main_frame, columns=(
            "ID", "Товар", "Поставщик", "Количество", "Цена",
            "Последняя поставка", "Последняя операция", "Дата операции", "Статус"
        ), show="headings")

        # Настройка заголовков
        headers = ["ID", "Товар", "Поставщик", "Количество", "Цена",
                   "Последняя поставка", "Последняя операция", "Дата операции", "Статус"]

        for i, header in enumerate(headers):
            self.tree.heading(i, text=header)
            self.tree.column(i, width=120)

        self.tree.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # Обновление данных
        self.refresh_data()

    def add_product(self):
        try:
            quantity = int(self.quantity.get())
            price = float(self.price.get())

            query = """
                INSERT INTO warehouse_data (
                    product_name, supplier_name, quantity, price,
                    last_delivery, last_operation, last_operation_date, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                self.product_name.get(),
                self.supplier_name.get(),
                quantity,
                price,
                datetime.now().date(),
                "Поступление",
                datetime.now(),
                "В наличии"
            )

            self.cursor.execute(query, values)
            self.db.commit()
            self.refresh_data()
            self.clear_fields()
            messagebox.showinfo("Успех", "Товар добавлен!")
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте правильность ввода количества и цены!")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def update_quantity(self, operation_type):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите товар!")
            return

        try:
            change_qty = int(self.quantity.get())
            if change_qty <= 0:
                raise ValueError("Количество должно быть положительным числом!")

            item_id = self.tree.item(selected[0])['values'][0]
            current_qty = self.tree.item(selected[0])['values'][3]

            if operation_type == "out" and change_qty > current_qty:
                messagebox.showerror("Ошибка", "Недостаточно товара на складе!")
                return

            new_qty = current_qty + change_qty if operation_type == "in" else current_qty - change_qty
            operation = "Поступление" if operation_type == "in" else "Списание"

            query = """
                UPDATE warehouse_data SET
                    quantity = %s,
                    last_operation = %s,
                    last_operation_date = %s,
                    status = %s
                WHERE id = %s
            """
            values = (
                new_qty,
                operation,
                datetime.now(),
                "В наличии" if new_qty > 0 else "Нет в наличии",
                item_id
            )

            self.cursor.execute(query, values)
            self.db.commit()
            self.refresh_data()
            self.clear_fields()
            messagebox.showinfo("Успех", f"Операция {operation.lower()} выполнена!")
        except ValueError as ve:
            messagebox.showerror("Ошибка", str(ve))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def edit_product(self):
        if self.current_role != "manager":
            messagebox.showerror("Ошибка", "Недостаточно прав!")
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите товар для изменения!")
            return

        try:
            item_id = self.tree.item(selected[0])['values'][0]
            query = """
                UPDATE warehouse_data SET
                    product_name = %s,
                    supplier_name = %s,
                    price = %s
                WHERE id = %s
            """
            values = (
                self.product_name.get(),
                self.supplier_name.get(),
                float(self.price.get()),
                item_id
            )

            self.cursor.execute(query, values)
            self.db.commit()
            self.refresh_data()
            self.clear_fields()
            messagebox.showinfo("Успех", "Данные обновлены!")
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте правильность ввода цены!")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def delete_product(self):
        if self.current_role != "manager":
            messagebox.showerror("Ошибка", "Недостаточно прав!")
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите товар для удаления!")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранный товар?"):
            item_id = self.tree.item(selected[0])['values'][0]
            self.cursor.execute("DELETE FROM warehouse_data WHERE id = %s", (item_id,))
            self.db.commit()
            self.refresh_data()
            self.clear_fields()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0])['values']
        self.clear_fields()

        self.product_name.insert(0, values[1])
        self.supplier_name.insert(0, values[2])
        self.quantity.insert(0, str(values[3]))
        self.price.insert(0, str(values[4]))

    def clear_fields(self):
        self.product_name.delete(0, tk.END)
        self.supplier_name.delete(0, tk.END)
        self.quantity.delete(0, tk.END)
        self.price.delete(0, tk.END)

    def refresh_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.cursor.execute("SELECT * FROM warehouse_data ORDER BY last_operation_date DESC")
        for row in self.cursor.fetchall():
            self.tree.insert("", "end", values=row)


if __name__ == "__main__":
    root = tk.Tk()
    app = WarehouseApp(root)
    root.mainloop()
