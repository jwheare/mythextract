#!/usr/bin/env python3
import os
import pathlib
import re
import struct
import sys
import time

import codec
import myth_headers
import myth_sound
import mesh_tag
import mono2tag
import mons_tag
import mesh2info
import loadtags
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
DIALOGUE_DEBUG = (os.environ.get('DIALOGUE_DEBUG') == '1')
TIME = (os.environ.get('TIME') == '1')
BLACKLIST = os.environ.get('BLACKLIST', '').split(',')
VERIFY = (os.environ.get('VERIFY') == '1')

def load_file(path):
    t = time.perf_counter()
    data = utils.load_file(path)
    TIME and print(path, f'{(time.perf_counter() - t):.3f}')

    return data

def main(game_directory, level, plugin_name, plugin_output):
    """
    Load Myth game tags and plugins and output basic text and html for the intro to a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, [plugin_name])

    try:
        if not level or level == 'list':
            plugin_names = [plugin_name] if plugin_name else None
            mono2tag.print_entrypoint_map(entrypoint_map, plugin_names=plugin_names)
        else:
            if game_version == 2 and level == 'all':
                for mesh_id, (entry_name, entry_long_name, archive_list) in entrypoint_map.items():
                    if mesh_id not in BLACKLIST:
                        if not plugin_name or plugin_name in archive_list:
                            if DEBUG or DIALOGUE_DEBUG:
                                print(f'mesh={mesh_id} file=[{archive_list}] [{entry_name}] [{entry_long_name}]')
                            plugin = plugin_name if plugin_name in archive_list else None
                            extract_level(game_version, tags, data_map, cutscenes, mesh_id, plugin, plugin_output)
            elif game_version == 1 and level == 'all':
                for level in range(1, 26):
                    (mesh_id, header_name, entry_name) = mesh2info.parse_level(f'{level:02}', tags)
                    if DEBUG or DIALOGUE_DEBUG:
                        print(f'level={level} mesh={mesh_id} file=[{header_name}] [{entry_name}]')
                    plugin = None
                    extract_level(game_version, tags, data_map, cutscenes, mesh_id, plugin, plugin_output)
            else:
                (mesh_id, header_name, entry_name) = mesh2info.parse_level(level, tags)
                if DEBUG or DIALOGUE_DEBUG:
                    print(f'level={level} mesh={mesh_id} file=[{header_name}] [{entry_name}]')
                plugin = plugin_name if plugin_name == header_name else None
                extract_level(game_version, tags, data_map, cutscenes, mesh_id, plugin, plugin_output)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def add_activator(
    backrefs, activators, action_id,
    act, subject,
    subtitle_tag, subtitle_idx, subtitle_string,
    color=None
):
    for (backref, backref_param, backref_param_i, _) in backrefs.get(action_id, []):
        if mesh_tag.action_param_is_activator(backref_param):
            if backref not in activators:
                activators[backref] = {}
            trigger_time = act['trigger_time_lower_bound']
            if trigger_time not in activators[backref]:
                activators[backref][trigger_time] = {}
            if backref_param not in activators[backref][trigger_time]:
                activators[backref][trigger_time][backref_param] = {}
            activators[backref][trigger_time][backref_param][action_id] = (
                backref_param_i,
                act,
                action_id,
                subject,
                subtitle_tag,
                subtitle_idx,
                subtitle_string,
                color
            )

def extract_level(game_version, tags, data_map, cutscene_paths, mesh_id, plugin, plugin_output):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
    tag_header = myth_headers.parse_header(mesh_tag_data)
    level = tag_header.name.split(' ')[0]

    mesh_header = mesh_tag.parse_header(mesh_tag_data)

    if plugin:
        prefix = plugin_output or plugin
    elif game_version == 2:
        prefix = 'myth2'
    elif game_version == 1:
        prefix = 'myth'
    else:
        prefix = 'unknown'

    # Extract dialogue
    stlis = {}
    sounds = {}
    (palette, _) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)
    units = palette.get(mesh_tag.MarkerType.UNIT, [])
    (actions, _) = mesh_tag.parse_map_actions(mesh_header, mesh_tag_data)
    backrefs = mesh_tag.build_action_backrefs(actions)
    activators = {}

    name_idxs = {}

    for i, (action_id, act) in enumerate(actions.items(), 1):
        if act['type'] == 'soun':
            sound_info = {}
            for p in act['parameters']:
                if p['name'] in ['soun', 'subj', 'over']:
                    sound_info[p['name']] = p['elements']
            if 'soun' in sound_info:
                if not len(sound_info['soun']):
                    print(f'‼️ Empty SOUN action: {act['name']}')
                else:
                    soun_tag = sound_info['soun'][0]
                    sound_header = sounds.get(soun_tag)
                    if not sound_header:
                        sound_data = loadtags.get_tag_data(tags, data_map, 'soun', soun_tag)
                        sound_header = myth_sound.parse_soun_header(sound_data)
                        sounds[soun_tag] = sound_header

                    subtitle_tag = codec.decode_string_none(sound_header.subtitle_string_list_tag)
                    if subtitle_tag:
                        subtitle_string = get_stli(
                            tags, data_map, stlis,
                            subtitle_tag, sound_header.first_subtitle_within_string_list_index
                        )
                        if subtitle_string:
                            add_activator(
                                backrefs, activators, action_id, act,
                                sound_info.get('subj', [None])[0],
                                subtitle_tag,
                                sound_header.first_subtitle_within_string_list_index,
                                subtitle_string
                            )
        elif act['type'] == 'ctrl':
            overhead_info = {}
            name_info = {}
            for p in act['parameters']:
                if p['name'] in ['nena', 'link', 'subj']:
                    name_info[p['name']] = p['elements']
                if p['name'] in ['otxt', 'otsi', 'otcl', 'subj']:
                    overhead_info[p['name']] = p['elements']
            if 'nena' in name_info and 'subj' in name_info:
                name_idxs[name_info['subj'][0]] = name_info['nena'][0]
            if 'nena' in name_info and 'link' in name_info:
                link_action = actions[name_info['link'][0]]
                for p in link_action['parameters']:
                    if p['name'] == 'subj':
                        name_idxs[p['elements'][0]] = name_info['nena'][0]
            if 'otxt' in overhead_info and 'otsi' in overhead_info:
                otxt_tag = overhead_info['otxt'][0]
                otsi = overhead_info['otsi'][0]
                otxt_string = get_stli(
                    tags, data_map, stlis,
                    otxt_tag, otsi
                )
                if otxt_string:
                    color = None
                    if 'otcl' in overhead_info and len(overhead_info['otcl']) == 3:
                        color = [int(x / 65535 * 255) for x in overhead_info['otcl']]
                    add_activator(
                        backrefs, activators, action_id, act,
                        overhead_info.get('subj', [None])[0],
                        otxt_tag,
                        otsi,
                        otxt_string,
                        color
                    )
    sound_tags = []
    stli_updates = {}
    ctrls_updated = False

    actions_processed = []

    if DEBUG or DIALOGUE_DEBUG:
        print(
            f"Actions: {len(actions)} / "
            f"Activators: {len(activators)} / "
            f"Backrefs: {len(backrefs)} / "
            f"Units: {len(units)}"
        )
    for backref_id, trigger_time_actions in activators.items():
        for trigger_time, param_actions in trigger_time_actions.items():
            for backref_param, act_actions in param_actions.items():
                print('---')
                if DEBUG or DIALOGUE_DEBUG:
                    print(
                        f"\x1b[90m[{backref_id}] {trigger_time} "
                        f"({actions[backref_id]['type'].upper()}) "
                        f"{actions[backref_id]['name']}\x1b[0m"
                    )
                soun_action = None
                ctrl_action = None
                subject = None
                subject_name = None
                subject_stli = None
                prefix_match = None
                subject_idx = None
                stli_updated = False
                ctrl_switched = False
                ctrl_color = None
                already_processed = False
                for (
                    backref_param_i, act, action_id, subject, stli, stli_idx, line, color
                ) in act_actions.values():
                    if action_id in actions_processed:
                        already_processed = True
                    actions_processed.append(action_id)

                    if act['type'] == 'soun':
                        soun_action = act
                        soun_stli = stli
                        soun_stli_idx = stli_idx
                    elif act['type'] == 'ctrl':
                        ctrl_action = act
                        ctrl_stli = stli
                        ctrl_stli_idx = stli_idx
                        ctrl_color = color
                    (subject_name, subject_stli, subject_idx) = get_subject_name(
                        game_version, tags, data_map, units, subject, name_idxs
                    )

                    if not subject_name:
                        if match := re.match(r'(?:CTRL )?([^:-]+)[:-].*', act['name']):
                            subject_name = match.group(1).strip()
                    prefix_match = re.match(r'([^:]+):.*', line)
                    if not already_processed and subject_name:
                        if not prefix_match:
                            stli_updated = True
                            new_content = codec.encode_string(f'{subject_name}: {line}')
                            (_, new_stli_header, new_stli_text) = update_stli(
                                tags, data_map, stlis, stli, stli_idx, new_content
                            )
                            stli_updates[stli] = (new_stli_header, new_stli_text)

                    if not already_processed and subject_stli is not None and subject_idx is not None and act['type'] == 'ctrl':
                        ctrl_switched = True
                        ctrls_updated = True
                        for p in act['parameters']:
                            if p['name'] == 'otxt':
                                p['elements'] = [subject_stli]
                            if p['name'] == 'otsi':
                                p['elements'] = [subject_idx]

                    if color:
                        (r, g, b) = color
                        line = f'\x1b[38;2;{r};{g};{b}m{line}\x1b[0m'
                        line += " (#{:02X}{:02X}{:02X})".format(r, g, b)

                    if DEBUG or DIALOGUE_DEBUG:
                        sep = '\n' if VERIFY else '- '
                        print(
                            f"\x1b[90m- {backref_param} "
                            f"[{action_id}] [{act['type']}.{act['name']}] "
                            f"- subj: {subject} {subject_name} "
                            f"- subj stli: {subject_stli}[{subject_idx}] "
                            f"- line stli: {stli}[{stli_idx}]\x1b[0m "
                            f"{sep}{line}"
                        )
                if VERIFY:
                    if ctrl_action:
                        if soun_action:
                            if soun_stli == ctrl_stli and soun_stli_idx == ctrl_stli_idx:
                                print('❌ SOUN matches CTRL')
                        else:
                            print('⚠️ SOUN missing')
                    else:
                        print('⚠️ CTRL missing')
                    continue
                if already_processed:
                    print('Already seen ⚠️♻️')
                if not ctrl_action:
                    if not soun_action:
                        print('SOUN missing ❌🔈')
                    elif subject_stli is not None and subject_idx is not None:
                        new_action_id = max(actions.keys()) + 1
                        action_params = [{
                            'type': mesh_tag.ParamType.FIELD_NAME,
                            'name': 'otxt',
                            'elements': [subject_stli],
                        }, {
                            'type': mesh_tag.ParamType.INTEGER,
                            'name': 'otsi',
                            'elements': [subject_idx],
                        }]
                        if subject:
                            action_params.append({
                                'type': mesh_tag.ParamType.MONSTER_IDENTIFIER,
                                'name': 'subj',
                                'elements': [subject],
                            })
                        new_ctrl_action = {
                            'type': 'ctrl',
                            'action_id': new_action_id,
                            'expiration_mode': soun_action['expiration_mode'],
                            'flags': soun_action['flags'],
                            'trigger_time_lower_bound': soun_action['trigger_time_lower_bound'],
                            'trigger_time_delta': soun_action['trigger_time_delta'],
                            'indent': soun_action['indent'],
                            'name': soun_action['name'],
                            'parameters': action_params,
                        }
                        actions[new_action_id] = new_ctrl_action
                        actions[backref_id]['parameters'][backref_param_i]['elements'].append(new_action_id)
                        ctrls_updated = True
                        print(f'CTRL created 🔵👤 action: [{new_action_id}] {subject_name}')
                    else:
                        print('CTRL missing ❌👤 SUBJ missing')

                    stli_value = get_stli(tags, data_map, stlis, soun_stli, soun_stli_idx)
                    if stli_updated:
                        print(f'STLI updated 🔵📜 (SOUN) {soun_stli}[{soun_stli_idx}] {stli_value}')
                    elif prefix_match:
                        print(f'STLI correct ✅📜 (SOUN) {soun_stli}[{soun_stli_idx}] {stli_value}')
                    else:
                        print('SUBJ missing ❌👤 (SOUN)')

                else:
                    if ctrl_switched:
                        ctrl_name = get_stli(tags, data_map, stlis, subject_stli, subject_idx)
                        if ctrl_color:
                            (r, g, b) = ctrl_color
                            ctrl_name = f'\x1b[38;2;{r};{g};{b}m{ctrl_name}\x1b[0m'
                        print(f'CTRL updated 🔵👤 {subject_stli}[{subject_idx}] {ctrl_name}')
                    else:
                        print('SUBJ unknown ⚠️👤')
                    stli_value = get_stli(tags, data_map, stlis, ctrl_stli, ctrl_stli_idx)
                    if stli_updated:
                        print(f'STLI updated 🔵📜 (CTRL) {ctrl_stli}[{ctrl_stli_idx}] {stli_value}')
                    elif prefix_match:
                        print(f'STLI correct ✅📜 (CTRL) {ctrl_stli}[{ctrl_stli_idx}] {stli_value}')
                    else:
                        print('SUBJ missing ❌👤 (CTRL)')
                    if soun_action:
                        if soun_stli == ctrl_stli and soun_stli_idx == ctrl_stli_idx:
                            print('SOUN matches ✅🔈')
                        else:
                            print('SOUN differs ❌🔈')
                    elif not already_processed:
                        # Create sound tag for dialogue
                        subject_slug = ''
                        if (subject_name):
                            subject_slug = f' ({utils.slugify(subject_name)})'
                        stli_bare_value = re.sub(r'(?:[^:]+): (.*)', r'\1', stli_value)
                        new_tag_name = f"{level}{subject_slug} {stli_bare_value}".encode('ascii')

                        tag_id_inc = ctrl_stli_idx
                        new_tag_id = (level[1:] + f'{tag_id_inc:02}')
                        if 'soun' in tags:
                            while new_tag_id in tags['soun']:
                                tag_id_inc += 1
                                new_tag_id = (level[1:] + f'{tag_id_inc:02}')

                        sound_tag = myth_sound.create_sound(ctrl_stli.encode('ascii'), ctrl_stli_idx)
                        new_sound_header = myth_headers.create_tag_header(
                            b'soun', new_tag_id.encode('ascii'), new_tag_name, len(sound_tag.value)
                        )
                        sound_tags.append((new_sound_header, sound_tag))
                        loadtags.append_tag_header(tags, new_sound_header, 'local')

                        new_action_id = max(actions.keys()) + 1

                        action_params = [{
                            'type': mesh_tag.ParamType.SOUND,
                            'name': 'soun',
                            'elements': [new_tag_id],
                        }]
                        if subject:
                            action_params.append({
                                'type': mesh_tag.ParamType.MONSTER_IDENTIFIER,
                                'name': 'subj',
                                'elements': [subject],
                            })
                        new_sound_action = {
                            'type': 'soun',
                            'action_id': new_action_id,
                            'expiration_mode': ctrl_action['expiration_mode'],
                            'flags': ctrl_action['flags'],
                            'trigger_time_lower_bound': ctrl_action['trigger_time_lower_bound'],
                            'trigger_time_delta': ctrl_action['trigger_time_delta'],
                            'indent': ctrl_action['indent'],
                            'name': ctrl_action['name'],
                            'parameters': action_params,
                        }
                        actions[new_action_id] = new_sound_action
                        actions[backref_id]['parameters'][backref_param_i]['elements'].append(new_action_id)

                        print(f'SOUN created 🔵🔈 action: [{new_action_id}] tag: [{new_tag_id}] {new_tag_name}')
    if not VERIFY:
        files_saved = 0
        if ctrls_updated or len(stli_updates) or len(sound_tags):
            new_mesh_tag_data = mesh_tag.encode_map_actions(mesh_tag_data, actions)
            out_path = pathlib.Path(sys.path[0], f'../output/mesh2dialogue/{prefix}').resolve()
            if True or prompt(out_path):
                mesh_tag_path = (out_path / f'{utils.local_folder(tag_header)}/{tag_header.name}')
                pathlib.Path(mesh_tag_path.parent).mkdir(parents=True, exist_ok=True)
                if not mesh_tag_path.is_file() or prompt(mesh_tag_path, '🚨 File exists. '):
                    with open(mesh_tag_path, 'wb') as new_mesh_tag_file:
                        new_mesh_tag_file.write(new_mesh_tag_data)
                        files_saved += 1

                for stli_id, (stli_header, stli_text) in stli_updates.items():
                    stli_tag_path = (
                        out_path / f'{utils.local_folder(stli_header)}/{stli_header.name}'
                    )
                    pathlib.Path(stli_tag_path.parent).mkdir(parents=True, exist_ok=True)

                    if not stli_tag_path.is_file() or prompt(stli_tag_path, '🚨 File exists. '):
                        with open(stli_tag_path, 'wb') as new_stli_tag_file:
                            new_stli_tag_file.write(stli_header.value + stli_text)
                            files_saved += 1

                for (sound_tag_header, sound_tag_content) in sound_tags:
                    sound_tag_path = (
                        out_path / f'{utils.local_folder(sound_tag_header)}/{sound_tag_header.name}'
                    )
                    pathlib.Path(sound_tag_path.parent).mkdir(parents=True, exist_ok=True)
                    if not sound_tag_path.is_file() or prompt(sound_tag_path, '🚨 File exists. '):
                        with open(sound_tag_path, 'wb') as new_sound_tag_file:
                            new_sound_tag_file.write(sound_tag_header.value + sound_tag_content.value)
                            files_saved += 1
        print('---')
        print(f'Files saved: {files_saved}')
    print('---------------------------------\n\n')


def get_stli(tags, data_map, stlis, tag_name, stli_idx):
    if tag_name not in stlis:
        tag_data = loadtags.get_tag_data(tags, data_map, 'stli', tag_name)
        if not tag_data:
            print(f'‼️ Missing STLI tag: {tag_name}')
        else:
            (tag_header, tag_text) = myth_headers.parse_text_tag(tag_data)
            strings = myth_headers.parse_stli(tag_text)
            stlis[tag_name] = (strings, tag_header, tag_text)
    if tag_name in stlis and len(stlis[tag_name][0]) > stli_idx:
        return stlis[tag_name][0][stli_idx]

def update_stli(tags, data_map, stlis, tag_name, stli_idx, new_content):
    (_, tag_header, tag_text) = stlis[tag_name]
    new_tag_text = myth_headers.update_stli(tag_text, stli_idx, new_content)
    new_stli_header = myth_headers.normalise_tag_header(
        tag_header,
        tag_data_size=len(new_tag_text)
    )
    stlis[tag_name] = (myth_headers.parse_stli(new_tag_text), new_stli_header, new_tag_text)
    return stlis[tag_name]

def get_subject_name(game_version, tags, data_map, units, subject, name_idxs):
    if subject:
        for obje in units:
            if subject in obje['markers']:
                unit_data = loadtags.get_tag_data(tags, data_map, 'unit', obje['tag'])
                unit_tag = mons_tag.parse_unit(unit_data)
                if unit_tag.mons:
                    (mons_loc, mons_header, mons_data) = loadtags.get_tag_info(
                        tags, data_map, 'mons', codec.decode_string(unit_tag.mons)
                    )
                    mons = mons_tag.parse_tag(game_version, mons_data)
                    (names, names_stli) = mons_tag.get_names(tags, data_map, mons, mons_header)
                    (spellings, spelling_stli) = mons_tag.get_spellings(tags, data_map, mons, mons_header)
                    filter_names = [n for n in names if n]
                    if len(filter_names) == 1:
                        return (filter_names[0], codec.decode_string(names_stli), 0)
                    elif subject in name_idxs:
                        name_idx = name_idxs[subject]
                        if len(names) > name_idx:
                            return (names[name_idx], codec.decode_string(names_stli), name_idx)

                    return (spellings[0], codec.decode_string(spelling_stli), 0)
    return (None, None, None)

def prompt(prompt_path, msg=''):
    print(msg, prompt_path)
    return True
    # response = input(f"{msg}Write to: {prompt_path} [Y/n]: ").strip().lower()
    # return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> [<level> [<plugin_name> [<plugin_output>]]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_name = None
    plugin_output = None
    if len(sys.argv) > 2:
        level = sys.argv[2]
        if len(sys.argv) > 3:
            plugin_name = sys.argv[3]
            if len(sys.argv) == 5:
                plugin_output = sys.argv[4]

    try:
        main(game_directory, level, plugin_name, plugin_output)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
