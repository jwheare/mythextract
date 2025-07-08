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
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
NO_TRADING = (os.environ.get('NO_TRADING') == '1')
COUNTS = os.environ.get('COUNTS')
GAME_TYPE = os.environ.get('GAME_TYPE')
STATS = os.environ.get('STATS')
TIME = os.environ.get('TIME')
DIFFICULTY = int(os.environ.get('DIFFICULTY', 2))

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output markers for a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    counts = []
    if COUNTS:
        counts = [int(c) for c in COUNTS.split(',')]
    try:
        if level and level != 'all':
            for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
                (trade_info, units, game_type) = parse_mesh_trades(
                    game_version, tags, data_map, mesh_id,
                    DIFFICULTY, GAME_TYPE, TIME, counts
                )

                (diffs, trade) = trade_info

                if not NO_TRADING:
                    input_loop(game_type, units, diffs)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
            mesh_input = input('Choose a mesh id: ')
            main(game_directory, f'mesh={mesh_input}', plugin_names)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_mesh_trades(
    game_version, tags, data_map, mesh_id,
    difficulty, game_type_choice, game_time,
    counts, team_choice=None
):
    (mesh_tag_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(tags, data_map, 'mesh', mesh_id)
    try:
        mesh_header = mesh_tag.parse_header(mesh_tag_data)
    except (struct.error, UnicodeDecodeError):
        print("Error loading mesh")
        return

    if mesh_tag.is_single_player(mesh_header):
        print("Not a netmap")
        sys.exit(0)

    (palette, orphans) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)
    level_name = mesh_tag.get_level_name(mesh_header, tags, data_map)

    (trade_info, units, game_type) = parse_game_teams(
        tags, data_map, palette, mesh_header,
        level_name, difficulty, game_type_choice, game_time,
        counts, team_choice
    )

    (diffs, trade) = trade_info
    print_game_info(mesh_header, level_name, game_type, DIFFICULTY, TIME)
    print('\n'.join(trade))

    return (trade_info, units, game_type)

def rekey_units(units):
    return OrderedDict(
        (u['palette_index'], u)
        for u in sort_units(units.values())
    )
def sort_units(units):
    return sorted(units, key=lambda k: (k['tradeable'], k['cost'], k['max'], k['palette_index']), reverse=True)

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
                adjustment = diff // u['cost']
                u['count'] += adjustment
                diff -= (adjustment * u['cost'])
                adjusted = True
    
    return adjusted

