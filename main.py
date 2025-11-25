import argparse
import json
import os
import pathlib
from typing import List

import inquirer

EXPORTS_DIR = "exports"
CLEANED_DIR = "cleaned"
REMOVED_DIR = "removed"
REVIEWED_ARTISTS_FILE = "reviewed_artists.json"


def main():
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    os.makedirs(CLEANED_DIR, exist_ok=True)
    os.makedirs(REMOVED_DIR, exist_ok=True)

    parser = argparse.ArgumentParser(description="Clean exported Spotify streaming history by ignoring specified artists.")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of artists to review in each batch.", dest="batch_size")
    parser.add_argument("--skip-review", action="store_true", help="Skip the artist review process and clean files with pervious selections.", dest="skip_review")

    args = parser.parse_args()
    batch_size = args.batch_size
    skip_review = args.skip_review

    streams = load_streaming_history()
    ignored_artists = get_ignored_artists(streams, batch_size, skip_review)
    cleanup_directories()
    clean_exported_data(ignored_artists)


def load_streaming_history() -> List[dict]:
    files = [EXPORTS_DIR + "/" + x for x in os.listdir(EXPORTS_DIR)]
    streams = []

    for file in files:
        with open(file, "r") as f:
            try:
                new_streams = json.load(f)
                streams += [
                    s
                    for s in new_streams
                    if s["master_metadata_track_name"]
                    is not None  # filter out podcasts and audiobooks not tracked by Stats.fm
                ]
                f.close()
            except Exception as e:
                print(f"Error loading streams from {f.name}: {str(e)}")

    return streams


def get_ignored_artists(streams: List[dict], batch_size: int, skip_review: bool) -> List[str]:
    try:
        with open(REVIEWED_ARTISTS_FILE, "r") as f:
            reviewed_json = json.load(f)
            previously_allowed_artists = reviewed_json.get("allowed_artists", [])
            previously_ignored_artists = reviewed_json.get("ignored_artists", [])
            f.close()
    except FileNotFoundError:
        previously_allowed_artists = []
        previously_ignored_artists = []

    if previously_allowed_artists and not skip_review:
        review_allowed_artists = inquirer.confirm(
            f"Review {len(previously_allowed_artists)} previously allowed artists?",
            default=False,
        )
        if review_allowed_artists:
            reviewed_previously_allowed_artists = inquirer.checkbox(
                message="Deselect previously allowed artists to review again:",
                choices=previously_allowed_artists,
                default=previously_allowed_artists,
                carousel=True,
            )
            previously_allowed_artists = reviewed_previously_allowed_artists
    if previously_ignored_artists and not skip_review:
        review_ignored_artists = inquirer.confirm(
            f"Review {len(previously_ignored_artists)} previously ignored artists?",
            default=False,
        )
        if review_ignored_artists:
            reviewed_previously_ignored_artists = inquirer.checkbox(
                message="Deselect previously ignored artists to review again:",
                choices=previously_ignored_artists,
                default=previously_ignored_artists,
                carousel=True,
            )
            previously_ignored_artists = reviewed_previously_ignored_artists
    filtered_artists = sorted(
        {s["master_metadata_album_artist_name"] for s in streams if (
            not (s["master_metadata_album_artist_name"] in previously_allowed_artists)
            and not (s["master_metadata_album_artist_name"] in previously_ignored_artists)
        )},
        key=lambda x: x.lower(),
    )

    allowed_artists = previously_allowed_artists
    ignored_artists = previously_ignored_artists

    if not skip_review:
        for i in range(0, len(filtered_artists), batch_size):
            batch = filtered_artists[i : i + batch_size]

            print(
                f"\nReviewing artists {i + 1} to {min(i + batch_size, len(filtered_artists))} of {len(filtered_artists)}"
            )
            questions = [
                inquirer.Checkbox(
                    "ignored_artists",
                    message=f"Which artists would you like to ignore? (Unchecked artists will be allowed)",
                    choices=batch,
                    default=previously_ignored_artists,
                    carousel=True,
                ),
                inquirer.Confirm(
                    "continue_filtering",
                    message="Continue reviewing next batch",
                    default=True,
                ),
            ]
            answers = inquirer.prompt(questions)
            batch_ignored_artists = answers.get("ignored_artists", [])
            batch_allowed_artists = [a for a in batch if a not in batch_ignored_artists]
            ignored_artists.extend(batch_ignored_artists)
            allowed_artists.extend(batch_allowed_artists)

            continue_filtering = answers.get("continue_filtering", True)
            if not continue_filtering:
                break

    with open(REVIEWED_ARTISTS_FILE, "w") as f:
        f.write(
            json.dumps(
                {"allowed_artists": allowed_artists, "ignored_artists": ignored_artists}
            )
        )

    return ignored_artists


def cleanup_directories():
    for directory in [CLEANED_DIR, REMOVED_DIR]:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error cleaning up file {file_path}: {str(e)}")


def clean_exported_data(ignored_artist: List[str]):
    files = [EXPORTS_DIR + "/" + x for x in os.listdir(EXPORTS_DIR)]

    for file in files:
        with open(file, "r", encoding="UTF-8") as f:
            try:
                streams = json.load(f)
                cleaned_streams = [
                    s
                    for s in streams
                    if s["master_metadata_album_artist_name"] not in ignored_artist
                ]
                filtered_streams = [
                    s
                    for s in streams
                    if s["master_metadata_album_artist_name"] in ignored_artist
                ]

                cleaned_file_name = (
                    CLEANED_DIR + "/" + pathlib.Path(f.name).stem + "_cleaned.json"
                )

                with open(cleaned_file_name, "w") as cf:
                    cf.write(json.dumps(cleaned_streams))
                    cf.close()

                print(
                    f"Cleaned {f.name} -> {cleaned_file_name} ({len(filtered_streams)} of {len(streams)}  streams removed)"
                )

                if filtered_streams:
                    removed_file_name = (
                        REMOVED_DIR + "/" + pathlib.Path(f.name).stem + "_removed.json"
                    )
                    os.makedirs(REMOVED_DIR, exist_ok=True)
                    with open(removed_file_name, "w") as rf:
                        rf.write(json.dumps(filtered_streams))
                        rf.close()
                    print(
                        f"|-> Removed streams saved to {removed_file_name}"
                    )
            except Exception as e:
                print(f"Error cleaning streams from {f.name}: {str(e)}")


if __name__ == "__main__":
    main()
