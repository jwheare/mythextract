#!/usr/bin/env python3
from collections import OrderedDict
import json
import os
import pathlib
import sys

import reco_tag
import myth_collection
import tag2png

DEBUG = (os.environ.get('DEBUG') == '1')

# MWC25 specific
CAPTAIN_TEAMS = {
    11: "spy kids",
    26: "ag",
    31: "d&t",
    34: "spy kids",
    38: "tmf",
    41: "mit",
    44: "z snake",
    47: "spy kids",
    51: "z snake",
    52: "spy kids",
    54: "ag",
    59: "spy kids",
    68: "spy kids",
    96: "tmf",
    150: "ag",
    210: "tmf",
    252: "tmf",
    283: "pk",
    338: "tmf",
    342: "pk"
}
FORFEIT_WINNERS = {
    43: ['tmf', 5],
    48: ['ag', 5],
}
ROUND_MAP = OrderedDict([
    ('QR1', 'Qualifying Round 1'),
    ('QR2', 'Qualifying Round 2'),
    ('QR3', 'Qualifying Round 3'),
    ('DE1', 'Double Elimination 1'),
    ('DE2', 'Double Elimination 2'),
    ('DE3', 'Double Elimination 3'),
    ('BB Finals', 'Bottom Bracket Finals'),
    ('Grand Finals', 'Grand Finals'),
])
TEAM_MAP = {
    'ag': ['AG', "Avon's Grove"],
    'd&t': ['D&T', "Death & Taxes"],
    'ma': ['MA', "Marmotas Assassinas"],
    'mit': ['MiT', "Men in Tights"],
    'pk': ['PK', "Peacekeepers"],
    'spy kids': ['SK', "Spy Kids"],
    'tmf': ['TMF', "The Myth-Fits"],
    'z snake': ['ZS', "Z Snake"],
}

