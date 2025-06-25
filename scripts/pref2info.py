#!/usr/bin/env python3
import sys
import os
import struct

import codec
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

def parse_pref_color(color_data):
    (r, ra, g, ga, b, ba, flags) = struct.unpack("B B B B B B H", color_data)
    vals = ((r, g, b), (ra, ga, ba), flags)
    return f'\x1b[48;2;{r};{g};{b}m \x1b[0m {vals}'

NetPrefsFmt = ('NetPrefs', [
    ('32s', 'game_name', codec.String),
    ('64s', 'mesh_name', codec.String),
    ('32s', 'game_password', codec.String),
    ('H', 'unknown'),
    ('H', 'flag1'),
    ('H', 'flag2'),
    ('H', 'flag3'),
    ('l', 'time_limit'),
    ('4s', 'mesh_tag', codec.String),
    ('H', 'difficulty', mesh_tag.difficulty),
    ('H', 'player_limit'),
    ('H', 'load_var1'),
    ('h', 'max_teams'),
    ('4s', 'load_var2'),
    ('4x', None),
    ('H', 'unknown2'),
    ('4x', None),
    ('H', 'unknown3'),
    ('2x', None),
    ('H', 'plugin_count1'),
    ('H', 'plugin_count2'),
    ('510s', 'plugins'),
    ('68s', 'unknown4'),
    ('H', 'player_icon'),
    ('2x', None),
    ('32s', 'player_name', codec.String),
    ('32s', 'team_name', codec.String),
    ('8s', 'color1', parse_pref_color),
    ('8s', 'color2', parse_pref_color),
    ('4s', 'net', codec.String),
    ('2x', None),
    ('H', 'plugin_count1a'),
    ('H', 'plugin_count2a'),
    ('510s', 'pluginsa'),
    ('256x', None),
])

def main(pref_file):
    """
    Show info stored in preferences file
    """

    try:
        data = utils.load_file(pref_file)
        parse_pref_file(data)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_pref_plugins(plugin_data, count1):
    next_chunk = plugin_data
    plugins = []
    for i in range(count1):
        checksum = next_chunk[:4]
        (name, url, next_chunk) = next_chunk[4:].split(b'\0', 2)
        plugins.append((name, url, checksum.hex()))
    return plugins


def parse_net_pref(pref_data):
    net_prefs = codec.codec(NetPrefsFmt)(pref_data)
    return net_prefs._replace(
        plugins=parse_pref_plugins(net_prefs.plugins, net_prefs.plugin_count1),
        pluginsa=parse_pref_plugins(net_prefs.pluginsa, net_prefs.plugin_count1a),
    )

def parse_pref_file(data):
    header = myth_headers.parse_header(data)
    print(header)
    pref_data = data[myth_headers.TAG_HEADER_SIZE:]

    pref_size = len(pref_data)
    print(pref_size)
    if header.tag_id == 'netw':
        net_prefs = parse_net_pref(pref_data)
        for i, (f, val) in enumerate(net_prefs._asdict().items()):
            if type(val) is list and len(val):
                for v in val:
                    print(f'{f:<16} {v}')
            else:
                print(f'{f:>16} {utils.val_repr(val)}')
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
        print(f"Usage: python3 {sys.argv[0]} <pref_file>")
        sys.exit(1)
    
    pref_file = sys.argv[1]

    try:
        main(pref_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
