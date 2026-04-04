import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque

# --- КОНФИГУРАЦИЯ ---
TOKEN = ''

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

queues = {}

# --- ИНТЕРФЕЙС ---


class MusicControlView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸ Пауза/Плей", style=discord.ButtonStyle.blurple)
    async def toggle_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Пауза", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Играем", ephemeral=True)

    @discord.ui.button(label="⏭ Пропустить", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await interaction.response.send_message("⏭ Пропущено", ephemeral=True)

    @discord.ui.button(label="🚪 Выгнать", style=discord.ButtonStyle.danger)
    async def leave_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("👋 Пока!", ephemeral=True)

# --- ЛОГИКА ---


def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id in queues and queues[guild_id]:
        url2, title = queues[guild_id].popleft()

        source = discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS)
        ctx.voice_client.play(source, after=lambda e: play_next(ctx))

        embed = discord.Embed(title="🎶 Следующий трек",
                              description=title, color=discord.Color.green())
        asyncio.run_coroutine_threadsafe(
            ctx.send(embed=embed, view=MusicControlView(ctx)), bot.loop)


@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(
        title="📚 Справка по командам",
        description="Вот что я умею:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="Основные команды",
        value=(
            "`!play [название/ссылка]` — Найти и включить музыку.\n"
            "`!help` — Показать это сообщение."
        ),
        inline=False
    )
    embed.add_field(
        name="Управление плеером",
        value=(
            "**⏸ Пауза/Плей** — Остановить или продолжить трек.\n"
            "**⏭ Пропустить** — Переключить на следующую песню в очереди.\n"
            "**🚪 Выгнать** — Остановить музыку и отключить бота от канала."
        ),
        inline=False
    )
    embed.set_footer(text="Приятного прослушивания! 🎧")
    await ctx.send(embed=embed)


@bot.command(name='play')
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        return await ctx.send("Зайди в голосовой канал!")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)
                if not info or 'entries' not in info or not info['entries']:
                    return await ctx.send("❌ Ничего не найдено!")

                video_data = info['entries'][0]
                url2 = video_data['url']
                title = video_data['title']
                thumb = video_data.get('thumbnail')

            except Exception as e:
                return await ctx.send(f"❌ Ошибка YouTube: {e}")

        guild_id = ctx.guild.id
        if guild_id not in queues:
            queues[guild_id] = deque()

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            queues[guild_id].append((url2, title))
            await ctx.send(f"📝 **{title}** добавлена в очередь!")
        else:
            try:
                source = discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS)
                ctx.voice_client.play(source, after=lambda e: play_next(ctx))

                embed = discord.Embed(
                    title="🎶 Сейчас играет", description=title, color=discord.Color.blue())
                if thumb:
                    embed.set_thumbnail(url=thumb)
                await ctx.send(embed=embed, view=MusicControlView(ctx))
            except Exception as e:
                await ctx.send(f"❌ Ошибка FFmpeg: {e}")


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!help"))
    print(f'Бот {bot.user.name} онлайн!')

bot.run(TOKEN)
