import requests
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('drone_flight.log'),
        logging.StreamHandler()
    ]
)

class DroneController:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.current_position = {"x": 0, "y": 0, "z": 0}
        self.current_heading = 0

    def send_command(self, command, params=None):
        """Отправка команды в API дрона и логирование результата"""
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/{command}",
                headers=self.headers,
                json=params
            )
            end_time = time.time()
            
            if response.status_code == 200:
                logging.info(f"Команда '{command}' успешно выполнена за {end_time - start_time:.2f} секунд")
                return response.json()
            else:
                logging.error(f"Команда '{command}' не выполнена, код статуса {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Ошибка при выполнении команды '{command}': {str(e)}")
            return None

    def takeoff(self, height=10):
        """Выполнение команды взлета"""
        logging.info(f"Начало взлета на высоту {height}м")
        result = self.send_command("takeoff", {"height": height})
        if result:
            self.current_position["z"] = height
        return result

    def move(self, x, y, z):
        """Выполнение команды движения"""
        logging.info(f"Движение к координатам: x={x}, y={y}, z={z}")
        result = self.send_command("move", {"x": x, "y": y, "z": z})
        if result:
            self.current_position = {"x": x, "y": y, "z": z}
        return result

    def rotate(self, degrees):
        """Выполнение команды поворота"""
        logging.info(f"Поворот на {degrees} градусов")
        result = self.send_command("rotate", {"degrees": degrees})
        if result:
            self.current_heading = (self.current_heading + degrees) % 360
        return result

    def land(self):
        """Выполнение команды посадки"""
        logging.info("Начало процедуры посадки")
        result = self.send_command("land")
        if result:
            self.current_position["z"] = 0
        return result

def main():
    # Загрузка переменных окружения
    load_dotenv()
    
    # Получение учетных данных API из переменных окружения
    base_url = os.getenv("DRONE_API_URL", "http://simworld.agrotechsim.com:8080/api")
    api_key = os.getenv("DRONE_API_KEY", "YOURAPIKEY")

    # Инициализация контроллера дрона
    drone = DroneController(base_url, api_key)

    try:
        # Выполнение последовательности полета
        logging.info("Начало последовательности полета")
        
        # 1. Взлет
        if not drone.takeoff(height=10):
            raise Exception("Ошибка взлета")
        
        # 2. Движение вперед
        if not drone.move(x=50, y=0, z=10):
            raise Exception("Ошибка движения вперед")
        
        # 3. Поворот на 180 градусов
        if not drone.rotate(degrees=180):
            raise Exception("Ошибка поворота")
        
        # 4. Посадка
        if not drone.land():
            raise Exception("Ошибка посадки")
        
        logging.info("Последовательность полета успешно завершена")
        
    except Exception as e:
        logging.error(f"Ошибка в последовательности полета: {str(e)}")
        # Попытка аварийной посадки
        logging.info("Инициация аварийной посадки")
        drone.land()

if __name__ == "__main__":
    main() 