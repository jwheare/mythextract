#!/usr/bin/env python3
from collections import OrderedDict, Counter, defaultdict
import enum
import datetime
import json
import os
import pathlib
import re
import struct
import sys

import codec
import myth_headers
import mesh_tag
import mesh2trades
import mons_tag
import pref2info
import utils
import loadtags
import game_headers
import player_headers

DEBUG = (os.environ.get('DEBUG') == '1')
DEBUG_CMDS = (os.environ.get('DEBUG_CMDS') == '1')
DEBUG_PICKUP = (os.environ.get('DEBUG_PICKUP') == '1')

HEADER_SIZE = 2606

class Commands(enum.Enum):
    # used by the server when no one is giving orders (0-1)
    NULL = 0
    SYNC = enum.auto()
    
    # monster commands (2-8)
    GENERAL = enum.auto()
    MOVEMENT = enum.auto()
    TARGET = enum.auto()
    ATTACK_LOCATION = enum.auto() # a specific (x,y,z) point
    PICK_UP = enum.auto() # an object_index/object_identifier pair
    RENAME = enum.auto()
    ROTATION = enum.auto()
    
    # player commands (9-14)
    DROP_PLAYER = enum.auto()
    CHAT = enum.auto()
    DETACH = enum.auto()
    UNIT_ADJUSTMENT = enum.auto()
    SKETCH = enum.auto()
    ALLY = enum.auto()
    
    # commands intended only to encode information in saved games (15-16)
    PRESET_SELECTION = enum.auto()
    SYNC_FORMATION = enum.auto()

    # extra commands hacked on by rank amateurs (17-20)
    INVENTORY = enum.auto()
    INVENTORY_DROP = enum.auto()
    INVENTORY_PREV = enum.auto()
    INVENTORY_NEXT = enum.auto()

    FORCED_ENDGAME = enum.auto()
    ADD_PLAYER = enum.auto()

    PAUSE = enum.auto()
    GAME_SPEED = enum.auto()
    SAVE_LOADED = enum.auto()
    REPLACE_PLAYER = enum.auto()
    SET_TEAM_CAPTAIN = enum.auto()

class GeneralCommands(enum.Enum):
    STOP = 0
    SCATTER = enum.auto()
    RETREAT = enum.auto()
    SPECIAL_ABILITY = enum.auto() # immediate (suicide, place satchel charge, etc.)
    GUARD = enum.auto()
    TAUNT = enum.auto()
    CELEBRATE = enum.auto()

class TargetFlags(enum.Flag):
    CLOSE = enum.auto() # close distance with target
    SPECIAL_ABILITY = enum.auto()
    DONT_OVERRIDE_LOCAL_AI = enum.auto()
    ATTACK_CLOSEST = enum.auto()
    DONT_OVERRIDE_EXISTING_TARGET = enum.auto()
    USE_COMMAND = enum.auto()
    PLAYER_INITIATED = enum.auto()
    ATTACK_INDIVIDUAL = enum.auto()
    USE_CLOSEST_ATTACK = enum.auto()
    USE_184_MATCHING = enum.auto()

class AttackLocationFlags(enum.Flag):
    SPECIAL_ABILITY = enum.auto()
    IGNORE_MODEL_COLLISION = enum.auto()
    FROM_MAP_ACTION = enum.auto()

class ChatFlags(enum.Flag):
    PRIVATE = enum.auto()

CommandHeaderFmt = ('CommandHeader', [
    ('h', 'size'),
    ('b', 'verb', Commands),
    ('b', 'player_index'),
    ('l', 'time'),
])

RecoHeaderFmt = ('RecoHeader', [
    ('h', 'version'),
    ('h', 'type'),
    ('l', 'data_offset'),
    ('l', 'recording_ending_time'),

    ('l', 'snapshot_offset'),
    ('l', 'snapshot_length'),
    
    ('l', 'monster_initializers_offset'),
    ('l', 'monster_initializers_length'),
    
    ('l', 'monster_placement_offset'),
    ('l', 'monster_placement_length'),
])

RecordingBlockHeaderFmt = ('RecordingBlockHeader', [
    ('L', 'flags'),
    ('h', 'size'), # in byte
    ('h', 'command_count'),
])

MonsterInitializerFmt = ('MonsterInitializer', [
    ('L', 'flags'),
    ('L', 'owner_player_identifier'),
    ('4s', 'unit_tag'),
    ('4s', 'monster_tag'),
    
    ('b', 'experience'),
    ('B', 'battles_survived'),
    ('B', 'color_table_permutation'),
    ('B', 'original_name_string_index'),
    
    ('2x', None),
    
    ('18s', 'name'),
])

BAGRADA_MATCH = r'bagrada\d{4,4}_\d{2,2}_\d{2,2}__\d{2,2}_\d{2,2}_\d{2,2}_\d{2,3}.m2rec'

def fetch_bagrada_stats(file_path):
    file_name = pathlib.Path(file_path).name
    if not re.match(BAGRADA_MATCH, file_name):
        return
    # https://bagrada.net/rank-server/api/public/games?recordingFileName=bagrada2025_06_22__20_39_32_13.m2rec
    data = {
        'recordingFileName': file_name,
    }
    url = 'https://bagrada.net/rank-server/api/public/games'
    (status, headers, response_text) = utils.http_request(url, 'GET', data)
    result = json.loads(response_text)
    if result and 'content' in result and len(result['content']) == 1:
        return result['content'][0]

def player_by_bagrada_id(bagrada_id, players):
    return next((
        (pi, p) for pi, p in (players).items() if p.metaserver_player_id == bagrada_id
    ), None)

def process_stats(bagrada_stats, players):
    if not bagrada_stats or 'teams' not in bagrada_stats:
        return
    info = {
        'team_info': {},
        'player_stats': {},
        'overall_stats': {
            'kills': 0,
            'losses': 0,
            'dmg_out': 0,
            'dmg_in': 0,
        },
        'host': None,
        'tie': False,
        'tie_teams': [],
        'winning_bagrada_captain': None,
    }

    winning_bagrada_captains = []
    for bagrada_team in bagrada_stats['teams']:
        spectators = bagrada_team.get('spectators', False)
        if 'players' in bagrada_team:
            # Check players for host first
            host = next((
                b_p for b_p in bagrada_team['players'] if b_p.get('host')
            ), None)
            if host:
                info['host'] = {
                    'name': host.get('nickName', 'Unknown'),
                    'bagrada_player': host.get('userId', None),
                    'observer': spectators,
                }
            # Only continue for non spectator teams
            if not spectators:
                process_team_stats(
                    info, winning_bagrada_captains, # these get modified by the function
                    bagrada_team, players
                )

    calculate_extra_stats(info['overall_stats'])

    if len(winning_bagrada_captains):
        if info['tie']:
            info['tie_teams'] = winning_bagrada_captains
        else:
            info['winning_bagrada_captain'] = winning_bagrada_captains[0]

    bagrada_stats['processed'] = info

