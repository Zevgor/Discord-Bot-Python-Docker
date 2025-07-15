# bot.py
import os, random, discord, requests, base64, asyncio, yt_dlp

import utilities

from dotenv import load_dotenv
load_dotenv()

from discord.utils import get
from discord.ext import commands
# currently importing all intents - clean this up later
bot = commands.Bot(command_prefix='.',intents=discord.Intents.all())

#ffmped recconect opts
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

sessions = []

ALLOWED_CHANNEL_IDS = os.getenv('DISCORD_CHANNELS')

# yt_dlp get audio stream
# pass URL and search true/false
def get_audio_stream(query_or_url, search=True):
    if search and not query_or_url.startswith(('http://', 'https://')):
        query_or_url = f"ytsearch1:{query_or_url}"  # Get only the first result

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplatlist': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query_or_url, download=False)
            if 'entries' in info:
                info = info['entries'][0]  # First result from search or playlist
            return {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'stream_url': info.get('url'),
                'webpage_url': info.get('webpage_url'),
                'id': info.get('id'),
                'ext': info.get('ext'),
                'thumb': info.get('thumbnail'),
            }
    except Exception:
        print("YTDLP ERROR!")
        return None

# on ready / load
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.check
async def is_in_allowed_channel(ctx):
        return ctx.channel.name in ALLOWED_CHANNEL_IDS

@bot.event
async def on_command_error(ctx, error):
    # if isinstance(error, commands.CheckFailure):
        # await ctx.send("� This command can only be used in the designated channel.")
    # else:
        # raise error  # Let other errors bubble through
    return

# bilzzard API wow token price
@bot.command(name='wt', help='Retrieves live WoW Token price.')
async def wow_token(ctx):
    def get_battlenet_oauth_token(client_id, client_secret, region='us'):
        auth_string = f"{client_id}:{client_secret}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        try:
            response = requests.post(f"https://{region}.battle.net/oauth/token", headers=headers, data=data)
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving token: {e}")
            return None
    
    access_token = get_battlenet_oauth_token(os.getenv('BATTLENET_CLIENT'), os.getenv('BATTLENET_SECRET'))

    blizz_response = requests.get(
        'https://us.api.blizzard.com/data/wow/token/?namespace=dynamic-us',headers={'Authorization':'Bearer '+access_token}
    )

    await ctx.send('Current WoW Token Price (US): ' + str(blizz_response.json().get('price'))[:-4])

# import here

def check_session(ctx):
    """
    Checks if there is a session with the same characteristics (guild and channel) as ctx param.

    :param ctx: discord.ext.commands.Context

    :return: session()
    """
    if len(sessions) > 0:
        for i in sessions:
            if i.guild == ctx.guild and i.channel == ctx.author.voice.channel:
                return i
        session = utilities.Session(
            ctx.guild, ctx.author.voice.channel, id=len(sessions))
        sessions.append(session)
        return session
    else:
        session = utilities.Session(ctx.guild, ctx.author.voice.channel, id=0)
        sessions.append(session)
        return session


def prepare_continue_queue(ctx):
    """
    Used to call next song in queue.

    Because lambda functions cannot call async functions, I found this workaround in discord's api documentation
    to let me continue playing the queue when the current song ends.

    :param ctx: discord.ext.commands.Context
    :return: None
    """
    fut = asyncio.run_coroutine_threadsafe(continue_queue(ctx), bot.loop)
    try:
        fut.result()
    except Exception as e:
        print(e)


async def continue_queue(ctx):
    """
    Check if there is a next in queue then proceeds to play the next song in queue.

    As you can see, in this method we create a recursive loop using the prepare_continue_queue to make sure we pass
    through all songs in queue without any mistakes or interaction.

    :param ctx: discord.ext.commands.Context
    :return: None
    """
    session = check_session(ctx)
    if not session.q.theres_next():
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        await voice.disconnect()
        await ctx.send("End of the queue.")
        return

    session.q.next()

    voice = discord.utils.get(bot.voice_clients, guild=session.guild)
    source = await discord.FFmpegOpusAudio.from_probe(session.q.current_music.url, **FFMPEG_OPTIONS)

    if voice.is_playing():
        voice.stop()

    voice.play(source, after=lambda e: prepare_continue_queue(ctx))
    await ctx.send(session.q.current_music.thumb)
    await ctx.send(f"Now Playing: {session.q.current_music.title}")


