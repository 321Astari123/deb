import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from datetime import datetime, timedelta
import os


class RestaurantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Система управления рестораном")
        self.root.geometry("800x600")

        # Подключение к базе данных
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="12345678",
            database="restaurant_db"
        )
        self.cursor = self.db.cursor()

        # Создание таблицы, если она не существует
        self.create_table()

        # Создание интерфейса
        self.create_gui()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS restaurant_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                client_name VARCHAR(100),
                menu_items TEXT,
                order_total DECIMAL(10, 2),
                order_date DATETIME,
                status VARCHAR(20)
            )
        """)
        self.db.commit()

    def create_gui(self):
        # Фрейм для авторизации
        self.auth_frame = ttk.Frame(self.root)
        self.auth_frame.pack(pady=20)

        ttk.Label(self.auth_frame, text="Выберите роль:").pack()
        self.role_var = tk.StringVar()
        ttk.Radiobutton(self.auth_frame, text="Кассир", variable=self.role_var, value="cashier").pack()
        ttk.Radiobutton(self.auth_frame, text="Администратор", variable=self.role_var, value="admin").pack()
        ttk.Button(self.auth_frame, text="Войти", command=self.login).pack(pady=10)

        # Основной фрейм (скрыт до авторизации)
        self.main_frame = ttk.Frame(self.root)

        # Фрейм для добавления заказа
        order_frame = ttk.LabelFrame(self.main_frame, text="Новый заказ")
        order_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(order_frame, text="Имя клиента:").grid(row=0, column=0, padx=5, pady=5)
        self.client_name = ttk.Entry(order_frame)
        self.client_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(order_frame, text="Заказ (через запятую):").grid(row=1, column=0, padx=5, pady=5)
        self.menu_items = ttk.Entry(order_frame)
        self.menu_items.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(order_frame, text="Сумма:").grid(row=2, column=0, padx=5, pady=5)
        self.order_total = ttk.Entry(order_frame)
        self.order_total.grid(row=2, column=1, padx=5, pady=5)

        ttk.Button(order_frame, text="Добавить заказ", command=self.add_order).grid(row=3, column=0, columnspan=2,
                                                                                    pady=10)

        # Таблица заказов
        self.tree = ttk.Treeview(self.main_frame, columns=("ID", "Клиент", "Заказ", "Сумма", "Дата", "Статус"),
                                 show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Клиент", text="Клиент")
        self.tree.heading("Заказ", text="Заказ")
        self.tree.heading("Сумма", text="Сумма")
        self.tree.heading("Дата", text="Дата")
        self.tree.heading("Статус", text="Статус")
        self.tree.pack(padx=10, pady=5, fill="both", expand=True)

        # Кнопки управления
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Удалить заказ", command=self.delete_order).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Изменить статус", command=self.change_status).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отчет за день", command=lambda: self.generate_report("day")).pack(side="left",
                                                                                                      padx=5)
        ttk.Button(btn_frame, text="Отчет за месяц", command=lambda: self.generate_report("month")).pack(side="left",
                                                                                                         padx=5)
        ttk.Button(btn_frame, text="Отчет за год", command=lambda: self.generate_report("year")).pack(side="left",
                                                                                                      padx=5)

    def login(self):
        role = self.role_var.get()
        if not role:
            messagebox.showerror("Ошибка", "Выберите роль!")
            return

        self.auth_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.current_role = role
        self.refresh_orders()

    def add_order(self):
        client = self.client_name.get()
        items = self.menu_items.get()
        total = self.order_total.get()

        if not all([client, items, total]):
            messagebox.showerror("Ошибка", "Заполните все поля!")
            return

        try:
            total = float(total)
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат суммы!")
            return

        query = "INSERT INTO restaurant_data (client_name, menu_items, order_total, order_date, status) VALUES (%s, %s, %s, %s, %s)"
        values = (client, items, total, datetime.now(), "Новый")
        self.cursor.execute(query, values)
        self.db.commit()

        self.client_name.delete(0, tk.END)
        self.menu_items.delete(0, tk.END)
        self.order_total.delete(0, tk.END)
        self.refresh_orders()

    def delete_order(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите заказ для удаления!")
            return

        if self.current_role != "admin":
            messagebox.showerror("Ошибка", "Только администратор может удалять заказы!")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранный заказ?"):
            order_id = self.tree.item(selected[0])['values'][0]
            self.cursor.execute("DELETE FROM restaurant_data WHERE id = %s", (order_id,))
            self.db.commit()
            self.refresh_orders()

    def change_status(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите заказ!")
            return

        order_id = self.tree.item(selected[0])['values'][0]
        self.cursor.execute("UPDATE restaurant_data SET status = 'Выполнен' WHERE id = %s", (order_id,))
        self.db.commit()
        self.refresh_orders()

    def generate_report(self, period):
        if self.current_role != "admin":
            messagebox.showerror("Ошибка", "Только администратор может генерировать отчеты!")
            return

        now = datetime.now()
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            title = f"Отчет за {now.strftime('%d.%m.%Y')}"
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            title = f"Отчет за {now.strftime('%m.%Y')}"
        else:  # year
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            title = f"Отчет за {now.year} год"

        self.cursor.execute("""
            SELECT SUM(order_total), COUNT(*) 
            FROM restaurant_data 
            WHERE order_date >= %s AND order_date <= %s
        """, (start_date, now))

        total_sum, total_orders = self.cursor.fetchone()

        if not total_sum:
            total_sum = 0
            total_orders = 0

        report_path = f"report_{period}_{now.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"{title}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Количество заказов: {total_orders}\n")
            f.write(f"Общая выручка: {total_sum:.2f} руб.\n")
            f.write(f"Дата формирования: {now.strftime('%d.%m.%Y %H:%M:%S')}\n")

        messagebox.showinfo("Успех", f"Отчет сохранен в файл: {report_path}")

    def refresh_orders(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.cursor.execute("SELECT * FROM restaurant_data ORDER BY order_date DESC")
        for row in self.cursor.fetchall():
            self.tree.insert("", "end", values=row)


if __name__ == "__main__":
    root = tk.Tk()
    app = RestaurantApp(root)
    root.mainloop()
