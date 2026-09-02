#!/usr/bin/env python3
import json
import os
import pathlib
import re
import sys
import math

import utils

DEBUG = (os.environ.get('DEBUG') == '1')
FILTER_PRINT = (os.environ.get('FILTER_PRINT') == '1')

def main(tourney_dir, output_path):
    """
    Parse chat from a tournament into stats json
    """
    tourney_path = pathlib.Path(tourney_dir)
    if not output_path:
        output_path = tourney_path / 'chat.json'

    tourney_info_file = tourney_path / 'info.json'
    try:
        with open(tourney_info_file, 'r') as t_info_file:
            tourney_info = json.load(t_info_file)
    except FileNotFoundError:
        print('No tourney info file', tourney_path.name)
        return

    if 'rounds' not in tourney_info:
        print('No round info', tourney_path.name)
        return
    
    for round_info in tourney_info['rounds']:
        for game_info in round_info['games']:
            game_info_file = tourney_path.parent.parent / f"{game_info['game_path']}/stats.json"
            with open(game_info_file, 'r') as g_info_file:
                game_full_info = json.load(g_info_file)
                game_header = game_full_info['header']['game']
                player_lookup = {}
                for t_slug, team in game_full_info['header']['teams'].items():
                    for p_id, player in team['players'].items():
                        player_lookup[int(p_id)] = {'player': player, 'team_slug': t_slug, 'team': team}
                for chat in game_full_info['chat']:
                    chat_norm = re.sub(r'\s', '', chat.get('message', '')).lower()
                    # if chat_norm.startswith('gg'):
                    # if chat_norm.startswith('gl'):
                    # if 'mid' in chat_norm:
                    if chat_norm and 'player' in chat:
                        pl = player_lookup[chat['player']]
                        pt = False
                        if chat['time'] < 0:
                            ticks = chat['time'] + game_header['planning_time']
                            pt = True
                        else:
                            ticks = chat['time']
                        mins = ticks / 30 / 60
                        mm = math.floor(mins)
                        ss = round((mins - mm) * 60)
                        print(
                            chat['time'] + game_header['planning_time'],
                            f"{'PT ' if pt else ''}{mm}:{ss:>02}",
                            '+' if pl['team'].get('winner') else '-',
                            'W' if chat.get('whisper') else 'Y',
                            utils.strip_order(utils.strip_format(pl['player']['name'])),
                            # chat_norm,
                            game_header['game_path'],
                            game_header['time_limit'], game_header['planning_time']
                        )

    # if prompt(output_path):
    #     with open(output_path, 'w') as output_json:
    #         json.dump(maps, output_json)

def prompt(output_path):
    # return True
    response = input(f"Write to {output_path}? [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <tourney_dir> [<output_path>]")
        sys.exit(1)
    
    tourney_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        output_path = None
    
    try:
        main(tourney_dir, output_path)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
