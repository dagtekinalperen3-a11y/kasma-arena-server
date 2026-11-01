@tool
class_name FactoryMachine
extends FactoryProp
## FABRIKA MAKINESI (hareketli isiklar, ekran, pervane, duman)
## AŞAMA 3'te "bozulan makineyi tamir et" gorevi bu objeyi kullanacak.

enum Kind { PRESS, GENERATOR, CONSOLE }

@export var kind: Kind = Kind.GENERATOR:
	set(value):
		kind = value
		queue_redraw()
@export var width: float = 130.0:
	set(value):
		width = value
		queue_redraw()
@export var depth: float = 44.0:
	set(value):
		depth = value
		queue_redraw()
@export var height: float = 70.0:
	set(value):
		height = value
		queue_redraw()
@export var main_color: Color = Color("4f86c6"):
	set(value):
		main_color = value
		queue_redraw()
@export var accent_color: Color = Color("ffc531"):
	set(value):
		accent_color = value
		queue_redraw()

var _t := 0.0


func _footprint() -> Rect2:
	return Rect2(-width * 0.5, -depth, width, depth)


func _process(delta: float) -> void:
	_t += delta
	queue_redraw()


func _draw() -> void:
	var x := -width * 0.5
	DrawUtils.soft_shadow(self, Vector2(5, -depth * 0.4), Vector2(width * 0.6, depth * 0.6))
	# Taban (ikaz seritli)
	DrawUtils.hazard_stripes(self, Rect2(x - 4, -9, width + 8, 9), 9.0)
	draw_rect(Rect2(x - 4, -9, width + 8, 9), DrawUtils.OUTLINE, false, 2.0)
	var bottom := -9.0
	var body_h := height
	if kind == Kind.PRESS:
		body_h = height * 0.6
	DrawUtils.box_3d(self, x, bottom, width, depth, body_h, main_color.lightened(0.12), main_color)
	var front := Rect2(x, bottom - body_h, width, body_h)
	var top_y := bottom - body_h - depth
	match kind:
		Kind.GENERATOR:
			_draw_generator(front, top_y)
		Kind.PRESS:
			_draw_press(front, top_y)
		Kind.CONSOLE:
			_draw_console(front, top_y)


func _draw_lights(start: Vector2, count: int) -> void:
	var colors := [Color("59f0a6"), Color("ffc531"), Color("ff5d73"), Color("4fd1ff")]
	for i in count:
		var on := fmod(_t * 2.0 + i * 0.37, 1.0) > 0.4
		var c: Color = colors[i % colors.size()]
		draw_circle(start + Vector2(i * 13, 0), 4.5, DrawUtils.OUTLINE)
		draw_circle(start + Vector2(i * 13, 0), 3.2, c if on else c.darkened(0.6))


func _draw_generator(front: Rect2, top_y: float) -> void:
	# Pervane
	var fan_center := Vector2(front.position.x + front.size.y * 0.5 + 4, front.get_center().y + 2)
	var fan_r := front.size.y * 0.36
	DrawUtils.ellipse(self, fan_center, Vector2(fan_r, fan_r), main_color.darkened(0.45), DrawUtils.OUTLINE, 2.0)
	for b in 4:
		var a := _t * 8.0 + b * TAU / 4.0
		var tip := fan_center + Vector2(cos(a), sin(a)) * fan_r * 0.85
		var side := fan_center + Vector2(cos(a + 0.5), sin(a + 0.5)) * fan_r * 0.5
		draw_colored_polygon(PackedVector2Array([fan_center, side, tip]), Color("c9d3e3"))
	draw_circle(fan_center, 4.0, accent_color)
	# Gosterge
	var gauge_c := Vector2(front.end.x - 26, front.position.y + 22)
	DrawUtils.ellipse(self, gauge_c, Vector2(13, 13), Color("f4f1ea"), DrawUtils.OUTLINE, 2.0)
	var needle_a := -PI * 0.75 + (sin(_t * 1.7) * 0.5 + 0.5) * PI
	draw_line(gauge_c, gauge_c + Vector2(cos(needle_a), sin(needle_a)) * 10.0, Color("ff5d73"), 2.0, true)
	_draw_lights(Vector2(front.end.x - 50, front.end.y - 14), 3)
	# Baca ve duman
	var chimney := Rect2(front.end.x - 34, top_y - 22, 16, 26)
	draw_rect(chimney, Color("5c5f78"))
	draw_rect(chimney, DrawUtils.OUTLINE, false, 2.0)
	for p in 3:
		var life := fmod(_t * 0.6 + p * 0.33, 1.0)
		var puff_pos := Vector2(chimney.get_center().x + sin(life * 6.0 + p) * 4.0, chimney.position.y - 6 - life * 40.0)
		draw_circle(puff_pos, 5.0 + life * 7.0, Color(1, 1, 1, 0.45 * (1.0 - life)))


