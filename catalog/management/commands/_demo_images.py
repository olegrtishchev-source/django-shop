"""Генерация простых тематических иконок-плейсхолдеров для демотоваров
(используется только seed_demo — своих фотографий товаров у нас нет, а
карточки на фронтенде безусловно обращаются к images[0].src, без картинки
падают). Каждому виду товара — свой узнаваемый силуэт и свой цвет, чтобы не
получилось «холодильник с картинкой наушников»."""
import io

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

SIZE = 600


def _canvas(bg):
    img = Image.new('RGB', (SIZE, SIZE), bg)
    return img, ImageDraw.Draw(img)


def _laptop(bg, fg, accent):
    img, d = _canvas(bg)
    d.rounded_rectangle([140, 120, 460, 360], radius=18, outline=fg, width=10)
    d.rounded_rectangle([165, 145, 435, 335], radius=8, fill=accent)
    d.polygon([(110, 400), (490, 400), (460, 440), (140, 440)], fill=fg)
    d.rectangle([100, 440, 500, 460], fill=fg)
    return img


def _smartphone(bg, fg, accent):
    img, d = _canvas(bg)
    d.rounded_rectangle([210, 90, 390, 510], radius=36, outline=fg, width=10)
    d.rounded_rectangle([230, 130, 370, 460], radius=10, fill=accent)
    d.ellipse([288, 100, 312, 124], outline=fg, width=6)
    d.rounded_rectangle([275, 478, 325, 492], radius=6, fill=fg)
    return img


def _earbuds(bg, fg, accent):
    img, d = _canvas(bg)
    for cx in (220, 380):
        d.ellipse([cx - 55, 220, cx + 55, 330], fill=fg)
        d.rectangle([cx - 18, 320, cx + 18, 420], fill=fg)
        d.ellipse([cx - 20, 400, cx + 20, 440], fill=accent)
    return img


def _headphones(bg, fg, accent):
    img, d = _canvas(bg)
    d.arc([140, 100, 460, 460], start=180, end=360, fill=fg, width=22)
    d.line([140, 280, 140, 380], fill=fg, width=22)
    d.line([460, 280, 460, 380], fill=fg, width=22)
    d.rounded_rectangle([90, 330, 200, 460], radius=30, fill=fg)
    d.rounded_rectangle([400, 330, 510, 460], radius=30, fill=fg)
    d.ellipse([120, 370, 170, 420], fill=accent)
    d.ellipse([430, 370, 480, 420], fill=accent)
    return img


def _graphics_card(bg, fg, accent):
    img, d = _canvas(bg)
    d.rounded_rectangle([90, 260, 510, 360], radius=10, outline=fg, width=8)
    d.rounded_rectangle([120, 160, 480, 280], radius=20, fill=fg)
    for cx in (220, 320, 420):
        d.ellipse([cx - 40, 180, cx + 40, 260], outline=accent, width=8)
        d.ellipse([cx - 6, 214, cx + 6, 226], fill=accent)
    d.rectangle([70, 270, 90, 420], fill=fg)
    for y in (290, 320, 350, 380):
        d.rectangle([74, y, 86, y + 14], fill=accent)
    for x in range(150, 480, 22):
        d.rectangle([x, 362, x + 12, 390], fill=fg)
    return img


def _ssd_stick(bg, fg, accent):
    img, d = _canvas(bg)
    d.rectangle([120, 250, 460, 340], fill=fg)
    d.polygon([(120, 250), (150, 250), (135, 285), (120, 285)], fill=accent)
    for x in (170, 230, 290):
        d.rectangle([x, 265, x + 45, 325], fill=accent)
    d.rectangle([355, 270, 440, 320], outline=accent, width=6)
    d.ellipse([455, 335, 471, 351], fill=fg)
    return img


def _motherboard(bg, fg, accent):
    img, d = _canvas(bg)
    d.rounded_rectangle([110, 110, 490, 490], radius=14, outline=fg, width=10)
    d.rectangle([160, 150, 300, 260], outline=fg, width=8)
    for i in range(6):
        y = 300 + i * 25
        d.line([160, y, 300, y], fill=fg, width=4)
    for cx in (380, 440):
        d.ellipse([cx - 14, 150, cx + 14, 178], fill=fg)
    d.rectangle([340, 320, 460, 460], outline=fg, width=8)
    return img


def _robot_vacuum(bg, fg, accent):
    img, d = _canvas(bg)
    d.ellipse([120, 120, 480, 480], outline=fg, width=14)
    d.ellipse([270, 180, 330, 240], fill=accent)
    d.arc([160, 160, 440, 440], start=200, end=340, fill=fg, width=6)
    return img


def _multicooker(bg, fg, accent):
    img, d = _canvas(bg)
    d.rounded_rectangle([170, 260, 430, 460], radius=16, fill=fg)
    d.rounded_rectangle([130, 300, 175, 340], radius=10, fill=fg)
    d.rounded_rectangle([425, 300, 470, 340], radius=10, fill=fg)
    d.pieslice([170, 170, 430, 290], start=180, end=360, fill=fg)
    d.ellipse([282, 168, 318, 190], fill=fg)
    d.rectangle([200, 350, 400, 358], fill=accent)
    return img


def _coffee_machine(bg, fg, accent):
    img, d = _canvas(bg)
    d.rounded_rectangle([180, 120, 420, 380], radius=14, fill=fg)
    d.rectangle([220, 380, 260, 430], fill=fg)
    d.polygon([(230, 430), (250, 430), (260, 470), (220, 470)], fill=accent)
    d.ellipse([260, 190, 300, 230], fill=accent)
    return img


# (функция-рисовалка, фон, цвет фигуры, акцентный цвет — обычно белый)
_ICONS = {
    'laptop': (_laptop, (219, 234, 254), (37, 99, 235), (255, 255, 255)),
    'smartphone': (_smartphone, (220, 252, 231), (22, 163, 74), (255, 255, 255)),
    'earbuds': (_earbuds, (255, 237, 213), (234, 88, 12), (255, 255, 255)),
    'headphones': (_headphones, (255, 237, 213), (194, 65, 12), (255, 255, 255)),
    'graphics_card': (_graphics_card, (237, 233, 254), (124, 58, 237), (255, 255, 255)),
    'ssd_stick': (_ssd_stick, (237, 233, 254), (109, 40, 217), (255, 255, 255)),
    'motherboard': (_motherboard, (237, 233, 254), (91, 33, 182), (91, 33, 182)),
    'robot_vacuum': (_robot_vacuum, (254, 226, 226), (220, 38, 38), (255, 255, 255)),
    'multicooker': (_multicooker, (254, 226, 226), (185, 28, 28), (255, 255, 255)),
    'coffee_machine': (_coffee_machine, (254, 226, 226), (153, 27, 27), (255, 255, 255)),
}


def generate_product_image(icon_key):
    """Возвращает ContentFile с PNG-иконкой для указанного вида товара —
    готов к присвоению в ImageField (product_image.image.save(name, файл))."""
    draw_fn, bg, fg, accent = _ICONS[icon_key]
    img = draw_fn(bg, fg, accent)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue())
