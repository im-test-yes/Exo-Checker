import os
import json
import user
import logging
import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import mask_email, mask_account_id, bool_to_emoji, country_to_flag
from user import RiftUser
from epic_auth import EpicUser, EpicEndpoints, EpicGenerator

def command_start(bot, message):
    if message.chat.type != "private":
        return
    
    user = RiftUser(message)
    user_data = user.register(message)
    if user_data == {}:
        bot.reply_to(message, "You have already used this command, you don't have to use it anymore!")
        return
    
    bot.reply_to(message, f'''
What is Rift Checker Bot?
> Rift is a free2use non-profit telegram fortnite skin checker bot, it visualises your locker into an image and sends it back to you, aswell it does display info about your account.

Why should we use Rift and not other skincheckers?
> Unlike majority of skincheckers, we make NO profit from our service, the bot is entirely hosted by choice, as well unlike Raika we DO NOT store your account information anywhere, for security reasons all account credentials are private and inaccessible.

How do i know you're not stealing our accounts?
> Rift checker will soon be open-sourced, if you don't believe that, you could soon check the source code yourself to make sure that rift is completely safe!
> Rift Checker's Official Github Repository(Currently Private): https://github.com/Debugtopia/RiftCheckerBot
> Other open sourced projects by @xhexago:
    - GrowBase(Growtopia Private Server - Game Server source code): https://github.com/Debugtopia/GrowBase

Who are the developers of Rift Checker Bot?
> Rift is a single-handedly developed by @xhexago and nobody else.

Commands:
/start - register to rift checker
/help - displays info about the bot, it's commands.
/login - skincheck your epic games fortnite account.
/style - choose your style based on your need, we support multiple skincheck styles.
/badges - toggle your achieved badges on your skincheck
/locker - shows last locker image for specified accountID(NOTE: it's inaccurate, because we use ALREADY CHECKED images)
''')
    
def command_help(bot, message):
    bot.reply_to(message, f'''
What is Rift Checker Bot?
> Rift is a free2use non-profit telegram fortnite skin checker bot, it visualises your locker into an image and sends it back to you, aswell it does display info about your account.

Why should we use Rift and not other skincheckers?
> Unlike majority of skincheckers, we make NO profit from our service, the bot is entirely hosted by choice, as well unlike Raika we DO NOT store your account information anywhere, for security reasons all account credentials are private and inaccessible.

How do i know you're not stealing our accounts?
> Rift checker will soon be open-sourced, if you don't believe that, you could soon check the source code yourself to make sure that rift is completely safe!
> Rift Checker's Official Github Repository(Currently Private): https://github.com/Debugtopia/RiftCheckerBot
> Other open sourced projects by @xhexago:
    - GrowBase(Growtopia Private Server - Game Server source code): https://github.com/Debugtopia/GrowBase

Who are the developers of Rift Checker Bot?
> Rift is a single-handedly developed by @xhexago and nobody else.

Commands:
/start - register to rift checker
/help - displays info about the bot, it's commands.
/login - skincheck your epic games fortnite account.
/style - choose your style based on your need, we support multiple skincheck styles.
/badges - toggle your achieved badges on your skincheck
/locker - shows last locker image for specified accountID(NOTE: it's inaccurate, because we use ALREADY CHECKED images)
''')
    
async def command_login(bot, message):
    if message.chat.type != "private":
        return
    
    user = RiftUser(message)
    user_data = user.load_data(message)
    if user_data == {}:
        bot.reply_to(message, "You haven't setup your user yet, please use /start before skinchecking!")
        return
    
    epic_generator = EpicGenerator()
    await epic_generator.start()

    device_data = await epic_generator.create_device_code()
    epic_games_auth_link = f"https://www.epicgames.com/activate?userCode={device_data['user_code']}"
    msg = bot.reply_to(message, "⏳ Creating authorization login link...")

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
    
    epic_user = await epic_generator.wait_for_device_code_completion(code=device_data['device_code'])
    account_data = await epic_generator.get_account_metadata(epic_user)
    account_public_data = await epic_generator.get_public_account_info(epic_user)
    common_profile_data = await epic_generator.get_common_profile(epic_user)

    accountID = account_data.get('id', "INVALID_ACCOUNT_ID")
    if (accountID == "INVALID_ACCOUNT_ID"):
        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text="Invalid account(banned or fortnite has not been launched).")
        return
    
    bot.delete_message(msg.chat.id, msg.message_id)
    msg = bot.send_message(message.chat.id, f"✅ Logged in account {account_data.get("displayName", "HIDDEN_ID_ACCOUNT")}")

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
    
    connected_accounts = 0
    connected_accounts_message = f"""
━━━━━━━━━━━
Connected Account
━━━━━━━━━━━\n\n"""
    
    external_auths = account_public_data.get('externalAuths', [])
    for auth in external_auths:
        auth_type = auth.get('type', '?').lower()
        display_name = auth.get('externalDisplayName', '?')
        external_id = auth.get('externalAuthId', '?')
        date_added = auth.get('dateAdded', '?')
        if date_added != '?':
            date_added = datetime.strptime(date_added, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y")

        connected_accounts += 1
        connected_accounts_message += f"""
Connection Type: {auth_type.upper()}
External Display Name: {display_name}
Date of Connection: {date_added}
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
    
    bot.send_message(message.chat.id,f'''
━━━━━━━━━━━
Activity Information
━━━━━━━━━━━

👪 Parental Control: {bool_to_emoji(account_data.get('minorVerified', False))}
🏷  Registration Date: {account_public_data.get("creation_date", "?")}
🤯 Headless: {bool_to_emoji(account_data.get("headless", False))}
✏️ Display Name Changes: {account_data.get("numberOfDisplayNameChanges", 0)}
✏️ Display Name Changeable: {bool_to_emoji(account_data.get("canUpdateDisplayName", False))}
#️⃣ Hashed email: {bool_to_emoji(account_data.get("hasHashedEmail", False))}
''')
    
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
💰 1000 Vbucks Bought: {vbucks_purchase_history["1000"]}
💰 2800 Vbucks Bought: {vbucks_purchase_history["2800"]}
💰 5000 Vbucks Bought: {vbucks_purchase_history["5000"]}
💰 7500 Vbucks Bought: {vbucks_purchase_history["7500"]}
💰 13500 Vbucks Bought: {vbucks_purchase_history["13500"]}

━━━━━━━━━━━
Gifts Information
━━━━━━━━━━━
🎁 Pending Gifts: {pending_gifts_amount}
🎁 Gifts Sent: {gift_sent}
🎁 Gifts Received: {gift_received}
''')
    
    # saved data path
    # note: it only saves the rendered images for locker, data that DOES NOT contain private or login information!!!
    save_path = f"accounts/{accountID}"
    if not os.path.exists(save_path):
       os.mkdir(save_path)

    