@tool
class_name FactoryDoor
extends Node2D
## OTOMATIK KAYAR KAPI
## Duvardaki bosluga yerlestirilir. Oyuncu yaklasinca kanatlar iki yana acilir.
## (0, 0) kapinin ortasidir. Dikey duvarlar icin dugumu 90 derece dondurun.
## Kapi oyuncuyu engellemez; sadece gorseldir (AŞAMA 2'de etkilesim gelecek).

@export var width: float = 160.0:
	set(value):
		width = maxf(value, 32.0)
		queue_redraw()
## Duvar kalinligi ile ayni olmali.
@export var thickness: float = 44.0:
	set(value):
		thickness = maxf(value, 8.0)
		queue_redraw()
@export var panel_color: Color = Color("8c93b8"):
	set(value):
		panel_color = value
		queue_redraw()
@export var light_color: Color = Color("59f0a6")

var _open_amount := 0.0
var _bodies_near := 0


func _ready() -> void:
	if Engine.is_editor_hint():
		return
	var area := Area2D.new()
	area.collision_layer = 0
	area.collision_mask = 2  # sadece oyuncular
	var shape := RectangleShape2D.new()
	shape.size = Vector2(width + 40.0, thickness + 200.0)
	var collision := CollisionShape2D.new()
	collision.shape = shape
	area.add_child(collision)
	add_child(area)
	area.body_entered.connect(_on_body_entered)
	area.body_exited.connect(_on_body_exited)


func _on_body_entered(_body: Node2D) -> void:
	_bodies_near += 1


func _on_body_exited(_body: Node2D) -> void:
	_bodies_near = maxi(_bodies_near - 1, 0)


func _process(delta: float) -> void:
	var target := 1.0 if _bodies_near > 0 else 0.0
	if not is_equal_approx(_open_amount, target):
		_open_amount = move_toward(_open_amount, target, delta * 3.5)
		queue_redraw()


func _draw() -> void:
	var half_w := width * 0.5
	var half_t := thickness * 0.5
	# Esik: sari-siyah ikaz cizgisi
	DrawUtils.hazard_stripes(self, Rect2(-half_w, -half_t, width, thickness), 12.0)
	draw_rect(Rect2(-half_w, -half_t, width, thickness), Color(0, 0, 0, 0.15))

	# Kanatlar (acildikca daralir = duvarin icine kayar)
	var eased := ease(_open_amount, -2.0)
	var panel_w := half_w * (1.0 - eased * 0.94)
	var face_h := minf(18.0, thickness * 0.45)
	for side in [-1.0, 1.0]:
		var x0: float = -half_w if side < 0.0 else half_w - panel_w
		var rect := Rect2(x0, -half_t, panel_w, thickness)
		if rect.size.x < 1.0:
			continue
		draw_rect(rect, panel_color)
		draw_rect(Rect2(x0, half_t - face_h, panel_w, face_h), panel_color.darkened(0.3))
		draw_rect(Rect2(x0, -half_t, panel_w, 3), panel_color.lightened(0.25))
		# Kanadin ortadaki kenarinda sari serit
		var edge_x: float = x0 + panel_w - 5.0 if side < 0.0 else x0
		draw_rect(Rect2(edge_x, -half_t, 5.0, thickness), Color("ffc531"))
		draw_rect(rect, DrawUtils.OUTLINE, false, 2.0)

	# Kasa (iki yandaki direkler) ve durum isigi
	for side in [-1.0, 1.0]:
		var post := Rect2(side * half_w - 7.0, -half_t - 6.0, 14.0, thickness + 6.0)
		draw_rect(post, Color("2f2c52"))
		draw_rect(post, DrawUtils.OUTLINE, false, 2.0)
	var lamp_color := light_color if _open_amount > 0.5 else Color("ff5d73")
	draw_circle(Vector2(-half_w, -half_t - 1.0), 4.0, lamp_color)
	draw_circle(Vector2(half_w, -half_t - 1.0), 4.0, lamp_color)
