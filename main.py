import os
import signal
import sys
from pypresence import Presence
from PIL import Image
from threading import Thread, Event
from typing import TypedDict
import psutil
from pywinauto import application, WindowSpecification
from pystray import Icon, MenuItem
from pystray._base import Icon as IconType


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Просто для понимания
class InfoData(TypedDict):
    create_time: float
    window: WindowSpecification


# client_id
CLIENT_ID = "1266358210822934559"

# Флаги для управления запуском/остановкой
stop_event = Event()
running = False
process_name = "Mine-imator.exe"

# Создаем объект Presence один раз
rpc = Presence(CLIENT_ID)


def check_discord_status():
    """Проверяет, запущен ли Discord через pypresence."""
    try:
        # Проверка подключения
        rpc.clear()
        return True
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        try:
            rpc.connect()
            print("Успешное подключение к Discord")
            return True
        except:
            return False


def find_window(pid):
    """Поиск окна."""
    try:
        app = application.Application()
        app.connect(process=pid)
        window = app.top_window()
        return window
    except Exception as e:
        print(f"Error: {e}")
        return None


def get_app_info(name):
    """Получение информации окна."""
    info = {}
    for proc in psutil.process_iter():
        if proc.name() == name:
            info["create_time"] = proc.create_time()
            info["window"] = find_window(proc.pid)
            print(f"Процесс {name} найден.")
    if not info:
        print(f"Процесс {name} не найден.")
        return None
    else:
        return info


def get_project_name(title):
    """Получение названия проекта."""
    project_name = title.split(" - ")
    if len(project_name) > 1:
        return project_name[0]
    else:
        return None


def update_status():
    info: InfoData = None
    """Функция для обновления статуса в Discord RPC."""
    global running
    while running:
        if check_discord_status():
            try:
                if not info:
                    info = get_app_info(process_name)
                    if info:
                        rpc.clear()  # Очистка старого статуса

                elif not info["window"].exists():
                    info = get_app_info(process_name)
                    if info:
                        rpc.clear()  # Очистка старого статуса

                else:
                    project_name = get_project_name(info["window"].window_text())

                    if project_name:
                        rpc.update(
                            large_image="mine-imator",
                            details=f"Анимирует {project_name}",
                            start=info["create_time"],
                        )
                    else:
                        rpc.update(
                            large_image="mine-imator",
                            details="Ожидает",
                            start=info["create_time"],
                        )

            except Exception as e:
                print(f"Ошибка обновления статуса: {e}")
        else:
            print("Discord не запущен. Ожидание запуска...")

        # Ждем либо 15 секунд, либо пока не установится stop_event
        stop_event.wait(15)
    try:
        rpc.clear()
    except Exception as e:
        print(f"Ошибка сброса статуса: {e}")


def on_clicked(icon: IconType, item: MenuItem):
    global running

    if item.text == "Запустить":
        on_start()
        print("RPC включен")

    elif item.text == "Остановить":
        running = False
        print("RPC отключен")

    icon.menu = generate_menu()


def on_quit(icon: IconType, item: MenuItem):
    """Завершение работы приложения при закрытии иконки трея."""
    global running
    running = False
    stop_event.set()
    icon.stop()
    print("Приложение остановлено")


def on_start():
    """Запуск обновления статуса."""
    global running
    if not running:
        print("Запуск обновления статуса...")
        running = True
        stop_event.clear()
        Thread(target=update_status, daemon=True).start()
    else:
        print("Обновление статуса уже запущено")


def generate_menu():
    menu = []

    if running:
        menu.append(MenuItem("Активно", None, enabled=False))
        menu.append(MenuItem("Остановить", on_clicked))

    else:
        menu.append(MenuItem("Приостановлено", None, enabled=False))
        menu.append(MenuItem("Запустить", on_clicked))

    menu.append(MenuItem("Выход", on_quit))

    return menu


def ctrl_c_handler(signum, frame):
    print('Для выхода используйте кнопку "Выход" в трее!')


signal.signal(signal.SIGINT, ctrl_c_handler)

if __name__ == "__main__":
    on_start()

    image = Image.open(resource_path("icon.ico"))

    icon = Icon(
        "Mine-Imator RPC", image, "Mine-Imator RPC Status", menu=generate_menu()
    )

    icon.run()
