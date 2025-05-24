#!/usr/bin/env python3
import os
import sys
import struct
import pathlib

import codec
import myth_headers
import mono2tag
import mesh_tag
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(mono_path, output_file):
    """
    Parse a Myth TFL or Myth II monolith file and export provided tag.
    If no tag provided, list all tags
    """
    mono_path = pathlib.Path(mono_path)
    data = utils.load_file(mono_path)

    try:
        mono_header = myth_headers.parse_mono_header(mono_path.name, data)
        mono2tag.debug_mono_header(mono_header, data)
        entrypoints = mono2tag.get_entrypoints(data, mono_header)
        if len(entrypoints):
            mono2tag.print_entrypoint_map(entrypoints, ': Current')
            new_mono_data = fix_entrypoint_map(entrypoints, data, mono_header)
            if not new_mono_data:
                print("Entrypoints up to date")
            else:
                new_mono_header = myth_headers.parse_mono_header(mono_path.name, new_mono_data)
                mono2tag.debug_mono_header(new_mono_header, new_mono_data)
                new_entrypoints = mono2tag.get_entrypoints(new_mono_data, new_mono_header)
                mono2tag.print_entrypoint_map(new_entrypoints, ': Fixed')

                if not output_file:
                    output_file = f'../output/fixed_entrypoints/{mono_path.name}'
                    new_mono_path = pathlib.Path(sys.path[0], output_file).resolve()
                else:
                    new_mono_path = pathlib.Path(output_file)

                if prompt(new_mono_path):
                    pathlib.Path(new_mono_path.parent).mkdir(parents=True, exist_ok=True)
                    with open(new_mono_path, 'wb') as new_mono_file:
                        new_mono_file.write(new_mono_data)
                        print(f"Entrypoints fixed. Output saved to {new_mono_path}")

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def fix_entrypoint_map(entrypoints, data, mono_header):
    print(
        """
Existing printable level names and names from mesh description STLIs
Mismatching entries that need fixing are marked with an x
------+------------------------------------------------------------------+------------------------------------------------------------------+
 fix? | current printable level name                                     | printable level name from mesh description
------+------------------------------------------------------------------+------------------------------------------------------------------+"""
    )
    tags = myth_headers.get_mono_tags(data, mono_header)
    fixed = False
    for entry_id, (entry_name, entry_long_name, archive_list) in entrypoints.items():
        mesh_data = mono2tag.seek_tag(tags, 'mesh', entry_id, data, mono_header)
        if mesh_data:
            mesh_header = mesh_tag.parse_header(mesh_data)
            desc_tag = codec.decode_string(mesh_header.map_description_string_list_tag)
            desc_data = mono2tag.seek_tag(tags, 'stli', desc_tag, data, mono_header)
            if desc_data:
                (_, desc_text) = myth_headers.parse_text_tag(desc_data)
                level_name = codec.decode_string(desc_text.split(b'\r')[0])
                correct = ''
                if level_name != entry_long_name:
                    correct = 'x'
                    entrypoints[entry_id] = (entry_name, level_name, archive_list)
                    fixed = True
                print(f' {correct:>4} | {mono2tag.format_entry_name(entry_long_name, entry_name)} | {mono2tag.format_entry_name(level_name, entry_name)}')
    print('---')
    if fixed:
        return mono2tag.encode_entrypoints(data, mono_header.header, entrypoints)
    else:
        return False

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fixentrypoints.py <mono_file> [<output_file>]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = None

    if len(sys.argv) == 3:
        output_file = sys.argv[2]
    
    try:
        main(input_file, output_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
