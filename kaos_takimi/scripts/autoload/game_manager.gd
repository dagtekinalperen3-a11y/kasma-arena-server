extends Node
## OYUN YONETICISI (Autoload)
## Bu script oyun acildigi anda otomatik yuklenir ve oyun kapanana kadar yasar.
## Her yerden "GameManager" adiyla ulasilabilir. Ornek: GameManager.start_local_game()
##
## Gorevleri:
##  - Sahneler arasi gecis (ekran kararip acilarak)
##  - Oyuncu adi / rengi gibi oyun boyunca saklanan bilgiler
##  - F11 ile tam ekran

const MAIN_MENU_SCENE := "res://scenes/main_menu/main_menu.tscn"
const KAOS_FABRIKASI_SCENE := "res://scenes/maps/kaos_fabrikasi/kaos_fabrikasi.tscn"

## Oyuncunun secili adi ve rengi (AŞAMA 2'de KARAKTERİM ekranindan degisecek).
var player_name: String = "Oyuncu"
var player_color: Color = Color("ff5d73")

var _fade_rect: ColorRect
var _is_changing_scene := false


func _ready() -> void:
	# Oyun dursa bile bu dugum calismaya devam etsin.
	process_mode = Node.PROCESS_MODE_ALWAYS
	_create_fade_layer()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_fullscreen"):
		toggle_fullscreen()


## Ana menuye don.
func go_to_main_menu() -> void:
	change_scene(MAIN_MENU_SCENE)


## Tek kisilik (yerel) test oyununu baslat.
func start_local_game() -> void:
	change_scene(KAOS_FABRIKASI_SCENE)


func quit_game() -> void:
	get_tree().quit()


func toggle_fullscreen() -> void:
	if DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)


## Ekrani karartip yeni sahneye gecer, sonra ekrani tekrar acar.
func change_scene(scene_path: String) -> void:
	if _is_changing_scene:
		return
	_is_changing_scene = true
	_fade_rect.mouse_filter = Control.MOUSE_FILTER_STOP

	var fade_out := create_tween()
	fade_out.tween_property(_fade_rect, "modulate:a", 1.0, 0.25)
	await fade_out.finished

	var error := get_tree().change_scene_to_file(scene_path)
	if error != OK:
		push_error("Sahne yuklenemedi: %s (hata kodu %d)" % [scene_path, error])

	# Yeni sahnenin yerlesmesi icin iki kare bekle.
	await get_tree().process_frame
	await get_tree().process_frame

	var fade_in := create_tween()
	fade_in.tween_property(_fade_rect, "modulate:a", 0.0, 0.35)
	await fade_in.finished
	_fade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_is_changing_scene = false


func _create_fade_layer() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 100
	add_child(layer)
	_fade_rect = ColorRect.new()
	_fade_rect.color = Color("140f28")
	_fade_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade_rect.modulate.a = 0.0
	layer.add_child(_fade_rect)
