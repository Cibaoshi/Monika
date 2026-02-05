import discord
from discord.ext import commands
import yt_dlp
import asyncio

# --- КОНФИГУРАЦИЯ ---
TOKEN = 'Token'

# Настройки для yt-dlp (чтобы искать и стримить аудио)
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
# Настройки для FFmpeg (чтобы соединение не разрывалось)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- НАСТРОЙКА БОТА ---
# Intents - это разрешения, которые мы включили на сайте разработчика
intents = discord.Intents.default()
intents.message_content = True

# Создаем экземпляр бота с префиксом команд "!"
bot = commands.Bot(command_prefix='!', intents=intents)

# --- СОБЫТИЯ ---


@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} запущен и готов к работе!')

# --- КОМАНДЫ ---

# 1. Команда !play (ссылка)


@bot.command(name='play', help='Играет музыку с YouTube')
async def play(ctx, url):
    # Проверяем, находится ли пользователь в голосовом канале
    if not ctx.message.author.voice:
        await ctx.send("Зайди сначала в голосовой канал!")
        return

    # Подключаемся к каналу пользователя
    channel = ctx.message.author.voice.channel
    voice_client = ctx.voice_client

    if voice_client is None:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)

    # Ищем и извлекаем прямую ссылку на аудио
    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                # Если это плейлист или поиск, берем первый результат
                if 'entries' in info:
                    url2 = info['entries'][0]['url']
                    title = info['entries'][0]['title']
                else:
                    url2 = info['url']
                    title = info['title']

                # Запускаем воспроизведение через FFmpeg
                voice_client.stop()  # Остановить текущее, если играет
                voice_client.play(
                    discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS))
                await ctx.send(f'🎶 Играет: **{title}**')

            except Exception as e:
                await ctx.send(f"Ошибка при воспроизведении: {e}")

# 2. Команда !stop


@bot.command(name='stop', help='Останавливает музыку')
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("Музыка остановлена.")

# 3. Команда !leave


@bot.command(name='leave', help='Бот покидает канал')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Бот отключился.")

# Запуск бота
bot.run(TOKEN)