def process_team_stats(info, winning_bagrada_captains, bagrada_team, players):
    team_info = {
        "stats": {
            'kills': 0,
            'losses': 0,
            'dmg_out': 0,
            'dmg_in': 0,
        },
    }
    if 'place' in bagrada_team:
        team_info["place"] = bagrada_team["place"]
    if 'placeTie' in bagrada_team:
        team_info["place_tie"] = bagrada_team["placeTie"]
    if 'eliminated' in bagrada_team:
        team_info["eliminated"] = bagrada_team["eliminated"]
    captain_id = None
    for bagrada_player in bagrada_team['players']:
        # Find player by metaserver_player_id
        p_res = player_by_bagrada_id(bagrada_player.get('userId'), players)
        if p_res:
            (player_id, player) = p_res
            bagrada_player_stats = {}
            captain_id = player.team_captain_identifier
            if captain_id == player_id:
                if team_info["place"] == 1:
                    winning_bagrada_captains.append(bagrada_player['userId'])
                    if team_info["place_tie"]:
                        info['tie'] = True
                        team_info['tied_winner'] = True
                    else:
                        team_info['winner'] = True
            bagrada_player_stats = {}
            if 'unitsKilled' in bagrada_player:
                bagrada_player_stats['kills'] = bagrada_player['unitsKilled']
                team_info['stats']['kills'] += bagrada_player['unitsKilled']
                info['overall_stats']['kills'] += bagrada_player['unitsKilled']
            if 'unitsLost' in bagrada_player:
                bagrada_player_stats['losses'] = bagrada_player['unitsLost']
                team_info['stats']['losses'] += bagrada_player['unitsLost']
                info['overall_stats']['losses'] += bagrada_player['unitsLost']
            if 'damageGiven' in bagrada_player:
                bagrada_player_stats['dmg_out'] = bagrada_player['damageGiven']
                team_info['stats']['dmg_out'] += bagrada_player['damageGiven']
                info['overall_stats']['dmg_out'] += bagrada_player['damageGiven']
            if 'damageTaken' in bagrada_player:
                bagrada_player_stats['dmg_in'] = bagrada_player['damageTaken']
                team_info['stats']['dmg_in'] += bagrada_player['damageTaken']
                info['overall_stats']['dmg_in'] += bagrada_player['damageTaken']
            calculate_extra_stats(bagrada_player_stats)
            info['player_stats'][player_id] = bagrada_player_stats
    if captain_id is not None:
        calculate_extra_stats(team_info['stats'])
        info['team_info'][captain_id] = team_info

def calculate_extra_stats(stats):
    if 'dmg_out' in stats and 'dmg_in' in stats:
        stats['dmg_ratio'] = round(stats['dmg_out'] / max(1, stats['dmg_in']), 2)
    if 'kills' in stats and 'dmg_in' in stats:
        stats['kill_loss_ratio'] = round(stats['kills'] / max(1, stats['losses']), 2)

def print_metaserver_info(teams_idx, teams, players, game_stats):
    game_header = game_stats['header']['game']
    if game_header['host'] is not None:
        print(
            f'Host: {utils.strip_format(game_header['host']['name'])}\n'
        )
    # TODO better check for metaserver stats
    if 'game_name' in game_header:
        print(game_header['game_name'])
        if game_header['room_type'] == 2:
            print('Room: Ranked')
        else:
            print('Room: Normal')
        start = datetime.datetime.fromisoformat(game_header['start']).astimezone()
        end = datetime.datetime.fromisoformat(game_header['end']).astimezone()
        date_part = start.strftime("%a %b %d, %Y")
        time_range = f"{start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p %Z (%z)')}"
        print(f"{date_part} {time_range}")
        print(f'Bagrada: https://bagrada.net/webui/games/{game_header["bagrada_game"]}')

        print('\n---\n')

def parse_reco_head(game_directory, reco_file, head_only=False):
    length = (myth_headers.TAG_HEADER_SIZE + HEADER_SIZE) if head_only else None
    data = utils.load_file(reco_file, length)
    header = myth_headers.parse_header(data)
    reco_data = data[myth_headers.TAG_HEADER_SIZE:]

    if DEBUG:
        print(header)
        reco_size = len(reco_data)
        print(reco_size)

    # RecoHeader
    # NewGameParamDataFmt
    # NewGameDataFmt
    # SaveGameHeader

    offset = 0
    reco = codec.codec(RecoHeaderFmt)(reco_data)

    if DEBUG:
        print(f'# {reco._name} [{offset}]')
        for i, (f, val) in enumerate(reco._asdict().items()):
            print(f'{f:<42} {utils.val_repr(val)}')

    offset += reco.data_size()
    game_param = game_headers.parse_params(reco_data[offset:])
    game_param = game_param._replace(
        plugin_data=pref2info.parse_pref_plugins(game_param.plugin_data, game_param.plugin_count)
    )

    if DEBUG:
        print(f'\n# {game_param._name} [{offset}]')
        for i, (f, val) in enumerate(game_param._asdict().items()):
            print(f'{f:<42} {utils.val_repr(val)}')

    offset += game_param.data_size()
    game_data = game_headers.parse_data(reco_data[offset:])
    game_data = game_data._replace_raw(
        players=game_data.players[:game_data.player_count]
    )

    if DEBUG:
        print(f'\n# {game_data._name} [{offset}]')
        for i, (f, val) in enumerate(game_data._asdict().items()):
            if f == 'players':
                for pi, player in enumerate(val):
                    print(f'players: {pi:<33} {utils.val_repr(player)}')
            else:
                print(f'{f:<42} {utils.val_repr(val)}')

    offset += game_data.data_size()
    save_game = game_headers.parse_save(reco_data[offset:])

    if DEBUG:
        print(f'\n# {save_game._name} [{offset}]')
        for i, (f, val) in enumerate(save_game._asdict().items()):
            print(f'{f:<42} {utils.val_repr(val)}')

    offset += save_game.data_size()
    if DEBUG:
        print('header offset', offset)

    return (header, reco_data, reco, game_param, game_data, save_game)

def parse_reco_file(game_directory, reco_file):
    (header, reco_data, reco, game_param, game_data, save_game) = parse_reco_head(game_directory, reco_file)

    plugin_names = [codec.decode_string(p[0]) for p in game_param.plugin_data]
    for plugin in plugin_names:
        if not pathlib.Path(game_directory, 'plugins', plugin).exists():
            print(f'Missing plugin: {plugin}')
            game_headers.print_plugins(game_param.plugin_data, True)
            sys.exit(1)
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    metaserver_stats = fetch_bagrada_stats(reco_file)

    return parse_timeline(
        header, tags, data_map, game_data,
        game_param, reco, reco_data, metaserver_stats
    )

def parse_mons_initializers(tags, data_map, reco, reco_data):
    mons_start = reco.monster_initializers_offset
    mons_end = mons_start + reco.monster_initializers_length

    print('monster_initializers')
    monster_initializers = codec.list_codec(None, MonsterInitializerFmt)(reco_data[mons_start:mons_end])
    for i, mons_init in enumerate(monster_initializers):
        (mons_loc, mons_header, mons_data) = loadtags.get_tag_info(
            tags, data_map, 'mons', codec.decode_string(mons_init.monster_tag)
        )

        (unit_loc, unit_header, unit_data) = loadtags.get_tag_info(
            tags, data_map, 'unit', codec.decode_string(mons_init.unit_tag)
        )
        print(
            f'{i:>2} [{mons_init.experience}] '
            f'{unit_header.name} / {mons_header.name}'
        )

def print_teams(teams, players, players_idx):
    print('Teams\n')
    for cap_id, team_players in teams.items():
        cap = players[cap_id]
        print(f'[{cap.team_index}] {utils.strip_format(cap.appearance.team_name)}')
        for p_i, player_id in enumerate(team_players):
            player = players[player_id]
            print(
                f'{players_idx.index(player_id):>2}: '
                f'{player_headers.colors(cap)[0]}'
                f'{player_headers.colors(player)[0]} '
                f'{"*" if cap_id == player.unique_identifier else " "} '
                f'{player.unique_identifier:<2} '
                f'{player_name(player)}'
            )
        print('---')