func _draw_press(front: Rect2, top_y: float) -> void:
	# Ekran
	var screen := Rect2(front.position.x + 10, front.position.y + 8, front.size.x * 0.42, front.size.y - 18)
	draw_rect(screen, Color("16233a"))
	var wave := PackedVector2Array()
	for i in 12:
		var px := screen.position.x + 3 + i * (screen.size.x - 6) / 11.0
		wave.append(Vector2(px, screen.get_center().y + sin(_t * 5.0 + i * 0.8) * screen.size.y * 0.25))
	draw_polyline(wave, Color("59f0a6"), 2.0, true)
	draw_rect(screen, DrawUtils.OUTLINE, false, 2.0)
	# Dugmeler
	DrawUtils.ellipse(self, Vector2(front.end.x - 40, front.get_center().y), Vector2(8, 8), Color("ff5d73"), DrawUtils.OUTLINE, 2.0)
	DrawUtils.ellipse(self, Vector2(front.end.x - 18, front.get_center().y), Vector2(8, 8), Color("59f0a6"), DrawUtils.OUTLINE, 2.0)
	# Pres kolu (inip kalkar)
	var cycle := clampf(sin(_t * 2.4) * 1.4, -1.0, 1.0) * 0.5 + 0.5
	var arm_x := front.get_center().x - 18
	var post_h := 46.0
	for px in [front.position.x + 6, front.end.x - 16]:
		draw_rect(Rect2(px, top_y - post_h, 10, post_h + 6), Color("5c5f78"))
		draw_rect(Rect2(px, top_y - post_h, 10, post_h + 6), DrawUtils.OUTLINE, false, 2.0)
	draw_rect(Rect2(front.position.x, top_y - post_h - 12, front.size.x, 14), accent_color)
	draw_rect(Rect2(front.position.x, top_y - post_h - 12, front.size.x, 14), DrawUtils.OUTLINE, false, 2.0)
	var head_y := top_y - post_h + 2 + cycle * (post_h - 20)
	draw_rect(Rect2(arm_x + 14, top_y - post_h + 2, 8, head_y - (top_y - post_h + 2)), Color("c9d3e3"))
	DrawUtils.box_3d(self, arm_x, head_y + 14, 36, 8, 12, Color("9aa7b8"), Color("6d7a8d"))


func _draw_console(front: Rect2, top_y: float) -> void:
	var screen := Rect2(front.position.x + 8, front.position.y + 7, front.size.x - 16, front.size.y * 0.55)
	draw_rect(screen, Color("16233a"))
	for i in 6:
		var bar_h := (sin(_t * 3.0 + i * 1.3) * 0.5 + 0.5) * (screen.size.y - 10) + 4
		draw_rect(Rect2(screen.position.x + 6 + i * ((screen.size.x - 12) / 6.0), screen.end.y - 4 - bar_h,
			(screen.size.x - 12) / 6.0 - 4, bar_h), Color("4fd1ff") if i % 2 == 0 else Color("59f0a6"))
	draw_rect(screen, DrawUtils.OUTLINE, false, 2.0)
	_draw_lights(Vector2(front.position.x + 14, front.end.y - 10), int((front.size.x - 20) / 13.0))
	# Ust yuzde klavye / kollar
	draw_rect(Rect2(front.position.x + 12, top_y + 8, front.size.x - 24, depth - 16), Color("2b2d4a"))
	for k in int((front.size.x - 30) / 10.0):
		draw_rect(Rect2(front.position.x + 16 + k * 10, top_y + 12, 7, 5), Color("d7dbe8"))
