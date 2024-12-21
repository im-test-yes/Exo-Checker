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
from commands import command_start, command_help, command_login, command_style, send_style_message, available_styles, avaliable_badges

import epic_auth
import cosmetic
import commands
import utils

# your telegram bot's api token
TELEGRAM_API_TOKEN = ""
# your discord bot's token
DISCORD_BOT_TOKEN = ""

# locker categories we render in the checker
telegram_bot = telebot.TeleBot(TELEGRAM_API_TOKEN)

telegram_bot.set_my_commands([
    telebot.types.BotCommand("/start", "Setup your user to start skinchecking."),
    telebot.types.BotCommand("/help", "Display Basic Info and the commands."),
    telebot.types.BotCommand("/login", "Skincheck your Epic Games account."),
    telebot.types.BotCommand("/style", "Customize your checker's style.")
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
    asyncio.run(command_login(telegram_bot, message))

@telegram_bot.message_handler(commands=['style'])
def handle_style(message):
    asyncio.run(command_style(telegram_bot, message))

@telegram_bot.callback_query_handler(func=lambda call: call.data.startswith("style_") or call.data.startswith("select_"))
def handle_style_navigation(call):
    data = call.data
    user = RiftUser(call.message)

    user_data = user.load_data(call.message)
    if not user_data:
        telegram_bot.reply_to(call.message, "You haven't setup your user yet, please use /start before skinchecking!")
        return 
    
    if data.startswith("style_"):
        new_index = int(data.split("_")[1])
        telegram_bot.delete_message(call.message.chat.id, call.message.message_id)
        send_style_message(telegram_bot, call.message.chat.id, new_index)

    elif data.startswith("select_"):
        selected_index = int(data.split("_")[1])
        selected_style = available_styles[selected_index]
        user_data['style'] = selected_style['ID']
        user.update_data()
        telegram_bot.send_message(call.message.chat.id, f"✅ Style {selected_style['name']} selected.")

print("starting rift checker...")          
if __name__ == '__main__':
    telegram_bot.infinity_polling()