from discord.ext import commands
from gtts import gTTS
from googletrans import Translator
from dotenv import load_dotenv
import discord
import os
import subprocess
import re
import asyncio

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
AMIGO_ID = int(os.getenv('AMIGO_ID'))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Fila para armazenar as mensagens
message_queue = []

# Flags para controle de estado
processing_message = False
current_voice_client = None
language_mode = {}
translator = Translator()

abreviacoes = {
    "vc": "você",
    "dnv": "de novo",
    "pq": "porque",
    "poh": "pô",
    "tbm": "também",
    "si": "sim",
    "mds": "meu Deus",
    "oq": "o que",
    "cll": "celular",
    "vcs": "vocês",
    "pera": "pêra",
    "nd": "nada",
    "hj": "hoje",
    "aq": "aqui",
    "cd": "cadê",
    "rlx": "relaxa",
    "vdd": "verdade",
    "bjs": "beijos",
    "mao": "mão",
    "nd": "nada",
}

def remove_emojis(text):
    emoji_pattern = re.compile(
        "["  
        "\U0001F600-\U0001F64F"  
        "\U0001F300-\U0001F5FF"  
        "\U0001F680-\U0001F6FF"  
        "\U0001F700-\U0001F77F"  
        "\U0001F780-\U0001F7FF"  
        "\U0001F800-\U0001F8FF"  
        "\U0001F900-\U0001F9FF"  
        "\U0001FA00-\U0001FA6F"  
        "\U0001FA70-\U0001FAFF"  
        "\U00002702-\U000027B0"  
        "\U000024C2-\U0001F251"
        "]", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

def substituir_abreviacoes(text):
    palavras = text.split()
    palavras_substituidas = [abreviacoes.get(palavra.lower(), palavra) for palavra in palavras]
    return ' '.join(palavras_substituidas)

def clean_text(text):
    # Mantém acentos e caracteres especiais e remove apenas caracteres indesejados
    text = re.sub(r'[^\w\s,.?!áéíóúãõâêîôûãç]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def process_message_queue():
    global processing_message, current_voice_client

    while message_queue:
        message = message_queue.pop(0)
        cleaned_message = remove_emojis(message.content).strip()
        cleaned_message = substituir_abreviacoes(cleaned_message)
        cleaned_message = clean_text(cleaned_message)

        if cleaned_message:
            try:
                if len(cleaned_message) > 200:
                    print("Texto muito longo para conversão TTS.")
                    continue

                voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)
                if voice_client is None:
                    voice_channel = message.author.voice.channel
                    voice_client = await voice_channel.connect()
                    current_voice_client = voice_client
                elif voice_client.channel != message.author.voice.channel:
                    await voice_client.move_to(message.author.voice.channel)

                lang = language_mode.get(message.author.id, 'pt')  # Obtém o idioma do usuário ou usa 'pt' por padrão

                if lang == 'it':
                    try:
                        translation = translator.translate(cleaned_message, src='pt', dest='it').text
                        print(f"Tradução para italiano: {translation}")
                        cleaned_message = translation
                    except Exception as e:
                        print(f"Erro ao traduzir a mensagem: {e}")

                try:
                    print(f"Gerando áudio para a mensagem: {cleaned_message}")  # Adiciona log
                    tts = gTTS(cleaned_message, lang=lang, slow=False)
                    tts.save("message.mp3")
                    voice_client.play(discord.FFmpegPCMAudio("message.mp3", executable="C:/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe"), after=lambda e: asyncio.run_coroutine_threadsafe(remove_mp3(), bot.loop))

                    while voice_client.is_playing():
                        await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Erro ao gerar o áudio com gTTS: {e}")
                    continue

            except Exception as e:
                print(f"Erro ao criar ou tocar áudio: {e}")
        else:
            print("Mensagem limpa está vazia, nada para falar.")

    processing_message = False

async def remove_mp3():
    await asyncio.sleep(1)  # Adiciona um atraso antes de tentar remover o arquivo
    try:
        if os.path.exists("message.mp3"):
            os.remove("message.mp3")
            print("Arquivo message.mp3 removido.")  # Adiciona log
    except Exception as e:
        print(f"Erro ao remover o arquivo: {e}")

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    try:
        output = subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
        print(f"FFmpeg está acessível:\n{output.decode()}")
    except FileNotFoundError:
        print("FFmpeg não encontrado no PATH.")

@bot.event
async def on_voice_state_update(member, before, after):
    global current_voice_client

    if member.id == AMIGO_ID and after.channel is not None and current_voice_client is None:
        voice_channel = after.channel
        vc = await voice_channel.connect()
        current_voice_client = vc
        print("Conectando ao canal de voz...")

    elif member.id == AMIGO_ID and after.channel is None:
        if current_voice_client and current_voice_client.channel == before.channel:
            await current_voice_client.disconnect()
            current_voice_client = None
            print("Desconectando do canal de voz...")

@bot.event
async def on_message(message):
    global processing_message

    if message.author == bot.user:
        return

    if not message.content.startswith("!"):
        if message.author.id == AMIGO_ID:
            message_queue.append(message)
            print(f"Mensagem adicionada à fila: {message.content}")  # Adiciona log

            if not processing_message:
                processing_message = True
                await process_message_queue()

    await bot.process_commands(message)

@bot.command(name='parar')
async def stop(ctx):
    global current_voice_client, message_queue, processing_message

    if ctx.author.id == AMIGO_ID:
        if current_voice_client:
            current_voice_client.stop()

        message_queue.clear()
        processing_message = False
        bot_message = await ctx.send("Parando todas as falas e limpando a fila.")
        await asyncio.sleep(3)
        await ctx.message.delete()
        await bot_message.delete()
    else:
        bot_message = await ctx.send("Você não tem permissão para usar este comando.")
        await asyncio.sleep(3)
        await ctx.message.delete()
        await bot_message.delete()

@bot.command(name='pular')
async def skip(ctx):
    global current_voice_client

    if ctx.author.id == AMIGO_ID:
        if current_voice_client and current_voice_client.is_playing():
            current_voice_client.stop()
            bot_message = await ctx.send("Pulando para a próxima mensagem.")
            await asyncio.sleep(3)
            await ctx.message.delete()
            await bot_message.delete()
    else:
        bot_message = await ctx.send("Você não tem permissão para usar este comando.")
        await asyncio.sleep(3)
        await ctx.message.delete()
        await bot_message.delete()

@bot.command(name='it')
async def italiano(ctx):
    if ctx.author.id == AMIGO_ID:
        language_mode[ctx.author.id] = 'it'
        bot_message = await ctx.send("Modo italiano ativado. Todas as mensagens serão traduzidas para italiano e lidas nesse idioma.")
        await asyncio.sleep(3)
        await ctx.message.delete()
        await bot_message.delete()
    else:
        bot_message = await ctx.send("Você não tem permissão para usar este comando.")
        await asyncio.sleep(3)
        await ctx.message.delete()
        await bot_message.delete()

@bot.command(name='pt')
async def portugues(ctx):
    if ctx.author.id == AMIGO_ID:
        language_mode[ctx.author.id] = 'pt'
        bot_message = await ctx.send("Modo português ativado. Todas as mensagens serão lidas em português.")
        await asyncio.sleep(3)
        await ctx.message.delete()
        await bot_message.delete()
    else:
        bot_message = await ctx.send("Você não tem permissão para usar este comando.")
        await asyncio.sleep(3)
        await ctx.message.delete()
        await bot_message.delete()

bot.run(DISCORD_BOT_TOKEN)
