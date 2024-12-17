import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from datetime import datetime, timedelta
from plyer import notification
import threading
import time


class TransportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Система управления транспортным парком")
        self.root.geometry("1200x800")

        # Подключение к базе данных
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="12345678",
            database="transport_db"
        )
        self.cursor = self.db.cursor()

        # Создание таблицы, если она не существует
        self.create_table()

        # Создание интерфейса
        self.create_gui()

        # Запуск проверки технического обслуживания в отдельном потоке
        self.maintenance_thread = threading.Thread(target=self.check_maintenance, daemon=True)
        self.maintenance_thread.start()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transport_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                driver_name VARCHAR(100),
                vehicle_number VARCHAR(20),
                route_number VARCHAR(20),
                last_maintenance DATE,
                next_maintenance DATE,
                status VARCHAR(20)
            )
        """)
        self.db.commit()

    def create_gui(self):
        # Создание основного фрейма
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Форма добавления/редактирования
        input_frame = ttk.LabelFrame(main_frame, text="Информация о транспорте")
        input_frame.pack(padx=10, pady=5, fill="x")

        # Поля ввода
        ttk.Label(input_frame, text="ФИО водителя:").grid(row=0, column=0, padx=5, pady=5)
        self.driver_name = ttk.Entry(input_frame)
        self.driver_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Номер ТС:").grid(row=1, column=0, padx=5, pady=5)
        self.vehicle_number = ttk.Entry(input_frame)
        self.vehicle_number.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="№ маршрута:").grid(row=2, column=0, padx=5, pady=5)
        self.route_number = ttk.Entry(input_frame)
        self.route_number.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Дата последнего ТО:").grid(row=3, column=0, padx=5, pady=5)
        self.last_maintenance = ttk.Entry(input_frame)
        self.last_maintenance.grid(row=3, column=1, padx=5, pady=5)
        self.last_maintenance.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # Кнопки управления
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Добавить", command=self.add_vehicle).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Изменить", command=self.update_vehicle).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_vehicle).pack(side="left", padx=5)

        # Таблица транспортных средств
        self.tree = ttk.Treeview(main_frame, columns=(
            "ID", "ФИО водителя", "Номер ТС", "№ маршрута",
            "Последнее ТО", "Следующее ТО", "Статус"
        ), show="headings")

        # Настройка заголовков
        headers = ["ID", "ФИО водителя", "Номер ТС", "№ маршрута",
                   "Последнее ТО", "Следующее ТО", "Статус"]

        for i, header in enumerate(headers):
            self.tree.heading(i, text=header)
            self.tree.column(i, width=130)

        self.tree.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # Обновление данных
        self.refresh_data()

    def add_vehicle(self):
        try:
            last_maintenance = datetime.strptime(self.last_maintenance.get(), '%Y-%m-%d')
            next_maintenance = last_maintenance + timedelta(days=30)  # ТО через каждые 30 дней

            query = """
                INSERT INTO transport_data (
                    driver_name, vehicle_number, route_number,
                    last_maintenance, next_maintenance, status
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                self.driver_name.get(),
                self.vehicle_number.get(),
                self.route_number.get(),
                last_maintenance,
                next_maintenance,
                "Активен"
            )

            self.cursor.execute(query, values)
            self.db.commit()
            self.refresh_data()
            self.clear_fields()
            messagebox.showinfo("Успех", "Транспортное средство добавлено!")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def update_vehicle(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите транспортное средство для изменения!")
            return

        try:
            last_maintenance = datetime.strptime(self.last_maintenance.get(), '%Y-%m-%d')
            next_maintenance = last_maintenance + timedelta(days=30)

            vehicle_id = self.tree.item(selected[0])['values'][0]
            query = """
                UPDATE transport_data SET
                    driver_name = %s,
                    vehicle_number = %s,
                    route_number = %s,
                    last_maintenance = %s,
                    next_maintenance = %s
                WHERE id = %s
            """
            values = (
                self.driver_name.get(),
                self.vehicle_number.get(),
                self.route_number.get(),
                last_maintenance,
                next_maintenance,
                vehicle_id
            )

            self.cursor.execute(query, values)
            self.db.commit()
            self.refresh_data()
            self.clear_fields()
            messagebox.showinfo("Успех", "Данные обновлены!")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def delete_vehicle(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите транспортное средство для удаления!")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранное транспортное средство?"):
            vehicle_id = self.tree.item(selected[0])['values'][0]
            self.cursor.execute("DELETE FROM transport_data WHERE id = %s", (vehicle_id,))
            self.db.commit()
            self.refresh_data()
            self.clear_fields()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        # Получение данных выбранной строки
        values = self.tree.item(selected[0])['values']

        # Очистка полей
        self.clear_fields()

        # Заполнение полей данными
        self.driver_name.insert(0, values[1])
        self.vehicle_number.insert(0, values[2])
        self.route_number.insert(0, values[3])
        self.last_maintenance.insert(0, values[4])

    def clear_fields(self):
        self.driver_name.delete(0, tk.END)
        self.vehicle_number.delete(0, tk.END)
        self.route_number.delete(0, tk.END)
        self.last_maintenance.delete(0, tk.END)
        self.last_maintenance.insert(0, datetime.now().strftime('%Y-%m-%d'))

    def refresh_data(self):
        # Очистка таблицы
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Получение данных из БД
        self.cursor.execute("SELECT * FROM transport_data ORDER BY next_maintenance")
        for row in self.cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def check_maintenance(self):
        while True:
            try:
                # Проверка ТС, у которых скоро ТО
                self.cursor.execute("""
                    SELECT vehicle_number, next_maintenance 
                    FROM transport_data 
                    WHERE next_maintenance <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                """)

                for vehicle in self.cursor.fetchall():
                    vehicle_number, maintenance_date = vehicle
                    notification.notify(
                        title='Напоминание о техобслуживании',
                        message=f'ТС {vehicle_number} требует ТО {maintenance_date}',
                        app_icon=None,
                        timeout=10,
                    )
            except Exception as e:
                print(f"Ошибка при проверке ТО: {str(e)}")

            # Проверка каждые 24 часа
            time.sleep(86400)


if __name__ == "__main__":
    root = tk.Tk()
    app = TransportApp(root)
    root.mainloop()
