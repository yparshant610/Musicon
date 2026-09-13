import os
import re
import asyncio
import random
import shutil
from urllib.request import Request, urlopen
from collections import deque

import discord
from discord.ext import commands
from discord import app_commands

import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

Client_ID = os.getenv("Client_ID")
Client_secret = os.getenv("Client_secret")
SPOTIFY_REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI",
    "http://127.0.0.1:8888/callback"
)


# ============================================================
# CONFIGURATION
# ============================================================

# True  = commands are registered immediately to your test server
# False = commands are registered globally for production
DEVELOPMENT_MODE = False

TEST_GUILD_ID = 1546916717559812268


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FFMPEG_PATH = shutil.which("ffmpeg") or os.path.join(
    BASE_DIR,
    "bin",
    "ffmpeg",
    "ffmpeg.exe"
)

YOUTUBE_COOKIE_FILE = os.getenv("YOUTUBE_COOKIE_FILE", "").strip()


def get_youtube_cookie_file():

    if not YOUTUBE_COOKIE_FILE:
        return None

    if not os.path.isfile(YOUTUBE_COOKIE_FILE):
        print(
            f"WARNING: YouTube cookie file was not found: {YOUTUBE_COOKIE_FILE}"
        )
        return None

    return YOUTUBE_COOKIE_FILE


# ============================================================
# VALIDATION
# ============================================================

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing from .env"
    )

if not os.path.isfile(FFMPEG_PATH):
    print(
        f"WARNING: FFmpeg was not found at:\n"
        f"{FFMPEG_PATH}"
    )


# ============================================================
# SPOTIFY
# ============================================================

spotify = None

if Client_ID and Client_secret:

    try:

        spotify_auth_manager = SpotifyOAuth(
            client_id=Client_ID,
            client_secret=Client_secret,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=(
                "playlist-read-private "
                "playlist-read-collaborative"
            ),
            cache_path=os.path.join(
                BASE_DIR,
                ".spotify_cache"
            )
        )

        spotify = spotipy.Spotify(
            auth_manager=spotify_auth_manager
        )

        print("Spotify API initialized.")

    except Exception as e:

        print(
            f"Spotify initialization failed: {e}"
        )

else:

    print(
        "WARNING: Spotify credentials are missing."
    )
    
def spotify_has_authorization():

    if not spotify:
        return False

    try:

        token_info = (
            spotify.auth_manager.get_cached_token()
        )

        return bool(
            token_info
            and token_info.get("refresh_token")
        )

    except Exception as e:

        print(
            f"Spotify token check failed: {e}"
        )

        return False


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()

# Slash commands do NOT require Message Content Intent.
# We keep this enabled for possible future message features.
intents.message_content = True


# ============================================================
# MUSIC DATA
# ============================================================

# guild_id -> deque of songs waiting to play
SONG_QUEUE = {}

# guild_id -> last 5 played songs
RECENT_SONGS = {}

# guild_id -> current song
CURRENT_SONG = {}

# guilds intentionally stopped by /stop
STOPPED_BY_USER = set()

# prevents multiple play_next_song() calls simultaneously
PLAYING_NEXT = set()


# ============================================================
# BOT CLASS
# ============================================================

# ============================================================
# BOT CLASS
# ============================================================

class MusicBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="/",
            intents=intents
        )

    async def setup_hook(self):

        print("\n" + "=" * 60)
        print("SYNCING APPLICATION COMMANDS")
        print("=" * 60)

        guild = discord.Object(
            id=TEST_GUILD_ID
        )

        # ====================================================
        # DEVELOPMENT MODE
        # ====================================================

        if DEVELOPMENT_MODE:

            # Get the commands currently defined in Python
            commands_to_register = list(
                self.tree.get_commands()
            )

            print(
                f"Found {len(commands_to_register)} local commands."
            )

            # ------------------------------------------------
            # Remove old GLOBAL commands
            # guild=None = global commands
            # ------------------------------------------------

            self.tree.clear_commands(
                guild=None
            )

            try:

                await self.tree.sync()

                print(
                    "Old global commands cleared."
                )

            except Exception as e:

                print(
                    f"Global cleanup error: {e}"
                )

            # ------------------------------------------------
            # Restore current local commands
            # ------------------------------------------------

            for command in commands_to_register:

                self.tree.add_command(
                    command
                )

            print(
                "Local commands restored."
            )

            # ------------------------------------------------
            # Remove old TEST GUILD commands
            # ------------------------------------------------

            self.tree.clear_commands(
                guild=guild
            )

            try:

                await self.tree.sync(
                    guild=guild
                )

                print(
                    "Old development-guild commands cleared."
                )

            except Exception as e:

                print(
                    f"Guild cleanup error: {e}"
                )

            # ------------------------------------------------
            # Copy current commands to test guild
            # ------------------------------------------------

            self.tree.copy_global_to(
                guild=guild
            )

            # ------------------------------------------------
            # Register fresh commands
            # ------------------------------------------------

            synced = await self.tree.sync(
                guild=guild
            )

            print(
                f"Development mode: "
                f"{len(synced)} commands synced."
            )

            print("\nCommands:")

            for command in synced:

                print(
                    f"  /{command.name}"
                )

        # ====================================================
        # PRODUCTION MODE
        # ====================================================

        else:

            synced = await self.tree.sync()

            print(
                f"Production mode: "
                f"{len(synced)} global commands synced."
            )

            print("\nCommands:")

            for command in synced:

                print(
                    f"  /{command.name}"
                )

        print("=" * 60 + "\n")


