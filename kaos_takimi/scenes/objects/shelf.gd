@tool
class_name StorageShelf
extends FactoryProp
## DEPO RAFI (uzerinde renkli koliler)

@export var width: float = 200.0:
	set(value):
		width = value
		queue_redraw()
@export var depth: float = 34.0:
	set(value):
		depth = value
		queue_redraw()
@export_range(1, 4) var levels: int = 3:
	set(value):
		levels = value
		queue_redraw()
@export var upright_color: Color = Color("3d6fd9"):
	set(value):
		upright_color = value
		queue_redraw()
@export var beam_color: Color = Color("ff8a3d"):
	set(value):
		beam_color = value
		queue_redraw()
@export var variation_seed: int = 1:
	set(value):
		variation_seed = value
		queue_redraw()

const LEVEL_HEIGHT := 30.0


func _footprint() -> Rect2:
	return Rect2(-width * 0.5, -depth, width, depth)


func _draw() -> void:
	var x := -width * 0.5
	var total_h := LEVEL_HEIGHT * levels
	DrawUtils.soft_shadow(self, Vector2(4, -depth * 0.4), Vector2(width * 0.56, depth * 0.6))
	# Arka direkler
	for px in [x, x + width - 8.0]:
		draw_rect(Rect2(px, -total_h - depth, 8, total_h), upright_color.darkened(0.35))
	var box_colors := [Color("d9a66b"), Color("c98a4b"), Color("8da2b5"), Color("ff5d73"), Color("59c3a0")]
	for level in levels:
		var shelf_y := -level * LEVEL_HEIGHT
		# Raf tablasi
		DrawUtils.box_3d(self, x, shelf_y, width, depth, 5, Color("b8bfd6"), beam_color, 1.5)
		if level == levels - 1 and levels > 1:
			continue
		# Koliler
		var bx := x + 10.0
		var n := 0
		while bx < x + width - 30.0:
			var r := DrawUtils.hash01(level, n, variation_seed)
			var bw := 22.0 + r * 18.0
			if bx + bw > x + width - 10.0:
				break
			if r > 0.15:
				var bh := 14.0 + r * 9.0
				var c: Color = box_colors[int(r * 100.0) % box_colors.size()]
				DrawUtils.box_3d(self, bx, shelf_y - 5 - depth * 0.25, bw, depth * 0.55, bh, c.lightened(0.1), c.darkened(0.1), 1.5)
			bx += bw + 6.0
			n += 1
	# On direkler
	for px in [x, x + width - 8.0]:
		draw_rect(Rect2(px, -total_h - depth + depth, 8, total_h), upright_color)
		draw_rect(Rect2(px, -total_h, 8, total_h), DrawUtils.OUTLINE, false, 1.5)
