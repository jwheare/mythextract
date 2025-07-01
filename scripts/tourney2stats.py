#!/usr/bin/env python3
import json
import os
import pathlib
import sys

import reco_tag

DEBUG = (os.environ.get('DEBUG') == '1')

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
        path = tourney_path
    else:
        path = pathlib.Path(output_dir)

    round_info = tourney_info['rounds']

    if prompt(path, len(round_info)):
        for round_i, round_info in enumerate(tourney_info['rounds']):
            for game_info in round_info['games']:
                game_dir = pathlib.Path(game_info['game_path'])
                if path.name == tourney_info['path']:
                    game_dir = (path.parent / game_dir).resolve()
                film_name = game_info['film_name']
                reco_file = game_dir / film_name
                print(
                    f'{round_i:>2}) Round {round_info['bagrada_round']} '
                    f'game {game_info['game_num']} ({game_info['bagrada_game']}): '
                    f'{game_info["game_path"]}/{film_name} ... ', end=''
                )
                (
                    reco_header, players, players_idx, monsters, teams, teams_idx,
                    plugins, mesh_header, level_name, game_time, game_type_choice, difficulty,
                    chat_lines, command_counts, trades, splits, metaserver_stats, command_log
                ) = reco_tag.parse_reco_file(game_directory, reco_file)

                print('PARSED... ', end='')

                command_log['header']['game']['game_num'] = game_info['game_num']
                command_log['header']['tournament'] = {k: v for k, v in tourney_info.items() if k not in ['rounds']}
                command_log['header']['round'] = round_info
                if metaserver_stats and 'processed' in metaserver_stats:
                    command_log['team_stats'] = metaserver_stats['processed']['teams']

                reco_stats_out_path = game_dir / 'stats.json'
                pathlib.Path(reco_stats_out_path.parent).mkdir(parents=True, exist_ok=True)
                with open(reco_stats_out_path, 'w') as reco_stats_out_file:
                    json.dump(command_log, reco_stats_out_file, separators=(',', ':'))

                print('DONE')

        print('All stats generated')


def prompt(prompt_path, round_count):
    # return True
    response = input(f"Generate stats for {round_count}x rounds in: {prompt_path} [Y/n]: ").strip().lower()
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
