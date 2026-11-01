class_name Player
extends CharacterBody2D
## OYUNCU KARAKTERI
## WASD / ok tuslari ile yumusak (ivmeli) hareket ve kamera takibi.
## Gorunum isi "Visual" dugumundeki player_visual.gd dosyasindadir.

## Saniyede piksel cinsinden en yuksek hiz.
@export var max_speed: float = 280.0
## Ne kadar hizli hizlanir (buyuk sayi = daha cevik).
@export var acceleration: float = 2400.0
## Tus birakilinca ne kadar hizli durur.
@export var friction: float = 2800.0
@export var body_color: Color = Color("ff5d73"):
	set(value):
		body_color = value
		if is_node_ready():
			visual.body_color = value

## false olunca oyuncu tuslara tepki vermez (ornek: duraklatma menusu acikken).
var input_enabled: bool = true

@onready var visual: PlayerVisual = $Visual
@onready var camera: Camera2D = $Camera2D


func _ready() -> void:
	add_to_group("players")
	visual.body_color = body_color


func _physics_process(delta: float) -> void:
	var direction := get_input_direction()
	if direction != Vector2.ZERO:
		velocity = velocity.move_toward(direction * max_speed, acceleration * delta)
	else:
		velocity = velocity.move_toward(Vector2.ZERO, friction * delta)
	move_and_slide()
	visual.update_motion(velocity, max_speed)


## Tuslardan yon bilgisini okur.
## Ayri bir fonksiyon olmasinin sebebi: ileride "ters kontrol" kaos olayi ve
## online oyun (AŞAMA 4-5) sadece burayi degistirerek eklenebilecek.
func get_input_direction() -> Vector2:
	if not input_enabled:
		return Vector2.ZERO
	return Input.get_vector("move_left", "move_right", "move_up", "move_down")


## Kameranin harita disini gostermemesi icin sinirlari ayarlar.
func set_camera_limits(world_rect: Rect2i) -> void:
	camera.limit_left = world_rect.position.x
	camera.limit_top = world_rect.position.y
	camera.limit_right = world_rect.end.x
	camera.limit_bottom = world_rect.end.y
	camera.reset_smoothing()
