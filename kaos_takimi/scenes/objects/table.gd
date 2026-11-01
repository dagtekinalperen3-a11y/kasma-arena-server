@tool
class_name WorkTable
extends FactoryProp
## CALISMA MASASI. Uzerindeki esyalar "items" ile secilir.

enum Items { EMPTY, TOOLS, PAPERS, COMPUTER, SNACKS }

@export var width: float = 120.0:
	set(value):
		width = value
		queue_redraw()
@export var depth: float = 48.0:
	set(value):
		depth = value
		queue_redraw()
@export var top_color: Color = Color("b77b4b"):
	set(value):
		top_color = value
		queue_redraw()
@export var items: Items = Items.TOOLS:
	set(value):
		items = value
		queue_redraw()

const LEG_HEIGHT := 18.0
const TOP_THICKNESS := 7.0


func _footprint() -> Rect2:
	return Rect2(-width * 0.5, -depth, width, depth)


func _draw() -> void:
	DrawUtils.soft_shadow(self, Vector2(4, -depth * 0.4), Vector2(width * 0.55, depth * 0.55))
	var x := -width * 0.5
	var leg_color := Color("4a4570")
	for lx in [x + 6.0, x + width - 14.0]:
		draw_rect(Rect2(lx, -LEG_HEIGHT, 8, LEG_HEIGHT), leg_color)
		draw_rect(Rect2(lx, -LEG_HEIGHT, 8, LEG_HEIGHT), DrawUtils.OUTLINE, false, 1.5)
	DrawUtils.box_3d(self, x, -LEG_HEIGHT, width, depth, TOP_THICKNESS, top_color, top_color.darkened(0.3))
	var top_y := -LEG_HEIGHT - TOP_THICKNESS - depth
	var cx := 0.0
	match items:
		Items.TOOLS:
			DrawUtils.box_3d(self, x + 10, top_y + depth - 10, 34, 10, 12, Color("ff5d73"), Color("c93a50"))
			draw_line(Vector2(cx, top_y + 14), Vector2(cx + 30, top_y + 26), Color("9aa7b8"), 4.0, true)
			draw_circle(Vector2(cx + 31, top_y + 27), 4.0, Color("9aa7b8"))
			draw_line(Vector2(cx - 4, top_y + 30), Vector2(cx + 14, top_y + 20), Color("ffc531"), 4.0, true)
		Items.PAPERS:
			for i in 3:
				var p := Vector2(x + 18 + i * 26, top_y + 10 + (i % 2) * 6)
				draw_rect(Rect2(p, Vector2(20, 24)), Color("f4f1ea"))
				draw_rect(Rect2(p, Vector2(20, 24)), DrawUtils.OUTLINE, false, 1.0)
				for l in 3:
					draw_line(p + Vector2(3, 6 + l * 5), p + Vector2(16, 6 + l * 5), Color("a9b4c8"), 1.0)
			DrawUtils.ellipse(self, Vector2(x + width - 22, top_y + 26), Vector2(7, 5), Color("ffffff"), DrawUtils.OUTLINE, 1.5)
			DrawUtils.ellipse(self, Vector2(x + width - 22, top_y + 25), Vector2(5, 3), Color("6b3e1f"))
		Items.COMPUTER:
			DrawUtils.box_3d(self, cx - 26, top_y + depth - 14, 52, 6, 30, Color("3a3d63"), Color("2b2d4a"))
			draw_rect(Rect2(cx - 22, top_y + depth - 14 - 27, 44, 22), Color("4fd1ff"))
			draw_rect(Rect2(cx - 18, top_y + depth - 14 - 23, 20, 3), Color(1, 1, 1, 0.7))
			draw_rect(Rect2(cx - 18, top_y + depth - 14 - 17, 30, 3), Color(1, 1, 1, 0.45))
			draw_rect(Rect2(cx - 20, top_y + depth - 9, 40, 7), Color("d7dbe8"))
		Items.SNACKS:
			DrawUtils.ellipse(self, Vector2(cx - 18, top_y + 22), Vector2(16, 9), Color("ffffff"), DrawUtils.OUTLINE, 1.5)
			for d in [Vector2(-24, 20), Vector2(-14, 24), Vector2(-18, 18)]:
				draw_circle(Vector2(cx, top_y) + d, 4.0, Color("f2a541"))
			DrawUtils.ellipse(self, Vector2(cx + 24, top_y + 24), Vector2(7, 5), Color("ff5d73"), DrawUtils.OUTLINE, 1.5)
