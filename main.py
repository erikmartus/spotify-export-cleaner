import inquirer
import os
from typing import List
import json
import pathlib

EXPORTS_DIR = "exports"
CLEANED_DIR = "cleaned"
REVIEWED_ARTISTS_FILE = "reviewed_artists.json"

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


def should_prompt_for_artist(
    artist: str,
    previously_allowed_artists: List[str],
    previously_ignored_artists: List[str],
    skip_previously_allowed_artists: bool,
    skip_previously_ignored_artists: bool
) -> bool:
    if skip_previously_allowed_artists and artist in previously_allowed_artists:
        return False
    if skip_previously_ignored_artists and artist in previously_ignored_artists:
        return False
    return True

def get_ignored_artists(streams: List[dict]) -> List[str]:
    try:
        with open(REVIEWED_ARTISTS_FILE, "r") as f:
            reviewed_json = json.load(f)
            previously_allowed_artists = reviewed_json.get("allowed_artists", [])
            previously_ignored_artists = reviewed_json.get("ignored_artists", [])
            f.close()
    except FileNotFoundError:
        previously_allowed_artists = []
        previously_ignored_artists = []

    skip_previously_allowed_artists = True
    skip_previously_ignored_artists = True
    if previously_allowed_artists:
        skip_previously_allowed_artists = inquirer.confirm(f"Skip reviewing {len(previously_allowed_artists)} previously allowed artists?", default=True)
    if previously_ignored_artists:
        skip_previously_ignored_artists = inquirer.confirm(f"Skip reviewing {len(previously_ignored_artists)} previously ignored artists?", default=True)
    all_artists = sorted({s["master_metadata_album_artist_name"] for s in streams}, key=lambda x: x.lower())
    filtered_artists = [
        a for a in all_artists
        if (
            not (skip_previously_allowed_artists and a in previously_allowed_artists)
            and not (skip_previously_ignored_artists and a in previously_ignored_artists)
        )
    ]

    # TODO: update questions to batch, figure out how to save progress as you go.
    questions = [
        inquirer.Checkbox(
            "ignored_artists",
            message=f"Which artists would you like to ignore? ({len(all_artists)} found, {len(previously_allowed_artists)} allowed, {len(previously_ignored_artists)} ignored)",
            choices=filtered_artists,
            default=previously_ignored_artists,
            carousel=True
        )
    ]
    answer = inquirer.prompt(questions)
    ignored_artists = answer.get("ignored_artists", [])

    with open(REVIEWED_ARTISTS_FILE, "w") as f:
        f.write(json.dumps({"allowed_artists": [], "ignored_artists": ignored_artists}))

    return ignored_artists


def clean_exported_data(ignored_artist: List[str]):
    files = [EXPORTS_DIR + "/" + x for x in os.listdir(EXPORTS_DIR)]

    for file in files:
        with open(file, "r", encoding="UTF-8") as f:
            try:
                streams = json.load(f)
                cleaned_streams = [s for s in streams if s["master_metadata_album_artist_name"] not in ignored_artist]
                filtered_streams = [s for s in streams if s["master_metadata_album_artist_name"] in ignored_artist]
                
                cleaned_file_name = CLEANED_DIR + "/" + pathlib.Path(f.name).stem + "_cleaned.json"

                with open(cleaned_file_name, "w") as cf:
                    cf.write(json.dumps(cleaned_streams))
                    cf.close()
                
                print(f"Cleaned {f.name} -> {cleaned_file_name} ({len(filtered_streams)} of {len(streams)}  streams removed)")
            except Exception as e:
                print(f"Error cleaning streams from {f.name}: {str(e)}")


if __name__ == "__main__":
    main()