def main(tourney_dir, game_directory, output_dir):
    """
    Parse downloaded films from a tournament into stats json
    """

    tourney_path = pathlib.Path(tourney_dir)
    tourney_info_file = tourney_path / 'info.json'
    try:
        with open(tourney_info_file, 'r') as t_info_file:
            tourney_info = json.load(t_info_file)
    except FileNotFoundError:
        print('No tourney info file')
        sys.exit(1)

    tourney_name = tourney_info['name']
    tourney_short_name = tourney_info['short_name']
    tourney_start = tourney_info['start']
    print(f"Tournament: {tourney_name} ({tourney_info['bagrada_tournament']})")
    print(f"Short name: {tourney_short_name}")
    print(f"Start date: {tourney_start}")

    if 'rounds' not in tourney_info:
        print('No round info')
        sys.exit(1)

    if not output_dir:
        base_path = tourney_path.parent.parent
    else:
        base_path = pathlib.Path(output_dir)
    
    tourney_rounds = tourney_info['rounds']
    tourney_info_data = {
        k: v for k, v in tourney_info.items() if k not in ['rounds']
    }

    if prompt(base_path, tourney_path, len(tourney_rounds)):
        for round_i, round_info in enumerate(tourney_info['rounds']):
            winning_teams = None
            # Relies on tourney specific data
            if round_info.get('_processed'):
                winning_teams = {}
                winning_teams[round_info['team1']] = 0
                winning_teams[round_info['team2']] = 0

            print(winning_teams)

            if not len(round_info['games']):
                if winning_teams:
                    forfeit_winner = FORFEIT_WINNERS[round_info['bagrada_round']]
                    winning_teams[forfeit_winner[0]] = forfeit_winner[1]
                    round_info['forfeit'] = (
                        round_info['team1'] if forfeit_winner[0] == round_info['team2'] else round_info['team2']
                    )
            for game_info in round_info['games']:
                game_dir = base_path / game_info['game_path']
                film_name = game_info['film_name']
                reco_file = game_dir / film_name
                print(
                    f'{(round_i+1):>2}/{len(tourney_rounds)}: round_id={round_info['bagrada_round']} '
                    f'game {game_info['game_num']} ({game_info['bagrada_game']}): '
                    f'{game_info["game_path"]}/{film_name} ... ', end=''
                )
                (
                    reco_header, players, players_idx, monsters, teams, teams_idx,
                    plugins, mesh_header, level_name, game_time, game_type_choice, difficulty,
                    overhead_map_data, chat_lines, trades, splits, game_stats
                ) = reco_tag.parse_reco_file(game_directory, reco_file)

                print('PARSED... ', end='')

                # Add path, tourney, round and film info to game_stats
                stats_game = game_stats['header']['game']
                stats_game['game_num'] = game_info['game_num']
                stats_game['game_path'] = game_info['game_path']
                stats_game['film_name'] = game_info['film_name']
                game_stats['header']['tournament'] = tourney_info_data
                game_stats['header']['round'] = round_info

                # Re-index teams header by tourney team slugs
                game_stats['header']['teams'] = {
                    # Relies on tourney specific data
                    CAPTAIN_TEAMS[team_data['captain']['bagrada_player']]: team_data | {
                        'team_index': team_index
                    }
                    for team_index, team_data in game_stats['header']['teams'].items()
                }

                reco_stats_out_path = game_dir / 'stats.json'
                pathlib.Path(reco_stats_out_path.parent).mkdir(parents=True, exist_ok=True)
                with open(reco_stats_out_path, 'w') as reco_stats_out_file:
                    json.dump(game_stats, reco_stats_out_file, separators=(',', ':'))

                print('STATS... ', end='')

                # Extract overhead map
                overhead_bitmaps = myth_collection.parse_sequence_bitmaps(overhead_map_data)
                if len(overhead_bitmaps):
                    (
                        overhead_name, overhead_width, overhead_height, overhead_rows
                    ) = overhead_bitmaps[0]['bitmaps'][0]
                    png = tag2png.make_png(overhead_width, overhead_height, overhead_rows)
                    overhead_out_path = game_dir / 'overhead.png'
                    with open(overhead_out_path, 'wb') as png_file:
                        png_file.write(png)

                print('MAP... ', end='')

                # game_info written to stats, now add extra info from
                # game_stats/stats_game into game_info. this gets saved
                # into the round_info and tourney_info dicts which are
                # written out after these loops

                # winning team info
                if 'tie' in stats_game:
                    game_info['tie'] = stats_game['tie']
                if 'host' in stats_game:
                    game_info['host'] = stats_game['host']
                if 'tie_teams' in stats_game:
                    game_info['tie_teams'] = [
                        tie_t['captain']['bagrada_player']
                        for tie_t in stats_game['tie_teams']
                    ]
                if 'winning_bagrada_captain' in stats_game:
                    if winning_teams:
                        winning_team = CAPTAIN_TEAMS[stats_game['winning_bagrada_captain']]
                        winning_teams[winning_team] += 1
                        game_info['winning_team'] = winning_team

                # teams and players info
                teams_info = {
                    # Relies on tourney specific data
                    CAPTAIN_TEAMS[team_data['captain']['bagrada_player']]: {
                        tk: tv
                        for tk, tv in team_data.items() if tk in [
                            'name',
                            'stats',
                            'color',
                            'tied_winner',
                            'winner',
                            'eliminated',
                            'place',
                            'place_tie',
                        ]
                    } | {
                        'captain_name': team_data['captain']['name'],
                        'players': {
                            player_data['bagrada_player']: {
                                pk: pv
                                for pk, pv in player_data.items() if pk in [
                                    'name',
                                    'stats',
                                    'color',
                                    'medals',
                                    'captain',
                                ]
                            }
                            for player_id, player_data in team_data['players'].items()
                        }
                    } for team_index, team_data in game_stats['header']['teams'].items()
                }
                game_info['teams'] = teams_info

                print('DONE')

            # Relies on tourney specific data
            if winning_teams:
                if winning_teams[round_info['team1']] > winning_teams[round_info['team2']]:
                    round_winner = round_info['team1']
                elif winning_teams[round_info['team2']] > winning_teams[round_info['team1']]:
                    round_winner = round_info['team2']
                round_info['winning_teams'] = winning_teams
                round_info['round_winner'] = round_winner

            # Write updated round_info to file
            round_info_path = base_path / round_info['round_path']
            round_info_file = round_info_path / 'info.json'

            with open(round_info_file, 'w') as r_info_file:
                json.dump(round_info | {'tournament': tourney_info_data}, r_info_file, separators=(',', ':'))

        print('All stats generated')

        # Write updated tourney_info to file
        with open(tourney_info_file, 'w') as t_info_file:
            json.dump(tourney_info, t_info_file, separators=(',', ':'))

def prompt(prompt_path, tourney_path, round_count):
    # return True
    response = input(
        f"Generate stats for {round_count}x rounds in: {prompt_path} ({tourney_path}/...) [Y/n]: "
    ).strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <tourney_dir> <game_directory> [<output_dir>]")
        sys.exit(1)
    
    tourney_dir = sys.argv[1]
    game_directory = sys.argv[2]
    if len(sys.argv) > 3:
        output_dir = sys.argv[3]
    else:
        output_dir = None
    
    try:
        main(tourney_dir, game_directory, output_dir)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
