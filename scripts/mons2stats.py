#!/usr/bin/env python3
import os
import struct
import sys

import loadtags
import mons_tag
import myth_headers
import myth_projectile
import myth_collection
import utils

DEBUG_STATS = (os.environ.get('DEBUG_STATS') == '1')

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

    can_block = mons.sequence_indexes[5] > -1
    heal_kills = mons.healing_fraction == 0

    attacks = process_attacks(mons, tags, data_map)

    return {
        'spellings': spellings,
        'class': mons.monster_class,
        'cost': mons.cost,
        'speed': mons.base_movement_speed,
        'movement_modifiers': mons.movement_modifiers._asdict(),
        'turning_speed': mons.turning_speed,
        'flavour_stli': utils.decode_string_none(mons.flavor_string_list_tag),
        'modifiers': obje_tag.effect_modifiers,
        'attacks': attacks,
        'can_block': can_block,
        'heal_kills': heal_kills,
        'stone': mons_tag.MonsFlag.TURNS_TO_STONE_WHEN_KILLED in mons.flags,
        'min_vitality': obje_tag.vitality_lower_bound,
        'max_vitality': obje_tag.vitality_lower_bound + obje_tag.vitality_delta,
        'healing_fraction': mons.healing_fraction,
        'flinch_system_shock': mons.flinch_system_shock,
        'absorbed_fraction': mons.absorbed_fraction,
        'maximum_mana': mons.maximum_mana,
        'mana_recharge_rate': mons.mana_recharge_rate,
        'berserk_system_shock': mons.berserk_system_shock,
        'berserk_vitality': mons.berserk_vitality,
    }

def sequence(tags, data_map, collection_tag, sequence_index):
    (_, coll_header, coll_data) = loadtags.get_tag_info(
        tags, data_map, '.256', utils.decode_string(collection_tag)
    )
    coll_head = myth_collection.parse_collection_header(coll_data, coll_header)
    seqs = myth_collection.parse_sequences(coll_data, coll_head)
    return seqs[sequence_index]

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
                ex_radius = ex_proj.damage.radius_lower_bound + ex_proj.damage.radius_delta
                attacks.append({
                    'name': f'{ex_proj_header.name} (explosion)',
                    'throw': False,
                    'type': ex_proj.damage.type,
                    'dmg': ex_dmg,
                    'dps': ex_dmg,
                    'special': False,
                    'melee': False,
                    'aoe': myth_projectile.DamageFlags.AREA_OF_EFFECT in ex_proj.damage.flags,
                    'radius': ex_radius,
                    'paralysis': myth_projectile.DamageFlags.CAN_CAUSE_PARALYSIS in ex_proj.damage.flags,
                    'unblockable': myth_projectile.DamageFlags.CANNOT_BE_BLOCKED in ex_proj.damage.flags,
                    'range': 0,
                    'recovery': 0,
                    'mana_cost': 0,
                    'min_velocity': 0,
                    'max_velocity': 0,
                    'velocity_error': 0,
                    'vet_recovery': 0,
                    'vet_velocity': 0,
                    'primary': False,
                })
    for attack_i in range(mons.number_of_attacks):
        attack = mons.attacks[attack_i]
        if attack:
            (_, proj_header, proj_data) = loadtags.get_tag_info(
                tags, data_map, 'proj', utils.decode_string(
                    attack.projectile_tag
                )
            )

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
                        'radius': 0,
                        'paralysis': False,
                        'unblockable': False,
                        'range': attack.maximum_range,
                        'recovery': attack.recovery_time,
                        'mana_cost': attack.mana_cost,
                        'min_velocity': attack.initial_velocity_lower_bound,
                        'max_velocity': attack.initial_velocity_lower_bound + attack.initial_velocity_delta,
                        'velocity_error': attack.initial_velocity_error,
                        'vet_recovery': attack.recovery_time_experience_delta,
                        'vet_velocity': attack.velocity_improvement_with_experience,
                        'primary': mons_tag.AttackFlag.IS_PRIMARY_ATTACK in attack.flags,
                    })
                continue

            proj = myth_projectile.parse_proj(proj_data)
            if proj.damage.type == myth_projectile.DamageType.HEALING:
                continue

            if (
                mons_tag.AttackFlag.IS_REFLEXIVE in attack.flags and
                myth_projectile.DamageFlags.CANNOT_HURT_OWNER not in proj.damage.flags
            ):
                continue

            dmg = proj.damage.damage_lower_bound + proj.damage.damage_delta

            avg_time_s = None
            attack_radius = proj.damage.radius_lower_bound + proj.damage.radius_delta
            attack_range = attack.maximum_range
            if myth_projectile.ProjFlags.CONTINUALLY_DETONATES in proj.flags:
                avg_time_s = 1/30
            else:
                seq_times = []
                recov_s = attack.recovery_time + 0.2
                for attack_si, attack_s in enumerate(attack.sequences):
                    if not attack_s:
                        continue

                    seq = sequence(tags, data_map, mons.collection_tag, attack_s.sequence_index)
                    seq_meta = seq['metadata']

                    ticks = (
                        seq_meta.frames_per_view * seq_meta.ticks_per_frame
                    )

                    tick_s = ticks / 30
                    transfer_s = seq_meta.transfer_period / 30
                    time_s = max(tick_s, tick_s + recov_s)

                    seq_times.append(time_s)
                    dps = dmg / max(1/30, time_s)
                    if DEBUG_STATS:
                        print(
                            f'{mons.collection_tag} [{proj_header.name}] [{attack_i} {attack_si} {seq['name']}] '
                            f'dmg={dmg} '
                            f'ticks={ticks} '
                            f'transfer={seq_meta.transfer_period} '
                            f'tick_s={tick_s} '
                            f'recov={recov_s} '
                            f'time_s={time_s} '
                            f'dps={round(dps,2)}'
                        )

                if len(seq_times):
                    avg_time_s = sum(seq_times) / len(seq_times)

            if avg_time_s:
                avg_dps = dmg / avg_time_s
                attacks.append({
                    'name': proj_header.name,
                    'throw': False,
                    'type': proj.damage.type,
                    'dmg': dmg,
                    'attack_time': avg_time_s,
                    'dps': avg_dps,
                    'special': mons_tag.AttackFlag.IS_SPECIAL_ABILITY in attack.flags,
                    'melee': myth_projectile.ProjFlags.MELEE_ATTACK in proj.flags,
                    'aoe': myth_projectile.DamageFlags.AREA_OF_EFFECT in proj.damage.flags,
                    'radius': attack_radius,
                    'paralysis': myth_projectile.DamageFlags.CAN_CAUSE_PARALYSIS in proj.damage.flags,
                    'unblockable': myth_projectile.DamageFlags.CANNOT_BE_BLOCKED in proj.damage.flags,
                    'range': attack_range,
                    'recovery': recov_s,
                    'mana_cost': attack.mana_cost,
                    'min_velocity': attack.initial_velocity_lower_bound,
                    'max_velocity': attack.initial_velocity_lower_bound + attack.initial_velocity_delta,
                    'velocity_error': attack.initial_velocity_error,
                    'vet_recovery': attack.recovery_time_experience_delta,
                    'vet_velocity': attack.velocity_improvement_with_experience,
                    'primary': mons_tag.AttackFlag.IS_PRIMARY_ATTACK in attack.flags,
                })
    return attacks

