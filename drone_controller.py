import requests
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import os
import serial
import threading
import struct
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('drone_flight.log'),
        logging.StreamHandler()
    ]
)

class MSPProtocol:
    """Класс для работы с MSP (MultiWii Serial Protocol)"""
    
    # MSP команды
    MSP_SET_RAW_RC = 200
    MSP_ARM = 210
    MSP_DISARM = 211
    MSP_SET_RAW_GPS = 201
    MSP_NAV_POSHOLD = 216
    
    def __init__(self, serial_port, baudrate=115200):
        """Инициализация MSP протокола с указанным COM-портом"""
        self.serial = serial.Serial(serial_port, baudrate, timeout=1)
        logging.info(f"MSP соединение установлено на порту {serial_port}")
    
    def _calculate_checksum(self, data):
        """Расчет контрольной суммы для MSP пакета"""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum
    
    def send_command(self, command, data=None):
        """Отправка MSP команды"""
        if data is None:
            data = []
        
        size = len(data)
        
        # Формирование пакета
        packet = bytearray()
        packet.extend(b'$M<')  # MSP заголовок (направление к FC)
        packet.append(size)
        packet.append(command)
        
        # Добавление данных
        if size > 0:
            packet.extend(data)
        
        # Расчет и добавление контрольной суммы
        checksum = self._calculate_checksum(packet[3:])
        packet.append(checksum)
        
        # Отправка пакета
        self.serial.write(packet)
        logging.debug(f"Отправлена MSP команда: {command}, данные: {data}")
        
        # Ожидание ответа
        time.sleep(0.05)
        
        # Чтение ответа (не всегда необходимо)
        if self.serial.in_waiting:
            response = self.serial.read(self.serial.in_waiting)
            logging.debug(f"Получен ответ: {response}")
            return response
        return None
    
    def set_rc_channels(self, roll, pitch, throttle, yaw, aux1=1000, aux2=1000, aux3=1000, aux4=1000):
        """Установка значений RC каналов"""
        data = bytearray()
        channels = [roll, pitch, throttle, yaw, aux1, aux2, aux3, aux4]
        for channel in channels:
            data.extend(struct.pack('<H', channel))  # little-endian unsigned short
        
        logging.info(f"Установка RC каналов: Roll={roll}, Pitch={pitch}, Throttle={throttle}, Yaw={yaw}")
        return self.send_command(self.MSP_SET_RAW_RC, data)
    
    def arm(self):
        """Включение моторов (ARM)"""
        logging.info("Включение моторов (ARM)")
        return self.send_command(self.MSP_ARM)
    
    def disarm(self):
        """Выключение моторов (DISARM)"""
        logging.info("Выключение моторов (DISARM)")
        return self.send_command(self.MSP_DISARM)
    
    def set_position_hold(self):
        """Включение режима удержания позиции"""
        logging.info("Включение режима удержания позиции")
        return self.send_command(self.MSP_NAV_POSHOLD)
    
    def set_gps_position(self, lat, lon, alt, ground_speed):
        """Установка GPS координат"""
        data = bytearray()
        data.extend(struct.pack('<B', 3))  # Fix type (3D fix)
        data.extend(struct.pack('<B', 8))  # Number of satellites
        data.extend(struct.pack('<l', int(lat * 10000000)))  # Latitude
        data.extend(struct.pack('<l', int(lon * 10000000)))  # Longitude
        data.extend(struct.pack('<H', int(alt * 100)))  # Altitude in cm
        data.extend(struct.pack('<H', int(ground_speed * 100)))  # Ground speed in cm/s
        
        logging.info(f"Установка GPS координат: Lat={lat}, Lon={lon}, Alt={alt}")
        return self.send_command(self.MSP_SET_RAW_GPS, data)
    
    def close(self):
        """Закрытие соединения"""
        if self.serial.is_open:
            self.serial.close()
            logging.info("MSP соединение закрыто")

