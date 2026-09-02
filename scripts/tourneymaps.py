#!/usr/bin/env python3
import json
import os
import pathlib
import re
import csv
import sys

import mesh2trades
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
TRADE = os.environ.get('TRADE')
FILTER_PRINT = (os.environ.get('FILTER_PRINT') == '1')

def main(tourneys_dir, output_path):
    """
    Parse maps from a tournament into stats json
    """
    tourneys_path = pathlib.Path(tourneys_dir)
    maps = {}
    if not output_path:
        output_path = tourneys_path / 'maps.json'

    csvwriter = csv.writer(sys.stdout, lineterminator='\n')

    tourney_slugs = []
    for tourney_path in [p for p in (tourneys_path / 'tournament').iterdir() if p.is_dir()]:
        # if 'mwc' not in tourney_path.name.lower():
        #     continue
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
        
        t_slug = re.sub(r'mwc|MWC20|MWC 20', '', tourney_info['short_name'])
        tourney_slugs.append(t_slug)
        for round_info in tourney_info['rounds']:
            for game_info in round_info['games']:
                map_name = utils.strip_format(game_info['map_name'])
                game_type = game_info['game_type']
                if map_name not in maps:
                    maps[map_name] = {'count': 0, 'game_types': {}, 'tourneys': {}}
                if game_type not in maps[map_name]['game_types']:
                    maps[map_name]['game_types'][game_type] = []
                if t_slug not in maps[map_name]['tourneys']:
                    maps[map_name]['tourneys'][t_slug] = 0
                maps[map_name]['tourneys'][t_slug] += 1
                maps[map_name]['count'] += 1
                game_info_file = tourneys_path / f"{game_info['game_path']}/stats.json"
                with open(game_info_file, 'r') as g_info_file:
                    game_full_info = json.load(g_info_file)
                    filtered_game_info = game_full_info['header']
                    del filtered_game_info['game']['locations']
                    del filtered_game_info['game']['dimensions']
                    del filtered_game_info['game']['stats']

                    filtered_game_info['round']['num_games'] = len(filtered_game_info['round']['games'])
                    del filtered_game_info['round']['games']

                    for team_id, team_info in filtered_game_info['teams'].items():
                        del team_info['players']
                        del team_info['stats']
                maps[map_name]['game_types'][game_type].append(filtered_game_info)

                if TRADE and TRADE.lower() in map_name.lower():
                    if FILTER_PRINT:
                        print(f"# FILTER_TRADE {map_name}\n")
                        for team_slug, team in game_full_info['header']['teams'].items():
                            if team.get('winner'):
                                result = 'won'
                                result_emoji = '✅'
                            elif team.get('tied_winner'):
                                result = 'tie'
                                result_emoji = '🤝'
                            else:
                                result = 'lost'
                                result_emoji = '❌'
                            if FILTER_PRINT:
                                print(f"FILTER_TRADE {game_type} {result_emoji} [{t_slug}] {mesh2trades.summarize_trade(team['trade'])} **[{team_slug} - {result}] - {team['captain']['name']}**")
                        if FILTER_PRINT:
                            print(f"FILTER_TRADE https://mythstats.bagrada.net/{game_info['game_path']}")
    tourney_slugs.sort()
    tourney_slug_header = ','.join([f'20{ts}' for ts in tourney_slugs])
    if FILTER_PRINT:
        csvwriter.writerow(["FILTER_CSV", 'Map', tourney_slug_header, 'total'])
    for map_name, map_detail in sorted(maps.items(), key=lambda m: m[1]['count'], reverse=True):
        tourney_summary = ', '.join([f'20{t}={tc}' for t, tc in sorted(map_detail['tourneys'].items())])
        tourney_summary_csv = ','.join([str(map_detail['tourneys'].get(ts, 0)) for ts in tourney_slugs])
        if FILTER_PRINT:
            print(f'FILTER_MAP {map_detail['count']:02d} {map_name} ({tourney_summary})')
            csvwriter.writerow(["FILTER_CSV", map_name, tourney_summary_csv, map_detail['count']])
        for gt, games in sorted(map_detail['game_types'].items(), key=lambda g: len(g[1]), reverse=True):
            if FILTER_PRINT:
                print(f'FILTER_GT {len(games):02d} {map_name} - {gt}')
                plugin_names = [p['name'] for p in games[0]['game']['plugins']]
                csvwriter.writerow(["FILTER_PLUGIN", map_detail['count'], len(games), map_name, *plugin_names])

    if prompt(output_path):
        with open(output_path, 'w') as output_json:
            json.dump(maps, output_json)

def prompt(output_path):
    # return True
    response = input(f"Write to {output_path}? [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <tourneys_dir> [<output_path>]")
        sys.exit(1)
    
    tourneys_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        output_path = None
    
    try:
        main(tourneys_dir, output_path)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
