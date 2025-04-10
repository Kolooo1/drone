import requests
import time
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

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
    """Класс для управления дроном в симуляторе AgroTechSim SimWorld"""
    
    def __init__(self, base_url=None, api_key=None):
        """Инициализация и подключение к симулятору"""
        # Загрузка переменных окружения если не указаны явно
        if base_url is None or api_key is None:
            load_dotenv()
            self.base_url = base_url or os.getenv("DRONE_API_URL", "http://simworld.agrotechsim.com:8080/api")
            api_key = api_key or os.getenv("DRONE_API_KEY", "YOURAPIKEY")
        else:
            self.base_url = base_url
            
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.current_position = {"x": 0, "y": 0, "z": 0}
        self.current_heading = 0
        
        print("Соединение с симулятором...")
        self.check_connection()
        print("Соединение с симулятором установлено")
        
        print(f"API Control enabled: True")
    
    def check_connection(self):
        """Проверка соединения с симулятором"""
        try:
            response = requests.get(f"{self.base_url}/status", headers=self.headers)
            if response.status_code != 200:
                raise Exception(f"Ошибка подключения к симулятору, код: {response.status_code}")
            return True
        except Exception as e:
            logging.error(f"Ошибка при проверке соединения: {str(e)}")
            raise
    
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
        """Взлет дрона на указанную высоту"""
        print("Запуск дрона")
        # Включение моторов
        self.send_command("arm", {"state": True})
        
        print("Полет в режиме удержания высоты")
        # Установка режима полета
        self.send_command("setMode", {"mode": "ALT_HOLD"})
        
        # Взлет на заданную высоту
        result = self.send_command("takeoff", {"height": height})
        if result:
            self.current_position["z"] = height
            logging.info(f"Взлет выполнен на высоту {height}м")
            return True
        return False
    
    def move_forward_back(self, distance=50, cycles=3):
        """Движение вперед-назад"""
        for i in range(cycles):
            # Движение вперед
            forward_pos = self.current_position.copy()
            forward_pos["x"] += distance
            self.send_command("move", forward_pos)
            time.sleep(3)
            
            # Движение назад
            back_pos = self.current_position.copy()
            back_pos["x"] -= distance
            self.send_command("move", back_pos)
            time.sleep(3)
        
        logging.info(f"Выполнено {cycles} циклов движения вперед-назад")
        return True
    
    def stabilize(self):
        """Переход в режим стабилизации"""
        print("Переход в режим STABILIZE")
        result = self.send_command("setMode", {"mode": "STABILIZE"})
        time.sleep(5)
        logging.info("Выполнен переход в режим стабилизации")
        return result
    
    def rotate(self, degrees):
        """Поворот дрона на заданный угол"""
        print(f"Поворот на {degrees} градусов")
        result = self.send_command("rotate", {"degrees": degrees})
        if result:
            self.current_heading = (self.current_heading + degrees) % 360
            logging.info(f"Выполнен поворот на {degrees} градусов")
        return result
    
    def land(self):
        """Посадка дрона"""
        result = self.send_command("land")
        print("Disarm дрона")
        self.send_command("arm", {"state": False})
        if result:
            self.current_position["z"] = 0
            logging.info("Посадка выполнена успешно")
        return result
    
    def load_waypoints_mission(self):
        """Загрузка миссии с точками маршрута"""
        print("Загрузка полетного задания в дрона...")
        waypoints = [
            {"id": 1, "lat": 105.0204522, "lon": 39.6641622, "alt": 20, "heading": 0},
            {"id": 2, "lat": 105.0279662, "lon": 39.6641101, "alt": 20, "heading": 0},
            {"id": 3, "lat": 105.0279511, "lon": 39.6652606, "alt": 20, "heading": 0},
            {"id": 4, "lat": 105.027765, "lon": 39.6652978, "alt": 20, "heading": 165}
        ]
        result = self.send_command("addWaypoints", {"waypoints": waypoints})
        time.sleep(5)
        logging.info("Маршрутные точки загружены в дрон")
        return result
    
    def execute_mission(self):
        """Выполнение миссии по точкам"""
        print("Начало выполнения миссии")
        # Запуск двигателей
        self.send_command("arm", {"state": True})
        
        # Установка режима для удержания высоты
        self.send_command("setMode", {"mode": "ALT_HOLD"})
        time.sleep(1)
        
        # Взлет на рабочую высоту
        self.send_command("takeoff", {"height": 20})
        time.sleep(5)
        
        # Переключение в режим следования по точкам
        result = self.send_command("setMode", {"mode": "WAYPOINT"})
        
        # Начало выполнения миссии
        self.send_command("startMission")
        
        logging.info("Миссия запущена, дрон движется по маршрутным точкам")
        return result
    
    def close(self):
        """Закрытие соединения с дроном"""
        print("Завершение работы с дроном")
        try:
            # Убедимся, что дрон приземлился и моторы выключены
            self.send_command("land")
            self.send_command("arm", {"state": False})
            logging.info("Соединение с дроном закрыто")
        except:
            logging.error("Ошибка при закрытии соединения с дроном")

def main():
    """Основная функция программы"""
    
    drone = DroneController()
    
    try:
        # Выполнение последовательности полета
        logging.info("Начало последовательности полета")
        
        # 1. Взлет
        drone.takeoff()
        
        # 2. Движение вперед-назад
        drone.move_forward_back()
        
        # 3. Стабилизация
        drone.stabilize()
        
        # 4. Разворот на 180 градусов
        drone.rotate(180)
        
        # 5. Посадка
        drone.land()
        
        # 6. Загрузка маршрута
        drone.load_waypoints_mission()
        
        # 7. Выполнение миссии
        drone.execute_mission()
        
        # Ожидание действия пользователя
        input("Нажмите Enter для завершения...")
        
        logging.info("Полетная последовательность успешно завершена")
        
    except Exception as e:
        logging.error(f"Ошибка в процессе выполнения полета: {str(e)}")
        # Аварийная посадка
        try:
            drone.land()
        except:
            pass
    finally:
        # Закрытие соединения
        drone.close()

if __name__ == "__main__":
    main()
