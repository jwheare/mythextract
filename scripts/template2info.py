#!/usr/bin/env python3
import sys
import os
import pathlib
import struct
import textwrap

import utils
import myth_headers
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')
RAW_OUTDIR = os.environ.get('RAW_OUTDIR')

def main(game_directory, template, template_file=None):
    """
    Load Myth game tags and print template info
    """
    try:
        if template == 'tag' and template_file:
            action_template_data = utils.load_file(template_file)
            print_template_info(action_template_data)
        elif template_file:
            mono_data = utils.load_file(template_file)
            mono_header = myth_headers.parse_mono_header(template_file, mono_data)
            mono_tags = myth_headers.get_mono_tags(mono_data, mono_header)
            print(f' {mono_header.name:<32} {template_file:>74}')
            for tag_header in mono_tags:
                if tag_header.tag_type == 'temp':
                    if template == 'file' or template == 'all' or template == tag_header.tag_id:
                        (tag_header_norm, action_template_data) = loadtags.collect_tag_data(tag_header, mono_data)
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
    if RAW_OUTDIR:
        (action_template_header, action_template) = myth_headers.parse_text_tag(action_template_data)
        template_lines = myth_headers.parse_stli(action_template)
        tag_file_name = f'{action_template_header.tag_id}.{action_template_header.name}'
        outdir = pathlib.Path(RAW_OUTDIR)
        tag_path = outdir / tag_file_name
        outdir.mkdir(parents=True, exist_ok=True)
        if False and tag_path.is_file():
            print('exists', tag_path)
        else:
            with open(tag_path, 'w') as tag_path_file:
                tag_path_file.write('\n'.join(template_lines))
            print('written', tag_path)
    else:
        data = parse_template(action_template_data)
        template_name = f'{data['name']} ({data['header'].name})'
        print()
        print(' ' + '-'*107 + ' ')
        print()
        exp_mode = f"{data['expiration_mode']}"
        print(f"  {data['header'].tag_id.upper()}   {template_name:<48}   \x1b[90m{exp_mode:>48}\x1b[0m")
        if len(data['params']):
            print()
        for i, (param_field, param) in enumerate(data['params'].items()):
            field = f'  {param_field}'
            if param['requirement'] == 'required':
                field = f'* \x1b[1m{param_field}\x1b[0m'
            param_name = param['name']
            param_type = param['type']
            md = [f'{k} = {v}' for k, v in param['metadata'].items()]
            if len(md):
                param_name = f"{param_name}  ({', '.join(md)})"
            print(f"{field}   {param_name:<64}   {param_type:>32}  ")
            if param['desc']:
                for chunk in textwrap.wrap(param['desc'], 80):
                    print(f"         \x1b[90m{chunk}\x1b[0m")

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