# ============================================================
# CREATE BOT
# ============================================================

bot = MusicBot()


# ============================================================
# QUEUE HELPERS
# ============================================================

def get_queue(guild_id):

    if guild_id not in SONG_QUEUE:

        SONG_QUEUE[guild_id] = deque()

    return SONG_QUEUE[guild_id]


def get_recent(guild_id):

    if guild_id not in RECENT_SONGS:

        RECENT_SONGS[guild_id] = deque(
            maxlen=5
        )

    return RECENT_SONGS[guild_id]


# ============================================================
# TEXT HELPER
# ============================================================

def clean_text(text):

    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip()


# ============================================================
# YOUTUBE SEARCH
# ============================================================

def search_youtube(query):

    try:

        options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "default_search": "ytsearch1",
            "source_address": "0.0.0.0"
        }

        cookie_file = get_youtube_cookie_file()

        if cookie_file:
            options["cookiefile"] = cookie_file
            print("Using configured YouTube cookie file for search.")

        with yt_dlp.YoutubeDL(options) as ytdl:

            result = ytdl.extract_info(
                f"ytsearch1:{query}",
                download=False
            )

        if not result:
            return None

        entries = result.get(
            "entries"
        )

        if not entries:
            return None

        video = entries[0]

        return {
            "title": video.get(
                "title",
                "Unknown Song"
            ),
            "url": (
                video.get("webpage_url")
                or video.get("original_url")
            ),
            "duration": video.get(
                "duration"
            ),
            "thumbnail": video.get(
                "thumbnail"
            ),
            "artist": video.get(
                "uploader"
            ),
            "genres": []
        }

    except Exception as e:

        print(
            f"YouTube search error: {e}"
        )

        return None


# ============================================================
# GET FRESH YOUTUBE AUDIO URL
# ============================================================

def get_audio_url(video_url):

    try:

        options = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "source_address": "0.0.0.0",

            # Helps YouTube extraction
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "web",
                        "android"
                    ]
                }
            }
        }

        # ----------------------------------------------------
        # Use exported YouTube cookies when configured
        # ----------------------------------------------------

        cookie_file = get_youtube_cookie_file()

        if cookie_file:

            options["cookiefile"] = cookie_file

            print(
                f"Using YouTube cookie file: {cookie_file}"
            )

        else:

            # Optional fallback for a local machine where a browser
            # is available. This is normally not used on EC2.
            browser = os.getenv(
                "YOUTUBE_BROWSER",
                ""
            ).strip().lower()

            supported_browsers = {
                "chrome",
                "edge",
                "firefox",
                "brave",
                "chromium",
                "opera",
                "vivaldi",
                "whale"
            }

            if browser in supported_browsers:

                options["cookiesfrombrowser"] = (
                    browser,
                )

                print(
                    f"Using {browser} browser cookies for YouTube."
                )

        with yt_dlp.YoutubeDL(options) as ytdl:

            info = ytdl.extract_info(
                video_url,
                download=False
            )

        if not info:
            return None

        return {
            "url": info.get("url"),

            "title": info.get(
                "title",
                "Unknown Song"
            ),

            "thumbnail": info.get(
                "thumbnail"
            ),

            "duration": info.get(
                "duration"
            ),

            "artist": (
                info.get("artist")
                or info.get("uploader")
            )
        }

    except Exception as e:

        print(
            f"Audio extraction error: {e}"
        )

        return None

# ============================================================
# URL DETECTION
# ============================================================

def is_youtube_url(url):

    return bool(
        re.search(
            r"(youtube\.com|youtu\.be)",
            url,
            re.IGNORECASE
        )
    )


def is_youtube_playlist(url):

    return bool(
        re.search(
            r"[?&]list=",
            url,
            re.IGNORECASE
        )
    )


def is_spotify_url(url):

    return (
        "open.spotify.com"
        in url.lower()
    )


def get_spotify_type(url):

    match = re.search(
        r"open\.spotify\.com/(track|playlist|album)/",
        url,
        re.IGNORECASE
    )

    if not match:
        return None

    return match.group(1).lower()


