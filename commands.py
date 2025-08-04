import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import json
import user
import colorsys
import logging
import math
import urllib.request
from datetime import datetime
from io import BytesIO
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import mask_email, mask_account_id, bool_to_emoji, country_to_flag
from user import ExoUser
from cosmetic import FortniteCosmetic
from epic_auth import EpicUser, EpicEndpoints, EpicGenerator, LockerData

def escape_markdown(text):
    """
    Escapes special characters for markdown formatting
    @note: sometimes external connections shows error due to these, so we handle it that way
    """
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
        
    return text

class FortniteCache:
    def __init__(self):
        self.cache = {}
        self.cache_dir = "cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        self.load_cache_from_directory()
        
    def load_cache_from_directory(self):
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".png"):
                id = os.path.splitext(filename)[0]
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    image = Image.open(file_path).convert('RGBA')
                    self.cache[id] = image
                except Exception as e:
                    continue
                    
    def get_cosmetic_icon_from_cache(self, url, id):
        if not url:
            print(f"Error: No URL provided for ID: {id}")
            return None
        
        cache_path = os.path.join(self.cache_dir, f"{id}.png")
        if id in self.cache:
            return self.cache[id]

        if os.path.exists(cache_path):
            # getting the icon from filesystem
            try:
                image = Image.open(cache_path).convert('RGBA')
                self.cache[id] = image
                return image
            except Exception as e:
                print(f"Error loading {cache_path}: {e}")

        try:
            # downloading the icon from url
            with urllib.request.urlopen(url) as response:
                image_data = response.read()
                image = Image.open(BytesIO(image_data)).convert('RGBA')
                try:
                    image.save(cache_path)
                except Exception as e:
                    print(f"Error saving {cache_path}: {e}")
                
                self.cache[id] = image
                return image 
        except Exception as e:
            print(f"Error downloading image from {url}: {e}")
            return None

# global members
fortnite_cache = FortniteCache()

available_styles = [
    {"ID": 0, "name": "Exo", "image": "img/styles/exo.png"},
    {"ID": 1, "name": "Easy", "image": "img/styles/easy.png"},
    {"ID": 2, "name": "Raika", "image": "img/styles/raika.png"},
    {"ID": 3, "name": "kayy", "image": "img/styles/kayy.png"},
    {"ID": 4, "name": "Storm", "image": "img/styles/storm.png"}
]

avaliable_badges = [
    {"name": "Alpha Tester 1", "data": "alpha_tester_1_badge", "data2": "alpha_tester_1_badge_active", "image": "badges/icon/alpha1.png"},
    {"name": "Alpha Tester 2", "data": "alpha_tester_2_badge", "data2": "alpha_tester_2_badge_active", "image": "badges/icon/alpha2.png"},
    {"name": "Alpha Tester 3", "data": "alpha_tester_3_badge", "data2": "alpha_tester_3_badge_active", "image": "badges/icon/alpha3.png"},
    {"name": "Epic Games", "data": "epic_badge", "data2": "epic_badge_active", "image": "badges/icon/epic.png"}
]

locker_categories = ['AthenaCharacter', 'AthenaBackpack', 'AthenaPickaxe', 'AthenaDance', 'AthenaGlider', 'AthenaPopular', 'AthenaExclusive']
# global members



def draw_gradient_text(gradient_type, draw, position, text, font, fill=(255, 255, 255)):
    """
    Draw text with a rainbow gradient at a given position.
    
    :param gradient_type: The gradient we use to render the text as.
    :param draw: ImageDraw object to draw on.
    :param position: Tuple (x, y) of the position where the text starts.
    :param text: Text to draw.
    :param font: Font object to use for the text.
    :param fill: the color in RGB in base to draw
    """
    
    num_colors = len(text)
    if gradient_type == 0:
        # white text(no gradient)
        gradient_colors = [(255, 255, 255)] * num_colors
        
    elif gradient_type == 1:
        # rainbow gradient
        gradient_colors = [
            tuple(int(c * 255) for c in colorsys.hsv_to_rgb(i / num_colors, 1, 1))
            for i in range(num_colors)
        ]
        
    elif gradient_type == 2:
        # golden gradient
        gradient_colors = [
            tuple(int(c * 255) for c in colorsys.hsv_to_rgb(0.13, 0.5 + (i / num_colors) * 0.5, 0.8 + (i / num_colors) * 0.2))
            for i in range(num_colors)
        ]
        
    elif gradient_type == 3:
        # silver gradient
        gradient_colors = [
            tuple(int(c * 255) for c in colorsys.hsv_to_rgb(0, 0 + (i / num_colors) * 0.2, 0.6 + (i / num_colors) * 0.4))
            for i in range(num_colors)
        ]
    
    x, y = position
    for i, char in enumerate(text):
        color = gradient_colors[i]
        char_width = font.getbbox(char)[2]
        draw.text((x, y), char, font=font, fill=color)
        x += char_width


