import * as Plot from "@observablehq/plot";
import * as d3 from "d3";

const titleHead = document.getElementById('title');
const subtitleHead = document.getElementById('subtitle');
const captionHead = document.getElementById('caption');
const overhead = document.getElementById('overhead');

const tournamentContainer = document.getElementById("tournament");

const roundContainer = document.getElementById("round");

const gameList = document.getElementById("gameList");
const clickGraph = document.getElementById("graph");
const graphFilter = document.getElementById("filter");
const actionLegend = document.getElementById('actionLegend');
const summaryGraph = document.getElementById("summary");
const playerList = document.getElementById("playerList");

let BASE_URL = import.meta.env.BASE_URL;
let PAGE_URL = null;

let TOURNEY_ID = null;
let ROUND_ID = null;
let PLAYER_ID = null;
let TEAM_ID = null;
let GAME_ID = null;
let ROUTE_NAME = null;
let TOURNEY_DATA = null;
let ROUND_MAP = null;
let TEAM_MAP = null;
let PROCESSED_ROUNDS = null;

let ROUND_DATA = null;

let GAME_DATA = null;
let PLAYER_GROUPS = null;
let FILTERED_PLAYER = null;
let UNIT_FILTER = null;

function dce (element, className, textContent) {
  let el = document.createElement(element);
  if (className) {
    el.className = className;
  }
  if (textContent != null) {
    el.textContent = textContent;
  }
  return el;
}

const ROUTES = {
  game: /^tournament\/([^/]+)\/rounds\/([^/]+)\/games\/([^/]+)/,
  round_stats: /^tournament\/([^/]+)\/rounds\/([^/]+)\/stats/,
  player: /^tournament\/([^/]+)\/players\/([^/]+)/,
  team: /^tournament\/([^/]+)\/teams\/([^/]+)/,
  round: /^tournament\/([^/]+)\/rounds\/([^/]+)/,
  tournament_stats: /^tournament\/([^/]+)\/stats/,
  tournament: /^tournament\/([^/]+)/,
  home: /^tournament/,
  info: /^info/,
};

const STAT_TOOLTIPS = {
  'Total\nDmg': "Total Damage Dealt",
  'Total\nBusy': "Total Busyness (Commands Issued)",
  'Total\nAggr.': "Total Aggression (Engagement commands issued)",

  'Median\nDmg': "Median Damage Dealt",
  'Median\nBusy': "Median Busyness (Commands issued)",
  'Median\nAggr.': "Median Aggression (Engagement commands issued)",
  'Median\nAssert': "Median Assertive Index (Dmg / Aggression vs average)",
  'Median\nEffic.': "Median Efficiency Index (Dmg / Unit value held vs average)",
  '🔹 Caps': "Total Times Captained",
  '🎖️ Medals': "Total Medals Earned",
}

routeUrl();

function parseUrl (url) {
  for (let [routeName, route] of Object.entries(ROUTES)) {
    let match = url.slice(BASE_URL.length).match(route);
    if (match) {
      return [routeName, match];
    }
  }
  return false
}

function routeUrl () {
  let newPath = window.location.pathname;
  if (PAGE_URL == newPath) {
    return;
  }

  let parsedUrl = parseUrl(newPath);
  if (!parsedUrl) {
    history.pushState({}, "", `${BASE_URL}tournament`);
    return routeUrl();
  }
  let [routeName, routeMatch] = parsedUrl;

  let hard = false;
  if (PAGE_URL) {
    let oldParsed = parseUrl(PAGE_URL);
    if (!oldParsed || ROUTE_NAME != routeName || TOURNEY_ID != routeMatch[1]) {
      hard = true;
    }
  }

  if (hard) {
    resetPage();
  }

  PAGE_URL = newPath;
  ROUTE_NAME = routeName;
  TOURNEY_ID = routeMatch[1];
  if (ROUTE_NAME == 'player') {
    ROUND_ID = null;
    PLAYER_ID = routeMatch[2];
    TEAM_ID = null;
  } else if (ROUTE_NAME == 'team') {
    ROUND_ID = null;
    PLAYER_ID = null;
    TEAM_ID = decodeURIComponent(routeMatch[2]);
  } else {
    ROUND_ID = routeMatch[2];
    PLAYER_ID = null;
    TEAM_ID = null;
  }
  if (ROUND_ID) {
    GAME_ID = routeMatch[3];
  } else {
    GAME_ID = null;
  }

  if (TOURNEY_ID == '7-mwc25') {
    initMWC25();
  }

  if (GAME_ID) {
    renderGame();
  } else if (ROUND_ID) {
    renderRound();
  } else if (TOURNEY_ID) {
    renderTournament();
  } else if (ROUTE_NAME == 'info') {
    renderInfo();
  } else {
    renderHome();
  }
}

window.addEventListener("popstate", () => {
  routeUrl();
});

function renderInfoTitle () {
  let title = "Myth Stats: Info";
  document.title = title;
}
function renderHomeTitle () {
  let title = "Myth Stats: Tournaments";
  document.title = title;
}
function renderTournamentTitle () {
  let title = `Tournament: ${TOURNEY_DATA.name}`;
  document.title = title;
}
function renderTournamentTeamTitle () {
  let title = `Tournament: ${TOURNEY_DATA.name}`;
  document.title = title;
}
function renderTournamentPlayerTitle () {
  let title = `Tournament: ${TOURNEY_DATA.name}`;
  document.title = title;
}
function renderTournamentStatsTitle () {
  let title = `Tournament: ${TOURNEY_DATA.name}`;
  document.title = title;
}
function renderRoundTitle () {
  let title = `${ROUND_DATA.round_name} / ${ROUND_DATA.tournament.name}`;
  document.title = title;
}
function renderGameTitle () {
  let title = `${GAME_DATA.header.game.game_num}. ${GAME_DATA.header.game.game_type} on ${GAME_DATA.header.game.map_name} / ${GAME_DATA.header.round.round_name} / ${GAME_DATA.header.tournament.name}`;
  document.title = title;
}

function resetPage () {
  document.body.classList.remove('show-info');

  clearTooltips();

  TOURNEY_ID = null;
  TOURNEY_DATA = null;
  ROUND_MAP = null;
  TEAM_MAP = null;
  PROCESSED_ROUNDS = null;

  ROUND_DATA = null;

  GAME_DATA = null;
  PLAYER_GROUPS = null;
  FILTERED_PLAYER = null;
  UNIT_FILTER = null;

  // Only blank out parts that won't be refilled
  subtitleHead.innerHTML = '';
  captionHead.innerHTML = '';
  overhead.innerHTML = '';

  tournamentContainer.innerHTML = '';

  roundContainer.innerHTML = '';

  gameList.innerHTML = '';
  playerList.innerHTML = '';
  summaryGraph.innerHTML = '';
  clickGraph.innerHTML = '';
  graphFilter.innerHTML = '';
  actionLegend.innerHTML = '';
}

function renderInfo () {
  renderInfoTitle();
  renderInfoInfo();
  document.body.classList.add('show-info');
}

function renderHome () {
  renderHomeTitle();
  renderHomeInfo();
  renderHomeTourneys();
}

async function renderTournament() {
  const response = await fetch(`${BASE_URL}tournament/${TOURNEY_ID}/info.json`);
  TOURNEY_DATA = JSON.parse(await response.text());
  window.TOURNEY_DATA = TOURNEY_DATA;

  processTournaments();
  if (ROUTE_NAME == 'tournament_stats') {
    renderTournamentStatsTitle();
    renderTournamentStatsInfo();
    renderTournmamentStats();
  } else if (PLAYER_ID) {
    renderTournamentPlayerTitle();
    renderTournamentPlayerInfo();
    renderTournamentPlayer();
  } else if (TEAM_ID) {
    renderTournamentTeamTitle();
    renderTournamentTeamInfo();
    renderTournamentTeam();
  } else {
    renderTournamentTitle();
    renderTournamentInfo();
    renderTournamentRounds();
  }
}

async function renderRound () {
  const response = await fetch(`${BASE_URL}tournament/${TOURNEY_ID}/rounds/${ROUND_ID}/info.json`);
  ROUND_DATA = JSON.parse(await response.text());
  window.ROUND_DATA = ROUND_DATA;

  processRounds();
  renderRoundTitle();
  renderRoundInfo();
  if (ROUTE_NAME == 'round_stats') {
    console.log('round stats');
  } else {
    renderRoundContents();
  }
}

