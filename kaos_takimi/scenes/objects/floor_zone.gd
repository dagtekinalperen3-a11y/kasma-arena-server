@tool
class_name FloorZone
extends Node2D
## ZEMIN BOLGESI (ODA ZEMINI)
## Bir odanin veya koridorun zeminini desenli olarak cizer.
## Ayrica oda adini tasir; ekrandaki "Su an buradasin" yazisi bunu kullanir.
## (0, 0) sol-ust kosedir.

enum Pattern { TILES, PLANKS, METAL, CONCRETE }

const LABEL_FONT := preload("res://assets/fonts/Baloo2-ExtraBold.ttf")

@export var size: Vector2 = Vector2(512, 512):
	set(value):
		size = value.max(Vector2(16, 16))
		queue_redraw()
@export var base_color: Color = Color("8fa3b8"):
	set(value):
		base_color = value
		queue_redraw()
@export var pattern: Pattern = Pattern.TILES:
	set(value):
		pattern = value
		queue_redraw()
@export var tile_size: float = 64.0:
	set(value):
		tile_size = maxf(value, 8.0)
		queue_redraw()
## Oda adi (ekranda ve zeminde gorunur).
@export var room_name: String = "":
	set(value):
		room_name = value
		queue_redraw()
## Oda adi zemine boyali yazi olarak cizilsin mi?
@export var show_floor_label: bool = true:
	set(value):
		show_floor_label = value
		queue_redraw()
## Zemindeki yazinin konumu (bolgenin sol-ust kosesine gore). (0,0) = ortasi.
@export var label_position: Vector2 = Vector2.ZERO:
	set(value):
		label_position = value
		queue_redraw()
@export var label_font_size: int = 64:
	set(value):
		label_font_size = value
		queue_redraw()
@export var variation_seed: int = 0:
	set(value):
		variation_seed = value
		queue_redraw()


func _ready() -> void:
	if not Engine.is_editor_hint():
		add_to_group("rooms")


## Verilen dunya konumu bu bolgenin icinde mi?
func contains_global_point(point: Vector2) -> bool:
	return Rect2(global_position, size).has_point(point)


func _draw() -> void:
	match pattern:
		Pattern.TILES:
			_draw_tiles()
		Pattern.PLANKS:
			_draw_planks()
		Pattern.METAL:
			_draw_metal()
		Pattern.CONCRETE:
			_draw_concrete()

	# Duvar dibindeki yumusak karanlik (derinlik hissi verir)
	draw_rect(Rect2(0, 0, size.x, 18), Color(0, 0, 0, 0.12))
	draw_rect(Rect2(0, 0, size.x, 8), Color(0, 0, 0, 0.08))

	if show_floor_label and room_name != "":
		var center := size * 0.5 if label_position == Vector2.ZERO else label_position
		var text_size := LABEL_FONT.get_string_size(room_name, HORIZONTAL_ALIGNMENT_LEFT, -1, label_font_size)
		var pos := center + Vector2(-text_size.x * 0.5, label_font_size * 0.3)
		var paint := base_color.darkened(0.35)
		paint.a = 0.35
		draw_string(LABEL_FONT, pos, room_name, HORIZONTAL_ALIGNMENT_LEFT, -1, label_font_size, paint)


func _varied(ix: int, iy: int, amount: float) -> Color:
	var v := DrawUtils.hash01(ix, iy, variation_seed) - 0.5
	if v > 0.0:
		return base_color.lightened(v * amount)
	return base_color.darkened(-v * amount)


func _draw_tiles() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), base_color.darkened(0.18))
	var cols := ceili(size.x / tile_size)
	var rows := ceili(size.y / tile_size)
	var bounds := Rect2(Vector2.ZERO, size)
	for iy in rows:
		for ix in cols:
			var tile := Rect2(ix * tile_size, iy * tile_size, tile_size, tile_size).grow(-1.5).intersection(bounds)
			if tile.size.x <= 0.0 or tile.size.y <= 0.0:
				continue
			draw_rect(tile, _varied(ix, iy, 0.1))
			draw_line(tile.position + Vector2(2, 2), Vector2(tile.end.x - 2, tile.position.y + 2), Color(1, 1, 1, 0.12), 2.0)


