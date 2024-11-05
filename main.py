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
from pytube import Playlist
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
#OS
import os
import shutil
from dotenv import load_dotenv
import re
from multiprocessing import Pool



#----====SPOTIFY CREDENTIALS====----#
# Create a .env file and edit it to have these variables:
# SP_CLIENT_ID ; SP_CLIENT_SECRET
# Assign them your spotify's ID and Secret respectively to enable spotify support

load_dotenv()
CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
if CLIENT_ID and CLIENT_SECRET:
    CLIENT_CREDENTIALS_MANAGER = SpotifyClientCredentials(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )
    SP = spotipy.Spotify(client_credentials_manager=CLIENT_CREDENTIALS_MANAGER)
    
    def get_spotify_uri(link : str) -> str:
        return link.split("/")[-1].split("?")[0]
    def get_spotify_info(query : str) -> str | list[str]:
        if "track" in query:
            uri = get_spotify_uri(query)
            return [f"{SP.track(uri)['name']} {SP.track(uri)['artists'][0]['name']}"]
        
        elif "playlist" in query:
            uri = get_spotify_uri(query)
            return [f"{song['track']['name']} {song['track']['artists'][0]['name']}" for song in SP.playlist_tracks(uri)["items"]]



#------======SONG CLASS======------#
# Class Utils
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