async function renderGame () {
  const response = await fetch(`${BASE_URL}tournament/${TOURNEY_ID}/rounds/${ROUND_ID}/games/${GAME_ID}/stats.json`);
  GAME_DATA = JSON.parse(await response.text());
  window.GAME_DATA = GAME_DATA;
  UNIT_FILTER = null;

  PLAYER_GROUPS = d3.group(GAME_DATA.commands, (d) => {
    let [player, ] = findPlayer(d.player);
    return player.bagrada_player;
  });

  processGames();
  renderGameTitle();
  renderPlayerList();
  renderGames();
  renderPlots();
  renderUnitFilter();
  renderGameInfo();
  renderSummary();
}

function renderInfoInfo () {
  let bagradaLink = dce('a');
  bagradaLink.target = '_blank';
  bagradaLink.textContent = 'bagrada.net';
  bagradaLink.href = `https://bagrada.net/webui/metaserver`;

  titleHead.textContent = 'Myth Stats / Info';

  captionHead.appendChild(bagradaLink);
  captionHead.append(' / ');
  captionHead.append(stateLink('', 'home'));
}

function renderHomeInfo () {
  let bagradaLink = dce('a');
  bagradaLink.target = '_blank';
  bagradaLink.textContent = 'bagrada.net';
  bagradaLink.href = `https://bagrada.net/webui/tournaments`;

  titleHead.textContent = 'Myth Stats / Tournaments';

  captionHead.appendChild(bagradaLink);
  captionHead.append(' / ');
  captionHead.append(stateLink('info', 'info'));
}

function renderHomeTourneys () {
  let tourneyLink = stateLink('tournament/7-mwc25', 'Myth World Cup 2025', 'tournamentLink');
  tournamentContainer.appendChild(tourneyLink);
}

function renderTournamentInfo () {
  let bagradaLink = dce('a');
  bagradaLink.target = '_blank';
  bagradaLink.textContent = 'bagrada.net';
  bagradaLink.href = `https://bagrada.net/webui/tournaments/${TOURNEY_DATA.bagrada_tournament}`;


  titleHead.textContent = ` / ${TOURNEY_DATA.name}`;
  let allTourney = stateLink('tournament/', 'Tournaments');
  titleHead.prepend(allTourney);

  captionHead.appendChild(bagradaLink);
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path + '/stats', ' overall stats'));
  captionHead.append(' / ');
  captionHead.append(stateLink('info', 'info'));
}
function renderTournamentTeamInfo () {
  let bagradaLink = dce('a');
  bagradaLink.target = '_blank';
  bagradaLink.textContent = 'bagrada.net';
  bagradaLink.href = `https://bagrada.net/webui/tournaments/${TOURNEY_DATA.bagrada_tournament}`;


  titleHead.textContent = ` / `;
  let tourneyLink = stateLink(TOURNEY_DATA.path, TOURNEY_DATA.name);
  titleHead.prepend(tourneyLink);
  titleHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'Stats'));
  titleHead.append(' / Team Stats');

  captionHead.appendChild(bagradaLink);
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'overall stats'));
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path, 'results'));
  captionHead.append(' / ');
  captionHead.append(stateLink('info', 'info'));
}
function renderTournamentPlayerInfo () {
  let bagradaLink = dce('a');
  bagradaLink.target = '_blank';
  bagradaLink.textContent = 'bagrada.net';
  bagradaLink.href = `https://bagrada.net/webui/users/${PLAYER_ID}`;

  titleHead.textContent = ` / `;
  let tourneyLink = stateLink(TOURNEY_DATA.path, TOURNEY_DATA.name);
  titleHead.prepend(tourneyLink);
  titleHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'Stats'));
  titleHead.append(' / Player Stats');

  captionHead.appendChild(bagradaLink);
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'overall stats'));
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path, 'results'));
  captionHead.append(' / ');
  captionHead.append(stateLink('info', 'info'));
}
function renderTournamentStatsInfo () {
  let bagradaLink = dce('a');
  bagradaLink.target = '_blank';
  bagradaLink.textContent = 'bagrada.net';
  bagradaLink.href = `https://bagrada.net/webui/tournaments/${TOURNEY_DATA.bagrada_tournament}`;


  titleHead.textContent = ' / Stats';
  let tourneyLink = stateLink(TOURNEY_DATA.path, TOURNEY_DATA.name);
  titleHead.prepend(tourneyLink);

  captionHead.appendChild(bagradaLink);
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path, 'results'));
  captionHead.append(' / ');
  captionHead.append(stateLink('info', 'info'));
}

function processGames () {
}

function processRounds () {
}

function processTournaments () {
  PROCESSED_ROUNDS = {};
  TOURNEY_DATA.rounds.forEach(round => {
    if (round._processed) {
      if (!(round.stage in PROCESSED_ROUNDS)) {
        PROCESSED_ROUNDS[round.stage] = [];
      }
      PROCESSED_ROUNDS[round.stage].push(round);
    }
  });
}

function initMWC25 () {
  // MWC 2025 specific
  ROUND_MAP = new Map([
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ]);
  TEAM_MAP = {
    'ag': ['AG', "Avon's Grove"],
    'd&t': ['D&T', "Death & Taxes"],
    'ma': ['MA', "Marmotas Assassinas"],
    'mit': ['MiT', "Men in Tights"],
    'pk': ['PK', "Peacekeepers"],
    'spy kids': ['SK', "Spy Kids"],
    'tmf': ['TMF', "The Myth-Fits"],
    'z snake': ['ZS', "Z Snake"],
  };
}

function initStats (obj, key) {
  if (!(key in obj)) {
    obj[key] = {
      'kills': 0,
      'losses': 0,
      'dmg_in': 0,
      'dmg_out': 0,
      'actions': 0,
      'actions_engage': 0,
      'game_wins': 0,
      'game_losses': 0,
      'round_wins': 0,
      'round_losses': 0,
      'medals': 0,
      'captains': 0,
      'games': 0,
      'rounds': 0,
      'game_dmg_action_ratio': [],
      'game_dmg_action_ratio_engage': [],
      'game_dmg_cost_ratio': [],
      'game_actions': [],
      'game_actions_engage': [],
      'game_dmg_out': [],
      'round_data': [],
      'game_data': [],
      'game_player': [],
      'game_stats': [],
    };
  }
  return obj[key];
}

function incrementStats (obj, key, gameStat) {
  // debugger;
  let stat = initStats(obj, key);
  for (let statKey of Object.keys(stat)) {
    if (statKey in gameStat) {
      stat[statKey] += gameStat[statKey];
    }
  }
  return stat;
}