def parse_game_teams(
    tags, data_map, palette, mesh_header,
    level_name, difficulty, game_type_choice, game_time,
    counts, team_choice=None, adjust=False
):
    game_type_units = OrderedDict()
    has_stampede_targets = False
    has_assassin_target = False

    for unit in palette[mesh_tag.MarkerType.UNIT]:
        netgame_info = mesh_tag.netgame_flag_info(unit['netgame_flags'])
        team = unit['team_index']
        if team > -1 and len(netgame_info):
            tag_id = unit['tag']
            unit_data = loadtags.get_tag_data(tags, data_map, 'unit', tag_id)
            unit_tag = mons_tag.parse_unit(unit_data)
            (mons_loc, mons_header, mons_data) = loadtags.get_tag_info(
                tags, data_map, 'mons', codec.decode_string(unit_tag.mons)
            )
            mons_dict = mons2stats.get_mons_dict(tags, data_map, mons_header, mons_data)
            for netgame in netgame_info:
                if netgame not in game_type_units:
                    game_type_units[netgame] = {}
                if team not in game_type_units[netgame]:
                    game_type_units[netgame][team] = OrderedDict()
                if tag_id not in game_type_units[netgame][team] and len(unit['markers']):
                    game_type_units[netgame][team][tag_id] = mons_dict | {
                        'tag': tag_id,
                        'team': team,
                        'initial_count': 0,
                        'count': 0,
                        'max': 0,
                        'min': 0,
                        'target': False,
                        'tradeable': mesh_tag.MarkerPaletteFlag.MAY_BE_TRADED in unit['flags'],
                    }
                    visible_count = 0
                    invisible_count = 0
                    for marker_id, marker in unit['markers'].items():
                        if marker['min_difficulty'] <= difficulty:
                            if mesh_tag.MarkerFlag.IS_INVISIBLE in marker['flags']:
                                invisible_count += 1
                            else:
                                visible_count += 1
                            is_target = mesh_tag.MarkerFlag.IS_NETGAME_TARGET in marker['flags']
                            game_type_units[netgame][team][tag_id]['target'] = is_target
                            if is_target and mesh_tag.NetgameFlag.STAMPEDE in unit['netgame_flags']:
                                has_stampede_targets = True
                            if is_target and mesh_tag.NetgameFlag.ASSASSIN in unit['netgame_flags']:
                                has_assassin_target = True
                        game_type_units[netgame][team][tag_id]['palette_index'] = marker['palette_index']
                    game_type_units[netgame][team][tag_id]['initial_count'] = visible_count
                    game_type_units[netgame][team][tag_id]['count'] = visible_count
                    game_type_units[netgame][team][tag_id]['max'] = visible_count + invisible_count
                    if mesh_tag.MarkerPaletteFlag.MAY_BE_TRADED not in unit['flags']:
                        game_type_units[netgame][team][tag_id]['min'] = game_type_units[netgame][team][tag_id]['max']

    if 'all' in game_type_units:
        included_game_types = list(mesh_tag.NetgameFlagInfo.values())
        if not has_stampede_targets:
            included_game_types.remove('stamp')
        if not has_assassin_target:
            included_game_types.remove('ass')
    else:
        included_game_types = list(game_type_units.keys())
    included_game_types.sort()

    if game_type_choice not in included_game_types:
        game_type_choice = None

    if not game_type_choice:
        game_type_nums = [
            f'{i+1:>2}) {mesh_tag.NetgameNames[gt]}' for i, gt in enumerate(included_game_types)
        ]
        print(f"\n{level_name}\n")
        game_type_choice_i = int(input(f"{'\n'.join(game_type_nums)}\n\nChoose game type: ").strip().lower())
        game_type_choice = included_game_types[game_type_choice_i-1]

    shared_units = game_type_units.get('all', {})
    teams = game_type_units.get(game_type_choice, shared_units)
    trades = {}
    for team, units in teams.items():
        merged_units = units
        if team in shared_units:
            merged_units = shared_units[team] | merged_units
        
        rekeyed_units = rekey_units(merged_units)
        counted_units = set_initial_counts(rekeyed_units, counts)
        trades[team] = team_trade_parts(game_type_choice, counted_units)

    if team_choice is None:
        mismatch = False
        for team_id, (diffs, trade) in trades.items():
            if trade != trades[0][1]:
                mismatch = True
                break
        if mismatch:
            print_game_info(mesh_header, level_name, game_type_choice, difficulty, game_time)
            print('- Assymetric teams -')
            for team_id, (diffs, trade) in trades.items():
                print(f"\nTeam {team_id}")
                print('\n'.join(trade))
            team_choice = int(input("\nChoose team: ").strip().lower())
        else:
            team_choice = 0

    final_merged_units = teams[team_choice]
    if team_choice in shared_units:
        final_merged_units = shared_units[team_choice] | teams[team_choice]
    final_units = rekey_units(final_merged_units)
    trade = trades[team_choice]
    if adjust:
        if auto_adjust_counts(final_units):
            trade = team_trade_parts(game_type_choice, final_units)
    return (trade, final_units, game_type_choice)

