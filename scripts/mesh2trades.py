#!/usr/bin/env python3
from collections import OrderedDict
import os
import re
import struct
import sys

import mesh_tag
import mesh2info
import mons2info
import mono2tag
import loadtags
import mons_tag
import myth_headers
import myth_projectile
import myth_collection
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
NO_TRADING = (os.environ.get('NO_TRADING') == '1')
COUNTS = os.environ.get('COUNTS')
GAME_TYPE = os.environ.get('GAME_TYPE')
STATS = os.environ.get('STATS')

NetgameNames = OrderedDict({
    'bc': 'Body Count',
    'stb': 'Steal the Bacon',
    'lmoth': 'Last Man on the Hill',
    'scav': 'Scavenger Hunt',
    'fr': 'Flag Rally',
    'ctf': 'Capture the Flag',
    'balls': 'Balls on Parade',
    'terries': 'Territories',
    'caps': 'Captures',
    'koth': 'King of the Hill',
    'stamp': 'Stampede',
    'ass': 'Assassin',
    'hunt': 'Hunting',
    'custom': 'Custom',
    'koth_tfl': 'King of the Hill (TFL)',
    'kotm': 'King of the Map',
})

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output markers for a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if level:
            for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
                parse_mesh_trades(game_version, tags, data_map, mesh_id)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_mesh_trades(game_version, tags, data_map, mesh_id):
    (mesh_tag_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(tags, data_map, 'mesh', mesh_id)
    try:
        mesh_header = mesh_tag.parse_header(mesh_tag_data)
    except (struct.error, UnicodeDecodeError) as e:
        print("Error loading mesh")
        return

    if mesh_tag.is_single_player(mesh_header):
        print("Not a netmap")
        sys.exit(0)

    (palette, orphans) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)
    
    level_name = get_level_name(mesh_header, tags, data_map)
    mesh_size = mesh_tag.mesh_size(mesh_header)
    (game_type, units, diffs, max_points) = parse_game_teams(tags, data_map, palette, level_name, mesh_size)

    if not NO_TRADING:
        input_loop(game_type, units, diffs, max_points)

def get_level_name(mesh_header, tags, data_map):
    level_name_data = loadtags.get_tag_data(
        tags, data_map, 'stli', myth_headers.decode_string(
            mesh_header.map_description_string_list_tag
        )
    )
    (level_name_header, level_name_text) = myth_headers.parse_text_tag(level_name_data)
    return utils.ansi_format(myth_headers.decode_string(level_name_text.split(b'\r')[0]))

def sort_units(units):
    return sorted(units, key=lambda k : (not k['tradeable'], k['spellings']))

def set_initial_counts(units):
    if COUNTS:
        counts = COUNTS.split(',')
        for i, u in enumerate(units):
            if i < len(counts):
                u['count'] = int(counts[i])
    return units