function calculateTourneyStats (teamFilter) {
  let teamStats = {};
  let playerStats = {};
  let playerData = {};
  TOURNEY_DATA.rounds.forEach(r => {
    r.games.forEach(g => {
      for (let [teamSlug, team] of Object.entries(g.teams)) {
        if (!teamFilter || teamFilter == teamSlug) {
          for (let [bagrada_player, player] of Object.entries(team.players)) {
            if (player.stats.actions) {
              if (!(bagrada_player in playerData)) {
                playerData[bagrada_player] = {
                  names: [],
                  colors: [],
                  teams: [],
                };
              }
              playerData[bagrada_player].names.push(player.name);
              playerData[bagrada_player].colors.push(player.color[0]);
              playerData[bagrada_player].teams.push(teamSlug);
              let stats = Object.assign({}, player.stats, {
                'medals': player.medals.filter(m => m != 'actions').length,
                'captains': player.captain ? 1 : 0,
              });
              incrementStats(teamStats, teamSlug, stats);
              let playerStat = incrementStats(playerStats, bagrada_player, stats);
              if (player.stats.actions_engage) {
                if (team.winner && player.stats.actions_engage) {
                  playerStat.game_wins += 1;
                } else {
                  playerStat.game_losses += 1;
                }
              }
              if (player.stats.dmg_action_ratio) {
                playerStat.game_dmg_action_ratio.push(player.stats.dmg_action_ratio);
              }
              if (player.stats.dmg_action_ratio_engage) {
                playerStat.game_dmg_action_ratio_engage.push(player.stats.dmg_action_ratio_engage);
              }
              if (player.stats.dmg_out) {
                playerStat.game_dmg_out.push(player.stats.dmg_out);
              }
              if (player.stats.dmg_cost_ratio) {
                playerStat.game_dmg_cost_ratio.push(player.stats.dmg_cost_ratio);
              }
              if (player.stats.actions) {
                playerStat.game_actions.push(player.stats.actions);
              }
              if (player.stats.actions_engage) {
                playerStat.game_actions_engage.push(player.stats.actions_engage);
                playerStat.games += 1;
              }
            }
          }
          let teamStat = initStats(teamStats, teamSlug);
          if (team.winner) {
            teamStat.game_wins += 1;
          } else {
            teamStat.game_losses += 1;
          }
          if (team.stats.dmg_action_ratio) {
            teamStat.game_dmg_action_ratio.push(team.stats.dmg_action_ratio);
          }
          if (team.stats.dmg_action_ratio_engage) {
            teamStat.game_dmg_action_ratio_engage.push(team.stats.dmg_action_ratio_engage);
          }
          if (team.stats.dmg_out) {
            teamStat.game_dmg_out.push(team.stats.dmg_out);
          }
          if (team.stats.dmg_cost_ratio) {
            teamStat.game_dmg_cost_ratio.push(team.stats.dmg_cost_ratio);
          }
          if (team.stats.actions) {
            teamStat.game_actions.push(team.stats.actions);
          }
          if (team.stats.actions_engage) {
            teamStat.game_actions_engage.push(team.stats.actions_engage);
            teamStat.games += 1;
          }
        }
      }
    });
    if (r.games.length) {
      let team1 = initStats(teamStats, r.team1);
      team1.rounds += 1;
      if (r.team1 == r.round_winner) {
        team1.round_wins += 1;
      } else {
        team1.round_losses += 1;
      }
      let team2 = initStats(teamStats, r.team2);
      team2.rounds += 1;
      if (r.team2 == r.round_winner) {
        team2.round_wins += 1;
      } else {
        team2.round_losses += 1;
      }

    }
  });
  let overallTeamStats = [];
  for (let [team, stats] of Object.entries(teamStats)) {
    overallTeamStats.push({
      Team: stateLink(
        `tournament/${TOURNEY_ID}/teams/${team}`,
        teamName(team)
      ),

      'Total\nDmg': stats.dmg_out,
      'Total\nBusy': stats.actions,
      'Total\nAggr.': stats.actions_engage,

      'Median\nDmg': Math.round(avgMedian(stats.game_dmg_out)),
      'Median\nBusy': Math.round(avgMedian(stats.game_actions)),
      'Median\nAggr.': Math.round(avgMedian(stats.game_actions_engage)),
      'Median\nAssert': avgMedian(stats.game_dmg_action_ratio_engage).toFixed(2),
      'Median\nEffic.': avgMedian(stats.game_dmg_cost_ratio).toFixed(2),

      'Games\nPlayed': stats.games,
      'Games\nWon': stats.game_wins,
      'Games\nLost': stats.game_losses,
      'Rounds\nPlayed': stats.rounds,
      'Round\nVictories': stats.round_wins,
      'Round\nDefeats': stats.round_losses,
      '🎖️ Medals': stats.medals + Math.max(0, stats.round_wins - stats.round_losses) + Math.max(0, stats.game_wins - stats.game_losses),
    });
  }
  let overallPlayerStats = [];
  for (let [playerId, stats] of Object.entries(playerStats)) {
    let player = playerData[playerId];
    let teamSlug = avgMode(player.teams);
    let playerColor = avgMode(player.colors);
    let playerLink = stateLink(
      `tournament/${TOURNEY_ID}/players/${playerId}`,
      stripFormat(stripOrder(avgMode(player.names)))
    );
    playerLink.style.borderLeft = `8px solid ${playerColor}`;
    overallPlayerStats.push(Object.assign({
      Team: stateLink(
        `tournament/${TOURNEY_ID}/teams/${teamSlug}`,
        teamNameShort(avgMode(player.teams))
      ),
      Player: playerLink,
    }, aggregatePlayerStats(stats)));
  }

  if (!teamFilter) {
    tournamentContainer.append(dce('h3', '', 'Team Stats'));
    let teamTable = makeTable(
      Object.keys(overallTeamStats[0]),
      overallTeamStats.map(s => Object.values(s)),
      ['string'],
      'teamDataTable',
      STAT_TOOLTIPS,
    );
    tournamentContainer.append(teamTable);
    teamTable.querySelector('td.dataTableHead___Medals').click();
  }

  let playerStatHeading = 'Player Stats';
  if (teamFilter) {
    playerStatHeading = `Team Stats: ${teamName(teamFilter)}`;
  }
  tournamentContainer.append(dce('h3', '', playerStatHeading));
  let playerTable = makeTable(
    Object.keys(overallPlayerStats[0]),
    overallPlayerStats.map(s => Object.values(s)),
    ['string', 'string'],
    'playerDataTable',
    STAT_TOOLTIPS
  );
  playerTable.querySelector('td.dataTableHead___Medals').click();
  tournamentContainer.append(playerTable);
}

function tableClass (name) {
  return name.replace(/[\n\s]+/g, '_').replace(/[^\w]/g, '');
}

function makeTable (headers, values, types, className, tooltips) {
  let table = dce('table', 'dataTable');
  if (className) {
    table.classList.add(className);
  }
  let thead = dce('thead');
  let theadRow = dce('tr');
  headers.forEach((h, i) => {
    let headCell = dce('td', `dataTableHead__${tableClass(h)}`, h);
    if (types && types[i] != 'none') {
      headCell.classList.add('sorthead');
      if (tooltips[h]) {
        tooltip(headCell, tooltips[h]);
      }
      headCell.dataset.type = types[i] || 'number';
    }
    theadRow.append(headCell);
  });
  thead.append(theadRow);
  table.append(thead)

  let tbody = dce('tbody');
  values.forEach(row => {
    let valueRow = dce('tr');
    row.forEach((v, i) => {
      if (v && (!types || !types[i] || !types[i] == 'number')) {
        v = v.toLocaleString();
      }
      let valueCell = dce('td', `dataTable__${tableClass(headers[i])}`);
      valueCell.append(v);
      valueRow.append(valueCell);
    });
    tbody.append(valueRow);
  });
  table.append(tbody);
  if (types && values.length > 1) {
    sortTable(table);
  }
  return table;
}

function sortTable (table) {
  table.querySelectorAll('thead td.sorthead').forEach((th, colIndex) => {
    th.addEventListener('click', () => {
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const type = th.dataset.type || 'string';
      let currentClass;
      if (th.classList.contains('asc')) {
        currentClass = 'asc';
      } else if (th.classList.contains('desc')) {
        currentClass = 'desc';
      }
      let ascending;
      if (currentClass) {
        ascending = currentClass !== 'asc'; // toggle
      } else {
        ascending = (type === 'string');    // default: string → asc, number → desc
      }

      rows.sort((a, b) => {
        const cellA = a.children[colIndex].textContent.trim();
        const cellB = b.children[colIndex].textContent.trim();
        let valA = type === 'number' ? parseFloat(cellA.replace(',', '')) : cellA.toLowerCase();
        let valB = type === 'number' ? parseFloat(cellB.replace(',', '')) : cellB.toLowerCase();

        if (valA < valB) return ascending ? -1 : 1;
        if (valA > valB) return ascending ? 1 : -1;
        return 0;
      });

      // Remove existing sort classes
      table.querySelectorAll('thead td.sorthead').forEach(thEl => {
        thEl.classList.remove('asc');
        thEl.classList.remove('desc');
      });
      th.classList.add(ascending ? 'asc' : 'desc');

      rows.forEach(row => tbody.appendChild(row)); // Reorder rows
    });
  });

}

// function avgMean (arr) {
//   return arr.reduce((a, b) => a + b) / arr.length;
// }

function avgMode(arr) {
  const counts = {};
  for (const val of arr) {
    counts[val] = (counts[val] || 0) + 1;
  }

  let maxCount = 0;
  let mode = null;
  for (const [val, count] of Object.entries(counts)) {
    if (count > maxCount) {
      maxCount = count;
      mode = val;
    }
  }

  return mode;
}

function avgMedian (arr) {
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
}
// median absolute deviation from the median
// a metric for score spread
// function mad (arr, med) {
//   const absDiffs = arr.map(x => Math.abs(x - med));
//   return avgMedian(absDiffs);
// }
// median / 1+mad 
// function computeRawScore (values) {
//   const med = avgMedian(values);
//   const madVal = mad(values, med);
//   return med / (1 + madVal); // your chosen formula
// }
// function scaleTo1to5 (score, min, max) {
//   if (max === min) return 3; // avoid divide-by-zero
//   return 1 + 4 * (score - min) / (max - min);
// }

