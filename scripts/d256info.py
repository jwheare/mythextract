#!/usr/bin/env python3
import sys
import os
import struct

import myth_collection
import loadtags
import tag2info

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, d256_id, plugin_names):
    """
    Load Myth game tags and plugins and output header info for a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if 'd256' not in tags:
            print('No d256 tags loaded')
            sys.exit(2)
        if d256_id == 'all':
            for tag_id, d256_headers in tags['d256'].items():
                parse_d256_tag(game_version, tags, data_map, tag_id)
        elif d256_id:
            parse_d256_tag(game_version, tags, data_map, d256_id)
        else:
            print_d256_tags(tags)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def print_d256_tags(tags):
    for d256_id, d256_headers in tags['d256'].items():
        print(d256_id)
        for headers in d256_headers:
            print(f' - {headers[1].name} [{headers[0]}]')

def parse_d256_tag(game_version, tags, data_map, d256_id):
    d256_tag_data = loadtags.get_tag_data(tags, data_map, 'd256', d256_id)

    print(d256_id, tags['d256'][d256_id], len(d256_tag_data))

    head = myth_collection.parse_d256_header(d256_tag_data)
    tag2info.print_tag_obj(head)
    
    myth_collection.parse_d256_bitmaps(d256_tag_data, head)
    myth_collection.parse_d256_hues(d256_tag_data, head)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> [<tag_id> [<plugin_names> ...]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    tag_id = None
    plugin_names = []
    if len(sys.argv) > 2:
        tag_id = sys.argv[2]
        if len(sys.argv) > 3:
            plugin_names = sys.argv[3:]

    try:
        main(game_directory, tag_id, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
