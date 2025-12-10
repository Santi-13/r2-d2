import serial
import time
import json
import threading

# Configuración Serial
SERIAL_PORT = '/dev/ttyUSB0' # O '/dev/ttyACM0', verifica con 'ls /dev/tty*'
BAUD_RATE = 115200

class BodyController:
    def __init__(self):
        self.ser = None
        self.is_connected = False
        self.connect()

    def connect(self):
        try:
            print(f"🔌 Conectando con ESP32 en {SERIAL_PORT}...")
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2) # Esperar a que el ESP32 se reinicie tras conectar
            self.is_connected = True
            print("✅ ESP32 Conectado.")
            # Handshake inicial (opcional)
            self.send_command("status", "init")
        except Exception as e:
            print(f"⚠️ Error conectando ESP32: {e}")
            self.is_connected = False

    def send_command(self, device, action, value=0):
        """
        Envía un JSON: {"device": "lights", "action": "blink", "value": 5}
        """
        if not self.is_connected:
            # Intento de reconexión al vuelo
            self.connect()
            if not self.is_connected: return

        command = {
            "device": device,  # 'lights', 'door_front', 'dome'
            "action": action,  # 'on', 'off', 'open', 'close', 'blink'
            "value": value     # Brillo, ángulo, velocidad, etc.
        }
        
        try:
            # Serializamos a JSON y agregamos salto de línea (delimitador)
            payload = json.dumps(command) + "\n"
            self.ser.write(payload.encode('utf-8'))
            # print(f"   >>> TX: {payload.strip()}") # Debug
        except Exception as e:
            print(f"⚠️ Error enviando comando: {e}")
            self.is_connected = False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

# Instancia global para usar en main.py
controller = BodyController()