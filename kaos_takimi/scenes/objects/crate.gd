@tool
class_name Crate
extends FactoryProp
## KUTU (tahta, karton veya metal). Ust uste "stack" adet dizilebilir.

enum Style { WOOD, CARDBOARD, METAL }

@export var style: Style = Style.WOOD:
	set(value):
		style = value
		queue_redraw()
@export var width: float = 52.0:
	set(value):
		width = value
		queue_redraw()
@export var depth: float = 26.0:
	set(value):
		depth = value
		queue_redraw()
@export var height: float = 30.0:
	set(value):
		height = value
		queue_redraw()
@export_range(1, 3) var stack: int = 1:
	set(value):
		stack = value
		queue_redraw()


func _footprint() -> Rect2:
	return Rect2(-width * 0.5, -depth, width, depth)


func _colors() -> Array[Color]:
	match style:
		Style.CARDBOARD:
			return [Color("d9a66b"), Color("b98348")]
		Style.METAL:
			return [Color("8da2b5"), Color("617488")]
	return [Color("d08c4f"), Color("a4652f")]


func _draw() -> void:
	DrawUtils.soft_shadow(self, Vector2(3, -depth * 0.35), Vector2(width * 0.62, depth * 0.55))
	var colors := _colors()
	for level in stack:
		var inset := level * 3.0
		var w := width - inset * 2.0
		var x := -width * 0.5 + inset + (2.0 if level % 2 == 1 else 0.0)
		var bottom := -level * height
		DrawUtils.box_3d(self, x, bottom, w, depth, height, colors[0], colors[1])
		var front := Rect2(x, bottom - height, w, height)
		match style:
			Style.WOOD:
				draw_rect(front.grow(-4.0), colors[1].darkened(0.15), false, 2.0)
				draw_line(front.position + Vector2(5, 5), front.end - Vector2(5, 5), colors[1].darkened(0.2), 3.0)
				draw_line(Vector2(front.position.x + 5, front.end.y - 5), Vector2(front.end.x - 5, front.position.y + 5), colors[1].darkened(0.2), 3.0)
				draw_line(Vector2(x + 2, bottom - height - depth * 0.5), Vector2(x + w - 2, bottom - height - depth * 0.5), colors[0].darkened(0.12), 1.5)
			Style.CARDBOARD:
				draw_rect(Rect2(x + w * 0.5 - 5, bottom - height - depth, 10, depth), Color("e8d3a8"))
				draw_rect(Rect2(x + w * 0.5 - 5, bottom - height, 10, 6), Color("e8d3a8"))
				draw_rect(Rect2(x + 6, bottom - height + 10, 12, 8), Color(0.2, 0.15, 0.1, 0.35))
			Style.METAL:
				draw_rect(Rect2(x, bottom - 8, w, 5), Color("ffc531"))
				for bx in [x + 5, x + w - 5]:
					draw_circle(Vector2(bx, bottom - height + 5), 1.8, colors[0].lightened(0.3))
		draw_rect(Rect2(x, bottom - height - depth, w, depth + height), DrawUtils.OUTLINE, false, 2.0)
