extends Node2D
## KAOS FABRIKASI HARITASI
## Haritanin kendisi kaos_fabrikasi.tscn icinde (Godot editorunde acip
## objeleri surukleyerek duzenleyebilirsiniz). Bu script sadece:
##  - oyuncuyu dogma noktasina yerlestirir,
##  - kamerayi harita sinirlarina gore ayarlar,
##  - HUD ve duraklatma menusunu oyuncuya baglar.
##
## Katmanlar (yukaridan asagi cizim sirasi):
##  Floors      -> oda zeminleri
##  FloorDecals -> zemin boyalari, lekeler
##  Conveyors   -> tasima bantlari
##  Walls       -> duvarlar
##  Doors       -> otomatik kapilar
##  World       -> oyuncular + objeler (Y'ye gore siralanir: asagidaki one cizilir)

const PLAYER_SCENE := preload("res://scenes/player/player.tscn")

## Haritanin piksel olarak siniri (kamera bunun disina cikmaz).
@export var world_rect: Rect2i = Rect2i(0, 0, 2560, 1664)

@onready var world: Node2D = $World
@onready var spawn_points: Node2D = $SpawnPoints
@onready var hud: CanvasLayer = $HUD
@onready var pause_menu: CanvasLayer = $PauseMenu

var local_player: Player


func _ready() -> void:
	local_player = spawn_player(0, GameManager.player_color)
	hud.set_player(local_player)
	pause_menu.opened.connect(_on_pause_menu_opened)
	pause_menu.closed.connect(_on_pause_menu_closed)


## Bir oyuncuyu verilen numarali dogma noktasinda olusturur.
## AŞAMA 5'te her baglanan oyuncu icin bu fonksiyon cagrilacak.
func spawn_player(spawn_index: int, color: Color) -> Player:
	var player: Player = PLAYER_SCENE.instantiate()
	var markers := spawn_points.get_children()
	var marker := markers[spawn_index % markers.size()] as Node2D
	player.position = marker.position
	player.body_color = color
	world.add_child(player)
	player.set_camera_limits(world_rect)
	return player


func _on_pause_menu_opened() -> void:
	local_player.input_enabled = false


func _on_pause_menu_closed() -> void:
	local_player.input_enabled = true
