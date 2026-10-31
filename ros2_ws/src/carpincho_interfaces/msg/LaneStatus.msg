# Estado del comportamiento autónomo de carril (carpincho_autonomy/lane_traverse).
std_msgs/Header header
string state                  # IDLE | OUTBOUND | TURN | INBOUND | RECOVER | DONE | ABORT
uint32 traverses_done
float32 distance              # m recorridos en el tramo actual
float32 lateral_error         # m (+ = estamos a la izquierda del centro)
float32 heading_error         # rad
string last_event
