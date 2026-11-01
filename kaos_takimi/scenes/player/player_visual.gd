@tool
class_name PlayerVisual
extends Node2D
## OYUNCU GORUNUMU
## Karakterin sevimli "fasulye" govdesini, baretini, gozlerini ve
## yurume sallanmasini kodla cizer. Ileride gercek sprite animasyonlari
## gelince sadece bu dosya degisecek; hareket kodu (player.gd) etkilenmeyecek.
##
## Koordinat: (0, 0) noktasi karakterin AYAK hizasidir.

@export var body_color: Color = Color("ff5d73"):
	set(value):
		body_color = value
		queue_redraw()
@export var helmet_color: Color = Color("ffc531"):
	set(value):
		helmet_color = value
		queue_redraw()

const BODY_SIZE := Vector2(30, 36)

var _time := 0.0
var _walk_phase := 0.0
var _speed_ratio := 0.0          # 0 = duruyor, 1 = tam hiz
var _facing := 1.0               # 1 = saga, -1 = sola
var _look := Vector2(0.0, 0.3)   # gozlerin baktigi yon
var _blink_timer := 2.5
var _blink := 0.0


## player.gd her karede bunu cagirarak hareket bilgisini verir.
func update_motion(velocity: Vector2, max_speed: float) -> void:
	_speed_ratio = clampf(velocity.length() / maxf(max_speed, 1.0), 0.0, 1.0)
	if absf(velocity.x) > 10.0:
		_facing = signf(velocity.x)
	if velocity.length() > 10.0:
		_look = _look.lerp(velocity.normalized(), 0.25)


## Menudeki karakterler icin: yurur gibi gorunsun.
func set_fake_walk(speed_ratio: float, facing: float) -> void:
	_speed_ratio = speed_ratio
	_facing = facing
	_look = Vector2(facing, 0.15).normalized()


func _process(delta: float) -> void:
	_time += delta
	_walk_phase += delta * lerpf(0.0, 15.0, _speed_ratio)
	_blink_timer -= delta
	if _blink_timer <= 0.0:
		_blink = 1.0
		_blink_timer = randf_range(2.0, 4.5)
	_blink = maxf(_blink - delta * 7.0, 0.0)
	queue_redraw()


func _draw() -> void:
	var walking := _speed_ratio > 0.08
	var step := sin(_walk_phase)
	var bob := absf(step) * 4.0 * _speed_ratio if walking else 0.0
	var breathe := sin(_time * 3.0) * 0.035 if not walking else 0.0
	# Hafif ezilme-uzama (squash & stretch) efekti
	var stretch := 1.0 + breathe + (absf(step) * 0.07 * _speed_ratio)
	var squash := 1.0 / stretch
	var lean := _facing * 0.08 * _speed_ratio

	# Golge
	DrawUtils.soft_shadow(self, Vector2(0, -1), Vector2(17, 6) * (1.0 - bob * 0.03))

	# Ayaklar
	var foot_offset := step * 6.0 * _speed_ratio
	var foot_lift_l := maxf(0.0, -step) * 3.0 * _speed_ratio
	var foot_lift_r := maxf(0.0, step) * 3.0 * _speed_ratio
	var foot_color := body_color.darkened(0.45)
	DrawUtils.ellipse(self, Vector2(-7 + foot_offset, -3 - foot_lift_l), Vector2(6, 4), foot_color, DrawUtils.OUTLINE, 2.0)
	DrawUtils.ellipse(self, Vector2(7 - foot_offset, -3 - foot_lift_r), Vector2(6, 4), foot_color, DrawUtils.OUTLINE, 2.0)

	# Govdeyi egerek / ziplatarak ciz
	var body_bottom := -5.0 - bob
	draw_set_transform(Vector2(0, body_bottom), lean, Vector2(squash, stretch))
	var w := BODY_SIZE.x
	var h := BODY_SIZE.y
	var body_rect := Rect2(-w * 0.5, -h, w, h)
	DrawUtils.rounded_box(self, body_rect, 14.0, body_color, DrawUtils.OUTLINE, 2.5)
	# Alt kisim golgesi ve parlama
	draw_colored_polygon(DrawUtils.rounded_rect_points(Rect2(-w * 0.5 + 4, -8, w - 8, 6), 3.0), body_color.darkened(0.1))
	DrawUtils.ellipse(self, Vector2(-7 * _facing, -h + 12), Vector2(4, 6), body_color.lightened(0.35))

	# Yanaklar
	var cheek := Color(1.0, 0.55, 0.65, 0.55)
	DrawUtils.ellipse(self, Vector2(-9 + _look.x * 3.0, -h + 25), Vector2(3.5, 2.2), cheek)
	DrawUtils.ellipse(self, Vector2(9 + _look.x * 3.0, -h + 25), Vector2(3.5, 2.2), cheek)

	# Gozler
	var eye_shift := Vector2(_look.x * 4.0, _look.y * 2.0)
	var eye_open := 1.0 - _blink
	for side in [-1.0, 1.0]:
		var eye_center := Vector2(side * 6.5, -h + 18) + eye_shift
		if eye_open > 0.2:
			DrawUtils.ellipse(self, eye_center, Vector2(4.5, 6.0 * eye_open), Color.WHITE, DrawUtils.OUTLINE, 1.8)
			DrawUtils.ellipse(self, eye_center + Vector2(_look.x * 1.5, 1.0 + _look.y * 1.2), Vector2(2.4, 3.2 * eye_open), DrawUtils.OUTLINE)
			draw_circle(eye_center + Vector2(-1.0, -2.0 * eye_open), 1.1, Color.WHITE)
		else:
			draw_line(eye_center + Vector2(-4, 0), eye_center + Vector2(4, 0), DrawUtils.OUTLINE, 2.0, true)

	# Baret (fabrika iscisi kaski)
	var helmet_y := -h + 7.0
	var dome := PackedVector2Array()
	for i in 17:
		var a := PI + PI * float(i) / 16.0
		dome.append(Vector2(cos(a) * 15.5, helmet_y + sin(a) * 13.0))
	DrawUtils.fill_shape(self, dome, helmet_color, DrawUtils.OUTLINE, 2.2)
	draw_line(Vector2(0, helmet_y - 13), Vector2(0, helmet_y), helmet_color.darkened(0.2), 3.0, true)
	DrawUtils.rounded_box(self, Rect2(-18 + _facing * 2.0, helmet_y - 2, 36, 5), 2.5, helmet_color.darkened(0.08), DrawUtils.OUTLINE, 2.0)
	DrawUtils.ellipse(self, Vector2(-6, helmet_y - 8), Vector2(3, 2), helmet_color.lightened(0.45))

	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
