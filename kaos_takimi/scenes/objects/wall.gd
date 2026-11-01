@tool
class_name FactoryWall
extends FactoryProp
## DUVAR
## (0, 0) sol-ust kosedir. "size" ile boyutu ayarlanir.
## Ust kisim (acik renk) duvarin tepesi, alt kisim (koyu) on yuzudur.

const FACE_HEIGHT := 20.0

@export var size: Vector2 = Vector2(256, 44):
	set(value):
		size = value.max(Vector2(8, 8))
		queue_redraw()
@export var cap_color: Color = Color("5d5a8c"):
	set(value):
		cap_color = value
		queue_redraw()
@export var face_color: Color = Color("3b3866"):
	set(value):
		face_color = value
		queue_redraw()


func _footprint() -> Rect2:
	return Rect2(Vector2.ZERO, size)


func _draw() -> void:
	var face_h := minf(FACE_HEIGHT, size.y * 0.45)
	var cap := Rect2(0, 0, size.x, size.y - face_h)
	var face := Rect2(0, size.y - face_h, size.x, face_h)

	# Yere dusen golge
	draw_rect(Rect2(0, size.y, size.x, 9), Color(0, 0, 0, 0.25))
	draw_rect(Rect2(0, size.y + 9, size.x, 7), Color(0, 0, 0, 0.1))

	# On yuz: metal paneller ve vidalar
	draw_rect(face, face_color)
	var seam_x := 64.0
	while seam_x < size.x - 6.0:
		draw_line(Vector2(seam_x, face.position.y + 3), Vector2(seam_x, face.end.y - 5), face_color.darkened(0.3), 2.0)
		draw_circle(Vector2(seam_x - 7, face.position.y + 6), 1.6, face_color.lightened(0.25))
		draw_circle(Vector2(seam_x + 7, face.position.y + 6), 1.6, face_color.lightened(0.25))
		seam_x += 64.0
	draw_rect(Rect2(0, size.y - 5, size.x, 5), face_color.darkened(0.35))

	# Ust yuz
	draw_rect(cap, cap_color)
	draw_rect(Rect2(0, 0, size.x, 3), cap_color.lightened(0.22))
	if cap.size.x > 14 and cap.size.y > 14:
		draw_rect(Rect2(5, 5, cap.size.x - 10, cap.size.y - 10), cap_color.darkened(0.1), false, 2.0)

	# Kontur
	draw_rect(Rect2(Vector2.ZERO, size), DrawUtils.OUTLINE, false, 2.5)
	draw_line(Vector2(0, face.position.y), Vector2(size.x, face.position.y), DrawUtils.OUTLINE, 2.0)
