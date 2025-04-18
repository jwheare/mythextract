#!/usr/bin/env python3
import os
import pathlib
import struct
import sys
import time

import myth_headers
import mesh_tag
import mono2tag
import mesh2info
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')
TIME = (os.environ.get('TIME') == '1')

def load_file(path):
    t = time.perf_counter()
    data = myth_headers.load_file(path)
    TIME and print(path, f'{(time.perf_counter() - t):.3f}')

    return data

def main(game_directory, level, plugin_name, plugin_output):
    """
    Load Myth game tags and plugins and output basic text and html for the intro to a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, [plugin_name])

    try:
        if level:
            if game_version == 2 and level == 'all':
                for mesh_id, (entry_name, entry_long_name, archive_list) in entrypoint_map.items():
                    if not plugin_name or plugin_name in archive_list:
                        if DEBUG:
                            print(f'mesh={mesh_id} file=[{archive_list}] [{entry_name}] [{entry_long_name}]')
                        plugin = plugin_name if plugin_name in archive_list else None
                        extract_level(game_version, tags, data_map, cutscenes, mesh_id, plugin, plugin_output)
                if not plugin_name:
                    extract_sb_epilogue(tags, data_map, cutscenes)
            elif game_version == 1 and level == 'all':
                for level in range(1, 26):
                    (mesh_id, header_name, entry_name) = mesh2info.parse_level(f'{level:02}', tags)
                    if DEBUG:
                        print(f'level={level} mesh={mesh_id} file=[{header_name}] [{entry_name}]')
                    plugin = None
                    extract_level(game_version, tags, data_map, cutscenes, mesh_id, plugin, plugin_output)
            elif game_version == 2 and not plugin_name and level == 'epilogue':
                extract_sb_epilogue(tags, data_map, cutscenes)
            else:
                (mesh_id, header_name, entry_name) = mesh2info.parse_level(level, tags)
                if DEBUG:
                    print(f'level={level} mesh={mesh_id} file=[{header_name}] [{entry_name}]')
                plugin = plugin_name if plugin_name == header_name else None
                extract_level(game_version, tags, data_map, cutscenes, mesh_id, plugin, plugin_output)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def extract_sb_epilogue(tags, data_map, cutscenes):
    prefix = 'myth2'
    game_version = 2
    level = 'epilogue'
    mesh_id = level
    level_name = 'Epilogue'
    caption_data = None
    desc_data = None
    plugin = None

    storyline_data = loadtags.get_tag_data(tags, data_map, 'text', 'epil')

    output_text(
        game_version, plugin, mesh_id,
        storyline_data, caption_data,
        prefix, level, desc_data, level_name
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

    if not mesh_tag.has_single_player_story(game_version, mesh_tag_data):
        if DEBUG:
            print('skip, no single player story', game_version, mesh_id, level, plugin)
        return

    # Extract narration text
    text_tag = myth_headers.decode_string(mesh_header.pregame_storyline_tag)
    storyline_data = loadtags.get_tag_data(tags, data_map, 'text', text_tag)

    # Extract level name
    desc_tag = myth_headers.decode_string(mesh_header.map_description_string_list_tag)
    desc_data = loadtags.get_tag_data(tags, data_map, 'stli', desc_tag)

    # Extract pregame captions
    caption_tag = myth_headers.decode_string(mesh_header.picture_caption_string_list_tag)
    caption_data = loadtags.get_tag_data(tags, data_map, 'stli', caption_tag)

    output_text(
        game_version, plugin, mesh_id,
        storyline_data, caption_data,
        prefix, level, desc_data
    )

def output_text(
    game_version, plugin, mesh_id,
    storyline_data, caption_data,
    prefix, level, desc_data, level_name=None
):
    # Extract intro text
    intro_text = ''
    intro_tag_values = (None, None)
    if storyline_data:
        (intro_header, intro_text) = myth_headers.parse_text_tag(storyline_data)
        intro_tag_values = (intro_header.tag_id, intro_header.name)

    desc_tag_values = (None, None)
    if desc_data:
        (desc_header, desc_text) = myth_headers.parse_text_tag(desc_data)
        desc_tag_values = (desc_header.tag_id, desc_header.name)
        level_name = myth_headers.decode_string(desc_text.split(b'\r')[0])

    # Extract caption
    caption = ''
    caption_tag_values = (None, None)
    if caption_data:
        (caption_header, caption_text) = myth_headers.parse_text_tag(caption_data)
        caption_tag_values = (caption_header.tag_id, caption_header.name)
        caption = myth_headers.decode_string(caption_text.split(b'\r')[0])

    if DEBUG:
        print(level, intro_tag_values, desc_tag_values, caption_tag_values, level_name)

    output_dir = f'../output/text/{prefix}'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    if prompt(output_path):
        output_path.mkdir(parents=True, exist_ok=True)

        ouput_text = f"""Level: {level_name.replace("'", "’")}
Caption: {caption.replace("'", "’")}

{decode_text(intro_text)}"""
        
        file_name = level
        file_path = (output_path / f'{file_name}.txt')
        with open(file_path, 'w') as text_file:
            text_file.write(ouput_text)

        print(f"Text extracted. Output saved to {file_path}")

def decode_text(text):
    return text.decode('mac-roman').replace('\r', '\n')

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mesh2text.py <game_directory> [<level> [<plugin_name> [<plugin_output>]]]")
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
