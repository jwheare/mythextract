#!/usr/bin/env python3

import urllib.request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser
import os
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import pathlib

import utils

executor = ThreadPoolExecutor(max_workers=10)

DEBUG = (os.environ.get('DEBUG') == '1')
DEBUG_CACHED = (os.environ.get('DEBUG_CACHED') == '1')
DEBUG_GAME = (os.environ.get('DEBUG_GAME') == '1')
DEBUG_ROUND = (os.environ.get('DEBUG_ROUND') == '1')
DEBUG_UID = (os.environ.get('DEBUG_UID') == '1')

def main(output_dir, tourney_id):
    if not output_dir:
        output_dir = '../output/gos_cache/'
    cache_path = pathlib.Path(sys.path[0], output_dir).resolve()

    if tourney_id:
        download_tourney(tourney_id, cache_path)
    else:
        tourney_list_html = load_html('tournaments', cache_path)
        tourney_list_parser = GosTourneyListParser()
        tourney_list_parser.feed(tourney_list_html)

        tourney_list_info_file = cache_path / 'info.json'
        if prompt(cache_path, len(tourney_list_parser.tourneys)):
            pathlib.Path(cache_path).mkdir(parents=True, exist_ok=True)
            if tourney_list_info_file.is_file():
                print(f"Tourney list info exists at {tourney_list_info_file}")
            else:
                with open(tourney_list_info_file, 'w') as tl_info_file:
                    json.dump(tourney_list_parser.tourneys, tl_info_file, indent=2)
                if DEBUG:
                    print(f"Tourney list info saved to {tourney_list_info_file}")

            for tourney_data in tourney_list_parser.tourneys:
                download_tourney(tourney_data['metaserver_tournament'], cache_path)

            print('All downloaded')

def download_tourney(tourney_id, cache_path):
    tourney_url = f'tournaments/{urllib.parse.quote(tourney_id)}'
    tourney_html = load_html(tourney_url, cache_path)
    tourney_parser = GosTourneyParser(tourney_id)
    tourney_parser.feed(tourney_html)
    tourney_info_data = tourney_parser.data

    if DEBUG:
        print(
            'Tournament', tourney_id, tourney_info_data['start'],
            tourney_info_data['short_name'], tourney_info_data['name'], 
        )

    round_futures = []
    round_games = {}
    for round_data in tourney_info_data['rounds']:
        if round_data['num_games'] > 200:
            print(
                f"! Skipping. Too Many games: {round_data['num_games']} "
                f"tourney_id={tourney_id} round={round_data['metaserver_round']}"
            )
        else:
            if DEBUG_ROUND:
                print(
                    'Round', tourney_id, round_data['metaserver_round'], round_data['round_name'],
                    f'num_games={round_data['num_games']}'
                )
            round_futures.append(executor.submit(parse_round, tourney_id, round_data['metaserver_round'], cache_path))

    game_count = 0
    for f in as_completed(round_futures):
        round_result = f.result()
        game_count += len(round_result.games)
        round_games[round_result.round_id] = round_result.games

    dl_futures = []
    game_futures = []
    # Make sure we use the original rounds order
    for round_info in tourney_info_data['rounds']:
        # Download films for each game in the round
        for game_info in round_games.get(round_info['metaserver_round'], []):
            game_futures.append(executor.submit(
                parse_game,
                tourney_id, round_info['metaserver_round'], game_info['metaserver_game'],
                cache_path
            ))
            dl_futures.append(executor.submit(
                download_film,
                tourney_url,  round_info['metaserver_round'],
                game_info, cache_path
            ))

    for f in as_completed(dl_futures):
        f_res = f.result()
        if not f_res:
            sys.exit(1)

        (film_name, film_url, film_output, film_size, game_id) = f_res
        if film_name:
            if DEBUG:
                if film_url != 'cached' or DEBUG_CACHED:
                    print(f'Downloaded {film_url} ({film_size}) -> {film_output}')

