#!/usr/bin/env python3
import sys
import os
import struct

import myth_headers
import mesh_tag
import mesh2info
import mono2tag
import loadtags
import utils
import action_browser


DEBUG = (os.environ.get('DEBUG') == '1')
VALIDATE = (os.environ.get('VALIDATE') == '1')
DEBUG_LINK = (os.environ.get('DEBUG_LINK') == '1')

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output scripting actions for a mesh
    """
    try:
        (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

        if not level or level == 'list':
            mono2tag.print_entrypoint_map(entrypoint_map, plugin_names=plugin_names)
            mesh_input = input('Choose a mesh id: ')
            main(game_directory, f'mesh={mesh_input}', plugin_names)
        else:
            action_templates = {}
            if VALIDATE:
                action_templates = action_browser.build_action_help(tags, data_map)
            if level.startswith('file='):
                file = level[5:]
                mesh_tag_data = utils.load_file(file)
                parse_mesh_actions(file, mesh_tag_data, action_templates, plugin_names)
            else:
                for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):

                    (mesh_tag_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(
                        tags, data_map, 'mesh', mesh_id
                    )
                    if myth_headers.tag_has_data(mesh_tag_data):
                        parse_mesh_actions(mesh_tag_location, mesh_tag_data, action_templates, plugin_names)
                    else:
                        print("Missing mesh tag data", mesh_id)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_mesh_actions(mesh_tag_location, mesh_tag_data, action_templates, plugin_names):
    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    tag_header = myth_headers.parse_header(mesh_tag_data)

    (actions, action_remainder) = mesh_tag.parse_map_actions(mesh_header, mesh_tag_data)
    print_actions(actions, tag_header, action_templates, plugin_names)

    if action_remainder:
        print(f'ACTION REMAINDER count={len(action_remainder)} mesh=[{tag_header.tag_id}] {tag_header.name} ({mesh_tag_location})')
        print(action_remainder.hex())

def print_actions(actions, tag_header, action_templates, plugin_names):
    for i, (action_id, act) in enumerate(actions.items(), 1):
        indent_space = act['indent'] * '  '
        prefix = ''
        if act['type']:
            prefix = f'{act['type'].upper()}.'

        action_vars = []
        if len(act['parameters']):
            if act['flags']:
                action_vars.append(','.join([f.name.lower() for f in act['flags']]))
            if act['expiration_mode'] != mesh_tag.ActionExpiration.TRIGGER:
                action_vars.append(f'expiry={act['expiration_mode'].name.lower()}')
            if act['trigger_time_lower_bound']:
                action_vars.append(f'delay={round(act['trigger_time_lower_bound'], 3)}s')
            if act['trigger_time_delta']:
                action_vars.append(f'dur={round(act['trigger_time_delta'], 3)}s')

        if len(act['parameters']):
            id_prefix = f'[{action_id}] '
        else:
            id_prefix = '        '
        # tag_prefix = f'{tag_header.tag_type}={tag_header.tag_id} {tag_header.name} '
        tag_prefix = ''
        line = f'{id_prefix}{indent_space}{prefix}{act['name']}'
        if mesh_tag.ActionFlag.INITIALLY_ACTIVE in act['flags']:
            print(f'{tag_prefix}\x1b[1m{line}\x1b[0m')
        else:
            print(f'{tag_prefix}{line}')
        for p in act['parameters']:
            print(f'{tag_prefix}        {indent_space}- {p['name']} {p['type'].name}={p['elements']}')
            param_name = p['name']
            element_count = len(p['elements'])
            if DEBUG_LINK:
                if param_name == 'link' and element_count > 0:
                    print_link_debug(actions, tag_header, action_id, act, line, p)
            if VALIDATE:
                template = action_templates.get(act['type'])
                if template:
                    template_field = template['params'].get(param_name)
                    if template_field:
                        required = template_field['requirement'] == 'required'
                        field_count = template_field['metadata'].get('count')
                        field_max = template_field['metadata'].get('max')
                        field_min = template_field['metadata'].get('min')
                        if field_count and element_count != int(field_count):
                            if p['type'].name == 'FLAG' and p['elements'] == [True]:
                                pass
                            elif not required and p['elements'] == []:
                                pass
                            else:
                                linked_valid = False
                                link_checked = False
                                for linked in collect_params(actions, act['parameters'], []):
                                    if linked['name'] == param_name and linked['elements'] != p['elements']:
                                        link_checked = True
                                        if len(linked['elements']) == int(field_count):
                                            linked_valid = True
                                if not linked_valid:
                                    checked_field = 'count'
                                    if link_checked:
                                        checked_field = f'(linked) {checked_field}'
                                    print_validation_error(checked_field, field_count, tag_header, action_id, prefix, line, p, plugin_names)
                        else:
                            if field_max and element_count > int(field_max):
                                print_validation_error('max', field_max, tag_header, action_id, prefix, line, p, plugin_names)
                            if field_min and element_count < int(field_min):
                                print_validation_error('min', field_min, tag_header, action_id, prefix, line, p, plugin_names)

        if len(action_vars):
            print(f'{tag_prefix}\x1b[3m[{' '.join(action_vars)}]\x1b[0m')

        print()

def collect_params(actions, elem_params, seen_actions = []):
    for param in elem_params:
        if param['name'] == 'link':
            for linked_element in param['elements']:
                if linked_element not in seen_actions and linked_element in actions:
                    seen_actions.append(linked_element)
                    next_elem_params = actions[linked_element]['parameters']
                    if len(next_elem_params):
                        yield from collect_params(actions, next_elem_params, seen_actions)
        else:
            yield param

def print_link_debug(actions, tag_header, action_id, act, line, p):
    print(f'{tag_header.tag_id} [{action_id}] DEBUG_LINK {tag_header.tag_type}={tag_header.tag_id} {tag_header.name}')
    print(f'{tag_header.tag_id} [{action_id}] DEBUG_LINK {line}')
    action_type = act['type'].upper() if act['type'] else 'NULL'
    for element in p['elements']:
        if element in actions:
            elem_params = actions[element]['parameters']
            if actions[element]['type']:
                suffix = f'type={actions[element]['type'].upper()} - {actions[element]['name']}'
            elif len(elem_params):
                linked_params = list(collect_params(actions, elem_params, []))
                linked_params_u = set(p['name'] for p in linked_params)
                if len(linked_params):
                    recurse = ''
                    if len(linked_params) > 1:
                        recurse = f'({len(linked_params)})'
                    suffix = f'param={','.join(linked_params_u)}{recurse} - {actions[element]['name']}'
                else:
                    suffix = f'empty link - {actions[element]['name']}'
            else:
                suffix = f'empty      - {actions[element]['name']}'
        print(f'{tag_header.tag_id} [{action_id}] DEBUG_LINK link: {action_type}->{suffix} ({element})')
        print(f'{tag_header.tag_id} [{action_id}] DEBUG_LINK ---')

def print_validation_error(type, value, tag_header, action_id, prefix, line, p, plugin_names):
    print(f'VALIDATION_ERROR mesh={tag_header.tag_id} {tag_header.name}')
    print(f'VALIDATION_ERROR {line}')
    print(f'VALIDATION_ERROR {p['name']} {p['type'].name}={p['elements']}')
    print(f'VALIDATION_ERROR mesh={tag_header.tag_id} [{action_id}] {prefix}{p['name']}(count={len(p['elements'])}) rule: {type}={value} | plugins: {plugin_names}')
    print(f'VALIDATION_ERROR ---')

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
