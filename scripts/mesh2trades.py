#!/usr/bin/env python3
from collections import OrderedDict
import os
import re
import struct
import sys

import codec
import mesh_tag
import mesh2info
import mons2stats
import mono2tag
import loadtags
import mons_tag
import myth_tags
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
NO_TRADING = (os.environ.get('NO_TRADING') == '1')
COUNTS = os.environ.get('COUNTS')
GAME_TYPE = os.environ.get('GAME_TYPE')
STATS = os.environ.get('STATS')
TIME = os.environ.get('TIME')
TEAM = os.environ.get('TEAM')
DIFFICULTY = int(os.environ.get('DIFFICULTY', 2))

CSV = os.environ.get('CSV')
JSON = os.environ.get('JSON')
PLUGIN_GROUP = os.environ.get('PLUGIN_GROUP')
PLUGIN_AUTHOR = os.environ.get('PLUGIN_AUTHOR')
PLUGIN_V = os.environ.get('PLUGIN_V')
PLUGIN_SLUG = os.environ.get('PLUGIN_SLUG')

def csv_header():
    return [
        'Mismatched teams',
        'Mesh name',

        'Unit',
        'Unit class',
        'Count',
        'Max',
        'Cost',
        'Value',
        'Tradeable',
        'Targets',
        'May Vet',
        'Must Vet',

        'Mesh ID',
        'Version',
        'Plugin',
        'Author',
        'Group',
        'Game type',
        'Difficulty',
        'Size',
        'URL',
    ]

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output markers for a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    counts = []
    if COUNTS:
        counts = [int(c) for c in COUNTS.split(',')]

    csv_rows = []
    json_rows = []
    try:
        if level and level != 'list':
            for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
                mesh_header, mesh_tag_data, mesh_tag_location = parse_mesh_header(tags, data_map, mesh_id)
                if mesh_tag.is_single_player(mesh_header):
                    continue

                level_name = mesh_tag.get_level_name(mesh_header, tags, data_map) or mesh_id
                (palette, orphans) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)

                if mesh_tag.MarkerType.UNIT not in palette:
                    continue

                game_types, game_type_units = parse_game_type_units(
                    game_version,
                    tags, data_map, palette, mesh_header,
                    level_name, DIFFICULTY, GAME_TYPE
                )

                detect_flag_issues(game_types, game_type_units, palette, tags, data_map)

                for game_type in game_types:
                    if not CSV and not JSON:
                        print_game_info(mesh_header, level_name, game_type, DIFFICULTY, game_time=TIME)

                    game_teams = parse_game_teams(
                        game_type, game_type_units,
                        counts, team_choice=TEAM
                    )
                    if not game_teams:
                        continue

                    (trade_info, units, mismatch) = game_teams
                    (diffs, trade, trade_data) = trade_info
                    (mismatch_team, mismatch_rows) = mismatch
                    if JSON:
                        level_name = mesh_tag.get_level_name(mesh_header, tags, data_map)
                        is_mismatch = False
                        mismatch_info = None
                        if mismatch_rows:
                            is_mismatch = True
                            mismatch_info = {'team_id': mismatch_team, 'rows': mismatch_rows}
                        json_rows.append({
                            'is_mismatch': is_mismatch,
                            'mismatch_info': mismatch_info,
                            'mesh_name': level_name,
                            'trade': trade,
                            'game_type': game_type,
                            'difficulty': mesh_tag.difficulty(DIFFICULTY),
                            'mesh_size': mesh_tag.mesh_size(mesh_header),
                            'mesh_id': mesh_id,
                            'mesh_plugin': mesh_tag_location,
                            'plugin_version': PLUGIN_V,
                            'plugin_tain_slug': PLUGIN_SLUG,
                            'plugin_author': PLUGIN_AUTHOR,
                            'plugin_group': PLUGIN_GROUP,
                        })
                    elif CSV:
                        level_name_strip = mesh_tag.get_level_name(mesh_header, tags, data_map, strip_format=True)
                        for i, row in enumerate(trade_data):
                            mismatch_str = ''
                            if mismatch_rows is True:
                                mismatch_str = 'mismatch'
                            elif mismatch_rows and i in mismatch_rows:
                                mismatch_str = ' / '.join(
                                    [f'{key}: {val1} -> {val2}' for (key, (val1, val2)) in mismatch_rows[i].items()]
                                )
                            csv_rows.append([
                                mismatch_str,
                                level_name_strip,

                                row['unit'],
                                row['class'],
                                row['count'],
                                row['max'],
                                row['cost'],
                                row['value'],
                                'Tradeable' if row['tradeable'] else 'Default',
                                row['targets'],
                                'Vettable' if row['may_use_vet'] else 'Unvettable',
                                'Max if vet only' if row['must_use_vet'] else 'Count only',

                                mesh_id,
                                PLUGIN_V,
                                mesh_tag_location,
                                PLUGIN_AUTHOR,
                                PLUGIN_GROUP,
                                game_type,
                                mesh_tag.difficulty(DIFFICULTY),
                                mesh_tag.mesh_size(mesh_header),
                                f"https://tain.totalcodex.net/items/show/{PLUGIN_SLUG}" if PLUGIN_SLUG else '',
                            ])
                    else:
                        print('\n'.join(trade))
                        if not NO_TRADING:
                            input_loop(game_type, units, diffs)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map, plugin_names=plugin_names)
            mesh_input = input('Choose a mesh id: ')
            main(game_directory, f'mesh={mesh_input}', plugin_names)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

    if JSON and len(json_rows):
        import json
        with open(JSON, 'a', newline='') as jsonfile:
            if jsonfile.tell() == 0:
                jsonfile.write('[\n{}')
            for row in json_rows:
                jsonfile.write(',\n')
                json.dump(row, jsonfile)
        json_rows
    elif CSV and len(csv_rows):
        import csv
        with open(CSV, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            if csvfile.tell() == 0:
                csvwriter.writerow(csv_header())
            csvwriter.writerows(csv_rows)

def detect_flag_issues(game_types, game_type_units, palette, tags, data_map):
    game_type_items = {}
    if mesh_tag.MarkerType.SCENERY in palette:
        for scenery in palette[mesh_tag.MarkerType.SCENERY]:
            tag_id = scenery['tag']
            (location, tag_header, tag_data) = loadtags.get_tag_info(tags, data_map, 'scen', tag_id)
            scen_tag = myth_tags.parse_scenery(tag_data) if tag_data else None
            if scen_tag:
                scen_game_types = mesh_tag.netgame_flag_info(scenery['netgame_flags'])
                for marker_id, marker in scenery['markers'].items():
                    scen_tag_info = myth_tags.scen_netgame_info(scen_tag)
                    if scen_tag_info:
                        scoring_type, flag_number = scen_tag_info
                        scoring_key = mesh_tag.netgame_scoring_key(scoring_type)
                        if scoring_key not in game_type_items:
                            game_type_items[scoring_key] = []
                        game_type_items[scoring_key].append({
                            'game_types': scen_game_types,
                            'min_difficulty': marker['min_difficulty'],
                            'flag_number': flag_number,
                            'team': scenery['team_index'],
                        })
    for gt in ['fr', 'scav']:
        # Check only one item of each number, and at least one item total
        if 'all' in game_types or gt in game_types:
            test_difficulty = False
            flag_counts = {}
            max_flag_num = 0
            for item in game_type_items.get(gt, []):
                if 'all' in item['game_types'] or gt in item['game_types']:
                    if item['min_difficulty'] > 0:
                        test_difficulty = True
                    max_flag_num = max(max_flag_num, item['flag_number'])
                    if item['flag_number'] not in flag_counts:
                        flag_counts[item['flag_number']] = 0
                    flag_counts[item['flag_number']] += 1
            target = mesh_tag.netgame_location_type(gt, True)
            if not len(flag_counts):
                print(f"\x1b[91m- {mesh_tag.NetgameNames[gt]}: No {target}s -\x1b[0m")
            else:
                for flag_num in range(1, max_flag_num + 1):
                    count = flag_counts.get(flag_num, 0)
                    if count != 1:
                        print(f"\x1b[91m- {mesh_tag.NetgameNames[gt]}: {target} {flag_num} unexpected count: {count} -\x1b[0m")

            if test_difficulty:
                print('TODO check difficulties')

    for gt in ['ctf', 'balls']:
        # Check only one item for each team
        if 'all' in game_types or gt in game_types:
            team_ids = game_type_units.get(gt, game_type_units.get('all', {})).keys()
            test_difficulty = False
            flag_counts = {}
            for item in game_type_items.get(gt, []):
                if 'all' in item['game_types'] or gt in item['game_types']:
                    if item['min_difficulty'] > 0:
                        test_difficulty = True
                    if item['team'] not in flag_counts:
                        flag_counts[item['team']] = 0
                    flag_counts[item['team']] += 1
            target = mesh_tag.netgame_location_type(gt, True)
            for team in team_ids:
                count = flag_counts.get(team, 0)
                if count != 1:
                    print(f"\x1b[91m- {mesh_tag.NetgameNames[gt]}: Team {team} unexpected {target} count: {count} -\x1b[0m")

            if test_difficulty:
                print('TODO check difficulties')

    for gt in ['stb', 'lmoth', 'koth']:
        # Check only one item total
        if 'all' in game_types or gt in game_types:
            team_ids = game_type_units.get(gt, game_type_units.get('all', {})).keys()
            test_difficulty = False
            count = 0
            for item in game_type_items.get(gt, []):
                if 'all' in item['game_types'] or gt in item['game_types']:
                    if item['min_difficulty'] > 0:
                        test_difficulty = True
                    count += 1
            target = mesh_tag.netgame_location_type(gt, True)
            if count != 1:
                print(f"\x1b[91m- {mesh_tag.NetgameNames[gt]}: Unexpected {target} count: {count} -\x1b[0m")

    for gt in ['terries', 'caps']:
        # Check at least one item total
        if 'all' in game_types or gt in game_types:
            team_ids = game_type_units.get(gt, game_type_units.get('all', {})).keys()
            test_difficulty = False
            count = 0
            for item in game_type_items.get(gt, []):
                if 'all' in item['game_types'] or gt in item['game_types']:
                    if item['min_difficulty'] > 0:
                        test_difficulty = True
                    count += 1
            target = mesh_tag.netgame_location_type(gt, True)
            if count < 1:
                print(f"\x1b[91m- {mesh_tag.NetgameNames[gt]}: Unexpected {target} count: {count} -\x1b[0m")

    for gt in ['stamp']:
        # Check same items per team
        if 'all' in game_types or gt in game_types:
            team_ids = game_type_units.get(gt, game_type_units.get('all', {})).keys()
            test_difficulty = False
            flag_counts = {}
            for item in game_type_items.get(gt, []):
                if 'all' in item['game_types'] or gt in item['game_types']:
                    if item['min_difficulty'] > 0:
                        test_difficulty = True
                    if item['team'] not in flag_counts:
                        flag_counts[item['team']] = 0
                    flag_counts[item['team']] += 1
            neutral_count = flag_counts.get(-1, 0)
            team_counts = []
            for team in team_ids:
                count = flag_counts.get(team, 0)
                team_counts.append(count)
                if not neutral_count and not count:
                    print(f"\x1b[91m- {mesh_tag.NetgameNames[gt]}: Team {team} missing flags -\x1b[0m")
            if min(team_counts) != max(team_counts):
                for team in team_ids:
                    count = flag_counts.get(team, 0)
                    print(f"\x1b[91m- {mesh_tag.NetgameNames[gt]}: Team {team} mismatched flags: {count} -\x1b[0m")

            if test_difficulty:
                print('TODO check difficulties')

def parse_mesh_header(tags, data_map, mesh_id):
    (mesh_tag_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(
        tags, data_map, 'mesh', mesh_id
    )
    try:
        mesh_header = mesh_tag.parse_header(mesh_tag_data)
    except (struct.error, UnicodeDecodeError):
        print("Error loading mesh")
        sys.exit(1)

    return mesh_header, mesh_tag_data, mesh_tag_location

def rekey_units(units):
    return OrderedDict(
        (u['tag'], u)
        for u in sort_units(units.values())
    )

# This is the sort order used in the trading dialog and trade film commands
def sort_units(units):
    return sorted(units, key=lambda k: (k['tradeable'], k['cost'], k['max'], k['palette_index'][0]), reverse=True)

# Sort by unit name for diffing only
def diff_sort_units(units):
    return sorted(units, key=lambda k: (k['tradeable'], k['targets'], k['unit']), reverse=True)

def set_initial_counts(units, counts):
    for i, u in enumerate(units.values()):
        if u['max'] > 0 and u['tradeable']:
            if i < len(counts):
                u['count'] = counts[i]
    return units

def auto_adjust_counts(units):
    adjusted = False
    diffs = [u['cost'] * (u['initial_count'] - u['count']) for u in units.values()]
    diff = sum(diffs)
    for i, u in enumerate(units.values()):
        if diff > 0:
            unit_diff = diffs[i]
            if unit_diff > 0:
                adjustment = min(diff // u['cost'], u['max'] - u['count'])
                u['count'] += adjustment
                diff -= (adjustment * u['cost'])
                adjusted = True
    
    return adjusted

def parse_game_type_units(
    game_version,
    tags, data_map, palette, mesh_header,
    level_name, difficulty, game_type_choice
):
    game_type_units = OrderedDict()
    team_has_stampede_targets = {}
    team_has_assassin_targets = {}

    if mesh_tag.MarkerType.UNIT in palette:
        for unit in palette[mesh_tag.MarkerType.UNIT]:
            netgame_info = mesh_tag.netgame_flag_info(unit['netgame_flags'])
            team = unit['team_index']
            if team > -1 and len(netgame_info) and len(unit['markers']):
                tag_id = unit['tag']
                unit_data = loadtags.get_tag_data(tags, data_map, 'unit', tag_id)
                unit_tag = mons_tag.parse_unit(unit_data)
                if not unit_tag.mons:
                    continue
                (mons_loc, mons_header, mons_data) = loadtags.get_tag_info(
                    tags, data_map, 'mons', codec.decode_string(unit_tag.mons)
                )
                if not mons_data:
                    continue

                if mesh_tag.MarkerPaletteFlag.UNCONTROLLABLE in unit['flags']:
                    uncontrollable_target = False
                    for uncontrollable_marker in unit['markers'].values():
                        if mesh_tag.MarkerFlag.IS_NETGAME_TARGET in uncontrollable_marker['flags']:
                            uncontrollable_target = True
                    if not uncontrollable_target:
                        continue
                if mesh_tag.is_reinforcements(unit):
                    continue
                mons_dict = mons2stats.get_mons_dict(game_version, tags, data_map, mons_header, mons_data, mons_loc)
                for netgame in netgame_info:
                    if netgame not in game_type_units:
                        game_type_units[netgame] = {}
                    if team not in game_type_units[netgame]:
                        game_type_units[netgame][team] = OrderedDict()
                    if tag_id not in game_type_units[netgame][team]:
                        game_type_units[netgame][team][tag_id] = mons_dict | {
                            'tag': tag_id,
                            'team': team,
                            'initial_count': 0,
                            'count': 0,
                            'max': 0,
                            'min': 0,
                            'targets': 0,
                            'markers': [],
                            'palette_index': [],
                            'tradeable': mesh_tag.MarkerPaletteFlag.MAY_BE_TRADED in unit['flags'],
                            'may_use_vet': mesh_tag.MarkerPaletteFlag.MAY_USE_VETERANS in unit['flags'],
                            'must_use_vet': mesh_tag.MarkerPaletteFlag.MUST_USE_VETERANS in unit['flags'],
                        }
                    visible_count = 0
                    invisible_count = 0
                    target_count = 0
                    markers = []
                    palette_index = None
                    for marker_id, marker in unit['markers'].items():
                        palette_index = marker['palette_index']
                        if mesh_tag.MarkerFlag.IS_INVISIBLE_OBSERVER in marker['flags']:
                            continue
                        if marker['min_difficulty'] <= difficulty:
                            if mesh_tag.MarkerFlag.IS_INVISIBLE in marker['flags']:
                                invisible_count += 1
                            else:
                                visible_count += 1
                            markers.append({
                                k: v for k, v in marker.items() if k not in [
                                    'tag', 'type', 'pos', 'flags'
                                ]
                            } | {
                                'position': mesh_tag.normalise_position(mesh_header, marker['pos']),
                                'flags': mesh_tag.marker_flag_info(marker['flags']),
                            })
                            is_target = mesh_tag.MarkerFlag.IS_NETGAME_TARGET in marker['flags']
                            if is_target:
                                target_count += 1
                            if is_target and mesh_tag.NetgameFlag.STAMPEDE in unit['netgame_flags']:
                                team_has_stampede_targets[team] = True
                            if is_target and mesh_tag.NetgameFlag.ASSASSIN in unit['netgame_flags']:
                                team_has_assassin_targets[team] = True

                    if mesh_tag.is_single_player(mesh_header):
                        count = visible_count + invisible_count
                        max_count = count
                    else:
                        count = visible_count
                        max_count = visible_count + invisible_count
                    game_type_units[netgame][team][tag_id]['initial_count'] += count
                    game_type_units[netgame][team][tag_id]['count'] += count
                    game_type_units[netgame][team][tag_id]['max'] += max_count
                    game_type_units[netgame][team][tag_id]['targets'] += target_count
                    game_type_units[netgame][team][tag_id]['markers'] += markers
                    if palette_index is not None and palette_index not in game_type_units[netgame][team][tag_id]['palette_index']:
                        game_type_units[netgame][team][tag_id]['palette_index'].append(palette_index)
                    if mesh_tag.MarkerPaletteFlag.MAY_BE_TRADED not in unit['flags']:
                        game_type_units[netgame][team][tag_id]['min'] = game_type_units[netgame][team][tag_id]['max']

    enabled_game_types = mesh_tag.enabled_netgames(mesh_header)
    if 'all' in game_type_units:
        included_game_types = enabled_game_types
    else:
        included_game_types = [k for k in game_type_units.keys() if k in enabled_game_types]

    included_game_types.sort()

    game_types = []
    if game_type_choice == 'all':
        game_types = included_game_types
    else:
        if game_type_choice not in included_game_types:
            game_type_choice = None

        if not game_type_choice:
            game_type_nums = [
                f'{i+1:>2}) {mesh_tag.NetgameNames[gt]}' for i, gt in enumerate(included_game_types)
            ]
            print(f"\n{level_name}\n")
            game_type_choice_i = int(input(f"{'\n'.join(game_type_nums)}\n\nChoose game type: ").strip().lower())
            game_type_choice = included_game_types[game_type_choice_i-1]

        game_types = [game_type_choice]

    if 'stamp' in game_types:
        stamp_units = game_type_units.get('stamp', game_type_units.get('all', {}))
        for team in stamp_units.keys():
            if not team_has_stampede_targets.get(team):
                print(f'\x1b[91m- Team {team} Missing stampede units -\x1b[0m')
    if 'ass' in game_types:
        ass_units = game_type_units.get('ass', game_type_units.get('all', {}))
        for team in ass_units.keys():
            if not team_has_assassin_targets.get(team):
                print(f'\x1b[91m- Team {team} Missing assassin targets -\x1b[0m')

    return game_types, game_type_units

def rekey_teams(game_type, game_type_units):
    shared_units = game_type_units.get('all', {})
    teams = game_type_units.get(game_type, shared_units)
    for team in shared_units.keys():
        if team not in teams:
            teams[team] = shared_units[team]
    rekeyed_teams = {}
    for team, units in teams.items():
        merged_units = units
        if team in shared_units:
            merged_units = shared_units[team] | merged_units
        
        rekeyed_units = rekey_units(merged_units)
        rekeyed_teams[team] = rekeyed_units
    return rekeyed_teams

def parse_game_teams(
    game_type, game_type_units,
    counts=[], team_choice=None, adjust=False
):
    shared_units = game_type_units.get('all', {})
    teams = game_type_units.get(game_type, shared_units)
    for team in shared_units.keys():
        if team not in teams:
            teams[team] = shared_units[team]
    trades = {}
    for team, units in teams.items():
        merged_units = units
        if team in shared_units:
            merged_units = shared_units[team] | merged_units
        
        rekeyed_units = rekey_units(merged_units)
        counted_units = set_initial_counts(rekeyed_units, counts)
        trades[team] = team_trade_parts(game_type, counted_units)

    mismatch = (None, None)
    first_trade_s = diff_sort_units(trades[list(trades.keys())[0]][2])
    for team_id, (diffs, trade, trade_data) in trades.items():
        trade_data_s = diff_sort_units(trade_data)
        if trade_data_s != first_trade_s:
            mismatch_rows = []
            if len(trade_data_s) != len(first_trade_s):
                mismatch = (team_id, True)
            else:
                for i, row in enumerate(first_trade_s):
                    if row != trade_data_s[i]:
                        mismatch_keys = {}
                        for col, val in row.items():
                            if (val != trade_data_s[i][col]):
                                mismatch_keys[col] = (val, trade_data_s[i][col])

                        if len(mismatch_keys) == 1 and 'unit' in mismatch_keys:
                            # Filter unit name only mismatches
                            pass
                        else:
                            mismatch_rows.append((i, mismatch_keys))
                mismatch = (team_id, dict(mismatch_rows))
            break

    mismatched = mismatch[1] is True or (mismatch[1] is not None and len(mismatch[1]) > 0)
    if len(counts) == 0 and mismatched:
        print(f'\x1b[91m- Asymmetric teams [{game_type}] -\x1b[0m', mismatch)

    if team_choice is None:
        if mismatched:
            if not CSV and not JSON:
                for team_id, (diffs, trade, trade_data) in trades.items():
                    print(f"\nTeam {team_id}")
                    print('\n'.join(trade))
            team_choice = input("\nChoose team: ").strip().lower()
        else:
            team_choice = 0
    team_choice = int(team_choice)

    if team_choice not in teams:
        print(f'\x1b[91m- No units for team: {team_choice} -\x1b[0m')
        return
    final_merged_units = teams[team_choice]
    if team_choice in shared_units:
        final_merged_units = shared_units[team_choice] | teams[team_choice]
    final_units = rekey_units(final_merged_units)
    trade = trades[team_choice]
    if adjust:
        if auto_adjust_counts(final_units):
            trade = team_trade_parts(game_type, final_units)
    return (trade, final_units, mismatch)

def print_game_info(mesh_header, level_name, game_type, difficulty, game_time=None):
    info = mesh_tag.get_game_info(mesh_header, level_name, game_type, difficulty, game_time)
    print(f"\n---\n\n{info}\n")

def input_loop(game_type, unit_dict, diffs):
    units = list(unit_dict.values())
    print("\n\x1b[1A", end='')
    while True:
        adjust = input("\x1b[KAdjust unit: (type unit num and count separated by a space, or num+ / num- for increment/decrement or num++ / num-- for max/min or num= to accept suggestion) ").strip().lower()
        unit = None
        count = None
        all_units = False
        if match := re.match(r'^(\d+)\s+(\d+)$', adjust):
            unit = int(match.group(1)) - 1
            count = int(match.group(2))
        elif match := re.match(r'^(\d+)?([+]{1,2}|[-]{1,2}|[=]{1,1})$', adjust):
            unit = int(match.group(1) or 0) - 1
            if unit < 0:
                unit = None
            unit_set = unit is not None
            valid_unit = unit_set and unit < len(units)
            op = match.group(2)
            if op == '-':
                if valid_unit:
                    count = units[unit]['count'] - 1
            elif op == '--':
                if not unit_set:
                    all_units = 'min'
                elif valid_unit:
                    count = 0
            elif op == '+':
                if valid_unit:
                    count = units[unit]['count'] + 1
            elif op == '++':
                if not unit_set:
                    all_units = 'max'
                elif valid_unit:
                    count = units[unit]['max']
            elif op == '=':
                if not unit_set:
                    unit = next((idx for idx, diff in enumerate(diffs) if diff != 0), None)
                elif valid_unit:
                    count = units[unit]['count'] + diffs[unit]
        elif adjust in ['x','q']:
            sys.exit(0)
        valid_input = count is not None and valid_unit
        if all_units:
            for u in units:
                u['count'] = u[all_units]
        elif valid_input:
            if units[unit]['tradeable']:
                units[unit]['count'] = max(min(count, units[unit]['max']), units[unit]['min'])
            else:
                valid_input = False

        (diffs, trade, trade_data) = team_trade_parts(game_type, unit_dict)
        # Move cursor up
        print(f"\x1b[{len(trade)+2}A", end='')
        for line in trade:
            print(f"\n\x1b[K{line}", end='')
        if valid_input:
            print(f"\x1b[K{units[unit]['spellings'][1]} -> {units[unit]['count']}")
        else:
            print("\x1b[K")

def unit_class_name(unit):
    class_name = unit['class'].name
    if unit['class'] == mons_tag.MonsClass.MISSILE:
        dmgs = [attack['dmg'] for attack in unit['attacks'] if attack['dmg'] is not None]
        if len(dmgs):
            # Some units (e.g. some assassin/stampede targets) don't have attacks
            max_dmg = max([attack['dmg'] for attack in unit['attacks'] if attack['dmg'] is not None])
            if max_dmg >= 3:
                class_name = 'artillery'
        else:
            class_name = 'target'
    return utils.cap_title(class_name)

def team_trade_parts_export(game_type, units):
    rows = []
    for i, (palette_index, u) in enumerate(units.items()):
        if u['tradeable'] or u['count']:
            u_name = unit_name(u)
            rows.append({
                'unit': u_name,
                'class': unit_class_name(u),
                'count': u['count'],
                'max': u['max'],
                'cost': u['cost'],
                'value': u['cost'] * u['count'],
                'tradeable': u['tradeable'],
                'targets': u['targets'],
                'may_use_vet': u['may_use_vet'],
                'must_use_vet': u['must_use_vet'],
            })

    return rows

def team_trade_parts(game_type, units):
    trade_data = team_trade_parts_export(game_type, units)
    if CSV or JSON:
        return ([], [], trade_data)
    trades = []
    divider = []
    untradeable = []
    suffix = []
    class_distribution = {}
    total = sum(u['cost']*u['count'] for u in units.values())
    class_total = 0
    diff = 0
    diffs = []
    max_points = sum(u['cost']*u['initial_count'] for u in units.values())
    diff = max_points - total
    for i, (tag_id, u) in enumerate(units.items()):
        if u['tradeable']:
            unit_class = unit_class_name(u)
            if unit_class not in class_distribution:
                class_distribution[unit_class] = 0
            unit_value = u['count'] * u['cost']
            class_total += unit_value
            class_distribution[unit_class] += unit_value
            afford = diff // u['cost']
            diff_amount = '           '
            if afford > 0:
                afford = min(afford, u['max'] - u['count'])
                if afford:
                    diff_amount = f'• \x1b[93m buy: {afford:<2}\x1b[0m '
            elif afford < 0:
                afford = max(afford, -u['count'])
                if afford:
                    diff_amount = f'• \x1b[91msell: {-afford:<2}\x1b[0m '

            if NO_TRADING:
                diff_amount = ''
            u_name = unit_name(u, with_class=True, with_tag=STATS)
            trades.append(
                f"{i+1:>7}) {u_name:<32}"
                f"{u['count']:>2} / "
                f"{u['max']:<2} "
                f"• cost: {u['cost']:<2} "
                f"• value: {(u['cost']*u['count']):<3} "
                f"{diff_amount} "
                f"{u['count']*'◼︎'}{(u['max'] - u['count'])*'◻︎'}"
            )
            if u['targets']:
                trades.append(f"{' ':>9}* Target: {mesh_tag.NetgameNames[game_type]} ({u['targets']})")
            if STATS:
                trades += mons2stats.mons_stats(u)
                trades.append(64*'-')
            # for marker in u['markers']:
            #     trades.append(f"{tag_id} {marker['palette_index']} {marker['marker_id']} {u_name}")

        elif u['count']:
            afford = 0
            if len(untradeable) == 0:
                divider.append("")
                divider.append("Not tradeable:")
                divider.append("")
            u_name = unit_name(u, with_class=True, with_tag=STATS)
            untradeable.append(
                f"         {u_name:<32}"
                f"{u['count']:>2} / "
                f"{u['max']:<2} "
                f"• cost: {u['cost']:<2} "
                f"• value: {(u['cost']*u['count']):<3} "
                " "
                f"{u['count']*'◼︎'}{(u['max'] - u['count'])*'◻︎'}"
            )
            if u['targets']:
                untradeable.append(f"{' ':>9}* Target: {mesh_tag.NetgameNames[game_type]} ({u['targets']})")
            if STATS:
                untradeable += mons2stats.mons_stats(u)
                untradeable.append(64*'-')
        else:
            afford = 0
        diffs.append(afford)
    suffix.append("")
    total_points = f"Total points: {total}"
    total_points += f'/{max_points}'
    if not NO_TRADING:
        if total > max_points:
            total_points += f' \x1b[91mexcess: {total - max_points}\x1b[0m'
        elif max_points > total:
            total_points += f' \x1b[93mremaining: {max_points - total}\x1b[0m'
        else:
            total_points += ' \x1b[92mremaining: 0\x1b[0m'

    suffix.append(total_points)
    if not NO_TRADING:
        suffix.append("")
        suffix.append(summarize_trade(units.values()))
        suffix.append("Class distribution:")

        class_graph = ''
        class_key = ''
        for i, unit_class in enumerate(sorted(class_distribution.keys())):
            color = f"\x1b[9{i+4}m"
            class_count = class_distribution[unit_class]
            class_graph += f"{color}{round(class_count/3)*'◼︎'}\x1b[0m"
            class_key += f'{color}◼︎\x1b[0m {unit_class} ({round(100*class_count/max(1, class_total))}%) '

        suffix.append(class_graph)
        suffix.append(class_key)
    # suffix.append("")
    # suffix.append("---")
    suffix.append("")
    return (diffs, trades + divider + untradeable + suffix, trade_data)

def summarize_trade(trade):
  return ', '.join([f"{unit['count']}x {unit_name(unit, count=1)}" for unit in trade if unit['count'] and unit['tradeable']])

def unit_name(u, count=None, with_class=False, with_tag=False):
    u_name = u['spellings'][0]
    if (count is None or count > 1) and len(u['spellings']) > 1 and u['spellings'][1]:
        u_name = u['spellings'][1]
    if with_class:
        u_name += f' ({unit_class_name(u)})'
    if with_tag:
        custom = ''
        if u['location'] != 'small install' and not u['location'].startswith('Patch 1.'):
            custom += ' - custom'
        u_name += f' [{u['tag']}{custom}]'
    return u_name

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> [<level> [<plugin_names> ...]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_names = []
    if len(sys.argv) > 2:
        level = sys.argv[2]
        if len(sys.argv) > 3:
            plugin_names = sys.argv[3:]

    try:
        main(game_directory, level, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
