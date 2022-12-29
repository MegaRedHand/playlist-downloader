#!/usr/bin/python3
import argparse
from typing import Iterable
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
    audio = mp4.Open(filename)
    audio.add_tags()
    audio[TRACK_TITLE] = title
    audio[ALBUM] = playlist
    audio[ARTIST] = author
    audio[COMMENT] = "generated by playlist-downloader"

    if thmbn_url != "":
        r = requests.get(thmbn_url)
        if r.headers["content-type"] == 'image/jpeg':
            img_format = mp4.MP4Cover.FORMAT_JPEG
        else:
            img_format = mp4.MP4Cover.FORMAT_PNG
            print(r.headers["content-type"], file=sys.stderr)
        audio[COVERS] = [
            mp4.MP4Cover(r.content, imageformat=img_format)
        ]

    audio.save()


def filter_videos(videos: Iterable[pytube.YouTube], start: str, stop: str):
    start = None if start is None else start.strip()
    stop = None if stop is None else stop.strip()
    filtered = []
    start_flag = start is None

    for v in videos:
        title = v.title.strip()

        if not start_flag:
            if title != start:
                continue
            start_flag = True

        filtered.append(v)

        if title == stop:
            break

    return filtered


def main(playlist: str, args: argparse.Namespace) -> int:
    p = pytube.Playlist(playlist)
    p_dir = p.title

    os.makedirs(p_dir, exist_ok=True)
    os.chdir(p_dir)

    errors = 0

    videos = filter_videos(p.videos, args.start, args.stop)

    print(f"Downloading {len(videos)} videos")

    for video in videos:
        video.oauth = args.oauth
        thumbnail = video.thumbnail_url
        cback = lambda _st, nm: add_tag(nm, video.title, video.author, p.title, thumbnail if args.icons else "")
        video.register_on_complete_callback(cback)
        try:
            stream = video.streams.get_audio_only()
            stream.download(filename_prefix=f"{video.author} - ", skip_existing=args.skip)
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
    parser.add_argument("--start", action="store", help="video index to start on (counts from 0)")
    parser.add_argument("--stop", action="store", help="video index to stop on (non-inclusive)")
    parser.add_argument("--no-icons", action="store_true", help="don't add icons to audio files")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    playlist = args.playlist_url

    if playlist == "":
        playlist = input("Por favor ingrese la url de la playlist a descargar: ")

    errors = main(playlist, args)

    if errors > 0:
        print(f"{errors} errors occured. Running with --oauth (or -o) may solve some of them.")