def process_attacks(mons, tags, data_map):
    attacks = []


    (_, ex_prgr_header, ex_prgr_data) = loadtags.get_tag_info(
        tags, data_map, 'prgr', myth_headers.decode_string(
            mons.exploding_projectile_group_tag
        )
    )
    if ex_prgr_data:
        (ex_prgr_head, ex_prgr_projlist) = myth_projectile.parse_prgr(ex_prgr_data)
        for ex_prgr_proj in ex_prgr_projlist:
            (_, ex_proj_header, ex_proj_data) = loadtags.get_tag_info(
                tags, data_map, 'proj', myth_headers.decode_string(
                    ex_prgr_proj.projectile_tag
                )
            )
            ex_proj = myth_projectile.parse_proj(ex_proj_data)
            ex_dmg = ex_proj.damage.damage_lower_bound + ex_proj.damage.damage_delta
            if ex_dmg > 2:
                attacks.append({
                    'name': f'{ex_proj_header.name} (explosion)',
                    'throw': False,
                    'type': ex_proj.damage.type,
                    'dmg': ex_dmg,
                    'dps': ex_dmg,
                    'special': False,
                    'melee': False,
                    'aoe': myth_projectile.DamageFlags.AREA_OF_EFFECT in ex_proj.damage.flags,
                    'range': 0,
                })
    for attack in mons.attacks:
        if attack:
            (_, proj_header, proj_data) = loadtags.get_tag_info(
                tags, data_map, 'proj', myth_headers.decode_string(
                    attack.projectile_tag
                )
            )

            if mons_tag.AttackFlag.IS_REFLEXIVE in attack.flags:
                continue

            if not proj_data:
                if mons_tag.AttackFlag.USES_CARRIED_PROJECTLE in attack.flags:
                    attacks.append({
                        'name': 'throw',
                        'throw': True,
                        'type': None,
                        'dmg': None,
                        'dps': None,
                        'special': False,
                        'melee': False,
                        'aoe': False,
                        'range': attack.maximum_range,
                    })
                continue

            proj = myth_projectile.parse_proj(proj_data)
            if proj.damage.type == myth_projectile.DamageType.HEALING:
                continue

            dmg = proj.damage.damage_lower_bound + proj.damage.damage_delta
            seq_ticks = []
            recov_s = attack.recovery_time
            for attack_s in attack.sequences:
                if not attack_s:
                    continue

                (_, coll_header, coll_data) = loadtags.get_tag_info(
                    tags, data_map, '.256', myth_headers.decode_string(
                        mons.collection_tag
                    )
                )
                coll_head = myth_collection.parse_collection_header(coll_data, coll_header)
                seqs = myth_collection.parse_sequences(coll_data, coll_head)
                seq = seqs[attack_s.sequence_index]
                seq_meta = seq['metadata']

                ticks = (seq_meta.frames_per_view * seq_meta.ticks_per_frame)
                ticks += seq_meta.transfer_period
                seq_ticks.append(ticks)

                tick_s = ticks / 30
                time_s = tick_s + recov_s

                total_ticks = ticks + (recov_s * 30)
                dmg_per_tick = dmg / total_ticks
                dps = max(dmg, dmg / time_s)
                if DEBUG:
                    print(
                        f'{mons.collection_tag} [{seq['name']}] '
                        f'dmg={dmg} '
                        f'ticks={ticks} transfer={seq_meta.transfer_period} '
                        f'tick_s={tick_s} '
                        f'recov={recov_s} '
                        f'time_s={time_s} '
                        f'dpt={round(dmg_per_tick,2)} '
                        f'dps={round(dps,2)}'
                    )

            if len(seq_ticks):
                avg_tick_s = sum(seq_ticks) / len(seq_ticks) / 30
                avg_time_s = avg_tick_s + recov_s

                avg_dps = max(dmg, dmg / avg_time_s)

                attacks.append({
                    'name': proj_header.name,
                    'throw': False,
                    'type': proj.damage.type,
                    'dmg': dmg,
                    'dps': dps,
                    'special': mons_tag.AttackFlag.IS_SPECIAL_ABILITY in attack.flags,
                    'melee': myth_projectile.ProjFlags.MELEE_ATTACK in proj.flags,
                    'aoe': myth_projectile.DamageFlags.AREA_OF_EFFECT in proj.damage.flags,
                    'range': attack.maximum_range,
                })
    return attacks

