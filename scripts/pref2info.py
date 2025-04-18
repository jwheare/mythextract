#!/usr/bin/env python3
from collections import namedtuple
import sys
import os
import struct

import myth_headers
import mesh_tag
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

# 0001 <- unknown
# 000D <- coop flag
# 202C <- tfl/anti clump flag (second byte)
# 4086 <- flags
# FFFFFFFF <- time limit (fff = none)
# 6C312020 <- mesh
# 0004 <- difficulty
# 0010 <- player limit
# 621E <- changes every load
# FFFF <- max teams (ffff = off)
# 527D <- changes every load
# 621E <- changes every load
# 00000000 <- unused
# 01D4 <- unknown
# 00000000 unused
# 0889 <- unknown
# 0000 <- unused
# 0001 <- plugin count
# 0001 <- plugin count
# CD857D76 <- plugin related


# 3. show enemy on map 0x00 / 0x40
# 3. play narration    0x00 / 0x08
# 3. allow alliances   0x00 / 0x20
# 3. allow teams       0x44 / 0x46
# 4. allow vets        0x84 / 0xA4
# 4. allow teams       0x84 / 0x86

# 5. player limit
# 7. tfl               0x0C (12)    / 0x2C (44)
# 7. anti-clump        0x0C (12)    / 0x4C (76)
# 9. coop              0x0D (13)    / 0x06 (06)
# 10. difficulty  0=timid 1=simple 2=normal 3=heroic 4=legendary
NET_PREF_SIZE = 1612
NetPrefsFmt = """>
    32s
    64s
    32s

    H H H H

    l
    4s
    H
    H

    H
    h
    4s

    4x
    H
    4x
    H
    2x

    H H
    510s

    68s

    H
    2x
    32s
    32s
    8s
    8s
    4s

    2x
    H H
    510s
    256x
"""
NetPrefs = namedtuple('NetPrefs', [
    'game_name',
    'mesh_name',
    'game_password',

    'unknown',
    'flag1',
    'flag2',
    'flag3',

    'time_limit',
    'mesh_tag',
    'difficulty',
    'player_limit',

    'load_var1',
    'max_teams',
    'load_var2',

    'unknown2',
    'unknown3',

    'plugin_count1',
    'plugin_count2',
    'plugins',

    'unknown4',

    'player_icon',
    'player_name',
    'team_name',
    'color1',
    'color2',
    'net',

    'plugin_count1a',
    'plugin_count2a',
    'pluginsa',
])

def main(pref_file):
    """
    Show info stored in preferences file
    """

    try:
        data = myth_headers.load_file(pref_file)
        parse_pref_file(data)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_pref_color(color_data):
    (r, ra, g, ga, b, ba, flags) = struct.unpack("B B B B B B H", color_data)
    vals = ((r, g, b), (ra, ga, ba), flags)
    return f'\x1b[48;2;{r};{g};{b}m \x1b[0m {vals}'

def parse_pref_plugins(plugin_data, count1, count2):
    next_chunk = plugin_data
    plugins = []
    for i in range(count1):
        flags = next_chunk[:4]
        (name, url, next_chunk) = next_chunk[4:].split(b'\0', 2)
        plugins.append((name, url, flags.hex()))
    return plugins


def parse_net_pref(pref_data):
    net_prefs = NetPrefs._make(struct.unpack(NetPrefsFmt, pref_data[:NET_PREF_SIZE]))
    return net_prefs._replace(
        game_name=myth_headers.decode_string(net_prefs.game_name),
        mesh_name=myth_headers.decode_string(net_prefs.mesh_name),
        game_password=myth_headers.decode_string(net_prefs.game_password),
        mesh_tag=myth_headers.decode_string(net_prefs.mesh_tag),
        player_name=myth_headers.decode_string(net_prefs.player_name),
        team_name=myth_headers.decode_string(net_prefs.team_name),
        net=myth_headers.decode_string(net_prefs.net),
        color1=parse_pref_color(net_prefs.color1),
        color2=parse_pref_color(net_prefs.color2),
        plugins=parse_pref_plugins(net_prefs.plugins, net_prefs.plugin_count1, net_prefs.plugin_count2),
        pluginsa=parse_pref_plugins(net_prefs.pluginsa, net_prefs.plugin_count1a, net_prefs.plugin_count2a),
        difficulty=mesh_tag.difficulty(net_prefs.difficulty)
    )

def parse_pref_file(data):
    header = myth_headers.parse_header(data)
    print(header)
    pref_data = data[myth_headers.TAG_HEADER_SIZE:]

    pref_size = len(pref_data)
    print(pref_size)
    if header.tag_id == 'netw':
        net_prefs = parse_net_pref(pref_data)
        utils.print_named_tuple(net_prefs, 16)
    else:
        seqs_4 = struct.unpack(f">{pref_size//4}L", pref_data)
        seqs_2 = struct.unpack(f">{pref_size//2}H", pref_data)
        seqs_1 = struct.unpack(f">{pref_size}B", pref_data)
        print(pref_size//4)
        utils.print_bytes(seqs_4, 4)
        print(pref_size//2)
        utils.print_bytes(seqs_2, 2)
        print(pref_size)
        utils.print_bytes(seqs_1, 1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 pref2info.py <pref_file>")
        sys.exit(1)
    
    pref_file = sys.argv[1]

    try:
        main(pref_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
