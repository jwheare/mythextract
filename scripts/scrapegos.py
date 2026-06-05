#!/usr/bin/env python3

import urllib.request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser
import os
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import shutil
import pathlib

import recording_stats
import utils

executor = ThreadPoolExecutor(max_workers=10)

DEBUG = (os.environ.get('DEBUG') == '1')
DEBUG_CACHED = (os.environ.get('DEBUG_CACHED') == '1')

CACHE_DIR = pathlib.Path(sys.path[0], '../output/gos_cache/').resolve()

BAD_GAMES = [
    # MWC2018
    (693, 235427), # spurious coop game tournaments/MWC2018/rounds/693
    (679, 230844), # misattributed dupe of tournaments/MWC2018/rounds/681/games/230844/
    (675, 228908), # restarted tournaments/MWC2018/rounds/675/games/228911/
]
BAD_ROUNDS = [
    # misnamed dupe of tournaments/MWC2018/rounds/682/
    678,
]

MISSING_ROUNDS = {
    'MWC2020': {
        'before': 763,
        'stage': 'QR3',
    },
}

METASERVER_IDS = {
    'Doyee5 ^freeagent^': 2325,
    'Texas Pete     |i  sauce': 70718,
    'monty': 70621,
    'YOLO': 2103,
    'khan              |ic⁄√inja': 71698,
    '|bC |ir u n i a c    |b  BME': 154,
    '|bS|icratch': 69,
    '|iKillerKing   ~sb~': 517,
    'Reekfish': 71428,
    '|ispy              ': 71258,
    '|F|i‹ cf ›  SpıceGırL': 71283,
    'Walter Wight     ‹SB›': 1407,
    'pallidice    ': 70670,
    'drunken -deer-': 70787,
    'Wulfsbane  ~deer~': 71163,
    '|bPHACE         ~∂eer~': 71630,
    'DagdA ~∂eer~': 70746,
    'RAFF': 1814,
    '|iSei Lah': 71656,
    '|bFidelix     « ⁄\\⁄\\ ⁄\\ »': 71200,
    'Empy Thyme -sb-': 71441,
    '|iV A S A Z E L ®': 70629,
}
METASERVER_ID_MAP = {
    '1073741865': 71175, # 'honkey'
    '1073741842': 71722, # '|iRamirez'
    '1073741856': 286, # 'Demolition'
    '1073741831': 71207, # 'sillek'
    '1073741832': 71718, # 'GENERALESXXX'
    '1073741840': 70625, # 'Pacer      ƒå'
    '1073741876': 70813, # 'Flatline110%hetero'
    '1073741852': 47860, # 'granis     ·ag·    |I|F|# ™'
    '1073741849': 71237, # 'valentine SR†'
    '1073741838': 71427, # 'EarthQuake •ag•'
    '1073741862': 70877, # 'Vigor'
    '1073741866': 71360, # ' .·bridgestone·tired·.'
    '1073741869': 1725, # '√\\JaHRaL †.ø.å.∂.√\\'
    '1073741863': 71180, # 'SiN'
}