@bot.command(name='play')
async def play(ctx, *, arg):
    """
    Checks where the command's author is, searches for the music required, joins the same channel as the command's
    author and then plays the audio directly from YouTube.

    :param ctx: discord.ext.commands.Context
    :param arg: str
        arg can be url to video on YouTube or just as you would search it normally.
    :return: None
    """
    try:
        voice_channel = ctx.author.voice.channel

    # If command's author isn't connected, return.
    except AttributeError as e:
        print(e)
        await ctx.send("You must be in a voice channel to play music.")
        return

    # Finds author's session.
    session = check_session(ctx)

    if arg.startswith(('http://', 'https://')) and ('list' in arg):
        await ctx.send("Sorry, I can't play playlists.")
        return
    else:
        # Searches for the video
        streaminfo = get_audio_stream(arg)

    url = streaminfo['stream_url']
    title = streaminfo['title']
    thumb = streaminfo['thumb']

    session.q.enqueue(title, url, thumb)

    # Finds an available voice client for the bot.
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice:
        await voice_channel.connect()
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    # If it is already playing something, adds to the queue
    if voice.is_playing():
        await ctx.send(thumb)
        await ctx.send(f"Added to Queue: {title}")
        return
    else:
        await ctx.send(thumb)
        await ctx.send(f"Now Playing: {title}")

        # Guarantees that the requested music is the current music.
        session.q.set_last_as_current()

        source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
        voice.play(source, after=lambda ee: prepare_continue_queue(ctx))


@bot.command(name='next', aliases=['skip'])
async def skip(ctx):
    """
    Skips the current song, playing the next one in queue if there is one.

    :param ctx: discord.ext.commands.Context
    :return: None
    """
    # Finds author's session.
    session = check_session(ctx)
    # If there isn't any song to be played next, return.
    if not session.q.theres_next():
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        voice.stop()        
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        await voice.disconnect()        
        return

    # Finds an available voice client for the bot.
    voice = discord.utils.get(bot.voice_clients, guild=session.guild)

    # If it is playing something, stops it. This works because of the "after" argument when calling voice.play as it is
    # a recursive loop and the current song is already going to play the next song when it stops.
    if voice.is_playing():
        voice.stop()
        return
    else:
        # If nothing is playing, finds the next song and starts playing it.
        session.q.next()
        source = await discord.FFmpegOpusAudio.from_probe(session.q.current_music.url, **FFMPEG_OPTIONS)
        voice.play(source, after=lambda e: prepare_continue_queue(ctx))
        return


@bot.command(name='queue', aliases=['q'])
async def queue_info(ctx):
    """
    A debug command to find session id, what is current playing and what is on the queue.
    :param ctx: discord.ext.commands.Context
    :return: None
    """
    session = check_session(ctx)
    # await ctx.send(f"Session ID: {session.id}")
    await ctx.send(f"Now Playing: {session.q.current_music.title}")
    queue = [q[0] for q in session.q.queue]
    await ctx.send(f"Queue: {queue}")

@bot.command(name='leave')
async def leave(ctx):
    """
    If bot is connected to a voice channel, it leaves it.

    :param ctx: discord.ext.commands.Context
    :return: None
    """
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_connected:
        check_session(ctx).q.clear_queue()
        await voice.disconnect()
    else:
        await ctx.send("Bot is not connected.")


@bot.command(name='pause')
async def pause(ctx):
    """
    If playing audio, pause it.

    :param ctx: discord.ext.commands.Context
    :return: None
    """
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
    else:
        await ctx.send("Already paused.")


@bot.command(name='resume')
async def resume(ctx):
    """
    If audio is paused, resumes playing it.

    :param ctx: discord.ext.commands.Context
    :return: None
    """
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_paused:
        voice.resume()
    else:
        await ctx.send("Already playing.")


@bot.command(name='stop')
async def stop(ctx):
    """
    Stops playing audio and clears the session's queue.

    :param ctx: discord.ext.commands.Context
    :return: None
    """
    session = check_session(ctx)
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing:
        voice.stop()
        session.q.clear_queue()
    else:
        await ctx.send("Already stopped.")

# end important

# run bot
bot.run(os.getenv('DISCORD_TOKEN'))