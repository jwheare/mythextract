#!/usr/bin/env python3
import os
import pathlib
import struct
import sys

import codec
import myth_headers
import mesh_tag
import mesh2info
import loadtags
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

TFLTagMap = {
    '01': (('30cb', '301 crows bridge'), ('30cc', '301 crows bridge'), ('30cb', '301 captions')),
    '02': (('30tr', '302 traitor'), ('30tr', '302 traitor'), ('30cd', '302 captions')),
    '03': (('30di', '303 diversion'), ('30di', '303 diversion'), ('30ca', '303 captions')),
    '04': (('30co', '304 covenant'), ('30co', '304 covenant'), ('30ce', '304 captions')),
    '05': (('30fl', '305 flight'), ('30fl', '305 flight'), ('30cf', '305 captions')),
    '06': (('30ft', '306 force ten'), ('30ft', '306 force ten'), ('30cg', '306 captions')),
    '07': (('30ba', '307 bagrada'), ('30ba', '307 bagrada'), ('30ci', '307 captions')),
    '08': (('30am', '308 ambush'), ('30am', '308 ambush'), ('30cj', '308 captions')),
    '09': (('30fc', '309 five champions'), ('30ch', '309 champions'), ('30ck', '309 captions')),
    '10': (('31ba', '310 barrier'), ('31ba', '310 barrier'), ('31cb', '310 captions')),
    '11': (('31si', '311 silvermines'), ('31si', '311 silvermines'), ('31cc', '311 captions')),
    '12': (('31sh', '312 shadow'), ('31sh', '312 shadow'), ('31ca', '312 captions')),
    '13': (('31sg', '313 seven gates'), ('31sg', '313 seven gates'), ('31cd', '313 captions')),
    '14': (('14fh', '314 forest heart'), ('14fh', '314 forest heart'), ('31ce', '314 captions')),
    '15': (('15ho', '315 heart of the stone'), ('15c1', '315 cave 1'), (None, None)),
    '16': (('16ts', '316 smiths of muirthemne'), ('16c2', '316 cave 2'), (None, None)),
    '17': (('17ts', '317 sons of myrgard'), ('17so', '317 myrgard 1'), ('31cf', '317 captions')),
    '18': (('18al', '318 a long awaited party'), ('18re', '318 myrgard 2'), ('31cg', '318 captions')),
    '19': (('19tr', '319 the road north'), ('19m1', '319 marsh 1'), ('31ch', '319 captions')),
    '20': (('32m2', '320 marsh 2'), ('32ma', '320 marsh2'), ('32ca', '320 captions')),
    '21': (('21ah', '321 hundred shallow graves'), ('21m3', '321 marsh 3'), ('32cb', '321 captions')),
    '22': (('22ro', '322 river of blood'), ('22rh', '322 trow 1'), ('32cc', '322 captions')),
    '23': (('23po', '323 pools of iron'), ('23t2', '323 trow 2'), ('32cd', '323 captions')),
    '24': (('24tl', '324 the last battle'), ('24t3', '325 trow 3'), ('32ce', '324 captions')),
    '25': (('25tg', '325 the great devoid'), ('25tg', '325 great devoid'), ('32cf', '325 captions')),
}

def main(game_directory, level):
    """
    Load Myth TFL game tags and convert text and stli tags for a given mesh to Myth II format
    Also maps to the tag ids used by the ports of TFL to Myth II
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory)

    if game_version != 1:
        print('Invalid TFL directory')
        sys.exit(1)

    try:
        if level == 'all':
            for level in range(1, 26):
                (mesh_id, header_name, entry_name) = mesh2info.parse_level(f'{level:02}', tags)
                print(f'level={level} mesh={mesh_id} file=[{header_name}] [{entry_name}]')
                convert_level(game_version, tags, data_map, mesh_id)
        else:
            (mesh_id, header_name, entry_name) = mesh2info.parse_level(level, tags)
            print(f'level={level} mesh={mesh_id} file=[{header_name}] [{entry_name}]')
            convert_level(game_version, tags, data_map, mesh_id)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def convert_level(game_version, tags, data_map, mesh_id):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
    tag_header = myth_headers.parse_header(mesh_tag_data)
    level = tag_header.name.split(' ')[0]

    mesh_header = mesh_tag.parse_header(mesh_tag_data)

    if not mesh_tag.has_single_player_story(game_version, mesh_tag_data):
        print('skip, no single player story', game_version, mesh_id, level)
        return

    # Extract narration text
    storyline_data = loadtags.get_tag_data(
        tags, data_map, 'text', codec.decode_string(mesh_header.pregame_storyline_tag)
    )

    # Extract description stli
    desc_data = loadtags.get_tag_data(
        tags, data_map, 'stli', codec.decode_string(mesh_header.map_description_string_list_tag)
    )

    # Extract caption stli
    caption_data = loadtags.get_tag_data(
        tags, data_map, 'stli', codec.decode_string(mesh_header.picture_caption_string_list_tag)
    )

    (text_tag, desc_tag, caption_tag) = TFLTagMap[level]

    output_dir = '../output/fixed_tfl_mesh_text/local'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    if prompt(output_path):
        for tag_data, tag_values in [
            (storyline_data, text_tag),
            (desc_data, desc_tag),
            (caption_data, caption_tag)
        ]:
            if tag_data:
                tag_header = myth_headers.parse_header(tag_data)
                tag_content = convert_formatting(tag_data[myth_headers.TAG_HEADER_SIZE:])

                # Replace with TFL port tag ids
                new_tag_header = tag_header._replace(
                    tag_id=codec.encode_string(tag_values[0]),
                    name=codec.encode_string(tag_values[1])
                )

                sb_tag_data = myth_headers.tfl2sb(new_tag_header, tag_content)

                file_path = (output_path / f'{utils.local_folder(new_tag_header)}/{new_tag_header.name}')
                pathlib.Path(file_path.parent).mkdir(parents=True, exist_ok=True)

                with open(file_path, 'wb') as tag_file:
                    tag_file.write(sb_tag_data)

                print(f"Tag converted. Output saved to {file_path}")

def convert_formatting(text_data):
    return text_data.replace(b'\\', b'|')

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> <level>")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = sys.argv[2]

    try:
        main(game_directory, level)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
