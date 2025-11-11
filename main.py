import inquirer
import os
from typing import List
import json
import pathlib

EXPORTS_DIR = "exports"
CLEANED_DIR = "cleaned"
IGNORED_ARTIST_FILE = "ignored_artists.json"

def main():
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    os.makedirs(CLEANED_DIR, exist_ok=True)

    streams = load_streaming_history()
    ignored_artists = get_ignored_artists(streams)
    clean_exported_data(ignored_artists)



def load_streaming_history() -> List[dict]:
    files = [EXPORTS_DIR + "/" + x for x in os.listdir(EXPORTS_DIR)]
    streams = []

    for file in files:
        with open(file, "r") as f:
            try:
                new_streams = json.load(f)
                streams += [
                    s for s in new_streams
                    if s["master_metadata_track_name"] is not None # filter out podcasts and audiobooks not tracked by Stats.fm
                ]
                f.close()
            except Exception as e:
                print(f"Error loading streams from {f.name}: {str(e)}")

    return streams


def get_ignored_artists(streams: List[dict]) -> List[str]:
    try:
        with open(IGNORED_ARTIST_FILE, "r") as f:
            previously_ignored_artists = json.load(f)
            f.close()
    except FileNotFoundError:
        previously_ignored_artists = []
    artists = sorted({ s["master_metadata_album_artist_name"] for s in streams }, key=lambda x: x.lower())

    questions = [
        inquirer.Checkbox(
            "ignored_artists",
            message=f"Which artists would you like to ignore? ({len(artists)} found, {len(previously_ignored_artists)} previously ignored)",
            choices=artists,
            default=previously_ignored_artists,
            carousel=True
        )
    ]
    answer = inquirer.prompt(questions)
    ignored_artists = answer.get("ignored_artists", [])

    with open(IGNORED_ARTIST_FILE, "w") as f:
        f.write(json.dumps(ignored_artists))

    return ignored_artists


def clean_exported_data(ignored_artist: List[str]):
    files = [EXPORTS_DIR + "/" + x for x in os.listdir(EXPORTS_DIR)]

    for file in files:
        with open(file, "r", encoding="UTF-8") as f:
            streams = json.load(f)
            cleaned_streams = [s for s in streams if s["master_metadata_album_artist_name"] not in ignored_artist]
            filtered_streams = [s for s in streams if s["master_metadata_album_artist_name"] in ignored_artist]
            
            cleaned_file_name = CLEANED_DIR + "/" + pathlib.Path(f.name).stem + "_cleaned.json"

            with open(cleaned_file_name, "w") as cf:
                cf.write(json.dumps(cleaned_streams))
                cf.close()
            
            print(f"Cleaned {f.name} -> {cleaned_file_name} ({len(filtered_streams)} of {len(streams)}  streams removed)")


if __name__ == "__main__":
    main()