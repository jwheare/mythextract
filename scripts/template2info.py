#!/usr/bin/env python3
import sys
import os
import struct

import utils
import myth_headers
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, template, template_file=None):
    """
    Load Myth game tags and print template info
    """
    try:
        if template == 'file' and template_file:
            mono_data = utils.load_file(template_file)
            mono_header = myth_headers.parse_mono_header(template_file, mono_data)
            mono_tags = myth_headers.get_mono_tags(mono_data, mono_header)
            print(mono_header.name)
            print()
            for tag_header in mono_tags:
                (tag_header_norm, action_template_data) = loadtags.collect_tag_data(tag_header, mono_data)
                print_template_info(action_template_data)
        elif template == 'tag' and template_file:
            action_template_data = utils.load_file(template_file)
            print_template_info(action_template_data)
        else:
            (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory)
            if not template or template == 'list':
                for action_type, locations in tags['temp'].items():
                    print(action_type)
                    # for loc, tag_header in locations:
                    #     print(f' - {tag_header.name} ({loc})')
                template_choice = input('Choose an action template type: ')
                main(game_directory, template_choice)
            elif template == 'all':
                for action_type in tags['temp'].keys():
                    action_template_data = loadtags.get_tag_data(tags, data_map, 'temp', action_type)
                    print_template_info(action_template_data)
            else:
                action_template_data = loadtags.get_tag_data(tags, data_map, 'temp', template)
                print_template_info(action_template_data)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def print_template_info(action_template_data):
    data = parse_template(action_template_data)
    print(f"{data['name']} [{data['header'].tag_id}] {data['header'].name}")
    print(data['expiration_mode'])
    for param_field, param in data['params'].items():
        print(f"- [{param_field}] {param['name']} \x1b[90m{param['type']}\x1b[0m ({param['requirement']})")
        if param['desc']:
            print(f"    {param['desc']}")
        for k, v in param['metadata'].items():
            print(f"    {k} = {v}")
    print()

def parse_template(action_template_data):
    (action_template_header, action_template) = myth_headers.parse_text_tag(action_template_data)
    template_lines = myth_headers.parse_stli(action_template)
    params = {}
    # '   optional monster_identifier subj / Monsters (subj) / Monsters to check for in the geometry.'
    for param in template_lines[2:]:
        if param.strip():
            # 'optional monster_identifier subj
            # 'Monsters (subj)'
            # 'Monsters to check for in the geometry.'
            p_parts = param.strip().split('/', 2)

            # 'optional'
            # 'monster_identifier'
            # 'subj'
            p_parts2 = p_parts[0].strip().split(' ')

            metadata = {}
            if len(p_parts2) > 3:
                metadata = {k: v for [k, v] in [m.split('=') for m in p_parts2[3:]]}

            param_field = p_parts2[2].strip()
            params[param_field] = {
                'name': p_parts[1].strip(),
                'type': p_parts2[1].strip(),
                'requirement': p_parts2[0].strip(),
                'desc': p_parts[2].strip(),
                'metadata': metadata,
            }
    return {
        'name': template_lines[0].strip(),
        'expiration_mode': template_lines[1].strip(),
        'params': params,
        'header': action_template_header,
    }
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> [<template> [<file>]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    template = None
    if len(sys.argv) > 2:
        template = sys.argv[2]

    template_file = None
    if len(sys.argv) > 3:
        template_file = sys.argv[3]

    try:
        main(game_directory, template, template_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
