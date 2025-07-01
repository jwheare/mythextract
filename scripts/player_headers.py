#!/usr/bin/env python3
import enum

import codec
import pref2info

class PlayerFlags(enum.Flag):
    USES_APPEARANCE_COLORS = enum.auto()
    IS_FROM_BUNGIE = enum.auto()
    HAS_BEEN_DROPPED = enum.auto()
    HAS_BEEN_SORTED = enum.auto()
    HAS_CD = enum.auto()
    HAS_INVALID_CAPTAIN = enum.auto()
    IS_OBSERVER = enum.auto()

PlayerAppearanceFmt = ('PlayerAppearance', [
    ('h', 'coat_of_arms_bitmap_index'),
    ('h', 'caste_bitmap_index'),
    ('32s', 'name', codec.String),
    ('32s', 'team_name', codec.String),
    ('8s', 'color1', pref2info.parse_pref_color),
    ('8s', 'color2', pref2info.parse_pref_color),
])

NewPlayerDataFmt = ('NewPlayerData', [
    ('h', 'team_index'),
    ('h', 'type'),
    ('h', 'flags', PlayerFlags),
    ('h', 'order'),
    ('l', 'team_captain_identifier'),
    ('l', 'unique_identifier'),

    ('l', 'agreed_to_play'), # boolean
    ('l', 'team_is_locked'), # boolean

    ('L', 'metaserver_player_id'),
    ('b', 'metaserver_player'),
    ('b', 'persistent_ready'),
    ('h', 'version'),
    ('h', 'build_number'),
    ('6x', None),

    ('84s', 'appearance', codec.codec(PlayerAppearanceFmt)),
])

def is_observer(player):
    return PlayerFlags.IS_OBSERVER in player.flags

def colors(player):
    return (player.appearance.color1.split(' (')[0], player.appearance.color2.split(' (')[0])

def colors_rgb(player):
    return (
        "rgb" + player.appearance.color1.split(' (')[1].strip(','),
        "rgb" + player.appearance.color2.split(' (')[1].strip(','),
    )
