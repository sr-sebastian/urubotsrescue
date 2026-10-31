# Estado de la placa base (ESP32) publicado por carpincho_base/base_bridge.
std_msgs/Header header
float32 battery_voltage       # V
float32 battery_current       # A (positivo = descarga)
float32 battery_percent       # 0..100 estimado por tensión (6S Li-ion)
bool estop_active             # bus de motores sin energía (hongo apretado)
bool motors_enabled           # armado por software
bool flipper_calibrated
bool link_ok                  # llegan tramas válidas del ESP32
uint8 faults                  # bits, ver firmware/include/protocol.h (Fault)
string[] fault_names
float32 hall_mt               # sensor Hall de la punta del brazo (mT)
float32 mcu_temp              # °C
uint16 loop_us_max            # peor tiempo de lazo del firmware
uint32 crc_errors
