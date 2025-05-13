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

def main(game_directory, mons_id, plugin_names):
    """
    Load Myth game tags and plugins and output stats for all monsters
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if mons_id == 'all':
            for mons_id, locations in tags['mons'].items():
                print_mons_stats(game_version, tags, data_map, mons_id)
        else:
            print_mons_stats(game_version, tags, data_map, mons_id)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def print_mons_stats(game_version, tags, data_map, mons_id):
    (mons_loc, mons_header, mons_data) = loadtags.get_tag_info(
        tags, data_map, 'mons', mons_id
    )
    mons_dict = get_mons_dict(tags, data_map, mons_header, mons_data)
    print(f"[{mons_id}] {mons_dict['spellings'][0]} ({mons_header.name})")
    lines = mons_stats(mons_dict)
    print('\n'.join(lines))
    print('================================')

def get_mons_dict(tags, data_map, mons_header, mons_data):
    mons = mons_tag.parse_tag(mons_data)

    obje_data = loadtags.get_tag_data(
        tags, data_map, 'obje', utils.decode_string(mons.object_tag)
    )
    obje_tag = mons_tag.parse_obje(obje_data)

    if utils.all_on(mons.spelling_string_list_tag) or utils.all_off(mons.spelling_string_list_tag):
        spellings = [mons_header.name, mons_header.name]
    else:
        spelling_data = loadtags.get_tag_data(
            tags, data_map, 'stli', utils.decode_string(
                mons.spelling_string_list_tag
            )
        )
        (spelling_header, spelling_text) = myth_headers.parse_text_tag(spelling_data)
        spellings = [utils.decode_string(s) for s in spelling_text.split(b'\r')]

    attacks = process_attacks(mons, tags, data_map)
    can_block = mons.sequence_indexes[5] > -1
    heal_kills = mons.healing_fraction == 0

    return {
        'spellings': spellings,
        'class': mons.monster_class,
        'cost': mons.cost,
        'speed': mons.base_movement_speed,
        'modifiers': obje_tag.effect_modifiers,
        'attacks': attacks,
        'can_block': can_block,
        'heal_kills': heal_kills,
        'min_vitality': obje_tag.vitality_lower_bound,
        'max_vitality': obje_tag.vitality_lower_bound + obje_tag.vitality_delta,
    }


def process_attacks(mons, tags, data_map):
    attacks = []

    (_, ex_prgr_header, ex_prgr_data) = loadtags.get_tag_info(
        tags, data_map, 'prgr', utils.decode_string(
            mons.exploding_projectile_group_tag
        )
    )
    if ex_prgr_data:
        (ex_prgr_head, ex_prgr_projlist) = myth_projectile.parse_prgr(ex_prgr_data)
        for ex_prgr_proj in ex_prgr_projlist:
            (_, ex_proj_header, ex_proj_data) = loadtags.get_tag_info(
                tags, data_map, 'proj', utils.decode_string(
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
                tags, data_map, 'proj', utils.decode_string(
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
                        'type': myth_projectile.DamageType.NONE,
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
                    tags, data_map, '.256', utils.decode_string(
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
                dmg_per_tick = dmg / max(1, total_ticks)
                dps = max(dmg, dmg / max(1/30, time_s))
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

                avg_dps = max(dmg, dmg / max(1/30, avg_time_s))

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

def mons_stats(mons_dict):
    lines = []
    lines.append(graph('   speed ', mons_dict['speed'], 15, 20, f" {mons_dict['speed']}"))
    if mons_dict['max_vitality'] == mons_dict['min_vitality']:
        vit_range = f'{round(mons_dict['max_vitality'], 2)}'
    else:
        vit_range = f'{round(mons_dict['min_vitality'], 2)} - {round(mons_dict['max_vitality'], 2)}'
    lines.append(graph('vitality ', round(mons_dict['max_vitality']*2), 10, 20, f" {vit_range}"))
    for attack in mons_dict['attacks']:
        special = " (special)" if attack['special'] else ""
        aoe = " (aoe)" if attack['aoe'] else ""
        attack_type = "melee" if attack['melee'] else "ranged"
        attack_details = f" [{utils.cap_title(attack['type'].name)} - {attack_type}] {attack['name']}{special}{aoe}"
        if attack['dps']:
            lines.append(graph('     dps ', round(attack['dps']*2), 1, 5, f" {round(attack['dps'], 2)} (per hit: {round(attack['dmg'], 2)}){attack_details}"))
            attack_details = ''
        throw = ' (throw)' if attack['throw'] else ''
        lines.append(graph('   range ', round(attack['range']*2), 5, 21, f" {round(attack['range'], 2)}{throw}{attack_details}"))

    indent = '         '

    if mons_dict['can_block']:
        lines.append(f'{indent}can \x1b[92mblock\x1b[0m')
    if mons_dict['heal_kills']:
        lines.append(f'{indent}\x1b[91mkilled by heal\x1b[0m')
    mods = mons_dict['modifiers']._asdict()
    puss_dur = mods['paralysis_duration']
    if puss_dur == 0:
        lines.append(f'{indent}\x1b[92mimmune\x1b[0m to puss')
    elif puss_dur > 1:
        lines.append(f'{indent}weak to puss: (\x1b[91m+{round((puss_dur-1)*100)}%\x1b[0m duration)')
    elif puss_dur < 1:
        lines.append(f'{indent}resistant to puss: (\x1b[92m-{round((1-puss_dur)*100)}%\x1b[0m duration)')

    for dmg in ['slashing', 'kinetic', 'explosive', 'electric', 'fire']:
        damage = mods[f'{dmg}_damage']
        if damage == 0:
            lines.append(f'{indent}\x1b[92mimmune\x1b[0m to {dmg}')
        elif damage > 1:
            lines.append(f'{indent}weak to {dmg}: (\x1b[91m+{round((damage-1)*100)}%\x1b[0m)')
        elif damage < 1:
            lines.append(f'{indent}resistant to {dmg}: (\x1b[92m-{round((1-damage)*100)}%\x1b[0m)')

    return lines

def graph(pfx, value, low, medium, suffix=''):
    if value < low:
        color = "\x1b[91m"
    elif value < medium:
        color = "\x1b[93m"
    else:
        color = "\x1b[92m"
    return f"{pfx}{color}{value*'◼︎'}\x1b[0m{suffix}"

def graph_emoji(pfx, value, low, medium, suffix=''):
    if value < low:
        square = "🟥"
    elif value < medium:
        square = "🟨"
    else:
        square = "🟩"
    return f"{pfx}{value * square}{suffix}"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 mons2stats.py <game_directory> <mons_id> [<plugin_names> ...]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    mons_id = sys.argv[2]
    plugin_names = []
    if len(sys.argv) > 3:
        plugin_names = sys.argv[3:]

    try:
        main(game_directory, mons_id, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
