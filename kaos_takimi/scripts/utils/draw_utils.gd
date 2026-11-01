@tool
class_name DrawUtils
extends RefCounted
## Kodla cizim icin ortak yardimci fonksiyonlar.
## Henuz gercek resim (sprite) dosyalarimiz olmadigi icin haritadaki her sey
## bu fonksiyonlarla "elle" ciziliyor. Ileride gercek cizimler gelince
## bu dosyaya olan ihtiyac azalacak.

## Tum objelerde kullanilan koyu cizgi film kontur rengi.
const OUTLINE := Color("1d1530")
## Yere dusen golgelerin rengi (yari saydam).
const SHADOW := Color(0.0, 0.0, 0.0, 0.28)


## Elips (oval) seklinin kose noktalarini verir.
static func ellipse_points(center: Vector2, radii: Vector2, segments: int = 28) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in segments:
		var a := TAU * float(i) / float(segments)
		pts.append(center + Vector2(cos(a) * radii.x, sin(a) * radii.y))
	return pts


## Koseleri yuvarlatilmis dikdortgenin kose noktalarini verir.
static func rounded_rect_points(rect: Rect2, radius: float, corner_segments: int = 5) -> PackedVector2Array:
	var r := minf(radius, minf(rect.size.x, rect.size.y) * 0.5)
	var pts := PackedVector2Array()
	if r <= 0.5:
		pts.append(rect.position)
		pts.append(Vector2(rect.end.x, rect.position.y))
		pts.append(rect.end)
		pts.append(Vector2(rect.position.x, rect.end.y))
		return pts
	var centers := [
		Vector2(rect.end.x - r, rect.position.y + r),
		Vector2(rect.end.x - r, rect.end.y - r),
		Vector2(rect.position.x + r, rect.end.y - r),
		Vector2(rect.position.x + r, rect.position.y + r),
	]
	var start_angles := [-PI * 0.5, 0.0, PI * 0.5, PI]
	for c in 4:
		for i in corner_segments + 1:
			var a: float = start_angles[c] + (PI * 0.5) * float(i) / float(corner_segments)
			pts.append(centers[c] + Vector2(cos(a), sin(a)) * r)
	return pts


## Kapali bir sekli dolu cizer, istenirse etrafina kontur cizer.
static func fill_shape(canvas: CanvasItem, pts: PackedVector2Array, fill: Color,
		outline: Color = OUTLINE, outline_width: float = 0.0) -> void:
	canvas.draw_colored_polygon(pts, fill)
	if outline_width > 0.0:
		var closed := pts.duplicate()
		closed.append(pts[0])
		canvas.draw_polyline(closed, outline, outline_width, true)


## Yuvarlak koseli kutu.
static func rounded_box(canvas: CanvasItem, rect: Rect2, radius: float, fill: Color,
		outline: Color = OUTLINE, outline_width: float = 0.0) -> void:
	fill_shape(canvas, rounded_rect_points(rect, radius), fill, outline, outline_width)


## Elips.
static func ellipse(canvas: CanvasItem, center: Vector2, radii: Vector2, fill: Color,
		outline: Color = OUTLINE, outline_width: float = 0.0) -> void:
	fill_shape(canvas, ellipse_points(center, radii), fill, outline, outline_width)


## Objelerin altina yumusak oval golge.
static func soft_shadow(canvas: CanvasItem, center: Vector2, radii: Vector2) -> void:
	canvas.draw_colored_polygon(ellipse_points(center, radii * 1.15), Color(0, 0, 0, 0.12))
	canvas.draw_colored_polygon(ellipse_points(center, radii), SHADOW)


## Sari-siyah ikaz seridi (verilen dikdortgenin icine).
static func hazard_stripes(canvas: CanvasItem, rect: Rect2, stripe_width: float = 14.0,
		color_a: Color = Color("ffc531"), color_b: Color = Color("2a2236")) -> void:
	canvas.draw_rect(rect, color_a)
	var h := rect.size.y
	var x := rect.position.x - h
	while x < rect.end.x:
		var poly := PackedVector2Array([
			Vector2(x, rect.end.y), Vector2(x + stripe_width, rect.end.y),
			Vector2(x + stripe_width + h, rect.position.y), Vector2(x + h, rect.position.y),
		])
		var clipped := Geometry2D.intersect_polygons(poly, PackedVector2Array([
			rect.position, Vector2(rect.end.x, rect.position.y), rect.end, Vector2(rect.position.x, rect.end.y),
		]))
		for c in clipped:
			canvas.draw_colored_polygon(c, color_b)
		x += stripe_width * 2.0


## Her tile icin her seferinde ayni cikan "rastgele" sayi (0..1).
## Boylece zemin her acilista ayni gorunur.
static func hash01(x: int, y: int, seed_value: int = 0) -> float:
	var h := hash(Vector3i(x, y, seed_value))
	return float(h % 10007) / 10007.0


## Yukaridan-capraz (3/4) bakista bir kutu cizer.
## x: sol kenar, bottom_y: on yuzun alt kenari (yere degdigi yer).
## depth: ust yuzun derinligi, height: on yuzun yuksekligi.
static func box_3d(canvas: CanvasItem, x: float, bottom_y: float, width: float, depth: float,
		height: float, top_color: Color, front_color: Color, outline_width: float = 2.0) -> void:
	var front := Rect2(x, bottom_y - height, width, height)
	var top := Rect2(x, bottom_y - height - depth, width, depth)
	canvas.draw_rect(front, front_color)
	canvas.draw_rect(top, top_color)
	canvas.draw_rect(Rect2(x, top.position.y, width, 2.5), top_color.lightened(0.25))
	if outline_width > 0.0:
		canvas.draw_rect(Rect2(x, top.position.y, width, depth + height), OUTLINE, false, outline_width)
		canvas.draw_line(Vector2(x, front.position.y), Vector2(x + width, front.position.y), OUTLINE, outline_width * 0.8)
