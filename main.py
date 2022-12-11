#!/usr/bin/python3
import argparse
from mutagen import mp4
import os
import pytube
import requests
import sys


TRACK_TITLE = "\xa9nam"
ALBUM = "\xa9alb"
ARTIST = "\xa9ART"
COMMENT = "\xa9cmt"
COVERS = "covr"


def add_tag(filename: str, title: str, author: str, playlist: str, thmbn_url: str) -> None:
    r = requests.get(thmbn_url)
    audio = mp4.Open(filename)
    audio.add_tags()
    audio[TRACK_TITLE] = title
    audio[ALBUM] = playlist
    audio[ARTIST] = author
    audio[COMMENT] = "generated by playlist-downloader"

    if r.headers["content-type"] == 'image/jpeg':
        img_format = mp4.MP4Cover.FORMAT_JPEG
    else:
        img_format = mp4.MP4Cover.FORMAT_PNG
        print(r.headers["content-type"], file=sys.stderr)
    audio[COVERS] = [
        mp4.MP4Cover(r.content, imageformat=img_format)
    ]
    audio.save()

def main(playlist: str, skip: bool, oauth: bool) -> int:
    p = pytube.Playlist(playlist)
    p_dir = p.title

    os.makedirs(p_dir, exist_ok=True)
    os.chdir(p_dir)

    errors = 0

    for video in p.videos:
        video.oauth = oauth
        thumbnail = video.thumbnail_url
        cback = lambda _st, nm: add_tag(nm, video.title, video.author, p.title, thumbnail)
        video.register_on_complete_callback(cback)
        try:
            stream = video.streams.get_audio_only()
            stream.download(filename_prefix=f"{video.author} - ", skip_existing=skip)
        except Exception:
            print(f"Error downloading video: {video.title} ({video.watch_url})")
            errors += 1

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='playlist-downloader',
        description='Download a YouTube playlist',
    )
    parser.add_argument("playlist_url", nargs='?', default="", help="URL of the playlist to download")
    parser.add_argument("-s", "--skip", action="store_true", help="skip existing files")
    parser.add_argument("-o", "--oauth", action="store_true", help="login to YouTube before downloading")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    playlist = args.playlist_url

    if playlist == "":
        playlist = input("Por favor ingrese la url de la playlist a descargar: ")

    errors = main(playlist, args.skip, args.oauth)

    if errors > 0:
        print(f"{errors} errors occured. Running with --oauth (or -o) may solve some of them.")