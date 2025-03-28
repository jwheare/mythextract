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

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and run a map action browser
    """
    try:
        (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

        if level:
            if level.startswith('file='):
                file = level[5:]
                mesh_tag_data = myth_headers.load_file(file)
                parse_mesh_actions(tags, data_map, mesh_tag_data)
            else:
                for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
                    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
                    parse_mesh_actions(tags, data_map, mesh_tag_data)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
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
                p_parts = param.strip().split('/', 2)
                p_parts2 = p_parts[0].strip().split(' ')

                param_field = p_parts2[2].strip()
                params[param_field] = {
                    'name': p_parts[1].strip(),
                    'type': p_parts2[1].strip(),
                    'requirement': p_parts2[0].strip(),
                    'desc': p_parts[2].strip(),
                }
        action_help[action_type] = {
            'name': template_lines[0].strip(),
            'expiration_mode': template_lines[1].strip(),
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

def parse_mesh_actions(tags, data_map, mesh_tag_data):
    mesh_header = mesh_tag.parse_header(mesh_tag_data)

    action_help = build_action_help(tags, data_map)

    (palette, orphans) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)

    (actions, _) = mesh_tag.parse_map_actions(mesh_header, mesh_tag_data)

    actions_tui(actions, palette, tags, action_help)

def build_backrefs(actions):
    backrefs = {}
    for (action_id, action) in actions.items():
        for param_i, param in enumerate(action['parameters']):
            for elem_i, element in enumerate(param['elements']):
                if param['type'] == mesh_tag.ParamType.ACTION_IDENTIFIER:
                    if element in actions:
                        if element not in backrefs:
                            backrefs[element] = []
                        backrefs[element].append((action_id, param_i, elem_i))
    return backrefs

def build_action_vars(action):
    action_vars = []
    if len(action['parameters']):
        if action['flags']:
            action_vars.append(','.join([f.name.lower() for f in action['flags']]))
        if action['expiration_mode'] != mesh_tag.ActionExpiration.TRIGGER:
            action_vars.append(f'expiry={action['expiration_mode'].name.lower()}')
        if action['trigger_time_lower_bound']:
            action_vars.append(f'delay={round(action['trigger_time_lower_bound'], 3)}s')
        if action['trigger_time_delta']:
            action_vars.append(f'dur={round(action['trigger_time_delta'], 3)}s')
    return action_vars

def build_backref_node(actions, action_id, backrefs, indent_space, action_help):
    backref_children = []
    for (ref_action, pi, vi) in backrefs[action_id]:
        param = actions[ref_action]['parameters'][pi]
        if actions[ref_action]['type']:
            suffix = f' {actions[ref_action]['type'].upper()}-{param['name']}'
        else:
            suffix = f' NONE-{param['name']}'
        suffix += f'[{vi}] {actions[ref_action]['name']}'
        if len(build_action_vars(actions[ref_action])):
            pi = pi + 1
        (help_text, more_help, param_bold) = action_param_help(actions[ref_action], param, action_help)
        backref_children.append(tree_curses.TreeNode(
            f'       {indent_space}{ref_action}',
            action_id,
            options={
                'help': help_text,
                'more_help': more_help,
                'id_link': ref_action,
                'id_link_children': [pi, vi],
                'suffix': suffix,
                'color': 'alt_color2',
            }
        ))
    return tree_curses.TreeNode(
        f'    {indent_space}<- ref ACTION_IDENTIFIER({len(backref_children)})',
        action_id,
        children=backref_children,
        options={
            'help': 'References',
            'more_help': '[action_identifier] Actions which reference this action',
            'color': 'alt_color5',
        }
    )

def action_param_help(action, param, action_help):
    help_text = None
    param_bold = False
    more_help = ''
    help_obj = lookup_action_help(action_help, action['type'], param['name'])
    if help_obj:
        help_text = help_obj['name']
        if action['type']:
            more_help = f'[{action['type'].upper()}-{param['name']}] '
        else:
            more_help = f'[NONE-{param['name']}] '
        if 'requirement' in help_obj:
            more_help += f'({help_obj['requirement']}) '
        if 'type' in help_obj:
            more_help += f'[{help_obj['type']}] '
        if 'desc' in help_obj:
            more_help += f'{help_obj['desc']} '
        param_bold = help_obj.get('requirement') == 'required'
    elif not action['type'] and param['type'] == mesh_tag.ParamType.MONSTER_IDENTIFIER:
        more_help = f'[NONE-{param['name']}] [{param['type'].name.lower()}] '
        if param['name'] == 'subj':
            help_text = 'Subject'
            more_help += 'Monster reference as subject'
        elif param['name'] == 'obje':
            help_text = 'Object'
            more_help += 'Monster reference as object'
        elif param['name'] == 'enem':
            help_text = 'Enemy'
            more_help += 'Monster reference as enemy'
    return (help_text, more_help, param_bold)

def tag_to_suffix(tags, tag_type, tag_id):
    (location, tag_header) = loadtags.lookup_tag_header(tags, tag_type, tag_id)
    if tag_header:
        return f' - {tag_header.name}'

def build_action_param_element_node(action, param, element, tags, actions, palette):
    # Action param elements
    suffix = None
    action_ref = None
    color = 'alt_color4'
    if param['type'] == mesh_tag.ParamType.FIELD_NAME:
        if (
            (action['type'] == 'geom' and param['name'] in ['type', 'hold', 'noho', 'holi', 'nhoi']) or
            (action['type'] == 'tuni' and param['name'] in ['hold', 'holi'])
        ):
            suffix = tag_to_suffix(tags, 'proj', element)
        elif (
            (action['type'] == 'geom' and param['name'] in ['mons'])
        ):
            color = 'alt_color3'
            suffix = tag_to_suffix(tags, 'unit', element)
    elif param['type'] == mesh_tag.ParamType.SOUND:
        suffix = tag_to_suffix(tags, 'soun', element)
    if param['type'] == mesh_tag.ParamType.ACTION_IDENTIFIER:
        color = 'alt_color2'
        if element in actions:
            action_ref = element
            if actions[element]['type']:
                suffix = f' {actions[element]['type'].upper()}.{actions[element]['name']}'
            elif len(actions[element]['parameters']):
                suffix = f' ({actions[element]['parameters'][0]['name']}) {actions[element]['name']}'
            else:
                suffix = f' {actions[element]['name']}'
        else:
            suffix = ' [missing]'
    else:
        if param['type'] == mesh_tag.ParamType.MONSTER_IDENTIFIER:
            color = 'alt_color3'
        palette_type = mesh_tag.param_id_marker(param['type'], param['name'])
        if palette_type:
            for obje in palette[palette_type]:
                if element in obje['markers']:
                    tag_id = obje['tag']
                    tag_suffix = tag_to_suffix(tags, mesh_tag.Marker2Tag.get(palette_type), tag_id) or ''
                    suffix = f' [{tag_id}]{tag_suffix}'

    return (action_ref, suffix, color)

def build_action_param_node(
    param, act, action_help, palette, tags, indent_space, actions, action_id
):
    (help_text, more_help, param_bold) = action_param_help(act, param, action_help)

    param_children = []
    if len(param['elements']) == 1:
        element = param['elements'][0]
        (action_ref, suffix, color) = build_action_param_element_node(act, param, element, tags, actions, palette)
        param_type = element
    else:
        action_ref = None
        suffix = None
        color = 'alt_color'
        param_type = f'{param['type'].name}({len(param['elements'])})'
        for element in param['elements']:
            (param_action_ref, param_suffix, param_color) = build_action_param_element_node(act, param, element, tags, actions, palette)
            param_element_node = tree_curses.TreeNode(
                f'       {indent_space}{element}',
                action_id,
                options={
                    'id_link': param_action_ref,
                    'suffix': param_suffix,
                    'more_help': more_help,
                    'color': param_color,
                }
            )
            param_children.append(param_element_node)
    # Action params
    return tree_curses.TreeNode(
        f'    {indent_space}- {param['name']} {param_type}',
        action_id,
        children=param_children,
        options={
            'id_link': action_ref,
            'suffix': suffix,
            'help': help_text,
            'more_help': more_help,
            'color': color,
            'bold': param_bold,
        }
    )

def action_type_help(action_help, act):
    help_text = None
    more_help = ''
    help_obj = lookup_action_help(action_help, act['type'])
    if help_obj:
        help_text = help_obj['name']
        more_help = f'[{act['type'].upper()}] {help_obj['name']} '
        if 'expiration_mode' in help_obj:
            more_help += f'(default expiry: {help_obj['expiration_mode']}) '
    return (help_text, more_help)

def actions_tui(actions, palette, tags, action_help):
    nodes = []
    backrefs = build_backrefs(actions)
    for (action_id, act) in actions.items():
        indent_space = act['indent'] * '  '
        bold = mesh_tag.ActionFlag.INITIALLY_ACTIVE in act['flags']
        children = []
        # Action flags
        action_vars = build_action_vars(act)
        if len(action_vars):
            children.append(tree_curses.TreeNode(f'    {indent_space}[{' '.join(action_vars)}]', action_id, options={
                'help': 'Flags',
                'bold': bold,
                'color': 'alt_color4',
            }))

        for param in act['parameters']:
            children.append(build_action_param_node(
                param, act, action_help, palette, tags, indent_space, actions, action_id
            ))

        if action_id in backrefs:
            children.append(build_backref_node(actions, action_id, backrefs, indent_space, action_help))

        # Action
        (help_text, more_help) = action_type_help(action_help, act)
        if len(act['parameters']):
            id_prefix = f'[{action_id}] '
        else:
            id_prefix = '        '
        prefix = ''
        if act['type']:
            prefix = f'{act['type'].upper()}.'
        elif len(act['parameters']):
            prefix = f'({act['parameters'][0]['name']}) '
        name = f'{id_prefix}{indent_space}{prefix}{act['name']}'

        nodes.append(tree_curses.TreeNode(name, action_id, children=children, options={
            'bold': bold,
            'help': help_text,
            'more_help': more_help,
        }))
    tree = tree_curses.TreeNode("Root", None, children=nodes)
    tree_curses.enter(tree)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mesh2actions.py <game_directory> [<level> [<plugin_names> ...]]")
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
