# Punto de interés confirmado y ubicado en el mapa (formato del CSV del reglamento RRL).
std_msgs/Header header        # frame = map
uint32 id                     # contador único (también va impreso en el GeoTIFF)
string type                   # ar_code | hazmat_sign | real_object | heat_sig
string name
geometry_msgs/Point position  # m, en el frame del mapa
float32 confidence
string robot
string mode                   # "A" autónomo | "T" teleoperado
builtin_interfaces/Time found
