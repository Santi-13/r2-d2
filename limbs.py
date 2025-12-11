import serial
import json
import time

# En Linux, el Bluetooth serial suele montarse aquí tras el 'rfcomm bind'
BT_PORT = '/dev/rfcomm0'
BAUD_RATE = 115200

class BodyController:
    def __init__(self):
        self.ser = None
        self.connect()

    def connect(self):
        try:
            print(f"🔌 Conectando Bluetooth en {BT_PORT}...")
            self.ser = serial.Serial(BT_PORT, BAUD_RATE, timeout=1)
            time.sleep(2) # Espera técnica para estabilizar conexión
            print("✅ R2-D2 Bluetooth Conectado.")
        except Exception as e:
            print(f"⚠️ Error Bluetooth: {e}")
            print("   (TIP: ¿Ejecutaste 'sudo rfcomm bind 0 <MAC>'?)")

    def send_command(self, device, action):
        if not self.ser or not self.ser.is_open:
            print("   ⚠️ Intentando reconectar Bluetooth...")
            self.connect()
            if not self.ser: return

        command = {"device": device, "action": action}
        
        try:
            payload = json.dumps(command) + "\n"
            self.ser.write(payload.encode('utf-8'))
        except Exception as e:
            print(f"⚠️ Error enviando datos: {e}")
            # Forzar reconexión en el siguiente intento
            try: self.ser.close()
            except: pass
            self.ser = None

# Instancia Global
controller = BodyController()