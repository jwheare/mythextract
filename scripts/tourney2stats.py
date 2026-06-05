#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import shutil
import sys
import traceback

import reco_tag
import myth_collection
import tag2png
import mesh_tag
# import utils

DEBUG = (os.environ.get('DEBUG') == '1')

MISSING_CAPS = {}

def cap2team(tourney_slug, round_id, round_slug, game_num, cap_id):
    teams = {
        'gos-mwc2013': {
            71: 'tmnt', # giant killer general
            142: 'agents', # wwo
            1086: 'dr' if (round_id == 268) else 'wtc', # thor
            134: 'dr' if (round_id == 230) else 'wtc', # gekko
            192: 'tmns', # zak
            58: 'tmns', # tirri
            263: 'agents', # limp
            222: 'zomg', # noblesteed
            1154: 'zomg', # highwired
            215: 'blades' if (round_id == 272) else 'deer', # drunken
            501: 'blades', # codex
            635: 'tcox', # kryptos
            64: 'ulms' if (round_id == 271) else 'dr', # funk
            172: 'dr' if (round_id == 230) else 'ulms', # samthebutcher
            517: 'ulms', # killerking
            1093: 'tmns', # bebop
            1162: 'tmns', # gateofstormtroopers
            123: 'deer', # empy
            8853: 'agents', # wwo
            21712: 'deer', # ponder
            1840: 'deer', # empy
            491: 'ulms', # spookybmf
            79: 'ulms', # father xmas
            1157: 'blades', # bax
            217: 'ulms', # arsenal
            431: 'tcox', # gamer
            65: 'dr', # ratking
            154: 'agents', # cruniac
            85: 'dr', # punkuser
            214: 'dr' if (round_id == 268) else 'blades', # pallidice
            75: 'tmns', # adrenaline
            106: 'blades', # cremisi
            228: 'tmnt', # asmodian
        },
        'gos-mwc2014': {
            71: 'bros', # giant killer general
            228: 'fotb', # asmodian
            142: 'gents', # wwo
            1670: 'udogs', # shotgun
            517: 'ulms2' if (round_id == 362 and game_num == 5) else 'ulms', # killerking
            1710: 'gents2' if (round_id == 363 and game_num == 5) else 'gents', # wywrd
            79: 'tea', # father xmas
            1162: 'tea', # gateofstormtroopers
            106: 'ulms', # cremisi
            1211: 'tea', # zaknafiend
            72: 'tea2' if (round_id == 362 and game_num == 5) else 'tea', # flatline
            215: 'ulms', # drunken_deer
            193: 'udogs2' if (round_id == 363 and game_num == 5) else 'udogs', # chohan
            74: 'gents', # paris
            635: 'tea', # kryptos
            225: 'ulms', # homer
            154: 'udogs' if (round_id == 360) else 'bros', # cruniac 
            75: 'gents', # adrenaline
            78: 'fotb', # arzenic
            217: 'tea', # arsenal
            1729: 'udogs', # iaindf
            64: 'gents', # funk
            65: 'gents', # ratking
            1455: 'udogs', # heyhoeletsgo
        },
        'gos-mwc2015': {
            71: 'tmnt2', # giant killer general
            65: 'mom', # ratking
            84: 'ncr', # ska
            263: 'ncr', # limp
            241: 'deer', # masterchief
            74: 'ncr', # paris
            228: 'rabble' if (round_id == 386) else 'tmnt2', # asmodian
            2015: 'owls', # lordscaryowl
            215: 'deer', # drunken
            278: 'ncr', # samuel
            1951: 'ncr', # garrick
        },
        'gos-mwc2016': {
            263: 'twf', # limp
            65: 'syn', # ratking
            192: 'twf', # zak
            2015: 'gom', # lordscaryowl

            74: 'tinh' if (round_id in [462, 486]) else 'syn', # paris
            75: 'tinh', # adrenaline
            142: 'boom', # wwo
            1814: 'por', # alfi
            63: 'por', # switch
            60: 'por', # hmp
            1296: 'ageha', # terrythekid
            1623: 'ageha', # ging
            228: 'boom', # asmodian
            11216: 'noobs', # phos
            77: 'noobs', # dantski
            2300: 'gom', # coca-cola
            1298: 'ageha', # ape
            52394: 'gom', # lordscaryowl
            134: 'boom', # gekko
            1086: 'gom', # thor
            635: 'gom', # kryptos
            2209: 'noobs', # k-size
            225: 'boom', # homer
            93: 'boom', # east wind
        },
        'gos-mwc2017': {
            70646: 'da', # ratking
            71: 'rofl', # giant killer general
            70630: 'lom', # akira
            70629: 'bers', # vasazel
            47860: 'bers', # garnish
            70721: 'da', # adrenaline
            106: 'lom', # cremisi
            74: 'da', # paris
            2015: 'lom', # lordscaryowl
            154: 'rofl', # cruniac
        },
        'gos-mwc2018': {
            71199: 'np', # rabican
            71: 'tmnt', # gkg
            228: 'np', # asmodian
            58: 'np', # tirri
            70646: 'sdm', # ratking
            70721: '7l', # adrenaline
            70787: 'tgp', # drunken
            70718: 'tcl', # limp
            1228: 'lh', # seeker
            70629: 'tgp', # vasazel
            47860: 'bkbk', # garnish
            1086: 'lh', # thor
            2015: 'sdm', # lordscaryowl
            71165: 'lh', # tramist
            74: '7l', # paris
            71175: 'lh', # honkey
        },
        'gos-mwc2019': {
            1407: 'sb', # walter wight
            70646: 'ftn', # ratking
            2015: 'nc' if (round_id in [725, 733]) else 'ftn', # lordscaryowl,
            70629: 'moc', # vasazel
            71442: 'nc', # wwo
            70737: 'moc', # renwood
            70704: 'nc', # homer
            70721: 'nc', # adrenaline
            71258: 'sb', # spy
            1086: 'moc', # thor
            70666: 'nc', # wwo
            11216: 'moc', # phos
            1725: 'moc', # jahral
        },
        'gos-mwc2020': {
            2015: "faf" if (round_id in [764, 753, 752]) else 'mm', # lordscaryowl
            70718: 'hots', # texas pete/lb/professor
            74: 'ba', # paris
            1228: 'gagt', # big chaz / seeker
            71677: 'mm', # blade
            71722: 'faf', # ramirez
            1407: 'sb', # walter wight
            70787: 'deer', # drunken
            47860: 'ag', # garnish
            154: 'sb', # cruniac
            71441: 'sb', # empy
            70646: 'gagt', # ratking
            262: 'mm', # spoon
            70629: 'deer', # vasazel
            71180: 'faf', # sin
            228: 'hots', # asmodian
            60: 'faf', # hmp
            71175: 'faf', # honkey
            70630: 'gagt', # akira
            71705: 'gagt', # al capone
        },
        'gos-mwc2021': {
            70646: 'b4', # ratking
            2015: 'kotet', # lordscaryowl
            70721: 'sm', # adrenaline
            71158: 'sm', # karma
            70787: 'ic', # drunken
            1407: 'ic', # walter wight
            70704: 'sm', # homer
            71223: 'dc', # general pepper
            218: 'kotet', # shad
            70698: 'ag', # jeoku
            1725: 'ag', # jahral
            74: "ag" if (round_id == 868) else "b4", # paris
            71258: 'ic', # spy
            228: 'b4', # asmodian
        },
        'gos-mwc2022': {
            228: 'sm', # asmodian
            70704: 'rsc', # homer
            70646: 'sm', # ratking
            71: 'mit', # gkg
            70698: 'ag', # jeoku
            71158: 'rsc', # karma
            2015: 'mit' # lordscaryowl
        },
        'gos-mwc2023': {
            2015: "mitt", # lordscaryowl
            70704: "rsc", # homer
            70646: "sm", # ratking
            228: "sm", # asmodian
            70643: "tjn", # father xmas
            70787: "tjn", # drunken
            47860: "ag", # garnish
            71322: "tjn", # overdose
            1407: "tjn", # walter wight
            11216: "sm", # phos
            72479: "rsc", # akira
            218: "mitt", # shad
            70689: "rsc", # arzenic
        },
        'gos-mwc2024': {
            70858: "tmf", # weiss
            71199: "bmlm", # rabican
            71276: "tl", # arsenal
            47860: "ag", # garnish
            71333: "tl", # ribfeast
            70704: "bmlm", # homer
            71739: "man", # wwo
            72479: "bmlm", # akira
            72909: "tl", # groove
            71184: "bmlm", # gheng bender
            74: "miit" if (round_id == 1003 and game_num == 8) else "miit", # paris
            71: "miit2" if (round_id == 1003 and game_num == 8) else "miit", # gkg
            2015: "miit3" if (round_id == 1003 and game_num == 8) else "miit", # lordscaryowl
            70646: "man" if (round_id == 1003 and game_num == 8) else "man", # ratking
            228: "man2" if (round_id == 1003 and game_num == 8) else "man", # asmodian
            70721: "man3" if (round_id == 1003 and game_num == 8) else "man", # adrenaline
        },
        '7-mwc25': {
            11: "spy kids",
            26: "ag",
            31: "d&t",
            34: "spy kids",
            38: "tmf",
            41: "mit",
            44: "z snake",
            47: "spy kids",
            51: "z snake",
            52: "spy kids",
            54: "ag",
            59: "spy kids",
            68: "spy kids",
            96: "tmf",
            150: "ag",
            210: "tmf",
            252: "tmf",
            283: "pk",
            338: "tmf",
            342: "pk"
        },
        '9-smo25': {
            31: 'homer' if round_id == 77 else 'asmo', # asmodian
            53: 'homer', # homer
            11: 'akira', # ephemeral
            103: 'dantski', # dantski
            41: 'dantski', # lordscaryowl
            51: 'akira', # akira
            52: 'homer', # karma
            283: 'akira', # drunken
            213: 'homer', # detriment
            13: 'akira', # giant killer general
        },
        '13-mwc26': {
            96: "tmf2" if (round_id == 121 and game_num == 5) else "tmf", # sanglaine
            212: "ag", # swatacular
            34: "4c", # spy
            103: "4c2" if (round_id == 107 and game_num == 3) else "4c", # dantski
            13: "v3", # gkg
            51: "cum2" if (round_id == 122 and game_num == 5) else "cum", # akira
            59: "4c", # overdose
            86: "ti", # ribfeast
            1657: "ti", # ymir
            28: "ag", # bran
            327: "cum2" if (round_id == 107 and game_num == 3) else "cum", # east wind (noolook)
            31: "v32" if (round_id == 122 and game_num == 5) else "v3", # asmodian
            65: "cum", # clank
            53: "cum", # yamnti
            52: "4c", # karma
            25: "4c", # gekko
            1815: 'ti', # pompous bastard
            306: 'ti', # terminal cheese
            152: 'ti', # meerkat
            338: "tmf", # gholsbane
            47: "4c2" if (round_id == 121 and game_num == 5) else "4c", # walter wight
        },
    }
    team_slug = teams.get(tourney_slug, {}).get(int(cap_id))
    if not team_slug:
        team_slug = MISSING_CAPS.get(tourney_slug, {}).get(int(cap_id), (None, None))[0]
    return team_slug

