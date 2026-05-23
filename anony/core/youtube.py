# Copyright (c) 2025 AnonymousX1025

import os
import re
import yt_dlp
import random
import asyncio
import requests

from pathlib import Path
from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils
from config import Config

config = Config()

YT_API_KEY = config.YT_API_KEY
YTPROXY = config.YTPROXY_URL


class YouTube:

    def __init__(self):

        self.base = "https://www.youtube.com/watch?v="
        self.cookie_dir = "anony/cookies"
        self.cookies = []

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com|youtu\.be)"
        )

    def get_cookie(self):

        if not os.path.exists(self.cookie_dir):
            return None

        files = [
            f"{self.cookie_dir}/{x}"
            for x in os.listdir(self.cookie_dir)
            if x.endswith(".txt")
        ]

        if not files:
            logger.warning("Cookies missing.")
            return None

        return random.choice(files)

    def valid(self, url: str):

        return bool(re.match(self.regex, url))

    async def search(
        self,
        query: str,
        m_id: int,
        video: bool = False
    ):

        try:

            data = (
                await VideosSearch(
                    query,
                    limit=1
                ).next()
            )["result"][0]

            return Track(
                id=data.get("id"),
                title=data.get("title")[:25],
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(
                    data.get("duration")
                ),
                channel_name=data.get(
                    "channel",
                    {}
                ).get("name"),
                thumbnail=data.get(
                    "thumbnails",
                    [{}]
                )[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get(
                    "viewCount",
                    {}
                ).get("short"),
                message_id=m_id,
                video=video,
            )

        except Exception as ex:

            logger.warning(
                "Search Error: %s",
                ex
            )

            return None

    async def playlist(
        self,
        limit: int,
        user: str,
        url: str,
        video: bool
    ):

        tracks = []

        try:

            plist = await Playlist.get(url)

            for data in plist["videos"][:limit]:

                tracks.append(
                    Track(
                        id=data.get("id"),
                        title=data.get("title")[:25],
                        duration=data.get("duration"),
                        duration_sec=utils.to_seconds(
                            data.get("duration")
                        ),
                        channel_name=data.get(
                            "channel",
                            {}
                        ).get("name", ""),
                        thumbnail=data.get(
                            "thumbnails"
                        )[-1].get("url").split("?")[0],
                        url=data.get("link").split("&list=")[0],
                        user=user,
                        video=video,
                    )
                )

        except Exception as ex:

            logger.warning(
                "Playlist Error: %s",
                ex
            )

        return tracks

    async def api_download(
        self,
        video_id: str,
        video: bool = False
    ):

        try:

            headers = {
                "x-api-key": YT_API_KEY,
                "User-Agent": "Mozilla/5.0"
            }

            r = requests.get(
                f"{YTPROXY}/info/{video_id}",
                headers=headers,
                timeout=20
            )

            data = r.json()

            if data.get("status") != "success":
                return None

            file_url = (
                data.get("video_url")
                if video
                else data.get("audio_url")
            )

            if not file_url:
                return None

            os.makedirs("downloads", exist_ok=True)

            ext = "mp4" if video else "webm"

            file = f"downloads/{video_id}.{ext}"

            if Path(file).exists():
                return file

            dl = requests.get(
                file_url,
                stream=True,
                timeout=60
            )

            with open(file, "wb") as f:

                for chunk in dl.iter_content(
                    1024 * 1024
                ):

                    if chunk:
                        f.write(chunk)

            return file

        except Exception as ex:

            logger.warning(
                "API Download Error: %s",
                ex
            )

            return None

    async def download(
        self,
        video_id: str,
        video: bool = False
    ):

        api = await self.api_download(
            video_id,
            video
        )

        if api:
            return api

        os.makedirs("downloads", exist_ok=True)

        ext = "mp4" if video else "webm"

        file = f"downloads/{video_id}.{ext}"

        if Path(file).exists():
            return file

        opts = {
            "outtmpl":
            "downloads/%(id)s.%(ext)s",

            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "nocheckcertificate": True,

            "cookiefile":
            self.get_cookie(),

            "extractor_args": {
                "youtube": {
                    "player_client":
                    ["android"]
                }
            },

            "http_headers": {
                "User-Agent":
                "Mozilla/5.0 (Android 13)"
            },

            "format":
            (
                "bestvideo+bestaudio"
                if video
                else "bestaudio/best"
            ),
        }

        if video:
            opts["merge_output_format"] = "mp4"

        def run():

            try:

                with yt_dlp.YoutubeDL(
                    opts
                ) as ydl:

                    ydl.download([
                        self.base + video_id
                    ])

                return file

            except Exception as ex:

                logger.warning(
                    "YT Error: %s",
                    ex
                )

                return None

        return await asyncio.to_thread(run)
