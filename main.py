#MUSIC FILES
from mutagen.flac import Picture, FLAC
import pydub
#MUSIC DOWNLOAD
from yt_dlp import YoutubeDL
from youtube_search import YoutubeSearch
import spotipy
#OS
import os
import asyncio
from multiprocessing import Pool


class Song():
    def __init__(self, url:str = None, title:str = None, album:str = None, cover:str = None, tracknumber:int = 0):
        #Mandatory
        self.url = url
        self.title = title
        self.album = album
        self.cover = cover
        self.tracknumber = tracknumber + 1 if tracknumber != 0 else tracknumber
        #To be assigned
        self.artist = None
        
    def download_song(self):
        if "youtube.com" in self.url or "youtu.be" in self.url:
            options = {
                'format': 'bestaudio/',
                'restrictfilenames': True,
                'noplaylist': True,
                'nocheckcertificate': True,
                'no_warnings': True,
                'default_search': 'auto',
                'source_address': '0.0.0.0',
                'quiet': True,
                'filter': 'audioonly',
            }
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(self.url)
                self.title = info["title"]