# ============================================================
# GET SPOTIFY ARTIST GENRES
# ============================================================

def get_artist_genres(artist_id):

    if not spotify or not artist_id:
        return []

    try:

        artist = spotify.artist(
            artist_id
        )

        return artist.get(
            "genres",
            []
        )

    except Exception as e:

        print(
            f"Artist genre error: {e}"
        )

        return []


# ============================================================
# SPOTIFY TRACK
# ============================================================

def process_spotify_track(url):

    if not spotify:
        return []

    try:

        track = spotify.track(
            url
        )

        if not track:
            return []

        track_name = clean_text(
            track.get("name")
        )

        artists = track.get(
            "artists",
            []
        )

        if not artists:
            return []

        artist_name = clean_text(
            artists[0].get(
                "name",
                ""
            )
        )

        artist_id = artists[0].get(
            "id"
        )

        genres = get_artist_genres(
            artist_id
        )

        youtube_song = search_youtube(
            f"{artist_name} {track_name}"
        )

        if not youtube_song:
            return []

        youtube_song["spotify_name"] = (
            track_name
        )

        youtube_song["spotify_artist"] = (
            artist_name
        )

        youtube_song["genres"] = genres

        return [
            youtube_song
        ]

    except Exception as e:

        print(
            f"Spotify track error: {e}"
        )

        return []


# ============================================================
# SPOTIFY PLAYLIST
# ============================================================

def process_spotify_playlist(url):

    if not spotify:
        return []

    songs = []

    try:

        results = spotify.playlist_items(
            url,
            additional_types=[
                "track"
            ]
        )

        while results:

            for item in results.get(
                "items",
                []
            ):

                track = item.get(
                    "track"
                )

                if not track:
                    continue

                if track.get(
                    "is_local"
                ):
                    continue

                track_name = clean_text(
                    track.get("name")
                )

                artists = track.get(
                    "artists",
                    []
                )

                if not artists:
                    continue

                artist_name = clean_text(
                    artists[0].get(
                        "name",
                        ""
                    )
                )

                artist_id = artists[0].get(
                    "id"
                )

                genres = get_artist_genres(
                    artist_id
                )

                youtube_song = search_youtube(
                    f"{artist_name} {track_name}"
                )

                if not youtube_song:
                    continue

                youtube_song["spotify_name"] = (
                    track_name
                )

                youtube_song["spotify_artist"] = (
                    artist_name
                )

                youtube_song["genres"] = genres

                songs.append(
                    youtube_song
                )

            if results.get("next"):

                results = spotify.next(
                    results
                )

            else:

                break

    except spotipy.SpotifyException as e:

        if e.http_status != 403:

            print(
                f"Spotify playlist error: {e}"
            )

            return songs

        print(
            "Spotify API blocked this playlist; "
            "trying its public page."
        )

        return process_public_spotify_playlist(
            url
        )

    except Exception as e:

        print(
            f"Spotify playlist error: {e}"
        )

    return songs