class DroneController:
    def __init__(self, base_url, api_key, serial_port=None):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.current_position = {"x": 0, "y": 0, "z": 0}
        self.current_heading = 0
        
        # Инициализация MSP соединения, если указан порт
        self.msp = None
        if serial_port:
            try:
                self.msp = MSPProtocol(serial_port)
                logging.info(f"MSP соединение инициализировано на порту {serial_port}")
            except Exception as e:
                logging.error(f"Ошибка инициализации MSP: {str(e)}")
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
        """Выполнение команды взлета"""
        logging.info(f"Начало взлета на высоту {height}м")
        
        if self.msp:
            # Включение моторов
            self.msp.arm()
            time.sleep(1)
            
            # Постепенное увеличение тяги для взлета
            for throttle in range(1000, 1500, 10):
                self.msp.set_rc_channels(1500, 1500, throttle, 1500)
                time.sleep(0.1)
            
            # Удержание высоты на протяжении заданного времени
            for _ in range(20):  # 2 сек на стабилизацию
                self.msp.set_rc_channels(1500, 1500, 1550, 1500)
                time.sleep(0.1)
                
            # Установка целевой высоты (в метрах)
            self.current_position["z"] = height
            logging.info(f"Достигнута высота {height}м")
            return True
        else:
            # Отправка команды через API
            result = self.send_command("takeoff", {"height": height})
            if result:
                self.current_position["z"] = height
            return result

    def move(self, x, y, z):
        """Выполнение команды движения"""
        logging.info(f"Движение к координатам: x={x}, y={y}, z={z}")
        
        if self.msp:
            # Расчет вектора движения относительно текущей позиции
            delta_x = x - self.current_position["x"]
            delta_y = y - self.current_position["y"]
            delta_z = z - self.current_position["z"]
            
            # Нормализация направления движения
            distance = (delta_x**2 + delta_y**2)**0.5
            
            if distance > 0:
                # Определение направления движения (крен и тангаж)
                # Значения RC каналов: 1000-2000, центр: 1500
                roll_value = 1500 + int((delta_x / distance) * 100)
                pitch_value = 1500 + int((delta_y / distance) * 100)
                
                # Ограничение значений
                roll_value = max(1400, min(1600, roll_value))
                pitch_value = max(1400, min(1600, pitch_value))
                
                # Расчет времени движения (примерно)
                move_time = distance * 2  # 2 секунды на 1 метр
                
                # Выполнение движения
                start_time = time.time()
                while time.time() - start_time < move_time:
                    self.msp.set_rc_channels(roll_value, pitch_value, 1500, 1500)
                    time.sleep(0.1)
                
                # Возврат в нейтральное положение
                self.msp.set_rc_channels(1500, 1500, 1500, 1500)
            
            # Обновление текущей позиции
            self.current_position = {"x": x, "y": y, "z": z}
            logging.info(f"Достигнуты координаты: x={x}, y={y}, z={z}")
            return True
        else:
            # Отправка команды через API
            result = self.send_command("move", {"x": x, "y": y, "z": z})
            if result:
                self.current_position = {"x": x, "y": y, "z": z}
            return result

    def rotate(self, degrees):
        """Выполнение команды поворота"""
        logging.info(f"Поворот на {degrees} градусов")
        
        if self.msp:
            # Определение направления поворота
            yaw_value = 1500
            if degrees > 0:  # поворот по часовой стрелке
                yaw_value = 1600
            elif degrees < 0:  # поворот против часовой стрелки
                yaw_value = 1400
            
            # Расчет времени поворота (примерно)
            # 1 секунда на 45 градусов
            rotate_time = abs(degrees) / 45
            
            # Выполнение поворота
            start_time = time.time()
            while time.time() - start_time < rotate_time:
                self.msp.set_rc_channels(1500, 1500, 1500, yaw_value)
                time.sleep(0.1)
            
            # Возврат в нейтральное положение
            self.msp.set_rc_channels(1500, 1500, 1500, 1500)
            
            # Обновление текущего направления
            self.current_heading = (self.current_heading + degrees) % 360
            logging.info(f"Достигнуто направление: {self.current_heading} градусов")
            return True
        else:
            # Отправка команды через API
            result = self.send_command("rotate", {"degrees": degrees})
            if result:
                self.current_heading = (self.current_heading + degrees) % 360
            return result

    def land(self):
        """Выполнение команды посадки"""
        logging.info("Начало процедуры посадки")
        
        if self.msp:
            # Плавное снижение тяги для посадки
            for throttle in range(1500, 1300, -5):
                self.msp.set_rc_channels(1500, 1500, throttle, 1500)
                time.sleep(0.1)
            
            # Ожидание достижения земли (примерно)
            time.sleep(5)
            
            # Выключение моторов
            self.msp.disarm()
            
            # Обновление текущей высоты
            self.current_position["z"] = 0
            logging.info("Посадка завершена")
            return True
        else:
            # Отправка команды через API
            result = self.send_command("land")
            if result:
                self.current_position["z"] = 0
            return result
    
    def close(self):
        """Закрытие всех соединений"""
        if self.msp:
            self.msp.close()