def parse_game_teams(tags, data_map, palette, level_name, mesh_size):
    game_type_units = OrderedDict()
    has_stampede_targets = False
    has_assassin_target = False

    for unit in palette[mesh_tag.MarkerType.UNIT]:
        netgame_info = mesh_tag.netgame_flag_info(unit['netgame_flags'])
        team = unit['team_index']
        if team > -1 and len(netgame_info):
            tag_id = unit['tag']
            unit_data = loadtags.get_tag_data(tags, data_map, 'unit', tag_id)
            (mons_id, core) = mons_tag.parse_unit(unit_data)
            (mons_loc, mons_header, mons_data) = loadtags.get_tag_info(
                tags, data_map, 'mons', myth_headers.decode_string(mons_id)
            )
            mons = mons_tag.parse_tag(mons_data)

            obje_data = loadtags.get_tag_data(
                tags, data_map, 'obje', myth_headers.decode_string(mons.object_tag)
            )
            obje_tag = mons_tag.parse_obje(obje_data)

            if myth_headers.all_on(mons.spelling_string_list_tag) or myth_headers.all_off(mons.spelling_string_list_tag):
                spellings = [mons_header.name, mons_header.name]
            else:
                spelling_data = loadtags.get_tag_data(
                    tags, data_map, 'stli', myth_headers.decode_string(
                        mons.spelling_string_list_tag
                    )
                )
                (spelling_header, spelling_text) = myth_headers.parse_text_tag(spelling_data)
                spellings = [myth_headers.decode_string(s) for s in spelling_text.split(b'\r')]

            attacks = process_attacks(mons, tags, data_map)
            can_block = mons.sequence_indexes[5] > -1
            heal_kills = mons.healing_fraction == 0

            for netgame in netgame_info:
                if netgame not in game_type_units:
                    game_type_units[netgame] = {}
                if team not in game_type_units[netgame]:
                    game_type_units[netgame][team] = OrderedDict()
                if tag_id not in game_type_units[netgame][team]:
                    game_type_units[netgame][team][tag_id] = {
                        'team': unit['team_index'],
                        'spellings': spellings,
                        'tag_id': tag_id,
                        'count': 0,
                        'max': 0,
                        'cost': mons.cost,
                        'target': False,
                        'speed': mons.base_movement_speed,
                        'modifiers': obje_tag.effect_modifiers,
                        'attacks': attacks,
                        'can_block': can_block,
                        'heal_kills': heal_kills,
                        'min_vitality': obje_tag.vitality_lower_bound,
                        'max_vitality': obje_tag.vitality_lower_bound + obje_tag.vitality_delta,
                        'tradeable': mesh_tag.MarkerPaletteFlag.MAY_BE_TRADED in unit['flags'],
                    }
                    visible_count = 0
                    invisible_count = 0
                    for marker_id, marker in unit['markers'].items():
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
                    game_type_units[netgame][team][tag_id]['count'] += visible_count
                    game_type_units[netgame][team][tag_id]['max'] += visible_count + invisible_count

    if 'all' in game_type_units:
        included_game_types = list(mesh_tag.NetgameFlagInfo.values())
        if not has_stampede_targets:
            included_game_types.remove('stamp')
        if not has_assassin_target:
            included_game_types.remove('ass')
    else:
        included_game_types = list(game_type_units.keys())
    included_game_types.sort()

    game_type_nums = [
        f'{i+1:>2}) {NetgameNames[gt]}' for i, gt in enumerate(included_game_types)
    ]

    game_type_choice = GAME_TYPE
    if game_type_choice not in included_game_types:
        game_type_choice = None

    if not game_type_choice:
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
        trades[team] = team_trade_parts(game_type_choice, set_initial_counts(sort_units(
            list(merged_units.values())
        )))

    game_type = NetgameNames[game_type_choice]
    print(f"\n---\n\n{game_type}: {level_name} ({mesh_size})\n")

    mismatch = False
    for team_id, (total, diffs, trade) in trades.items():
        if trade != trades[0][2]:
            mismatch = True
            print('- Assymetric teams -')
            break
    if mismatch:
        for team_id, (total, diffs, trade) in trades.items():
            print(f"\nTeam {team_id}")
            print('\n'.join(trade))
        team_choice = int(input("\nChoose team: ").strip().lower())
    else:
        team_choice = 0
        print('\n'.join(trades[team_choice][2]))
    
    (max_points, diffs, trade) = trades[team_choice]

    final_merged_units = teams[team]
    if team_choice in shared_units:
        final_merged_units = shared_units[team_choice] | teams[team]
    units = sort_units(
        list(final_merged_units.values())
    )
    return (game_type_choice, units, diffs, max_points)

def input_loop(game_type, units, diffs, max_points):
    print("\n\x1b[1A", end='')
    while True:
        adjust = input("\x1b[KAdjust unit: (type unit num and count separated by a space, or num+ / num- for increment/decrement or num++ / num-- for max/min or num= to accept suggestion) ").strip().lower()
        unit = None
        count = None
        if match := re.match(r'^(\d+)\s+(\d+)$', adjust):
            unit = int(match.group(1)) - 1
            count = int(match.group(2))
        elif match := re.match(r'^(\d+)([+]{1,2}|[-]{1,2}|[=]{1,1})$', adjust):
            unit = int(match.group(1)) - 1
            op = match.group(2)
            if op == '-':
                count = units[unit]['count'] - 1
            elif op == '--':
                count = 0
            elif op == '+':
                count = units[unit]['count'] + 1
            elif op == '++':
                count = units[unit]['max']
            elif op == '=':
                count = units[unit]['count'] + diffs[unit]
        elif adjust in ['x','q']:
            sys.exit(0)

        if unit is not None and count is not None:
            units[unit]['count'] = min(count, units[unit]['max'])

        (total, diffs, trade) = team_trade_parts(game_type, units, max_points)
        # Move cursor up
        print(f"\x1b[{len(trade)+2}A", end='')
        for line in trade:
            print(f"\n\x1b[K{line}", end='')
        if unit is not None and count is not None:
            print(f"\x1b[K{units[unit]['spellings'][1]} -> {units[unit]['count']}")
        else:
            print(f"\x1b[K")

