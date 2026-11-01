@tool
class_name Plant
extends FactoryProp
## SAKSI BITKISI (dekor)

@export var pot_color: Color = Color("e0734a"):
	set(value):
		pot_color = value
		queue_redraw()
@export var leaf_color: Color = Color("4cc471"):
	set(value):
		leaf_color = value
		queue_redraw()


func _make_shape() -> Shape2D:
	var circle := CircleShape2D.new()
	circle.radius = 13.0
	return circle


func _shape_offset() -> Vector2:
	return Vector2(0, -7)


func _draw() -> void:
	DrawUtils.soft_shadow(self, Vector2(2, -4), Vector2(17, 7))
	# Yapraklar
	var leaves := [Vector2(-12, -44), Vector2(12, -46), Vector2(0, -56), Vector2(-6, -36), Vector2(8, -36)]
	for i in leaves.size():
		var p: Vector2 = leaves[i]
		var c := leaf_color.darkened(0.15) if i % 2 == 0 else leaf_color
		DrawUtils.ellipse(self, p, Vector2(10, 14), c, DrawUtils.OUTLINE, 2.0)
		draw_line(p + Vector2(0, 10), p + Vector2(0, -8), c.darkened(0.25), 1.5)
	# Saksi
	var pot := PackedVector2Array([Vector2(-15, -30), Vector2(15, -30), Vector2(11, -2), Vector2(-11, -2)])
	DrawUtils.fill_shape(self, pot, pot_color, DrawUtils.OUTLINE, 2.0)
	draw_rect(Rect2(-17, -34, 34, 7), pot_color.lightened(0.12))
	draw_rect(Rect2(-17, -34, 34, 7), DrawUtils.OUTLINE, false, 2.0)