def find_inav_port():
    """Поиск порта, на котором работает INAV"""
    available_ports = []
    for i in range(256):
        try:
            port = f"COM{i}"
            s = serial.Serial(port, 115200, timeout=0.1)
            available_ports.append(port)
            s.close()
        except (OSError, serial.SerialException):
            pass
    
    if available_ports:
        logging.info(f"Найдены следующие COM-порты: {', '.join(available_ports)}")
        # Если есть несколько портов, предложим выбрать
        if len(available_ports) > 1:
            print("Найдено несколько COM-портов:")
            for i, port in enumerate(available_ports):
                print(f"{i+1}. {port}")
            try:
                choice = int(input("Выберите номер порта для подключения к INAV: "))
                if 1 <= choice <= len(available_ports):
                    return available_ports[choice-1]
            except ValueError:
                pass
        return available_ports[0]
    else:
        logging.warning("COM-порты не найдены. INAV не будет использоваться.")
        return None

def main():
    # Загрузка переменных окружения
    load_dotenv()
    
    # Получение учетных данных API из переменных окружения
    base_url = os.getenv("DRONE_API_URL", "http://simworld.agrotechsim.com:8080/api")
    api_key = os.getenv("DRONE_API_KEY", "YOURAPIKEY")
    
    # Поиск COM-порта для INAV
    inav_port = find_inav_port()
    
    # Инициализация контроллера дрона
    try:
        drone = DroneController(base_url, api_key, inav_port)
    except Exception as e:
        logging.error(f"Ошибка инициализации контроллера дрона: {str(e)}")
        return

    try:
        # Выполнение последовательности полета
        logging.info("Начало последовательности полета")
        
        # 1. Взлет
        if not drone.takeoff(height=10):
            raise Exception("Ошибка взлета")
        
        # Пауза для стабилизации после взлета
        time.sleep(3)
        
        # 2. Движение вперед
        if not drone.move(x=50, y=0, z=10):
            raise Exception("Ошибка движения вперед")
        
        # Пауза для стабилизации после движения
        time.sleep(2)
        
        # 3. Поворот на 180 градусов
        if not drone.rotate(degrees=180):
            raise Exception("Ошибка поворота")
        
        # Пауза для стабилизации после поворота
        time.sleep(2)
        
        # 4. Посадка
        if not drone.land():
            raise Exception("Ошибка посадки")
        
        logging.info("Последовательность полета успешно завершена")
        
    except Exception as e:
        logging.error(f"Ошибка в последовательности полета: {str(e)}")
        # Попытка аварийной посадки
        logging.info("Инициация аварийной посадки")
        drone.land()
    finally:
        # Закрытие соединений
        drone.close()

if __name__ == "__main__":
    main() 