def mons_stats(mons_dict):
    lines = []
    lines.append(graph('   speed ', round(mons_dict['speed']), 15, 20, f" {round(mons_dict['speed'], 3)}"))
    if mons_dict['max_vitality'] == mons_dict['min_vitality']:
        vit_range = f'{round(mons_dict['max_vitality'], 2)}'
    else:
        vit_range = f'{round(mons_dict['min_vitality'], 2)} - {round(mons_dict['max_vitality'], 2)}'
    lines.append(graph('vitality ', round(mons_dict['max_vitality']*2), 10, 20, f" {vit_range}"))
    for attack in mons_dict['attacks']:
        special = " (special)" if attack['special'] else ""
        aoe = " (aoe)" if attack['aoe'] else ""
        paralysis = " (paralyses)" if attack['paralysis'] else ""
        attack_type = "melee" if attack['melee'] else "ranged"
        attack_details = f" [{utils.cap_title(attack['type'].name)} - {attack_type}] {attack['name']}{special}{aoe}{paralysis}"
        if attack['dps']:
            recov = ''
            if attack['mana_cost'] > 0:
                mana_recharge_time = (attack['mana_cost'] / (mons_dict['mana_recharge_rate'] * 30))
                recov = f' (mana recovery: {round(mana_recharge_time, 1)}s)'
            elif 'attack_time' in attack:
                recov = f' (recovery: {round(attack['recovery'], 2)}s total_time: {round(attack['attack_time'], 2)}s)'
            lines.append(graph('     dmg ', round(attack['dmg']*2), 1.2, 4, f" {round(attack['dmg'], 2)}{attack_details}"))
            lines.append(graph('     dps ', round(attack['dps']*2), 1.2, 4, f" {round(attack['dps'], 2)}{recov}"))
            attack_details = ''
        throw = ' (throw)' if attack['throw'] else ''
        if attack['range']:
            lines.append(graph('   range ', round(attack['range']*2), 5, 21, f" {round(attack['range'], 2)}{throw}{attack_details}"))
        if attack['radius']:
            lines.append(graph('  radius ', round(attack['radius']*2), 5, 21, f" {round(attack['radius'], 2)}"))

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
