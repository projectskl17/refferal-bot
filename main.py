import telebot
from telebot import types
from database import Database
from config import CHANNELS, OWNER_ID, BOT_TOKEN, MONGODB_URL, ADMIN_IDS

bot = telebot.TeleBot(BOT_TOKEN)
db = Database(MONGODB_URL)

def check(id):
    for i in CHANNELS:
        check = bot.get_chat_member(i, id)
        if check.status == 'left':
            return False
    return True

def menu(id):
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row('🙌🏻 Referrals', '🆔 Account')
    bot.send_message(id, "*🏡 Home*", parse_mode="Markdown", reply_markup=keyboard)

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.chat.id
        msg = message.text
        first_name = message.from_user.first_name or "User"
        username = f"@{message.from_user.username}" if message.from_user.username else "No username"
        existing_user = db.get_user(str(user_id))

        if existing_user:
            menu(user_id)
        else:
            if msg == '/start':
                db.create_user(str(user_id), first_name=first_name, username=username)
            else:
                referrer_id = message.text.split()[1]
                db.create_user(str(user_id), referrer_id, first_name=first_name, username=username)
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                text='🤼‍♂️ Joined',
                callback_data='check'
            ))
            msg_start = "*🔔 To Use This Bot You Need To Join This Channel:*"
            for i in CHANNELS:
                msg_start += f"\n➡️ {i}"
            bot.send_message(user_id, msg_start, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        print(f"Error in start: {e}")
        bot.send_message(user_id, "This command is having an error. Please wait for the admin to fix it.")
        bot.send_message(OWNER_ID, f"Your bot encountered an error: {e}")

@bot.message_handler(commands=['info'])
def info_command(message):
    try:
        if message.from_user.id != OWNER_ID and message.from_user.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, "❌ You do not have permission to access this command.")
            return

        referred_users = db.get_users_with_referrals()
        if not referred_users:
            bot.send_message(message.chat.id, "*📊 No users have referred anyone yet!*", parse_mode="Markdown")
            return

        msg = "*📊 Users with Referrals:*\n"
        for i, user in enumerate(referred_users, 1):
            referrer = user.get('username', 'Unknown User')
            referred_usernames = db.get_referred_usernames(user['_id'])
            referred_list = ", ".join(referred_usernames) if referred_usernames else "None"
            msg += (
                f"{i}. Referrer: {referrer} | Referrals: {user['referred_users']} | Referred Users: {referred_list}\n"
            )
        msg += f"\n*Total Referring Users: {len(referred_users)}*"

        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in info command: {e}")

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    try:
        if call.data == 'check':
            if check(call.message.chat.id):
                user_id = str(call.message.chat.id)
                user = db.get_user(user_id)
                
                if user and not user.get('refer_claimed', False):
                    referrer_id = user['referrer']
                    if referrer_id != user_id:
                        if db.claim_referral_bonus(user_id, referrer_id):
                            bot.send_message(
                                referrer_id,
                                "*🏧 New Referral Added!*",
                                parse_mode="Markdown"
                            )

                bot.answer_callback_query(
                    callback_query_id=call.id,
                    text='✅ You joined Successfully'
                )
                bot.delete_message(call.message.chat.id, call.message.message_id)
                menu(call.message.chat.id)
            else:
                bot.answer_callback_query(
                    callback_query_id=call.id,
                    text='❌ You have not Joined'
                )
                bot.delete_message(call.message.chat.id, call.message.message_id)
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(text='🤼‍♂️ Joined', callback_data='check'))
                msg_start = "*🔔 To Use This Bot You Need To Join This Channel:*"
                for i in CHANNELS:
                    msg_start += f"\n➡️ {i}"
                bot.send_message(call.message.chat.id, msg_start, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        print(f"Error in query handler: {e}")
        bot.send_message(call.message.chat.id, "This command is having an error. Please wait for the admin to fix it.")
        bot.send_message(OWNER_ID, f"Your bot encountered an error: {e}")

@bot.message_handler(content_types=['text'])
def send_text(message):
    try:
        if message.text == '🆔 Account':
            user = str(message.chat.id)
            level_info = db.get_user_level_info(user)
            
            if level_info:
                msg = (
                    f"*👤 User: {message.from_user.first_name}*\n\n"
                    f"*📊 Level: {level_info['current_level']}*\n"
                    f"*👥 Total Referrals: {level_info['referral_count']}*\n\n"
                    f"*📈 Progress to Level {level_info['next_level']}:*\n"
                    f"*Need {level_info['referrals_needed']} more referrals*"
                )
            else:
                msg = "*👤 User information not found*"
            
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        
        elif message.text == '🙌🏻 Referrals':
            user = str(message.chat.id)
            level_info = db.get_user_level_info(user)
            bot_name = bot.get_me().username
            ref_link = f'https://telegram.me/{bot_name}?start={message.chat.id}'
            
            if level_info:
                share_keyboard = telebot.types.InlineKeyboardMarkup()
                share_button = telebot.types.InlineKeyboardButton(
                    "Share Referral Link", 
                    url=f"https://telegram.me/share/url?url={ref_link}"
                )
                share_keyboard.add(share_button)
                
                msg = (
                    f"*📊 Your Referral Stats:*\n\n"
                    f"*Level: {level_info['current_level']}*\n"
                    f"*Total Referrals: {level_info['referral_count']}*\n"
                    f"*Referrals for Next Level: {level_info['referrals_needed']}*\n\n"
                    f"*🔗 Your Referral Link ⬇️*\n"
                    f"`{ref_link}`"
                )
                
                bot.send_message(
                    message.chat.id, 
                    msg, 
                    parse_mode="Markdown", 
                    reply_markup=share_keyboard
                )
            else:
                msg = "*❌ Error fetching referral information*"
                bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        
    except Exception as e:
        bot.send_message(message.chat.id, "This command is having an error. Please wait for the admin to fix the glitch.")
        bot.send_message(OWNER_ID, f"Your bot got an error. Fix it fast!\nError on command: {message.text}")


if __name__ == '__main__':
    bot.polling(none_stop=True)