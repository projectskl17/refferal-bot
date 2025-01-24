import time
import telebot
from telebot import types
from database import Database
from datetime import datetime
import random
from config import TOKEN, CHANNELS, PAYMENT_CHANNEL, OWNER_ID, BOT_TOKEN, DAILY_BONUS, MINI_WITHDRAW, PER_REFER, REQUEST_CHANNELS, JOIN_REQUEST

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

class JoinRequestCache:
    def __init__(self):
        self.invite_links = {}
        self.last_update = None

    def update_links(self, bot):
        current_time = time.time()
        if self.last_update and current_time - self.last_update < 6600:
            return
        
        for channel in REQUEST_CHANNELS:
            try:
                if JOIN_REQUEST:
                    link = bot.create_chat_invite_link(
                        channel,
                        creates_join_request=True
                    ).invite_link
                else:
                    link = bot.create_chat_invite_link(
                        channel
                    ).invite_link
                self.invite_links[channel] = link
            except Exception as e:
                print(f"Error creating invite link for {channel}: {e}")
        
        self.last_update = current_time

join_cache = JoinRequestCache()

def check(id):
    for i in CHANNELS:
        check = bot.get_chat_member(i, id)
        if check.status != 'left':
            pass
        else:
            return False
    return True

def menu(id):
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row('🆔 Account')
    keyboard.row('🙌🏻 Referrals', '🎁 Bonus', '💸 Withdraw')
    keyboard.row('⚙️ Set Wallet')
    bot.send_message(id, "*🏡 Home*", parse_mode="Markdown", reply_markup=keyboard)

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user = message.chat.id
        msg = message.text
        existing_user = db.get_user(str(user))

        if existing_user:
            menu(user)
        else:
            if msg == '/start':
                db.create_user(str(user))
            else:
                refid = message.text.split()[1]
                db.create_user(str(user), refid)
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                text='🤼‍♂️ Joined',
                callback_data='check'
            ))
            msg_start = "*🍔 To Use This Bot You Need To Join This Channel - "
            for i in CHANNELS:
                msg_start += f"\n➡️ {i}\n"
            msg_start += "*"
            bot.send_message(str(user), msg_start, parse_mode="Markdown", reply_markup=markup)
        
    except Exception as e:
        print(f"Error in start: {e}")
        bot.send_message(message.chat.id, "This command is having an error. Please wait for the admin to fix it.")
        bot.send_message(OWNER_ID, "Your bot got an error, fix it fast!\n Error on command: "+message.text)


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    try:
        if call.data.startswith('bonus_'):
            channel = call.data.split('_')[1]
            user_id = str(call.message.chat.id)
            
            if JOIN_REQUEST:
                member = bot.get_chat_member(channel, user_id)
                if not db.check_join_request(user_id, channel) and member.status == 'left':
                    bot.answer_callback_query(
                        call.id,
                        "❌ Please send join request first!",
                        show_alert=True
                    )
                    return
            else:
                
                member = bot.get_chat_member(channel, user_id)
                if member.status == 'left':
                    bot.answer_callback_query(
                        call.id,
                        "❌ Please join the channel first!",
                        show_alert=True
                    )
                    return

            db.update_balance(user_id, DAILY_BONUS)
            db.update_bonus_time(user_id)
            
            bot.answer_callback_query(
                call.id,
                f"✅ Bonus of {DAILY_BONUS} {TOKEN} has been credited!",
                show_alert=True
            )
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return
            
        elif call.data == 'check':
            ch = check(call.message.chat.id)
            if ch == True:
                user_id = str(call.message.chat.id)
                user = db.users.find_one({'_id': user_id})
                
                if user and not user.get('refer_claimed', False):
                    referrer_id = user['referrer']
                    if referrer_id != user_id:
                        if db.claim_referral_bonus(user_id, referrer_id):
                            bot.send_message(
                                referrer_id,
                                f"*🏧 New Referral on Level 1, You Got : +{PER_REFER} {TOKEN}*",
                                parse_mode="Markdown"
                            )

                bot.answer_callback_query(
                    callback_query_id=call.id,
                    text='✅ You joined Now you can earn money'
                )
                bot.delete_message(call.message.chat.id, call.message.message_id)
                menu(call.message.chat.id)
            else:
                bot.answer_callback_query(
                    callback_query_id=call.id,
                    text='❌ You not Joined'
                )
                bot.delete_message(call.message.chat.id, call.message.message_id)
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(text='🤼‍♂️ Joined', callback_data='check'))
                msg_start = "*🍔 To Use This Bot You Need To Join This Channel - "
                for i in CHANNELS:
                    msg_start += f"\n➡️ {i}\n"
                msg_start += "*"
                bot.send_message(call.message.chat.id, msg_start, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        print(e)
        bot.send_message(call.message.chat.id, "This command having error pls wait for fixing the glitch by admin")
        bot.send_message(OWNER_ID, "Your bot got an error fix it fast!\n Error on command: "+call.data)

@bot.message_handler(content_types=['text'])
def send_text(message):
    try:
        if message.text == '🆔 Account':
            user = str(message.chat.id)
            balance = db.get_balance(user)
            wallet = db.get_wallet(user)
            msg = f'*👮 User : {message.from_user.first_name}\n\n⚙️ Wallet : *`{wallet}`*\n\n💸 Balance : *`{balance}`* {TOKEN}*'
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")

        elif message.text == '🙌🏻 Referrals':
            user = str(message.chat.id)
            ref_count = db.get_referral_count(user)
            bot_name = bot.get_me().username
            ref_link = f'https://telegram.me/{bot_name}?start={message.chat.id}'
            msg = f"*⏯️ Total Invites : {ref_count} Users\n\n👥 Refferrals System\n\n1 Level:\n🥇 Level°1 - {PER_REFER} {TOKEN}\n\n🔗 Referral Link ⬇️\n{ref_link}*"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")

        elif message.text == "⚙️ Set Wallet":
            keyboard = telebot.types.ReplyKeyboardMarkup(True)
            keyboard.row('🚫 Cancel')
            send = bot.send_message(message.chat.id, "_⚠️Send your TON Wallet Address._", parse_mode="Markdown", reply_markup=keyboard)
            bot.register_next_step_handler(message, trx_address)

        elif message.text == "🎁 Bonus":
            user = str(message.chat.id)
            if not db.can_claim_bonus(user):
                bot.send_message(
                    message.chat.id,
                    "❌*You can only take bonus once every 24 hours!*",
                    parse_mode="markdown"
                )
                return

            join_cache.update_links(bot)
            channel = random.choice(REQUEST_CHANNELS)
            invite_link = join_cache.invite_links.get(channel)

            if not invite_link:
                bot.send_message(
                    message.chat.id,
                    "❌ Failed to generate invite link. Please try again later.",
                    parse_mode="markdown"
                )
                return

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Join Channel", url=invite_link))
            markup.add(types.InlineKeyboardButton("✅ Check Join", callback_data=f'bonus_{channel}'))

            bot.send_message(
                message.chat.id,
                f"*🎁 To claim your bonus of {DAILY_BONUS} {TOKEN}, please join our channel:*",
                parse_mode="markdown",
                reply_markup=markup
            )

        elif message.text == "📊Statistics":
            stats = db.get_stats()
            msg = f"*📊 Total members : {stats['total_users']} Users\n\n🥊 Total successful Withdraw : {stats['total_withdrawals']} {TOKEN}*"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")

        elif message.text == "💸 Withdraw":
            user = str(message.chat.id)
            balance = db.get_balance(user)
            wallet = db.get_wallet(user)

            if wallet == "none":
                bot.send_message(message.chat.id, "_❌ wallet Not set_", parse_mode="Markdown")
                return

            if balance >= MINI_WITHDRAW:
                bot.send_message(message.chat.id, "_Enter Your Amount_", parse_mode="Markdown")
                bot.register_next_step_handler(message, amo_with)
            else:
                bot.send_message(message.chat.id, f"_❌Your balance low you should have at least {MINI_WITHDRAW} {TOKEN} to Withdraw_", parse_mode="Markdown")

    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "This command having error pls wait for fixing the glitch by admin")
        bot.send_message(OWNER_ID, "Your bot got an error fix it fast!\n Error on command: "+message.text)