def process_public_spotify_playlist(url):

    try:

        track_ids = []

        playlist_match = re.search(
            r"open\.spotify\.com/playlist/([A-Za-z0-9]+)",
            url,
            re.IGNORECASE
        )

        page_urls = [url]

        if playlist_match:
            page_urls.append(
                "https://open.spotify.com/embed/playlist/"
                + playlist_match.group(1)
            )

        for page_url in page_urls:

            request = Request(
                page_url,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            with urlopen(
                request,
                timeout=20
            ) as response:

                page = response.read().decode(
                    "utf-8",
                    errors="ignore"
                )

            patterns = (
                r'music:song"\s+content="https://open\.spotify\.com/track/([^"?]+)',
                r'open\.spotify\.com/track/([A-Za-z0-9]+)',
                r'spotify:track:([A-Za-z0-9]+)',
                r'"track"\s*:\s*\{[^{}]*"id"\s*:\s*"([A-Za-z0-9]+)"',
            )

            for pattern in patterns:

                for track_id in re.findall(
                    pattern,
                    page,
                    re.IGNORECASE
                ):

                    if track_id not in track_ids:

                        track_ids.append(
                            track_id
                        )

        if not track_ids:

            print(
                "No public Spotify tracks were found."
            )

            return []

        songs = []

        for track_id in track_ids:

            try:

                track = spotify.track(
                    track_id
                )

                track_name = clean_text(
                    track.get("name")
                )

                artists = track.get(
                    "artists",
                    []
                )

                if not track_name or not artists:

                    continue

                artist_name = clean_text(
                    artists[0].get(
                        "name",
                        ""
                    )
                )

                youtube_song = search_youtube(
                    f"{artist_name} {track_name}"
                )

                if not youtube_song:

                    continue

                youtube_song["spotify_name"] = (
                    track_name
                )

                youtube_song["spotify_artist"] = (
                    artist_name
                )

                songs.append(
                    youtube_song
                )

            except Exception as e:

                print(
                    f"Public Spotify track error: {e}"
                )

        return songs

    except Exception as e:

        print(
            f"Public Spotify playlist error: {e}"
        )

        return []


# ============================================================
# SPOTIFY ALBUM
# ============================================================

def process_spotify_album(url):

    if not spotify:
        return []

    songs = []

    try:

        results = spotify.album_tracks(
            url
        )

        while results:

            for track in results.get(
                "items",
                []
            ):

                track_name = clean_text(
                    track.get("name")
                )

                artists = track.get(
                    "artists",
                    []
                )

                if not artists:
                    continue

                artist_name = clean_text(
                    artists[0].get(
                        "name",
                        ""
                    )
                )

                artist_id = artists[0].get(
                    "id"
                )

                genres = get_artist_genres(
                    artist_id
                )

                youtube_song = search_youtube(
                    f"{artist_name} {track_name}"
                )

                if not youtube_song:
                    continue

                youtube_song["spotify_name"] = (
                    track_name
                )

                youtube_song["spotify_artist"] = (
                    artist_name
                )

                youtube_song["genres"] = genres

                songs.append(
                    youtube_song
                )

            if results.get("next"):

                results = spotify.next(
                    results
                )

            else:

                break

    except Exception as e:

        print(
            f"Spotify album error: {e}"
        )

    return songs


# ============================================================
# PROCESS SPOTIFY URL
# ============================================================

def process_spotify_url(url):

    spotify_type = get_spotify_type(
        url
    )

    if spotify_type == "track":

        return process_spotify_track(
            url
        )

    if spotify_type == "playlist":

        return process_spotify_playlist(
            url
        )

    if spotify_type == "album":

        return process_spotify_album(
            url
        )

    return []


# ============================================================
# YOUTUBE PLAYLIST
# ============================================================

def process_youtube_playlist(url):

    songs = []

    try:

        options = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True
        }

        cookie_file = get_youtube_cookie_file()

        if cookie_file:
            options["cookiefile"] = cookie_file
            print("Using configured YouTube cookie file for playlist.")

        with yt_dlp.YoutubeDL(options) as ytdl:

            playlist = ytdl.extract_info(
                url,
                download=False
            )

        if not playlist:
            return []

        entries = playlist.get(
            "entries",
            []
        )

        for entry in entries:

            if not entry:
                continue

            video_url = (
                entry.get("webpage_url")
                or entry.get("url")
            )

            if not video_url:
                continue

            songs.append(
                {
                    "title": entry.get(
                        "title",
                        "Unknown Song"
                    ),
                    "url": video_url,
                    "duration": entry.get(
                        "duration"
                    ),
                    "thumbnail": None,
                    "artist": entry.get(
                        "uploader"
                    ),
                    "genres": []
                }
            )

    except Exception as e:

        print(
            f"YouTube playlist error: {e}"
        )

    return songs


# ============================================================
# AUTO-DJ GENRE
# ============================================================

def get_preferred_genre(guild_id):

    recent = get_recent(
        guild_id
    )

    genre_count = {}

    for song in recent:

        for genre in song.get(
            "genres",
            []
        ):

            genre = clean_text(
                genre.lower()
            )

            if not genre:
                continue

            genre_count[genre] = (
                genre_count.get(
                    genre,
                    0
                ) + 1
            )

    if not genre_count:
        return None

    return max(
        genre_count,
        key=genre_count.get
    )


# ============================================================
# AUTO-DJ SONG GENERATOR
# ============================================================

