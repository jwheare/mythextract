#!/usr/bin/env python3
import json
import os
import pathlib
import re
import sys
import urllib.request
from urllib.error import URLError, HTTPError

from concurrent.futures import ThreadPoolExecutor, as_completed

import mesh_tag
import utils

executor = ThreadPoolExecutor(max_workers=10)

DEBUG = (os.environ.get('DEBUG') == '1')

def fetch_json(url):
    try:
        (status, headers, response_text) = utils.http_request(url)
        return json.loads(response_text)
    except HTTPError as e:
        print(f"HTTP error for {url}: {e.code} {e.reason}")
    except URLError as e:
        print(f"Failed to reach {url}: {e.reason}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON from {url}: {e}")
    except Exception as e:
        print(f"Unexpected error fetching {url}: {e}")

    return None

def fetch_tourney(tourney_id):
    url = f'https://bagrada.net/rank-server/api/public/tournaments/{tourney_id}'
    return fetch_json(url)

def fetch_rounds(tourney_id):
    url = f'https://bagrada.net/rank-server/api/public/tournaments/{tourney_id}/rounds'
    return fetch_json(url)

def fetch_round(tourney_id, round_id):
    url = f'https://bagrada.net/rank-server/api/public/tournaments/{tourney_id}/rounds/{round_id}'
    return fetch_json(url)

def download_film(film_name, output_dir):
    try:
        film_url = f'https://bagrada.net/recordings/public/{film_name}'
        urllib.request.urlretrieve(film_url, output_dir / film_name)
        return (film_name, film_url, output_dir / film_name)
    except HTTPError as e:
        print(f"HTTP error for {film_url}: {e.code} {e.reason}")
    except URLError as e:
        print(f"Failed to reach {film_url}: {e.reason}")
    except Exception as e:
        print(f"Unexpected error downloading {film_url}: {e}")

    return False