def player_name(player):
    return utils.strip_order(utils.strip_format(player.appearance.name))

def setup_teams(game_data, game_param, palette, mesh_header):
    players = OrderedDict()
    players_idx = []
    observers = {}
    computer_players = {}
    # Filter out observers and set up indexes
    # players: player objects by id in consistent order
    # players_idx: player_ids by index
    # observers: observer player_ids
    for player in game_data.players:
        player_id = player.unique_identifier
        if player.type == 0:
            if player_headers.is_observer(player) or player.team_captain_identifier in observers:
                observers[player_id] = player
            else:
                players_idx.append(player_id)
                players[player_id] = player
        else:
            computer_players[player_id] = player

    # Don't trust game_param.maximum_teams, scan marker palette to determine team count
    if mesh_tag.is_single_player(mesh_header):
        max_teams = 1
    else:
        max_teams = max([
            unit_palette['team_index'] + 1 for unit_palette in palette[mesh_tag.MarkerType.UNIT]
        ])

    # TODO subtract prohibited teams for this game type if defined by the map action

    initial_rand = game_param.random_seed

    while True:
        # Build teammate and solo lists
        team_players = {}
        solo_players = []
        for player_id, player in players.items():
            captain_id = player.team_captain_identifier
            if captain_id > -1:
                if captain_id not in team_players:
                    team_players[captain_id] = []
                team_players[captain_id].append(player_id)
            else:
                solo_players.append(player_id)

        if DEBUG:
            print('[solo_players]', [f'{player_id} {player_name(players[player_id])}' for player_id in solo_players])
            for captain_id, team_mates in team_players.items():
                print(f'[team_players] {captain_id}', [f'{player_id} {player_name(players[player_id])}' for player_id in team_mates])
            print(f'= max={max_teams} captains={len(team_players)}')

        # Disband smallest teams if we have too many
        while len(team_players) > max_teams:
            if DEBUG:
                print('> too many captains, disbanding')
            # Find first smallest team captain
            smallest_team_captain = None
            smallest_team_player_count = 16

            for player_id, player in players.items():
                cap_id = player.team_captain_identifier
                if cap_id in team_players and len(team_players[cap_id]) < smallest_team_player_count:
                    if DEBUG:
                        print('smallest candidate', len(team_players[cap_id]), cap_id, player_id, player_name(player))
                    smallest_team_captain = cap_id
                    smallest_team_player_count = len(team_players[cap_id])

            if DEBUG:
                print('smallest team', smallest_team_player_count, smallest_team_captain, player_name(players[smallest_team_captain]))

            # Unset smallest captain from players, remove the lookup and add to solo players
            for player_id, player in players.items():
                if player_id == smallest_team_captain:
                    if DEBUG:
                        print('>> disband team', player_id, player_name(player))
                    del team_players[player_id]
                if player.team_captain_identifier == smallest_team_captain:
                    if DEBUG:
                        print('>> make solo', player_id, player_name(player))
                    players[player_id] = player._replace(team_captain_identifier=-1)
                    solo_players.append(player_id)

        # No more teams to disband and not enough players to make new teams, we're done
        if DEBUG:
            print(f'= max={max_teams} teams={len(team_players)} solos={len(solo_players)} teams+solos={len(team_players) + len(solo_players)}')
        if (len(team_players) + len(solo_players)) <= max_teams:
            if DEBUG:
                print('> no more teams to create, done')
            break

        if len(team_players) < max_teams:
            if DEBUG:
                print('> promote solos')
            # Promote solos to captains if we can fill more teams
            if len(solo_players):
                # Pop a *random* solo
                (r, initial_rand) = utils.myth_random(initial_rand)
                idx = r % len(solo_players)
                random_solo_id = solo_players.pop(idx)
                if DEBUG:
                    print('>> promote solo to cap', random_solo_id, player_name(players[random_solo_id]))
                # Add to team and set captain
                team_players[random_solo_id] = [random_solo_id]
                players[random_solo_id] = players[random_solo_id]._replace(
                    team_captain_identifier=random_solo_id
                )
            else:
                # No players to promote, we're done
                break
        else:
            if DEBUG:
                print('> add solos to teams')
            # Add solos to teams if we can't fill more teams
            weakest_team_size = 16
            weakest_captains = []
            for player_id, player in players.items():
                if player_id in team_players:
                    team_mate_count = len(team_players[player_id])
                    if team_mate_count <= weakest_team_size:
                        if team_mate_count < weakest_team_size:
                            weakest_captains = []    
                        weakest_team_size = team_mate_count
                        weakest_captains.append(player_id)

            if DEBUG:
                [print(f'[weakest captains] {captain_id} {player_name(players[captain_id])}') for captain_id in weakest_captains]

            if len(solo_players) and len(weakest_captains):
                # Pop a random solo
                (r, initial_rand) = utils.myth_random(initial_rand)
                idx = r % len(solo_players)
                random_solo_id = solo_players.pop(idx)
                if DEBUG:
                    print(f'>> add solo to team [solo]: {random_solo_id} {player_name(players[random_solo_id])}')
                # Get a *random* weakest captain
                (r, initial_rand) = utils.myth_random(initial_rand)
                idx = r % len(weakest_captains)
                random_weakest_captain = weakest_captains[idx]
                if DEBUG:
                    print(f'>> add solo to team [team]: {random_weakest_captain} {player_name(players[random_weakest_captain])}')

                players[random_solo_id] = players[random_solo_id]._replace(
                    team_captain_identifier=random_weakest_captain
                )
                team_players[random_weakest_captain].append(random_solo_id)
            else:
                # No solos or weak captains, we're done
                break

    # end while

    # TODO arbitrate colors (actual_player_count)

    # Create empty team slots for each team
    # teams_idx: actual teams slots for the game, to be filled with captain ids
    teams_idx = max_teams * [None]

    # Assign captains and remaining solos to teams
    # teams: lookup from captain id to list of player ids
    teams = {}
    team_rand = game_param.initial_team_random_seed
    for player_id, player in players.items():
        if player_id in solo_players or player_id in team_players:
            # Choose a random starting team index
            (r, team_rand) = utils.myth_random(team_rand)
            original_team_index = r % max_teams
            if DEBUG:
                print(f'= starting random team index {original_team_index}')
            team_index = original_team_index
            while True:
                # If team is unclaimed it will be None
                if teams_idx[team_index] is None:
                    # Set team_index, assign captain to teams_idx, and initialize teams players
                    if DEBUG:
                        print(f'>> team={team_index} assign captain: {player_id} {player_name(player)}')
                    players[player_id] = player._replace(team_index=team_index)
                    teams_idx[team_index] = player_id
                    teams[player_id] = [player_id]
                    break
                if DEBUG:
                    print(f'team={team_index} already claimed, increment')
                team_index = (team_index + 1) % max_teams
                if original_team_index == team_index:
                    if DEBUG:
                        print(f'! team={team_index} looped back to start={original_team_index}, break')
                    break
        else:
            # Not a team captain, make sure team_index is unset just in case it was set in the film
            players[player_id] = player._replace(team_index=-1)

    # Assign non captain team mates to teams
    for player_id, player in players.items():
        captain_id = player.team_captain_identifier
        # If not in team and has captain
        if player.team_index < 0 and captain_id > -1:
            # Set team_index to captain team_index and add to team players
            if DEBUG:
                print(f'team={players[captain_id].team_index} assign player: {player_id} {player_name(player)}')
            players[player_id] = player._replace(team_index=players[captain_id].team_index)
            teams[captain_id].append(player_id)

    return (players, players_idx, teams, teams_idx, observers, computer_players)