def prompt(prompt_path, tourney_count):
    # return True
    response = input(f"Download {tourney_count}x tournaments to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def download_film(tourney_url, round_id, game_info, cache_path):
    redirect_url = f'{tourney_url}/rounds/{round_id}/games/{game_info['metaserver_game']}/download'
    output_dir = cache_path / redirect_url
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    saved_films = list(output_dir.glob('*.m2rec'))
    if len(saved_films) == 1:
        cached_film = saved_films[0]
        cached_size = cached_film.stat().st_size
        if cached_size > 5000:
            return (cached_film.name, 'cached', cached_film, cached_size, game_info['metaserver_game'])
        else:
            print('Corrupt cache', cached_film, cached_size)
    elif len(saved_films):
        print(f'More than one film found in {output_dir}')
        for f in saved_films:
            print(f.name)
        return False
    try:
        with urllib.request.urlopen(f'http://gateofstorms.net/{redirect_url}') as response:
            film_url = response.url
            film_name = os.path.basename(film_url)
            output_path = (output_dir / film_name).with_suffix('.m2rec')
            with open(output_path, "wb") as f:
                written = f.write(response.read())
            return (film_name, film_url, output_path, written, game_info['metaserver_game'])
    except HTTPError as e:
        print(f"HTTP error for {redirect_url}: {e.code} {e.reason}")
    except URLError as e:
        print(f"Failed to reach {redirect_url}: {e.reason}")
    except Exception as e:
        print(f"Unexpected error downloading {redirect_url}: {e}")

    return False

def parse_round(tourney_id, round_id, cache_path):
    round_url = f'tournaments/{urllib.parse.quote(tourney_id)}/rounds/{round_id}'
    round_html = load_html(round_url, cache_path)
    round_parser = GosRoundParser(round_id)
    round_parser.feed(round_html)
    return round_parser

def parse_game(tourney_id, round_id, game_id, cache_path):
    round_url = f'tournaments/{urllib.parse.quote(tourney_id)}/rounds/{round_id}'
    game_url = f'{round_url}/games/{game_id}'
    game_html = load_html(game_url, cache_path)
    game_parser = GosGameParser(game_id)
    game_parser.feed(game_html)
    return game_parser

# http://gateofstorms.net/tournaments/
class GosTourneyListParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tourneys = []

        self.in_tourney_list = False
        self.in_tourney_item = False
        self.current_tourney = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == 'ul' and attr_dict.get('class') == 'tournaments':
            self.in_tourney_list = True
        elif tag == 'a' and self.in_tourney_list:
            self.in_tourney_item = True
            self.current_tourney = {'metaserver_tournament': attr_dict.get('href').strip('/')}

    def handle_endtag(self, tag):
        if tag == 'ul':
            self.in_tourney_list = False
        elif tag == 'a' and self.in_tourney_item:
            self.tourneys.append(self.current_tourney)
            self.in_tourney_item = False

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self.in_tourney_item:
            [tourney_start, tourney_name] = text.split(' - ', 1)
            self.current_tourney['start'] = tourney_start
            self.current_tourney['name'] = tourney_name

# http://gateofstorms.net/tournaments/MWC2024/
class GosTourneyParser(HTMLParser):
    def __init__(self, tourney_id):
        super().__init__()
        self.tourney_id = tourney_id
        self.data = {
            'metaserver': 'gos',
            'metaserver_tournament': tourney_id,
            'short_name': tourney_id,
            'name': None, # get from h1 tag
            'start': None, # get from first round
            'rounds': [],
        }

        self.in_name = False
        self.in_round_table = False
        self.current_row = []
        self.column = 0
        self.in_td = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == 'h1':
            self.in_name = True
        elif tag == 'table' and 'class' not in attr_dict:
            self.in_round_table = True
        elif tag == 'tr':
            self.current_row = []
            self.column = 0
        elif tag == 'td':
            self.in_td = True
        elif tag == 'a' and self.in_round_table:
            self.current_row.append(attr_dict['href'])

    def handle_endtag(self, tag):
        if tag == 'h1':
            self.in_name = False
        elif tag == 'table' and self.in_round_table:
            self.in_round_table = False
        elif tag == 'td':
            self.in_td = False
            self.column += 1
        elif tag == 'tr':
            if len(self.current_row) != 4:
                return
            round_match = re.match(r'^/tournaments/[^/]+/rounds/(\d+)', self.current_row[1])
            if not round_match:
                print('No round match', self.current_row)
                return
            round_id = round_match.group(1)
            if not len(self.data['rounds']):
                self.data['start'] = self.current_row[0]
            self.data['rounds'].append({
                'metaserver_round': int(round_id),
                'round_name': self.current_row[2],
                'games': [],
                'num_games': int(self.current_row[3])
            })

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self.in_name:
            self.data['name'] = text
        elif self.in_round_table and self.in_td:
            self.current_row.append(text)

# http://gateofstorms.net/tournaments/MWC2024/rounds/1003/
class GosRoundParser(HTMLParser):
    def __init__(self, round_id):
        super().__init__()
        self.round_id = round_id
        self.games = []

        self.in_game_table = False
        self.current_row = []
        self.column = 0
        self.in_td = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == 'table' and 'class' not in attr_dict:
            self.in_game_table = True
        elif tag == 'tr':
            self.current_row = []
            self.column = 0
        elif tag == 'td':
            self.in_td = True
        elif tag == 'a' and self.in_game_table:
            self.current_row.append(attr_dict['href'])

    def handle_endtag(self, tag):
        if tag == 'table' and self.in_game_table:
            self.in_game_table = False
        elif tag == 'td':
            self.in_td = False
            self.column += 1
        elif tag == 'tr':
            if len(self.current_row) != 7:
                return
            game_match = re.match(r'^/tournaments/[^/]+/rounds/\d+/games/(\d+)', self.current_row[1])
            if not game_match:
                print('No game match', self.current_row)
                return
            game_id = game_match.group(1)
            (game_type, game_map) = process_game_name(self.current_row[2])
            game_num = len(self.games) + 1
            if DEBUG_GAME:
                print(f'[{game_id}] {game_num}) {game_type}: {game_map}')
            self.games.append({
                'game_num': game_num,
                'metaserver_game': int(game_id),
                'game_type': game_type,
                'map_name': utils.strip_format(game_map),
                # populated from location header when downloading film
                'film_name': None,
                # populated in tourney2stats.py
                'game_name': None,
                'time_limit': None,
                'difficulty': None,
            })

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        elif self.in_game_table and self.in_td:
            self.current_row.append(text)

# Used in reco_tag
class GosGameParser(HTMLParser):
    def __init__(self, game_id):
        super().__init__()
        self.game_id = game_id
        self.teams = []
        self.spectators = []
        self.host = None
        self.start = None
        self.duration = None

        self.in_stats_table = False
        self.current_row = {}
        self.current_team = None
        self.column = 0
        self.in_td = False
        self.in_team_header = False
        self.in_p = False
        self.in_spectators = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == 'table' and attr_dict.get('class') == 'game':
            self.in_stats_table = True
        elif tag == 'tr':
            self.current_row = {}
            self.column = 0
            if 'team_header' in attr_dict.get('class', '').split(' '):
                if self.current_team:
                    self.teams.append(self.current_team)
                self.in_team_header = True
        elif tag == 'td':
            self.in_td = True
        elif tag == 'a' and self.in_stats_table:
            self.current_row['link'] = attr_dict['href']
        elif tag == 'p':
            self.in_p = True

    def handle_endtag(self, tag):
        if tag == 'table' and self.in_stats_table:
            if self.current_team:
                self.teams.append(self.current_team)
            self.in_stats_table = False
        elif tag == 'td':
            self.in_td = False
            self.column += 1
        elif tag == 'tr':
            if 7 not in self.current_row:
                if (
                    len(self.current_row) == 2 and
                    self.current_row.get(0) == '-' and
                    self.current_row.get(1) == 'Spectators'
                ):
                    self.in_spectators = True
                elif (
                    self.in_spectators and
                    len(self.current_row) <= 2 and
                    'link' in self.current_row
                ):
                    user_id = self.parse_uid(self.current_row['link'])
                    self.spectators.append({
                        'name': self.current_row.get(1, ''),
                        'metaserver_player': user_id
                    })
            else:
                row_data = {
                    'name': self.current_row.get(1, ''),
                    'killed': self.current_row[2],
                    'lost': self.current_row[3],
                    'kill_ratio': self.current_row[4],
                    'dmg_given': self.current_row[5],
                    'dmg_taken': self.current_row[6],
                    'dmg_ratio': self.current_row[7],
                }
                if self.current_row.get(8):
                    row_data['status'] = self.current_row.get(8)
                if self.in_team_header:
                    row_data['place'] = self.current_row[0]
                    row_data['players'] = []
                    self.current_team = row_data
                    self.in_team_header = False
                else:
                    user_id = None
                    if 'link' in self.current_row:
                        user_id = self.parse_uid(self.current_row['link'])
                    if user_id:
                        row_data['metaserver_player'] = int(user_id)
                    else:
                        if DEBUG_UID:
                            print('No uid match', self.current_row)
                    
                    self.current_team['players'].append(row_data)
        elif tag == 'p':
            self.in_p = False

    def parse_uid(self, value):
        uid_match = re.match(r'^/users/(\d+)', value)
        if uid_match:
           return uid_match.group(1)

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self.in_stats_table and self.in_td:
            self.current_row[self.column] = text
        elif self.in_p:
            host_match = re.match(r'Hosted by (.*)', text)
            if host_match:
                self.host = host_match.group(1)
            time_match = re.match(r'\s*Began at (.*) and lasted for (.*)', text)
            if time_match:
                self.start = time_match.group(1)
                self.duration = time_match.group(2)

def process_game_name(game_name):
    name_lower = game_name.lower()
    lower_starts = [
        'last man on the hill',
        'balls on parade'
    ]
    for start in lower_starts:
        if name_lower.startswith(start):
            return (
                game_name[:len(start)],
                game_name[len(start)+4:]
            )
    return tuple(re.split(r' on ', game_name, maxsplit=1, flags=re.IGNORECASE))

# Load from URL
def load_html(url, cache_dir):
    cache_path = cache_dir / url / 'index.html'
    if cache_path.is_file():
        with open(cache_path, 'r') as cached_file:
            if DEBUG_CACHED:
                print('CACHED', cache_path)
            return cached_file.read()
    else:
        (status, headers, response) = utils.http_request(f'http://gateofstorms.net/{url}')
        pathlib.Path(cache_path.parent).mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w') as cache_file:
            if DEBUG:
                print('CACHE', cache_path)
            cache_file.write(response)
    return response

if __name__ == "__main__":
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = None

    tourney_id = None
    if len(sys.argv) > 2:
        tourney_id = sys.argv[2]
    
    try:
        main(output_dir, tourney_id)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
