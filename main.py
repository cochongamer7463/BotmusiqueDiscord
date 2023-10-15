import io
import random
import sqlite3
import threading
import time

import asyncio
import discord
from discord import app_commands, Intents, Client, Interaction
from pytube import YouTube, Playlist, Search, exceptions

db = sqlite3.connect("music_queue.db")
SQL = db.cursor()


# create a decorator to time a function
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print('%r  %2.2f sec' % \
              (method.__name__, te - ts))
        return result

    return timed


class test(Client):
    def __init__(self, *, intents: Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        await self.tree.sync(guild=None)


client = test(intents=Intents.all())


@client.event
async def on_ready():
    print("le bot est prêt")
    SQL.execute('CREATE table IF NOT EXISTS music('
                'server_id integer,'
                'server_name text,'
                'voice_id integer,'
                'song_url text,'
                'played boolean,'
                'downloaded boolean'
                ')')
    SQL.execute("DELETE FROM music")
    db.commit()


@client.tree.command(description="spammer un innocent (utilisable uniquement par cochongamer_7463)")
async def spam(interaction: Interaction, user: discord.User, message: str):
    if interaction.user.id == 775466490932625429 or interaction.user.id == 681884655968190540:
        if user.id != client.user.id:
            global who_spam
            for elements in who_spam:
                if elements["who"] == user.id and elements["where"] == interaction.guild:
                    del who_spam[who_spam.index({"who": user.id, "where": interaction.guild, "what": elements["what"]})]
                    await interaction.response.send_message(f"stop spamming {user.name}", ephemeral=True)
                    break
            else:
                who_spam.append({"who": user.id, "where": interaction.guild, "what": message})
                await interaction.response.send_message(f"start spamming {user.name}", ephemeral=True)
        else:
            await interaction.response.send_message("I can't do this me", ephemeral=True)
    else:
        await interaction.response.send_message(
            f"only <@775466490932625429> or <@681884655968190540>can do this command", ephemeral=True)


@client.tree.command(name="spam_message_prive")
async def spam_mp(interaction: Interaction, user: discord.User, nombres: int, message: str):
    if interaction.user.id == 775466490932625429 or interaction.user.id == 681884655968190540:
        if user.id != client.user.id:
            await interaction.response.send_message(";)", ephemeral=True)
            for i in range(0, nombres):
                await user.send(message)
        else:
            await interaction.response.send_message("I can't do this me", ephemeral=True)

    else:
        await interaction.response.send_message(
            f"only <@775466490932625429> or <@681884655968190540>can do this command", ephemeral=True)


@client.event
async def on_message(message):
    global who_spam
    for elements in who_spam:
        if elements["who"] == message.author.id and elements["where"] == message.guild:
            await message.reply(who_spam[who_spam.index({"who": message.author.id,
                                                         "where": message.guild,
                                                         "what": elements["what"]})]["what"])


async def rejoindre(interaction: Interaction):
    channel = interaction.user.voice.channel
    try:
        return await channel.connect()
    except discord.errors.ClientException as e:
        return discord.utils.get(client.voice_clients, guild=interaction.guild)


async def saveToDatabase(interaction: Interaction, urls: list[str] = None, url=None):
    if urls is None:
        urls = [url, ]
    data = list()
    for url in urls:
        data.append((interaction.guild.id,
                     interaction.guild.name,
                     interaction.user.voice.channel.id,
                     url,
                     False,
                     False))

    def save():
        db2 = sqlite3.connect("music_queue.db")
        SQL2 = db2.cursor()
        SQL2.executemany(
            "INSERT INTO music(server_id, server_name, voice_id,song_url, played, downloaded) VALUES(?,?,?,?,?,?)",
            data)
        db2.commit()
        db2.close()

    threadSave = threading.Thread(target=save)
    threadSave.start()
    while threadSave.is_alive():
        await asyncio.sleep(1)


@client.tree.command(
    description="commence à jouer les pistes audio de la queue et si indiquer ajoute 1 piste audio à la suite")
async def play(interaction: Interaction, aleatoire: bool = False, terme: str = None):
    await interaction.response.defer()
    try:
        channel_id = interaction.user.voice.channel.id
    except AttributeError:
        await interaction.followup.send("Vous n'êtes pas dans un channel", ephemeral=True)
    else:
        voice_client: discord.VoiceClient = await rejoindre(interaction)
        server_id = interaction.guild_id
        server_name = interaction.guild.name
        if terme is not None:
            await saveToDatabase(interaction, url=terme)
        bufferBefore = io.BytesIO()
        bufferAfter = io.BytesIO()
        urlBefore = [str(), ]
        urlAfter = [str(), ]
        rowidBefore = [int(), ]
        rowidAfter = [int(), ]

        # @timeit
        def download(url: str, buffer: io.BytesIO):
            buffer.seek(0)
            buffer.truncate(0)
            if url == "":
                return
            if url.find("https://") != -1:
                YouTube(url).streams.filter(only_audio=True, file_extension="mp4").first().stream_to_buffer(buffer)
            else:
                Search(url).results[0].streams.filter(only_audio=True,
                                                      file_extension="mp4").first().stream_to_buffer(buffer)

        def after(error):
            if error:
                print(error)
            try:
                asyncio.run_coroutine_threadsafe(check_queueAfter(urlBefore, rowidBefore, urlAfter, rowidAfter),
                                                 client.loop)
            except (TypeError, ValueError) as errorCheckQueue:
                print(errorCheckQueue)
                asyncio.run_coroutine_threadsafe(interaction.user.voice.channel.send("Queue de lecture vide"),
                                                 client.loop)

        async def check_queueStart(url_before, rowid_before, url_after, rowid_after):
            if await check_num_database() < 1:
                if aleatoire:
                    (url_before[0], rowid_before[0]), (url_after[0], rowid_after[0]) = random.choices(SQL.execute(
                        'SELECT song_url, _rowid_ FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? AND downloaded = ? ORdER BY _Rowid_ ASC',
                        (server_id, server_name, channel_id, False)).fetchall(), k=2)
                else:
                    (url_before[0], rowid_before[0]), (url_after[0], rowid_after[0]) = SQL.execute(
                        'SELECT song_url, _rowid_ FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? AND downloaded = ? ORDER BY _rowid_ ASC',
                        (server_id, server_name, channel_id, False)).fetchmany(size=2)
            elif not await check_num_database():
                await interaction.followup.send("pas de son ajouter", ephemeral=True)
            else:
                if aleatoire:
                    url_before[0], rowid_before[0] = random.choice(SQL.execute(
                        'SELECT song_url, _rowid_ FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? AND downloaded = ? ORdER BY _Rowid_ ASC',
                        (server_id, server_name, channel_id, False)).fetchall())
                else:
                    url_before[0], rowid_before[0] = SQL.execute(
                        'SELECT song_url, _rowid_ FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? AND downloaded = ? ORDER BY _rowid_ ASC',
                        (server_id, server_name, channel_id, False)).fetchone()

            try:
                threadDownloadBefore = threading.Thread(target=download, args=(url_before[0], bufferBefore))
                threadDownloadBefore.start()
                threadDownloadAfter = threading.Thread(target=download, args=(url_after[0], bufferAfter))
                threadDownloadAfter.start()
                SQL.executemany("UPDATE music SET downloaded = ? WHERE _rowid_ = ?",
                                ((True, rowid_before[0]), (True, rowid_after[0])))
                db.commit()
                while threadDownloadBefore.is_alive():
                    await asyncio.sleep(1)
            except (KeyError, exceptions.AgeRestrictedError) as e:
                await interaction.user.voice.channel.send(
                    f"{url_before[0]}: lecture impossible dû à une restriction d'âge")
            if voice_client.is_connected():
                bufferBefore.seek(0)
                voice_client.play(source=discord.FFmpegPCMAudio(source=bufferBefore, pipe=True), after=after)
                SQL.execute("UPDATE music SET played = ? WHERE _rowid_ = ?", (True, rowid_before[0]))
                db.commit()

        async def check_queueAfter(url_before, rowid_before, url_after, rowid_after):
            if bufferAfter.getbuffer().nbytes == 0:
                if await check_num_database() > 0:
                    if aleatoire:
                        url_after[0], rowid_after[0] = random.choice(SQL.execute(
                            'SELECT song_url, _rowid_ FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? AND downloaded = ? ORdER BY _Rowid_ ASC',
                            (server_id, server_name, channel_id, False)).fetchall())
                    else:
                        url_after[0], rowid_after[0] = SQL.execute(
                            'SELECT song_url, _rowid_ FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? AND downloaded = ? ORDER BY _rowid_ ASC',
                            (server_id, server_name, channel_id, False)).fetchone()
                    try:
                        threadDownload = threading.Thread(target=download, args=(url_after[0], bufferAfter))
                        threadDownload.start()
                        SQL.execute("UPDATE music SET downloaded = ? WHERE _rowid_ = ?", (True, rowid_after[0]))
                        db.commit()
                    except (KeyError, exceptions.AgeRestrictedError) as e:
                        await interaction.user.voice.channel.send(
                            f"{url_after[0]}: lecture impossible dû à une restriction d'âge")
            bufferBefore.seek(0)
            bufferBefore.truncate(0)
            bufferBefore.write(bufferAfter.getvalue())
            url_before[0] = url_after[0]
            rowid_before[0] = rowid_after[0]
            bufferAfter.seek(0)
            bufferAfter.truncate(0)

            if await check_num_database() > 0:
                if aleatoire:
                    url_after[0], rowid_after[0] = random.choice(SQL.execute(
                    'SELECT song_url, _rowid_ FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? AND downloaded = ? ORdER BY _Rowid_ ASC',
                    (server_id, server_name, channel_id, False)).fetchall())
                else:
                    url_after[0], rowid_after[0] = SQL.execute(
                    'SELECT song_url, _rowid_ FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? AND downloaded = ? ORDER BY _rowid_ ASC',
                    (server_id, server_name, channel_id, False)).fetchone()
            else:
                await interaction.user.voice.channel.send("Plus de son dans la queue")
                voice_client.stop()
                await voice_client.disconnect()
            try:
                threadDownload = threading.Thread(target=download, args=(url_after[0], bufferAfter))
                threadDownload.start()
                SQL.execute("UPDATE music SET downloaded = ? WHERE _rowid_ = ?", (True, rowid_after[0]))
                db.commit()
            except (KeyError, exceptions.AgeRestrictedError) as e:
                await interaction.user.voice.channel.send(
                    f"{url_after[0]}: lecture impossible dû à une restriction d'âge")
            if voice_client.is_connected():
                bufferBefore.seek(0)
                voice_client.play(source=discord.FFmpegPCMAudio(source=bufferBefore, pipe=True), after=after)
                SQL.execute("UPDATE music SET played = ? WHERE _rowid_ = ?", (True, rowid_before[0]))
                db.commit()

        async def check_num_database():
            return SQL.execute("SELECT COUNT(*) FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ? and downloaded = ?",
                               (server_id, server_name, channel_id, False)).fetchone()[0]

        try:
            await check_queueStart(urlBefore, rowidBefore, urlAfter, rowidAfter)
        except (TypeError, ValueError) as e:
            print(e)
            await interaction.followup.send("pas de son ajouter", ephemeral=True)
        else:
            await interaction.followup.send("musique en route", ephemeral=False)


@client.tree.command(description="Met en pause la lecture audio si elle est en route")
async def pause(interaction: Interaction):
    voice_client: discord.VoiceClient = discord.utils.get(client.voice_clients, guild=interaction.guild)
    try:
        if voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("/reprendre pour reprendre")
        elif voice_client.is_paused():
            await interaction.response.send_message("musique deja en pause", ephemeral=True)
    except AttributeError:
        await interaction.response.send_message("vous n'êtes pas dans un channel", ephemeral=True)


@client.tree.command(description="Reprend la lecture si mis en pause")
async def reprendre(interaction: Interaction):
    voice_client: discord.VoiceClient = discord.utils.get(client.voice_clients, guild=interaction.guild)
    try:
        if voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("reprise de la musique")
        else:
            await interaction.response.send_message("musique pas en pause", ephemeral=True)
    except AttributeError:
        await interaction.response.send_message("vous n'êtes pas dans un channel", ephemeral=True)


@client.tree.command(description="Arrête la lecture audio et vide la queue")
async def stop(interaction: Interaction):
    server_name = str(interaction.guild)
    server_id = interaction.guild_id
    channel_id = interaction.user.voice.channel.id
    SQL.execute('DELETE FROM music WHERE server_id = ? AND server_name = ? AND voice_id = ?',
                (server_id, server_name, channel_id))
    db.commit()
    voice_client: discord.VoiceClient = discord.utils.get(client.voice_clients, guild=interaction.guild)
    try:
        if voice_client.is_connected():
            voice_client.stop()
            await voice_client.disconnect()
            await interaction.response.send_message("musique arrêté")
        else:
            await interaction.response.send_message("le bot n'est pas connecté a un channel", ephemeral=True)
    except AttributeError:
        await interaction.response.send_message("vous n'êtes pas dans un channel", ephemeral=True)


@client.tree.command(name="ajouter-playlist-à-la-suite", description="Ajoute une playlist youtube à la queue")
async def add_playlist_to_queue(interaction: Interaction, lien: str):
    await interaction.response.defer()
    try:
        channel = interaction.user.voice.channel
    except:
        await interaction.followup.send("vous n'êtes pas dans un channel", ephemeral=True)
    else:
        message = await interaction.followup.send("Téléchargement de la playlist en cours ...")
        await saveToDatabase(interaction, urls=[i for i in Playlist(lien).video_urls])
        await message.edit(content=f"{lien} ajoutée à la queue")


@client.tree.command(description="Ajoute un url youtube à la suite ou fais une recherche par mots-clés sur youtube")
async def ajouter_a_la_suite(interaction: Interaction, terme: str):
    await interaction.response.defer()
    try:
        channel = interaction.user.voice.channel
    except:
        await interaction.followup.send("vous n'êtes pas dans un channel", ephemeral=True)
    else:
        message = await interaction.followup.send("Téléchargement de la musique en cours ...")
        await saveToDatabase(interaction, url=terme)
        await message.edit(content=f"{terme} ajoutée a la suit")


@client.tree.command(description="Passe à la prochaine musique dans la queue")
async def suivant(interaction: Interaction):
    try:
        channel = interaction.user.voice.channel
    except:
        await interaction.response.send_message("vous n'êtes pas dans un channel", ephemeral=True)
    else:
        voice_client: discord.VoiceClient = discord.utils.get(client.voice_clients, guild=interaction.guild)
        voice_client.stop()
        await interaction.response.send_message("chanson passée")


class View(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.page = 0
        self.pages = []

    def add_page(self, page: str):
        self.pages.append(page)

    @discord.ui.button(label="<")
    async def previous(self, interaction: Interaction, button: discord.ui.button):
        if self.page > 0:
            await interaction.message.edit(content=self.pages[self.page - 1])
            self.page -= 1
        await interaction.response.defer()

    @discord.ui.button(label=">")
    async def next(self, interaction: Interaction, button: discord.ui.button):
        try:
            await interaction.message.edit(content=self.pages[self.page + 1])
        except IndexError:
            pass
        else:
            self.page += 1
        await interaction.response.defer()


@client.tree.command(name="queue", description="Affiche la queue")
async def show_queue(interaction: Interaction, joue: bool = None):
    await interaction.response.defer()
    try:
        channel = interaction.user.voice.channel
    except:
        await interaction.response.send_message("vous n'êtes pas dans un channel", ephemeral=True)
    else:
        reponse = ["", ]
        view = View()
        if joue is None:
            for index, (ID, name, etat) in enumerate(
                    SQL.execute("SELECT _rowid_, song_url, played FROM music WHERE voice_id = ?",
                                (interaction.user.voice.channel.id,)).fetchall(), 1):
                reponse[0] += f"{index}: `id: {ID} {name}`, **{'joué' if etat else 'non joué'}**;\n"
        else:
            for index, (ID, name) in (
            SQL.execute("SELECT _rowid_, song_url FROM music WHERE voice_id = ? AND played = ?",
                        (interaction.user.voice.channel.id, joue)).fetchall(), 1):
                reponse[0] += f"{index}: `id: {ID} {name}`;\n"
        if len(reponse[0]) // 2000:
            reponse.append(reponse[0][:2000].rsplit("\n", 1)[0])
            for i in range(1, (len(reponse[0]) // 2000) + 2):
                reponse.append(reponse[0][len(reponse[i]):len(reponse[i]) + 2000].rsplit("\n", 1)[0])
                view.add_page(reponse[i])
            await interaction.followup.send(content=view.pages[0], view=view)
        else:
            try:
                await interaction.followup.send(reponse[0])
            except:
                await interaction.followup.send("Il n'y a rien dans la queue")


@client.tree.command(description="Rejoue une entrée deja jouée par son id")
async def rejouer(interaction: Interaction, id_chanson: int):
    try:
        channel = interaction.user.voice.channel
    except:
        await interaction.response.send_message("vous n'êtes pas dans un channel", ephemeral=True)
    else:
        SQL.execute("UPDATE music SET played = ? and downloaded = ? WHERE _rowid_ = ?", (False, False, id_chanson))
        db.commit()
        await interaction.response.send_message(
            f"{SQL.execute('SELECT song_url FROM music WHERE _rowid_ = ?', (id_chanson,)).fetchone()[0]} sera rejoué")


@client.tree.command(description="Supprime une entrée de la queue par son id")
async def supprimer(interaction: Interaction, id_chanson: int):
    try:
        channel = interaction.user.voice.channel
    except:
        await interaction.response.send_message("vous n'êtes pas dans un channel", ephemeral=True)
    else:
        song = SQL.execute("SELECT song_url FROM music WHERE _rowid_ = ?", (id_chanson,)).fetchone()[0]
        SQL.execute("DELETE FROM music WHERE _rowid_ = ?", (id_chanson,))
        db.commit()
        await interaction.response.send_message(f"{song}, id: {id_chanson} à été supprimé de la queue")


who_spam = []
list_playlist = []
with open("discord.key", "r") as file:
    key = file.read()
client.run(key)