def get_trades(
    tags, data_map, palette, mesh_header,
    level_name, game_param, game_type_choice, game_time,
    unit_counts, players_idx, captain
):
    (trade_info, units, _game_type) = mesh2trades.parse_game_teams(
        tags, data_map, palette, mesh_header,
        level_name, game_param.difficulty_level, game_type_choice, game_time,
        unit_counts, captain.team_index, adjust=True
    )

    team_markers = {}
    # Build monster index
    for tag_id, u in units.items():
        if u['count']:
            for unit_palette in palette[mesh_tag.MarkerType.UNIT]:
                if unit_palette['team_index'] == captain.team_index and unit_palette['tag'] == tag_id:
                    markers = unit_palette['markers']
                    selected = 0
                    for marker in sorted_markers(markers, game_param):
                        marker['player_id'] = captain.unique_identifier
                        marker['player_index'] = players_idx.index(captain.unique_identifier)
                        team_markers[marker['marker_id']] = marker
                        selected += 1
                        if selected >= u['count']:
                            break
    return (trade_info, units, team_markers)

def get_computers(tags, data_map, palette, mesh_header):
    computer_markers = {}
    computer_monsters = {}
    sp = mesh_tag.is_single_player(mesh_header)
    for tag_id, unit_palette in enumerate(palette[mesh_tag.MarkerType.UNIT]):
        if (sp and unit_palette['team_index'] != 0) or unit_palette['team_index'] < 0:
            markers = unit_palette['markers']
            for marker_id, marker in markers.items():
                tag_id = marker['tag']
                if tag_id not in computer_monsters:
                    mons_dict = mons_tag.unit_stats(tags, data_map, tag_id)
                    computer_monsters[tag_id] = mons_dict
                computer_markers[marker['marker_id']] = tag_id
    return (computer_markers, computer_monsters)

def get_ambients(tags, data_map, palette):
    ambients = {}
    ambient_monsters = {}
    for tag_id, unit_palette in enumerate(palette[mesh_tag.MarkerType.UNIT]):
        if unit_palette['team_index'] == -1:
            markers = unit_palette['markers']
            for marker_id, marker in markers.items():
                tag_id = marker['tag']
                if tag_id not in ambient_monsters:
                    mons_dict = mons_tag.unit_stats(tags, data_map, tag_id)
                    ambient_monsters[tag_id] = mons_dict
                ambients[marker['marker_id']] = tag_id
    return (ambients, ambient_monsters)

def init_cmd_counters():
    return {
        'player': Counter(),
        'team': Counter(),
        'overall': 0,
    }