# Song Class
class Song():
    """_summary_
    Song class representing a song and it's metadata.\n
    Assumes initial download folder is .tmp and destination is ./MUSIC/Folder|Album/Album|Songfolder/song\n
    Can work as an album if no album is provided, but will have but a single song attached to it.\n
    Class not intended to be used outside this script. Could be used obeying its directory and naming rules.
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
        print(f"[+][DOWNLOAD] Downloading song [{self.title}]")
        try:
            # Get info and download
            options = {
                    'format': 'bestaudio/',
                    'noplaylist': True,
                    'nocheckcertificate': True,
                    'default_search': 'auto',
                    'source_address': '0.0.0.0',
                    'quiet': True,
                    'filter': 'audioonly',
                    'outtmpl': f'{self.path}{self.filename}.%(ext)s',
                    'sleep_interval': 20,
                    'max_sleep_interval':35
                }
            if "youtube.com" in self.title or "youtu.be" in self.title:
                with YoutubeDL(options) as ydl:
                    info = ydl.extract_info(self.title)
            else:
                info = YoutubeSearch(self.title, max_results=1).to_dict()[0]
                with YoutubeDL(options) as ydl:
                    ydl.extract_info(f"https://youtube.com{info["url_suffix"]}") 
        except Exception as e:
            print(f"[-][DOWNLOAD] [{self.title}] Download exception\n#EXCEPTION: {e}")
        
        # Set song metadata
        try:
            print(f"[+][DOWNLOAD-MTD] Setting metadata for [{self.title}][{self.filename}]")
            
            self.title = info["title"]
            self.artist = info["channel"]
            self.album = self.album or info["title"]
            self.cover = self.cover or (info["thumbnails"][0] if "thumbnails" in info else info["thumbnail"])
            self.ext = get_fileext_fromname(self.path, self.filename)[1].replace(".", "")
        except Exception as e:
            print(f"[-][DOWNLOAD-MTD] [{self.title}] failed metadata addition\n#EXCEPTION: {e}")

    def transcode_song(self, format_to:str = "flac") -> None:
        print(f"[+][TRANSCODE] Transcoding song [{self.title}.{self.ext}] to [{format_to}]")
        try:
            # Get name and extension
            filename, ext = get_fileext_fromname(self.path, self.filename)
            ext = ext.replace(".", "")
            
            # Transform and replace
            AudioSegment.from_file(file=f"{self.path}{filename}.{ext}", ext=ext).export(f"{self.path}{self.filename}.{format_to}", format=format_to)
            os.remove(f"{self.path}{filename}.{ext}")
            
            # Update variables
            self.ext = format_to
        except Exception as e:
            print(f"[-][TRANSCODE] [{self.title}.{self.ext}] failed transcode to [{format_to}]\n#EXCEPTION: {e}")
    
    def rename_totitle(self):
        try:
            print(f"[+][RENAME] Renaming [{self.filename}] to [{self.title}]")
            # Rename
            os.rename(f"{self.path}{self.filename}.{self.ext}", f"{self.path}{format_filename(self.title)}.{self.ext}")
            
            # Update variables
            self.filename = format_filename(self.title)
        except Exception as e:
            print(f"[-][RENAME] [{self.filename}] failed renaming to [{self.title}]\n#EXCEPTION: {e}")
    
    def move_to_directory(self):
        print(f"[+][MOVE] Moving [{self.title}] to proper directory")
        try:
            # Set song path
            path = "./MUSIC/"
            if self.folder:
                path += f"{format_filename(self.folder)}/"
                os.mkdir(path) if not os.path.exists(path) else None
            if self.album:
                path += f"{format_filename(self.album)}/"
                os.mkdir(path) if not os.path.exists(path) else None
            
            # Move song
            shutil.move(f"{self.path}{self.filename}.{self.ext}", f"{path}{self.filename}.{self.ext}")
            
            # Update variables
            self.path = path
        except Exception as e:
            print(f"[-][DOWNLOAD] [{self.title}] failed moving\n#EXCEPTION: {e}")
    
    def add_metadata(self):
        print(f"[+][METADATA] Adding metadata to [{self.title}]")
        try:
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
                    print(f"[-] [METADATAIMG] Could not add cover to song {self.filename}>>>\n{e}")

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
                    print(f"[-] [METADATAIMG] Could not add cover to song {self.filename}>>>\n{e}")
            
            # Universal metadata
            songf["title"] = self.title
            songf["artist"] = self.artist
            songf["album"] = self.album
            songf["albumartist"] = self.artist if self.album == self.title else "Various Artists"
            
            songf.save()
        except Exception as e:
            print(f"[-][METADATA] Failed adding metadata to [{self.title}]\n#EXCEPTION: {e}")



#-----=====FILE STRUCTURE=====-----#
# Structure Assemblers
def read_lines(textfile:str) -> list[str]:
    with open(textfile, "r") as fl:
        lines = fl.readlines()
    lines = [line.replace("\n", "") for line in lines]
    lines = [line for line in lines if line != ""]
    
    return lines
def line_type(line:str, linetype:str) -> str:
    # Structure bool
    is_structure = line[0] == "[" and line[-1] == "]"
    is_song = not is_structure
    
    linetype = list(linetype)
    # Folder
    if "F" in linetype and is_structure and line[1] == "F":
        raise SyntaxError(f"Double folder stacked on line ( {line} )")
    linetype += "F" if is_structure and line[1] == "F" else ""
    linetype.remove("F") if line == "[!F]" and "F" in linetype else None
    # Album
    if "A" in linetype and is_structure and line[1] == "A":
        raise SyntaxError(f"Double album stacked on line ( {line} )")
    linetype += "A" if is_structure and line[1] == "A" else ""
    linetype.remove("A") if line == "[!A]" and "A" in linetype else None
    # Cover
    if "C" in linetype and is_structure and line[1] == "C":
        raise SyntaxError(f"Double cover stacked on line ( {line} )")
    linetype += "C" if is_structure and line[1] == "C" else ""
    linetype.remove("C") if line == "[!C]" and "C" in linetype else None
    # Song
    linetype += "S" if is_song and "S" not in linetype else ""
    linetype.remove("S") if not is_song and "S" in linetype else None
    
    return "".join(linetype)
def assemble_structure(lines:list) -> list[str]:
    # Vars
    structure = []
    line_composition = ""
    
    # Create structure
    for line in lines:
        line_composition = line_type(line, line_composition)
        structure.append(line_composition)

    # Return
    return structure
def assign_songs(lines:list[str], structure:list[str]) -> dict[str:Song]:
    songs = {}
    toappend = {}
    # Assign songs
    for idx in range(len(lines)):
        # Enter Empty
        if not structure[idx]:
            continue
        # Enter Folder
        if structure[idx][0] == "F":
            # Assign folder name
            if structure[idx] == "F" and (idx == 0 or "F" not in structure[idx-1]):
                folder = lines[idx][3:-1]
        else:
            folder = None
        # Enter album folder
        if "A" in structure[idx]:
            # Assign album name
            if "A" in structure[idx] and (idx == 0 or "A" not in structure[idx-1]):
                album = lines[idx][3:-1]
        else:
            album = None
        # Enter cover
        if "C" in structure[idx]:
            # Assign cover
            if "C" in structure[idx] and (idx == 0 or "C" not in structure[idx-1]):
                cover = lines[idx][3:-1]
        else:
            cover = None        
        
        # Assign song
        if "S" in structure[idx]:
            # Spotify / Playlist append
            if "https://" in lines[idx] or "http://" in lines[idx]:
                # Spotify
                if "open.spotify" in lines[idx]:
                    playlist_songs = get_spotify_info(query=lines[idx])
                    
                    for song in playlist_songs:
                        toappend[song] = Song(title=song, album=album, folder=folder, cover=cover)  
                # Youtube
                elif ("youtu.be" in lines[idx] or "youtube.com" in lines[idx]) and "playlist" in lines[idx]:
                    playlist = Playlist(song)
                    playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)") # Youtube changed regex of video links
                    playlist_urls = playlist.video_urls
                    
                    if playlist_urls:
                        for url in playlist_urls:
                            toappend[url] = Song(title=url, album=album, folder=folder, cover=cover)
            # Normal YT link / song name
            else:
                songs[lines[idx]] = Song(title=lines[idx], album=album, folder=folder, cover=cover)
    # Return
    if toappend:
        songs = songs | toappend
    return songs

# Song download process
def download_process(song_tuple:str) -> None:
    # Main vars
    song = song_tuple[0]
    songs_dict = song_tuple[1]
    
    # Process songs
    try:
        print(f"[+][SONG] Working on: {song}")
        # Download and treat song
        songs_dict[song].download_song()
        songs_dict[song].transcode_song()
        songs_dict[song].rename_totitle()
        songs_dict[song].move_to_directory()
        songs_dict[song].add_metadata()
    except Exception as e:
        print(f"[?] [DOWNLOADEXC] Exception downloading {song}\n#EXCEPTION> {e}")



#--------=======MAIN========--------#
# Main function
def main():
    # Get music list filename
    while True:
        filepath = input("[Filename | Path to file] Plain text file containing songs to download. Leave empty to use default (MusicList.txt): ")
        if not filepath:
            filepath = "./MusicList.txt"
            break

        if os.path.exists(filepath):
            break
        else:
            print("File not found. Make sure your Local Filename / Path is correct.")
    
    # Create structure
    print("[+][LINES] READING LINES...")
    lines = read_lines(filepath)
    print("[+][STRUCTURE] ASSEMBLING STRUCTURE...")
    structure = assemble_structure(lines)
    print("[+][SONGS] ASSIGNING SONGS...")
    songs_dict = assign_songs(lines=lines, structure=structure)
    
    #Download songs with pool
    print("[+][DOWNLOAD] STARTING DOWNLOAD PROCESS...")
    songs = [(song, songs_dict) for song in songs_dict]
    with Pool() as pool:
        pool.map(download_process, songs)
        
if __name__=="__main__":
    main()