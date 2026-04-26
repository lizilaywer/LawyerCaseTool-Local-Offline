# -*- coding: utf-8 -*-
"""生成应用图标 - 现代扁平风格

设计理念：
- 主元素：文件夹 + 法律文档
- 风格：现代扁平化，圆角设计
- 主色调：专业蓝 #3b82f6
- 辅助色：白色、浅灰
"""

from PIL import Image, ImageDraw, ImageFilter
import os

# 图标尺寸列表（从大到小，包含所有常用尺寸）
SIZES = [1024, 512, 256, 192, 180, 152, 144, 128, 120, 114, 100, 96, 88, 76, 72, 64, 60, 57, 48, 40, 36, 32, 24, 20, 16]

# 配色方案
COLORS = {
    'primary': '#3b82f6',      # 主色：专业蓝
    'primary_dark': '#2563eb',  # 深色
    'primary_light': '#60a5fa', # 浅色
    'white': '#ffffff',
    'surface': '#f8fafc',
    'accent': '#10b981',       # 成功绿
}

def create_base_image(size):
    """创建基础图像（带透明背景）"""
    return Image.new('RGBA', (size, size), (0, 0, 0, 0))

def hex_to_rgb(hex_color):
    """十六进制颜色转RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def draw_rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = xy
    r = radius
    
    # 主体矩形
    draw.rectangle([x1+r, y1, x2-r, y2], fill=fill)
    draw.rectangle([x1, y1+r, x2, y2-r], fill=fill)
    
    # 四个角
    draw.ellipse([x1, y1, x1+r*2, y1+r*2], fill=fill)
    draw.ellipse([x2-r*2, y1, x2, y1+r*2], fill=fill)
    draw.ellipse([x1, y2-r*2, x1+r*2, y2], fill=fill)
    draw.ellipse([x2-r*2, y2-r*2, x2, y2], fill=fill)
    
    if outline:
        # 绘制边框（简化版）
        pass

def draw_folder_icon(size):
    """
    绘制文件夹+法律文档图标
    
    设计：
    - 背景：圆角方形，渐变蓝色
    - 主体：文件夹形状
    - 前景：文档/法槌元素
    """
    img = create_base_image(size)
    draw = ImageDraw.Draw(img)
    
    # 缩放比例
    scale = size / 1024
    
    # 1. 背景圆角方形
    padding = int(64 * scale)
    bg_rect = [padding, padding, size - padding, size - padding]
    corner_radius = int(180 * scale)
    
    # 绘制渐变效果（多层实现）
    primary = hex_to_rgb(COLORS['primary'])
    primary_dark = hex_to_rgb(COLORS['primary_dark'])
    
    # 主背景
    draw_rounded_rect(draw, bg_rect, corner_radius, primary)
    
    # 2. 文件夹主体
    folder_margin = int(200 * scale)
    folder_top = int(340 * scale)
    folder_rect = [
        folder_margin,
        folder_top,
        size - folder_margin,
        size - folder_margin
    ]
    folder_radius = int(80 * scale)
    
    # 文件夹 - 使用白色
    white = hex_to_rgb(COLORS['white'])
    draw_rounded_rect(draw, folder_rect, folder_radius, white)
    
    # 3. 文件夹标签（突出的部分）
    tab_width = int(280 * scale)
    tab_height = int(100 * scale)
    tab_rect = [
        folder_margin + int(40 * scale),
        folder_top - int(40 * scale),
        folder_margin + tab_width,
        folder_top + tab_height
    ]
    draw_rounded_rect(draw, tab_rect, int(40 * scale), white)
    
    # 4. 文档/法槌元素（象征法律文件）
    doc_margin = int(320 * scale)
    doc_top = int(240 * scale)
    doc_rect = [
        doc_margin,
        doc_top,
        size - doc_margin,
        size - doc_margin - int(40 * scale)
    ]
    doc_radius = int(60 * scale)
    
    # 文档背景 - 浅蓝色
    light_blue = hex_to_rgb(COLORS['primary_light'])
    draw_rounded_rect(draw, doc_rect, doc_radius, light_blue)
    
    # 5. 文档内容线条（模拟文字）
    line_color = white
    line_y_start = doc_top + int(80 * scale)
    line_height = int(24 * scale)
    line_gap = int(48 * scale)
    line_margin = int(60 * scale)
    
    for i in range(4):
        y = line_y_start + i * line_gap
        # 不同长度的线条
        if i == 0:
            line_width = int(200 * scale)
        elif i == 3:
            line_width = int(120 * scale)
        else:
            line_width = int(280 * scale)
        
        line_rect = [
            doc_margin + line_margin,
            y,
            doc_margin + line_margin + line_width,
            y + line_height
        ]
        draw_rounded_rect(draw, line_rect, line_height // 2, line_color)
    
    # 6. 装饰性法槌/天平元素（小圆点代表）
    accent = hex_to_rgb(COLORS['accent'])
    circle_x = size - int(280 * scale)
    circle_y = int(280 * scale)
    circle_r = int(40 * scale)
    draw.ellipse([
        circle_x - circle_r,
        circle_y - circle_r,
        circle_x + circle_r,
        circle_y + circle_r
    ], fill=accent)
    
    return img

def draw_simple_icon(size):
    """
    简化版图标（用于小尺寸）
    
    小尺寸下简化细节，保持清晰可辨
    """
    img = create_base_image(size)
    draw = ImageDraw.Draw(img)
    
    scale = size / 1024
    padding = int(64 * scale)
    
    primary = hex_to_rgb(COLORS['primary'])
    white = hex_to_rgb(COLORS['white'])
    
    # 简化的圆角方形背景
    rect = [padding, padding, size - padding, size - padding]
    radius = int(180 * scale)
    draw_rounded_rect(draw, rect, radius, primary)
    
    # 简化的文件夹
    folder_padding = int(220 * scale)
    folder_rect = [
        folder_padding,
        int(380 * scale),
        size - folder_padding,
        size - folder_padding
    ]
    folder_radius = int(60 * scale)
    draw_rounded_rect(draw, folder_rect, folder_radius, white)
    
    # 文档角标
    doc_size = int(200 * scale)
    doc_x = size - folder_padding - doc_size + int(40 * scale)
    doc_y = folder_padding + int(40 * scale)
    doc_rect = [doc_x, doc_y, doc_x + doc_size, doc_y + doc_size]
    doc_radius = int(40 * scale)
    
    light_blue = hex_to_rgb(COLORS['primary_light'])
    draw_rounded_rect(draw, doc_rect, doc_radius, light_blue)
    
    return img

def generate_all_icons():
    """生成所有尺寸的图标"""
    
    # 确保目录存在
    icons_dir = os.path.join(os.path.dirname(__file__), '..', 'resources', 'icons')
    icons_dir = os.path.abspath(icons_dir)
    os.makedirs(icons_dir, exist_ok=True)
    
    print(f"图标将保存到: {icons_dir}")
    print("=" * 60)
    
    # 生成各尺寸 PNG
    for size in SIZES:
        if size >= 64:
            img = draw_folder_icon(size)
        else:
            img = draw_simple_icon(size)
        
        # 保存 PNG
        png_path = os.path.join(icons_dir, f'app_icon_{size}x{size}.png')
        img.save(png_path, 'PNG')
        print(f"[OK] {size}x{size} PNG")
    
    # 生成 Windows ICO 文件（包含多尺寸）
    print("\n生成 Windows ICO 文件...")
    ico_sizes = [256, 128, 64, 48, 32, 24, 16]
    ico_images = []
    
    for size in ico_sizes:
        if size >= 64:
            img = draw_folder_icon(size)
        else:
            img = draw_simple_icon(size)
        ico_images.append(img)
    
    ico_path = os.path.join(icons_dir, 'app_icon.ico')
    ico_images[0].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_images[1:]
    )
    print(f"[OK] Windows ICO: {ico_path}")
    
    # 生成 macOS ICNS（使用 1024x1024 作为基础）
    print("\n生成 macOS ICNS...")
    mac_icon = draw_folder_icon(1024)
    icns_path = os.path.join(icons_dir, 'app_icon.icns')
    # PIL 不直接支持 ICNS，保存高分辨率 PNG 供后续转换
    mac_icon.save(icns_path.replace('.icns', '_1024.png'), 'PNG')
    print(f"[OK] macOS icon base: {icns_path.replace('.icns', '_1024.png')}")
    
    # 生成应用 logo（大分辨率用于宣传等）
    print("\n生成应用 Logo...")
    logo = draw_folder_icon(1024)
    logo_path = os.path.join(icons_dir, 'app_logo.png')
    logo.save(logo_path, 'PNG')
    print(f"[OK] Logo: {logo_path}")
    
    # 生成带阴影的版本（用于某些场景）
    print("\n生成带阴影版本...")
    shadow_img = draw_folder_icon(512)
    # 添加投影效果
    shadow_layer = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.rounded_rectangle(
        [80, 80, 432, 432],
        radius=80,
        fill=(0, 0, 0, 40)
    )
    shadow_img = Image.alpha_composite(shadow_layer, shadow_img)
    shadow_path = os.path.join(icons_dir, 'app_logo_shadow.png')
    shadow_img.save(shadow_path, 'PNG')
    print(f"[OK] Shadow logo: {shadow_path}")
    
    print("\n" + "=" * 60)
    print("图标生成完成！")
    print(f"总计: {len(SIZES)} 个 PNG + 1 个 ICO")
    print(f"目录: {icons_dir}")

if __name__ == '__main__':
    generate_all_icons()
