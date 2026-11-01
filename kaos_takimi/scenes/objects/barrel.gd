@tool
class_name Barrel
extends FactoryProp
## VARIL

@export var barrel_color: Color = Color("3d8bd9"):
	set(value):
		barrel_color = value
		queue_redraw()
@export var radius: float = 17.0:
	set(value):
		radius = value
		queue_redraw()
@export var height: float = 34.0:
	set(value):
		height = value
		queue_redraw()
## Uzerinde ikaz isareti olsun mu?
@export var hazard_sign: bool = false:
	set(value):
		hazard_sign = value
		queue_redraw()


func _make_shape() -> Shape2D:
	var circle := CircleShape2D.new()
	circle.radius = radius * 0.9
	return circle


func _shape_offset() -> Vector2:
	return Vector2(0, -radius * 0.45)


func _draw() -> void:
	var ry := radius * 0.45
	DrawUtils.soft_shadow(self, Vector2(3, -ry * 0.6), Vector2(radius * 1.1, ry * 1.1))
	var body := PackedVector2Array()
	for i in 13:
		var a := PI * float(i) / 12.0
		body.append(Vector2(cos(a) * radius, -ry + sin(a) * ry))
	body.append(Vector2(-radius, -ry - height))
	body.append(Vector2(radius, -ry - height))
	body.reverse()
	DrawUtils.fill_shape(self, body, barrel_color, DrawUtils.OUTLINE, 2.0)
	# Halkalar
	for t: float in [0.28, 0.72]:
		var y := -ry - height * t
		draw_line(Vector2(-radius, y), Vector2(radius, y), barrel_color.darkened(0.35), 3.0)
	draw_rect(Rect2(-radius * 0.6, -ry - height + 2, 5, height - 4), barrel_color.lightened(0.2))
	if hazard_sign:
		var c := Vector2(0, -ry - height * 0.5)
		DrawUtils.fill_shape(self, PackedVector2Array([c + Vector2(0, -8), c + Vector2(8, 6), c + Vector2(-8, 6)]),
			Color("ffc531"), DrawUtils.OUTLINE, 1.5)
		draw_line(c + Vector2(0, -3), c + Vector2(0, 1), DrawUtils.OUTLINE, 2.0)
		draw_circle(c + Vector2(0, 3.5), 1.1, DrawUtils.OUTLINE)
	# Kapak
	DrawUtils.ellipse(self, Vector2(0, -ry - height), Vector2(radius, ry), barrel_color.lightened(0.15), DrawUtils.OUTLINE, 2.0)
	DrawUtils.ellipse(self, Vector2(0, -ry - height), Vector2(radius * 0.7, ry * 0.65), barrel_color.darkened(0.05))
	draw_circle(Vector2(radius * 0.35, -ry - height), 2.5, barrel_color.darkened(0.4))
