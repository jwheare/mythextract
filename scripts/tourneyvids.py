#!/usr/bin/env python3
import json
import os
import pathlib
import re
import sys
import csv


DEBUG = (os.environ.get('DEBUG') == '1')
TRADE = os.environ.get('TRADE')
FILTER_PRINT = (os.environ.get('FILTER_PRINT') == '1')

def tourney_slug(short_name):
    return re.sub(r'mwc|MWC20|MWC 20', '', short_name)

def main(tourneys_dir, vid_csv, output_path):
    """
    Map youtube videos from a csv into tournament into stats
    """
    tourneys_path = pathlib.Path(tourneys_dir)
    if not output_path:
        output_path = tourneys_path / 'youtube.json'

    try:
        with open(output_path, 'r') as output_file:
            youtube_info = json.load(output_file)
    except FileNotFoundError:
        youtube_info = {}

    tourneys = {}
    for tourney_path in [p for p in (tourneys_path / 'tournament').iterdir() if p.is_dir()]:
        if 'mwc' not in tourney_path.name.lower():
            continue
        tourney_info_file = tourney_path / 'info.json'
        try:
            with open(tourney_info_file, 'r') as t_info_file:
                tourney_info = json.load(t_info_file)
        except FileNotFoundError:
            print('No tourney info file', tourney_path.name)
            continue

        if 'rounds' not in tourney_info:
            print('No round info', tourney_path.name)
            continue
        
        t_slug = tourney_slug(tourney_info['short_name'])
        tourneys[t_slug] = tourney_info

    with open(vid_csv, newline='') as csv_file:
        vid_reader = csv.DictReader(csv_file, fieldnames=[
            'short_name',
            'stage',
            'channel',
            'title',
            'yt_id',
            'yt_url',
        ])
        for vid_i, row in enumerate(vid_reader):
            try:
                process_row(vid_i, row, tourneys, youtube_info)
            except AbortException:
                break
            except Exception as exc:
                print(exc)
                continue

    if prompt(f"Write to {output_path}?"):
        with open(output_path, 'w') as output_json:
            json.dump(youtube_info, output_json, indent=2)

class AbortException(Exception):
    pass

def process_row(vid_i, row, tourneys, youtube_info):
    # Check if already mapped
    if row['yt_id'] in youtube_info:
        return
    print("\n---")
    print(f"{row['yt_url']}")
    print(f"{vid_i}. {row['short_name']} {row['stage']}: {row['title']} ({row['yt_id']} - {row['channel']})")
    print()
    vid_slug = tourney_slug(row['short_name'])
    if vid_slug not in tourneys:
        print('No tourney matches, SKIP')
        return

    tourney_info = tourneys.get(vid_slug)

    round_matches = []
    for round_info in tourney_info['rounds']:
        if round_info.get('stage') == row['stage']:
            round_matches.append(round_info)
    chosen = False

    info = {
        "meta": row,
        "mapping": []
    }
    multiple = True
    while multiple:
        if len(round_matches):
            for round_i, round_info in enumerate(round_matches):
                print(f"{round_i + 1}) {tourney_info['short_name']} {round_info['round_name']} ({round_info['round_slug']}) {len(round_info['games'])}x")
            round_choices = input("\nChoose a round by number (0 for none) (optionally specify game after a space): ").strip().split(' ', 1)
            game_choice = None
            first_choice = round_choices[0]
            if first_choice.startswith('m'):
                first_choice = first_choice.lstrip('m')
            else:
                multiple = False

            if first_choice != '':
                round_choice = int(first_choice)
                if len(round_choices) == 2:
                    game_choice = int(round_choices[1])
                if round_choice > 0 and round_choice:
                    mapping = {}
                    round_match = round_matches[round_choice-1]
                    if game_choice is not None:
                        game_match = round_match['games'][game_choice-1]
                        mapping['game_num'] = game_choice
                        mapping['game_path'] = game_match['game_path']
                    mapping['tournament'] = tourney_info['slug']
                    mapping['path'] = round_match['round_path']
                    info['mapping'].append(mapping)
                    youtube_info[row['yt_id']] = info
                    chosen = True
        if not chosen:
            if prompt("Map to tournament?"):
                info['mapping'].append({
                    'tournament': tourney_info['slug'],
                    'path': tourney_info['path'],
                })
                youtube_info[row['yt_id']] = info
                chosen = True
                multiple = False
            else:
                raise AbortException

    if chosen:
        print([m['path'] for m in youtube_info[row['yt_id']]['mapping']])

def prompt(text):
    response = input(f"{text} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <tourneys_dir> <vid_csv> [<output_path>]")
        sys.exit(1)
    
    tourneys_dir = sys.argv[1]
    vid_csv = sys.argv[2]
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
    else:
        output_path = None
    
    try:
        main(tourneys_dir, vid_csv, output_path)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
