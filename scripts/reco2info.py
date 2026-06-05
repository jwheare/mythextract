#!/usr/bin/env python3
import os
import struct
import sys

import reco_tag
import mesh_tag
import game_headers

DEBUG = (os.environ.get('DEBUG') == '1')


# find m2/recordings/ -type f -depth 1 -print0 | while read -d $'\0' r; do basename "$r"; ./scripts/reco2info.py m2 "$r"; done

def main(game_directory, reco_file, metaserver, metaserver_game):
    """
    Show info stored in recording file
    """

    try:
        metaserver_stats = reco_tag.fetch_metaserver_stats(reco_file, metaserver, metaserver_game)
        (
            reco_header, players, players_idx, monsters,
            teams, teams_idx, alliances, dropped_players,
            plugins, mesh_header, level_name, game_time, game_type_choice, difficulty,
            overhead_map_data, cmap_export, chat_lines, movement_data, trades, splits, game_stats
        ) = reco_tag.parse_reco_file(
            game_directory, reco_file,
            metaserver_stats
        )

        reco_tag.print_metaserver_info(teams_idx, teams, players, game_stats)
        info = mesh_tag.get_game_info(mesh_header, level_name, game_type_choice, difficulty, game_time)
        print(info)

        print()
        game_headers.print_plugins(plugins, True)
        print()

        reco_tag.print_teams(teams, players, players_idx, alliances, dropped_players)

        print('\nTeams\n')

        reco_tag.print_splits(players, players_idx, teams_idx, trades, splits)

        reco_tag.print_chat(chat_lines, players)

        reco_tag.print_combined_stats(
            reco_header, players, players_idx, teams, teams_idx, alliances, dropped_players, game_stats
        )

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> <reco_file> [<metaserver> <metaserver_game>]")
        sys.exit(1)
    
    game_directory = sys.argv[1]
    reco_file = sys.argv[2]
    metaserver = None
    metaserver_game = None
    if len(sys.argv) == 5:
        metaserver = sys.argv[3]
        metaserver_game = sys.argv[4]

    try:
        main(game_directory, reco_file, metaserver, metaserver_game)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