FORFEIT_WINNERS = {
    '7-mwc25': {
        43: ['tmf', 5],
        48: ['ag', 5],
    }
}
SUDDEN_DEATH_WINNERS = {
    'gos-mwc2018': {
        693: ['tmnt', [7, 8]]
    }
}

def prompt_missing_cap(tourney_slug, round_info, team_data, game_stats):
    stats_game = game_stats['header']['game']
    print('\nMissing cap', tourney_slug, stats_game.get('metaserver_url'))
    print()
    for team_index, team in game_stats['header']['teams'].items():
        print(team['name'])
        for player in team['players'].values():
            print(
                f't={team_index}',
                f"p={player['metaserver_player']:>6}",
                '*' if player['captain'] else ' ',
                player['name']
            )
    response = ''
    while response not in ['1', '2']:
        print()
        print(f"1) {round_info['team1']}")
        print(f"2) {round_info['team2']}")
        response = input(
            f"Choose team for: {team_data['captain']}: "
        ).strip().lower()

    input_team = round_info[f'team{response}']
    if tourney_slug not in MISSING_CAPS:
        MISSING_CAPS[tourney_slug] = {}
    MISSING_CAPS[tourney_slug][team_data['captain']['metaserver_player']] = (input_team, team_data['captain']['name'])
    print('MISSING_CAPS', MISSING_CAPS)
    return input_team

