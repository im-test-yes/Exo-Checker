import os
import json
import aiohttp
import asyncio
import random
import threading
import telebot
from io import BytesIO
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from PIL import Image, ImageDraw, ImageFont
from epic_auth import EpicUser, EpicGenerator, EpicEndpoints
from user import RiftUser
from cosmetic import FortniteCosmetic
from commands import command_start, command_help, command_login

import epic_auth
import cosmetic
import commands
import utils

# your telegram bot's api token
TELEGRAM_API_TOKEN = ""

# locker categories we render in the checker
locker_categories = ['AthenaCharacter', 'AthenaBackpack', 'AthenaPickaxe', 'AthenaDance', 'AthenaGlider', 'AthenaPopular', 'AthenaExclusive']
telegram_bot = telebot.TeleBot(TELEGRAM_API_TOKEN)

telegram_bot.set_my_commands([
    telebot.types.BotCommand("/start", "Setup your user to start skinchecking."),
    telebot.types.BotCommand("/help", "Display Basic Info and the commands."),
    telebot.types.BotCommand("/login", "Skincheck your Epic Games account.")
])

auth_code = None
@telegram_bot.message_handler(commands=['start'])
def handle_start(message):
    command_start(telegram_bot, message)

@telegram_bot.message_handler(commands=['help'])
def handle_help(message):
    command_help(telegram_bot, message)

@telegram_bot.message_handler(commands=['login'])
def handle_login(message):
    import asyncio
    asyncio.run(command_login(telegram_bot, message))

print("starting rift checker...")          
if __name__ == '__main__':
    telegram_bot.infinity_polling()