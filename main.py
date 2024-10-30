#MUSIC FILES
from mutagen.flac import Picture, FLAC
from mutagen.id3 import APIC
from mutagen.easyid3 import EasyID3
from pydub import AudioSegment
#COVERS
import requests
from PIL import Image
#MUSIC DOWNLOAD
from yt_dlp import YoutubeDL
from youtube_search import YoutubeSearch
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
#OS
import os
import shutil
from dotenv import load_dotenv
from multiprocessing import Pool



# Spotify Credentials
load_dotenv()
CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    print("[!][SPOTIFY] SPOTIFY KEY NOT SET!\n[!][SPOTIFY] Spotify search and download wont work.")
else:
    CLIENT_CREDENTIALS_MANAGER = SpotifyClientCredentials(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )
    SP = spotipy.Spotify(client_credentials_manager=CLIENT_CREDENTIALS_MANAGER)
    
    def get_spotify_uri(link : str) -> str:
        return link.split("/")[-1].split("?")[0]
    def get_spotify_info(query : str) -> str | list[str | list[str]]:
        if "track" in query:
            uri = get_spotify_uri(query)
            return f"{SP.track(uri)['name']} {SP.track(uri)['artists'][0]['name']}"
        elif "playlist" in query:
            uri = get_spotify_uri(query)
            return [SP.playlist(uri)['name'] ,[f"{song['track']['name']} {song['track']['artists'][0]['name']}" for song in SP.playlist_tracks(uri)["items"]]]

# Main functionality
def format_filename(filename:str) -> str:
    for char in " \\|?:/><'\"*.":
        filename = filename.replace(char, "_")
    return filename
def get_fileext_fromname(path:str, filename:str) -> str:
    files_withext = os.listdir(path)
    files_noext = [os.path.splitext(dir)[0] for dir in os.listdir(path)]
    idx = files_noext.index(filename)
    
    return os.path.splitext(files_withext[idx])
def crop_image(image:Image) -> Image:
    width, height = image.size
    if width == height:
        return image
    # Crop
    offset  = int(abs(height-width)/2)
    if width>height:
        image = image.crop([offset,0,width-offset,height])
    else:
        image = image.crop([0,offset,width,height-offset])

    return image
    
