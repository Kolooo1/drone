import airsim
import cv2
import numpy as np
import os
import time
import tempfile
import logging
from datetime import datetime

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
    """Класс для управления дроном в симуляторе AirSim"""
    
    def __init__(self):
        """Инициализация и подключение к симулятору"""
        print("Соединение с симулятором...")
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True)
        print("Соединение с симулятором установлено")
        
        print(f"API Control enabled: {self.client.isApiControlEnabled()}")
    
    def takeoff(self, height=10):
        """Взлет дрона на указанную высоту"""
        print("Запуск дрона")
        self.client.armDisarm(True)
        print("Полет в режиме POS_ALT_HOLD с помощью ручных игр, крена и высланья")
        self.client.setMode(airsim.AirMultirotorMode.POS_ALT_HOLD)
        
        time.sleep(1)
        self.client.moveByRollPitchYawThrottleAsync(0, 0, 0, 1, 1)
        time.sleep(2)
        self.client.moveByRollPitchYawThrottleAsync(0, 0, 0, 0.61, 1)
        time.sleep(1)
        
        logging.info(f"Взлет выполнен на высоту примерно {height}м")
        return True
    
    def move_forward_back(self, distance=50, cycles=3):
        """Движение вперед-назад"""
        for i in range(cycles):
            # Движение вперед
            self.client.moveByRollPitchYawThrottleAsync(0.5, 0, 0, 0.61, 1)
            time.sleep(3)
            self.client.moveByRollPitchYawThrottleAsync(0, 0, 0, 0.61, 1)
            time.sleep(1)
            
            # Движение назад
            self.client.moveByRollPitchYawThrottleAsync(-0.5, 0, 0, 0.61, 1)
            time.sleep(3)
            self.client.moveByRollPitchYawThrottleAsync(0, 0, 0, 0.61, 1)
            time.sleep(1)
        
        logging.info(f"Выполнено {cycles} циклов движения вперед-назад")
        return True
    
    def stabilize(self):
        """Переход в режим стабилизации"""
        print("Переход в режим STABILIZE")
        self.client.moveByRollPitchYawThrottleAsync(0, 0, 0, 0.5, 1)
        self.client.setMode(airsim.AirMultirotorMode.STABILIZE)
        time.sleep(5)
        logging.info("Выполнен переход в режим стабилизации")
        return True
    
    def land(self):
        """Посадка дрона"""
        self.client.moveByRollPitchYawThrottleAsync(0, 0, 0, 0, 1)
        print("Disarm дрона")
        self.client.armDisarm(False)
        logging.info("Посадка выполнена успешно")
        return True
    
    def load_waypoints_mission(self):
        """Загрузка миссии с точками маршрута"""
        print("Загрузка полетного задания в дрона...")
        self.client.addWaypointsToMission([
            airsim.Waypoint(1, 105.0204522, 39.6641622, 20, 0, 0, 0, 0),
            airsim.Waypoint(2, 105.0279662, 39.6641101, 20, 0, 0, 0, 0),
            airsim.Waypoint(3, 105.0279511, 39.6652606, 20, 0, 0, 0, 0),
            airsim.Waypoint(4, 105.027765, 39.6652978, 20, 0, 0, 0, 165),
        ])
        time.sleep(5)
        logging.info("Маршрутные точки загружены в дрон")
        return True
    
    def execute_mission(self):
        """Выполнение миссии по точкам"""
        print("Начало выполнения миссии")
        self.client.armDisarm(True)
        self.client.setMode(airsim.AirMultirotorMode.POS_ALT_HOLD)
        time.sleep(1)
        self.client.moveByRollPitchYawThrottleAsync(0, 0, 0, 0.9, 1)
        time.sleep(5)
        self.client.moveByRollPitchYawThrottleAsync(0, 0, 0, 0.71, 1)
        self.client.setMode(airsim.AirMultirotorMode.WP_MODE)
        logging.info("Миссия запущена, дрон движется по маршрутным точкам")
        return True
    
    def close(self):
        """Закрытие соединения с дроном"""
        print("Завершение работы с дроном")
        self.client.armDisarm(False)
        self.client.enableApiControl(False)
        logging.info("Соединение с дроном закрыто")
    
    def capture_image(self, save_folder="images"):
        """Захват изображения с камеры дрона"""
        os.makedirs(save_folder, exist_ok=True)
        
        # Получение изображения
        responses = self.client.simGetImages([
            airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)
        ])
        
        # Сохранение изображения
        if responses:
            img1d = np.fromstring(responses[0].image_data_uint8, dtype=np.uint8)
            img_rgb = img1d.reshape(responses[0].height, responses[0].width, 3)
            filename = os.path.join(save_folder, f"drone_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            cv2.imwrite(filename, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
            logging.info(f"Изображение сохранено: {filename}")
            return filename
        return None

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
        
        # 4. Посадка
        drone.land()
        
        # 5. Загрузка маршрута
        drone.load_waypoints_mission()
        
        # 6. Выполнение миссии
        drone.execute_mission()
        
        # Ожидание действия пользователя
        input("Нажмите Enter для завершения...")
        
        logging.info("Полетная последовательность успешно завершена")
        
    except Exception as e:
        logging.error(f"Ошибка в процессе выполнения полета: {str(e)}")
        # Аварийная посадка
        try:
            drone.client.armDisarm(False)
        except:
            pass
    finally:
        # Закрытие соединения
        drone.close()

if __name__ == "__main__":
    main()