def team_trade_parts(game_type, units, max_points=None):
    trades = []
    divider = []
    untradeable = []
    suffix = []
    total = sum(u['cost']*u['count'] for u in units)
    diff = 0
    diffs = []
    if max_points:
        diff = max_points - total
    for i, u in enumerate(units):
        if u['target'] and game_type in ['ass', 'stamp']:
            afford = 0
        elif u['tradeable']:
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
            trades.append(
                f"{i+1:>2}) {u['spellings'][1]:<32}"
                f"{u['count']:>2} / "
                f"{u['max']:<2} "
                f"• cost: {u['cost']:<2} "
                f"• value: {(u['cost']*u['count']):<3} "
                f"{diff_amount} "
                f"{u['count']*'◼︎'}{(u['max'] - u['count'])*'◻︎'}"
            )
            if STATS:
                trades.append(graph('spd ', u['speed'], 15, 20, f" {u['speed']}"))
                if u['max_vitality'] == u['min_vitality']:
                    vit_range = f'{round(u['max_vitality'], 2)}'
                else:
                    vit_range = f'{round(u['min_vitality'], 2)} - {round(u['max_vitality'], 2)}'
                trades.append(graph('vit ', round(u['max_vitality']*2), 10, 20, f" {vit_range}"))
                for attack in u['attacks']:
                    special = " (special)" if attack['special'] else ""
                    aoe = " (aoe)" if attack['aoe'] else ""
                    attack_type = "melee" if attack['melee'] else "ranged"
                    if attack['dps']:
                        trades.append(graph('dps ', round(attack['dps']*2), 1, 5, f" {round(attack['dps'], 2)} (per hit: {round(attack['dmg'], 2)}) [{attack['type'].name} - {attack_type}] {attack['name']}{special}{aoe}"))
                    throw = ' (throw)' if attack['throw'] else ''
                    trades.append(graph('ran ', round(attack['range']*2), 5, 21, f" {round(attack['range'], 2)}{throw}"))

                if u['can_block']:
                    trades.append('    can \x1b[92mblock\x1b[0m')
                if u['heal_kills']:
                    trades.append('    \x1b[91mkilled by heal\x1b[0m')
                mods = u['modifiers']._asdict()
                puss_dur = mods['paralysis_duration']
                if puss_dur == 0:
                    trades.append('    \x1b[92mimmune\x1b[0m to puss')
                elif puss_dur > 1:
                    trades.append(f'    weak to puss: (\x1b[91m+{round((puss_dur-1)*100)}%\x1b[0m duration)')
                elif puss_dur < 1:
                    trades.append(f'    resistant to puss: (\x1b[92m-{round((1-puss_dur)*100)}%\x1b[0m duration)')

                for dmg in ['slashing', 'kinetic', 'explosive', 'electric', 'fire']:
                    damage = mods[f'{dmg}_damage']
                    if damage == 0:
                        trades.append(f'    \x1b[92mimmune\x1b[0m to {dmg}')
                    elif damage > 1:
                        trades.append(f'    weak to {dmg}: (\x1b[91m+{round((damage-1)*100)}%\x1b[0m)')
                    elif damage < 1:
                        trades.append(f'    resistant to {dmg}: (\x1b[92m-{round((1-damage)*100)}%\x1b[0m)')

        elif u['count']:
            afford = 0
            if len(untradeable) == 0:
                divider.append("")
                divider.append("Not tradeable:")
            untradeable.append(
                f"{u['spellings'][1]:<32}"
                f"count={u['count']:>2} "
            )
        else:
            afford = 0
        diffs.append(afford)
    suffix.append("")
    total_points = f"Total points: {total}"
    if max_points:
        total_points += f'/{max_points}'
        if total > max_points:
            total_points += f' \x1b[91mexcess: {total - max_points}\x1b[0m'
        elif max_points > total:
            total_points += f' \x1b[93mremaining: {max_points - total}\x1b[0m'
        else:
            total_points += ' \x1b[92mremaining: 0\x1b[0m'
    else:
        total_points += f'/{total} \x1b[92mremaining: 0\x1b[0m'

    suffix.append(total_points)
    suffix.append("")
    suffix.append("---")
    suffix.append("")
    return (total, diffs, trades + divider + untradeable + suffix)

def graph(pfx, value, low, medium, suffix=''):
    if value < low:
        color = "\x1b[91m"
    elif value < medium:
        color = "\x1b[93m"
    else:
        color = "\x1b[92m"
    return f"{pfx}{color}{value*'◼︎'}\x1b[0m{suffix}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mesh2trades.py <game_directory> [<level> [<plugin_names> ...]]")
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