def add_missing_rounds(tourney_info, outpath):
    seen_metaserver_ids = {}
    seen_metaserver_ids_used = {}
    bad_metaserver_ids = {}
    tourney_id = tourney_info['metaserver_tournament']
    if tourney_id in MISSING_ROUNDS:
        missing = MISSING_ROUNDS[tourney_id]
        if 'before' in missing:
            rounds = tourney_info['rounds']
            insert_before = len(rounds)
            for i, round_data in enumerate(rounds):
                if round_data['metaserver_round'] == missing['before']:
                    insert_before = i

            stage = missing['stage']
            missing_path = pathlib.Path(
                sys.path[0], '../input/missing_metaserver',
                tourney_id, stage
            ).resolve()
            round_paths = [p for p in missing_path.iterdir() if p.is_dir()]
            missing_rounds = []
            for r_path in sorted(round_paths):
                team_match = re.match(r'(\w+)_v_(\w+)', r_path.name)
                if team_match:
                    team1 = team_match.group(1)
                    team2 = team_match.group(2)
                    round_name = f"{stage}: {team1} vs {team2}"
                    r_slug = utils.slugify(round_name)
                    round_path = f'rounds/{r_slug}'
                    full_round_path = f"{tourney_info['path']}/{round_path}"
                    games = []
                    for game_num, stats_csv in enumerate(sorted(r_path.glob('*.csv')), 1):
                        film_path = stats_csv.with_suffix('.m2rec')
                        if not film_path.is_file():
                            print('Missing film for stats')
                            continue
                        parsed = recording_stats.parse_csv(stats_csv)
                        game_map = parsed['game_info']['Map']
                        game_type = parsed['game_info']['Type']
                        g_slug = game_slug(game_num, game_map)
                        game_path = (
                            f'{full_round_path}/'
                            f'games/{g_slug}'
                        )

                        film_destination = outpath / game_path
                        pathlib.Path(film_destination).mkdir(parents=True, exist_ok=True)
                        shutil.copy2(film_path, film_destination)
                        print(f'Copied {film_path} -> {film_destination}')

                        place_counts = {}
                        for parsed_team in parsed['team_stats']:
                            place = parsed_team['Place']
                            if place not in place_counts:
                                place_counts[place] = 0
                            place_counts[place] += 1

                        teams = []
                        for parsed_team in parsed['team_stats']:
                            players = []
                            for parsed_player in parsed['player_stats']:
                                if parsed_player['Team'] == parsed_team['Team']:
                                    metaserver_player = parsed_player['Metaserver ID']
                                    player_name = parsed_player['Name']
                                    if len(str(metaserver_player)) == 10:
                                        if player_name in METASERVER_IDS:
                                            metaserver_player = METASERVER_IDS[player_name]
                                        elif player_name in seen_metaserver_ids:
                                            if len(seen_metaserver_ids[player_name]) > 1:
                                                print('Bad metaserver id, multiple choice', metaserver_player, player_name, seen_metaserver_ids[player_name])
                                            else:
                                                seen_id = seen_metaserver_ids[player_name][0]
                                                seen_metaserver_ids_used[player_name] = (metaserver_player, seen_id)
                                                metaserver_player = seen_id
                                        else:
                                            print('Bad metaserver id', metaserver_player, player_name)
                                            if player_name not in bad_metaserver_ids:
                                                bad_metaserver_ids[player_name] = []
                                            if metaserver_player not in bad_metaserver_ids[player_name]:
                                                bad_metaserver_ids[player_name].append(metaserver_player)
                                    else:
                                        if player_name not in seen_metaserver_ids:
                                            seen_metaserver_ids[player_name] = []
                                        if metaserver_player not in seen_metaserver_ids[player_name]:
                                            seen_metaserver_ids[player_name].append(metaserver_player)
                                    players.append({
                                        # TODO fix bad metaserver_player_ids
                                        'playerIdx': parsed_player['Player'],
                                        'userId': metaserver_player,
                                        'nickName': player_name,
                                        'teamName': parsed_team['Name'],
                                        'unitsKilled': parsed_player['Kills'],
                                        'unitsLost': parsed_player['Deaths'],
                                        'unitsSurvived': parsed_player['Survived'],
                                        'damageGiven': parsed_player['Damage Dealt'],
                                        'damageTaken': parsed_player['Damage Taken'],
                                        'dropped': parsed_player['Dropped'] == 1,
                                    })

                            place = parsed_team['Place']
                            teams.append({
                                'teamName': parsed_team['Name'],
                                'players': players,
                                'place': place + 1,
                                'placeTie': place_counts[place] > 1,
                                'eliminated': parsed_team['Eliminated'] == 1,
                            })
                        stats = {
                            'metaserver': 'gos',
                            'teams': teams
                        }

                        games.append({
                            'game_num': game_num,
                            'game_type': game_type,
                            'map_name': utils.strip_format(game_map),
                            'game_path': game_path,
                            'game_slug': g_slug,
                            # populated from location header when downloading film
                            'film_name': film_path.name,
                            # prepopulate metaserver_stats
                            'metaserver_stats': stats,
                            # populated in tourney2stats.py
                            'game_name': None,
                            'time_limit': None,
                            'difficulty': None,
                        })

                    missing_rounds.append({
                        'round_name': round_name,
                        'round_path': full_round_path,
                        'round_slug': r_slug,
                        'games': games,
                        'stage': stage,
                        'team1': team1.lower(),
                        'team2': team2.lower(),
                        '_processed': True,
                    })

            for to_insert in reversed(missing_rounds):
                rounds.insert(insert_before, to_insert)
    if len(seen_metaserver_ids_used):
        print('Used seen metaserver ids')
        for name, m_id in seen_metaserver_ids_used.items():
            print(m_id, [name])
    if len(bad_metaserver_ids):
        print('Bad metaserver ids')
        for name, m_ids in bad_metaserver_ids.items():
            print(m_ids, [name])

