extends Control
## ANA MENU ARKA PLANI
## Degrade renk, donen dev disliler, yukselen parcaciklar ve
## alttaki tasima bandini kodla cizer.

## Bandin ekranin altindan yuksekligi (main_menu.gd karakterleri buna gore dizer).
const BELT_HEIGHT_FROM_BOTTOM := 70.0

## Sagdaki karakter onizlemesinin durdugu kaide merkezi (main_menu.gd ayarlar).
var pedestal_center := Vector2(-1000, -1000)

var _t := 0.0
var _particles: Array[Vector3] = []  # x, y, hiz


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	for i in 40:
		_particles.append(Vector3(randf(), randf(), randf_range(0.02, 0.07)))


func _process(delta: float) -> void:
	_t += delta
	for i in _particles.size():
		var p := _particles[i]
		p.y -= p.z * delta
		if p.y < -0.05:
			p = Vector3(randf(), 1.05, randf_range(0.02, 0.07))
		_particles[i] = p
	queue_redraw()


func get_belt_y() -> float:
	return size.y - BELT_HEIGHT_FROM_BOTTOM


func _draw() -> void:
	var w := size.x
	var h := size.y
	# Degrade arka plan
	draw_polygon(PackedVector2Array([Vector2.ZERO, Vector2(w, 0), Vector2(w, h), Vector2(0, h)]),
		PackedColorArray([Color("3a2a7a"), Color("2a5a8a"), Color("152044"), Color("1a1236")]))

	# Hafif hareketli capraz seritler
	var stripe_w := 90.0
	var offset := fmod(_t * 20.0, stripe_w * 2.0)
	var x := -h - stripe_w * 2.0 + offset
	while x < w:
		draw_colored_polygon(PackedVector2Array([Vector2(x, h), Vector2(x + stripe_w, h),
			Vector2(x + stripe_w + h, 0), Vector2(x + h, 0)]), Color(1, 1, 1, 0.025))
		x += stripe_w * 2.0

	# Donen disliler
	_draw_gear(Vector2(w * 0.86, h * 0.18), 150.0, 14, _t * 0.15, Color(1, 1, 1, 0.05))
	_draw_gear(Vector2(w * 0.66, h * 0.02), 90.0, 10, -_t * 0.25 + 0.2, Color(1, 1, 1, 0.045))
	_draw_gear(Vector2(w * 0.97, h * 0.62), 110.0, 12, -_t * 0.2, Color(1, 1, 1, 0.04))
	_draw_gear(Vector2(w * 0.04, h * 0.95), 130.0, 12, _t * 0.18, Color(1, 1, 1, 0.035))

	# Parcaciklar
	for p in _particles:
		var a := 0.15 + 0.25 * sin(_t * 2.0 + p.x * 20.0) * 0.5 + 0.1
		draw_circle(Vector2(p.x * w, p.y * h), 1.5 + p.z * 30.0, Color(1, 0.85, 0.5, a))

	# Karakter kaidesi ve spot isik
	if pedestal_center.x > 0.0:
		var c := pedestal_center
		draw_colored_polygon(PackedVector2Array([c + Vector2(-40, -420), c + Vector2(40, -420),
			c + Vector2(150, 0), c + Vector2(-150, 0)]), Color(1, 0.95, 0.7, 0.06))
		DrawUtils.ellipse(self, c + Vector2(0, 14), Vector2(150, 40), Color("1d1530"))
		DrawUtils.ellipse(self, c, Vector2(150, 40), Color("5d5a8c"), DrawUtils.OUTLINE, 3.0)
		DrawUtils.ellipse(self, c, Vector2(120, 30), Color("6f6ca3"))
		var ring := DrawUtils.ellipse_points(c, Vector2(135, 35), 40)
		ring.append(ring[0])
		draw_polyline(ring, Color(1, 0.773, 0.192, 0.5 + 0.3 * sin(_t * 3.0)), 3.0, true)

	# Alttaki tasima bandi
	var belt_y := get_belt_y()
	draw_rect(Rect2(0, belt_y - 6, w, 14), Color("5c5f78"))
	draw_rect(Rect2(0, belt_y + 8, w, h - belt_y), Color("221b3d"))
	DrawUtils.hazard_stripes(self, Rect2(0, belt_y + 8, w, 12), 14.0)
	var chev := fmod(_t * 60.0, 40.0)
	var cx := -40.0 + chev
	while cx < w:
		draw_polyline(PackedVector2Array([Vector2(cx, belt_y + 30), Vector2(cx + 12, belt_y + 42),
			Vector2(cx, belt_y + 54)]), Color(1, 1, 1, 0.08), 3.0)
		cx += 40.0
	draw_line(Vector2(0, belt_y - 6), Vector2(w, belt_y - 6), DrawUtils.OUTLINE, 3.0)


func _draw_gear(center: Vector2, radius: float, teeth: int, angle: float, color: Color) -> void:
	var pts := PackedVector2Array()
	var inner := radius * 0.82
	for i in teeth:
		var a0 := angle + TAU * float(i) / float(teeth)
		var step := TAU / float(teeth)
		pts.append(center + Vector2.from_angle(a0) * inner)
		pts.append(center + Vector2.from_angle(a0 + step * 0.15) * radius)
		pts.append(center + Vector2.from_angle(a0 + step * 0.45) * radius)
		pts.append(center + Vector2.from_angle(a0 + step * 0.6) * inner)
	draw_colored_polygon(pts, color)
	draw_circle(center, radius * 0.35, Color(0.1, 0.08, 0.2, 0.25))