function teamName (name) {
  return TEAM_MAP ? TEAM_MAP[name.toLowerCase()][1] : name;
}
function teamNameShort (name) {
  return TEAM_MAP ? TEAM_MAP[name.toLowerCase()][0] : name;
}

function renderTournmamentStats () {
  tournamentContainer.innerHTML = '';
  calculateTourneyStats();
}

function renderTournamentPlayer () {
  tournamentContainer.innerHTML = '';
  renderPlayerStats(PLAYER_ID);
}

function aggregatePlayerStats (stats) {
  return {
    'Total\nDmg': stats.dmg_out,
    'Total\nBusy': stats.actions,
    'Total\nAggr.': stats.actions_engage,

    'Median\nDmg': Math.round(avgMedian(stats.game_dmg_out)),
    'Median\nBusy': Math.round(avgMedian(stats.game_actions)),
    'Median\nAggr.': Math.round(avgMedian(stats.game_actions_engage)),
    'Median\nAssert': avgMedian(stats.game_dmg_action_ratio_engage).toFixed(2),
    'Median\nEffic.': avgMedian(stats.game_dmg_cost_ratio).toFixed(2),

    'Games\nPlayed': stats.games,
    'Games\nWon': stats.game_wins,
    'Games\nLost': stats.game_losses,
    '🔹 Cap': stats.captains,
    '🎖️ Medals': stats.medals + Math.max(0, stats.game_wins - stats.game_losses),
  };
}

function renderPlayerStats (bagrada_player) {
  let playerStats = {};
  let playerData = {
    names: [],
    colors: [],
    teams: [],
  };
  TOURNEY_DATA.rounds.forEach(r => {
    r.games.forEach(g => {
      for (let [teamSlug, team] of Object.entries(g.teams)) {
        let player = team.players[bagrada_player];
        if (player && player.stats.actions) {
          playerData.names.push(player.name);
          playerData.colors.push(player.color[0]);
          playerData.teams.push(teamSlug);
          let stats = Object.assign({}, player.stats, {
            'medals': player.medals.filter(m => m != 'actions').length,
            'captains': player.captain ? 1 : 0,
          });
          let playerStat = incrementStats(playerStats, bagrada_player, stats);
          if (player.stats.actions_engage) {
            if (team.winner && player.stats.actions_engage) {
              playerStat.game_wins += 1;
            } else {
              playerStat.game_losses += 1;
            }
          }
          if (player.stats.dmg_action_ratio) {
            playerStat.game_dmg_action_ratio.push(player.stats.dmg_action_ratio);
          }
          if (player.stats.dmg_action_ratio_engage) {
            playerStat.game_dmg_action_ratio_engage.push(player.stats.dmg_action_ratio_engage);
          }
          if (player.stats.dmg_out) {
            playerStat.game_dmg_out.push(player.stats.dmg_out);
          }
          if (player.stats.dmg_cost_ratio) {
            playerStat.game_dmg_cost_ratio.push(player.stats.dmg_cost_ratio);
          }
          playerStat.game_actions.push(player.stats.actions);
          if (player.stats.actions_engage) {
            playerStat.game_actions_engage.push(player.stats.actions_engage);
            playerStat.games += 1;
          }
          playerStat.round_data.push(r);
          playerStat.game_data.push(g);
          playerStat.game_player.push(player);
          playerStat.game_stats.push(player.stats);
        }
      }
    });
  });
  let stats = playerStats[bagrada_player];
  let teamSlug = avgMode(playerData.teams);
  let playerColor = avgMode(playerData.colors);
  let playerName = stripFormat(stripOrder(avgMode(playerData.names)));
  let finalPlayerStats = Object.assign({
    Team: stateLink(
      `tournament/${TOURNEY_ID}/teams/${teamSlug}`,
      teamNameShort(avgMode(playerData.teams))
    ),
    Player: playerName
  }, aggregatePlayerStats(stats));

  let playerStatHeading = `Player Stats: ${playerName}`;
  tournamentContainer.append(dce('h3', '', playerStatHeading));

  let playerStatTable = makeTable(
    Object.keys(finalPlayerStats),
    [Object.values(finalPlayerStats)],
    ['string', 'string'],
    'playerDataTable',
    STAT_TOOLTIPS
  );
  playerStatTable.style.borderLeft = `8px solid ${playerColor}`;
  tournamentContainer.append(playerStatTable);

  renderPlayerGraph(stats, 'dmg_out', 'Damage Dealt', "Damage Dealt");
  renderPlayerGraph(stats, 'actions', 'Busyness', "Busyness (Commands issued)");
  renderPlayerGraph(stats, 'actions_engage', 'Aggression', "Aggression (Engagement commands issued)");
  renderPlayerGraph(stats, 'dmg_action_ratio_engage', 'Assertive Index', "Assertive Index (Damage / Aggression vs average)");
  renderPlayerGraph(stats, 'dmg_cost_ratio', 'Efficiency', "Efficiency Index (Damage / Unit value held vs average)");
}

function renderPlayerGraph (stats, stat, label, title) {
  let graph = Plot.plot({
    width: 1200,
    height: 80,
    x: {
      axis: false,
    },
    y: {
      axis: false,
    },
    marks: [
      Plot.line(stats.game_stats, {
        x: (d, i) => i,
        y: stat,
        stroke: '#2B4965',
        strokeWidth: 3,
        curve: 'catmull-rom',
      }),
      Plot.text(stats.game_stats, {
        dy: -10,
        x: (d, i) => i,
        y: stat,
        text: (d, i) => {
          let ret = d[stat];
          if (stats.game_player[i].medals.includes(stat)) {
            ret += '🎖️';
          }
          return ret;
        },
        fontSize: 11,
        title: (d, i) => {
          if (d[stat]) {
            return `${stats.round_data[i].round_name}: Game ${stats.game_data[i].game_num}\n${stats.game_data[i].game_type}\n${stats.game_data[i].map_name}\n${label}: ${d[stat]}`
          }
        },
        tip: {
          dy: 5,
          anchor: 'top',
          fontSize: 13,
        },
        href: (d, i) => `${BASE_URL}${stats.game_data[i].game_path}`,
      })
    ]
  });
  tournamentContainer.append(
    dce('h4', 'playerGraph__head', title)
  );
  tournamentContainer.append(graph);
}

function renderTournamentTeam () {
  tournamentContainer.innerHTML = '';
  calculateTourneyStats(TEAM_ID);

  if (ROUND_MAP && PROCESSED_ROUNDS) {
    let groupedRoundContainer = renderRounds(PROCESSED_ROUNDS, TEAM_ID);
    tournamentContainer.appendChild(groupedRoundContainer);
  }
}

function renderTournamentRounds () {
  tournamentContainer.innerHTML = '';
  if (!TOURNEY_DATA.rounds || !TOURNEY_DATA.rounds.length) {
    return;
  }
  if (ROUND_MAP && PROCESSED_ROUNDS) {
    let groupedRoundContainer = renderRounds(PROCESSED_ROUNDS);
    tournamentContainer.appendChild(groupedRoundContainer);
  } else {
    let roundList = dce('ul', 'tournamentRounds');
    TOURNEY_DATA.rounds.forEach(round => {
      let roundItem = dce('li', 'tournamentRounds__round');
      
      let roundLink = stateLink(round.round_path, round.round_name);
      roundItem.appendChild(roundLink);

      roundList.appendChild(roundItem);
    });
    tournamentContainer.appendChild(roundList);
  }
}