def print_game_info(mesh_header, level_name, game_type_choice, difficulty, game_time):
    info = mesh_tag.get_game_info(mesh_header, level_name, game_type_choice, difficulty, game_time)
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
            op = match.group(2)
            if op == '-':
                if unit is not None:
                    count = units[unit]['count'] - 1
            elif op == '--':
                if unit is None:
                    all_units = 'min'
                else:
                    count = 0
            elif op == '+':
                if unit is not None:
                    count = units[unit]['count'] + 1
            elif op == '++':
                if unit is None:
                    all_units = 'max'
                else:
                    count = units[unit]['max']
            elif op == '=':
                if unit is None:
                    unit = next((idx for idx, diff in enumerate(diffs) if diff != 0), None)
                if unit is not None:
                    count = units[unit]['count'] + diffs[unit]
        elif adjust in ['x','q']:
            sys.exit(0)

        if all_units:
            for u in units:
                u['count'] = u[all_units]
        elif count is not None and unit is not None:
            units[unit]['count'] = max(min(count, units[unit]['max']), units[unit]['min'])

        (diffs, trade) = team_trade_parts(game_type, unit_dict)
        # Move cursor up
        print(f"\x1b[{len(trade)+2}A", end='')
        for line in trade:
            print(f"\n\x1b[K{line}", end='')
        if unit is not None and count is not None:
            print(f"\x1b[K{units[unit]['spellings'][1]} -> {units[unit]['count']}")
        else:
            print("\x1b[K")

def unit_class_name(unit):
    class_name = unit['class'].name
    if unit['class'] == mons_tag.MonsClass.MISSILE:
        dmgs = [attack['dmg'] for attack in unit['attacks'] if attack['dmg'] is not None]
        if len(dmgs):
            # Assassin targets don't have attacks
            max_dmg = max([attack['dmg'] for attack in unit['attacks'] if attack['dmg'] is not None])
            if max_dmg >= 3:
                class_name = 'artillery'
        else:
            class_name = 'target'
    return utils.cap_title(class_name)

def team_trade_parts(game_type, units):
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
    for i, u in enumerate(units.values()):
        if u['target'] and game_type in ['ass', 'stamp']:
            afford = 0
        elif u['tradeable']:
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
            u_name = unit_name(u, with_class=True)
            trades.append(
                f"{i+1:>7}) {u_name:<32}"
                f"{u['count']:>2} / "
                f"{u['max']:<2} "
                f"• cost: {u['cost']:<2} "
                f"• value: {(u['cost']*u['count']):<3} "
                f"{diff_amount} "
                f"{u['count']*'◼︎'}{(u['max'] - u['count'])*'◻︎'}"
            )
            if STATS:
                trades += mons2stats.mons_stats(u)
                trades.append(64*'-')

        elif u['count']:
            afford = 0
            if len(untradeable) == 0:
                divider.append("")
                divider.append("Not tradeable:")
                divider.append("")
            u_name = unit_name(u, with_class=True)
            untradeable.append(
                f"         {u_name:<32}"
                f"{u['count']:>2} / "
                f"{u['max']:<2} "
                f"• cost: {u['cost']:<2} "
                f"• value: {(u['cost']*u['count']):<3} "
                " "
                f"{u['count']*'◼︎'}{(u['max'] - u['count'])*'◻︎'}"
            )
            if STATS:
                untradeable += mons2stats.mons_stats(u)
                # untradeable.append(64*'-')
        else:
            afford = 0
        diffs.append(afford)
    suffix.append("")
    total_points = f"Total points: {total}"
    total_points += f'/{max_points}'
    if total > max_points:
        total_points += f' \x1b[91mexcess: {total - max_points}\x1b[0m'
    elif max_points > total:
        total_points += f' \x1b[93mremaining: {max_points - total}\x1b[0m'
    else:
        total_points += ' \x1b[92mremaining: 0\x1b[0m'

    suffix.append(total_points)
    suffix.append("")
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
    return (diffs, trades + divider + untradeable + suffix)

def unit_name(u, count=None, with_class=False):
    u_name = u['spellings'][0]
    if (count is None or count > 1) and len(u['spellings']) > 1:
        u_name = u['spellings'][1]
    if with_class:
        u_name += f' ({unit_class_name(u)})'
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
