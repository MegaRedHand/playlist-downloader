#!/usr/bin/python3
import argparse
import pathlib
import itertools
from typing import Iterable, Optional
from mutagen import mp3
import os, sys, re
import pytube
import requests


TRACK_TITLE = "\xa9nam"
ALBUM = "\xa9alb"
ARTIST = "\xa9ART"
COMMENT = "\xa9cmt"
COVERS = "covr"


def add_tag(filename: str, title: str, author: str, playlist: str, thmbn_url: str) -> None:
    return
    audio = mp3.Open(filename)
    audio.add_tags()
    audio[TRACK_TITLE] = title
    audio[ALBUM] = playlist
    audio[ARTIST] = author
    audio[COMMENT] = "generated by playlist-downloader"

    if thmbn_url != "":
        r = requests.get(thmbn_url)
        if r.headers["content-type"] == 'image/jpeg':
            img_format = mp3.MP4Cover.FORMAT_JPEG
        else:
            img_format = mp3.MP4Cover.FORMAT_PNG
            print(r.headers["content-type"], file=sys.stderr)
        audio[COVERS] = [
            mp3.MP4Cover(r.content, imageformat=img_format)
        ]

    audio.save(filename)


def filter_videos(videos: Iterable[pytube.YouTube], start: Optional[int], stop: Optional[int]) -> Iterable[pytube.YouTube]:
    if stop is not None:
        filtered = itertools.islice(videos, start or 0, stop)
    elif start is not None:
        for _ in itertools.islice(videos, start):
            pass  # exhaust first `start` videos
        filtered = videos
    else:
        filtered = videos

    return filtered


def strip_nonstandard(name):
    name = re.sub(r'[^\w\(\)\s-]', 'x', name)
    return name.strip('-_')


def main(playlist: str, args: argparse.Namespace) -> int:
    p = pytube.Playlist(playlist)

    p_dir = pathlib.Path(strip_nonstandard(p.title) if args.output is None else args.output)

    os.makedirs(p_dir, exist_ok=True)

    errors = 0

    start = None if args.start is None else int(args.start)
    stop = None if args.stop is None else int(args.stop)

    videos = filter_videos(p.videos, start, stop)

    n_downloaded = 0

    for video in videos:
        video.use_oauth = args.oauth
        thumbnail = video.thumbnail_url
        cback = lambda _st, nm: add_tag(nm, video.title, video.author, p.title, thumbnail if not args.no_icons else "")
        video.register_on_complete_callback(cback)
        try:
            stream = video.streams.get_audio_only()
            output = p_dir.joinpath(f"{strip_nonstandard(video.author)} - {strip_nonstandard(video.title)}.mp3")
            print(f"Downloading '{video.title}' ...")
            stream.download(filename=output, skip_existing=args.skip)
            n_downloaded += 1
        except Exception as e:
            print(f"Error downloading video: {video.title} ({video.watch_url})")
            print(e, file=sys.stderr)
            errors += 1

    print(f"Finished downloading {n_downloaded} videos")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='playlist-downloader',
        description='Download a YouTube playlist',
    )
    parser.add_argument("playlist_url", nargs='?', default="", help="URL of the playlist to download")
    parser.add_argument("-s", "--skip", action="store_true", help="skip existing files")
    parser.add_argument("-o", "--output", action="store", help="path to output directory")
    parser.add_argument("--oauth", action="store_true", help="login to YouTube before downloading")
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