def parse_timeline(
    reco_header, tags, data_map, game_data,
    game_param, reco, reco_data, metaserver_stats
):
    # Get mesh tag data
    (mesh_tag_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(
        tags, data_map, 'mesh', codec.decode_string(game_param.scenario_tag)
    )
    try:
        mesh_header = mesh_tag.parse_header(mesh_tag_data)
    except (struct.error, UnicodeDecodeError):
        print("Error loading mesh")
        sys.exit(1)

    (palette, orphans) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)

    level_name = mesh_tag.get_level_name(mesh_header, tags, data_map)

    overhead_map_data = loadtags.get_tag_data(
        tags, data_map, '.256', codec.decode_string(
            mesh_header.overhead_map_collection_tag
        )
    )

    (ambients, ambient_monsters) = get_ambients(tags, data_map, palette)
    (computer_markers, computer_monsters) = get_computers(tags, data_map, palette, mesh_header)
    
    game_type_choice = mesh_tag.NetgameFlagInfo[game_param.scoring]
    game_time = game_param.time_limit/30/60
    planning_ticks = game_param.pregame_time_limit

    # Set up teams
    (
        players, players_idx, teams, teams_idx, observers, computer_players
    ) = setup_teams(
        game_data, game_param, palette, mesh_header
    )
    if DEBUG:
        print_teams(teams, players, players_idx)
    process_stats(metaserver_stats, players)

    chat_lines = []
    counters = {
        'command': init_cmd_counters(),
        'engage': init_cmd_counters(),
        'chat': init_cmd_counters(),
    }
    self_heal_kill_dmg = defaultdict(Counter)
    block_header_codec = codec.codec(RecordingBlockHeaderFmt)
    command_header_codec = codec.codec(CommandHeaderFmt)
    block_offset = reco.data_offset
    splits = None
    game_header = {
        'time_limit': game_param.time_limit,
        'game_type': mesh_tag.NetgameNames[game_type_choice],
        'map_name': mesh_tag.get_level_name(mesh_header, tags, data_map, True),
        'difficulty': mesh_tag.difficulty(game_param.difficulty_level),
        'host': None,
        'stats': {}
    }
    metaserver_player_stats = {}
    metaserver_team_info = {}
    if metaserver_stats:
        game_header = game_header | {
            'game_name': metaserver_stats.get('gameName').rstrip(),
            'room_type': metaserver_stats.get('roomType'),
            'start': metaserver_stats.get('startDatetime'),
            'end': metaserver_stats.get('endDatetime'),
            'bagrada_game': metaserver_stats.get('id'),
        }
        if 'processed' in metaserver_stats:
            game_header['host'] = metaserver_stats['processed']['host']
            game_header['tie'] = metaserver_stats['processed']['tie']
            game_header['tie_teams'] = metaserver_stats['processed']['tie_teams']
            game_header['winning_bagrada_captain'] = metaserver_stats['processed']['winning_bagrada_captain']

            game_header['stats'] = metaserver_stats['processed']['overall_stats']
            metaserver_player_stats = metaserver_stats['processed']['player_stats']
            metaserver_team_info = metaserver_stats['processed']['team_info']
    game_stats = {
        'header': {
            'game': game_header,
            'teams': {
                team_index: {
                    'name': utils.strip_format(players[cap_id].appearance.team_name),
                    'captain': {
                        'player': cap_id,
                        'bagrada_player': players[cap_id].metaserver_player_id,
                        'name': utils.strip_format(players[cap_id].appearance.name),
                    },
                    'color': player_headers.colors_rgb(players[cap_id]),
                    'players': {
                        player_id: {
                            'name': utils.strip_format(player.appearance.name),
                            'bagrada_player': player.metaserver_player_id,
                            'color': player_headers.colors_rgb(player),
                            'stats': metaserver_player_stats.get(player_id, {}),
                            'captain': player_id == cap_id,
                            'medals': [],
                        }
                        for player_id, player in players.items() if player.team_index == team_index
                    },
                    'stats': metaserver_team_info.get(cap_id, {}).get('stats', {})
                } | {k: v for k, v in metaserver_team_info.get(cap_id, {}).items() if k != 'stats'}
                for team_index, cap_id in enumerate(teams_idx) if cap_id is not None
            },
        },
        'commands': []
    }

    monsters = {}
    trades = {}
    for team_index, cap_id in enumerate(teams_idx):
        if cap_id is not None:
            (trade_info, units, team_markers) = get_trades(
                tags, data_map, palette, mesh_header,
                level_name, game_param, game_type_choice, game_time,
                [], players_idx, players[cap_id]
            )
            monsters[team_index] = team_markers
            trades[team_index] = (trade_info, units)
            if DEBUG:
                print('trades', team_index, units.keys())
    if DEBUG:
        print_trades(teams_idx, trades)

    prev_command_time = None
    while block_offset < len(reco_data):
        block_header = block_header_codec(reco_data[block_offset:])
        if DEBUG_CMDS:
            print(block_header)

        commands_start = block_offset + block_header.data_size()
        commands_end = commands_start + block_header.size
        commands_data = reco_data[commands_start:commands_end]

        command_offset = 0
        for command_i in range(block_header.command_count):
            command_header = command_header_codec(commands_data[command_offset:])
            command_data_start = command_offset + command_header.data_size()
            command_data_end = command_offset + command_header.size
            command_data = commands_data[command_data_start:command_data_end]

            (pt, remaining) = time_vars(command_header.time, game_param)

            if DEBUG_CMDS:
                print(command_i, tick_to_time(pt, remaining), command_header.time, prev_command_time, planning_ticks)

            player = None
            # This changed after 1.8.4
            if game_param.version <= 2184:
                player_idx = command_header.player_index
                player_id = players_idx[player_idx]
            else:
                player_id = command_header.player_index
                player_idx = players_idx.index(player_id) if player_id in players_idx else None

            if player_id in players:
                player = players[player_id]
                if DEBUG_CMDS:
                    print(f'- player_id={player_id} (idx={player_idx}) team={player.team_index}')
            if command_header.verb == Commands.UNIT_ADJUSTMENT:
                (unit_adjust_flags, unit_count) = struct.unpack('>h h', command_data[:4])
                unit_counts = codec.list_pack('unit_counts', unit_count, '>h')(command_data[4:])
                (trade_info, units, team_markers) = get_trades(
                    tags, data_map, palette, mesh_header,
                    level_name, game_param, game_type_choice, game_time,
                    unit_counts, players_idx, player
                )
                monsters[player.team_index] = team_markers
                trades[player.team_index] = (trade_info, units)
                if DEBUG:
                    print('trades', player.team_index, units.keys())
                if DEBUG_CMDS:
                    print(
                        f'{tick_to_time(pt, command_header.time)}: '
                        f'[player={player.unique_identifier:<2} team_index={player.team_index}] '
                        f'Adjust Units={unit_counts} '
                        f'{player_name(player)}'
                    )
                    ((diffs, trade), units) = trades[player.team_index]
                    print('\n'.join(trade))

            elif command_header.verb == Commands.DETACH:
                (detach_flags, player_index, monster_count) = struct.unpack('>h h h', command_data[:6])
                monster_ids = codec.list_pack('monster_ids', monster_count, '>h')(command_data[6:])
                detached = []
                if DEBUG_CMDS:
                    print(
                        f'from_id={player_id} '
                        f'to_idx={player_index} to_id={players_idx[player_index]} '
                        f'team_index={player.team_index} '
                        f'monster_teams={list(monsters.keys())} '
                        f'players_idx={players_idx} ({len(players_idx)})'
                    )
                    print('team_monsters', list(monsters[player.team_index].keys()))
                for monster_id in monster_ids:
                    if monster_id in monsters[player.team_index]:
                        monsters[player.team_index][monster_id]['player_id'] = players_idx[player_index]
                        monsters[player.team_index][monster_id]['player_index'] = player_index
                        detached.append(str(monsters[player.team_index][monster_id]['tag']))
                    else:
                        print(f'! {monster_id} missing from team {player.team_index} monsters')
                if DEBUG_CMDS:
                    to_player = player_name(players[players_idx[player_index]])
                    print(
                        f'{tick_to_time(pt, command_header.time)}: '
                        f'[player={player.unique_identifier:<2} team_index={player.team_index}] '
                        f'DETACH {player_name(player)} '
                        f'-> {to_player}[{player_index}] id={players_idx[player_index]} ' 
                        f'{dict(Counter(detached)), monster_ids}'
                    )
                # TODO log_command

            elif command_header.verb == Commands.CHAT:
                (chat_flags,) = struct.unpack('>h', command_data[:2])
                chat_message = codec.decode_string(command_data[2:])
                chat_lines.append((pt, command_header.time, player, chat_flags, chat_message))

                counters['chat']['player'][player_id] += 1
                counters['chat']['team'][player.team_index] += 1
                counters['chat']['overall'] += 1
                if DEBUG_CMDS:
                    print(
                        f'{tick_to_time(pt, command_header.time)}: '
                        f'{chat_message}'
                    )

            elif command_header.verb in [
                Commands.MOVEMENT,
                Commands.GENERAL,
                Commands.TARGET,
                Commands.PICK_UP,
                Commands.ATTACK_LOCATION,
                Commands.ROTATION,
            ]:  
                if DEBUG_CMDS:
                    print(
                        f'{tick_to_time(pt, command_header.time)}: '
                        f'{command_header.verb} '
                    )
                if command_header.time > planning_ticks:
                    cmd = log_command(
                        players, player_id, monsters, computer_markers, computer_monsters, trades,
                        command_header, command_data, self_heal_kill_dmg, planning_ticks
                    )
                    if cmd:
                        if cmd.get('self_heal_kill'):
                            validate_self_heal_kill_dmg(self_heal_kill_dmg, players_idx, monsters, trades)
                        game_stats['commands'].append(cmd)

                    if player:
                        # init team and player indexes
                        counters['command']['player'][player_id] += 1
                        counters['command']['team'][player.team_index] += 1
                        counters['command']['overall'] += 1
                        if is_engagement(cmd):
                            counters['engage']['player'][player_id] += 1
                            counters['engage']['team'][player.team_index] += 1
                            counters['engage']['overall'] += 1

            else:
                if DEBUG_CMDS:
                    print(
                        f'{tick_to_time(pt, command_header.time)}: '
                        f'{command_header.verb} {command_data.hex()}'
                    )

            if pt_over(prev_command_time, command_header.time, game_param):
                splits = get_splits(monsters, trades)
                if DEBUG_CMDS:
                    print_splits(players, players_idx, teams_idx, trades, splits)

            prev_command_time = command_header.time
            command_offset = command_data_end

        block_offset = commands_end
        if DEBUG_CMDS:
            print('block_offset', block_offset)

    # end blocks

    process_splits(game_stats, trades, splits, players_idx)
    process_counters(game_stats, players, counters, self_heal_kill_dmg)

    return (
        reco_header, players, players_idx, monsters, teams, teams_idx, game_param.plugin_data,
        mesh_header, level_name, game_time, game_type_choice, game_param.difficulty_level,
        overhead_map_data, chat_lines, trades, splits, game_stats
    )

def validate_self_heal_kill_dmg(self_heal_kill_dmg, players_idx, monsters, trades):
    for player_id, self_heal_kill_dmg_pallette in self_heal_kill_dmg.items():
        palette_max_dmg_counter = Counter()

        for team_index, team_monsters in monsters.items():
            (trade_info, units) = trades[team_index]
            for marker_id, marker in team_monsters.items():
                tag_id = marker['tag']
                if player_id == players_idx[marker['player_index']]:
                    palette_max_dmg_counter[tag_id] += units[tag_id]['cost']

        for tag_id, self_heal_kill_dmg_item in self_heal_kill_dmg_pallette.items():
            self_heal_kill_dmg_pallette[tag_id] = min(self_heal_kill_dmg_item, palette_max_dmg_counter[tag_id])

def is_engagement(cmd):
    if cmd and cmd['action'] in ["ATTACK", "ATTACK_SPECIAL", "GROUND_SPECIAL", "GROUND"]:
        return True
    return False

