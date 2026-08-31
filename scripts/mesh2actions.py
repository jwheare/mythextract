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
                parse_mesh_actions(file, mesh_tag_data, action_templates)
            else:
                for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):

                    (mesh_tag_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(
                        tags, data_map, 'mesh', mesh_id
                    )
                    parse_mesh_actions(mesh_tag_location, mesh_tag_data, action_templates)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_mesh_actions(mesh_tag_location, mesh_tag_data, action_templates):
    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    tag_header = myth_headers.parse_header(mesh_tag_data)

    (actions, action_remainder) = mesh_tag.parse_map_actions(mesh_header, mesh_tag_data)
    print_actions(actions, tag_header, action_templates)

    if action_remainder:
        print(f'ACTION REMAINDER count={len(action_remainder)} mesh=[{tag_header.tag_id}] {tag_header.name} ({mesh_tag_location})')
        print(action_remainder.hex())

def print_actions(actions, tag_header, action_templates):
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
            if VALIDATE:
                template = action_templates.get(act['type'])
                if template:
                    template_field = template['params'].get(p['name'])
                    if template_field:
                        field_count = template_field['metadata'].get('count')
                        field_max = template_field['metadata'].get('max')
                        field_min = template_field['metadata'].get('min')
                        if field_count and len(p['elements']) != int(field_count):
                            if p['type'].name == 'FLAG' and p['elements'] == [True]:
                                pass
                            else:
                                print_validation_error('count', field_count, tag_header, line, p)
                        else:
                            if field_max and len(p['elements']) > int(field_max):
                                print_validation_error('max', field_max, tag_header, line, p)
                            if field_min and len(p['elements']) < int(field_min):
                                print_validation_error('min', field_min, tag_header, line, p)

        if len(action_vars):
            print(f'{tag_prefix}\x1b[3m[{' '.join(action_vars)}]\x1b[0m')

        print()

def print_validation_error(type, value, tag_header, line, p):
    print(f'VALIDATION_ERROR {tag_header.tag_type}={tag_header.tag_id} {tag_header.name}')
    print(f'VALIDATION_ERROR {line}')
    print(f'VALIDATION_ERROR {p['name']} {p['type'].name}={p['elements']}')
    print(f'VALIDATION_ERROR {type}={value}')
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
