@tool
class_name TaskPoint
extends Node2D
## GOREV NOKTASI (simdilik sadece isaret)
## Haritada gorevlerin yapilacagi yerleri gosterir. Parlayan bir zemin
## isareti ve uzerinde suzulen bir ikon cizer.
## AŞAMA 3'te gorev sistemi bu noktalari "task_points" grubundan bulacak.

@export var task_id: String = "gorev_noktasi"
@export var point_color: Color = Color("59f0a6"):
	set(value):
		point_color = value
		queue_redraw()
@export var title: String = "GÖREV":
	set(value):
		title = value
		queue_redraw()

const LABEL_FONT := preload("res://assets/fonts/Baloo2-ExtraBold.ttf")

var _t := 0.0


func _ready() -> void:
	if not Engine.is_editor_hint():
		add_to_group("task_points")


func _process(delta: float) -> void:
	_t += delta
	queue_redraw()


func _draw() -> void:
	var pulse := sin(_t * 3.0) * 0.5 + 0.5
	var glow := point_color
	glow.a = 0.18 + pulse * 0.12
	DrawUtils.ellipse(self, Vector2.ZERO, Vector2(44, 20) * (1.0 + pulse * 0.08), glow)
	var ring := point_color
	ring.a = 0.9
	var ring_pts := DrawUtils.ellipse_points(Vector2.ZERO, Vector2(34, 15), 32)
	ring_pts.append(ring_pts[0])
	draw_polyline(ring_pts, ring, 3.0, true)
	var inner := DrawUtils.ellipse_points(Vector2.ZERO, Vector2(22, 9), 32)
	inner.append(inner[0])
	draw_polyline(inner, Color(ring, 0.5), 2.0, true)

	# Suzulen ikon
	var icon_y := -54.0 + sin(_t * 2.2) * 5.0
	DrawUtils.ellipse(self, Vector2(0, -6), Vector2(10 - pulse * 2.0, 4), Color(0, 0, 0, 0.2))
	var bubble := DrawUtils.rounded_rect_points(Rect2(-15, icon_y - 15, 30, 30), 10.0)
	DrawUtils.fill_shape(self, bubble, point_color, DrawUtils.OUTLINE, 2.5)
	DrawUtils.fill_shape(self, PackedVector2Array([Vector2(-5, icon_y + 13), Vector2(5, icon_y + 13), Vector2(0, icon_y + 21)]),
		point_color, DrawUtils.OUTLINE, 2.0)
	draw_rect(Rect2(-6, icon_y + 11, 12, 4), point_color)
	draw_line(Vector2(0, icon_y - 8), Vector2(0, icon_y + 3), DrawUtils.OUTLINE, 4.5, true)
	draw_circle(Vector2(0, icon_y + 8.5), 2.6, DrawUtils.OUTLINE)

	var font_size := 15
	var text_w := LABEL_FONT.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	draw_string_outline(LABEL_FONT, Vector2(-text_w * 0.5, 34), title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, 5, DrawUtils.OUTLINE)
	draw_string(LABEL_FONT, Vector2(-text_w * 0.5, 34), title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color.WHITE)
