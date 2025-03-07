from PIL import Image, ImageDraw, ImageFont

# Размер изображения
width, height = 1280, 720

# Создание изображения с белым фоном
image = Image.new("L", (width, height), 255)
draw = ImageDraw.Draw(image)

# Попытка загрузки шрифта с масштабированием
font = ImageFont.load_default(280)

# Определяем границы текста
text = "NeuroFlex"
while True:
    bbox = draw.textbbox((0, 0), text, font=font)  # Получаем размеры
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # if text_width < width * 0.95 and text_height < height * 0.95:  # Чуть меньше границ
    break

# Центрируем текст
text_x = (width - text_width) // 2
text_y = (height - text_height) // 2

# Рисуем текст
draw.text((text_x, text_y), text, fill=0, font=font)

# Сохранение
mask_path = "neuroflex_mask.png"
image.save(mask_path)