def generate_auto_dj_song(guild_id):

    recent = get_recent(
        guild_id
    )

    recent_titles = {
        clean_text(
            song.get(
                "title",
                ""
            ).lower()
        )
        for song in recent
    }

    preferred_genre = get_preferred_genre(
        guild_id
    )

    # --------------------------------------------------------
    # Spotify Auto-DJ
    # --------------------------------------------------------

    if spotify:

        try:

            if preferred_genre:

                results = spotify.search(
                    q=f"genre:{preferred_genre}",
                    type="track",
                    limit=10
                )

            else:

                results = spotify.search(
                    q="popular",
                    type="track",
                    limit=10
                )

            tracks = results.get(
                "tracks",
                {}
            ).get(
                "items",
                []
            )

            random.shuffle(
                tracks
            )

            for track in tracks:

                track_name = clean_text(
                    track.get("name")
                )

                artists = track.get(
                    "artists",
                    []
                )

                if not artists:
                    continue

                artist_name = clean_text(
                    artists[0].get(
                        "name",
                        ""
                    )
                )

                if not track_name:
                    continue

                if (
                    track_name.lower()
                    in recent_titles
                ):
                    continue

                youtube_song = search_youtube(
                    f"{artist_name} {track_name}"
                )

                if not youtube_song:
                    continue

                artist_id = artists[0].get(
                    "id"
                )

                genres = get_artist_genres(
                    artist_id
                )

                youtube_song[
                    "spotify_name"
                ] = track_name

                youtube_song[
                    "spotify_artist"
                ] = artist_name

                youtube_song[
                    "genres"
                ] = genres

                youtube_song[
                    "auto_dj"
                ] = True

                return youtube_song

        except Exception as e:

            print(
                f"Spotify Auto-DJ error: {e}"
            )

    # --------------------------------------------------------
    # Fallback Auto-DJ
    # --------------------------------------------------------

    fallback_queries = [
        "popular music",
        "latest popular songs",
        "trending music",
        "top songs"
    ]

    # Prefer an artist from recent history
    artists = []

    for song in recent:

        artist = (
            song.get("spotify_artist")
            or song.get("artist")
        )

        if artist:
            artists.append(
                artist
            )

    if artists:

        fallback_queries.insert(
            0,
            f"{random.choice(artists)} songs"
        )

    random.shuffle(
        fallback_queries
    )

    for query in fallback_queries:

        song = search_youtube(
            query
        )

        if song:

            song["genres"] = []
            song["auto_dj"] = True

            return song

    return None


# ============================================================
# NOW PLAYING EMBED
# ============================================================

def create_now_playing_embed(song):

    title = song.get(
        "title",
        "Unknown Song"
    )

    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"**{title}**"
    )

    artist = (
        song.get("spotify_artist")
        or song.get("artist")
    )

    if artist:

        embed.add_field(
            name="Artist",
            value=artist,
            inline=True
        )

    if song.get(
        "auto_dj"
    ):

        embed.add_field(
            name="Mode",
            value="🤖 Auto-DJ",
            inline=True
        )

    thumbnail = song.get(
        "thumbnail"
    )

    if thumbnail:

        embed.set_thumbnail(
            url=thumbnail
        )

    return embed


# ============================================================
# PLAY NEXT SONG
# ============================================================

async def play_next_song(
    guild_id,
    voice_client
):

    # --------------------------------------------------------
    # Prevent duplicate playback operations
    # --------------------------------------------------------

    if guild_id in PLAYING_NEXT:
        return

    if not voice_client:
        return

    if not voice_client.is_connected():
        return

    PLAYING_NEXT.add(
        guild_id
    )

    try:

        # ----------------------------------------------------
        # Try a few times if yt-dlp fails.
        # ----------------------------------------------------

        for attempt in range(3):

            if not voice_client.is_connected():
                return

            queue = get_queue(
                guild_id
            )

            # ------------------------------------------------
            # User intentionally stopped the bot
            # ------------------------------------------------

            if guild_id in STOPPED_BY_USER:

                return

            # ------------------------------------------------
            # Get queued song
            # ------------------------------------------------

            if queue:

                song = queue.popleft()

            # ------------------------------------------------
            # Queue empty -> Auto-DJ
            # ------------------------------------------------

            else:

                print(
                    f"[Auto-DJ] Generating next song "
                    f"for guild {guild_id}"
                )

                song = await asyncio.to_thread(
                    generate_auto_dj_song,
                    guild_id
                )

                if not song:

                    print(
                        "[Auto-DJ] Could not find a song."
                    )

                    return

            # ------------------------------------------------
            # Get fresh audio URL
            # ------------------------------------------------

            print(
                f"Preparing: "
                f"{song.get('title', 'Unknown')}"
            )

            audio_data = await asyncio.to_thread(
                get_audio_url,
                song.get("url")
            )

            if not audio_data:

                print(
                    f"Could not extract audio "
                    f"(attempt {attempt + 1}/3)"
                )

                continue

            audio_url = audio_data.get(
                "url"
            )

            if not audio_url:

                continue

            # ------------------------------------------------
            # Update metadata
            # ------------------------------------------------

            song["title"] = audio_data.get(
                "title",
                song.get(
                    "title",
                    "Unknown Song"
                )
            )

            if not song.get(
                "thumbnail"
            ):

                song["thumbnail"] = (
                    audio_data.get(
                        "thumbnail"
                    )
                )

            if not song.get(
                "artist"
            ):

                song["artist"] = (
                    audio_data.get(
                        "artist"
                    )
                )

            # ------------------------------------------------
            # FFmpeg
            # ------------------------------------------------

            ffmpeg_before_options = (
                "-reconnect 1 "
                "-reconnect_streamed 1 "
                "-reconnect_delay_max 5"
            )

            ffmpeg_options = "-vn"

            source = discord.FFmpegPCMAudio(
                audio_url,
                executable=FFMPEG_PATH,
                before_options=ffmpeg_before_options,
                options=ffmpeg_options
            )

            # ------------------------------------------------
            # Save current song
            # ------------------------------------------------

            CURRENT_SONG[
                guild_id
            ] = song

            # ------------------------------------------------
            # Add to recent history
            # ------------------------------------------------

            recent = get_recent(
                guild_id
            )

            recent.append(
                song
            )

            # ------------------------------------------------
            # Playback callback
            # ------------------------------------------------

            def after_playing(error):

                if error:

                    print(
                        f"Playback error: {error}"
                    )

                CURRENT_SONG.pop(
                    guild_id,
                    None
                )

                async def continue_playing():

                    await asyncio.sleep(1)

                    if guild_id in STOPPED_BY_USER:
                        return

                    guild = bot.get_guild(
                        guild_id
                    )

                    if not guild:
                        return

                    vc = guild.voice_client

                    if not vc:
                        return

                    if not vc.is_connected():
                        return

                    if vc.is_playing():
                        return

                    await play_next_song(
                        guild_id,
                        vc
                    )

                bot.loop.create_task(
                    continue_playing()
                )

            # ------------------------------------------------
            # Start playback
            # ------------------------------------------------

            voice_client.play(
                source,
                after=after_playing
            )

            print(
                f"Now playing: "
                f"{song.get('title')}"
            )

            return

        print(
            "Failed to start playback after 3 attempts."
        )

        # Stop Auto-DJ from continuously generating
        # new songs when YouTube extraction is unavailable.
        if guild_id in CURRENT_SONG:
            CURRENT_SONG.pop(
                guild_id,
                None
            )
        return
    
    except Exception as e:

        print(
            f"play_next_song error: {e}"
        )

    finally:

        PLAYING_NEXT.discard(
            guild_id
        )


