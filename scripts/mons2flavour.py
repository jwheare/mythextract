#!/usr/bin/env python3
import os
import pathlib
import struct
import sys

import codec
import loadtags
import mesh_tag
import mons_tag
import mons2stats
import myth_headers
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, input_mons_id, plugin_names):
    """
    Load Myth game tags and plugins and output stats as flavour text for monsters
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        write_flavours(tags, data_map, input_mons_id)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def collect_flavours(tags, data_map, input_mons_id):
    for (mons_id, mons_dict, mons_header, flavour) in generate_flavour(tags, data_map, input_mons_id):
        if DEBUG:
            print(f"[{mons_id}] {mons_dict['spellings'][0]} ({mons_header.name})")
            print(flavour)

        if not mons_dict['flavour_stli']:
            print(f"[{mons_id}] Missing flavour: {mons_dict['spellings'][0]} ({mons_header.name})")

        if DEBUG:
            print('================================')

        if mons_dict['flavour_stli']:
            yield (mons_dict['flavour_stli'], flavour)

def encode_flavour(tags, data_map, flavour_stli, flavour):
    (stli_loc, stli_header, stli_data) = loadtags.get_tag_info(
        tags, data_map, 'stli', flavour_stli
    )

    flavour_data = codec.encode_string(flavour)
    # Adjust tag header size
    new_tag_header = myth_headers.normalise_tag_header(
        stli_header, 
        tag_data_size=len(flavour_data)
    )
    return (new_tag_header, flavour_data)

def generate_flavour(tags, data_map, input_mons_id):
    if input_mons_id == 'all':
        for mons_id, locations in tags['mons'].items():
            if not plugin_names or set(loc[0] for loc in locations) == set(plugin_names):
                yield get_flavour(tags, data_map, mons_id)
    elif input_mons_id.startswith('mesh='):
        mesh_id = input_mons_id[5:]

        (mesh_tag_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(
            tags, data_map, 'mesh', mesh_id
        )
        mesh_header = mesh_tag.parse_header(mesh_tag_data)
        (palette, _) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)

        for unit in palette[mesh_tag.MarkerType.UNIT]:
            if unit['team_index'] == 0:
                unit_data = loadtags.get_tag_data(tags, data_map, 'unit', unit['tag'])
                unit_tag = mons_tag.parse_unit(unit_data)
                yield get_flavour(tags, data_map, codec.decode_string(unit_tag.mons))
    else:
        yield get_flavour(tags, data_map, input_mons_id)

def get_flavour(tags, data_map, mons_id):
    (mons_loc, mons_header, mons_data) = loadtags.get_tag_info(
        tags, data_map, 'mons', mons_id
    )
    mons_dict = mons2stats.get_mons_dict(tags, data_map, mons_header, mons_data)
    return (mons_id, mons_dict, mons_header, mons_flavour(mons_dict))

def write_flavours(tags, data_map, input_mons_id):
    flavours = collect_flavours(tags, data_map, input_mons_id)

    output_dir = '../output/mons2flavour/local'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    if prompt(output_path):
        for (flavour_stli, flavour) in flavours:
            (tag_header, flavour_data) = encode_flavour(tags, data_map, flavour_stli, flavour)

            file_path = (output_path / f'{utils.local_folder(tag_header)}/{tag_header.name}')
            pathlib.Path(file_path.parent).mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as tag_file:
                tag_file.write(myth_headers.encode_header(tag_header))
                tag_file.write(flavour_data)

            print(f"Flavour STLI generated. Output saved to {file_path}")

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def pct(val):
    return round(val * 100, 1)

def mons_flavour(mons_dict):
    can_block = "[This unit can block] " if mons_dict['can_block'] else ""
    heal_percent = pct(mons_dict['healing_fraction'])

    if mons_dict['flinch_system_shock'] > 0:
        flinch_percent = pct(mons_dict['flinch_system_shock'])
        flinch = f"[Flinches when damage source does {flinch_percent}% or more of health.] "
    else:
        flinch = "[Flinches] "

    stone = ''
    if mons_dict['stone']:
        stone = '[Turns to Stone at 25% of health] '

    absorbtion = ''
    if mons_dict['absorbed_fraction'] > 0:
        absorbtion_percent = pct(mons_dict['absorbed_fraction'])
        absorbtion = f"[Absorbs attack damage, {absorbtion_percent}% of the time] "

    heal_fraction = f"[Heals {heal_percent}%]" if heal_percent else "[Heal kills]"

    mana = ''
    if mons_dict['maximum_mana'] > 0:
        mana = (
            f"[Max Mana: {round(mons_dict['maximum_mana'], 1)} "
            f"Mana recharge rate: {round(mons_dict['mana_recharge_rate'], 3)}] "
        )
    berserk = ''
    if mons_dict['berserk_vitality'] > 0:
        berserk_percent = pct(mons_dict['berserk_vitality'])
        berserk = f"[Goes berserk at {berserk_percent}% of health] "

    main_attack_text = ''
    main_attack = next((a for a in mons_dict['attacks'] if a['primary']), None)
    if main_attack:
        main_attack_parts = [
            # f"Main attack damage: {round(main_attack['dmg'], 1)} recovery time: {main_attack['recovery']}s."
            f"Main attack recovery time: {round(main_attack['recovery'], 2)}s."
        ]
        acc = main_attack['velocity_error']
        if acc > 0:
            main_attack_parts.append(f"Accuracy: {pct(1-acc)}%.")

        if main_attack['vet_recovery'] > 0 or main_attack['vet_velocity'] > 0:
            main_attack_parts.append("Vetting improvement per kill(up to 5):")
            if main_attack['vet_recovery'] > 0:
                main_attack_parts.append(f"Recovery time {round(main_attack['vet_recovery'], 2)}s.")
            if main_attack['vet_velocity'] > 0:
                main_attack_parts.append(f"Accuracy: {pct(main_attack['vet_velocity'])}%")

        main_attack_text = f'[{" ".join(main_attack_parts)}] '

        if main_attack['unblockable']:
            main_attack_text = f"[Attack cannot be blocked] {main_attack_text}"

    mods = mons_dict['modifiers']._asdict()
    puss_dur = mods['paralysis_duration']
    puss_effect = ''
    if puss_dur == 0:
        puss_effect = "Immune to Paralysis. "
    elif puss_dur != 1:
        puss_effect = f"Effect duration {pct(puss_dur)}% from Paralysis. "

    mod_amounts = {}
    for dmg in ['slashing', 'kinetic', 'explosive', 'electric', 'fire']:
        type_damage = mods[f'{dmg}_damage']
        if type_damage != 1:
            if type_damage not in mod_amounts:
                mod_amounts[type_damage] = []
            mod_amounts[type_damage].append(dmg)

    type_amounts = []
    for type_amount, dmg_types in mod_amounts.items():
        if type_amount == 0:
            type_amounts.append(f"Immune to {', '.join(dmg_types)} Damage. ")
        else:
            type_amounts.append(f"Takes {pct(type_amount)}% damage from {', '.join(dmg_types)} Damage. ")
    type_amounts_text = ''.join(type_amounts)

    terrain_mod_amounts = {}
    for terrain, t_mod in mons_dict['movement_modifiers'].items():
        if t_mod > 0 and t_mod != 1:
            if t_mod not in terrain_mod_amounts:
                terrain_mod_amounts[t_mod] = []
            terrain_mod_amounts[t_mod].append(terrain)

    terrain_amounts = []
    for terrain_amount, terrain_types in terrain_mod_amounts.items():
        if set(terrain_types) == set(['dwarf_depth_media', 'human_depth_media', 'giant_depth_media', 'really_deep_media']):
            terrain_amounts.append(f"Speed in water: {pct(terrain_amount)}% ")
        else:
            tt = [utils.cap_title(t.removesuffix('_media')) for t in terrain_types]
            terrain_amounts.append(f"Speed on {', '.join(tt)} terrain: {pct(terrain_amount)}% ")
    terrain_amounts_text = ''.join(terrain_amounts)

    if mons_dict['min_vitality'] == mons_dict['max_vitality']:
        health = f"Starting Health: {round(mons_dict['max_vitality'], 2)}."
    else:
        health = f"Starting Health Range: {round(mons_dict['min_vitality'], 2)} - {round(mons_dict['max_vitality'], 2)}."

    flavour = (
        f"{health} "
        f"{type_amounts_text}"
        f"{puss_effect}"
        f"{heal_fraction} "
        f"[Base Walking Speed: {round(mons_dict['speed'], 3)}. "
        f"{terrain_amounts_text}"
        f"Turning Speed: {round(mons_dict['turning_speed'])}] "
        f"{flinch}"
        f"{stone}"
        f"{absorbtion}"
        f"{mana}"
        f"{berserk}"
        f"{main_attack_text}"
        f"{can_block}"
        f"[Unit Trade Value: {mons_dict['cost']}] "
    )
    return flavour

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 mons2flavour.py <game_directory> <mons_id> [<plugin_names> ...]")
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