def process_round_name(tourney_id, round_name):
    if tourney_id == '7':
        # MWC 2025
        if match := re.match(r'((?:.*Finals)|(?:DE 2)|\w+)\s(.*) vs (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            if stage == 'DE 2':
                stage = 'DE2'
            part = None
            part_suffix = ''
            if part_match := re.match(r'(.*)\s\((\d+)\)$', team2):
                team2 = part_match.group(1)
                part = part_match.group(2)
                part_suffix = f' ({part})'

            round_name = f'{stage}: {team1} vs {team2}{part_suffix}'

            return round_name, {
                'stage': stage,
                'team1': team1.lower(),
                'team2': team2.lower(),
                'part': part,
                '_processed': True,
            }

    return round_name, {}

def main(tourney_id, output_dir):
    """
    Download all films from a tournament from bagrada.net
    """

    tourney_info = fetch_tourney(tourney_id)
    if not tourney_info:
        print('No tourney info')
        sys.exit(1)

    tourney_name = tourney_info['tournamentName']
    tourney_short_name = tourney_info['tournamentShortName']
    tourney_start = tourney_info['startDate']
    print(f"Tournament: {tourney_name}")
    print(f"Short name: {tourney_short_name}")
    print(f"Start date: {tourney_start}")

    rounds = fetch_rounds(tourney_id)
    if not rounds:
        print('No round info')
        sys.exit(1)

    film_count = 0
    rounds_info = {}
    round_futures = []

    t_slug = tourney_slug(tourney_id, tourney_short_name)
    tourney_path = f'tournament/{t_slug}'
    tourney_info_data = {
        'bagrada_tournament': tourney_id,
        'name': tourney_name,
        'short_name': tourney_short_name,
        'slug': t_slug,
        'path': tourney_path,
        'start': tourney_start
    }

    for r in rounds:
        round_futures.append(executor.submit(fetch_round, tourney_id, r['roundId']))
    for f in as_completed(round_futures):
        round_data = f.result()
        if round_data:
            round_id = round_data['roundId']
            round_name, extra_round_data = process_round_name(tourney_id, round_data['roundName'])
            r_slug = round_slug(round_id, round_name)
            round_path = f'rounds/{r_slug}'
            if DEBUG:
                print(
                    round_name, r_slug,
                    extra_round_data.get('stage'),
                    [extra_round_data.get('team1'), extra_round_data.get('team2')]
                )
            games = round_data['games']
            film_count += len(games)
            games_data = []
            for game_num, game_info in enumerate(round_data['games'], 1):
                games_data.append({
                    'game_num': game_num,
                    'bagrada_game': game_info['id'],
                    'game_name': game_info['gameName'].rstrip(),
                    'time_limit': game_info['timeLimit'],
                    'game_type': mesh_tag.netgame_scoring_name(game_info['scoring']),
                    'map_name': utils.strip_format(game_info['mapName']),
                    'difficulty': mesh_tag.difficulty(game_info['difficulty']),
                    'game_path': game_dir(
                        tourney_id, tourney_short_name,
                        round_id, round_name,
                        game_num, game_info['mapName']
                    ),
                    'game_slug': game_slug(game_num, game_info['mapName']),
                    'film_name': game_info['recordingFileName'],
                })
            rounds_info[round_id] = {
                'bagrada_round': round_id,
                'round_name': round_name,
                'round_path': f'{tourney_path}/{round_path}',
                'round_slug': r_slug,
                'games': games_data
            } | extra_round_data

    if not output_dir:
        output_dir = '../output/dltourney'
        path = pathlib.Path(sys.path[0], output_dir).resolve()
    else:
        path = pathlib.Path(output_dir)

    outpath = path / tourney_path
    if prompt(outpath, len(rounds), film_count):
        pathlib.Path(outpath).mkdir(parents=True, exist_ok=True)
        # Write the tournament info file
        tourney_info_file = outpath / 'info.json'
        # Make sure we use the original rounds order
        sorted_rounds_info = [rounds_info[r['roundId']] for r in rounds]
        with open(tourney_info_file, 'w') as t_info_file:
            json.dump(tourney_info_data | {'rounds': sorted_rounds_info}, t_info_file, indent=2)
        if DEBUG:
            print(f"Tournament info saved to {tourney_info_file}")

        dl_futures = []
        # Order here doesn't matter
        for round_info in rounds_info.values():
            round_info_path = path / round_info['round_path']
            pathlib.Path(round_info_path).mkdir(parents=True, exist_ok=True)

            # Write the round info file
            round_info_file = round_info_path / 'info.json'
            with open(round_info_file, 'w') as r_info_file:
                json.dump(round_info | {'tournament': tourney_info_data}, r_info_file, indent=2)
            if DEBUG:
                print(f"Round info saved to {round_info_file}")

            # Download films for each game in the round
            for game_info in round_info['games']:
                output_path = path / game_info['game_path']
                pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)
                dl_futures.append(executor.submit(download_film, game_info['film_name'], output_path))

        for f in as_completed(dl_futures):
            (film_name, film_url, film_output) = f.result()
            if film_url and DEBUG:
                print(f'Downloaded {film_name}')

        print('All downloaded')

def tourney_slug(tourney_id, tourney_short_name):
    return f'{tourney_id}-{tourney_short_name}'

def round_slug(round_id, round_name):
    return f'{round_id}-{utils.slugify(round_name)}'

def game_slug(game_num, game_map):
    return f'{game_num}-{utils.slugify(game_map)}'

def game_dir(tourney_id, tourney_short_name, round_id, round_name, game_num, game_map):
    return (
        f'tournament/{tourney_slug(tourney_id, tourney_short_name)}/'
        f'rounds/{round_slug(round_id, round_name)}/'
        f'games/{game_slug(game_num, game_map)}'
    )

def prompt(prompt_path, round_count, film_count):
    # return True
    response = input(f"Download {round_count}x rounds - {film_count}x films to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <tourney_id> [<output_dir>]")
        sys.exit(1)
    
    tourney_id = sys.argv[1]
    if len(sys.argv) == 3:
        output_dir = sys.argv[2]
    else:
        output_dir = None
    
    try:
        main(tourney_id, output_dir)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
