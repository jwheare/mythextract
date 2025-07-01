#!/usr/bin/env python3
import enum
import urllib.request
import urllib.parse

import codec
import mesh_tag
import utils
import player_headers

class GameOptionFlags(enum.Flag):
    RANDOM_ENDGAME_COUNTDOWN = enum.auto()
    ALLOW_MULTIPLAYER_TEAMS = enum.auto()
    LIMITED_VISIBILITY = enum.auto()
    NO_INGAME_RANKINGS = enum.auto()
    ALLOW_UNIT_TRADING = enum.auto()
    ALLOW_VETERANS = enum.auto()
    CONTINUATION = enum.auto()
    COOPERATIVE = enum.auto()
    RANDOM_TEAMS = enum.auto()
    LIMITED_TERRAIN_VISIBILITY = enum.auto()
    CAMERA_TRACKING_INITIALLY_ON = enum.auto()
    NETGAME_CUTSCENES = enum.auto()
    UNUSED2 = enum.auto()
    ALLOW_ALLIANCES = enum.auto()
    ALLOW_OVERHEAD_MAP = enum.auto()
    ORDER_GAME = enum.auto()
    SERVER_IS_OBSERVER = enum.auto()
    RESTORE_VETERANS = enum.auto()
    PATCH_VERSION_0 = enum.auto()
    PATCH_VERSION_1 = enum.auto()
    DEATHMATCH = enum.auto()
    USES_TFL = enum.auto()
    USES_ANTICLUMP = enum.auto()
    TEAM_CAPTAIN_CHOSEN = enum.auto()
    VERSION_151 = enum.auto()
    VERSION_UNUSED1 = enum.auto()
    VERSION_UNUSED2 = enum.auto()
    VERSION_UNUSED3 = enum.auto()
    VERSION_UNUSED4 = enum.auto()
    VERSION_MODIFIER = enum.auto()
    HAS_CAPTAINS = enum.auto()

NewGameDataFmt = ('NewGameData', [
    ('h', 'player_count'),
    ('h', 'local_player_index'),
    ('1984s', 'players', codec.list_codec(16, player_headers.NewPlayerDataFmt)),
    ('L', 'public_tags_checksum'),
    ('L', 'private_tags_checksum'),
])

NewGameParamDataFmt = ('NewGameParamData', [
    ('h', 'type'),
    ('h', 'scoring', utils.flag(mesh_tag.NetgameFlag)),
    
    ('L', 'option_flags', GameOptionFlags),
    
    ('l', 'time_limit'), # zero or negative is no time limit

    ('4s', 'scenario_tag'),
    
    ('h', 'difficulty_level'),
    ('h', 'maximum_players'), # for networking
    
    ('H', 'initial_team_random_seed'),
    ('h', 'maximum_teams'),
    
    ('L', 'random_seed'),

    ('l', 'pregame_time_limit'), # none if zero

    ('h', 'extra_flags'),

    ('h', 'buildnum'),
    ('l', 'version'),

    ('h', 'room_id'),
    ('h', 'plugin_count'),
    ('h', 'plugin_count2'),
    ('510s', 'plugin_data'),
])

ObserverLocationFmt = ('ObserverLocation', [
    ('l', 'position', codec.World),
    ('H', 'yaw', codec.Angle),
    ('2x', None),
])

SaveGameHeaderFmt = ('SaveGameHeader', [
    ('h', 'snapshot_width'),
    ('h', 'snapshot_height'),
    ('8s', 'observer', codec.codec(ObserverLocationFmt)),
    ('h', 'encoding'),
    ('2x', None),
    ('h', 'zoom_factor', codec.Fixed),
])

def parse_data(data):
    return codec.codec(NewGameDataFmt)(data)

def parse_params(data):
    return codec.codec(NewGameParamDataFmt)(data)

def parse_save(data):
    return codec.codec(SaveGameHeaderFmt)(data)

def find_plugin(plugin):
    # POST data
    data = {
        'plugin_name': codec.decode_string(plugin[0]),
        'plugin_url': codec.decode_string(plugin[1]),
        'plugin_checksum': plugin[2],
    }
    encoded_data = urllib.parse.urlencode(data).encode('utf-8')

    req = urllib.request.Request(
        url='https://tain.totalcodex.net/plugins/find/',
        data=encoded_data,
        method='POST',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'github.com/jwheare/mythextract',
        },
    )

    with urllib.request.urlopen(req) as response:
        result = response.read().decode('utf-8')
        if result.startswith('http://') or result.startswith('https://'):
            return result

def print_plugins(plugins, find=False):
    for p in plugins:
        print(f'- Plugin: {codec.decode_string(p[0])}')
        if find:
            tain_url = find_plugin(p)
            if tain_url:
                print(f'- Tain: {tain_url}')
            else:
                print('- Tain: NOT_FOUND')