func _draw_planks() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), base_color.darkened(0.3))
	var plank_h := tile_size * 0.5
	var rows := ceili(size.y / plank_h)
	for iy in rows:
		var x := -DrawUtils.hash01(0, iy, variation_seed) * tile_size * 2.0
		var ix := 0
		while x < size.x:
			var length := tile_size * (1.5 + DrawUtils.hash01(ix, iy, variation_seed + 7) * 2.0)
			var plank := Rect2(x, iy * plank_h, length, plank_h).grow(-1.0).intersection(Rect2(Vector2.ZERO, size))
			if plank.size.x > 0.0 and plank.size.y > 0.0:
				var c := _varied(ix, iy, 0.14)
				draw_rect(plank, c)
				draw_line(plank.position + Vector2(4, plank_h * 0.45), Vector2(plank.end.x - 6, plank.position.y + plank_h * 0.4), c.darkened(0.08), 1.5)
				draw_line(plank.position + Vector2(1, 1), Vector2(plank.end.x - 1, plank.position.y + 1), Color(1, 1, 1, 0.1), 1.5)
			x += length
			ix += 1


func _draw_metal() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), base_color.darkened(0.25))
	var cols := ceili(size.x / tile_size)
	var rows := ceili(size.y / tile_size)
	var bounds := Rect2(Vector2.ZERO, size)
	var tread := base_color.lightened(0.12)
	for iy in rows:
		for ix in cols:
			var plate := Rect2(ix * tile_size, iy * tile_size, tile_size, tile_size).grow(-1.0).intersection(bounds)
			if plate.size.x <= 0.0 or plate.size.y <= 0.0:
				continue
			draw_rect(plate, _varied(ix, iy, 0.06))
			# Kaymaz metal desen
			var step := 13.0
			var py := plate.position.y + 8.0
			var row := 0
			while py < plate.end.y - 4.0:
				var px := plate.position.x + 8.0 + (6.0 if row % 2 == 1 else 0.0)
				while px < plate.end.x - 6.0:
					var d := Vector2(3, -3) if (row % 2 == 0) else Vector2(3, 3)
					draw_line(Vector2(px, py) - d, Vector2(px, py) + d, tread, 2.0)
					px += step
				py += step * 0.7
				row += 1
			for corner in [plate.position + Vector2(5, 5), Vector2(plate.end.x - 5, plate.position.y + 5),
					Vector2(plate.position.x + 5, plate.end.y - 5), plate.end - Vector2(5, 5)]:
				draw_circle(corner, 2.0, base_color.darkened(0.35))


func _draw_concrete() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), base_color.darkened(0.12))
	var slab := tile_size * 2.0
	var cols := ceili(size.x / slab)
	var rows := ceili(size.y / slab)
	var bounds := Rect2(Vector2.ZERO, size)
	for iy in rows:
		for ix in cols:
			var r := Rect2(ix * slab, iy * slab, slab, slab).grow(-1.5).intersection(bounds)
			if r.size.x <= 0.0 or r.size.y <= 0.0:
				continue
			draw_rect(r, _varied(ix, iy, 0.07))
			for s in 6:
				var p := r.position + Vector2(DrawUtils.hash01(ix * 13 + s, iy, variation_seed) * r.size.x,
					DrawUtils.hash01(ix, iy * 17 + s, variation_seed) * r.size.y)
				draw_circle(p, 1.5 + DrawUtils.hash01(s, ix + iy, 3) * 1.5, base_color.darkened(0.15))
			if DrawUtils.hash01(ix, iy, variation_seed + 99) > 0.72:
				var a := r.position + Vector2(r.size.x * 0.2, r.size.y * 0.3)
				var crack := PackedVector2Array([a, a + Vector2(18, 10), a + Vector2(30, 6), a + Vector2(46, 20)])
				draw_polyline(crack, base_color.darkened(0.28), 1.5, true)
