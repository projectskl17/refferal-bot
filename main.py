import telebot
from telebot import types
from database import Database
from config import CHANNEL_IDS, OWNER_ID, BOT_TOKEN, MONGODB_URL, ADMIN_IDS
from typing import Dict, Optional

bot = telebot.TeleBot(BOT_TOKEN)
db = Database(MONGODB_URL)

invite_links_cache: Dict[int, str] = {}

def get_channel_invite_link(channel_id: int) -> Optional[str]:
    """Get cached invite link or generate new one"""
    if channel_id in invite_links_cache:
        return invite_links_cache[channel_id]
    
    try:
        invite_link = bot.create_chat_invite_link(channel_id).invite_link
        invite_links_cache[channel_id] = invite_link
        return invite_link
    except Exception as e:
        print(f"Error getting invite link for channel {channel_id}: {e}")
        return None

def check(user_id: int) -> bool:
    """Check if user is member of all channels"""
    for channel_id in CHANNEL_IDS:
        try:
            check = bot.get_chat_member(channel_id, user_id)
            if check.status == 'left':
                return False
        except Exception as e:
            print(f"Error checking membership for channel {channel_id}: {e}")
            return False
    return True

def menu(id):
    if not check(id):
        send_join_channels_message(id)
        return
    
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row('🙌🏻 Referrals', '🆔 Account')
    bot.send_message(id, "*🏡 Home*", parse_mode="Markdown", reply_markup=keyboard)

def send_join_channels_message(user_id: int):
    """Send message with channel join buttons"""
    markup = telebot.types.InlineKeyboardMarkup()
    for channel_id in CHANNEL_IDS:
        try:
            channel_info = bot.get_chat(channel_id)
            channel_name = channel_info.title
            invite_link = get_channel_invite_link(channel_id)
            if invite_link:
                markup.add(
                    telebot.types.InlineKeyboardButton(
                        text=f'Join {channel_name}',
                        url=invite_link
                    )
                )
        except Exception as e:
            print(f"Error getting channel info for {channel_id}: {e}")
            continue
    
    markup.add(
        telebot.types.InlineKeyboardButton(
            text='Joined ✅,
            callback_data='check'
        )
    )
    
    msg_start = "*🔔 Please join our channels to use this bot:*"
    bot.send_message(user_id, msg_start, parse_mode="Markdown", reply_markup=markup)

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
            
            send_join_channels_message(user_id)
            
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
                    text='❌ You have not joined all channels'
                )
                bot.delete_message(call.message.chat.id, call.message.message_id)
                send_join_channels_message(call.message.chat.id)

    except Exception as e:
        print(f"Error in query handler: {e}")
        bot.send_message(call.message.chat.id, "This command is having an error. Please wait for the admin to fix it.")
        bot.send_message(OWNER_ID, f"Your bot encountered an error: {e}")

@bot.message_handler(content_types=['text'])
def send_text(message):
    try:
        if not check(message.chat.id):
            send_join_channels_message(message.chat.id)
            return
            
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
