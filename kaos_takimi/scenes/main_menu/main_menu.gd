extends Control
## ANA MENU
## Butonlarin ne yapacagini ve menudeki animasyonlari yonetir.

const PARADE_COLORS: Array[Color] = [
	Color("ff5d73"), Color("4fd1ff"), Color("59f0a6"), Color("ffc531"),
	Color("b57cff"), Color("ff8a3d"), Color("f7f7f7"), Color("3d6fd9"),
]

@onready var background: Control = $Background
@onready var parade: Node2D = $Parade
@onready var logo: Control = $Margin/HBox/Left/Logo
@onready var preview_area: Control = $Margin/HBox/PreviewArea
@onready var preview: PlayerVisual = $Preview
@onready var toast: PanelContainer = $Toast
@onready var toast_label: Label = $Toast/Label
@onready var play_button: Button = $Margin/HBox/Left/Buttons/PlayButton
@onready var buttons: VBoxContainer = $Margin/HBox/Left/Buttons

var _walkers: Array[PlayerVisual] = []
var _toast_tween: Tween
var _preview_color_index := 0


func _ready() -> void:
	toast.visible = false
	preview.body_color = GameManager.player_color
	_connect_buttons()
	_spawn_parade()
	_animate_logo()
	_animate_buttons_in()
	play_button.grab_focus()
	resized.connect(_layout_preview)
	preview_area.resized.connect(_layout_preview)
	_layout_preview.call_deferred()


func _connect_buttons() -> void:
	$Margin/HBox/Left/Buttons/PlayButton.pressed.connect(_on_play_pressed)
	$Margin/HBox/Left/Buttons/CreateRoomButton.pressed.connect(
		_show_toast.bind("Oda kurma AŞAMA 5'te geliyor!"))
	$Margin/HBox/Left/Buttons/JoinRoomButton.pressed.connect(
		_show_toast.bind("Odaya katılma AŞAMA 5'te geliyor!"))
	$Margin/HBox/Left/Buttons/CharacterButton.pressed.connect(_on_character_pressed)
	$Margin/HBox/Left/Buttons/SettingsButton.pressed.connect(
		_show_toast.bind("Ayarlar yakında! (Tam ekran için F11)"))
	$QuitButton.pressed.connect(GameManager.quit_game)
	for child in buttons.get_children():
		if child is Button:
			var button := child as Button
			button.mouse_entered.connect(_on_button_hover.bind(button, true))
			button.mouse_exited.connect(_on_button_hover.bind(button, false))
			button.focus_entered.connect(_on_button_hover.bind(button, true))
			button.focus_exited.connect(_on_button_hover.bind(button, false))
			button.resized.connect(func() -> void: button.pivot_offset = button.size * 0.5)


func _on_play_pressed() -> void:
	GameManager.start_local_game()


## Simdilik KARAKTERİM: onizlemedeki karakterin rengini degistirir.
## AŞAMA 2'de ayri bir karakter ekrani olacak.
func _on_character_pressed() -> void:
	_preview_color_index = (_preview_color_index + 1) % PARADE_COLORS.size()
	GameManager.player_color = PARADE_COLORS[_preview_color_index]
	preview.body_color = GameManager.player_color
	var tween := create_tween()
	tween.tween_property(preview, "scale", Vector2(5.2, 4.2), 0.08)
	tween.tween_property(preview, "scale", Vector2(4.5, 4.5), 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_show_toast("Renk değişti! Karakter ekranı AŞAMA 2'de.")


func _on_button_hover(button: Button, hovered: bool) -> void:
	var tween := button.create_tween()
	tween.tween_property(button, "scale", Vector2(1.06, 1.06) if hovered else Vector2.ONE, 0.12)\
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func _show_toast(text: String) -> void:
	toast_label.text = text
	toast.visible = true
	toast.reset_size()
	toast.position = Vector2((size.x - toast.size.x) * 0.5, size.y - 170.0)
	toast.modulate.a = 0.0
	if _toast_tween:
		_toast_tween.kill()
	_toast_tween = create_tween()
	_toast_tween.tween_property(toast, "modulate:a", 1.0, 0.15)
	_toast_tween.tween_interval(2.2)
	_toast_tween.tween_property(toast, "modulate:a", 0.0, 0.3)
	_toast_tween.tween_callback(func() -> void: toast.visible = false)


func _animate_logo() -> void:
	logo.pivot_offset = logo.size * 0.5
	var tween := create_tween().set_loops()
	tween.tween_property(logo, "rotation", deg_to_rad(-1.5), 1.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.tween_property(logo, "rotation", deg_to_rad(1.5), 1.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func _animate_buttons_in() -> void:
	var i := 0
	for child in buttons.get_children():
		var control := child as Control
		control.modulate.a = 0.0
		var tween := create_tween()
		tween.tween_interval(0.08 * i)
		tween.tween_property(control, "modulate:a", 1.0, 0.25)
		i += 1


func _spawn_parade() -> void:
	for i in PARADE_COLORS.size():
		var walker := PlayerVisual.new()
		walker.body_color = PARADE_COLORS[i]
		walker.scale = Vector2(1.5, 1.5)
		walker.position.x = i * 190.0 + randf_range(-30.0, 30.0)
		walker.set_fake_walk(1.0, 1.0)
		parade.add_child(walker)
		_walkers.append(walker)


func _process(delta: float) -> void:
	var belt_y: float = background.get_belt_y()
	var wrap_width := maxf(size.x + 200.0, PARADE_COLORS.size() * 190.0)
	for walker in _walkers:
		walker.position.x += 70.0 * delta
		if walker.position.x > size.x + 60.0:
			walker.position.x -= wrap_width
		walker.position.y = belt_y
	# Onizleme karakteri ara sira saga sola bakar
	var look := sin(Time.get_ticks_msec() / 1400.0)
	preview.set_fake_walk(0.0, 1.0 if look > 0.0 else -1.0)


func _layout_preview() -> void:
	var rect := preview_area.get_global_rect()
	var center := Vector2(rect.get_center().x, rect.position.y + rect.size.y * 0.72)
	preview.visible = rect.size.x > 220.0
	preview.position = center
	background.pedestal_center = center if preview.visible else Vector2(-1000, -1000)
