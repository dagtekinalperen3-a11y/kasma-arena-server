@tool
class_name FloorDecal
extends Node2D
## ZEMIN BOYASI / LEKE (dekor, carpismasi yok)
## (0, 0) sol-ust kosedir (OIL ve DRAIN icin merkez).

enum Kind { HAZARD_BORDER, WALKWAY_LINE, ARROW, OIL_STAIN, DRAIN }

@export var kind: Kind = Kind.HAZARD_BORDER:
	set(value):
		kind = value
		queue_redraw()
@export var size: Vector2 = Vector2(200, 120):
	set(value):
		size = value
		queue_redraw()
@export var paint_color: Color = Color("ffc531"):
	set(value):
		paint_color = value
		queue_redraw()


func _draw() -> void:
	match kind:
		Kind.HAZARD_BORDER:
			var b := 12.0
			var faded_dark := Color("2a2236", 0.75)
			var faded_paint := Color(paint_color, 0.8)
			DrawUtils.hazard_stripes(self, Rect2(0, 0, size.x, b), 10.0, faded_paint, faded_dark)
			DrawUtils.hazard_stripes(self, Rect2(0, size.y - b, size.x, b), 10.0, faded_paint, faded_dark)
			DrawUtils.hazard_stripes(self, Rect2(0, b, b, size.y - b * 2.0), 10.0, faded_paint, faded_dark)
			DrawUtils.hazard_stripes(self, Rect2(size.x - b, b, b, size.y - b * 2.0), 10.0, faded_paint, faded_dark)
		Kind.WALKWAY_LINE:
			draw_rect(Rect2(Vector2.ZERO, size), Color(paint_color, 0.7))
		Kind.ARROW:
			var c := Color(paint_color, 0.55)
			var shaft_h := size.y * 0.36
			draw_rect(Rect2(0, (size.y - shaft_h) * 0.5, size.x * 0.6, shaft_h), c)
			draw_colored_polygon(PackedVector2Array([Vector2(size.x * 0.6, 0), Vector2(size.x, size.y * 0.5),
				Vector2(size.x * 0.6, size.y)]), c)
		Kind.OIL_STAIN:
			var dark := Color(0.08, 0.06, 0.12, 0.35)
			DrawUtils.ellipse(self, Vector2.ZERO, size * 0.5, dark)
			DrawUtils.ellipse(self, size * Vector2(0.35, 0.2), size * 0.22, dark)
			DrawUtils.ellipse(self, size * Vector2(-0.3, 0.25), size * 0.15, dark)
			DrawUtils.ellipse(self, size * Vector2(-0.1, -0.15), size * Vector2(0.18, 0.1), Color(1, 1, 1, 0.12))
		Kind.DRAIN:
			var r := size.x * 0.5
			DrawUtils.ellipse(self, Vector2.ZERO, Vector2(r, r * 0.6), Color("3b3866"), DrawUtils.OUTLINE, 2.0)
			for i in 5:
				var lx := -r * 0.6 + i * r * 0.3
				draw_line(Vector2(lx, -r * 0.35), Vector2(lx, r * 0.35), Color("1d1530"), 3.0)