class Song():
    """_summary_
    Methods intended to be used in order: download > transform > rename > move\n
    Can skip a method. Cannot alter order.\n
    Assumes initial download folder is .tmp and destination is ./MUSIC/Folder|Album/Album|Songfolder/song
    """
    def __init__(self, title:str, artist:str = None, cover:str = None, folder:str = None, album:str = None, path:str = "./.tmp/"):
        # Song info
        self.title = title
        self.artist = artist
        self.cover = cover
        self.folder = folder
        self.album = album
        # Variables
        self.filename = format_filename(self.title)
        self.ext = None
        self.path = path
               
    def download_song(self) -> None:
        # Get info and download
        options = {
                'format': 'bestaudio/',
                'noplaylist': True,
                'nocheckcertificate': True,
                'no_warnings': True,
                'default_search': 'auto',
                'source_address': '0.0.0.0',
                'quiet': True,
                'filter': 'audioonly',
                'outtmpl': f'{self.path}{self.filename}.{"%(ext)s"}'
            }
        if "open.spotify" in self.title:
            track = get_spotify_info(self.title)
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info("ytsearch:%s" % track)
        if "youtube.com" in self.title or "youtu.be" in self.title:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(self.title)
        else:
            info = YoutubeSearch(self.title, max_results=1).to_dict()[0]
            with YoutubeDL(options) as ydl:
                ydl.extract_info("ytsearch:%s" % info["title"])
        
        # Set song metadata
        self.title = info["title"]
        self.artist = info["channel"]
        self.album = self.album or info["title"]
        self.cover = self.cover or info["thumbnail"] if "thumbnail" in info else info["thumbnails"][0]
        self.ext = get_fileext_fromname(self.path, self.filename)[1].replace(".", "")
    
    def transcode_song(self, format:str = "flac") -> None:
        # Get name and extension
        filename, ext = get_fileext_fromname(self.path, self.filename)
        ext = ext.replace(".", "")
        
        # Transform and replace
        AudioSegment.from_file(file=f"{self.path}{filename}.{ext}", ext=ext).export(f"{self.path}{self.filename}.{format}", format=format)
        os.remove(f"{self.path}{filename}.{ext}")
        
        # Update variables
        self.ext = format
    
    def rename_totitle(self):
        # Rename
        os.rename(f"{self.path}{self.filename}.{self.ext}", f"{self.path}{format_filename(self.title)}.{self.ext}")
        
        # Update variables
        self.filename = format_filename(self.title)
    
    def move_to_directory(self):
        # Set song path
        path = "./MUSIC/"
        if self.folder:
            path += f"{format_filename(self.folder)}/"
            os.mkdir(path) if not os.path.exists(path) else None
        if self.album:
            path += f"{format_filename(self.album)}/"
            os.mkdir(path) if not os.path.exists(path) else None
        else:
            path += f"{format_filename(self.filename)}/"
            os.mkdir(path) if not os.path.exists(path) else None
        
        # Move song
        shutil.move(f"{self.path}{self.filename}.{self.ext}", f"{path}{self.filename}.{self.ext}")
        
        # Update variables
        self.path = path
    
    def add_metadata(self):
        # Mp3
        if self.ext == "mp3":
            songf = EasyID3(f"{self.path}{self.filename}.{self.ext}")
            # Image metadata
            try:
                # Url check for second statement
                try:
                    coverresponse = requests.get(self.cover)
                except Exception:
                    coverresponse = None
                
                # Cover is file
                if os.path.exists(self.cover):
                    # Save and Crop cover as png on local
                    topng = Image.open(self.cover)
                    topng = crop_image(topng)
                    topng.save(f"{self.path}cover.png")
                    # Add image
                    songf.add(APIC(mime="image/png", type=3, desc="Cover", data=open(f"{self.path}cover.png", "rb").read()))
                
                # Cover is url
                elif coverresponse and coverresponse.ok:
                    # Download image
                    ext = coverresponse.headers["Content-Type"].split("/")[1]
                    if not os.path.exists(f"{self.path}cover.{ext}"):
                        with open(f"{self.path}cover.{ext}", "w+b") as coverf:
                            coverf.write(coverresponse.content)
                    # Crop and Transform to png
                    topng = Image.open(f"{self.path}cover.{ext}")
                    topng = crop_image(topng)
                    topng.save(f"{self.path}cover.png")
                    os.remove(f"{self.path}cover.{ext}")
                    # Set image
                    songf.add(APIC(mime="image/png", type=3, desc="Cover", data=open(f"{self.path}cover.png", "rb").read()))
                
                # Not valid cover
                else:
                    print("[!] [METADATAIMG] Cover not valid")
            except Exception as e:
                print(f"[-] [METADATAIMG] Could not add cover to song {song.filename}>>>\n{e}")
        
        # FLAC
        elif self.ext == "flac":
            songf = FLAC(f"{self.path}{self.filename}.{self.ext}")
            # Image metadata
            try:
                # Url check for second statement
                try:
                    coverresponse = requests.get(self.cover)
                except Exception:
                    coverresponse = None
                
                img = Picture()
                img.desc = 'Cover'
                # Cover is file
                if os.path.exists(self.cover):
                    # Crop and Transform to png
                    topng = Image.open(self.cover)
                    topng = crop_image(topng)
                    topng.save(f"{self.path}cover.png")
                    img.mime = "image/png"
                    # Set image
                    with open(f"{self.path}cover.png", "rb") as coverf:
                        img.data = coverf.read()
                    with Image.open(f"{self.path}cover.png") as imagePil:
                        img.width, img.height = imagePil.size
                        img.depth = 24
                    songf.add_picture(img)
                
                # Cover is url
                elif coverresponse and coverresponse.ok:
                    # Download image
                    ext = coverresponse.headers["Content-Type"].split("/")[1]
                    if not os.path.exists(f"{self.path}cover.{ext}"):
                        with open(f"{self.path}cover.{ext}", "w+b") as coverf:
                            coverf.write(coverresponse.content)
                    # Crop and Transform to png
                    topng = Image.open(f"{self.path}cover.{ext}")
                    topng = crop_image(topng)
                    topng.save(f"{self.path}cover.png")
                    os.remove(f"{self.path}cover.{ext}")
                    # Set image
                    img.mime = "image/png"
                    with open(f"{self.path}cover.png", "rb") as coverf:
                        img.data = coverf.read()
                    with Image.open(f"{self.path}cover.png") as imagePil:
                        img.width, img.height = imagePil.size
                        img.depth = 24
                    songf.add_picture(img)
                
                # Not valid cover
                else:
                    print("[!] [METADATAIMG] Cover not valid")
            except Exception as e:
                print(f"[-] [METADATAIMG] Could not add cover to song {song.filename}>>>\n{e}")
        
        # Universal metadata
        songf["title"] = self.title
        songf["artist"] = self.artist
        songf["album"] = self.album
        songf["albumartist"] = self.artist
        songf.save
        
        
if __name__=="__main__":
    song = Song(title="The survivor, the winner")
    song.download_song()
    song.transcode_song()
    song.rename_totitle()
    song.move_to_directory()
    song.cover = "C:\\Users\\Parab\\Desktop\\Pics\\little_one.png"
    song.add_metadata()