@tool
class_name FactoryProp
extends StaticBody2D
## CARPISILABILIR OBJELERIN ORTAK TEMELI
## Kutu, varil, masa, makine, raf ve duvarlar bu sinifi "extends" eder.
## Oyun calisinca carpisma seklini (collision) otomatik olusturur;
## boylece her objenin sahnesinde ayri ayri sekil ayarlamak gerekmez.
##
## Not: (0, 0) noktasi objenin yere degdigi ON-ALT kenarin ortasidir.
## Bu sayede oyuncu objenin arkasina gecince obje oyuncunun onunde cizilir.


func _ready() -> void:
	if Engine.is_editor_hint():
		return
	collision_layer = 1
	collision_mask = 0
	var shape := _make_shape()
	if shape == null:
		return
	var collision := CollisionShape2D.new()
	collision.shape = shape
	collision.position = _shape_offset()
	add_child(collision)


## Objenin yerde kapladigi alan. Alt siniflar bunu degistirir.
func _footprint() -> Rect2:
	return Rect2(-16, -16, 32, 32)


func _make_shape() -> Shape2D:
	var rect_shape := RectangleShape2D.new()
	rect_shape.size = _footprint().size
	return rect_shape


func _shape_offset() -> Vector2:
	return _footprint().get_center()
