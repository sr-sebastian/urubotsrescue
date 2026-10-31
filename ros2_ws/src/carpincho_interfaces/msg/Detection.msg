# Una detección en una imagen (QR, hazmat, AprilTag, movimiento, calor...).
std_msgs/Header header        # frame de la cámara que la vio
string type                   # qr_code | hazmat_sign | ar_code | real_object | heat_sig | motion
string name                   # texto del QR, clase hazmat, id del tag, etc.
float32 confidence
int32 x                       # caja en píxeles (esquina superior izquierda)
int32 y
int32 w
int32 h
bool has_position             # true si position es válida (en header.frame_id)
geometry_msgs/Point position