def trx_address(message):
    try:
        if message.text == "🚫 Cancel":
            return menu(message.chat.id)
        if len(message.text) == 48:
            user = str(message.chat.id)
            db.update_wallet(user, message.text)
            bot.send_message(message.chat.id, "*💹Your TON wallet set to " + message.text + "*", parse_mode="Markdown")
            return menu(message.chat.id)
        else:
            bot.send_message(message.chat.id, "*⚠️ It's Not a Valid TON Address!*", parse_mode="Markdown")
            return menu(message.chat.id)
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "This command having error pls wait for fixing the glitch by admin")
        bot.send_message(OWNER_ID, "Your bot got an error fix it fast!\n Error on command: "+message.text)

def amo_with(message):
    try:
        user = str(message.chat.id)
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "_📛 Invalid value. Enter only numeric value. Try again_", parse_mode="Markdown")
            return

        amount = int(message.text)
        if amount < MINI_WITHDRAW:
            bot.send_message(message.chat.id, f"_❌ Minimum withdraw {MINI_WITHDRAW} {TOKEN}_", parse_mode="Markdown")
            return

        balance = db.get_balance(user)
        if amount > balance:
            bot.send_message(message.chat.id, "_❌ You Can't withdraw More than Your Balance_", parse_mode="Markdown")
            return

        if db.process_withdrawal(user, amount):
            wallet = db.get_wallet(user)
            bot_name = bot.get_me().username
            bot.send_message(message.chat.id, "✅* Withdraw is request to our owner automatically\n\n💹 Payment Channel :- "+PAYMENT_CHANNEL +"*", parse_mode="Markdown")

            ref_count = db.get_referral_count(user)
            username = message.from_user.username
            masked_username = username[:len(username)//2] + "*" * (len(username) - len(username)//2)
            half_length = len(wallet) // 2
            wallet = wallet[:10] + "*" * 10 if len(wallet) >= 10 else wallet[:len(wallet)//2] + "*" * (len(wallet) - len(wallet)//2)
            markupp = telebot.types.InlineKeyboardMarkup()
            markupp.add(telebot.types.InlineKeyboardButton(text='🍀 BOT LINK', url=f'https://telegram.me/{bot_name}?start={OWNER_ID}'))
            send = bot.send_message(
                PAYMENT_CHANNEL,
                f"✅ New Withdraw\n\n⭐ Amount - {amount} {TOKEN}\n🦁 User - {masked_username}\n💠 Wallet - `{wallet}...`\n☎️ User Referrals = {ref_count}\n\n🏖 Bot Link - @{bot_name}\n⏩ Status: PENDING",
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=markupp
                )

    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "This command having error pls wait for fixing the glitch by admin")
        bot.send_message(OWNER_ID, "Your bot got an error fix it fast!\n Error on command: "+message.text)

@bot.chat_join_request_handler()
def handle_join_request(update):
    try:
        user_id = str(update.from_user.id)
        channel_id = update.chat.id
        db.save_join_request(user_id, channel_id)
    except Exception as e:
        print(f"Error handling join request: {e}")

if __name__ == '__main__':
    bot.polling(none_stop=True)