def render_exo_style(header:str, user_data: json, arr: list[str], nametosave:str) -> None:
    # calculating cosmetics per row
    cosmetic_per_row = 6
    total_cosmetics = len(arr)
    num_rows = math.ceil(total_cosmetics / cosmetic_per_row)
    if total_cosmetics > 30:
        num_rows = int(math.sqrt(total_cosmetics))
        cosmetic_per_row = math.ceil(total_cosmetics / num_rows)
        
        while cosmetic_per_row * num_rows < total_cosmetics:
            num_rows += 1
            cosmetic_per_row = math.ceil(total_cosmetics / num_rows)

    # setup for our image, thumbnails
    padding = 30
    thumbnail_width = 128
    thumbnail_height = 128
    image_width = int(cosmetic_per_row * thumbnail_width)
    image_height = int(thumbnail_height + 5 + thumbnail_width * num_rows + 180)
    font_path = 'styles/exo/font.ttf'
    font_size = 16
    font = ImageFont.truetype(font_path, font_size)
    image = Image.new('RGB', (image_width, image_height), (0, 0, 0))
    
    # custom background
    custom_background_path = f"users/backgrounds/{user_data['ID']}.png"
    if os.path.isfile(custom_background_path):
        custom_background = Image.open(custom_background_path).resize((image_width, image_height), Image.Resampling.BILINEAR)
        image.paste(custom_background, (0, 0))
        
    current_row = 0
    current_column = 0
    sortarray = ['mythic', 'legendary', 'dark', 'slurp', 'starwars', 'marvel', 'lava', 'frozen', 'gaminglegends', 'shadow', 'icon', 'dc', 'epic', 'rare', 'uncommon', 'common']
    arr.sort(key=lambda x: sortarray.index(x.rarity_value))

    # had some issues with exclusives rendering in wrong order, so i'm sorting them
    try:
        with open('exclusive.txt', 'r', encoding='utf-8') as f:
            exclusive_cosmetics = [i.strip() for i in f.readlines()]
        
        with open('most_wanted.txt', 'r', encoding='utf-8') as f:
            popular_cosmetics = [i.strip() for i in f.readlines()]
    except FileNotFoundError:
        print("Error: 'exclusive.txt' or 'most_wanted.txt' not found.")
        exclusive_cosmetics = []
        popular_cosmetics = []

    mythic_items = [item for item in arr if item.rarity_value == 'mythic']
    other_items = [item for item in arr if item.rarity_value != 'mythic']
    mythic_items.sort(
        key=lambda x: exclusive_cosmetics.index(x.cosmetic_id) 
        if x.cosmetic_id in exclusive_cosmetics else float('inf')
    )
        
    if header == "Popular":
        other_items.sort(
            key=lambda x: popular_cosmetics.index(x.cosmetic_id) 
            if x.cosmetic_id in popular_cosmetics else float('inf')
        )
        
    arr = mythic_items + other_items
    draw = ImageDraw.Draw(image)

    # top
    icon_logo = Image.open(f'cosmetic_icons/{header}.png')
    icon_logo.thumbnail((thumbnail_width, thumbnail_height)) 
    image.paste(icon_logo, (5, 0), mask=icon_logo)
    draw.text((thumbnail_width + 12, 14), '{}'.format(len(arr)), font=ImageFont.truetype(font_path, 70), fill=(0, 0, 0)) # shadow
    draw.text((thumbnail_width + 12, 82), '{}'.format(header), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw.text((thumbnail_width + 8, 10), '{}'.format(len(arr)), font=ImageFont.truetype(font_path, 70), fill=(255, 255, 255))
    draw.text((thumbnail_width + 8, 78), '{}'.format(header), font=ImageFont.truetype(font_path, 40), fill=(200, 200, 200))
        
    special_items = {
        "CID_029_Athena_Commando_F_Halloween": "cache/pink_ghoul.png",
        "CID_030_Athena_Commando_M_Halloween": "cache/purple_skull.png",
        "CID_116_Athena_Commando_M_CarbideBlack": "cache/omega_max.png",
        "CID_694_Athena_Commando_M_CatBurglar": "cache/gold_midas.png",
        "CID_693_Athena_Commando_M_BuffCat": "cache/gold_cat.png",
        "CID_691_Athena_Commando_F_TNTina": "cache/gold_tntina.png",
        "CID_690_Athena_Commando_F_Photographer": "cache/gold_skye.png",
        "CID_701_Athena_Commando_M_BananaAgent": "cache/gold_peely.png",
        "CID_315_Athena_Commando_M_TeriyakiFish": "cache/worldcup_fish.png",
        "CID_971_Athena_Commando_M_Jupiter_S0Z6M": "cache/black_masterchief.png",
        "CID_028_Athena_Commando_F": "cache/og_rene.png",
        "CID_017_Athena_Commando_M": "cache/og_aat.png"
    }
        
    for cosmetic in arr:
        special_icon = False
        is_banner = cosmetic.is_banner
        photo = None
        if cosmetic.rarity_value.lower() == "mythic" and cosmetic.cosmetic_id in special_items:
            special_icon = True
            icon_path = special_items[cosmetic.cosmetic_id]
            if os.path.exists(icon_path):
                try:
                    photo = Image.open(icon_path)
                except Exception as e:
                    special_icon = False
            else:
                special_icon = False
        else:
            photo = fortnite_cache.get_cosmetic_icon_from_cache(cosmetic.small_icon, cosmetic.cosmetic_id)
            
        if is_banner:
            scaled_width = int(photo.width * 1.5)
            scaled_height = int(photo.height * 1.5)
            photo = photo.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            x_offset = 32
            y_offset = 10
                
            new_img = Image.open(f'styles/exo/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA')
            new_img.paste(photo, (x_offset, y_offset), mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))
        else:
            new_img = Image.open(f'styles/exo/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA').resize(photo.size)    
            new_img.paste(photo, mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))

        # black box for cosmetic name
        box = Image.new('RGBA', (128, 28), (0, 0, 0, 100))
        photo.paste(box, (0, new_img.size[1] - 28), mask=box)
            
        if header != "Exclusives" and cosmetic.cosmetic_id in popular_cosmetics:
            star_image = Image.open('cosmetic_icons/WantedStar.png').resize((128, 128), Image.BILINEAR)
            photo.paste(star_image, (0, 0), star_image.convert("RGBA"))

        x = thumbnail_width * current_column
        y = thumbnail_width + thumbnail_height * current_row
        image.paste(photo, (x, y))

        name = cosmetic.name.upper()
        max_text_width = thumbnail_width - 10
        max_text_height = 20
            
        # fixed font size
        font_size = 16
        offset = 9
        while True:
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), name, font=font)
            name_width = bbox[2] - bbox[0]
            name_height = bbox[3] - bbox[1]

            if name_width > max_text_width or name_height > max_text_height:
                font_size -= 1
                offset += 0.5
            else:
                break

        # cosmetic name
        bbox = draw.textbbox((0, 0), name, font=font)
        name_width = bbox[2] - bbox[0]
        draw.text((x + (thumbnail_width - name_width) // 2, y + (thumbnail_height - padding + offset)), name, font=font, fill=(255, 255, 255))
            
        # make the cosmetics show ordered in rows(cosmetic_per_row is hardcoded)
        current_column += 1
        if current_column >= cosmetic_per_row:
            current_row += 1
            current_column = 0

    # footer
    current_date = datetime.now().strftime('%B %d, %Y')
    
    # custom logo
    custom_logo_path = f"users/logos/{user_data['ID']}.png"
    if os.path.isfile(custom_logo_path):
        custom_logo = Image.open(custom_logo_path).resize((150, 150), Image.Resampling.BILINEAR)
        image.paste(custom_logo, (10, image_height - 165), mask=custom_logo)
    else:
        # original logo if not found
        logo = Image.open('img/logo.png').resize((150, 150), Image.Resampling.BILINEAR)     
        image.paste(logo, (10, image_height - 165), mask=logo)
    
    draw.text((174, image_height - 40 * 3 - 24), '{}'.format(current_date), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw.text((170, image_height - 40 * 3 - 28), '{}'.format(current_date), font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))
    draw.text((174, image_height - 40 * 2 - 24), '@{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw_gradient_text(user_data['gradient_type'], draw, (170, image_height - 40 * 2 - 28), '@{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 40))
    # badges
    font_size = 40
    font = ImageFont.truetype(font_path, font_size)
    username_width = font.getbbox(f"@{user_data['username']}")[2]
    offset_badge = 170 + username_width + 8

    if user_data['epic_badge_active'] == True and user_data['epic_badge'] == True:
        # epic games badge(special people only)
        alpha_badge = Image.open('badges/epic.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45

    if user_data['alpha_tester_3_badge_active'] == True and user_data['alpha_tester_3_badge'] == True:
        # alpha tester 3 badge
        alpha_badge = Image.open('badges/alpha3.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
        
    if user_data['alpha_tester_2_badge_active'] == True and user_data['alpha_tester_2_badge'] == True:
        # alpha tester 2 badge
        alpha_badge = Image.open('badges/alpha2.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
        
    if user_data['alpha_tester_1_badge_active'] == True and user_data['alpha_tester_1_badge'] == True:
        # alpha tester 1 badge
        alpha_badge = Image.open('badges/alpha1.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45

    draw.text((174, image_height - 61), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow       
    draw.text((170, image_height - 65), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))
    image.save(nametosave)
    
def render_easy_style(header:str, user_data: json, arr: list[str], nametosave:str) -> None:
    # calculating cosmetics per row
    cosmetic_per_row = 6
    total_cosmetics = len(arr)
    num_rows = math.ceil(total_cosmetics / cosmetic_per_row)
    if total_cosmetics > 30:
        num_rows = int(math.sqrt(total_cosmetics))
        cosmetic_per_row = math.ceil(total_cosmetics / num_rows)
        
        while cosmetic_per_row * num_rows < total_cosmetics:
            num_rows += 1
            cosmetic_per_row = math.ceil(total_cosmetics / num_rows)

    # setup for our image, thumbnails
    padding_height = 10
    padding_width = 50
    thumbnail_width = 128
    thumbnail_height = 128
    image_width = int(cosmetic_per_row * thumbnail_width + padding_width * 2)
    image_height = int(padding_width + (padding_height + thumbnail_width) * num_rows + padding_width * 2)
    font_path = 'styles/easy/font.ttf'
    font_size = 16
    font = ImageFont.truetype(font_path, font_size)
    image = Image.new('RGB', (image_width, image_height), (58, 58, 58))

    current_row = 0
    current_column = 0
    sortarray = ['mythic', 'legendary', 'dark', 'slurp', 'starwars', 'marvel', 'lava', 'frozen', 'gaminglegends', 'shadow', 'icon', 'dc', 'epic', 'rare', 'uncommon', 'common']
    arr.sort(key=lambda x: sortarray.index(x.rarity_value))

    # had some issues with exclusives rendering in wrong order, so i'm sorting them
    try:
        with open('exclusive.txt', 'r', encoding='utf-8') as f:
            exclusive_cosmetics = [i.strip() for i in f.readlines()]
        
        with open('most_wanted.txt', 'r', encoding='utf-8') as f:
            popular_cosmetics = [i.strip() for i in f.readlines()]
    except FileNotFoundError:
        print("Error: 'exclusive.txt' or 'most_wanted.txt' not found.")
        exclusive_cosmetics = []
        popular_cosmetics = []

    mythic_items = [item for item in arr if item.rarity_value == 'mythic']
    other_items = [item for item in arr if item.rarity_value != 'mythic']
    mythic_items.sort(
        key=lambda x: exclusive_cosmetics.index(x.cosmetic_id) 
        if x.cosmetic_id in exclusive_cosmetics else float('inf')
    )
        
    if header == "Popular":
        other_items.sort(
            key=lambda x: popular_cosmetics.index(x.cosmetic_id) 
            if x.cosmetic_id in popular_cosmetics else float('inf')
        )
        
    arr = mythic_items + other_items
    draw = ImageDraw.Draw(image)

    # cosmetics count
    cosmetics = '{} count: {}'.format(header, len(arr))
    max_text_width = image_width - 20
    max_text_height = 40
    min_font_size = 10
            
    font_size = 40
    while True:
        bbox = draw.textbbox((0, 0), cosmetics, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if text_width > max_text_width or font_size > image_height - 2:
            font_size -= 1
            if font_size < min_font_size:
                font_size = min_font_size
                break
            font = ImageFont.truetype(font_path, font_size)
        else:
            break


    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), cosmetics, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (image_width - text_width) // 2
    draw.text((text_x, 9), cosmetics, font=font, fill=(255, 255, 255))
        
    special_items = {
        "CID_029_Athena_Commando_F_Halloween": "cache/pink_ghoul.png",
        "CID_030_Athena_Commando_M_Halloween": "cache/purple_skull_old.png",
        "CID_116_Athena_Commando_M_CarbideBlack": "cache/omega_max.png",
        "CID_694_Athena_Commando_M_CatBurglar": "cache/gold_midas.png",
        "CID_693_Athena_Commando_M_BuffCat": "cache/gold_cat.png",
        "CID_691_Athena_Commando_F_TNTina": "cache/gold_tntina.png",
        "CID_690_Athena_Commando_F_Photographer": "cache/gold_skye.png",
        "CID_701_Athena_Commando_M_BananaAgent": "cache/gold_peely.png",
        "CID_315_Athena_Commando_M_TeriyakiFish": "cache/worldcup_fish.png",
        "CID_971_Athena_Commando_M_Jupiter_S0Z6M": "cache/black_masterchief.png",
        "CID_028_Athena_Commando_F": "cache/og_rene.png",
        "CID_017_Athena_Commando_M": "cache/og_aat.png"
    }
        
    for cosmetic in arr:
        special_icon = False
        is_banner = cosmetic.is_banner
        photo = None
        if cosmetic.rarity_value.lower() == "mythic" and cosmetic.cosmetic_id in special_items:
            special_icon = True
            icon_path = special_items[cosmetic.cosmetic_id]
            if os.path.exists(icon_path):
                try:
                    photo = Image.open(icon_path)
                except Exception as e:
                    special_icon = False
            else:
                special_icon = False
        else:
            photo = fortnite_cache.get_cosmetic_icon_from_cache(cosmetic.small_icon, cosmetic.cosmetic_id)
            
        if is_banner:
            scaled_width = int(photo.width * 1.5)
            scaled_height = int(photo.height * 1.5)
            photo = photo.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            x_offset = 32
            y_offset = 10
                
            new_img = Image.open(f'styles/easy/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA')
            new_img.paste(photo, (x_offset, y_offset), mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))
        else:
            new_img = Image.open(f'styles/easy/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA').resize(photo.size)    
            new_img.paste(photo, mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))

        # black box for cosmetic name
        box = Image.new('RGBA', (128, 20), (0, 0, 0, 75))
        photo.paste(box, (0, new_img.size[1] - 40), mask=box)
        
        border = Image.open(f'styles/easy/border/{cosmetic.rarity_value.lower()}.png').convert('RGBA').resize(photo.size)    
        photo.paste(border, mask=border)
        
        x = padding_width + thumbnail_width * current_column
        y = padding_width + (thumbnail_height + padding_height) * current_row
        image.paste(photo, (x, y))

        name = cosmetic.name
        max_text_width = thumbnail_width - 10
        max_text_height = 20
        offset_y = 38
        font_size = 18
        while True:
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), name, font=font)
            name_width = bbox[2] - bbox[0]
            name_height = bbox[3] - bbox[1]

            if name_width > max_text_width or name_height > max_text_height:
                font_size -= 1
                offset_y -= 0.5
            else:
                break

        # cosmetic name
        bbox = draw.textbbox((0, 0), name, font=font)
        name_width = bbox[2] - bbox[0]
        draw.text((x + (thumbnail_width - name_width) // 2, y + (thumbnail_height - offset_y)), name, font=font, fill=(255, 255, 255))
            
        # make the cosmetics show ordered in rows(cosmetic_per_row is hardcoded)
        current_column += 1
        if current_column >= cosmetic_per_row:
            current_row += 1
            current_column = 0

    # footer
    current_date = datetime.now().strftime('%d/%m/%Y')
    footer = 'Submitted by @{} on {}'.format(user_data['username'], current_date)
    max_text_width = image_width - 20
    max_text_height = 40
    min_font_size = 15
            
    font_size = 40
    while True:
        bbox = draw.textbbox((0, 0), footer, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if text_width > max_text_width or font_size > image_height - 2:
            font_size -= 1
            if font_size < min_font_size:
                font_size = min_font_size
                break
            
            font = ImageFont.truetype(font_path, font_size)
        else:
            break
        
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), footer, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (image_width - text_width) // 2
    text_y = image_height - font_size - 52
    draw.text((text_x, text_y), footer, font=font, fill=(255, 255, 255))
    
    # bot advertisment
    footer2 = 't.me/ExoCheckerBot'
    max_text_width = image_width - 20
    max_text_height = 40
    min_font_size = 15
            
    font_size = 40
    while True:
        bbox = draw.textbbox((0, 0), footer2, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if text_width > max_text_width or font_size > image_height - 2:
            font_size -= 1
            if font_size < min_font_size:
                font_size = min_font_size
                break
            
            font = ImageFont.truetype(font_path, font_size)
        else:
            break


    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), footer2, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (image_width - text_width) // 2
    text_y = image_height - font_size - 8
    draw.text((text_x, text_y), footer2, font=font, fill=(255, 255, 255))
     
    image.save(nametosave)

def render_raika_style(header:str, user_data: json, arr: list[str], nametosave:str) -> None:
    # calculating cosmetics per row
    cosmetic_per_row = 6
    total_cosmetics = len(arr)
    num_rows = math.ceil(total_cosmetics / cosmetic_per_row)
    if total_cosmetics > 30:
        num_rows = int(math.sqrt(total_cosmetics))
        cosmetic_per_row = math.ceil(total_cosmetics / num_rows)
        
        while cosmetic_per_row * num_rows < total_cosmetics:
            num_rows += 1
            cosmetic_per_row = math.ceil(total_cosmetics / num_rows)

    # setup for our image, thumbnails
    padding = 30
    thumbnail_width = 128
    thumbnail_height = 128
    image_width = int(cosmetic_per_row * thumbnail_width)
    image_height = int(thumbnail_height + 5 + thumbnail_width * num_rows + 180)
    font_path = 'styles/raika/font.ttf'
    font_size = 16
    font = ImageFont.truetype(font_path, font_size)
    image = Image.new('RGB', (image_width, image_height), (0, 0, 0))
    
    # custom background
    custom_background_path = f"users/backgrounds/{user_data['ID']}.png"
    if os.path.isfile(custom_background_path):
        custom_background = Image.open(custom_background_path).resize((image_width, image_height), Image.Resampling.BILINEAR)
        image.paste(custom_background, (0, 0))
        
    current_row = 0
    current_column = 0
    sortarray = ['mythic', 'legendary', 'dark', 'slurp', 'starwars', 'marvel', 'lava', 'frozen', 'gaminglegends', 'shadow', 'icon', 'dc', 'epic', 'rare', 'uncommon', 'common']
    arr.sort(key=lambda x: sortarray.index(x.rarity_value))

    # had some issues with exclusives rendering in wrong order, so i'm sorting them
    try:
        with open('exclusive.txt', 'r', encoding='utf-8') as f:
            exclusive_cosmetics = [i.strip() for i in f.readlines()]
        
        with open('most_wanted.txt', 'r', encoding='utf-8') as f:
            popular_cosmetics = [i.strip() for i in f.readlines()]
    except FileNotFoundError:
        print("Error: 'exclusive.txt' or 'most_wanted.txt' not found.")
        exclusive_cosmetics = []
        popular_cosmetics = []

    mythic_items = [item for item in arr if item.rarity_value == 'mythic']
    other_items = [item for item in arr if item.rarity_value != 'mythic']
    mythic_items.sort(
        key=lambda x: exclusive_cosmetics.index(x.cosmetic_id) 
        if x.cosmetic_id in exclusive_cosmetics else float('inf')
    )
        
    if header == "Popular":
        other_items.sort(
            key=lambda x: popular_cosmetics.index(x.cosmetic_id) 
            if x.cosmetic_id in popular_cosmetics else float('inf')
        )
        
    arr = mythic_items + other_items
    draw = ImageDraw.Draw(image)

    # top
    icon_logo = Image.open(f'cosmetic_icons/{header}.png')
    icon_logo.thumbnail((thumbnail_width, thumbnail_height)) 
    image.paste(icon_logo, (5, 0), mask=icon_logo)
    draw.text((thumbnail_width + 12, 14), '{}'.format(len(arr)), font=ImageFont.truetype(font_path, 70), fill=(0, 0, 0)) # shadow
    draw.text((thumbnail_width + 12, 82), '{}'.format(header), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw.text((thumbnail_width + 8, 10), '{}'.format(len(arr)), font=ImageFont.truetype(font_path, 70), fill=(255, 255, 255))
    draw.text((thumbnail_width + 8, 78), '{}'.format(header), font=ImageFont.truetype(font_path, 40), fill=(200, 200, 200))
        
    special_items = {
        "CID_029_Athena_Commando_F_Halloween": "cache/pink_ghoul.png",
        "CID_030_Athena_Commando_M_Halloween": "cache/purple_skull_old.png",
        "CID_116_Athena_Commando_M_CarbideBlack": "cache/omega_max.png",
        "CID_694_Athena_Commando_M_CatBurglar": "cache/gold_midas.png",
        "CID_693_Athena_Commando_M_BuffCat": "cache/gold_cat.png",
        "CID_691_Athena_Commando_F_TNTina": "cache/gold_tntina.png",
        "CID_690_Athena_Commando_F_Photographer": "cache/gold_skye.png",
        "CID_701_Athena_Commando_M_BananaAgent": "cache/gold_peely.png",
        "CID_315_Athena_Commando_M_TeriyakiFish": "cache/worldcup_fish.png",
        "CID_971_Athena_Commando_M_Jupiter_S0Z6M": "cache/black_masterchief.png",
        "CID_028_Athena_Commando_F": "cache/og_rene.png",
        "CID_017_Athena_Commando_M": "cache/og_aat.png"
    }
        
    for cosmetic in arr:
        special_icon = False
        is_banner = cosmetic.is_banner
        photo = None
        if cosmetic.rarity_value.lower() == "mythic" and cosmetic.cosmetic_id in special_items:
            special_icon = True
            icon_path = special_items[cosmetic.cosmetic_id]
            if os.path.exists(icon_path):
                try:
                    photo = Image.open(icon_path)
                except Exception as e:
                    special_icon = False
            else:
                special_icon = False
        else:
            photo = fortnite_cache.get_cosmetic_icon_from_cache(cosmetic.small_icon, cosmetic.cosmetic_id)
            
        if is_banner:
            scaled_width = int(photo.width * 1.5)
            scaled_height = int(photo.height * 1.5)
            photo = photo.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            x_offset = 32
            y_offset = 10
                
            new_img = Image.open(f'styles/raika/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA')
            new_img.paste(photo, (x_offset, y_offset), mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))
        else:
            new_img = Image.open(f'styles/raika/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA').resize(photo.size)    
            new_img.paste(photo, mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))

        # black box for cosmetic name
        box = Image.new('RGBA', (128, 28), (0, 0, 0, 100))
        photo.paste(box, (0, new_img.size[1] - 28), mask=box)
            
        if header != "Exclusives" and cosmetic.cosmetic_id in popular_cosmetics:
            star_image = Image.open('cosmetic_icons/WantedStar.png').resize((128, 128), Image.BILINEAR)
            photo.paste(star_image, (0, 0), star_image.convert("RGBA"))

        x = thumbnail_width * current_column
        y = thumbnail_width + thumbnail_height * current_row
        image.paste(photo, (x, y))

        name = cosmetic.name.upper()
        max_text_width = thumbnail_width - 10
        max_text_height = 20
            
        # fixed font size
        font_size = 16
        offset = 6
        while True:
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), name, font=font)
            name_width = bbox[2] - bbox[0]
            name_height = bbox[3] - bbox[1]

            if name_width > max_text_width or name_height > max_text_height:
                font_size -= 1
                offset += 0.5
            else:
                break

        # cosmetic name
        bbox = draw.textbbox((0, 0), name, font=font)
        name_width = bbox[2] - bbox[0]
        draw.text((x + (thumbnail_width - name_width) // 2, y + (thumbnail_height - padding + offset)), name, font=font, fill=(255, 255, 255))
            
        # make the cosmetics show ordered in rows(cosmetic_per_row is hardcoded)
        current_column += 1
        if current_column >= cosmetic_per_row:
            current_row += 1
            current_column = 0

    # footer
    current_date = datetime.now().strftime('%B %d, %Y')
    
    # custom logo
    custom_logo_path = f"users/logos/{user_data['ID']}.png"
    if os.path.isfile(custom_logo_path):
        custom_logo = Image.open(custom_logo_path).resize((150, 150), Image.Resampling.BILINEAR)
        image.paste(custom_logo, (10, image_height - 165), mask=custom_logo)
    else:
        # original logo if not found
        logo = Image.open('img/logo.png').resize((150, 150), Image.Resampling.BILINEAR)     
        image.paste(logo, (10, image_height - 165), mask=logo)

    draw.text((174, image_height - 40 * 3 - 24), '{}'.format(current_date), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw.text((170, image_height - 40 * 3 - 28), '{}'.format(current_date), font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))  
    draw.text((174, image_height - 40 * 2 - 24), '@{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow 
    draw_gradient_text(user_data['gradient_type'], draw, (170, image_height - 40 * 2 - 28), '@{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 40))
        
    # badges
    font_size = 40
    font = ImageFont.truetype(font_path, font_size)
    username_width = font.getbbox(f"@{user_data['username']}")[2]
    offset_badge = 170 + username_width + 8

    if user_data['epic_badge_active'] == True and user_data['epic_badge'] == True:
        # epic games badge(special people only)
        alpha_badge = Image.open('badges/epic.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45

    if user_data['alpha_tester_3_badge_active'] == True and user_data['alpha_tester_3_badge'] == True:
        # alpha tester 3 badge
        alpha_badge = Image.open('badges/alpha3.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
        
    if user_data['alpha_tester_2_badge_active'] == True and user_data['alpha_tester_2_badge'] == True:
        # alpha tester 2 badge
        alpha_badge = Image.open('badges/alpha2.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
        
    if user_data['alpha_tester_1_badge_active'] == True and user_data['alpha_tester_1_badge'] == True:
        # alpha tester 1 badge
        alpha_badge = Image.open('badges/alpha1.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
   
    draw.text((174, image_height - 61), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow     
    draw.text((170, image_height - 65), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))
    image.save(nametosave)
    
def render_kayy_style(header:str, user_data: json, arr: list[str], nametosave:str) -> None:
    # calculating cosmetics per row
    cosmetic_per_row = 6
    total_cosmetics = len(arr)
    num_rows = math.ceil(total_cosmetics / cosmetic_per_row)
    if total_cosmetics > 30:
        num_rows = int(math.sqrt(total_cosmetics))
        cosmetic_per_row = math.ceil(total_cosmetics / num_rows)
        
        while cosmetic_per_row * num_rows < total_cosmetics:
            num_rows += 1
            cosmetic_per_row = math.ceil(total_cosmetics / num_rows)

    # setup for our image, thumbnails
    padding = 30
    thumbnail_width = 128
    thumbnail_height = 128
    image_width = int(cosmetic_per_row * thumbnail_width)
    image_height = int(thumbnail_width * num_rows + 180)
    font_path = 'styles/kayy/font.ttf'
    font_size = 16
    font = ImageFont.truetype(font_path, font_size)
    image = Image.new('RGB', (image_width, image_height), (0, 0, 0))
    
    # custom background
    custom_background_path = f"users/backgrounds/{user_data['ID']}.png"
    if os.path.isfile(custom_background_path):
        custom_background = Image.open(custom_background_path).resize((image_width, image_height), Image.Resampling.BILINEAR)
        image.paste(custom_background, (0, 0))
        
    current_row = 0
    current_column = 0
    sortarray = ['mythic', 'legendary', 'dark', 'slurp', 'starwars', 'marvel', 'lava', 'frozen', 'gaminglegends', 'shadow', 'icon', 'dc', 'epic', 'rare', 'uncommon', 'common']
    arr.sort(key=lambda x: sortarray.index(x.rarity_value))

    # had some issues with exclusives rendering in wrong order, so i'm sorting them
    try:
        with open('exclusive.txt', 'r', encoding='utf-8') as f:
            exclusive_cosmetics = [i.strip() for i in f.readlines()]
        
        with open('most_wanted.txt', 'r', encoding='utf-8') as f:
            popular_cosmetics = [i.strip() for i in f.readlines()]
    except FileNotFoundError:
        print("Error: 'exclusive.txt' or 'most_wanted.txt' not found.")
        exclusive_cosmetics = []
        popular_cosmetics = []

    mythic_items = [item for item in arr if item.rarity_value == 'mythic']
    other_items = [item for item in arr if item.rarity_value != 'mythic']
    mythic_items.sort(
        key=lambda x: exclusive_cosmetics.index(x.cosmetic_id) 
        if x.cosmetic_id in exclusive_cosmetics else float('inf')
    )
        
    if header == "Popular":
        other_items.sort(
            key=lambda x: popular_cosmetics.index(x.cosmetic_id) 
            if x.cosmetic_id in popular_cosmetics else float('inf')
        )
        
    arr = mythic_items + other_items
    draw = ImageDraw.Draw(image)

    special_items = {
        "CID_029_Athena_Commando_F_Halloween": "cache/pink_ghoul.png",
        "CID_030_Athena_Commando_M_Halloween": "cache/purple_skull_old.png",
        "CID_116_Athena_Commando_M_CarbideBlack": "cache/omega_max.png",
        "CID_694_Athena_Commando_M_CatBurglar": "cache/gold_midas.png",
        "CID_693_Athena_Commando_M_BuffCat": "cache/gold_cat.png",
        "CID_691_Athena_Commando_F_TNTina": "cache/gold_tntina.png",
        "CID_690_Athena_Commando_F_Photographer": "cache/gold_skye.png",
        "CID_701_Athena_Commando_M_BananaAgent": "cache/gold_peely.png",
        "CID_315_Athena_Commando_M_TeriyakiFish": "cache/worldcup_fish.png",
        "CID_971_Athena_Commando_M_Jupiter_S0Z6M": "cache/black_masterchief.png",
        "CID_028_Athena_Commando_F": "cache/og_rene.png",
        "CID_017_Athena_Commando_M": "cache/og_aat.png"
    }
        
    for cosmetic in arr:
        special_icon = False
        is_banner = cosmetic.is_banner
        photo = None
        if cosmetic.rarity_value.lower() == "mythic" and cosmetic.cosmetic_id in special_items:
            special_icon = True
            icon_path = special_items[cosmetic.cosmetic_id]
            if os.path.exists(icon_path):
                try:
                    photo = Image.open(icon_path)
                except Exception as e:
                    special_icon = False
            else:
                special_icon = False
        else:
            photo = fortnite_cache.get_cosmetic_icon_from_cache(cosmetic.small_icon, cosmetic.cosmetic_id)
            
        if is_banner:
            scaled_width = int(photo.width * 1.5)
            scaled_height = int(photo.height * 1.5)
            photo = photo.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            x_offset = 32
            y_offset = 10
                
            new_img = Image.open(f'styles/kayy/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA')
            new_img.paste(photo, (x_offset, y_offset), mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))
        else:
            new_img = Image.open(f'styles/kayy/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA').resize(photo.size)    
            new_img.paste(photo, mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))

        # black box for cosmetic name
        box = Image.new('RGBA', (128, 28), (0, 0, 0, 100))
        photo.paste(box, (0, new_img.size[1] - 28), mask=box)
            
        if header != "Exclusives" and cosmetic.cosmetic_id in popular_cosmetics:
            star_image = Image.open('cosmetic_icons/WantedStar.png').resize((128, 128), Image.BILINEAR)
            photo.paste(star_image, (0, 0), star_image.convert("RGBA"))

        x = thumbnail_width * current_column
        y = thumbnail_height * current_row
        image.paste(photo, (x, y))

        name = cosmetic.name.upper()
        max_text_width = thumbnail_width - 10
        max_text_height = 20
            
        # fixed font size
        font_size = 16
        offset = 9
        while True:
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), name, font=font)
            name_width = bbox[2] - bbox[0]
            name_height = bbox[3] - bbox[1]

            if name_width > max_text_width or name_height > max_text_height:
                font_size -= 1
                offset += 0.5
            else:
                break

        # cosmetic name
        bbox = draw.textbbox((0, 0), name, font=font)
        name_width = bbox[2] - bbox[0]
        draw.text((x + (thumbnail_width - name_width) // 2, y + (thumbnail_height - padding + offset)), name, font=font, fill=(255, 255, 255))
            
        # make the cosmetics show ordered in rows(cosmetic_per_row is hardcoded)
        current_column += 1
        if current_column >= cosmetic_per_row:
            current_row += 1
            current_column = 0

    # footer
    current_date = datetime.now().strftime('%d/%m/%Y')
    
    # custom logo
    custom_logo_path = f"users/logos/{user_data['ID']}.png"
    if os.path.isfile(custom_logo_path):
        custom_logo = Image.open(custom_logo_path).resize((150, 150), Image.Resampling.BILINEAR)
        image.paste(custom_logo, (10, image_height - 165), mask=custom_logo)
    else:
        # original logo if not found
        logo = Image.open('img/logo.png').resize((150, 150), Image.Resampling.BILINEAR)     
        image.paste(logo, (10, image_height - 165), mask=logo)

    draw.text((174, image_height - 40 * 3 - 24), 'Objects Total: {}'.format(len(arr)), font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255)) # shadow
    draw.text((170, image_height - 40 * 3 - 28), 'Objects Total: {}'.format(len(arr)), font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))
    draw.text((174, image_height - 40 * 2 - 24), '@{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255)) # shadow
    draw_gradient_text(user_data['gradient_type'], draw, (170, image_height - 40 * 2 - 28), '@{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 40))
        
    # badges
    font_size = 40
    font = ImageFont.truetype(font_path, font_size)
    username_width = font.getbbox(f"@{user_data['username']}")[2]
    offset_badge = 170 + username_width + 8

    if user_data['epic_badge_active'] == True and user_data['epic_badge'] == True:
        # epic games badge(special people only)
        alpha_badge = Image.open('badges/epic.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45

    if user_data['alpha_tester_3_badge_active'] == True and user_data['alpha_tester_3_badge'] == True:
        # alpha tester 3 badge
        alpha_badge = Image.open('badges/alpha3.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
        
    if user_data['alpha_tester_2_badge_active'] == True and user_data['alpha_tester_2_badge'] == True:
        # alpha tester 2 badge
        alpha_badge = Image.open('badges/alpha2.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
        
    if user_data['alpha_tester_1_badge_active'] == True and user_data['alpha_tester_1_badge'] == True:
        # alpha tester 1 badge
        alpha_badge = Image.open('badges/alpha1.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
     
    draw.text((offset_badge + 10, image_height - 40 * 2 - 26), '| {}'.format(current_date), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow   
    draw.text((offset_badge + 8, image_height - 40 * 2 - 28), '| {}'.format(current_date), font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))
    draw.text((174, image_height - 61), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw.text((170, image_height - 65), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))
    image.save(nametosave)   
    
def render_storm_style(header:str, user_data: json, arr: list[str], nametosave:str) -> None:
    # calculating cosmetics per row
    cosmetic_per_row = 6
    total_cosmetics = len(arr)
    num_rows = math.ceil(total_cosmetics / cosmetic_per_row)
    if total_cosmetics > 30:
        num_rows = int(math.sqrt(total_cosmetics))
        cosmetic_per_row = math.ceil(total_cosmetics / num_rows)
        
        while cosmetic_per_row * num_rows < total_cosmetics:
            num_rows += 1
            cosmetic_per_row = math.ceil(total_cosmetics / num_rows)

    # setup for our image, thumbnails
    padding = 30
    thumbnail_width = 128
    thumbnail_height = 128
    image_width = int(cosmetic_per_row * thumbnail_width)
    image_height = int(thumbnail_width * num_rows + 180)
    font_path = 'styles/storm/font.ttf'
    font_size = 16
    font = ImageFont.truetype(font_path, font_size)
    image = Image.new('RGB', (image_width, image_height), (0, 0, 0))
    
    # custom background
    custom_background_path = f"users/backgrounds/{user_data['ID']}.png"
    if os.path.isfile(custom_background_path):
        custom_background = Image.open(custom_background_path).resize((image_width, image_height), Image.Resampling.BILINEAR)
        image.paste(custom_background, (0, 0))
        
    current_row = 0
    current_column = 0
    sortarray = ['mythic', 'legendary', 'dark', 'slurp', 'starwars', 'marvel', 'lava', 'frozen', 'gaminglegends', 'shadow', 'icon', 'dc', 'epic', 'rare', 'uncommon', 'common']
    arr.sort(key=lambda x: sortarray.index(x.rarity_value))

    # had some issues with exclusives rendering in wrong order, so i'm sorting them
    try:
        with open('exclusive.txt', 'r', encoding='utf-8') as f:
            exclusive_cosmetics = [i.strip() for i in f.readlines()]
        
        with open('most_wanted.txt', 'r', encoding='utf-8') as f:
            popular_cosmetics = [i.strip() for i in f.readlines()]
    except FileNotFoundError:
        print("Error: 'exclusive.txt' or 'most_wanted.txt' not found.")
        exclusive_cosmetics = []
        popular_cosmetics = []

    mythic_items = [item for item in arr if item.rarity_value == 'mythic']
    other_items = [item for item in arr if item.rarity_value != 'mythic']
    mythic_items.sort(
        key=lambda x: exclusive_cosmetics.index(x.cosmetic_id) 
        if x.cosmetic_id in exclusive_cosmetics else float('inf')
    )
        
    if header == "Popular":
        other_items.sort(
            key=lambda x: popular_cosmetics.index(x.cosmetic_id) 
            if x.cosmetic_id in popular_cosmetics else float('inf')
        )
        
    arr = mythic_items + other_items
    draw = ImageDraw.Draw(image)

    special_items = {
        "CID_029_Athena_Commando_F_Halloween": "cache/pink_ghoul.png",
        "CID_030_Athena_Commando_M_Halloween": "cache/purple_skull_old.png",
        "CID_116_Athena_Commando_M_CarbideBlack": "cache/omega_max.png",
        "CID_694_Athena_Commando_M_CatBurglar": "cache/gold_midas.png",
        "CID_693_Athena_Commando_M_BuffCat": "cache/gold_cat.png",
        "CID_691_Athena_Commando_F_TNTina": "cache/gold_tntina.png",
        "CID_690_Athena_Commando_F_Photographer": "cache/gold_skye.png",
        "CID_701_Athena_Commando_M_BananaAgent": "cache/gold_peely.png",
        "CID_315_Athena_Commando_M_TeriyakiFish": "cache/worldcup_fish.png",
        "CID_971_Athena_Commando_M_Jupiter_S0Z6M": "cache/black_masterchief.png",
        "CID_028_Athena_Commando_F": "cache/og_rene.png",
        "CID_017_Athena_Commando_M": "cache/og_aat.png"
    }
        
    for cosmetic in arr:
        special_icon = False
        is_banner = cosmetic.is_banner
        photo = None
        if cosmetic.rarity_value.lower() == "mythic" and cosmetic.cosmetic_id in special_items:
            special_icon = True
            icon_path = special_items[cosmetic.cosmetic_id]
            if os.path.exists(icon_path):
                try:
                    photo = Image.open(icon_path)
                except Exception as e:
                    special_icon = False
            else:
                special_icon = False
        else:
            photo = fortnite_cache.get_cosmetic_icon_from_cache(cosmetic.small_icon, cosmetic.cosmetic_id)
            
        if is_banner:
            scaled_width = int(photo.width * 1.5)
            scaled_height = int(photo.height * 1.5)
            photo = photo.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            x_offset = 32
            y_offset = 10
                
            new_img = Image.open(f'styles/storm/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA')
            new_img.paste(photo, (x_offset, y_offset), mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))
        else:
            new_img = Image.open(f'styles/storm/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA').resize(photo.size)    
            new_img.paste(photo, mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))

        # black box for cosmetic name
        box = Image.new('RGBA', (128, 28), (0, 0, 0, 100))
        photo.paste(box, (0, new_img.size[1] - 28), mask=box)
            
        if header != "Exclusives" and cosmetic.cosmetic_id in popular_cosmetics:
            star_image = Image.open('cosmetic_icons/WantedStar.png').resize((128, 128), Image.BILINEAR)
            photo.paste(star_image, (0, 0), star_image.convert("RGBA"))

        x = thumbnail_width * current_column
        y = thumbnail_height * current_row
        image.paste(photo, (x, y))

        name = cosmetic.name.upper()
        max_text_width = thumbnail_width - 10
        max_text_height = 20
            
        # fixed font size
        font_size = 16
        offset = 9
        while True:
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), name, font=font)
            name_width = bbox[2] - bbox[0]
            name_height = bbox[3] - bbox[1]

            if name_width > max_text_width or name_height > max_text_height:
                font_size -= 1
                offset += 0.5
            else:
                break

        # cosmetic name
        bbox = draw.textbbox((0, 0), name, font=font)
        name_width = bbox[2] - bbox[0]
        draw.text((x + (thumbnail_width - name_width) // 2, y + (thumbnail_height - padding + offset)), name, font=font, fill=(255, 255, 255))
            
        # make the cosmetics show ordered in rows(cosmetic_per_row is hardcoded)
        current_column += 1
        if current_column >= cosmetic_per_row:
            current_row += 1
            current_column = 0

    # footer
    current_date = datetime.now().strftime('%d %B %Y')
    
    # custom logo
    custom_logo_path = f"users/logos/{user_data['ID']}.png"
    if os.path.isfile(custom_logo_path):
        custom_logo = Image.open(custom_logo_path).resize((150, 150), Image.Resampling.BILINEAR)
        image.paste(custom_logo, (10, image_height - 165), mask=custom_logo)
    else:
        # original logo if not found
        logo = Image.open('img/logo.png').resize((150, 150), Image.Resampling.BILINEAR)     
        image.paste(logo, (10, image_height - 165), mask=logo)

    draw.text((174, image_height - 40 * 3 - 24), '{}'.format(current_date), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw.text((170, image_height - 40 * 3 - 28), '{}'.format(current_date), font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))
    draw.text((174, image_height - 40 * 2 - 24), 'Submitted by ', font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw_gradient_text(0, draw, (170, image_height - 40 * 2 - 28), 'Submitted by ', font=ImageFont.truetype(font_path, 40))
        
    # badges
    font_size = 40
    font = ImageFont.truetype(font_path, font_size)
    submit_width = font.getbbox(f"Submitted by")[2]
    offset_submit = 170 + submit_width + 8
    username_width = font.getbbox(f"Submitted by @{user_data['username']}")[2]
    offset_badge = 170 + username_width + 8

    if user_data['epic_badge_active'] == True and user_data['epic_badge'] == True:
        # epic games badge(special people only)
        alpha_badge = Image.open('badges/epic.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45

    if user_data['alpha_tester_3_badge_active'] == True and user_data['alpha_tester_3_badge'] == True:
        # alpha tester 3 badge
        alpha_badge = Image.open('badges/alpha3.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
        
    if user_data['alpha_tester_2_badge_active'] == True and user_data['alpha_tester_2_badge'] == True:
        # alpha tester 2 badge
        alpha_badge = Image.open('badges/alpha2.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
        
    if user_data['alpha_tester_1_badge_active'] == True and user_data['alpha_tester_1_badge'] == True:
        # alpha tester 1 badge
        alpha_badge = Image.open('badges/alpha1.png').resize((40, 40), Image.BILINEAR)
        image.paste(alpha_badge, (offset_badge, image_height - 40 * 2 - 28), alpha_badge.convert("RGBA"))
        offset_badge += 45
      
    draw.text((offset_submit + 2, image_height - 40 * 2 - 26), '@{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow  
    draw_gradient_text(user_data['gradient_type'], draw, (offset_submit, image_height - 40 * 2 - 28), '@{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 40))
    draw.text((174, image_height - 61), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw.text((170, image_height - 65), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 40), fill=(255, 255, 255))
    image.save(nametosave)
    
def render_aqua_style(header:str, user_data: json, arr: list[str], nametosave:str) -> None:
    # calculating cosmetics per row
    cosmetic_per_row = 6
    total_cosmetics = len(arr)
    num_rows = math.ceil(total_cosmetics / cosmetic_per_row)
    if total_cosmetics > 30:
        num_rows = int(math.sqrt(total_cosmetics))
        cosmetic_per_row = math.ceil(total_cosmetics / num_rows)
        
        while cosmetic_per_row * num_rows < total_cosmetics:
            num_rows += 1
            cosmetic_per_row = math.ceil(total_cosmetics / num_rows)

    # setup for our image, thumbnails
    padding = 30
    padding_height = 2
    thumbnail_width = 128
    thumbnail_height = 128
    image_width = int(cosmetic_per_row * thumbnail_width)
    image_height = int(thumbnail_height + 5 + (num_rows * (padding_height + thumbnail_height)) + 140)
    font_path = 'styles/aqua/font.ttf'
    font_size = 16
    font = ImageFont.truetype(font_path, font_size)
    image = Image.new('RGB', (image_width, image_height), (0, 0, 0))
        
    current_row = 0
    current_column = 0
    sortarray = ['mythic', 'legendary', 'dark', 'slurp', 'starwars', 'marvel', 'lava', 'frozen', 'gaminglegends', 'shadow', 'icon', 'dc', 'epic', 'rare', 'uncommon', 'common']
    arr.sort(key=lambda x: sortarray.index(x.rarity_value))

    # had some issues with exclusives rendering in wrong order, so i'm sorting them
    try:
        with open('exclusive.txt', 'r', encoding='utf-8') as f:
            exclusive_cosmetics = [i.strip() for i in f.readlines()]
        
        with open('most_wanted.txt', 'r', encoding='utf-8') as f:
            popular_cosmetics = [i.strip() for i in f.readlines()]
    except FileNotFoundError:
        print("Error: 'exclusive.txt' or 'most_wanted.txt' not found.")
        exclusive_cosmetics = []
        popular_cosmetics = []

    mythic_items = [item for item in arr if item.rarity_value == 'mythic']
    other_items = [item for item in arr if item.rarity_value != 'mythic']
    mythic_items.sort(
        key=lambda x: exclusive_cosmetics.index(x.cosmetic_id) 
        if x.cosmetic_id in exclusive_cosmetics else float('inf')
    )
        
    if header == "Popular":
        other_items.sort(
            key=lambda x: popular_cosmetics.index(x.cosmetic_id) 
            if x.cosmetic_id in popular_cosmetics else float('inf')
        )
        
    arr = mythic_items + other_items
    draw = ImageDraw.Draw(image)

    # top
    icon_logo = Image.open(f'cosmetic_icons/{header}.png').resize((128, 128), Image.Resampling.BILINEAR)
    icon_logo.thumbnail((thumbnail_width, thumbnail_height)) 
    image.paste(icon_logo, (10, 5), mask=icon_logo)
    draw.text((162, 30), '{}'.format(len(arr)), font=ImageFont.truetype(font_path, 70), fill=(0, 0, 0)) # shadow
    draw.text((166, 87), '{}'.format(header), font=ImageFont.truetype(font_path, 40), fill=(0, 0, 0)) # shadow
    draw.text((162, 26), '{}'.format(len(arr)), font=ImageFont.truetype(font_path, 70), fill=(255, 255, 255))
    draw.text((166, 83), '{}'.format(header), font=ImageFont.truetype(font_path, 40), fill=(167, 167, 167))
        
    special_items = {
        "CID_029_Athena_Commando_F_Halloween": "cache/pink_ghoul.png",
        "CID_030_Athena_Commando_M_Halloween": "cache/purple_skull_old.png",
        "CID_116_Athena_Commando_M_CarbideBlack": "cache/omega_max.png",
        "CID_694_Athena_Commando_M_CatBurglar": "cache/gold_midas.png",
        "CID_693_Athena_Commando_M_BuffCat": "cache/gold_cat.png",
        "CID_691_Athena_Commando_F_TNTina": "cache/gold_tntina.png",
        "CID_690_Athena_Commando_F_Photographer": "cache/gold_skye.png",
        "CID_701_Athena_Commando_M_BananaAgent": "cache/gold_peely.png",
        "CID_315_Athena_Commando_M_TeriyakiFish": "cache/worldcup_fish.png",
        "CID_971_Athena_Commando_M_Jupiter_S0Z6M": "cache/black_masterchief.png",
        "CID_028_Athena_Commando_F": "cache/og_rene.png",
        "CID_017_Athena_Commando_M": "cache/og_aat.png"
    }
        
    for cosmetic in arr:
        special_icon = False
        is_banner = cosmetic.is_banner
        photo = None
        if cosmetic.rarity_value.lower() == "mythic" and cosmetic.cosmetic_id in special_items:
            special_icon = True
            icon_path = special_items[cosmetic.cosmetic_id]
            if os.path.exists(icon_path):
                try:
                    photo = Image.open(icon_path)
                except Exception as e:
                    special_icon = False
            else:
                special_icon = False
        else:
            photo = fortnite_cache.get_cosmetic_icon_from_cache(cosmetic.small_icon, cosmetic.cosmetic_id)
            
        if is_banner:
            scaled_width = int(photo.width * 1.5)
            scaled_height = int(photo.height * 1.5)
            photo = photo.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            x_offset = 32
            y_offset = 10
                
            new_img = Image.open(f'styles/aqua/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA')
            new_img.paste(photo, (x_offset, y_offset), mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))
        else:
            new_img = Image.open(f'styles/aqua/rarity/{cosmetic.rarity_value.lower()}.png').convert('RGBA').resize(photo.size)    
            new_img.paste(photo, mask=photo)
            photo = new_img
            photo.thumbnail((thumbnail_width, thumbnail_height))

        # black box for cosmetic name
        box = Image.new('RGBA', (128, 27), (0, 0, 0, 100))
        photo.paste(box, (0, new_img.size[1] - 27), mask=box)
            
        if header != "Exclusives" and cosmetic.cosmetic_id in popular_cosmetics:
            star_image = Image.open('cosmetic_icons/WantedStar.png').resize((128, 128), Image.BILINEAR)
            photo.paste(star_image, (0, 0), star_image.convert("RGBA"))

        x = thumbnail_width * current_column
        y = thumbnail_width + (thumbnail_height + padding_height) * current_row
        image.paste(photo, (x, y))

        name = cosmetic.name.upper()
        max_text_width = thumbnail_width - 10
        max_text_height = 20
            
        # fixed font size
        font_size = 16
        offset = 6
        while True:
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), name, font=font)
            name_width = bbox[2] - bbox[0]
            name_height = bbox[3] - bbox[1]

            if name_width > max_text_width or name_height > max_text_height:
                font_size -= 1
                offset += 0.5
            else:
                break

        # cosmetic name
        bbox = draw.textbbox((0, 0), name, font=font)
        name_width = bbox[2] - bbox[0]
        draw.text((x + (thumbnail_width - name_width) // 2, y + (thumbnail_height - padding + offset)), name, font=font, fill=(255, 255, 255))
            
        # make the cosmetics show ordered in rows(cosmetic_per_row is hardcoded)
        current_column += 1
        if current_column >= cosmetic_per_row:
            current_row += 1
            current_column = 0

    # footer
    current_date = datetime.now().strftime('%d %B %Y')
    
    # custom logo
    custom_logo_path = f"users/logos/{user_data['ID']}.png"
    if os.path.isfile(custom_logo_path):
        custom_logo = Image.open(custom_logo_path).resize((125, 125), Image.Resampling.BILINEAR)
        image.paste(custom_logo, (25, image_height - 140), mask=custom_logo)
    else:
        # original logo if not found
        logo = Image.open('img/logo.png').resize((125, 125), Image.Resampling.BILINEAR)     
        image.paste(logo, (25, image_height - 140), mask=logo)

    draw.text((179, image_height - 114), '{}'.format(current_date), font=ImageFont.truetype(font_path, 30), fill=(0, 0, 0)) # shadow
    draw.text((175, image_height - 118), '{}'.format(current_date), font=ImageFont.truetype(font_path, 30), fill=(255, 255, 255))  
    draw.text((179, image_height - 84), 'Submitted By: @{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 30), fill=(0, 0, 0)) # shadow 
    draw.text((175, image_height - 88), 'Submitted By: @{}'.format(user_data['username']), font=ImageFont.truetype(font_path, 30), fill=(255, 255, 255))
    draw.text((179, image_height - 31), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 20), fill=(0, 0, 0)) # shadow     
    draw.text((175, image_height - 55), "t.me/ExoCheckerBot", font=ImageFont.truetype(font_path, 20), fill=(255, 255, 255))
    image.save(nametosave)
    
    
    
def command_start(bot, message):
    if message.chat.type != "private":
        return
    
    user = ExoUser(message.from_user.id, message.from_user.username)
    user_data = user.register()
    if not user_data:
        bot.reply_to(message, "You have already used this command, you don't have to use it anymore!")
        return
    
    bot.reply_to(message, f'''
What is Exo-Checker Bot?
> Exo-Checker is provably safe open-sourced telegram fortnite skin checker bot, it visualises your locker into an image and sends it back to you, aswell it does display info about your account.

Why should we use Exo and not other skincheckers?
> Unlike majority of skincheckers, we make NO profit from our service, the bot is entirely hosted by choice, as well unlike Raika we DO NOT store your account information anywhere, for security reasons all account credentials are private and inaccessible.

How do i know you're not stealing our accounts?
> Exo-Checker is open-sourced bot, if you don't believe that it's safe, you could check the source code yourself to make sure that Exo is completely safe!
> Exo-Checker's Official Github Repository: https://github.com/im-test-yes/Exo-Checker
> Yes, you could use Exo's source code to create your own bot aswell! just make to credit @xhexago for his work :)

> Other open sourced projects by @xhexago:
    - GrowBase(Growtopia Private Server - Game Server source code): https://github.com/Debugtopia/GrowBase

Who are the developers of Exo-Checker Bot?
> Exo is a single-handedly developed by @xhexago and nobody else.

Commands:
/start - register to Exo-Checker
/help - displays info about the bot, it's commands.
/login - skincheck your epic games fortnite account.
/style - choose your style based on your need, we support multiple skincheck styles.
/badges - toggle your achieved badges on your skincheck.
/stats - shows statistics of how many accounts have u checked with our bot or the badges you have enabled.
''')
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Source Code", url="https://github.com/im-test-yes/Exo-Checker")],
        [InlineKeyboardButton("🔗 Stock Channel", url="https://t.me/exostock"),
         InlineKeyboardButton("🔗 News Channel", url="https://t.me/ExoCheckerNews")]
    ])

    bot.send_message(
        chat_id=message.chat.id,
        text=(
            "Welcome to Exo-Checker Bot!\n"
            "Developed by @xhexago\n"
            "Interested in purchasing Fortnite accounts?\n"
            "- @exostock\n\n"
            "Exo-Checker Bot's News channel:\n"
            "- @exocheckernews"
        ),
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
def command_help(bot, message):
    bot.reply_to(message, f'''
What is Exo-Checker Bot?
> Exo-Checker is provably safe open-sourced telegram fortnite skin checker bot, it visualises your locker into an image and sends it back to you, aswell it does display info about your account.

Why should we use Exo and not other skincheckers?
> Unlike majority of skincheckers, we make NO profit from our service, the bot is entirely hosted by choice, as well unlike Raika we DO NOT store your account information anywhere, for security reasons all account credentials are private and inaccessible.

How do i know you're not stealing our accounts?
> Exo-Checker is open-sourced bot, if you don't believe that it's safe, you could check the source code yourself to make sure that Exo is completely safe!
> Exo-Checker's Official Github Repository: https://github.com/im-test-yes/Exo-Checker
> Yes, you could use Exo's source code to create your own bot aswell! just make to credit @xhexago for his work :)

> Other open sourced projects by @xhexago:
    - GrowBase(Growtopia Private Server - Game Server source code): https://github.com/Debugtopia/GrowBase

Who are the developers of Exo-Checker Bot?
> Exo is a single-handedly developed by @xhexago and nobody else.

Commands:
/start - register to Exo-Checker
/help - displays info about the bot, it's commands.
/login - skincheck your epic games fortnite account.
/style - choose your style based on your need, we support multiple skincheck styles.
/badges - toggle your achieved badges on your skincheck.
/stats - shows statistics of how many accounts have u checked with our bot or the badges you have enabled.
''')
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Source Code", url="https://github.com/im-test-yes/Exo-Checker")],
        [InlineKeyboardButton("🔗 Stock Channel", url="https://t.me/exostock"),
         InlineKeyboardButton("🔗 News Channel", url="https://t.me/ExoCheckerNews")]
    ])

    bot.send_message(
        chat_id=message.chat.id,
        text=(
            "Welcome to Exo-Checker Bot!\n"
            "Developed by @xhexago\n"
            "Interested in purchasing Fortnite accounts?\n"
            "- @exostock\n\n"
            "Exo-Checker Bot's News channel:\n"
            "- @exocheckernews"
        ),
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
async def command_login(bot, message):
    if message.chat.type != "private":
        return
    
    user = ExoUser(message.from_user.id, message.from_user.username)
    user_data = user.load_data()
    if user_data == {}:
        bot.reply_to(message, "You haven't setup your user yet, please use /start before skinchecking!")
        return
    
    msg = bot.reply_to(message, "⏳ Creating authorization login link...")
    epic_generator = EpicGenerator()
    await epic_generator.start()
    device_data = await epic_generator.create_device_code()
    epic_games_auth_link = f"https://www.epicgames.com/activate?userCode={device_data['user_code']}"

    # login link message(embed link button)
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton("🔗 Login", url=epic_games_auth_link)
    markup.add(button)
    bot.edit_message_text(
        chat_id=msg.chat.id,
        message_id=msg.message_id,
        text=f"Open [this link](<{epic_games_auth_link}>) to log in to your account.", 
        reply_markup=markup,
        parse_mode="Markdown")
    
    epic_user = await epic_generator.wait_for_device_code_completion(bot, message, code=device_data['device_code'])
    if not epic_user:
        # something went wrong so we can't check the account
        await epic_generator.kill()
        return
    
    account_data = await epic_generator.get_account_metadata(epic_user)
   
    accountID = account_data.get('id', "INVALID_ACCOUNT_ID")
    if (accountID == "INVALID_ACCOUNT_ID"):
        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text="Invalid account(banned or fortnite has not been launched).")
        return
    
    bot.delete_message(msg.chat.id, msg.message_id)
    msg = bot.send_message(message.chat.id, f'✅ Logged in account {account_data.get("displayName", "HIDDEN_ID_ACCOUNT")}')

    # account information
    account_public_data = await epic_generator.get_public_account_info(epic_user)
    bot.send_message(message.chat.id,f'''
━━━━━━━━━━━
Account Information
━━━━━━━━━━━
#️⃣ Account ID: {mask_account_id(accountID)}
📧 Email: {mask_email(account_data.get('email', ''))}          
🧑‍🦱 Display Name: {account_data.get('displayName', 'DeletedUser')}
📛 Full Name: {account_data.get('name', '')} {account_data.get('lastName', '')}
🌐 Country: {account_data.get('country', 'US')} {country_to_flag(account_data.get('country', 'US'))}
🔐 Email Verified: {bool_to_emoji(account_data.get('emailVerified', False))}
🔒 Mandatory 2FA Security: {bool_to_emoji(account_data.get('tfaEnabled', False))}
''')
    
    # external connections
    connected_accounts = 0
    connected_accounts_message = f"""
━━━━━━━━━━━
Connected Account
━━━━━━━━━━━\n"""
 
    external_auths = account_public_data.get('externalAuths', [])
    for auth in external_auths:
        auth_type = auth.get('type', '?').lower()
        display_name = auth.get('externalDisplayName', '?')
        external_id = auth.get('externalAuthId', '?')
        date_added = auth.get('dateAdded', '?')
        if date_added != '?':
            parsed_date = datetime.strptime(date_added, "%Y-%m-%dT%H:%M:%S.%fZ")
            date_added = parsed_date.strftime("%d/%m/%Y")

        connected_accounts += 1
        connected_accounts_message += f"""
Connection Type: {escape_markdown(auth_type.upper())}
External Display Name: {escape_markdown(display_name)}
Date of Connection: {escape_markdown(date_added)}
"""

    if connected_accounts == 0:
        connected_accounts_message += "No connected accounts."

    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton("🔗 Remove Restrictions", url='https://www.epicgames.com/help/en/wizards/w4')
    markup.add(button)
    bot.send_message(
        chat_id=msg.chat.id,
        text=connected_accounts_message, 
        reply_markup=markup,
        parse_mode="Markdown")
    
    # purchases infos
    vbucks_categories = [
        "Currency:MtxPurchased",
        "Currency:MtxEarned",
        "Currency:MtxGiveaway",
        "Currency:MtxPurchaseBonus"
    ]
        
    total_vbucks = 0
    refunds_used = 0
    refund_credits = 0
    receipts = []
    vbucks_purchase_history = {
        "1000": 0,
        "2800": 0,
        "5000": 0,
        "7500": 0,
        "13500": 0
    }

    gift_received = 0
    gift_sent = 0
    pending_gifts_amount = 0
    
    common_profile_data = await epic_generator.get_common_profile(epic_user)
    for item_id, item_data in common_profile_data.get("profileChanges", [{}])[0].get("profile", {}).get("items", {}).items():
        if item_data.get("templateId") in vbucks_categories:
            # getting vbucks
            total_vbucks += item_data.get("quantity", 0)
    
    for profileChange in common_profile_data.get("profileChanges", []):
        attributes = profileChange["profile"]["stats"]["attributes"]
        mtx_purchases = attributes.get("mtx_purchase_history", {})
        if mtx_purchases:
            refunds_used = mtx_purchases.get("refundsUsed", 0)
            refund_credits = mtx_purchases.get("refundCredits", 0)
            
        iap = attributes.get("in_app_purchases", {})
        if iap:
            receipts = iap.get("receipts", [])
            purchases = iap.get("fulfillmentCounts", {})
            if purchases:
                # vbucks purchases packs amount
                vbucks_purchase_history["1000"] = purchases.get("FN_1000_POINTS", 0)
                vbucks_purchase_history["2800"] = purchases.get("FN_2800_POINTS", 0)
                vbucks_purchase_history["5000"] = purchases.get("FN_5000_POINTS", 0)
                vbucks_purchase_history["7500"] = purchases.get("FN_7500_POINTS", 0)
                vbucks_purchase_history["13500"] = purchases.get("FN_13500_POINTS", 0)

        gift_history = attributes.get("gift_history", {})
        if gift_history:
            # pending gifts count
            gifts_pending = gift_history.get("gifts", [])
            pending_gifts_amount = len(gifts_pending)

            # gifts sent & received count
            gift_sent = gift_history.get("num_sent", 0)
            gift_received = gift_history.get("num_received", 0)

    total_vbucks_bought = 1000 * vbucks_purchase_history["1000"] + 2800 * vbucks_purchase_history["2800"] + 5000 * vbucks_purchase_history["5000"] + 7500 * vbucks_purchase_history["7500"] + 13500 * vbucks_purchase_history["13500"]
    bot.send_message(message.chat.id,f'''
━━━━━━━━━━━
Purchases Information
━━━━━━━━━━━
💰 VBucks: {total_vbucks}
🎟  Refunds Used: {refunds_used}
🎟  Refund Tickets: {refund_credits}

━━━━━━━━━━━
Vbucks Purchases
━━━━━━━━━━━
#️⃣ Receipts: {len(receipts)}
💰 1000 Vbucks Packs: {vbucks_purchase_history["1000"]}
💰 2800 Vbucks Packs: {vbucks_purchase_history["2800"]}
💰 5000 Vbucks Packs: {vbucks_purchase_history["5000"]}
💰 7500 Vbucks Packs: {vbucks_purchase_history["7500"]}
💰 13500 Vbucks Packs: {vbucks_purchase_history["13500"]}

💰 Total Vbucks Purchased: {total_vbucks_bought}

━━━━━━━━━━━
Gifts Information
━━━━━━━━━━━
🎁 Pending Gifts: {pending_gifts_amount}
🎁 Gifts Sent: {gift_sent}
🎁 Gifts Received: {gift_received}
''')
    
    # season history
    seasons_msg = await epic_generator.get_seasons_message(epic_user)
    bot.send_message(message.chat.id, seasons_msg)

    # locker data
    locker_data = await epic_generator.get_locker_data(epic_user)
    
    # activity info
    bot.send_message(message.chat.id,f'''
━━━━━━━━━━━
Activity Information
━━━━━━━━━━━
👪 Parental Control: {bool_to_emoji(account_data.get('minorVerified', False))}
🕘 Last Match: {locker_data.last_match}
🤯 Headless: {bool_to_emoji(account_data.get("headless", False))}
✏️ Display Name Changes: {account_data.get("numberOfDisplayNameChanges", 0)}
✏️ Display Name Changeable: {bool_to_emoji(account_data.get("canUpdateDisplayName", False))}
#️⃣ Hashed email: {bool_to_emoji(account_data.get("hasHashedEmail", False))}
''')
    
    bot.send_message(message.chat.id,f'''
━━━━━━━━━━━
Locker Information
━━━━━━━━━━━
🧍‍♂️  Outfits: {len(locker_data.cosmetic_array.get('AthenaCharacter', []))}
🎒  Backpacks: {len(locker_data.cosmetic_array.get('AthenaBackpack', []))}
⛏️  Pickaxes: {len(locker_data.cosmetic_array.get('AthenaPickaxe', []))}
🕺  Emotes: {len(locker_data.cosmetic_array.get('AthenaDance', []))}
✈️  Gliders: {len(locker_data.cosmetic_array.get('AthenaGlider', []))}
⭐  Most Wanted Cosmetics: {len(locker_data.cosmetic_array.get('AthenaPopular', []))}
🌟  Exclusives: {len(locker_data.cosmetic_array.get('AthenaExclusive', []))}
''')
    
    homebase_data = await epic_generator.get_homebase_profile(epic_user)
    stats = homebase_data.get("profileChanges", [{}])[0].get("profile", {}).get("stats", {}).get("attributes", {})
    if stats:
        stw_level = 1
        research_offence = 1
        research_fortitude = 1
        research_resistance = 1
        research_tech = 1
        collection_book_level = 1
        stw_claimed = False
        legacy_research_points = 0
        matches_played = 0
    
        stats = homebase_data.get("profileChanges", [{}])[0].get("profile", {}).get("stats", {}).get("attributes", {})
        if stats:
            stw_level = stats.get("level", 1)
            research_offence = stats.get("research_levels", {}).get("offence", 1)
            research_fortitude = stats.get("research_levels", {}).get("fortitude", 1)
            research_resistance = stats.get("research_levels", {}).get("resistance", 1)
            research_tech = stats.get("research_levels", {}).get("technology", 1)
            collection_book_level = stats.get("collection_book", {}).get("maxBookXpLevelAchieved", 1)
            stw_claimed = stats.get("mfa_reward_claimed", False)
            legacy_research_points = stats.get("legacy_research_points_spent", 0)
            matches_played = stats.get("matches_played", 0)
        bot.send_message(message.chat.id,f'''
━━━━━━━━━━━
Homebase Information
━━━━━━━━━━━
#️⃣ Level: {stw_level}
🎒 Collection Book Level: {collection_book_level}
🎁 Claimed Rewards: {bool_to_emoji(stw_claimed)}

Research:
⭐ Total spent points: {legacy_research_points}
⛏️ Offence: {research_offence}
⚔️ Fortitude: {research_fortitude}
🪖 Resistance: {research_resistance}
🔧 Tech: {research_tech}

Activity:
🎟  Matches Played: {matches_played}
''')
        
    # saved data path
    # note: it only saves the rendered images for locker, data that DOES NOT contain private or login information!!!
    save_path = f"accounts/{accountID}"
    if not os.path.exists(save_path):
       os.mkdir(save_path)

    for category in locker_categories:
        if category not in locker_data.cosmetic_array or len(locker_data.cosmetic_array[category]) < 1:
            continue

        header = 'Outfits'
        if category == 'AthenaBackpack':
            header = 'Backblings'
        elif category == 'AthenaPickaxe':
            header = 'Pickaxes'
        elif category == 'AthenaDance':
            header = 'Emotes'
        elif category == 'AthenaGlider':
            header = 'Gliders'
        elif category == 'AthenaExclusive':
            header = 'Exclusives'
        elif category == 'AthenaPopular':
            header = 'Popular'
            
        if user_data['style'] == 0: # exo style
            render_exo_style(header, user_data, locker_data.cosmetic_array[category], f'{save_path}/{category}.png')
            
        elif user_data['style'] == 1: # easy style
            render_easy_style(header, user_data, locker_data.cosmetic_array[category], f'{save_path}/{category}.png')
                     
        elif user_data['style'] == 2: # raika style
            render_raika_style(header, user_data, locker_data.cosmetic_array[category], f'{save_path}/{category}.png')
            
        elif user_data['style'] == 3: # kayy style
            render_kayy_style(header, user_data, locker_data.cosmetic_array[category], f'{save_path}/{category}.png') 
             
        elif user_data['style'] == 4: # storm style
            render_storm_style(header, user_data, locker_data.cosmetic_array[category], f'{save_path}/{category}.png') 
        
        elif user_data['style'] == 5: # aqua style
            render_aqua_style(header, user_data, locker_data.cosmetic_array[category], f'{save_path}/{category}.png') 
                
        with open(f'{save_path}/{category}.png', 'rb') as photo_file:
            file_size = os.path.getsize(f'{save_path}/{category}.png')
            if file_size > 10 * 1024 * 1024:  # 10 MBs
                print("File too large for photo, sending as a document.")
                bot.send_document(msg.chat.id, photo_file)
            else:
                bot.send_photo(msg.chat.id, photo_file)

    skins = len(locker_data.cosmetic_array['AthenaCharacter'])
    excl = locker_data.cosmetic_array['AthenaExclusive']
    cosmetic_list = ''
    desc = ''      
    cosmetics_listed = 0
    for cosmetic in excl:
        cosmetic_list += cosmetic.name + " + "
        cosmetics_listed += 1
        
        if cosmetics_listed >= 10:
            break
    
    cosmetic_list = cosmetic_list.rstrip(" + ")
    desc = f'{skins} + {cosmetic_list} + {total_vbucks}VB'
    bot.send_message(message.chat.id,f'{desc}')
    await epic_generator.kill()
    
    # button-embed message
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Source Code", url="https://github.com/im-test-yes/Exo-Checker")],
        [InlineKeyboardButton("🔗 Exo Stock", url="https://t.me/exostock"),
         InlineKeyboardButton("🔗 News Channel", url="https://t.me/ExoCheckerNews")]
    ])

    bot.send_message(
        chat_id=message.chat.id,
        text=(
            "Thanks for using Exo-Checker Bot!\n"
            "Developed by @xhexago\n"
            "Interested in purchasing Fortnite accounts?\n"
            "- @exostock\n\n"
            "Exo-Checker Bot's News channel:\n"
            "- @exocheckernews"
        ),
        reply_markup=markup,
        parse_mode="Markdown"
    )
    

async def command_style(bot, message):
    if message.chat.type != "private":
        return
    
    user = ExoUser(message.from_user.id, message.from_user.username)
    user_data = user.load_data()
    if not user_data:
        bot.reply_to(message, "You haven't setup your user yet, please use /start before skinchecking!")
        return
        
    current_style_index = user_data['style']
    send_style_message(bot, message.chat.id, current_style_index)

async def command_badges(bot, message):
    if message.chat.type != "private":
        return
    
    user = ExoUser(message.from_user.id, message.from_user.username)
    user_data = user.load_data()
    if not user_data:
        bot.reply_to(message, "You haven't setup your user yet, please use /start before skinchecking!")
        return
        
    badges_unlocked = 0
    for badge in avaliable_badges:
        if user_data[badge['data']] == True:
            badges_unlocked += 1
    
    if badges_unlocked < 1:
        msg = bot.reply_to(message, "You don't have any badges unlocked.")
        return
                  
    current_badge_index = 0
    send_badges_message(bot, message.chat.id, current_badge_index, user_data)

async def command_stats(bot, message):
    if message.chat.type != "private":
        return
    
    user = ExoUser(message.from_user.id, message.from_user.username)
    user_data = user.load_data()
    if not user_data:
        bot.reply_to(message, "You haven't setup your user yet, please use /start before skinchecking!")
        return
    
    style = 'exo'
    if user_data['style'] == 0:
        style = 'exo'
    elif user_data['style'] == 1:
        style = 'easy'
    elif user_data['style'] == 2:
        style = 'raika'
    elif user_data['style'] == 3:
        style = 'kayy'
    elif user_data['style'] == 4:
        style = 'storm'
    elif user_data['style'] == 5:
        style = 'aqua'
    else:
        style = 'unknown style'
          
    msg = bot.reply_to(message, f'''
Stats for user {message.from_user.username}(#{user_data['ID']}):
Checked accounts: {user_data['accounts_checked']}
Style: {style}

Badges:
Alpha Tester 1 Badge: {bool_to_emoji(user_data['alpha_tester_1_badge'])}
> Badge Enabled: {bool_to_emoji(user_data['alpha_tester_1_badge_active'])}
Alpha Tester 2 Badge: {bool_to_emoji(user_data['alpha_tester_2_badge'])}
> Badge Enabled: {bool_to_emoji(user_data['alpha_tester_2_badge_active'])}
Alpha Tester 3 Badge: {bool_to_emoji(user_data['alpha_tester_3_badge'])}
> Badge Enabled: {bool_to_emoji(user_data['alpha_tester_3_badge_active'])}
Epic Games Badge: {bool_to_emoji(user_data['epic_badge'])}
> Badge Enabled: {bool_to_emoji(user_data['epic_badge_active'])}
100 Checks Badge: {bool_to_emoji(user_data['newbie_badge'])}
> Badge Enabled: {bool_to_emoji(user_data['newbie_badge_active'])}
200 Checks Badge: {bool_to_emoji(user_data['advanced_badge'])}
> Badge Enabled: {bool_to_emoji(user_data['advanced_badge_active'])}
''')
    
def send_style_message(bot, chat_id, style_index):
    style = available_styles[style_index]
    markup = InlineKeyboardMarkup()

    if style_index > 0:
        markup.add(InlineKeyboardButton("◀️", callback_data=f"style_{style_index - 1}"))
    if style_index < len(available_styles) - 1:
        markup.add(InlineKeyboardButton("▶️", callback_data=f"style_{style_index + 1}"))

    markup.add(InlineKeyboardButton("✅ Select This Style", callback_data=f"select_{style_index}"))
    with open(style['image'], 'rb') as img_file:
        img = Image.open(style['image']).convert("RGBA") 
        bot.send_photo(
            chat_id,
            img,
            caption=f"{style['name']}",
            reply_markup=markup,
            parse_mode="Markdown"
        )

def send_badges_message(bot, chat_id, badge_index, user_data):
    unlocked_badges = [
        (i, badge)
        for i, badge in enumerate(avaliable_badges)
        if user_data.get(badge['data'], False)
    ]
    
    if not unlocked_badges:
        bot.send_message(chat_id, "You don't have any badges unlocked.")
        return

    badge_index = min(max(0, badge_index), len(unlocked_badges) - 1)
    actual_index, badge = unlocked_badges[badge_index]

    badge_status = user_data.get(badge['data2'], False)
    toggle_text = "✅ Enabled" if badge_status else "❌ Disabled"

    markup = InlineKeyboardMarkup()
    if badge_index > 0:
        markup.add(InlineKeyboardButton("◀️", callback_data=f"badge_{badge_index - 1}"))
    if badge_index < len(unlocked_badges) - 1: 
        markup.add(InlineKeyboardButton("▶️", callback_data=f"badge_{badge_index + 1}"))
    markup.add(InlineKeyboardButton(toggle_text, callback_data=f"toggle_{actual_index}"))

    try:
        with open(badge['image'], 'rb') as img:
            bot.send_photo(
                chat_id,
                img,
                caption=f"{badge['name']}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
    except FileNotFoundError:
        bot.send_message(chat_id, f"Image for badge {badge['name']} not found.")