def main(tourney_dir, game_directory, output_dir):
    """
    Parse downloaded films from a tournament into stats json
    """

    tourney_path = pathlib.Path(tourney_dir)
    tourney_info_file = tourney_path / 'info.json'
    try:
        with open(tourney_info_file, 'r') as t_info_file:
            tourney_info = json.load(t_info_file)
    except FileNotFoundError:
        print('No tourney info file')
        sys.exit(1)

    tourney_name = tourney_info['name']
    tourney_short_name = tourney_info['short_name']
    tourney_start = tourney_info['start']
    tourney_slug = tourney_info['slug']
    tourney_id = tourney_info['metaserver_tournament']
    metaserver = tourney_info['metaserver']
    print(f"Tournament: [{metaserver}] {tourney_name} ({tourney_id})")
    print(f"Short name: {tourney_short_name}")
    print(f"Start date: {tourney_start}")

    if 'rounds' not in tourney_info:
        print('No round info')
        sys.exit(1)

    if not output_dir:
        base_path = tourney_path.parent.parent
    else:
        base_path = pathlib.Path(output_dir)
    
    tourney_rounds = tourney_info['rounds']
    tourney_info_data = {
        k: v for k, v in tourney_info.items() if k not in ['rounds']
    }

    prompt_text = f"Generate stats for {len(tourney_rounds)}x rounds in: {base_path} ({tourney_path}/...) [Y/n]"
    if prompt(prompt_text):
        # for round_i, round_info in enumerate(reversed(tourney_rounds)):
        for round_i, round_info in enumerate(tourney_rounds):
            winning_teams = None
            # Relies on tourney specific data
            if round_info.get('_processed'):
                winning_teams = {}
                winning_teams[round_info['team1']] = 0
                winning_teams[round_info['team2']] = 0

            round_id = round_info.get('metaserver_round')
            round_slug = round_info['round_slug']
            sd_winner = SUDDEN_DEATH_WINNERS.get(tourney_slug, {}).get(round_id)
            if not len(round_info['games']):
                if winning_teams:
                    forfeit_winner = FORFEIT_WINNERS.get(tourney_slug, {}).get(round_id)
                    if forfeit_winner:
                        winning_teams[forfeit_winner[0]] = forfeit_winner[1]
                        round_info['forfeit'] = (
                            round_info['team1'] if forfeit_winner[0] == round_info['team2'] else round_info['team2']
                        )
            for game_info in round_info['games']:
                game_dir = base_path / game_info['game_path']
                film_name = game_info['film_name']
                reco_file = game_dir / film_name
                game_id = game_info.get('metaserver_game')
                print(
                    f'{(round_i+1):>2}/{len(tourney_rounds)}: round_id={round_id} {round_slug} '
                    f'game {game_info['game_num']} ({game_id}): '
                    f'{game_info["game_path"]}/{film_name} ... ', end='', flush=True
                )
                try:
                    # utils.profileStart()
                    if 'metaserver_stats' in game_info:
                        metaserver_stats = game_info['metaserver_stats']
                        del game_info['metaserver_stats']
                    else:
                        metaserver_stats = reco_tag.fetch_metaserver_stats(
                            reco_file, metaserver, game_id,
                            tourney_id, round_id
                        )
                    parsed_reco = reco_tag.parse_reco_file(
                        game_directory, reco_file,
                        metaserver_stats
                    )
                    # utils.profileEnd()
                    # sys.exit(1)
                except Exception as e:
                    print('\x1b[93mSKIPPED\x1b[0m')
                    print(f"Unexpected error parsing film: {e}")
                    print(traceback.format_exc())
                    prompt("Continue")
                    continue

                if not parsed_reco:
                    print('\x1b[93mSKIPPED\x1b[0m')
                    continue

                (
                    reco_header, players, players_idx, monsters,
                    teams, teams_idx, alliances, dropped_players,
                    plugins, mesh_header, level_name, game_time, game_type_choice, difficulty,
                    overhead_map_data, cmap_export, chat_lines, movement_data, trades, splits, game_stats
                ) = parsed_reco

                print('PARSED... ', end='', flush=True)

                # Add path, tourney, round and film info to game_stats
                stats_game = game_stats['header']['game']
                stats_game['game_num'] = game_info['game_num']
                stats_game['game_path'] = game_info['game_path']
                stats_game['game_slug'] = game_info['game_slug']
                stats_game['film_name'] = game_info['film_name']
                game_stats['header']['tournament'] = tourney_info_data
                game_stats['header']['round'] = round_info

                game_info['time_limit'] = stats_game['time_limit']
                game_info['difficulty'] = stats_game['difficulty']
                game_info['game_name'] = stats_game.get('game_name')
                game_info['game_type_map_slug'] = stats_game['game_type_map_slug']

                for team_index, team_data in game_stats['header']['teams'].items():
                    metaserver_captain = team_data['captain']['metaserver_player']
                    # Relies on tourney specific data
                    team_name = cap2team(
                        tourney_slug, round_id, round_slug, game_info['game_num'], metaserver_captain
                    )
                    if not team_name:
                        team_name = prompt_missing_cap(tourney_slug, round_info, team_data, game_stats)

                winning_team = None
                if stats_game['winning_metaserver_captain']:
                    winning_team = cap2team(
                        tourney_slug, round_id, round_slug, game_info['game_num'], stats_game['winning_metaserver_captain']
                    )
                    if winning_teams:
                        if winning_team not in winning_teams:
                            print(f"\x1b[93mTEAM_NAME_INVALID\x1b[0m({winning_team}) {stats_game['winning_metaserver_captain']} {winning_teams.keys()}")
                            print('SKIPPED')
                            continue
                        winning_teams[winning_team] += 1
                    stats_game['winning_team'] = winning_team
                    game_info['winning_team'] = winning_team

                # Re-index teams header by tourney team slugs
                reindexed = {}
                for team_index, team_data in game_stats['header']['teams'].items():
                    metaserver_captain = team_data['captain']['metaserver_player']
                    # Relies on tourney specific data
                    team_name = cap2team(
                        tourney_slug, round_id, round_slug, game_info['game_num'], metaserver_captain
                    )
                    if team_name not in [round_info['team1'], round_info['team2']]:
                        print(f'\x1b[93mTEAM_NAME_MISMATCH\x1b[0m({team_name})... ', end='', flush=True)

                    if 'alliances' in team_data:
                        team_data['alliances'] = {
                            k: [cap2team(
                                tourney_slug, round_id, round_slug, game_info['game_num'],
                                game_stats['header']['teams'][t_idx]['captain']['metaserver_player']
                            ) for t_idx in l]
                            for k, l in team_data['alliances'].items()
                        }
                        if winning_team in team_data['alliances'].get('mutual', []) and not team_data.get('winner'):
                            team_data['allied_winner'] = True

                    reindexed[team_name] = team_data | {
                        'team_index': team_index
                    }
                game_stats['header']['teams'] = reindexed

                if sd_winner and game_info['game_num'] in sd_winner[1]:
                    stats_game['sudden_death'] = True
                    game_info['sudden_death'] = True

                # Extract overhead map
                overhead_bitmaps = myth_collection.parse_sequence_bitmaps(overhead_map_data)
                if len(overhead_bitmaps):
                    overhead_hash = hashlib.md5(overhead_map_data).hexdigest()[:8]
                    overhead_path = f'img/overheads/overhead-{overhead_hash}.png'
                    overhead_out_path = base_path / overhead_path
                    stats_game['overhead_path'] = overhead_path
                    game_info['overhead_path'] = overhead_path
                    (
                        overhead_name, overhead_width, overhead_height, overhead_rows
                    ) = overhead_bitmaps[0]['bitmaps'][0]
                    old_overhead_path = game_dir / 'overhead.png'
                    if overhead_out_path.is_file():
                        print('OVERHEAD EXISTS... ', end='', flush=True)
                    elif old_overhead_path.is_file():
                        shutil.move(old_overhead_path, overhead_out_path)
                        print('OVERHEAD MOVED... ', end='', flush=True)
                    else:
                        overhead_png = tag2png.make_png(overhead_width, overhead_height, overhead_rows)
                        with open(overhead_out_path, 'wb') as png_file:
                            png_file.write(overhead_png)
                        print('OVERHEAD... ', end='', flush=True)

                # Extract colormap
                if cmap_export:
                    (cmap_data, cmap_hash) = cmap_export
                    cmap_path = f'img/cmaps/cmap-{cmap_hash}.png'
                    cmap_out_path = base_path / cmap_path
                    stats_game['cmap_path'] = cmap_path
                    game_info['cmap_path'] = cmap_path
                    old_cmap_path = game_dir / 'cmap.png'
                    if cmap_out_path.is_file():
                        print('CMAP EXISTS... ', end='', flush=True)
                    elif old_cmap_path.is_file():
                        shutil.move(old_cmap_path, cmap_out_path)
                        print('CMAP MOVED... ', end='', flush=True)
                    else:
                        (cmap_width, cmap_height, cmap_rows) = mesh_tag.assemble_colormap(mesh_header, cmap_data)
                        cmap_png = tag2png.make_png(cmap_width, cmap_height, cmap_rows)
                        with open(cmap_out_path, 'wb') as png_file:
                            png_file.write(cmap_png)
                        print('CMAP... ', end='', flush=True)

                reco_stats_out_path = game_dir / 'stats.json'
                pathlib.Path(reco_stats_out_path.parent).mkdir(parents=True, exist_ok=True)
                with open(reco_stats_out_path, 'w') as reco_stats_out_file:
                    json.dump(game_stats, reco_stats_out_file, separators=(',', ':'))

                print('STATS... ', end='', flush=True)

                # game_info written to stats, now add extra info from
                # game_stats/stats_game into game_info. this gets saved
                # into the round_info and tourney_info dicts which are
                # written out after these loops

                # winning team info
                if 'tie' in stats_game:
                    game_info['tie'] = stats_game['tie']
                if 'host' in stats_game:
                    game_info['host'] = stats_game['host']
                if 'tie_teams' in stats_game:
                    game_info['tie_teams'] = stats_game['tie_teams']

                # teams and players info
                teams_info = {}
                if metaserver:
                    for team_index, team_data in game_stats['header']['teams'].items():
                        # Relies on tourney specific data
                        team_name = cap2team(
                            tourney_slug, round_id, round_slug, game_info['game_num'], team_data['captain']['metaserver_player']
                        )
                        teams_info[team_name] = {
                            tk: tv
                            for tk, tv in team_data.items() if tk in [
                                'name',
                                'stats',
                                'color',
                                'tied_winner',
                                'winner',
                                'allied_winner',
                                'eliminated',
                                'place',
                                'place_tie',
                            ]
                        } | {
                            'captain_name': team_data['captain']['name'],
                            'players': {
                                player_data['metaserver_player']: {
                                    pk: pv
                                    for pk, pv in player_data.items() if pk in [
                                        'name',
                                        'stats',
                                        'color',
                                        'medals',
                                        'captain',
                                    ]
                                }
                                for player_id, player_data in team_data['players'].items()
                            }
                        }
                game_info['teams'] = teams_info

                print('DONE')

            # Relies on tourney specific data
            if winning_teams:
                round_winner = None
                if winning_teams[round_info['team1']] > winning_teams[round_info['team2']]:
                    round_winner = round_info['team1']
                elif winning_teams[round_info['team2']] > winning_teams[round_info['team1']]:
                    round_winner = round_info['team2']
                elif sd_winner:
                    round_winner = sd_winner[0]
                round_info['winning_teams'] = winning_teams
                round_info['round_winner'] = round_winner

            # Write updated round_info to file
            round_info_path = base_path / round_info['round_path']
            round_info_file = round_info_path / 'info.json'

            with open(round_info_file, 'w') as r_info_file:
                json.dump(round_info | {'tournament': tourney_info_data}, r_info_file, separators=(',', ':'))

        print('All stats generated')

        # Write updated tourney_info to file
        with open(tourney_info_file, 'w') as t_info_file:
            json.dump(tourney_info, t_info_file, separators=(',', ':'))

        if len(MISSING_CAPS):
            print('MISSING_CAPS', MISSING_CAPS)

def prompt(text):
    # return True
    response = input(f"{text}: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <tourney_dir> <game_directory> [<output_dir>]")
        sys.exit(1)
    
    tourney_dir = sys.argv[1]
    game_directory = sys.argv[2]
    if len(sys.argv) > 3:
        output_dir = sys.argv[3]
    else:
        output_dir = None
    
    try:
        main(tourney_dir, game_directory, output_dir)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