def main(tourney_id, output_dir):
    tourney_url = f'tournaments/{urllib.parse.quote(tourney_id)}'
    tourney_html = load_html(tourney_url)
    tourney_parser = GosTourneyParser(tourney_id)
    tourney_parser.feed(tourney_html)
    tourney_info_data = tourney_parser.data

    round_futures = []
    round_games = {}
    for round_data in tourney_info_data['rounds']:
        round_futures.append(executor.submit(parse_round, tourney_id, round_data))

    game_count = 0
    for f in as_completed(round_futures):
        round_result = f.result()
        game_count += len(round_result.games)
        round_games[round_result.round_id] = round_result.games

    if not output_dir:
        output_dir = '../output/gos/'
    path = pathlib.Path(sys.path[0], output_dir).resolve()
    outpath = path / tourney_parser.tourney_path
    if prompt(outpath, len(tourney_info_data['rounds']), game_count):
        dl_futures = []
        # Make sure we use the original rounds order
        for round_info in tourney_info_data['rounds']:
            # Download films for each game in the round
            for game_info in round_games[round_info['metaserver_round']]:
                output_path = path / game_info['game_path']
                pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)
                dl_futures.append(executor.submit(
                    download_film,
                    tourney_url, round_info['metaserver_round'],
                    game_info, output_path
                ))

        game_films = {}
        for f in as_completed(dl_futures):
            f_res = f.result()
            if not f_res:
                sys.exit(1)

            (film_name, film_url, film_output, film_size, game_id) = f_res
            if film_name:
                game_films[game_id] = film_name
                if DEBUG:
                    print(f'Downloaded {film_url} ({film_size}) -> {film_output}')

        add_missing_rounds(tourney_info_data, path)

        for round_info in tourney_info_data['rounds']:
            if 'metaserver_round' in round_info:
                for game_info in round_games[round_info['metaserver_round']]:
                    if game_info['metaserver_game'] in game_films:
                        game_info['film_name'] = game_films[game_info['metaserver_game']]
                round_info['games'] = round_games[round_info['metaserver_round']]

            round_info_path = path / round_info['round_path']
            pathlib.Path(round_info_path).mkdir(parents=True, exist_ok=True)
            # Write the round info file
            round_info_file = round_info_path / 'info.json'
            with open(round_info_file, 'w') as r_info_file:
                json.dump(round_info | {'tournament': tourney_info_data}, r_info_file, indent=2)
            if DEBUG:
                print(f"Round info saved to {round_info_file}")

        pathlib.Path(outpath).mkdir(parents=True, exist_ok=True)
        # Write the tournament info file
        tourney_info_file = outpath / 'info.json'
        with open(tourney_info_file, 'w') as t_info_file:
            json.dump(tourney_info_data, t_info_file, indent=2)
        if DEBUG:
            print(f"Tournament info saved to {tourney_info_file}")

        print('All downloaded')

