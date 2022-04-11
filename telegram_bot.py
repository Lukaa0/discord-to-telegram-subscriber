from datetime import datetime
from email.mime import base
import os
import disnake
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import telegram
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import more_itertools as mit
from tinydb import TinyDB, Query, where
from googletrans import Translator
import languages
import logging
import traceback

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

logging.basicConfig(filename='logs.log', filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s')

db = TinyDB("db.json")
updater = Updater(TELEGRAM_TOKEN)
channel_prefix = 'ch_'
language_prefix = 'lan_'
translator = Translator()


def start(update: Update, context: CallbackContext) -> None:
    if(update.message.chat_id == update.message.from_user.id):
        menu = [
            [
                InlineKeyboardButton(
                    "Select channels", callback_data='select_channels'),
                InlineKeyboardButton("Select a language",
                                     callback_data='select_language'),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(menu)

        update.message.reply_text(
            'Select an action:', reply_markup=reply_markup)


def channels(update: Update, context: CallbackContext) -> None:
    discord_channels = [r for r in db.table('discord_channels')]
    user_channels = [r for r in db.table('users')]
    keyboard = []
    buttons = []
    for channel in discord_channels:
        btn_title = channel["discord_channel_title"]
        for user_channel in user_channels:
            if user_channel['user_id'] == update.effective_user.id and user_channel['channel_id'] == channel['discord_channel_id']:
                btn_title = f"✓{btn_title}"
                break
        buttons.append(InlineKeyboardButton(
            btn_title, callback_data=f"{channel_prefix}{channel['discord_channel_id']}"))

    keyboard = list(mit.chunked(buttons, 3))
    keyboard.append([InlineKeyboardButton(
        "Done", callback_data=f"{channel_prefix}200")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(
        'Select channels:', reply_markup=reply_markup)


def language(update: Update, context: CallbackContext) -> None:
    buttons = []
    for key, value in languages.LANGUAGES.items():
        buttons.append(InlineKeyboardButton(
            value, callback_data=f"{language_prefix}{key}"))
    keyboard = []

    keyboard = list(mit.chunked(buttons, 2))

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.callback_query.edit_message_text(
        'Choose a language:', reply_markup=reply_markup)


def language_callback(update: Update, context: CallbackContext) -> None:
    query = Query()
    callback = update.callback_query
    user_languages = db.table("user_languages")
    user_languages.upsert({
        "user_id": update.callback_query.from_user.id,
        "language_name": callback.data.removeprefix(language_prefix)
    }, query.user_id == update.callback_query.from_user.id)

    callback.answer()
    callback.edit_message_text('Language configured.')


def start_callback(update: Update, context: CallbackContext) -> None:
    query = Query()
    callback = update.callback_query
    users = db.table("users")
    if(callback.data == f"{channel_prefix}200"):
        for container in update.callback_query.message.reply_markup.inline_keyboard:
            for btn in container:
                channel_id = btn.callback_data.removeprefix(channel_prefix)
                if '✓' in btn.text:
                    users.upsert(
                        {
                            "user_id": update.callback_query.from_user.id,
                            "channel_id": channel_id,
                        },
                        (where('channel_id') == channel_id) & (
                            where('user_id') == update.callback_query.from_user.id),
                    )
                elif btn.text != "Done":
                    users.remove((where('channel_id') == channel_id) & (
                        where('user_id') == update.callback_query.from_user.id))

        callback.answer()

        callback.edit_message_text('Channels added.')
        return

    for container in update.callback_query.message.reply_markup.inline_keyboard:
        for btn in container:
            if btn.callback_data == callback.data:
                btn.text = btn.text.replace(
                    '✓', '') if '✓' in btn.text else f"✓{btn.text}"
    callback.answer()

    callback.edit_message_text(
        'Please choose', reply_markup=update.callback_query.message.reply_markup)


def base_callback(update: Update, context: CallbackContext) -> None:
    callback = update.callback_query.data
    if callback.startswith(channel_prefix):
        start_callback(update, context)
    elif callback.startswith(language_prefix):
        language_callback(update, context)
    elif callback == "select_channels":
        channels(update, context)
    elif callback == "select_language":
        language(update, context)


def help_command(update: Update, context: CallbackContext) -> None:

    update.message.reply_text(
        "Use /start select channels that you want to subscribe.")


def add_handlers():
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(base_callback))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))


def send_message(message: disnake.Message, discord_channel_id):
    users = [r for r in db.table('users')]
    user_languages = db.table('user_languages')
    for user in users:
        try:
            if(user['channel_id'] == discord_channel_id):
                if(len(message.embeds) > 0):
                    description = message.embeds[0].description
                    image = message.embeds[0].image.url
                else:
                    description = message.content
                    image = message.attachments[0].url if len(
                        message.attachments) > 0 else None

                result = user_languages.get(
                    Query()['user_id'] == user['user_id'])
                language_code = "en" if result is None else result['language_name']
                translated_content = translator.translate(
                    description, src="en", dest=language_code).text
                content = f'''
{message.channel.name}
---------------
{translated_content}'''
                updater.bot.send_message(
                    chat_id=user['user_id'], text=content)
                if image is not disnake.Embed.Empty or image is not None:
                    updater.bot.send_photo(
                        user['user_id'], image)

        except Exception as ex:
            logging.error('something failed: %s' % str(ex))
            formatted_lines = traceback.format_exc().splitlines()
            logging.error('; '.join(formatted_lines))
            continue


async def start_telegram_bot():
    print('Telegram ON')
    add_handlers()
    updater.start_polling()
if __name__ == '__main__':
    x = 5