def process_splits(game_stats, trades, splits, players_idx):
    # Add trades and splits to game_stats
    for team_index, team_data in game_stats['header']['teams'].items():
        ((diffs, trade), units) = trades[team_index]
        team_data['trade'] = []
        for tag_id, unit in units.items():
            team_data['trade'].append({
                'name': mesh2trades.unit_name(unit, count=1),
                'count': unit['count'],
                'cost': unit['cost'],
                'class': mesh2trades.unit_class_name(unit),
            })

        if splits:
            split = splits[team_index]
            team_data['trade_value'] = split['total']
            for player_index in sorted(split['allocation'].keys()):
                player_id = players_idx[player_index]
                player_data = team_data['players'][player_id]
                player_data['unit_allocation'] = {
                    'cost': 0,
                    'units': [],
                }
                for tag_id, player_markers in split['allocation'][player_index].items():
                    player_data['unit_allocation']['cost'] += (
                        units[tag_id]['cost'] * len(player_markers)
                    )
                    unit_name = mesh2trades.unit_name(units[tag_id], count=1)
                    player_data['unit_allocation']['units'].append({
                        'name': unit_name,
                        'count': len(player_markers),
                        'cost': units[tag_id]['cost'],
                        'class': mesh2trades.unit_class_name(unit),
                    })
                player_data['unit_allocation']['percent'] = round(
                    100 * player_data['unit_allocation']['cost'] / split['total']
                )

def process_medal(medals, player_stats, stat_name, player_val):
    # Medal winners needs to have made at least 10 engagements in a game
    if player_stats['actions_engage'] > 10:
        if player_stats[stat_name] > medals[stat_name][0]:
            medals[stat_name] = (player_stats[stat_name], [player_val])
        elif player_stats[stat_name] == medals[stat_name][0]:
            medals[stat_name][1].append(player_val)

def process_counters(game_stats, players, counters, self_heal_kill_dmg):
    # Add command counts to game_stats
    # calculate dmg/action, effectiveness, dominance, etc
    # chat
    # self_heal_kill_dmg
    # medals
    # winner
    total_dmg_action = None
    total_dmg_action_engage = None
    total_dmg_cost = None
    overall_stats = game_stats['header']['game']['stats']
    overall_stats['actions'] = counters['command']['overall']
    overall_stats['actions_engage'] = counters['engage']['overall']
    overall_stats['chat'] = counters['chat']['overall']
    overall_stats['self_heal_kill_dmg'] = 0
    overall_value = 0

    # Prefill self_heal_kill_dmg stats before we calculate dmg ratios
    # Also collect overall trade values for dmg_cost index
    for team_index, stat_team in game_stats['header']['teams'].items():
        team_stats = stat_team['stats']
        team_stats['self_heal_kill_dmg'] = 0
        overall_value += stat_team.get('trade_value', 0)
        for player_id, stat_player in stat_team['players'].items():
            player_self_heal_kill_dmg = self_heal_kill_dmg[player_id].total()
            stat_player['stats']['self_heal_kill_dmg'] = player_self_heal_kill_dmg
            team_stats['self_heal_kill_dmg'] += player_self_heal_kill_dmg
            overall_stats['self_heal_kill_dmg'] += player_self_heal_kill_dmg

    if 'dmg_out' in overall_stats:
        # Adjust for self_heal_kill_dmg
        # TODO maybe restrict this to the first minute of the game
        # to avoid rewarding accidental later game thrall kills???
        # if so, check team and player adjustments too
        if overall_stats['self_heal_kill_dmg']:
            total_dmg_out_adjusted = overall_stats['dmg_out'] + overall_stats['self_heal_kill_dmg']
            overall_stats['dmg_out_adjusted'] = True
            overall_stats['dmg_out_orig'] = overall_stats['dmg_out']
            overall_stats['dmg_out'] = total_dmg_out_adjusted

        total_dmg_action = (
            overall_stats['dmg_out'] / max(1, overall_stats['actions'])
        )
        total_dmg_action_engage = (
            overall_stats['dmg_out'] / max(1, overall_stats['actions_engage'])
        )
        total_dmg_cost = (
            overall_stats['dmg_out'] / max(1, overall_value)
        )
        overall_stats['dmg_action'] = round(total_dmg_action, 3)
        overall_stats['dmg_action_engage'] = round(total_dmg_action_engage, 3)
        overall_stats['dmg_cost'] = round(total_dmg_cost, 2)

    medals = {
        'dmg_out': (0, []),
        'actions': (0, []),
        'actions_engage': (0, []),
        'dmg_action_ratio_engage': (0, []),
        'dmg_cost_ratio': (0, []),
    }

    for team_index, stat_team in game_stats['header']['teams'].items():
        team_stats = stat_team['stats']
        team_stats['chat'] = counters['chat']['team'][team_index]
        team_stats['actions'] = counters['command']['team'][team_index]
        team_stats['actions_engage'] = counters['engage']['team'][team_index]

        team_dmg_action = None
        team_dmg_cost = None
        if 'dmg_out' in team_stats:
            # Adjust for self_heal_kill_dmg
            if team_stats['self_heal_kill_dmg']:
                team_dmg_out_adjusted = team_stats['dmg_out'] + team_stats['self_heal_kill_dmg']
                team_stats['dmg_out_adjusted'] = True
                team_stats['dmg_out_orig'] = team_stats['dmg_out']
                team_stats['dmg_out'] = team_dmg_out_adjusted

            if trade_value := stat_team.get('trade_value'):
                team_dmg_cost = team_stats['dmg_out'] / max(1, trade_value)
                team_stats['dmg_cost'] = round(team_dmg_cost, 2)
                if total_dmg_cost is not None:
                    team_stats['dmg_cost_ratio'] = round(team_dmg_cost / total_dmg_cost, 2)
            team_dmg_action = (
                team_stats['dmg_out'] / max(1, team_stats['actions'])
            )
            team_dmg_action_engage = (
                team_stats['dmg_out'] / max(1, team_stats['actions_engage'])
            )
            team_stats['dmg_action'] = round(team_dmg_action, 3)
            team_stats['dmg_action_engage'] = round(team_dmg_action_engage, 3)
            # Team effectiveness (vs overall) (dominance)
            if total_dmg_action is not None:
                team_stats['dmg_action_ratio'] = round(team_dmg_action / total_dmg_action, 2)
                team_stats['dmg_action_ratio_engage'] = round(team_dmg_action_engage / total_dmg_action_engage, 2)

        for player_id, stat_player in stat_team['players'].items():
            player = players[player_id]
            player_val = (player_id, player)
            player_stats = stat_player['stats']
            player_stats['chat'] = counters['chat']['player'][player_id]
            player_stats['actions'] = counters['command']['player'][player_id]
            player_stats['actions_engage'] = counters['engage']['player'][player_id]

            if player_id in self_heal_kill_dmg:
                player_stats['self_heal_kill_dmg'] = self_heal_kill_dmg[player_id].total()

            # actions_engage medal
            process_medal(medals, player_stats, 'actions', player_val)
            process_medal(medals, player_stats, 'actions_engage', player_val)

            if 'dmg_out' in player_stats:
                # Adjust for self_heal_kill_dmg
                if player_self_heal_kill_dmg := player_stats.get('self_heal_kill_dmg', 0):
                    dmg_out_adjusted = player_stats['dmg_out'] + player_self_heal_kill_dmg
                    player_stats['dmg_out_adjusted'] = True
                    player_stats['dmg_out_orig'] = player_stats['dmg_out']
                    player_stats['dmg_out'] = dmg_out_adjusted

                # dmg_out medal
                process_medal(medals, player_stats, 'dmg_out', player_val)

                if 'unit_allocation' in stat_team['players'][player_id]:
                    player_cost = stat_team['players'][player_id]['unit_allocation']['cost']
                    if player_cost:
                        player_dmg_cost = player_stats['dmg_out'] / max(1, player_cost)
                        player_stats['dmg_cost'] = round(player_dmg_cost, 2)
                        if total_dmg_cost is not None:
                            player_stats['dmg_cost_ratio'] = round(player_dmg_cost / total_dmg_cost, 2)
                            # dmg_cost_ratio medal
                            process_medal(medals, player_stats, 'dmg_cost_ratio', player_val)
                        if team_dmg_cost is not None:
                            player_stats['dmg_cost_ratio_team'] = round(player_dmg_cost / team_dmg_cost, 2)
                player_dmg_action = (
                    player_stats['dmg_out'] / max(1, player_stats['actions'])
                )
                player_dmg_action_engage = (
                    player_stats['dmg_out'] / max(1, player_stats['actions_engage'])
                )
                player_stats['dmg_action'] = round(player_dmg_action, 3)
                player_stats['dmg_action_engage'] = round(player_dmg_action_engage, 3)
                if total_dmg_action is not None:
                    # Effectiveness (vs overall)
                    player_stats['dmg_action_ratio'] = round(player_dmg_action / total_dmg_action, 2)
                    player_stats['dmg_action_ratio_engage'] = round(player_dmg_action_engage / total_dmg_action_engage, 2)
                    # dmg_action_ratio_engage medal
                    process_medal(medals, player_stats, 'dmg_action_ratio_engage', player_val)
                if team_dmg_action is not None:
                    # Effectiveness (vs team)
                    player_stats['dmg_action_ratio_team'] = round(player_dmg_action / team_dmg_action, 2)

    for medal_stat, (value, medal_winners) in medals.items():
        for (player_id, player) in medal_winners:
            game_stats['header']['teams'][player.team_index]['players'][player_id]['medals'].append(medal_stat)