function renderRounds(rounds, teamFilter) {
  let groupedRoundContainer = dce('div', 'tournamentGroupedRounds');
  for (const [roundStage, roundStageFull] of ROUND_MAP) {
    let roundContainer = dce('div', 'tournamentGroupedRounds__group');

    let roundHead = dce('h4', 'tournamentGroupedRounds__head', roundStageFull);

    let roundList = dce('ul', 'tournamentGroupedRounds__rounds');
    let hasRounds = false;
    PROCESSED_ROUNDS[roundStage].forEach(round => {
      if (!teamFilter || round.team1 == teamFilter || round.team2 == teamFilter) {
        hasRounds = true;
        let roundItem = dce('li',  'tournamentGroupedRounds__round');

        let suffixText = '';
        if (round.part != null) {
          suffixText += ` (${round.part})`;
        }
        let roundLink = stateLink(round.round_path, ' vs ');
        tooltip(roundLink, `${roundStage}: ${teamName(round.team1)} vs ${teamName(round.team2)}${suffixText}`);
        roundLink.className = 'tournamentGroupedRounds__round_link';
        let team1 = dce('span', 'tournamentGroupedRounds__team', teamNameShort(round.team1));
        let team2 = dce('span', 'tournamentGroupedRounds__team', teamNameShort(round.team2));
        let suffix = dce('span', 'tournamentGroupedRounds__suffix', suffixText);
        let result = dce('span', 'tournamentGroupedRounds__result');

        roundLink.prepend(team1);
        roundLink.appendChild(team2);
        roundLink.appendChild(suffix);
        roundLink.append(' ');
        roundLink.appendChild(result);

        roundItem.appendChild(roundLink);

        if (round.games.length) {
          let roundGameLinks = dce('div',  'tournamentGroupedRounds__games');
          round.games.forEach(game => {
            let roundGameLink = stateLink(game.game_path, game.game_num);
            tooltip(roundGameLink, `${game.game_num}. ${game.game_type} — ${stripFormat(game.map_name)}`);
            roundGameLink.className = 'tournamentGroupedRounds__game';
            roundGameLinks.appendChild(roundGameLink);
          });

          roundItem.appendChild(roundGameLinks);
        } else if (round.forfeit) {
          let roundGameForfeit = dce('div', 'tournamentGroupedRounds__forfeit');
          roundGameForfeit.textContent = `${teamNameShort(round.forfeit)} forfeit`;
          roundItem.appendChild(roundGameForfeit);
        } else {
          roundItem.append('No games');
        }

        result.textContent = `${round.winning_teams[round.team1]} - ${round.winning_teams[round.team2]}`;
        if (round.round_winner == round.team1) {
          team1.classList.add('tournamentGroupedRounds__team--winner');
          team2.classList.add('tournamentGroupedRounds__team--loser');
        } else if (round.round_winner == round.team2) {
          team1.classList.add('tournamentGroupedRounds__team--loser');
          team2.classList.add('tournamentGroupedRounds__team--winner');
        }

        roundList.appendChild(roundItem);
      }
    });

    if (hasRounds) {
      roundContainer.appendChild(roundHead);
      roundContainer.appendChild(roundList);
      groupedRoundContainer.appendChild(roundContainer);
    }
  }
  return groupedRoundContainer;
}

function renderRoundInfo () {
  let bagradaLink = dce('a');
  bagradaLink.target = '_blank';
  bagradaLink.textContent = 'bagrada.net';
  bagradaLink.href = `https://bagrada.net/webui/tournaments/${ROUND_DATA.tournament.bagrada_tournament}/rounds/${ROUND_DATA.bagrada_round}`;
  captionHead.appendChild(bagradaLink);
  captionHead.append(' / ');
  captionHead.append(stateLink(ROUND_DATA.tournament.path + '/stats', 'overall stats'));
  captionHead.append(' / ');
  captionHead.append(stateLink('info', 'info'));

  titleHead.textContent = ` / ${ROUND_DATA.round_name}`;
  let tourneyLink = stateLink(ROUND_DATA.tournament.path, ROUND_DATA.tournament.name);
  titleHead.prepend(tourneyLink);

  let result, team1, team2;
  if (ROUND_DATA._processed) {
    let partSuffix = ROUND_DATA.part ? `(${ROUND_DATA.part})` : ''
    subtitleHead.textContent = ' vs ';
    team1 = dce('span', 'round__team', teamName(ROUND_DATA.team1));
    team2 = dce('span', 'round__team', teamName(ROUND_DATA.team2));
    let suffix = dce('span', 'round__suffix', partSuffix);
    result = dce('span', 'round__result');
    subtitleHead.prepend(team1);
    subtitleHead.appendChild(team2);
    subtitleHead.append(' ');
    subtitleHead.append(suffix);
    subtitleHead.append(' ');
    subtitleHead.append(result);

    let subtitleStage = dce('span', 'round__stage', `${ROUND_MAP.get(ROUND_DATA.stage)}: `);
    subtitleHead.prepend(subtitleStage);
  } else {
    subtitleHead.textContent = ROUND_DATA.round_name;
  }

  if (result && team1 && team2) {
    result.textContent = `${ROUND_DATA.winning_teams[ROUND_DATA.team1]} - ${ROUND_DATA.winning_teams[ROUND_DATA.team2]}`;
    if (ROUND_DATA.round_winner == ROUND_DATA.team1) {
      team1.classList.add('tournamentGroupedRounds__team--winner');
      team2.classList.add('tournamentGroupedRounds__team--loser');
    } else if (ROUND_DATA.round_winner == ROUND_DATA.team2) {
      team1.classList.add('tournamentGroupedRounds__team--loser');
      team2.classList.add('tournamentGroupedRounds__team--winner');
    }
  }
}

function renderRoundContents () {
  if (ROUND_DATA.games.length) {
    let gameList = renderRoundGames(ROUND_DATA.games);
    roundContainer.appendChild(gameList);
  } else if (ROUND_DATA.forfeit) {
    roundContainer.textContent = `${teamName(ROUND_DATA.forfeit)} forfeit`;
  } else {
    roundContainer.textContent = `No games`;
  }
}

function renderRoundGames (games) {
  let gameList = dce('ol', 'roundGames');
  games.forEach(game => {
    let gameItem = dce('li', 'roundGames__game');

    let gameLink = stateLink(game.game_path);
    gameLink.className = 'roundGames__link';
    let gameInfo = dce('div', 'roundGames__info', ` — `);
    let gameType = dce('span', 'roundGames__type', game.game_type);
    gameInfo.prepend(gameType);

    let gameWinner = dce('span', 'roundGames__winner', teamNameShort(game.winning_team));
    let winningTeam = game.teams[game.winning_team];
    gameWinner.style.borderBottom = `5px solid ${winningTeam.color[0]}`;
    tooltip(gameWinner, `Winner: ${teamName(game.winning_team)}`);
    gameInfo.prepend(' ');
    gameInfo.prepend(gameWinner);

    let gameTime = dce('span', 'roundGames__time', `${Math.round(game.time_limit/30/60)} mins`);
    gameInfo.appendChild(gameTime);

    let gameMap = dce('div', 'roundGames__map', stripFormat(game.map_name));

    let overheadDiv = dce('div', 'roundGames__overhead');
    let overheadMap = dce('img', 'roundGames__overhead_img');
    overheadMap.src = `${BASE_URL}${game.game_path}/overhead.png`;
    overheadDiv.appendChild(overheadMap)
    gameLink.appendChild(overheadDiv);

    gameLink.appendChild(gameInfo);
    gameLink.appendChild(gameMap);

    gameItem.appendChild(gameLink);

    gameList.appendChild(gameItem);
  });
  return gameList;
}

// Custom action type colors
const ACTIONS = [
  "MOVEMENT",
  "HEAL",
  "SPECIAL_ABILITY",
  "PICK_UP",
  "STOP",
  "SCATTER",
  "GUARD",
  "ATTACK",
  "ATTACK_SPECIAL",
  "GROUND",
  "GROUND_SPECIAL",
  // "TAUNT",
];
const ACTION_NAMES = [
  "Move",
  "Heal",
  "Instant Special",
  "Pick Up",
  "Stop",
  "Scatter",
  "Guard",
  "Attack",
  "Special Attack",
  "Ground Attack",
  "Ground Special",
  // "Taunt",
];
const ACTION_MAP = Object.fromEntries(
  ACTIONS.map((key, i) => [key, ACTION_NAMES[i]])
);
const ACTION_COLORS = [
  "yellow",
  "lightgreen",
  "brown",
  "green",
  "grey",
  "lightgrey",
  "orange",
  "red",
  "#08f",
  "violet",
  "purple",
  // "white",
];

function fiterUnits (d) {
  if (UNIT_FILTER && UNIT_FILTER.length) {
    if (d.monsters && Object.keys(d.monsters).some(monster => UNIT_FILTER.includes(monster))) {
      return true;
    }
    // Don't filter on targets, just attackers
    if (d.targets && Object.values(d.targets).map(v => Object.keys(v)).flat().some(monster => UNIT_FILTER.includes(monster))) {
      return true;
    }
    return false;
  } else {
    return true;
  }
}

