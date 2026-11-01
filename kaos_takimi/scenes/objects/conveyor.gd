@tool
class_name Conveyor
extends Node2D
## TASIMA BANDI (hareketli)
## (0, 0) bandin sol ucunun ortasidir; bant +X yonune akar.
## Farkli yon icin dugumu dondurun (rotation).
## Simdilik sadece gorsel. AŞAMA 4'te "Hizli bant" olayi oyunculari itecek.

@export var length: float = 384.0:
	set(value):
		length = maxf(value, 64.0)
		queue_redraw()
@export var belt_width: float = 52.0:
	set(value):
		belt_width = value
		queue_redraw()
## Bandin hizi (piksel / saniye).
@export var speed: float = 55.0
@export var carry_boxes: bool = true:
	set(value):
		carry_boxes = value
		queue_redraw()

const CHEVRON_GAP := 28.0
const BOX_GAP := 120.0

var _scroll := 0.0


func _process(delta: float) -> void:
	_scroll += speed * delta
	if _scroll > 100000.0:
		_scroll = 0.0
	queue_redraw()


func _draw() -> void:
	var hw := belt_width * 0.5
	draw_rect(Rect2(-6, hw + 10, length + 12, 10), Color(0, 0, 0, 0.22))
	# Raylar
	var rail := Color("5c5f78")
	draw_rect(Rect2(-10, -hw - 9, length + 20, 9), rail.lightened(0.15))
	draw_rect(Rect2(-10, hw, length + 20, 12), rail.darkened(0.2))
	# Bant
	var belt := Rect2(0, -hw, length, belt_width)
	draw_rect(belt, Color("2d2b3d"))
	var offset := fmod(_scroll, CHEVRON_GAP)
	var cx := -CHEVRON_GAP + offset
	while cx < length:
		if cx > 4.0 and cx + 12.0 < length - 4.0:
			draw_polyline(PackedVector2Array([Vector2(cx, -hw + 9), Vector2(cx + 12, 0), Vector2(cx, hw - 9)]),
				Color("ffc531", 0.55), 3.0, true)
		cx += CHEVRON_GAP
	# Uclardaki silindirler
	for end_x in [0.0, length]:
		DrawUtils.ellipse(self, Vector2(end_x, 0), Vector2(9, hw + 2), Color("8a8fab"), DrawUtils.OUTLINE, 2.0)
		draw_circle(Vector2(end_x, 0), 3.0, Color("2d2b3d"))
	# Kontur
	draw_rect(Rect2(-10, -hw - 9, length + 20, belt_width + 21), DrawUtils.OUTLINE, false, 2.0)
	# Uzerinde giden kutular
	if carry_boxes:
		var box_offset := fmod(_scroll, BOX_GAP)
		var bx := -BOX_GAP + box_offset
		var i := -int(_scroll / BOX_GAP)  # her kutu rengini korusun
		while bx < length:
			if bx > 6.0 and bx + 26.0 < length - 6.0:
				var c := Color("d9a66b") if posmod(i, 2) == 0 else Color("8da2b5")
				DrawUtils.box_3d(self, bx, hw * 0.45, 26, 14, 16, c, c.darkened(0.25))
			bx += BOX_GAP
			i += 1