def parse_command_monsters(data, monsters, computer_markers, player=None):
    command_monsters = {}
    (monster_count,) = struct.unpack('>h', data[:2])
    end = 2 + (monster_count * 2)
    monster_ids = codec.list_pack('monster_ids', monster_count, '>h')(data[2:end])
    for monster_id in monster_ids:
        if monster_id < 0:
            # Happens for e.g. frenzied myrks
            # Their id gets reset to INT16_MIN -32768 and then incremented
            if 'custom' not in command_monsters:
                command_monsters['custom'] = {}
            if 'Frenzied' not in command_monsters['custom']:
                command_monsters['custom']['Frenzied'] = 0
            command_monsters['custom']['Frenzied'] += 1
        elif player:
            if monster_id in monsters[player.team_index]:
                tag_id = monsters[player.team_index][monster_id]['tag']
                if tag_id not in command_monsters:
                    command_monsters[tag_id] = 0
                command_monsters[tag_id] += 1
            else:
                print(f'! {monster_id} missing from team {player.team_index} monsters {data.hex()}')
                if 'invalid' not in command_monsters:
                    command_monsters['invalid'] = []
                command_monsters['invalid'].append(monster_id)
        else:
            found = False
            for team_index, team_monsters in monsters.items():
                if monster_id in team_monsters:
                    found = True
                    tag_id = team_monsters[monster_id]['tag']
                    target_player = team_monsters[monster_id]['player_id']
                    if target_player not in command_monsters:
                        command_monsters[target_player] = {}
                    if tag_id not in command_monsters[target_player]:
                        command_monsters[target_player][tag_id] = 0
                    command_monsters[target_player][tag_id] += 1
            if not found:
                if monster_id in computer_markers:
                    tag_id = computer_markers[monster_id]
                    if 'ambient' not in command_monsters:
                        command_monsters['ambient'] = {}
                    if tag_id not in command_monsters['ambient']:
                        command_monsters['ambient'][tag_id] = 0
                    command_monsters['ambient'][tag_id] += 1
                else:
                    print(f'! {monster_id} missing from all team monsters and computers {data.hex()}')
                    if 'invalid' not in command_monsters:
                        command_monsters['invalid'] = []
                    command_monsters['invalid'].append(monster_id)

    return (command_monsters, end)

def log_command(
    players, player_id, monsters, computer_markers, computer_monsters, trades,
    command_header, command_data, self_heal_kill_dmg, planning_ticks=0
):
    player = players[player_id]
    action = command_header.verb.name
    extra_data = {}
    command_monsters = {}
    target_monsters = {}
    match command_header.verb:
        case Commands.GENERAL:
            (general_flags, general_type) = struct.unpack('>h h', command_data[:4])
            action = GeneralCommands(general_type).name
            if action == 'TAUNT':
                return
            (command_monsters, _offset) = parse_command_monsters(command_data[4:], monsters, computer_markers, player)
        case Commands.TARGET:
            (target_flags,) = struct.unpack('>h', command_data[:2])
            target_flags = TargetFlags(target_flags)
            if TargetFlags.SPECIAL_ABILITY in target_flags:
                action = 'ATTACK_SPECIAL'
            # elif TargetFlags.ATTACK_INDIVIDUAL in target_flags:
            #     action = 'ATTACK_ONE'
            else:
                action = 'ATTACK'
            (command_monsters, offset) = parse_command_monsters(command_data[2:], monsters, computer_markers, player)
            (target_monsters, _offset2) = parse_command_monsters(command_data[offset+2:], monsters, computer_markers)
        case Commands.ATTACK_LOCATION:
            (attack_location_flags, x, y, z) = struct.unpack('>h 2x L L L', command_data[:16])
            attack_location_flags = AttackLocationFlags(attack_location_flags)
            (command_monsters, _offset) = parse_command_monsters(command_data[16:], monsters, computer_markers, player)
            if AttackLocationFlags.SPECIAL_ABILITY in attack_location_flags:
                action = 'GROUND_SPECIAL'
            else:
                action = 'GROUND'
        case Commands.PICK_UP:
            (pickup_flags, object_idx, object_id) = struct.unpack('>h 2x H H', command_data[:8])
            (command_monsters, _offset) = parse_command_monsters(command_data[8:], monsters, computer_markers, player)
        case Commands.ROTATION:
            action = 'MOVEMENT'
    if len(command_monsters):
        (trade_info, units) = trades[player.team_index]
        expanded_monsters = {}
        if 'invalid' in command_monsters:
            expanded_monsters['invalid'] = command_monsters['invalid']
            del command_monsters['invalid']
        if 'custom' in command_monsters:
            for custom_name, count in command_monsters['custom'].items():
                expanded_monsters[custom_name] = count
            del command_monsters['custom']
        for tag_id, count in command_monsters.items():
            unit = units[tag_id]
            if action == 'ATTACK_SPECIAL' and unit['special_heals']:
                action = 'HEAL'
            monster_name = mesh2trades.unit_name(unit, 1)
            expanded_monsters[monster_name] = count
        extra_data['monsters'] = expanded_monsters
    if len(target_monsters):
        expanded_target_monsters = {}
        if 'invalid' in target_monsters:
            expanded_target_monsters['invalid'] = target_monsters['invalid']
            del target_monsters['invalid']
        if 'custom' in target_monsters:
            if 'custom' not in expanded_target_monsters:
                expanded_target_monsters['custom'] = {}
            for k, v in target_monsters['custom'].items():
                expanded_target_monsters['custom'][k] = v
            del target_monsters['custom']
        if 'ambient' in target_monsters:
            if 'custom' not in expanded_target_monsters:
                expanded_target_monsters['custom'] = {}
            for tag_id, count in target_monsters['ambient'].items():
                expanded_target_monsters['custom'][
                    mesh2trades.unit_name(computer_monsters[tag_id], 1)
                ] = count
            del target_monsters['ambient']
        for target_player_id, target_player_monsters in target_monsters.items():
            ((diffs, trade), units) = trades[players[target_player_id].team_index]

            expanded_target_monsters[target_player_id] = {}
            for tag_id, count in target_player_monsters.items():
                target_unit = units[tag_id]
                if (
                    action == 'HEAL' and
                    target_unit['heal_kills'] and
                    target_player_id == player_id
                ):
                    self_heal_kill_dmg[player_id][tag_id] += count * target_unit['cost']
                    extra_data['self_heal_kill'] = True
                expanded_target_monsters[target_player_id][
                    mesh2trades.unit_name(target_unit, 1)
                ] = count
        extra_data['targets'] = expanded_target_monsters
    return {
        'time': command_header.time - planning_ticks,
        'player': player_id,
        'action': action,
    } | extra_data