function renderPlots () {
  // Remove old plot if exists
  clickGraph.innerHTML = '';

  // Marks with opacity based on FILTERED_PLAYER

  const marks = Array.from(PLAYER_GROUPS, ([bagradaPlayer, points]) => {
    return [
      Plot.line(points, {
        x: "time",
        y: (d, i) => {
          d.index = i;
          return i
        },
        z: null,
        stroke: "yellow",
        strokeWidth: 3,
        filter: fiterUnits,
        opacity: FILTERED_PLAYER ? (bagradaPlayer == FILTERED_PLAYER ? 1 : 0.1) : 1,
      }),
      Plot.dot(points, {
        x: "time",
        y: (d, i) => i,
        stroke: "action",
        r: FILTERED_PLAYER ? (bagradaPlayer == FILTERED_PLAYER ? 3 : 2) : 2,
        fill: "action",
        opacity: FILTERED_PLAYER ? (bagradaPlayer == FILTERED_PLAYER ? 1 : 0.05) : 1,
        filter: (d) => {
          if (d.action == 'MOVEMENT') {
            return false;
          }
          return fiterUnits(d);
        },
      }),
    ]
  }).flat();

  let tip = Plot.tip(GAME_DATA.commands, Plot[FILTERED_PLAYER ? 'pointerX' : 'pointer']({
    x: 'time',
    y: 'index',
    maxRadius: FILTERED_PLAYER ? 200 : 40,
    filter: (d) => {
      if (d.action == 'MOVEMENT') {
        return false;
      }
      if (!FILTERED_PLAYER) {
        return fiterUnits(d);
      }
      let [player, ] = findPlayer(d.player);
      if (player.bagrada_player == FILTERED_PLAYER) {
        return fiterUnits(d);
      }
      return false;
    },
    fontSize: 13,
    textPadding: 10,
    lineHeight: 1.4,
    lineWidth: 40,
    title: (d) => {
      let seconds = (GAME_DATA.header.game.time_limit - d.time) / 30;
      let t;
      if (seconds < 0) {
        t = 'Sudden Death';
      } else {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        t = `${mins}:${secs.toString().padStart(2, "0")}`;
      }
      let monsters = summarizeMonsters(d.monsters);
      let [targets, targetOwner] = summarizeTargets(d.targets, d.player);
      if (targets) {
        monsters += ` → ${targets}`;
      }
      let [player, teamSlug] = findPlayer(d.player);
      let teamName = teamNameShort(teamSlug);
      let playerLine = `[${teamName}] ${stripOrder(player.name)} → ${ACTION_MAP[d.action] || d.action}`;
      if (targetOwner) {
        playerLine += `: ${targetOwner}`;
      }
      let tipText = `${playerLine} @ ${t}\n${monsters}`;
      return tipText;
    },
  }));

  actionLegend.innerHTML = '';
  actionLegend.append(makeLegend());

  let showStats = showingStats();
  let plotWidth = showStats ? 600 : 900;
  const plot = Plot.plot({
    width: plotWidth,
    height: showStats ? 515 : 540,
    x: {
        label: "Time remaining",
        ticks: Plot.numberInterval(1800),
        grid: true,
        tickFormat: ticks => {
          let seconds = (GAME_DATA.header.game.time_limit - ticks) / 30;
          const mins = Math.floor(seconds / 60);
          const secs = Math.floor(seconds % 60);
          return `${mins}:${secs.toString().padStart(2, "0")}`;
        }

    },
    y: {
      label: "Commands",
      grid: true
    },
    color: {
      domain: ACTIONS,
      range: ACTION_COLORS,
      legend: false
    },
    marks: [
      Plot.ruleX([GAME_DATA.header.game.time_limit], {
        stroke: '#666',
      })
    ].concat(marks, [
      tip,
    ])
  });
  // plot.addEventListener("input", () => {
  //   console.log(plot.value);
  // });
  // clickGraph.append(Plot.legend({
  //   width: showStats ? 440 : 900,
  //   fontSize: '40px',
  //   color: {
  //     domain: ACTION_NAMES,
  //     range: ACTION_COLORS,
  //   },
  // }));
  clickGraph.append(plot);
}

function renderUnitFilter () {
  graphFilter.innerHTML = '';

  let unitFilter = dce('div', 'unitFilter');
  let unitFilterButton = dce('span', 'unitFilter__button', 'Unit filter');
  let units = {};
  for (const team of Object.values(GAME_DATA.header.teams)) {
    team.trade.forEach(t => {units[t.name] = true});
  }
  unitFilterButton.addEventListener('click', () => {
    unitFilter.classList.toggle('unitFilter--selected');
  });
  let unitFilterDropdown = dce('form', 'unitFilter__dropdown');

  let labelAll = dce('label', 'unitFilter__label', " All");
  let checkboxAll = dce('input', 'unitFilter__checkbox unitFilter__checkbox_all');
  checkboxAll.type = 'checkbox';
  checkboxAll.checked = true;
  checkboxAll.name = 'all';
  checkboxAll.value = '1';
  labelAll.prepend(checkboxAll);
  unitFilterDropdown.append(labelAll);

  Object.keys(units).forEach(u => {
    let label = dce('label', 'unitFilter__label', ` ${u}`);
    let checkbox = dce('input', 'unitFilter__checkbox unitFilter__checkbox_unit');
    checkbox.type = 'checkbox';
    checkbox.name = 'unit';
    checkbox.value = u;
    label.prepend(checkbox);
    unitFilterDropdown.append(label);
  })
  unitFilter.append(unitFilterButton);
  unitFilter.append(unitFilterDropdown);
  unitFilter.addEventListener('change', (e) => {
    const params = new FormData(unitFilterDropdown);
    UNIT_FILTER = Array.from(params).flatMap(p => {
      if (p[0] == 'unit') {
        return [p[1]];
      }
      return [];
    });
    if (e.target == checkboxAll) {
      if (UNIT_FILTER.length) {
        document.querySelectorAll('.unitFilter__checkbox_unit').forEach(c => {
          c.checked = false;
        });
        UNIT_FILTER = [];
      } else {
        checkboxAll.checked = true;
      }
    } else {
      checkboxAll.checked = !UNIT_FILTER.length;
    }
    unitFilter.classList.toggle('unitFilter--active', !!UNIT_FILTER.length);
    renderPlots();
  });

  graphFilter.append(unitFilter);
}

function makeLegend () {
  let legend = dce('table', 'legendTable');
  let col = 0;
  let row = dce('tr');
  let maxCols = showingStats() ? 6 : 16;
  ACTION_NAMES.forEach((name, i) => {
    let span = 1;
    if (name.length > 10) {
      span = 2;
    }
    col += span;
    let cell = dce('td', 'legendTable__cell', ` ${name}`);
    cell.colSpan = span;
    let swatch = dce('span', 'legendTable__swatch');
    swatch.style.backgroundColor = ACTION_COLORS[i];
    cell.prepend(swatch);
    row.appendChild(cell);
    if (col > maxCols) {
      legend.appendChild(row);
      col = 0;
      row = dce('tr');
    }
  });
  if (col) {
    legend.appendChild(row);
  }

  return legend;
}

function summarizeAllocation (allocation) {
  if (!allocation) {
    return '';
  }
  let summaryParts = [];
  allocation.forEach(u => {
    if (u.count) {
      let summaryPart = `${u.count}x ${u.name}`;
      summaryParts.push(summaryPart);
    }
  });
  return summaryParts.join(', ');
}

function summarizeMonsters (monsters) {
  if (!monsters) {
    return '';
  }
  let summaryParts = [];
  for (const [monsterName, monsterCount] of Object.entries(monsters)) {
    let summaryPart = '';
    if (monsterCount > 1) {
      summaryPart = `${monsterCount}x `;
    }
    summaryPart += monsterName;
    summaryParts.push(summaryPart);
  }
  return summaryParts.join(', ');
}

function summarizeTargets (targets, self) {
  if (!targets) {
    return [null, null];
  }
  let summaryTargets = [];
  let owner = null;
  for (const [playerId, monsters] of Object.entries(targets)) {
    summaryTargets.push(summarizeMonsters(monsters));
    if (!['ambient', 'custom'].includes(playerId)) {
      let [player, ] = findPlayer(playerId);
      if (playerId == self) {
        owner = 'self';
      } else if (player) {
        owner = stripOrder(player.name);
      }
    }
  }
  return [summaryTargets.join(', '), owner];
}

