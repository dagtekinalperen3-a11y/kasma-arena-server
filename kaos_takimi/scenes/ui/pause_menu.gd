extends CanvasLayer
## DURAKLATMA MENUSU (ESC)
## Not: Oyunu gercekten DURDURMUYORUZ (get_tree().paused kullanmiyoruz),
## cunku online oyunda bir kisi menu acinca herkesin oyunu durmamali.
## Sadece menuyu gosterip oyuncunun kontrolunu kapatiyoruz.

signal opened
signal closed

@onready var root: Control = $Root
@onready var resume_button: Button = %ResumeButton
@onready var menu_button: Button = %MainMenuButton


func _ready() -> void:
	root.visible = false
	resume_button.pressed.connect(close)
	menu_button.pressed.connect(_on_main_menu_pressed)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		if root.visible:
			close()
		else:
			open()
		get_viewport().set_input_as_handled()


func is_open() -> bool:
	return root.visible


func open() -> void:
	root.visible = true
	root.modulate.a = 0.0
	create_tween().tween_property(root, "modulate:a", 1.0, 0.12)
	resume_button.grab_focus()
	opened.emit()


func close() -> void:
	root.visible = false
	closed.emit()


func _on_main_menu_pressed() -> void:
	GameManager.go_to_main_menu()
