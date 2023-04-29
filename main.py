import asyncio
from io import BytesIO
import os
import disnake
from dotenv import load_dotenv
from googletrans import Translator
from tinydb import TinyDB, Query, where
from disnake.ext import commands
import telegram_bot

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

db = TinyDB("db.json")

discord_bot = commands.Bot(
    command_prefix="$", sync_commands=True
)


@discord_bot.slash_command(description="unattach")
async def unattach(
    inter: disnake.ApplicationCommandInteraction,
    discord_channel: disnake.TextChannel
):
    await inter.response.defer()
    try:
        channels_table = db.table("discord_channels")
        channels_table.remove(where('discord_channel_id')
                              == str(discord_channel.id))
        await inter.edit_original_message(content="Deleted successfully")
    except Exception as ex:
        print(ex)
        await inter.edit_original_message(content="Could not find channel. Verify that ID is correct")


@discord_bot.slash_command(description="Attach channels")
async def attach(
    inter: disnake.ApplicationCommandInteraction,
    discord_channel: disnake.TextChannel,
):
    query = Query()
    await inter.response.defer()
    if not guild.get_member(inter.author.id).member.permissions.administrator:
        await inter.edit_original_message(content="You can't do that")
        return

    discord_channel_id = str(discord_channel.id)
    channels_table = db.table("discord_channels")
    channels_table.upsert(
        {
            "discord_channel_id": discord_channel_id,
            "discord_channel_title": discord_channel.name,
        },
        query.discord_channel_id == discord_channel_id,
    )
    await inter.edit_original_message(content=f"{discord_channel.name} has been attached")


@discord_bot.event
async def on_message(message: disnake.Message):
    discord_channels = [r for r in db.table('discord_channels')]
    for channels in discord_channels:
        if channels['discord_channel_id'] == str(message.channel.id):
            telegram_bot.send_message(message, str(message.channel.id))


if __name__ == '__main__':
    print('Discord ON')
    loop = asyncio.get_event_loop()
    loop.create_task(telegram_bot.start_telegram_bot())
    loop.create_task(
        discord_bot.run(DISCORD_TOKEN)
    )
    loop.run_forever()
