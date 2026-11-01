extends CanvasLayer
## OYUN ICI EKRAN BILGILERI (HUD)
## Sol ustte harita adi ve oyuncunun bulundugu oda, sag ustte tus bilgisi.
## AŞAMA 3'te gorev listesi, sure ve puan buraya eklenecek.

@onready var room_label: Label = %RoomLabel
@onready var room_panel: PanelContainer = %RoomPanel

var _player: Node2D
var _current_room := ""


## Harita, takip edilecek oyuncuyu buradan verir.
func set_player(player: Node2D) -> void:
	_player = player


func _process(_delta: float) -> void:
	if _player == null or not is_instance_valid(_player):
		return
	var room := _find_room_name(_player.global_position)
	if room != _current_room:
		_current_room = room
		room_label.text = room
		_pop(room_panel)


func _find_room_name(point: Vector2) -> String:
	for room in get_tree().get_nodes_in_group("rooms"):
		if room.contains_global_point(point):
			return room.room_name
	return "Kapı Önü"


func _pop(control: Control) -> void:
	control.pivot_offset = Vector2(0, control.size.y * 0.5)
	var tween := create_tween()
	tween.tween_property(control, "scale", Vector2(1.08, 1.08), 0.08)
	tween.tween_property(control, "scale", Vector2.ONE, 0.2).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