function findPlayer (playerId) {
  for (const [teamSlug, team] of Object.entries(GAME_DATA.header.teams)) {
    if (playerId in team.players) {
      return [team.players[playerId], teamSlug];
    }
  }
}

function renderGames () {
  // Render round game list
  gameList.innerHTML = ''
  let gameSelect = dce('div', 'gameSelect');
  GAME_DATA.header.round.games.forEach(game => {
    const a = stateLink(game.game_path);
    a.className = 'gameSelect__game';
    if (game.bagrada_game == GAME_DATA.header.game.bagrada_game) {
      a.classList.add('gameSelect__game--selected');
    }
    let mapName = dce('span', 'gameSelect__game_map', `${game.game_num}. ${stripBrackets(stripFormat(game.map_name))}`);
    let gameType = dce('span', 'gameSelect__game_type', game.game_type);
    a.appendChild(mapName);
    a.appendChild(gameType);
    gameSelect.appendChild(a);
  });
  gameList.appendChild(gameSelect);
}

const STAT_COLS = new Map([
  // ['dmg_in', 'DI'],
  ['dmg_out', ['Dmg', 'Damage Dealt']],
  ['kills', ['Kill', 'Kills']],
  ['losses', ['Loss', 'Losses']],
  ['kill_loss_ratio', ['K/L', 'Kill/Loss ratio']],
  ['actions', ['Busy', 'Busyness (Commands issued)']],
  ['actions_engage', ['Aggr.', 'Aggression (Engagement commands issued)']],
  ['dmg_cost_ratio', ['Effic.', 'Efficiency Index (Dmg / Unit value held vs average)']],
  ['dmg_action_ratio_engage', ['Assert', 'Assertive Index (Dmg / Aggression vs average)']],
]);

function colCalc (col, stats) {
  if (col in stats) {
    let stat = stats[col];
    if (['kill_loss_ratio', 'dmg_action_ratio_engage', 'dmg_cost_ratio'].includes(col)) {
      stat = stat.toFixed(2);
    } else {
      if (col == 'dmg_out' && stats['dmg_out_adjusted']) {
        stat = `* ${stat}`;
      }
    }
    return stat;
  } else {
    return '';
  }
}

const TOOLTIP = dce('div', 'tooltip');
document.body.appendChild(TOOLTIP);
let TOOLTIP_ID = 1;
let TOOLTIP_CONTENTS = {};

function tooltip (el, content) {
  let node = dce('span', 'tooltip__plain', content);
  tooltipNode(el, node);
}

function tooltipNode (el, node) {
  TOOLTIP.innerHTML = '';
  let tipId = TOOLTIP_ID++;
  el.dataset.tooltip_id = tipId;
  TOOLTIP_CONTENTS[tipId] = node
  el.classList.add('tooltip__target');
  el.addEventListener("mouseenter", () => {
    showTooltip(el);
  });

  el.addEventListener("mousemove", e => {
    const offset = 10;
    const smudge = 10;
    const tooltipWidth = TOOLTIP.offsetWidth;
    const tooltipHeight = TOOLTIP.offsetHeight;
    const pageX = e.pageX;
    const pageY = e.pageY;

    const willOverflowRight = pageX + offset + smudge + tooltipWidth > window.innerWidth;
    const willOverflowBottom = pageY + offset + smudge + tooltipHeight > window.innerHeight;

    const left = willOverflowRight
      ? pageX - tooltipWidth - offset
      : pageX + offset;

    const top = willOverflowBottom
      ? pageY - tooltipHeight - offset
      : pageY + offset;

    TOOLTIP.style.left = `${Math.max(left, offset)}px`;
    TOOLTIP.style.top = `${Math.max(top, offset)}px`;

  });

  el.addEventListener("mouseleave", () => {
    hideTooltip();
  });
}

function showTooltip (el) {
  TOOLTIP.innerHTML = '';
  TOOLTIP.appendChild(TOOLTIP_CONTENTS[el.dataset.tooltip_id]);
  TOOLTIP.classList.add('tooltip--show');
}

function hideTooltip () {
  TOOLTIP.classList.remove('tooltip--show');
}

function clearTooltips () {
  hideTooltip();
  TOOLTIP_CONTENTS = {};
}

function renderPlayerList () {
  // Render player list
  playerList.innerHTML = ''
  let statsTable = dce('table', 'playerStats');

  let statsCols = dce('colgroup');
  let col, col_name, col_desc;
  for ([col, [col_name, col_desc]] of STAT_COLS) {
    statsCols.append(dce('col',  `col_stat col_stat__${col}`));
  }
  statsCols.append(dce('col', 'col_spacerLeft'));
  statsCols.append(dce('col', 'col_name'));
  statsCols.append(dce('col', 'col_pct'));
  statsCols.append(dce('col', 'col_spacerRight'));
  statsTable.append(statsCols);

  let statsHead = dce('thead');
  let statsHeadRow = dce('tr', 'playerStats__head');
  for ([col, [col_name, col_desc]] of STAT_COLS) {
    let headCell = dce('td',  `statHead statCell statCell__${col}`, col_name);
    tooltip(headCell, col_desc);
    statsHeadRow.appendChild(headCell);
  }

  statsHeadRow.append(dce('td', 'playerListLeftSpacer'));

  let playerListHead = dce('td', 'playerListHead');
  playerListHead.colSpan = 2;
  let showStats = dce('span', 'playerList__show_stats_button');
  let showStatsShow = dce('span', 'playerList__show_stats_show', 'show stats');
  let showStatsHide = dce('span', 'playerList__show_stats_hide', 'hide stats');
  showStats.appendChild(showStatsShow);
  showStats.appendChild(showStatsHide);
  showStats.addEventListener('click', () => {
    if (showingStats()) {
      document.getElementById('columns').classList.remove('show-stats');
    } else {
      document.getElementById('columns').classList.add('show-stats');
    }
    renderPlots();
    renderSummary();
  });
  playerListHead.appendChild(showStats);
  statsHeadRow.appendChild(playerListHead);

  statsHeadRow.append(dce('td', 'playerListRightSpacer'));

  statsHead.appendChild(statsHeadRow);

  let statsBody = dce('tbody');
  for (const [teamSlug, team] of Object.entries(GAME_DATA.header.teams)) {
    // Team stat line
    let teamRow = dce('tr', 'playerStats__team');

    for ([col, ] of STAT_COLS) {
      let statCell = dce('td', `statTeam statCell statCell__${col}`, colCalc(col, team.stats));
      if (col == 'dmg_out' && team.stats['dmg_out_adjusted']) {
        tooltip(statCell, `Dmg adjusted for self heal kills (orig: ${team.stats['dmg_out_orig']})`);
      }
      teamRow.appendChild(statCell);
    }

    let teamLeftSpacer = dce('td', 'playerListLeftSpacer playerListLeftSpacerTeam');
    let teamLeftColor = dce('div', 'playerListTeamColor');
    teamLeftColor.style.backgroundColor = team.color[0];
    teamLeftSpacer.append(teamLeftColor);
    teamRow.append(teamLeftSpacer);

    let teamHead = dce('td', 'playerSelect__team', teamName(teamSlug));
    if (team.winner) {
      teamHead.append(' ');
      let winner = dce('span', 'playerSelect__winner', '🏆');
      tooltip(winner, 'Winning Team');
      teamHead.appendChild(winner);
    }
    teamRow.appendChild(teamHead);

    let pctHead = dce('td', 'playerSelect__percentHead', "%");
    tooltip(pctHead, `Percentage split after planning time\n\nFull Trade:\n${summarizeAllocation(team.trade)}`);
    teamRow.appendChild(pctHead);

    teamRow.append(dce('td', 'playerListRightSpacer'));

    statsBody.append(teamRow);

    for (const player of Object.values(team.players)) {
      // Player stat line
      const playerRow = dce("tr", 'playerStats__player');
      let bagradaPlayer = player.bagrada_player;
      if (FILTERED_PLAYER == bagradaPlayer) {
        playerRow.classList.add('playerStats__player--selected');
      }
      playerRow.dataset.bagrada_player = bagradaPlayer;

      for ([col, ] of STAT_COLS) {
        let statCell = dce('td', `statCell statCell__${col}`, colCalc(col, player.stats));
        if (col == 'dmg_out' && player.stats['dmg_out_adjusted']) {
          tooltip(statCell, `Dmg adjusted for self heal kills (orig: ${player.stats['dmg_out_orig']})`);
        }
        playerRow.appendChild(statCell);
      }

      let playerLeftSpacer = dce('td', 'playerListLeftSpacer');
      let playerLeftColor = dce('div', 'playerListTeamColor');
      playerLeftColor.style.backgroundColor = team.color[0];
      playerLeftSpacer.append(playerLeftColor);
      playerRow.append(playerLeftSpacer);

      const playerItem = dce("td", 'playerSelect__player', stripOrder(player.name));
      if (player.captain) {
        playerItem.append(' ');
        let captain = dce('span', 'playerSelect__captain', '🔹');
        tooltip(captain, 'Team Captain');
        playerItem.appendChild(captain);
      }
      if (player.medals.length) {
        playerItem.append(' ');
        player.medals.forEach(medal => {
          let medalEl = dce('span', 'playerSelect__medal', '🎖️');
          let statInfo = STAT_COLS.get(medal);
          tooltip(medalEl, `Medal: ${statInfo[1]}`)
          playerItem.appendChild(medalEl);
        });
      }
      playerItem.dataset.bagrada_player = bagradaPlayer;

      playerItem.addEventListener("click", (e) => {
        e.preventDefault();
        selectPlayer(playerRow);
      });
      playerRow.appendChild(playerItem);

      let pct = dce('td', 'playerSelect__percent');
      if (player.unit_allocation) {
        pct.textContent = `${player.unit_allocation.percent}%`;
        tooltip(pct, summarizeAllocation(player.unit_allocation.units));
      }
      playerRow.appendChild(pct);

      let playerRightSpacer = dce('td', 'playerListRightSpacer');
      let playerRightColor = dce('div', 'playerListPlayerColor');
      playerRightColor.style.backgroundColor = player.color[0];
      playerRightSpacer.append(playerRightColor);
      playerRow.append(playerRightSpacer);

      statsBody.appendChild(playerRow);
    }
  }

  statsTable.append(statsHead);
  statsTable.append(statsBody);
  playerList.append(statsTable);
}