def print_trades(teams_idx, trades):
    for team_index, cap_id in enumerate(teams_idx):
        if cap_id is not None:
            ((diffs, trade), units) = trades[team_index]
            print('\n'.join(trade))

def get_splits(monsters, trades):
    splits = {}
    for team_index, team_monsters in monsters.items():
        (trade_info, units) = trades[team_index]
        team_allocation = {}
        total_value = 0
        for marker_id, marker in team_monsters.items():
            tag_id = marker['tag']
            player_monsters = team_allocation.get(marker['player_index'], {})
            player_markers = player_monsters.get(tag_id, [])
            player_markers.append(marker_id)
            player_monsters[tag_id] = player_markers
            team_allocation[marker['player_index']] = player_monsters
            total_value += units[tag_id]['cost']

        splits[team_index] = {'total': total_value, 'allocation': team_allocation}
    return splits

def print_team_split(trade, cap, team_split, players, players_idx):
    ((diffs, trade), units) = trade
    print(
        f'{player_headers.colors(cap)[0]} '
        f'{utils.strip_format(cap.appearance.team_name)}\n'
    )
    print('\n'.join(trade))
    print('Unit Splits at end of Planning Time\n')
    for player_index in sorted(team_split['allocation'].keys()):
        player_value = 0
        player_monsters = team_split['allocation'][player_index]
        marker_list = []
        for tag_id, player_markers in player_monsters.items():
            player_value += (units[tag_id]['cost'] * len(player_markers))
            unit_name = mesh2trades.unit_name(units[tag_id], count=len(player_markers))
            marker_list.append(f'{len(player_markers)} {unit_name}')
        player = players[players_idx[player_index]]
        print(
            f'{player_headers.colors(cap)[0]}'
            f'{player_headers.colors(player)[0]} '
            f'{"*" if player.team_captain_identifier == player.unique_identifier else " "} '
            f'{player_name(player)[:12]:<12} '
            f'{round(100*player_value/team_split['total']):>2}% | '
            f'{" / ".join(marker_list)}'
        )
    print('\n---\n')

def print_splits(players, players_idx, teams_idx, trades, splits):
    if not splits:
        return
    for team_index, team_split in splits.items():
        print_team_split(
            trades[team_index], players[teams_idx[team_index]], team_split, players, players_idx
        )

def print_combined_stats(reco_header, players, players_idx, teams, teams_idx, game_stats):
    print('Stats\n')

    # Ordered by team
    for team_index, team_data in game_stats['header']['teams'].items():
        cap_id = teams_idx[team_index]
        cap = players[cap_id]
        place_str = f'Place: {team_data['place']}) ' if 'place' in team_data else ''
        print(
            f'{2*player_headers.colors(cap)[0]} '
            f'{place_str}'
            f'{utils.strip_format(cap.appearance.team_name)}'
        )
        team_dmg_action = None
        ts = team_data['stats']
        dominance = ''
        if 'dmg_action_ratio' in ts:
            dominance = f'Dominance:     {ts['dmg_action_ratio']:6.2f} '
        team_actions = ''
        if 'actions' in ts:
            team_actions = f'Actions: {ts['actions']:>5}/{ts.get('actions_engage', 0):>5} '
        team_dmg_action = ts.get('dmg_action')
        print(
            f'{2*player_headers.colors(cap)[0]} '
            f'= '
            f'Team Stats === | '
            f'{team_actions}'
            f'{format_stats(ts, team_dmg_action)} '
            f'{dominance}'
        )
        for player_id, player_data in team_data['players'].items():
            player = players[player_id]
            player_stats = ''
            # Players can have missing stats on the metaserver
            ps = player_data['stats']
            effectiveness = ''
            if 'dmg_action_ratio_engage' in ps:
                effectiveness = f'Effectiveness: {ps['dmg_action_ratio_engage']:6.2f}'
            medals = ''
            if medal_count := len(player_data['medals']):
                medals = f' {medal_count * "🎖️"}'
            player_stats = (
                f'{format_stats(ps, ps.get('dmg_action'))} '
                f'{effectiveness}{medals}'
            )
            print(
                f'{player_headers.colors(cap)[0]}'
                f'{player_headers.colors(player)[0]} '
                f'{"*" if player.team_captain_identifier == player.unique_identifier else " "} '
                f'{player_name(player)[:12]:<14} | '
                f'Actions: {ps.get('actions', 0):>5}/{ps.get('actions_engage', 0):>5} '
                f'{player_stats}'
            )
        print('\n---\n')

def format_stats(stats, dmg_action):
    if 'dmg_out' not in stats:
        return ''
    dmg_action_val = ''
    if dmg_action is not None:
        dmg_action_val = f' DMG/Action: {dmg_action:6.3f}'
    return (
        f'Kills: {stats['kills']:>3} '
        f'Losses: {stats['losses']:>3} '
        f'DMG: {stats['dmg_out']:>4} '
        f'DMG taken: {stats['dmg_in']:>4} '
        f'DMG ratio: {stats['dmg_ratio']:5.2f} '
        f'K/L: {stats['kill_loss_ratio']:5.2f}'
        f'{dmg_action_val}'
    )

def print_chat(chat_lines, players):
    print('Chat\n')
    for (pt, chat_time, player, chat_flags, chat_message) in chat_lines:
        whisper = '[whisper] ' if ChatFlags.PRIVATE in ChatFlags(chat_flags) else ''
        cap = players[player.team_captain_identifier]
        print(
            f'{tick_to_time(pt, chat_time)}: '
            f'{player_headers.colors(cap)[0]}'
            f'{player_headers.colors(player)[0]} '
            f'{player_name(player)[:12]:<12} | '
            f'{whisper}'
            f'{utils.ansi_format(chat_message)}'
        )
    print('\n---\n')

def sorted_markers(markers, game_param):
    return sorted(markers.values(), key=lambda m: (game_param.difficulty_level < m['min_difficulty'], mesh_tag.MarkerFlag.IS_INVISIBLE in m['flags']))

def time_vars(command_time, game_param):
    planning_ticks = game_param.pregame_time_limit
    total_ticks = game_param.time_limit + planning_ticks
    if command_time <= planning_ticks:
        pt = True
        remaining = planning_ticks - command_time
    else:
        pt = False
        remaining = total_ticks - command_time

    return (pt, remaining)

def pt_over(prev_command_time, command_time, game_param):
    if not prev_command_time:
        return False
    # Add 2s, late adjusts can come in slightly after pt is over
    # Add further 30s to account for late splits
    planning_ticks = game_param.pregame_time_limit + 60 + 900
    return prev_command_time <= planning_ticks and command_time > planning_ticks

def tick_to_time(pt, ticks):
    seconds = ticks / 30
    mins = round(seconds // 60)
    secs = round(seconds % 60)
    return f'{"PT " if pt else "   "}{mins:02}m{secs:02}s'
