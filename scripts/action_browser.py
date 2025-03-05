#!/usr/bin/env python3
import sys
import os
import struct

import myth_headers
import mesh_tag
import mesh2info
import mono2tag
import loadtags
import tree_curses

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, level, plugin_name):
    """
    Load Myth game tags and plugins and run a map action browser
    """
    (files, cutscenes) = loadtags.build_file_list(game_directory, plugin_name)
    (game_version, tags, entrypoint_map, data_map) = loadtags.build_tag_map(files)

    try:
        if level:
            for mesh_id in mesh2info.mesh_entries(level, entrypoint_map, tags):
                parse_mesh_actions(game_version, tags, data_map, mesh_id)
        else:
            for header_name, entrypoints in entrypoint_map.items():
                mono2tag.print_entrypoints(entrypoints, header_name)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def build_action_help(tags, data_map):
    action_help = {}
    for action_type in tags['temp'].keys():
        action_template_data = loadtags.get_tag_data(tags, data_map, 'temp', action_type)
        action_template = action_template_data[myth_headers.TAG_HEADER_SIZE:]
        template_lines = [myth_headers.decode_string(tpl_line) for tpl_line in action_template.split(b'\r')]
        params = {}
        for param in template_lines[2:]:
            if param.strip():
                p_parts = param.lstrip('\t').split(' / ')
                p_parts2 = p_parts[0].split(' ')

                param_field = p_parts2[2]
                params[param_field] = {
                    'name': p_parts[1],
                    'type': p_parts2[1],
                    'requirement': p_parts2[0],
                    'desc': p_parts[2],
                }
        action_help[action_type] = {
            'name': template_lines[0],
            'expiration_mode': template_lines[1],
            'params': params
        }
    return action_help

def lookup_action_help(action_help, action_type, param_type=None):
    action = action_help.get(action_type)
    if param_type:
        param = None
        if action:
            param = action['params'].get(param_type)
        if not param:
            param = action_help['defa']['params'].get(param_type)
        return param

    else:
        return action

def parse_mesh_actions(game_version, tags, data_map, mesh_id):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
    mesh_header = mesh_tag.parse_header(mesh_tag_data)

    action_help = build_action_help(tags, data_map)

    (palette, orphans) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)

    (actions, _) = mesh_tag.parse_map_actions(game_version, mesh_header, mesh_tag_data)

    actions_tui(actions, palette, tags, action_help)

def actions_tui(actions, palette, tags, action_help):
    nodes = []
    for (action_id, act) in actions.items():
        indent_space = act['indent'] * '  '
        prefix = ''
        if act['type']:
            prefix = f'{act['type'].upper()}.'
        elif len(act['parameters']):
            prefix = f'({act['parameters'][0]['name']}) '

        action_vars = []
        if len(act['parameters']):
            if act['flags']:
                action_vars.append(','.join([f.name.lower() for f in act['flags']]))
            if act['expiration_mode'] != mesh_tag.ActionExpiration.TRIGGER:
                action_vars.append(f'expiry={act['expiration_mode'].name.lower()}')
            if act['trigger_time_start']:
                action_vars.append(f'delay={round(act['trigger_time_start'], 3)}s')
            if act['trigger_time_duration']:
                action_vars.append(f'dur={round(act['trigger_time_duration'], 3)}s')

        if len(act['parameters']):
            id_prefix = f'[{action_id}] '
        else:
            id_prefix = '        '
        name = f'{id_prefix}{indent_space}{prefix}{act['name']}'
        bold = mesh_tag.ActionFlag.INITIALLY_ACTIVE in act['flags']

        children = []
        for p in act['parameters']:
            param_children = []
            for value in p['values']:
                # Action param values
                suffix = None
                if act['type'] == 'geom' and p['name'] == 'type' and p['type'] == mesh_tag.ParamType.FIELD_NAME:
                    suffix = f' [{value}]'
                    (location, tag_header) = loadtags.lookup_tag_header(tags, 'proj', value)
                    if tag_header:
                        suffix = f'{suffix} {tag_header.name}'
                if p['type'] == mesh_tag.ParamType.ACTION_IDENTIFIER:
                    if value in actions:
                        suffix = f' {actions[value]['name']}'
                    else:
                        suffix = ' [missing]'
                elif p['type'] == mesh_tag.ParamType.SOUND:
                    (location, tag_header) = loadtags.lookup_tag_header(tags, 'soun', value)
                    if tag_header:
                        suffix = f' - {tag_header.name}'
                else:
                    palette_type = mesh_tag.param_id_marker(p['type'], p['name'])
                    if palette_type:
                        for obje in palette[palette_type]:
                            if value in obje['markers']:
                                tag_id = obje['tag']
                                suffix = f' [{tag_id}]'
                                (location, tag_header) = loadtags.lookup_tag_header(tags, mesh_tag.Marker2Tag.get(palette_type), tag_id)
                                if tag_header:
                                    suffix = f'{suffix} {tag_header.name}'
                param_children.append(tree_curses.TreeNode(
                    f'{indent_space}       {value}',
                    action_id,
                    options={
                        'id_link': value if mesh_tag.ParamType.ACTION_IDENTIFIER else None,
                        'suffix': suffix,
                        'more_help': p['type'].name,
                        'alt_color2': True,
                    }
                ))
            # Action params
            help_text = None
            more_help = ''
            help_obj = lookup_action_help(action_help, act['type'], p['name'])
            if help_obj:
                help_text = help_obj['name']
                if act['type']:
                    more_help = f'[{act['type'].upper()}-{p['name']}] '
                else:
                    more_help = f'[NONE-{p['name']}] '
                if 'requirement' in help_obj:
                    more_help += f'({help_obj['requirement']}) '
                if 'type' in help_obj:
                    more_help += f'[{help_obj['type']}] '
                if 'desc' in help_obj:
                    more_help += f'{help_obj['desc']} '
            children.append(tree_curses.TreeNode(
                f'    {indent_space}- {p['name']} {p['type'].name}',
                action_id,
                children=param_children,
                options={
                    'help': help_text,
                    'more_help': more_help,
                    'alt_color': True,
                }
            ))

        suffix = None
        if len(action_vars):
            suffix = f' [{' '.join(action_vars)}]'

        # Action
        help_text = None
        more_help = ''
        help_obj = lookup_action_help(action_help, act['type'])
        if help_obj:
            help_text = help_obj['name']
            more_help = f'[{act['type'].upper()}] {help_obj['name']} '
            if 'expiration_mode' in help_obj:
                more_help += f'({help_obj['expiration_mode']}) '
        nodes.append(tree_curses.TreeNode(name, action_id, children=children, options={
            'bold': bold,
            'suffix': suffix,
            'help': help_text,
            'more_help': more_help,
        }))
    tree = tree_curses.TreeNode("Root", None, children=nodes)
    tree_curses.enter(tree)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mesh2actions.py <game_directory> [<level> [plugin_name]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_name = None
    if len(sys.argv) > 2:
        level = sys.argv[2]
        if len(sys.argv) == 4:
            plugin_name = sys.argv[3]

    try:
        main(game_directory, level, plugin_name)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.exit(1)