function renderGameInfo() {
  captionHead.innerHTML = '';

  let subtitle = `${GAME_DATA.header.game.game_type} on ${stripFormat(GAME_DATA.header.game.map_name)} (${GAME_DATA.header.game.difficulty}) - ${Math.round(GAME_DATA.header.game.time_limit/30/60)} mins`;

  // let host;
  // if ('host' in GAME_DATA.header.game) {
  //   host = stripOrder(GAME_DATA.header.game.host.name);
  // }

  // let start = new Date(GAME_DATA.header.game.start);
  // let end = new Date(GAME_DATA.header.game.end);
  // let timeRange = `${start.toDateString()} - ${start.toLocaleTimeString('en-gb', {
  //   hour: '2-digit',
  //   minute: '2-digit',
  //   hour12: true,
  // })} - ${end.toLocaleTimeString('en-gb', {
  //   timeZoneName: 'short',
  //   hour: '2-digit',
  //   minute: '2-digit',
  //   hour12: true,
  // })}`;
  // let caption = `${timeRange} `;
  // if (host) {
  //   caption += `(Host: ${stripFormat(host)}) - `;
  // }

  let bagradaLink = dce('a');
  bagradaLink.target = '_blank';
  bagradaLink.textContent = 'bagrada.net';
  bagradaLink.href = `https://bagrada.net/webui/games/${GAME_DATA.header.game.bagrada_game}`;

  let filmLink = dce('a');
  filmLink.target = '_blank';
  filmLink.textContent = 'download film';
  filmLink.href = `https://bagrada.net/recordings/public/${GAME_DATA.header.game.film_name}`;

  titleHead.textContent = ' / ';
  let tourneyLink = stateLink(GAME_DATA.header.tournament.path, GAME_DATA.header.tournament.name);
  let roundLink = stateLink(GAME_DATA.header.round.round_path, GAME_DATA.header.round.round_name);
  titleHead.prepend(tourneyLink);
  titleHead.append(roundLink);

  subtitleHead.textContent = subtitle;

  let overheadMap = dce('img');
  overheadMap.src = `${PAGE_URL}/overhead.png`;
  overhead.innerHTML = '';
  overhead.appendChild(overheadMap);

  captionHead.append(bagradaLink);
  captionHead.append(' / ');
  captionHead.append(filmLink);
  captionHead.append(' / ');
  captionHead.append(stateLink(GAME_DATA.header.tournament.path + '/stats', 'overall stats'));
  captionHead.append(' / ');
  captionHead.append(stateLink('info', 'info'));
}

function stateLink (href, textContent, className) {
  let link = dce('a', className, textContent);
  link.href = `${BASE_URL}${href}`;
  link.addEventListener("click", (e) => {
    e.preventDefault();
    history.pushState({}, "", link.href);
    routeUrl();
  });
  return link;
}

function showingStats () {
  return document.getElementById('columns').classList.contains('show-stats');
}

function renderSummary () {
  summaryGraph.innerHTML = '';
  let showStats = showingStats();
  let plotWidth = showStats ? 600 : 900;

  let engagements = GAME_DATA.commands.filter((d) => {
    return ["ATTACK", "ATTACK_SPECIAL", "GROUND_SPECIAL", "GROUND"].includes(d.action);
  });

  let groupedEngagements = d3.group(engagements, (d) => {
    let [, team] = findPlayer(d.player);
    return team;
  });

  const summaryPlot = Plot.plot({
    width: plotWidth,
    height: 100,
    color: {
      domain: [teamName(GAME_DATA.header.round.team1), teamName(GAME_DATA.header.round.team2)],
      range: ["crimson", "orange"],
      legend: true,
      swatchSize: 10,
      marginLeft: 0,
    },
    x: {
      domain: [0, Math.max(GAME_DATA.commands[GAME_DATA.commands.length-1].time, GAME_DATA.header.game.time_limit)],
      label: "Time remaining",
      ticks: Plot.numberInterval(1800),
      grid: true,
      tickFormat: ticks => {
          let seconds = (GAME_DATA.header.game.time_limit - ticks) / 30;
          const mins = Math.floor(seconds / 60);
          const secs = Math.floor(seconds % 60);
          return `${mins}:${secs.toString().padStart(2, "0")}`;
      }
    },
    y: {
      label: 'Engagements',
      tickFormat: () => '',
      tickSize: 0,
    },
    marks: Array.from(groupedEngagements, ([teamSlug, actions]) => {
      return [
        Plot.line(actions, Plot.binX({
          y: "count",
        }, {
          x: {
            interval: 90,
            value: "time"
          },
          stroke: () => teamName(teamSlug),
          curve: 'step',
        }))
      ];
    })
  });

  summaryGraph.append(summaryPlot);
}

function stripFormat (name) {
  // The private use symbol (often the apple symbol) \uF8FF is sometimes used
  // but isn't displayable in game without interface changes (e.g. JINN) Just strip it
  return name.replace(/[|\\][bip]/i, '').replace(/\uF8FF/g, '');
}

function stripBrackets (name) {
  return name.replace(/\s+\([^)]+\)/i, '');
}

function stripOrder (name) {
  return name.replace(/\s{3,}.*/, '');
}

function selectPlayer (playerEl) {
  document.querySelectorAll('.playerStats__player').forEach((el) => {
    el.classList.remove('playerStats__player--selected');
  });
  let bagradaPlayer = playerEl.dataset.bagrada_player;
  if (FILTERED_PLAYER == bagradaPlayer) {
    FILTERED_PLAYER = null;
  } else {
    FILTERED_PLAYER = bagradaPlayer;
    playerEl.classList.add('playerStats__player--selected');
  }
  renderPlots();
}

document.addEventListener('keydown', (e) => {
  if (FILTERED_PLAYER != null) {
    let listPlayers = document.querySelectorAll('.playerStats__player');
    let selected = document.querySelector('.playerStats__player--selected');
    let index = Array.prototype.indexOf.call(listPlayers, selected);
    if (e.key == 'ArrowDown') {
      e.preventDefault();
      let next = listPlayers[index+1];
      if (next) {
        selectPlayer(next);
      } else {
        selectPlayer(listPlayers[0]);
      }
    } else if (e.key == 'ArrowUp') {
      e.preventDefault();
      let prev = listPlayers[index-1];
      if (prev) {
        selectPlayer(prev);
      } else {
        selectPlayer(listPlayers[listPlayers.length-1]);
      }
    } else if (e.key == 'Enter') {
      e.preventDefault();
      selectPlayer(selected);
    }
  }
});