def prompt(prompt_path, round_count, game_count):
    # return True
    response = input(f"Download {round_count}x rounds - {game_count}x games to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def download_film(tourney_url, round_id, game_info, output_dir):
    # Check already saved
    saved_films = list(output_dir.glob('*.m2rec'))
    if len(saved_films) == 1:
        saved_film = saved_films[0]
        saved_size = saved_film.stat().st_size
        if saved_size > 10000:
            return (saved_film.name, 'saved', saved_film, saved_size, game_info['metaserver_game'])
        else:
            print('Corrupt cache', saved_film, saved_size)
    elif len(saved_films):
        print(f'More than one film found in {output_dir}')
        for f in saved_films:
            print(f.name)
        return False

    # Check CACHE_DIR
    redirect_url = f'{tourney_url}/rounds/{round_id}/games/{game_info['metaserver_game']}/download'
    cache_path = CACHE_DIR / redirect_url
    cached_films = list(cache_path.glob('*.m2rec'))
    if len(cached_films) == 1:
        cached_film = cached_films[0]
        cached_size = cached_film.stat().st_size
        shutil.copy2(cached_film, output_dir)
        return (cached_film.name, 'cached', cached_film, cached_size, game_info['metaserver_game'])
    elif len(cached_films):
        print(f'More than one film found in {cache_path}')
        for f in cached_films:
            print(f.name)
        return False

    # Download
    try:
        with urllib.request.urlopen(f'http://gateofstorms.net/{redirect_url}') as response:
            film_url = response.url
            film_name = os.path.basename(film_url)
            output_path = output_dir / film_name
            with open(output_dir / film_name, "wb") as f:
                written = f.write(response.read())
            return (film_name, film_url, output_path, written, game_info['metaserver_game'])
    except HTTPError as e:
        print(f"HTTP error for {film_url}: {e.code} {e.reason}")
    except URLError as e:
        print(f"Failed to reach {film_url}: {e.reason}")
    except Exception as e:
        print(f"Unexpected error downloading {film_url}: {e}")

    return False

def parse_round(tourney_id, round_data):
    round_id = round_data['metaserver_round']
    round_url = f'tournaments/{urllib.parse.quote(tourney_id)}/rounds/{round_id}'
    round_html = load_html(round_url)
    round_parser = GosRoundParser(round_id, round_data['round_path'])
    round_parser.feed(round_html)
    return round_parser

def parse_game(tourney_id, round_id, game_id):
    round_url = f'tournaments/{urllib.parse.quote(tourney_id)}/rounds/{round_id}'
    game_url = f'{round_url}/games/{game_id}'
    game_html = load_html(game_url)
    game_parser = GosGameParser(game_id)
    game_parser.feed(game_html)
    return game_parser


# http://gateofstorms.net/tournaments/MWC2024/
class GosTourneyParser(HTMLParser):
    def __init__(self, tourney_id):
        super().__init__()
        self.tourney_id = tourney_id
        tourney_slug = f'gos-{re.sub(' ', '', tourney_id).lower()}'
        self.tourney_path = f'tournament/{tourney_slug}'
        self.data = {
            'metaserver': 'gos',
            'metaserver_tournament': tourney_id,
            'short_name': tourney_id,
            'slug': tourney_slug,
            'path': self.tourney_path,
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
            round_id = int(round_match.group(1))
            round_name, extra_round_data = process_round_name(self.tourney_id, self.current_row[2])
            r_slug = round_slug(round_id, round_name)
            round_path = f'rounds/{r_slug}'

            if round_id not in BAD_ROUNDS:
                if DEBUG:
                    print(
                        round_name, r_slug,
                        [extra_round_data.get('stage'), extra_round_data.get('team1'), extra_round_data.get('team2')]
                    )
                if not len(self.data['rounds']):
                    # TODO convert to iso
                    self.data['start'] = self.current_row[0]
                self.data['rounds'].append({
                    'metaserver_round': round_id,
                    'round_name': round_name,
                    'round_path': f'{self.tourney_path}/{round_path}',
                    'round_slug': r_slug,
                    'games': [],
                } | extra_round_data)

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
    def __init__(self, round_id, round_path):
        super().__init__()
        self.round_path = round_path
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
            game_id = int(game_match.group(1))
            (game_type, game_map) = process_game_name(self.current_row[2])
            game_num = len(self.games) + 1
            g_slug = game_slug(game_num, game_map)
            if (self.round_id, game_id) not in BAD_GAMES:
                if DEBUG:
                    print(f'[{game_id}] {game_num}) {game_type}: {game_map} ({g_slug})')
                self.games.append({
                    'game_num': game_num,
                    'metaserver_game': game_id,
                    'game_type': game_type,
                    'map_name': utils.strip_format(game_map),
                    'game_path': (
                        f'{self.round_path}/'
                        f'games/{g_slug}'
                    ),
                    'game_slug': g_slug,
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


def process_round_name(tourney_id, round_name):
    team_map = None
    team1 = None
    team2 = None

    if tourney_id == 'MWC2013':
        team_map = {
            'ulms': ['ulms', 'Until Last Man Stands'],
            'blades': ['blades', 'Blades'],
            'the blades': ['blades', 'Blades'],
            'tcox': ['tcox', 'ThunderCox'],
            'dr': ['dr', "Devil's Rejects"],
            'agents': ['agents', 'Agents'],
            'tmns': ['tmns', 'Teenage Mutant Ninja Squirters'],
            'tmnt': ['tmnt', 'Teenage Mutant Ninja Turtles'],
            'zomg': ['zomg', 'ZOMG'],
            'deer': ['deer', 'Deer'],
            'wtc': ['wtc', 'Wu Tang Clan'],
        }
        if match := re.match(r'(.+) - (.+) vs (.+)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            if stage == 'BBF':
                stage = 'BB Finals'
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2014':
        team_map = {
            'bros': ['bros', 'The Bros'],
            'fellowship': ['fotb', 'Fellowship of the Bling'],
            'gentlemen': ['gents', 'The Gentlemen'],
            'teabaggers': ['tea', 'Teabaggers'],
            'team fx': ['tea', 'Teabaggers'],
            'ulms': ['ulms', 'Until Last Man Stands'],
            'underdogs': ['udogs', 'Underdogs'],
        }
        if match := re.match(r'(.+) - (.+) vs (.+)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2015':
        team_map = {
            'deer': ['deer', 'Deer'],
            'mom': ['mom', 'Masters of Myth'],
            'ncr': ['ncr', 'Namechangers Resurrection'],
            'owls': ['owls', 'Sociopathic Owls'],
            'rabble(ncr/tmnt)': ['rabble', 'Rabble (NCR/TMNT)'],
            'tmnt2': ['tmnt2', 'Teenage Mutant Ninja Turtles 2'],
        }
        if match := re.match(r'(.*) ([^ ]+) vs ([^ ]+)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            if stage == 'DE 3 BB Finals':
                stage = 'BB Finals'
            if stage == 'MWC finals':
                stage = 'Grand Finals'
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2016':
        team_map = {
            'ageha': ['ageha', 'Ageha'],
            'boom town': ['boom', 'Boom Town'],
            'gom': ['gom', 'Gods of Myth'],
            'gods of myth': ['gom', 'Gods of Myth'],
            'noobs inc': ['noobs', 'Noobs Inc'],
            'por': ['por', 'Prophets of Rage'],
            'prophets of rage': ['por', 'Prophets of Rage'],
            'syn': ['syn', 'The Syndicate'],
            'the syndicate': ['syn', 'The Syndicate'],
            'tinh': ['tinh', 'Team Insert Name Here'],
            'team insert': ['tinh', 'Team Insert Name Here'],
            'twf': ['twf', 'The Wight Foundation'],
        }
        if match := re.match(r'(.*) - (.*) vs? (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            if stage == 'BBF':
                stage = 'BB Finals'
            if stage == 'DE1' and team1 == 'Team Insert' and team2 == 'PoR':
                team2 = 'GoM'
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2017':
        team_map = {
            'berserkers': ['bers', 'Berserkers'],
            'da': ['da', 'Dragon Army'],
            'lom': ['lom', 'Legends of Myth'],
            'roflmazzers': ['rofl', 'ROFLmazzers'],
        }
        if match := re.match(r'(.*) - (.*) vs\.? (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2018':
        team_map = {
            '7l': ['7l', '7th Legion'],
            'bkbk': ['bkbk', "Baron Kildaer's Black Knights"],
            'lh': ['lh', 'Legendary Heterosexuals'],
            'sdm': ['sdm', 'Slong D0ng McKong'],
            'smd': ['sdm', 'Slong D0ng McKong'],
            'tcl': ['tcl', 'The Casket Lottery'],
            'tgp': ['tgp', 'Team Good Players'],
            'tmnt': ['tmnt', 'Teenage Mutant Ninja Turtles'],
            'tmnt 3': ['tmnt', 'Teenage Mutant Ninja Turtles'],
            '~np~': ['np', 'Northern Paladins'],
            'np': ['np', 'Northern Paladins'],
        }
        if match := re.match(r'(.*?)[ ]*[:\-][ ]*(.*) vs (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            if stage == 'BBF':
                stage = 'BB Finals'
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC 2019':
        team_map = {
            'nc': ['nc', 'Namechangers'],
            'ftn': ['ftn', 'Fellowship of the Team Name'],
            'moc': ['moc', 'Murder of Crows'],
            'sb': ['sb', 'Spice Boys'],
        }
        if match := re.match(r'(.*) - (.*) vs (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            if stage.startswith('DE2'):
                stage = 'DE2'
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2020':
        team_map = {
            'ag': ['ag', 'Avons Grove'],
            'ba': ['ba', 'Business Associates'],
            'deer': ['deer', 'Deer'],
            'faf': ['faf', 'Free Agent Freedom'],
            'gagt': ['gagt', 'Good Ass Guys Team'],
            'hots': ['hots', 'HOTSquad'],
            'sb': ['sb', 'Spice Boiz II Men'],
            'mm': ['mm', 'The Mystery Men'],
        }
        stage, round_name = tuple(re.split(r' - ', round_name, maxsplit=1))
        round_parts = re.split(r' - ', round_name, maxsplit=1)
        if len(round_parts) == 2:
            if round_parts[0] == 'BB Finals':
                stage = round_parts[0]
            # stage += f' ({round_parts[0]})'
            round_name = round_parts[1]
        else:
            round_name = round_parts[0]
        if match := re.match(r'(.*) vs (.*)', round_name):
            team1 = match.group(1)
            team2 = match.group(2)
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2021':
        team_map = {
            'kotet': ['kotet', 'The Knights of the Elliptical Table'],
            'nato': ['sm', 'Sparkle Motion'],
            'sm': ['sm', 'Sparkle Motion'],
            'b4': ['b4', 'Bridge Four'],
            'ic': ['ic', 'Team Icecream'],
            'ag:td': ['ag', 'Avons Grove'],
            'ag': ['ag', 'Avons Grove'],
            'dc': ['dc', 'The Dunshire Coneheads'],
        }
        if match := re.match(r'(.*) - (.*) vs (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2022':
        team_map = {
            'ag': ['ag', 'Avons Grove'],
            'mit': ['mit', 'Men in Tights'],
            'rsc': ['rsc', 'Rat Sized Cats'],
            'sm': ['sm', 'Save Myth'],
        }
        if match := re.match(r'(.*) - (.*) vs (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            if stage == 'DE2 (TBF)':
                stage = 'DE2'
            if stage == 'DE3 (BBF)':
                stage = 'BB Finals'
            if stage == 'DE4 (Grand Finals)':
                stage = 'Grand Finals'
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2023':
        team_map = {
            'ag': ['ag', 'Avons Grove'],
            'mitt': ['mitt', 'Men in Tighter Tights'],
            'rsc': ['rsc', 'Rat Sized Cats'],
            'sm': ['sm', 'Save MWC WITH CAPS LOCK'],
            'tjn': ['tjn', 'The JuggerNots'],
        }
        if match := re.match(r'(.*) - (.*) vs (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            round_name = f'{stage}: {team1} vs {team2}'

    elif tourney_id == 'MWC2024':
        team_map = {
            'ag': ['ag', 'Avons Grove'],
            'b?mlm': ['bmlm', 'Boys? More Like Men'],
            'manbowski': ['man', 'The Big Manbowski'],
            'mit': ['miit', 'The Men In Impeccably Immaculate Tights'],
            'tl': ['tl', 'Treasure Island'],
            'tmf': ['tmf', 'The Myth-Fits'],
        }
        if match := re.match(r'((?:.*Finals)|(?:DE 2)|(?:DE2 BB)|\w+)\s(.*) vs (.*)', round_name):
            stage = match.group(1)
            team1 = match.group(2)
            team2 = match.group(3)
            if stage in ['DE 2', 'DE2 BB']:
                stage = 'DE2'
            round_name = f'{stage}: {team1} vs {team2}'

    if team1 and team2:
        return round_name, {
            'stage': stage,
            'team1': team_map[team1.lower()][0],
            'team2': team_map[team2.lower()][0],
            '_processed': True,
        }
    return round_name, {}

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

def round_slug(round_id, round_name):
    return f'{round_id}-{utils.slugify(round_name)}'

def game_slug(game_num, game_map):
    return f'{game_num}-{utils.slugify(game_map)}'

# Load from URL
def load_html(url):
    cache_path = CACHE_DIR / url / 'index.html'
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