# ============================================================
# /PLAY
# ============================================================

@bot.tree.command(
    name="spotify_auth",
    description="Authorize Spotify for the bot owner"
)
async def spotify_auth(
    interaction: discord.Interaction
):

    if not await bot.is_owner(
        interaction.user
    ):

        await interaction.response.send_message(
            "❌ Only the bot owner can authorize Spotify.",
            ephemeral=True
        )

        return

    if not spotify:

        await interaction.response.send_message(
            "❌ Spotify API credentials are not configured.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        await asyncio.to_thread(
            spotify.auth_manager.get_access_token,
            check_cache=False
        )

        await interaction.followup.send(
            "✅ Spotify authorization completed. "
            "Users can now load playlists.",
            ephemeral=True
        )

    except Exception as e:

        print(
            f"Spotify authorization error: {e}"
        )

        await interaction.followup.send(
            "❌ Spotify authorization failed. "
            "Check the redirect URI and Spotify app settings.",
            ephemeral=True
        )

@bot.tree.command(
    name="play",
    description="Play a song, YouTube URL, YouTube playlist, or Spotify URL"
)
@app_commands.describe(
    query="Song name, YouTube URL, YouTube playlist, or Spotify track/playlist/album"
)
async def play(
    interaction: discord.Interaction,
    query: str
):

    await interaction.response.defer()

    # --------------------------------------------------------
    # Must be in a server
    # --------------------------------------------------------

    if not interaction.guild:

        await interaction.followup.send(
            "❌ This command can only be used inside a server."
        )

        return

    guild = interaction.guild
    guild_id = guild.id

    if (
        is_spotify_url(query)
        and not spotify_has_authorization()
    ):

        await interaction.followup.send(
            "❌ Spotify has not been authorized yet. "
            "The bot owner must run `/spotify_auth` once.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # User manually played something.
    # Allow Auto-DJ again.
    # --------------------------------------------------------

    STOPPED_BY_USER.discard(
        guild_id
    )

    # --------------------------------------------------------
    # Must be in voice
    # --------------------------------------------------------

    if not interaction.user.voice:

        await interaction.followup.send(
            "❌ Join a voice channel first."
        )

        return

    voice_channel = (
        interaction.user.voice.channel
    )

    # --------------------------------------------------------
    # Connect to voice
    # --------------------------------------------------------

    voice_client = guild.voice_client

    try:

        if voice_client:

            if (
                voice_client.channel
                != voice_channel
            ):

                await voice_client.move_to(
                    voice_channel
                )

        else:

            voice_client = await voice_channel.connect()

    except Exception as e:

        await interaction.followup.send(
            f"❌ Could not connect to voice channel:\n`{e}`"
        )

        return

    queue = get_queue(
        guild_id
    )

    # ========================================================
    # SPOTIFY
    # ========================================================

    if is_spotify_url(query):

        if not spotify:

            await interaction.followup.send(
                "❌ Spotify API is not configured."
            )

            return

        spotify_type = get_spotify_type(
            query
        )

        await interaction.followup.send(
            f"🔎 Loading Spotify "
            f"{spotify_type or 'content'}..."
        )

        songs = await asyncio.to_thread(
            process_spotify_url,
            query
        )

        if not songs:

            await interaction.followup.send(
                "❌ Could not load songs from this Spotify URL."
            )

            return

        for song in songs:

            queue.append(
                song
            )

        if voice_client.is_playing():

            await interaction.followup.send(
                f"✅ Added **{len(songs)}** song(s) to the queue."
            )

            return

        await interaction.followup.send(
            f"✅ Added **{len(songs)}** song(s). "
            f"Starting playback..."
        )

        await play_next_song(
            guild_id,
            voice_client
        )

        return

    # ========================================================
    # YOUTUBE PLAYLIST
    # ========================================================

    if (
        is_youtube_url(query)
        and is_youtube_playlist(query)
    ):

        await interaction.followup.send(
            "🔎 Loading YouTube playlist..."
        )

        songs = await asyncio.to_thread(
            process_youtube_playlist,
            query
        )

        if not songs:

            await interaction.followup.send(
                "❌ Could not load this YouTube playlist."
            )

            return

        for song in songs:

            queue.append(
                song
            )

        if voice_client.is_playing():

            await interaction.followup.send(
                f"✅ Added **{len(songs)}** songs to the queue."
            )

            return

        await interaction.followup.send(
            f"✅ Added **{len(songs)}** songs. "
            f"Starting playback..."
        )

        await play_next_song(
            guild_id,
            voice_client
        )

        return

    # ========================================================
    # YOUTUBE SINGLE VIDEO
    # ========================================================

    if is_youtube_url(query):

        song = {
            "title": "YouTube Song",
            "url": query,
            "genres": []
        }

        queue.append(
            song
        )

        if voice_client.is_playing():

            await interaction.followup.send(
                "✅ Added song to the queue."
            )

            return

        await interaction.followup.send(
            "▶️ Starting playback..."
        )

        await play_next_song(
            guild_id,
            voice_client
        )

        return

    # ========================================================
    # NORMAL SEARCH
    # ========================================================

    await interaction.followup.send(
        f"🔎 Searching for **{query}**..."
    )

    song = await asyncio.to_thread(
        search_youtube,
        query
    )

    if not song:

        await interaction.followup.send(
            "❌ Could not find that song."
        )

        return

    queue.append(
        song
    )

    if voice_client.is_playing():

        await interaction.followup.send(
            f"✅ Added **{song['title']}** to the queue."
        )

        return

    await interaction.followup.send(
        f"▶️ Starting **{song['title']}**..."
    )

    await play_next_song(
        guild_id,
        voice_client
    )


# ============================================================
# /SKIP
# ============================================================

@bot.tree.command(
    name="skip",
    description="Skip the current song"
)
async def skip(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used inside a server."
        )

        return

    voice_client = (
        interaction.guild.voice_client
    )

    if (
        not voice_client
        or not voice_client.is_playing()
    ):

        await interaction.response.send_message(
            "❌ Nothing is currently playing."
        )

        return

    voice_client.stop()

    await interaction.response.send_message(
        "⏭️ Skipped the current song."
    )


# ============================================================
# /PAUSE
# ============================================================

@bot.tree.command(
    name="pause",
    description="Pause the current song"
)
async def pause(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used inside a server."
        )

        return

    voice_client = (
        interaction.guild.voice_client
    )

    if (
        not voice_client
        or not voice_client.is_playing()
    ):

        await interaction.response.send_message(
            "❌ Nothing is currently playing."
        )

        return

    voice_client.pause()

    await interaction.response.send_message(
        "⏸️ Playback paused."
    )


# ============================================================
# /RESUME
# ============================================================

@bot.tree.command(
    name="resume",
    description="Resume the paused song"
)
async def resume(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used inside a server."
        )

        return

    voice_client = (
        interaction.guild.voice_client
    )

    if not voice_client:

        await interaction.response.send_message(
            "❌ I'm not connected to a voice channel."
        )

        return

    if not voice_client.is_paused():

        await interaction.response.send_message(
            "▶️ Playback is not paused."
        )

        return

    voice_client.resume()

    await interaction.response.send_message(
        "▶️ Playback resumed."
    )


# ============================================================
# /STOP
# ============================================================

@bot.tree.command(
    name="stop",
    description="Stop playback and disconnect the bot"
)
async def stop(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used inside a server."
        )

        return

    guild = interaction.guild
    guild_id = guild.id

    # --------------------------------------------------------
    # IMPORTANT:
    # Prevent Auto-DJ from starting again.
    # --------------------------------------------------------

    STOPPED_BY_USER.add(
        guild_id
    )

    # --------------------------------------------------------
    # Clear queue
    # --------------------------------------------------------

    get_queue(
        guild_id
    ).clear()

    CURRENT_SONG.pop(
        guild_id,
        None
    )

    # --------------------------------------------------------
    # Stop and disconnect
    # --------------------------------------------------------

    voice_client = (
        guild.voice_client
    )

    if voice_client:

        try:

            if voice_client.is_playing():

                voice_client.stop()

            await voice_client.disconnect()

        except Exception as e:

            print(
                f"Disconnect error: {e}"
            )

    await interaction.response.send_message(
        "⏹️ Stopped playback, cleared the queue, and disconnected."
    )


# ============================================================
# /QUEUE
# ============================================================

@bot.tree.command(
    name="queue",
    description="Show the current music queue"
)
async def queue_command(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used inside a server."
        )

        return

    guild_id = interaction.guild.id

    queue = get_queue(
        guild_id
    )

    current = CURRENT_SONG.get(
        guild_id
    )

    lines = []

    # --------------------------------------------------------
    # Current song
    # --------------------------------------------------------

    if current:

        lines.append(
            f"🎵 **Now Playing:** "
            f"{current.get('title', 'Unknown')}"
        )

    # --------------------------------------------------------
    # Queue
    # --------------------------------------------------------

    if queue:

        lines.append(
            "\n📋 **Queue:**"
        )

        for index, song in enumerate(
            list(queue)[:20],
            start=1
        ):

            lines.append(
                f"`{index}.` "
                f"{song.get('title', 'Unknown')}"
            )

        if len(queue) > 20:

            lines.append(
                f"\n...and "
                f"{len(queue) - 20} more."
            )

    else:

        lines.append(
            "\n📋 Queue is empty."
        )

        if guild_id not in STOPPED_BY_USER:

            lines.append(
                "🤖 Auto-DJ will choose the next song automatically."
            )

    embed = discord.Embed(
        title="🎶 Music Queue",
        description="\n".join(lines)
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# /HISTORY
# ============================================================

@bot.tree.command(
    name="history",
    description="Show the last 5 played songs"
)
async def history(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used inside a server."
        )

        return

    guild_id = interaction.guild.id

    recent = get_recent(
        guild_id
    )

    if not recent:

        await interaction.response.send_message(
            "📜 No song history yet."
        )

        return

    lines = []

    for index, song in enumerate(
        reversed(
            list(recent)
        ),
        start=1
    ):

        title = song.get(
            "title",
            "Unknown"
        )

        if song.get(
            "auto_dj"
        ):

            title = (
                f"🤖 {title}"
            )

        lines.append(
            f"`{index}.` {title}"
        )

    embed = discord.Embed(
        title="📜 Recent Songs",
        description="\n".join(lines)
    )

    embed.set_footer(
        text="Last 5 played songs"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# VOICE STATE UPDATE
# ============================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    # Only monitor the bot itself
    if not bot.user:
        return

    if member.id != bot.user.id:
        return

    guild = member.guild
    guild_id = guild.id

    # --------------------------------------------------------
    # Bot disconnected unexpectedly
    # --------------------------------------------------------

    if (
        before.channel is not None
        and after.channel is None
    ):

        # /stop caused this disconnect
        if guild_id in STOPPED_BY_USER:

            print(
                f"[Voice] Intentional disconnect "
                f"from {guild.name}"
            )

            return

        print(
            f"[Voice] Unexpected disconnect "
            f"from {guild.name}"
        )

        await asyncio.sleep(2)

        # ----------------------------------------------------
        # Check again before reconnecting
        # ----------------------------------------------------

        if guild.voice_client:

            return

        try:

            await before.channel.connect()

            print(
                f"[Voice] Reconnected to "
                f"{before.channel.name}"
            )

            voice_client = (
                guild.voice_client
            )

            if voice_client:

                await play_next_song(
                    guild_id,
                    voice_client
                )

        except Exception as e:

            print(
                f"[Voice] Reconnect error: {e}"
            )


# ============================================================
# READY EVENT
# ============================================================

@bot.event
async def on_ready():

    print("\n" + "=" * 60)

    print(
        f"Bot logged in as: {bot.user}"
    )

    print(
        f"Bot ID: {bot.user.id}"
    )

    if DEVELOPMENT_MODE:

        print(
            f"Development Guild: "
            f"{TEST_GUILD_ID}"
        )

    else:

        print(
            "Mode: Production / Global commands"
        )

    print("=" * 60 + "\n")


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    try:

        bot.run(
            DISCORD_TOKEN
        )

    except KeyboardInterrupt:

        print(
            "\nBot stopped by user."
        )

    except Exception as e:

        print(
            f"\nBot crashed: {e}"
        )