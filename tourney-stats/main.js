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
const heatmap = document.getElementById("heatmap");
const playerList = document.getElementById("playerList");
const mediaList = document.getElementById("media");

let BASE_URL = import.meta.env.BASE_URL;
let PAGE_URL = null;

const DATA_VERSION = '2026-07-09';
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

let MAPS_DATA = null;
let YT_DATA = {};
let YT_DATA_PATH_MAP = {};
window.YT_DATA_PATH_MAP = YT_DATA_PATH_MAP;

let GAME_DATA = null;
let PLAYER_GROUPS = null;
let FILTERED_PLAYER = null;
let FILTERED_TEAM = null;
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

const TOURNIES = [{
  slug: 'gos-mwc2013',
  name: 'Myth World Cup 2013',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['DE4', 'Double Elimination 4'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'ulms': ['ULMS', 'Until Last Man Stands'],
    'blades': ['Blades', 'The Blades'],
    'tcox': ['TCox', 'ThunderCox'],
    'dr': ['DR', "Devil's Rejects"],
    'agents': ['Agents', 'Agents'],
    'tmns': ['TMNS', 'Teenage Mutant Ninja Squirters'],
    'tmnt': ['TMNT', 'Teenage Mutant Ninja Turtles'],
    'zomg': ['ZOMG', 'ZOMG'],
    'deer': ['DEER', 'Deer'],
    'wtc': ['WTC', 'Wu Tang Clan'],
  },
}, {
  slug: 'gos-mwc2014',
  name: 'Myth World Cup 2014',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['DE4', 'Double Elimination 4'],
    ['Finals', 'Grand Finals'],
  ],
  teams: {
    'bros': ['Bros', 'The Bros'],
    'fotb': ['FotB', 'Fellowship of the Bling'],
    'gents': ['Gents', 'The Gentlemen'],
    'gents2': ['Gents', 'The Gentlemen', 'gents'],
    'tea': ['Tea', 'Teabaggers'],
    'tea2': ['Tea', 'Teabaggers', 'tea'],
    'ulms': ['ULMS', 'Until Last Man Stands'],
    'ulms2': ['ULMS', 'Until Last Man Stands', 'ulms'],
    'udogs': ['Udogs', 'Underdogs'],
    'udogs2': ['Udogs', 'Underdogs', 'udogs'],
  },
}, {
  slug: 'gos-mwc2015',
  name: 'Myth World Cup 2015',
  rounds: [
    ['QR 1', 'Qualifying Round 1'],
    ['QR 2', 'Qualifying Round 2'],
    ['DE 1', 'Double Elimination 1'],
    ['DE 2', 'Double Elimination 2'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'deer': ['Deer', 'Deer'],
    'mom': ['MoM', 'Masters of Myth'],
    'ncr': ['NCR', 'Namechangers Resurrection'],
    'owls': ['Owls', 'Sociopathic Owls'],
    'rabble': ['Rabble', 'Rabble (NCR/TMNT)'],
    'tmnt2': ['TMNT2', 'Teenage Mutant Ninja Turtles 2'],
  },
}, {
  slug: 'gos-mwc2016',
  name: 'Myth World Cup 2016',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['DE4', 'Double Elimination 4'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'ageha': ['Ageha', 'Ageha'],
    'boom': ['Boom', 'Boom Town'],
    'gom': ['GoM', 'Gods of Myth'],
    'noobs': ['Noobs', 'Noobs Inc'],
    'por': ['PoR', 'Prophets of Rage'],
    'syn': ['Syn', 'The Syndicate'],
    'tinh': ['TINH', 'Team Insert Name Here'],
    'twf': ['TWF', 'The Wight Foundation'],
  },
}, {
  slug: 'gos-mwc2017',
  name: 'Myth World Cup 2017',
  rounds: [
    ['W1', 'Week 1'],
    ['W2', 'Week 2'],
    ['W3', 'Week 3'],
    ['W4', 'Week 4'],
    ['W5', 'Week 5'],
  ],
  teams: {
    'bers': ['BERS', 'Berserkers'],
    'da': ['DA', 'Dragon Army'],
    'lom': ['LoM', 'Legends of Myth'],
    'rofl': ['ROFL', 'ROFLmazzers'],
  }
}, {
  slug: 'gos-mwc2018',
  name: 'Myth World Cup 2018',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    '7l': ['7L', '7th Legion'],
    'bkbk': ['BKBK', "Baron Kildaer's Black Knights"],
    'lh': ['LH', 'Legendary Heterosexuals'],
    'sdm': ['SDM', 'Slong D0ng McKong'],
    'tcl': ['TCL', 'The Casket Lottery'],
    'tgp': ['TGP', 'Team Good Players'],
    'tmnt': ['TMNT', 'Teenage Mutant Ninja Turtles'],
    'np': ['NP', 'Northern Paladins'],
  },
}, {
  slug: 'gos-mwc2019',
  name: 'Myth World Cup 2019',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['Semi Finals', 'Semi Finals'],
    ['Grand Finals', 'Grand Finals'],
    ['Sudden Death', 'Sudden Death'],
  ],
  teams: {
    'nc': ['NC', 'Namechangers'],
    'ftn': ['FTN', 'Fellowship of the Team Name'],
    'moc': ['MoC', 'Murder of Crows'],
    'sb': ['SB', 'Spice Boys'],
  },
}, {
  slug: 'gos-mwc2020',
  name: 'Myth World Cup 2020',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['DE4', 'Double Elimination 4'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'ag': ['AG', 'Avons Grove'],
    'ba': ['BA', 'Business Associates'],
    'deer': ['Deer', '~DEER~'],
    'faf': ['FaF', 'Free Agent Freedom'],
    'gagt': ['GAGT', 'Good Ass Guys Team'],
    'hots': ['HOTS', 'HOTSquad'],
    'sb': ['SB', 'Spice Boiz II Men'],
    'mm': ['MM', 'The Mystery Men'],
  },
}, {
  slug: 'gos-mwc2021',
  name: 'Myth World Cup 2021',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['QR4', 'Qualifying Round 4'],
    ['QR5', 'Qualifying Round 5'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['TBF', 'Top Bracket Finals'],
    ['BBSF', 'Bottom Bracket Semis'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'kotet': ['KOTET', 'The Knights of the Elliptical Table'],
    'sm': ['SM', 'Sparkle Motion'],
    'b4': ['B4', 'Bridge Four'],
    'ic': ['IC', 'Team Icecream'],
    'ag': ['AG', 'Avons Grove'],
    'dc': ['DC', 'The Dunshire Coneheads'],
  },
}, {
  slug: 'gos-mwc2022',
  name: 'Myth World Cup 2022',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'ag': ['AG', 'Avons Grove'],
    'mit': ['MiT', 'Men in Tights'],
    'rsc': ['RSC', 'Rat Sized Cats'],
    'sm': ['SM', 'Save Myth'],
  },
}, {
  slug: 'gos-mwc2023',
  name: 'Myth World Cup 2023',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'ag': ['AG', 'Avons Grove'],
    'mitt': ['MiTT', 'Men in Tighter Tights'],
    'rsc': ['RSC', 'Rat Sized Cats'],
    'sm': ['SM', 'Save MWC WITH CAPS LOCK'],
    'tjn': ['TJN', 'The JuggerNots'],
  },
}, {
  slug: 'gos-mwc2024',
  name: 'Myth World Cup 2024',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'ag': ['AG', 'Avons Grove'],
    'miit': ['MIIT', 'The Men In Impeccably Immaculate Tights'],
    'miit2': ['MIIT', 'The Men In Impeccably Immaculate Tights', 'miit'],
    'miit3': ['MIIT', 'The Men In Impeccably Immaculate Tights', 'miit'],
    'bmlm': ['BMLM', 'Boys? More Like Men'],
    'tl': ['TL', 'Treasure Island'],
    'tmf': ['TMF', 'The Myth-Fits'],
    'man': ['MAN', 'The Big Manbowski'],
    'man2': ['MAN', 'The Big Manbowski', 'man'],
    'man3': ['MAN', 'The Big Manbowski', 'man'],
  },
}, {
  slug: '7-mwc25',
  name: 'Myth World Cup 2025',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'ag': ['AG', "Avon's Grove"],
    'd&t': ['D&T', "Death & Taxes"],
    'ma': ['MA', "Marmotas Assassinas"],
    'mit': ['MiT', "Men in Tights"],
    'pk': ['PK', "Peacekeepers"],
    'spy kids': ['SK', "Spy Kids"],
    'tmf': ['TMF', "The Myth-Fits"],
    'z snake': ['ZS', "Z Snake"],
  },
}, {
  slug: '9-smo25',
  name: "'smo draft tournament 2025",
  rounds: [
    ['Round 1', 'Round 1'],
    ['Round 2', 'Round 2'],
    ['Round 3', 'Round 3'],
    ['SE', 'Single Elimination'],
    ['Finals', 'Finals'],
  ],
  teams: {
    'asmo': ['Asmo', 'Asmodian'],
    'dantski': ['Dant', 'Dantski'],
    'homer': ['Homer', 'Homer'],
    'akira': ['Akira', 'Akira'],
  },
}, {
  slug: '13-mwc26',
  name: 'Myth World Cup 2026',
  rounds: [
    ['QR1', 'Qualifying Round 1'],
    ['QR2', 'Qualifying Round 2'],
    ['QR3', 'Qualifying Round 3'],
    ['QR4', 'Qualifying Round 4'],
    ['DE1', 'Double Elimination 1'],
    ['DE2', 'Double Elimination 2'],
    ['DE3', 'Double Elimination 3'],
    ['BB Finals', 'Bottom Bracket Finals'],
    ['Grand Finals', 'Grand Finals'],
  ],
  teams: {
    'ag': ['AG', "Avon's Grove"],
    'v3': ['V3', "Veni Vidi Vici"],
    'v32': ['V3', "Veni Vidi Vici", "v3"],
    '4c': ['4C', "Canadian Calisthenic Club for Casuals"],
    '4c2': ['4C', "Canadian Calisthenic Club for Casuals", "4c"],
    'cum': ['CUM', "Company of Unvanquished Mauls"],
    'cum2': ['CUM', "Company of Unvanquished Mauls", "cum"],
    'ti': ['TI', "Treasure Island"],
    'tmf': ['TMF', "The Myth-Fits"],
    'tmf2': ['TMF', "The Myth-Fits", "tmf"],
  },
}];

const ROUTES = {
  game: /^tournament\/([^/]+)\/rounds\/([^/]+)\/games\/([^/]+)/,
  round_stats: /^tournament\/([^/]+)\/rounds\/([^/]+)\/stats/,
  player: /^tournament\/([^/]+)\/players\/([^/]+)/,
  team: /^tournament\/([^/]+)\/teams\/([^/]+)/,
  round: /^tournament\/([^/]+)\/rounds\/([^/]+)/,
  tournament_stats: /^tournament\/([^/]+)\/stats/,
  tournament_all: /^tournament\/([^/]+)\/all/,
  tournament: /^tournament\/([^/]+)/,
  maps: /^maps/,
  info: /^info/,
  home: /^tournament/,
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
    // let oldParsed = parseUrl(PAGE_URL);
    // if (!oldParsed || ROUTE_NAME != routeName || TOURNEY_ID != routeMatch[1]) {
    //   hard = true;
    // }
    hard = true;
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

  TOURNIES.forEach(({slug, rounds, teams}) => {
    if (TOURNEY_ID == slug) {
      ROUND_MAP = new Map(rounds);
      TEAM_MAP = teams;
    }
  });

  if (GAME_ID) {
    renderGame();
  } else if (ROUND_ID) {
    renderRound();
  } else if (TOURNEY_ID) {
    renderTournament();
  } else if (ROUTE_NAME == 'info') {
    renderInfo();
  } else if (ROUTE_NAME == 'maps') {
    renderMaps(window.location.hash.slice(1));
  } else if (ROUTE_NAME == 'home') {
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
function renderMapsTitle () {
  let title = "Myth Stats: Maps";
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
  MAPS_DATA = null;
  ROUND_MAP = null;
  TEAM_MAP = null;
  PROCESSED_ROUNDS = null;

  ROUND_DATA = null;

  GAME_DATA = null;
  PLAYER_GROUPS = null;
  FILTERED_PLAYER = null;
  FILTERED_TEAM = null;
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
  heatmap.innerHTML = '';
  clickGraph.innerHTML = '';
  graphFilter.innerHTML = '';
  actionLegend.innerHTML = '';

  mediaList.innerHTML = '';
}

function renderInfo () {
  renderInfoTitle();
  renderInfoInfo();
  document.body.classList.add('show-info');
}

async function renderMaps (hashSlug) {
  const response = await fetch(`${BASE_URL}maps.json?v=${DATA_VERSION}`);
  MAPS_DATA = JSON.parse(await response.text());
  window.MAPS_DATA = MAPS_DATA;

  renderMapsTitle();
  renderMapsInfo();
  renderMapsList(hashSlug);
}

function renderHome () {
  renderHomeTitle();
  renderHomeInfo();
  renderHomeTourneys();
}

async function renderTournament() {
  const response = await fetch(`${BASE_URL}tournament/${TOURNEY_ID}/info.json?v=${DATA_VERSION}`);
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
  } else if (ROUTE_NAME == 'tournament_all') {
    renderTournamentTitle();
    renderTournamentInfo();
    renderTournamentRoundsAll();
  } else {
    renderTournamentTitle();
    renderTournamentInfo();
    renderTournamentRounds();
  }
}

async function renderRound () {
  const response = await fetch(`${BASE_URL}tournament/${TOURNEY_ID}/rounds/${ROUND_ID}/info.json?v=${DATA_VERSION}`);
  ROUND_DATA = JSON.parse(await response.text());
  window.ROUND_DATA = ROUND_DATA;

  processRounds();
  renderRoundTitle();
  renderRoundHead(ROUND_DATA);
  renderRoundInfo(ROUND_DATA, subtitleHead);
  if (ROUTE_NAME == 'round_stats') {
    console.log('round stats');
  } else {
    renderRoundContents(ROUND_DATA, roundContainer);
    renderRoundMedia(ROUND_DATA)
  }
}

function ytLink (video, seenIds) {
  const vidMeta = YT_DATA[video.yt_id].meta;
  const vidLink = dce('a', 'mediaLink');
  vidLink.target = '_blank';
  let ytUrl = `https://www.youtube.com/watch?v=${video.yt_id}`;
  if (video.details.ts) {
    ytUrl += `&t=${video.details.ts}s`;
  }
  vidLink.href = ytUrl;

  const vid = dce('img', 'mediaVideo');
  vid.src = `https://img.youtube.com/vi/${video.yt_id}/mqdefault.jpg`
  vid.width = 80;
  vid.height = 45;
  vidLink.append(vid);

  const vidChannel = dce('span', 'mediaChannel', `▶️ YouTube: ${vidMeta.channel}`);
  vidLink.append(vidChannel);
  const vidTitle = dce('span', 'mediaTitle', vidMeta.title);
  vidLink.append(vidTitle);

  if (video.details.game_num) {
    const vidGameNum = dce('span', 'mediaGameNum', ` - Game: ${video.details.game_num}`);
    vidChannel.append(vidGameNum);
    seenIds[video.yt_id] = vidGameNum;
  } else {
    seenIds[video.yt_id] = true;
  }
  return vidLink;
}

function renderRoundMedia (round, gameNum) {
  if (round.round_path in YT_DATA_PATH_MAP) {
    const roundVids = YT_DATA_PATH_MAP[round.round_path].sort((a, b) => {
      if (a.details.game_num && b.details.game_num) {
        return a.details.game_num - b.details.game_num;
      } else if (a.details.game_num) {
        return 0;
      } else {
        return -1;
      }
    });
    const seenIds = {};
    roundVids.forEach(video => {
      if (gameNum && video.details.game_num && gameNum != video.details.game_num) {
        return;
      }
      if (video.yt_id in seenIds) {
        if (seenIds[video.yt_id] !== true) {
          if (video.details.game_num) {
            const vidGameNum = seenIds[video.yt_id];
            vidGameNum.append(`, ${video.details.game_num}`);
            vidGameNum.innerText = vidGameNum.innerText.replace(/Game:/, 'Games:');
          }
        }
      } else {
        const vidLink = ytLink(video, seenIds);
        mediaList.append(vidLink);
      }
    });
    if (Object.keys(seenIds).length) {
      mediaList.prepend(dce('h2', 'mediaCoverage', 'Coverage'));
    }
  }
}

function renderTournamentMedia (tournament) {
  if (tournament.path in YT_DATA_PATH_MAP) {
    const seenIds = {};
    YT_DATA_PATH_MAP[tournament.path].forEach(video => {
      if (!(video.yt_id in seenIds)) {
        const vidLink = ytLink(video, seenIds);
        mediaList.append(vidLink);
      }
    });
    if (Object.keys(seenIds).length) {
      mediaList.prepend(dce('h2', 'mediaCoverage', 'Coverage'));
    }
  }
}

async function renderGame () {
  const response = await fetch(`${BASE_URL}tournament/${TOURNEY_ID}/rounds/${ROUND_ID}/games/${GAME_ID}/stats.json?v=${DATA_VERSION}`);
  try {
    GAME_DATA = JSON.parse(await response.text());
  } catch {
    history.pushState({}, "", `${BASE_URL}tournament/${TOURNEY_ID}/rounds/${ROUND_ID}`);
    return routeUrl();
  }
  window.GAME_DATA = GAME_DATA;
  UNIT_FILTER = null;

  PLAYER_GROUPS = d3.group(GAME_DATA.commands, (d) => {
    let [player, ] = findPlayer(d.player);
    return player.metaserver_player;
  });

  processGames();
  renderGameTitle();
  renderPlayerList();
  renderGames();
  renderPlots();
  renderUnitFilter();
  renderGameInfo();
  renderSummary();
  renderHeatmap();
  renderRoundMedia(GAME_DATA.header.round, GAME_DATA.header.game.game_num);
}

function metaserverLink (info = {}) {
  let link = dce('a');
  link.target = '_blank';
  if (info.gos || (info.tourney && info.tourney.metaserver == 'gos')) {
    link.textContent = 'gateofstorms.net';
    if (info.round && info.game) {
      link.href = `http://gateofstorms.net/tournaments/${info.tourney.metaserver_tournament}/rounds/${info.round}/games/${info.game}`;
    } else if (info.player) {
      link.href = `http://gateofstorms.net/users/${info.player}`;
    } else if (info.round) {
      link.href = `http://gateofstorms.net/tournaments/${info.tourney.metaserver_tournament}/rounds/${info.round}`;
    } else if (info.tourney) {
      link.href = `http://gateofstorms.net/tournaments/${info.tourney.metaserver_tournament}`;
    } else {
      link.href = `http://gateofstorms.net/tournaments`;
    }
  } else {
    link.textContent = 'bagrada.net';
    if (info.game) {
      link.href = `https://bagrada.net/webui/games/${info.game}`;
    } else if (info.player) {
      link.href = `https://bagrada.net/webui/users/${info.player}`;
    } else if (info.tourney && info.round) {
      link.href = `https://bagrada.net/webui/tournaments/${info.tourney.metaserver_tournament}/rounds/${info.round}`;
    } else if (info.tourney) {
      link.href = `https://bagrada.net/webui/tournaments/${info.tourney.metaserver_tournament}`;
    } else {
      link.href = `https://bagrada.net/webui/tournaments`;
    }
  }
  return link;
}

function renderInfoInfo () {
  titleHead.textContent = 'Myth Stats / Info';

  captionHead.appendChild(metaserverLink());
  captionHead.append(' / ');
  captionHead.appendChild(metaserverLink({'gos': true}));
  captionHead.append(' / ');
  captionHead.append(stateLink('', 'home'));
  captionHead.append(' / ');
  captionHead.append(stateLink('maps', 'maps'));
}

function renderMapsInfo () {
  titleHead.textContent = 'Myth Stats / Maps';

  captionHead.appendChild(metaserverLink());
  captionHead.append(' / ');
  captionHead.appendChild(metaserverLink({'gos': true}));
  captionHead.append(' / ');
  captionHead.append(stateLink('', 'home'));
}

function renderHomeInfo () {
  titleHead.textContent = 'Myth Stats / Tournaments';

  captionHead.appendChild(metaserverLink());
  captionHead.append(' / ');
  captionHead.appendChild(metaserverLink({'gos': true}));
  captionHead.append(' / ');
  captionHead.append(stateLink('maps', 'maps'));
}

function renderHomeTourneys () {
  let tournamentLinks = dce('div', 'tournamentLinks');
  for (let i = TOURNIES.length - 1; i >= 0; i--) {
    const {slug, name} = TOURNIES[i];
    tournamentLinks.appendChild(
      stateLink(`tournament/${slug}`, name, 'tournamentLink')
    );
  }
  tournamentContainer.append(tournamentLinks);
}

function normaliseShortName (shortName) {
  return shortName.replace(/mwc|MWC20|MWC 20/, 'MWC').toUpperCase();
}

const LIGATURES = {
    'æ': 'ae', 'Æ': 'AE',
    'œ': 'oe', 'Œ': 'OE',
    'ß': 'ss',
    'ð': 'd',  'Ð': 'D',
    'þ': 'th', 'Þ': 'Th',
    'ł': 'l',  'Ł': 'L',
    'ĳ': 'ij', 'Ĳ': 'IJ',
}
function slugify(name) {
  // Strip myth formatting
  name = stripFormat(name);
  // Note this is different to the python side, which removes the bracketed text
  // don't try to reconstruct slugs created there for matching
  // Strip brackets
  name = name.replace(/[()]/g, "");
  // Lowercase and replace ligatures
  name = [...name.toLowerCase()].map(c => LIGATURES[c] ?? c).join("");
  // Normalize and convert accented chars to ASCII
  name = name.normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
  // Replace non-word characters with dashes
  name = name.replace(/[^\w\s-]/g, "");
  // Replace spaces and underscores with a single dash
  name = name.trim().replace(/[\s_]+/g, "-");
  // Collapse multiple dashes into one
  name = name.replace(/-{2,}/g, "-");
  // Strip leading/trailing dashes
  name = name.replace(/^-+|-+$/g, "");
  return name;
}

function slugifyMapGt (game) {
  let typeSlug = slugify(game.game_type)
  let mapSlug = slugify(game.map_name);
  return `${typeSlug}-${mapSlug}`;
}
function hashGameMatch (hashSlug, game) {
  let slug = slugifyMapGt(game);
  return hashSlug == slug;
}

function renderMapsList (hashSlug) {
  let mapList = dce('ol', 'mapList');
  
  let opts = {
    // groupByMap: true,
    showGames: true,
    showTrades: true,
  };

  let scrollTo;

  if (opts.groupByMap) {
    Object.values(MAPS_DATA).sort((a, b) => b.count - a.count).forEach(mapInfo => {
      const withGameType = [];
      Object.values(mapInfo['game_types']).forEach(games => {
        withGameType.push(games);
      });
      withGameType.sort((a, b) => b.length - a.length).forEach(games => {
        let mapEntry = renderMapsListEntry(games, opts);
        if (hashGameMatch(hashSlug, games[0].game)) {
          scrollTo = mapEntry;
        }
        mapList.appendChild(mapEntry);
      });
    });
  } else {
    const withGameType = [];
    Object.values(MAPS_DATA).forEach(mapInfo => {
      Object.values(mapInfo['game_types']).forEach(games => {
        withGameType.push(games);
      });
    });
    withGameType.sort((a, b) => b.length - a.length).forEach(games => {
      let mapEntry = renderMapsListEntry(games, opts);
      if (hashGameMatch(hashSlug, games[0].game)) {
        scrollTo = mapEntry;
      }
      mapList.appendChild(mapEntry);
    });
  }
  tournamentContainer.appendChild(mapList);
  if (scrollTo) {
    scrollTo.scrollIntoView();
  } else if (hashSlug) {
    tournamentContainer.prepend(dce('div', 'warningMessage', 'Map not found'));
  }
}

function renderMapsListEntry (games, opts) {
  let mapEntry = dce('li', 'mapList__entry');

  let mapItem = dce('span', 'mapList__item');
  let gameType = dce('span', 'mapList__type', games[0].game.game_type);
  let gameInfo = dce('div', 'mapList__info');
  gameInfo.append(gameType);

  let gameCount = dce('span', 'mapList__badge gameList__badge', games.length)
  gameInfo.prepend(' ');
  gameInfo.prepend(gameCount);

  let gameMap = dce('div', 'mapList__map', stripFormat(games[0].game.map_name));

  let overheadDiv = dce('div', 'mapList__overhead');
  let overheadMap = dce('img', 'mapList__overhead_img');
  overheadMap.src = `${BASE_URL}${games[0].game.overhead_path}`;
  overheadDiv.appendChild(overheadMap)
  mapItem.appendChild(overheadDiv);

  mapItem.appendChild(gameInfo);
  mapItem.appendChild(gameMap);

  if (opts.showGames) {
    let mapGameInfo = renderMapListGames(games, opts);
    mapItem.append(mapGameInfo);
  }

  mapEntry.appendChild(mapItem);

  return mapEntry;
}

function renderMapListGames (games, opts) {
  let mapGameInfo = dce('div', 'mapList__gameList');
  let lastShort;
  games.sort((a, b) => {
    return normaliseShortName(b.tournament.short_name).localeCompare(normaliseShortName(a.tournament.short_name));
  }).forEach(game => {
    let mapGameItem = dce('div', 'mapList__gameListItem');

    let tourneyShort = normaliseShortName(game.tournament.short_name);
    let gameName = `${tourneyShort}: ${game.round.round_name} - ${game.game.game_num}/${game.round.num_games}`;
    let gameLink = stateLink(game.game.game_path, gameName, 'mapList__gameLink');
    tooltip(gameLink, `${game.tournament.name}: ${game.round.round_name} - Game ${game.game.game_num} of ${game.round.num_games} (${Math.round(game.game.time_limit/30/60)} mins)`);
    mapGameItem.append(gameLink);
    if (game.round.round_path in YT_DATA_PATH_MAP) {
      const coverage = dce('span', 'mapList__coverageIcon', '▶️ ');
      tooltip(coverage, `Covered by: ${coverageChannels(game.round.round_path).join(', ')}`);
      mapGameItem.prepend(coverage);
    }

    if (opts.showTrades) {
      for (let [teamSlug, team] of Object.entries(game.teams)) {
        let result = 'Lost';
        if (team.winner || team.allied_winner) {
          result = 'Won'
        } else if (team.tied_winner) {
          result = 'Tied'
        }
        let mapGameTrade = dce('div', 'mapList__trade', summarizeAllocation(team.trade));
        let mapGameTeam = dce('span', 'mapList__badge', teamNameShort(teamSlug, game.tournament.slug));
        if (game.game.tie) {
          mapGameTeam.classList.add('mapList__badge--tie');
        } else {
          if (team.winner || team.allied_winner) {
            mapGameTeam.classList.add('mapList__badge--winner');
          } else {
            mapGameTeam.classList.add('mapList__badge--loser');
          }
        }
        mapGameTrade.prepend(mapGameTeam);
        tooltip(mapGameTrade, `${result}: ${teamName(teamSlug, game.tournament.slug)} (Captain: ${stripFormat(stripOrder(team.captain.name))})`);
        mapGameItem.append(mapGameTrade);
      }
    }

    if (lastShort && lastShort != tourneyShort) {
      mapGameInfo.append(dce('hr', 'mapList__gameListDivider'));
    }
    lastShort = tourneyShort;

    mapGameInfo.append(mapGameItem);
  });
  return mapGameInfo;
}

function renderTournamentInfo () {
  titleHead.textContent = ` / ${TOURNEY_DATA.name}`;
  let allTourney = stateLink('tournament/', 'Tournaments');
  titleHead.prepend(allTourney);

  captionHead.appendChild(metaserverLink({tourney: TOURNEY_DATA}));


  if (ROUTE_NAME == 'tournament_all') {
    captionHead.append(' / ');
    captionHead.append(stateLink(TOURNEY_DATA.path, 'summary'));
  } else {
    captionHead.append(' / ');
    captionHead.append(stateLink(TOURNEY_DATA.path + '/all', 'all games'));
  }

  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'tournament stats'));
}
function renderTournamentTeamInfo () {
  titleHead.textContent = ` / `;
  let tourneyLink = stateLink(TOURNEY_DATA.path, TOURNEY_DATA.name);
  titleHead.prepend(tourneyLink);
  titleHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'Stats'));
  titleHead.append(' / Team Stats');

  captionHead.appendChild(metaserverLink({tourney: TOURNEY_DATA}));
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'tournament stats'));
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path, 'results'));
}
function renderTournamentPlayerInfo () {
  titleHead.textContent = ` / `;
  let tourneyLink = stateLink(TOURNEY_DATA.path, TOURNEY_DATA.name);
  titleHead.prepend(tourneyLink);
  titleHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'Stats'));
  titleHead.append(' / Player Stats');

  captionHead.appendChild(metaserverLink({tourney: TOURNEY_DATA, player: PLAYER_ID}));
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path + '/stats', 'tournament stats'));
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path, 'results'));
}
function renderTournamentStatsInfo () {
  titleHead.textContent = ' / Stats';
  let tourneyLink = stateLink(TOURNEY_DATA.path, TOURNEY_DATA.name);
  titleHead.prepend(tourneyLink);

  captionHead.appendChild(metaserverLink({tourney: TOURNEY_DATA}));
  captionHead.append(' / ');
  captionHead.append(stateLink(TOURNEY_DATA.path, 'results'));
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
      'game_ties': 0,
      'round_wins': 0,
      'round_losses': 0,
      'round_ties': 0,
      'points': 0,
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
      if (!g.teams) {
        return;
      }
      for (let [origTeamSlug, team] of Object.entries(g.teams)) {
        let teamSlug = teamSlugMap(origTeamSlug);
        if (!teamFilter || teamFilter == teamSlug) {
          for (let [metaserver_player, player] of Object.entries(team.players)) {
            if (player.stats.actions) {
              if (!(metaserver_player in playerData)) {
                playerData[metaserver_player] = {
                  names: [],
                  colors: [],
                  teams: [],
                };
              }
              playerData[metaserver_player].names.push(player.name);
              playerData[metaserver_player].colors.push(player.color[0]);
              playerData[metaserver_player].teams.push(teamSlug);
              let stats = Object.assign({}, player.stats, {
                'medals': player.medals.filter(m => m != 'actions').length,
                'captains': player.captain ? 1 : 0,
              });
              incrementStats(teamStats, teamSlug, stats);
              let playerStat = incrementStats(playerStats, metaserver_player, stats);
              if (player.stats.actions_engage) {
                if (team.winner || team.allied_winner) {
                  playerStat.game_wins += 1;
                } else if (g.tie) {
                  playerStat.game_ties += 1;
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
          if (origTeamSlug == teamSlug) {
            if (team.winner || team.allied_winner) {
              teamStat.game_wins += 1;
              teamStat.points += 3;
            } else if (g.tie) {
              teamStat.game_ties += 1;
              teamStat.points += 1;
            } else {
              teamStat.game_losses += 1;
            }
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
            if (origTeamSlug == teamSlug) {
              teamStat.games += 1;
            }
          }
        }
      }
    });
    if (r.games.length) {
      let team1 = initStats(teamStats, r.team1);
      team1.rounds += 1;
      if (r.team1 == r.round_winner) {
        team1.round_wins += 1;
      } else if (r.round_winner) {
        team1.round_losses += 1;
      } else {
        team1.round_ties += 1;
      }
      let team2 = initStats(teamStats, r.team2);
      team2.rounds += 1;
      if (r.team2 == r.round_winner) {
        team2.round_wins += 1;
      } else if (r.round_winner) {
        team2.round_losses += 1;
      } else {
        team2.round_ties += 1;
      }

    }
  });
  let overallTeamStats = [];
  for (let [team, stats] of Object.entries(teamStats)) {
    if (!teamFilter || teamFilter == team) {
      let teamLink = dce('span', null, teamNameShort(team));
      if (!teamFilter) {
        teamLink = stateLink(
          `tournament/${TOURNEY_ID}/teams/${team}`,
          teamNameShort(team)
        );
      }
      teamLink.title = teamName(team);
      overallTeamStats.push({
        Team: teamLink,

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
        'Games\nTied': stats.game_ties,
        'Points\n ': stats.points,
        'Rounds\nPlayed': stats.rounds,
        'Round\nVictories': stats.round_wins,
        'Round\nDefeats': stats.round_losses,
        'Round\nTies': stats.round_ties,
        '🎖️ Medals': stats.medals + Math.max(0, stats.round_wins - stats.round_losses) + Math.max(0, stats.game_wins - stats.game_losses),
      });
    }
  }
  let overallPlayerStats = [];
  const ranked = [];
  for (let [playerId, stats] of Object.entries(playerStats)) {
    augmentMedals(stats);
    ranked.push([playerId, stats.medals]);
  };
  ranked.sort((a, b) => {
    return b[1] - a[1];
  });
  const rankLookup = {};
  ranked.forEach(([playerId, ], i) => {
    rankLookup[playerId] = i;
  });

  for (let [playerId, stats] of Object.entries(playerStats)) {
    let player = playerData[playerId];
    let teamSlug = avgMode(player.teams);
    let playerColor = avgMode(player.colors);


    let playerLink = stateLink(
      `tournament/${TOURNEY_ID}/players/${playerId}`,
      stripFormat(stripOrder(avgMode(player.names)))
    );

    if (!teamFilter) {
      const rank = pos2Rank(rankLookup[playerId], ranked.length, stats.medals);
      const rankIcon = dce('span', 'rankIcon');
      rankIcon.style.backgroundImage = `url(${BASE_URL}img/rank/${rank}.png)`;
      playerLink.prepend(rankIcon);
      tooltip(rankIcon, RANK_NAMES[rank]);
    }

    playerLink.style.borderLeft = `8px solid ${playerColor}`;
    let teamLink = teamNameShort(avgMode(player.teams));
    if (!teamFilter) {
      teamLink = stateLink(
        `tournament/${TOURNEY_ID}/teams/${teamSlug}`,
        teamNameShort(avgMode(player.teams))
      );
    }
    overallPlayerStats.push(Object.assign({
      Team: teamLink,
      Player: playerLink,
    }, aggregatePlayerStats(stats)));
  }

  if (!PLAYER_ID) {
    let teamStatHeading = 'Team Stats';
    if (teamFilter) {
      teamStatHeading = `Team Stats: ${teamName(teamFilter)}`;
    }
    tournamentContainer.append(dce('h3', '', teamStatHeading));
    let teamTable = makeTable(
      Object.keys(overallTeamStats[0]),
      overallTeamStats.map(s => Object.values(s)),
      ['string'],
      'teamDataTable',
      STAT_TOOLTIPS,
    );
    tournamentContainer.append(teamTable);
    teamTable.querySelector('td.dataTableHead__Points_').click();
  }

  if (!teamFilter) {
    tournamentContainer.append(dce('h3', '', 'Player Stats'));
  }
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

const RANK_NAMES = [
  "Dagger",
  "Double Dagger", // Dagger with Hilt
  "Triple Dagger", // Kris Knife
  "Sword and Dagger",
  "Crossed Swords",
  "Crossed Axes",
  "Shield",
  "Shield Crossed Swords",
  "Shield Crossed Axes",
  "Prince", // Simple Crown
  "Lord", // Crown
  "Emperor", // Nice Crown
  "Crescent Moon", // Eclipsed Moon
  "Moon",
  "Eclipse", // Eclipsed Sun
  "Sun",
  "Comet",
];
const RANK_PERCENTAGES = [
  0.01,
  0.03,
  0.07,
  0.13,
  0.21,
  0.31,
  0.43,
  0.57,
  0.73,
];

function pos2Rank (pos, total, medals) {
  // Celestials
  if (pos == 0) {
    return 16;
  } else if (pos == 1) {
    return 15;
  } else if (pos == 2) {
    return 14;
  } else if (pos == 3) {
    return 13;
  } else if (pos == 4) {
    return 12;
  }
  // Plebs
  const numRanks = RANK_PERCENTAGES.length;
  for (let i = 0; i < numRanks; i++) {
    let pc = (pos - 5) / (total - 5);
    // debugger;
    if (pc < RANK_PERCENTAGES[i]) {
      return (numRanks - i) + 2;
    }
  }
  // Noobs
  if (medals < 1) {
    return 0;
  }
  if (medals < 2) {
    return 1;
  }
  return 2;
}

function makeTable (headers, values, types, className, tooltips) {
  let table = dce('table', 'dataTable');
  if (className) {
    table.classList.add(className);
  }
  let thead = dce('thead');
  let theadRow = dce('tr');
  theadRow.append(dce('td', 'dataTablePos'));
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
  values.forEach((row, i) => {
    let valueRow = dce('tr');
    valueRow.append(dce('td', 'dataTablePos', i+1));
    row.forEach((v, rowI) => {
      if (v && (!types || !types[rowI] || !types[rowI] == 'number')) {
        v = v.toLocaleString();
      }
      let valueCell = dce('td', `dataTable__${tableClass(headers[rowI])}`);
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
        const cellA = a.children[colIndex+1].textContent.trim();
        const cellB = b.children[colIndex+1].textContent.trim();
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

      rows.forEach((row, i) => {
        row.querySelector('.dataTablePos').textContent = i + 1;
        tbody.appendChild(row)
      }); // Reorder rows
    });
  });

}

function avgMean (arr) {
  return arr.reduce((a, b) => a + b) / arr.length;
}

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

function tourneyTeams (tourneySlug) {
  let tourney = TOURNIES.find(t => t.slug == tourneySlug);
  if (tourney) {
    return tourney.teams;
  }
}

function teamName (name, tourneySlug) {
  let map = tourneySlug ? tourneyTeams(tourneySlug) : TEAM_MAP;
  return map ? map[name.toLowerCase()][1] : name;
}
function teamNameShort (name, tourneySlug) {
  let map = tourneySlug ? tourneyTeams(tourneySlug) : TEAM_MAP;
  return map ? map[name.toLowerCase()][0] : name;
}
function teamSlugMap (slug, tourneySlug) {
  let map = tourneySlug ? tourneyTeams(tourneySlug) : TEAM_MAP;
  return map ? map[slug][2] || slug : slug;
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
    'Games\nTied': stats.game_ties,
    '🔹 Cap': stats.captains,
    '🎖️ Medals': stats.medals,
  };
}

function renderPlayerStats (metaserver_player) {
  let playerStats = {};
  let playerData = {
    names: [],
    colors: [],
    teams: [],
  };
  TOURNEY_DATA.rounds.forEach(r => {
    r.games.forEach(g => {
      if (!g.teams) {
        return;
      }
      for (let [teamSlug, team] of Object.entries(g.teams)) {
        let player = team.players[metaserver_player];
        if (player && player.stats.actions) {
          playerData.names.push(player.name);
          playerData.colors.push(player.color[0]);
          playerData.teams.push(teamSlug);
          let stats = Object.assign({}, player.stats, {
            'medals': player.medals.filter(m => m != 'actions').length,
            'captains': player.captain ? 1 : 0,
          });
          let playerStat = incrementStats(playerStats, metaserver_player, stats);
          if (player.stats.actions_engage) {
            if ((team.winner || team.allied_winner) && player.stats.actions_engage) {
              playerStat.game_wins += 1;
            } else if (g.tie) {
              playerStat.game_ties += 1;
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
  let stats = playerStats[metaserver_player];
  augmentMedals(stats);
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

function augmentMedals (stats) {
  stats.medals = stats.medals + Math.max(0, stats.game_wins - stats.game_losses);
}

function renderPlayerGraph (stats, stat, label, title) {
  let graph = Plot.plot({
    width: 1200,
    height: 80,
    marginBottom: 10,
    className: 'playerGraph__plot',
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
          return `${stats.round_data[i].round_name}: Game ${stats.game_data[i].game_num}\n${stats.game_data[i].game_type}\n${stripFormat(stats.game_data[i].map_name)}\n${label}: ${d[stat]}`
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

function renderTournamentRoundsAll () {
  tournamentContainer.innerHTML = '';
  if (!TOURNEY_DATA.rounds || !TOURNEY_DATA.rounds.length) {
    return;
  }
  if (ROUND_MAP && PROCESSED_ROUNDS) {
    let groupedRoundContainer = dce('div', 'tournamentAllRounds');
    for (const [roundStage, ] of ROUND_MAP) {
      let roundContainer = dce('div', 'tournamentAllRounds__stage');

      let roundList = dce('div', 'tournamentAllRounds__list');

      let hasRounds = false;
      PROCESSED_ROUNDS[roundStage].forEach(round => {
        hasRounds = true;
        const subtitleHead = dce('h2', 'subtitle');
        renderRoundInfo(round, subtitleHead, true);
        const roundContainer = dce('div', 'tournamentAllRounds__round');
        renderRoundContents(round, roundContainer);
        roundList.append(subtitleHead);
        roundList.append(roundContainer);
      });

      if (hasRounds) {
        roundContainer.appendChild(roundList);
        groupedRoundContainer.appendChild(roundContainer);
      }
    }
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
  renderTournamentMedia(TOURNEY_DATA);
}

function renderRounds (rounds, teamFilter) {
  let groupedRoundContainer = dce('div', 'tournamentGroupedRounds');
  for (const [roundStage, roundStageFull] of ROUND_MAP) {
    let roundContainer = dce('div', 'tournamentGroupedRounds__group');

    let roundHead = dce('h4', 'tournamentGroupedRounds__head', roundStageFull);

    let roundList = dce('ul', 'tournamentGroupedRounds__rounds');
    let hasRounds = false;
    rounds[roundStage].forEach(round => {
      if (!teamFilter || round.team1 == teamFilter || round.team2 == teamFilter) {
        hasRounds = true;
        let roundItem = dce('li', 'tournamentGroupedRounds__round');

        let suffixText = '';
        if (round.part != null) {
          suffixText += ` (${round.part})`;
        }
        let vs = 'vs';
        let coverage = '';
        if (round.round_path in YT_DATA_PATH_MAP) {
          vs = '▶️';
          coverage = `\n▶️ Covered by: ${coverageChannels(round.round_path).join(', ')}`;
        }
        let roundLink = stateLink(round.round_path, ` ${vs} `);
        tooltip(roundLink, `${roundStage}: ${teamName(round.team1)} vs ${teamName(round.team2)}${suffixText}${coverage}`);
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

        let ties = 0;
        if (round.games.length) {
          let roundGameLinks = dce('div',  'tournamentGroupedRounds__games');
          round.games.forEach(game => {
            let roundGameLink = stateLink(game.game_path, game.game_num);
            let sd = game.sudden_death ? 'Sudden Death: ' : '';
            
            let tt = tooltip(roundGameLink);
            let overhead = dce('img', 'tooltipOverhead');
            overhead.src = `${BASE_URL}${game.overhead_path}`;
            let ttContent = dce('span', 'tooltipContent', `${game.game_num}. ${sd}${game.game_type}\n${stripFormat(game.map_name)}`);
            tt.append(overhead);
            if (game.winning_team) {
              ttContent.append(dce('p', 'tooltipPara', `Winner: ${teamNameShort(game.winning_team)}`));
            } else if (game.tie) {
              ttContent.append(dce('p', 'tooltipPara', 'Tie'));
            }
            tt.append(ttContent);

            roundGameLink.className = 'tournamentGroupedRounds__game';
            if (round.games.length > 7) {
              roundGameLink.classList.add('tournamentGroupedRounds__game--wrap');
            }
            if (game.tie) {
              ties++;
              roundGameLink.classList.add('tournamentGroupedRounds__game--tie');
            } else {
              if ((teamFilter || round.round_winner) == game.winning_team) {
                roundGameLink.classList.add('tournamentGroupedRounds__game--winner');
              } else if (round.round_winner) {
                roundGameLink.classList.add('tournamentGroupedRounds__game--loser');
              }
            }
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

        let resultText = `${round.winning_teams[round.team1]} - ${round.winning_teams[round.team2]}`;
        if (ties) {
          resultText = `${resultText} - ${ties}`;
        }
        result.textContent = resultText;
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

function renderRoundHead (round_data) {
  titleHead.textContent = ` / ${round_data.round_name}`;
  let tourneyLink = stateLink(round_data.tournament.path, round_data.tournament.name);
  titleHead.prepend(tourneyLink);

  captionHead.appendChild(metaserverLink({
    tourney: round_data.tournament,
    round: round_data.metaserver_round
  }));
  captionHead.append(' / ');
  captionHead.append(stateLink(round_data.tournament.path + '/stats', 'tournament stats'));
}

function renderRoundInfo (round_data, subtitle, linkStage) {
  let result, team1, team2;
  if (round_data._processed) {
    let partSuffix = round_data.part ? `(${round_data.part})` : ''
    subtitle.textContent = ' vs ';
    team1 = dce('span', 'round__team', teamName(round_data.team1));
    team2 = dce('span', 'round__team', teamName(round_data.team2));
    let suffix = dce('span', 'round__suffix', partSuffix);
    result = dce('span', 'round__result');
    subtitle.prepend(team1);
    subtitle.appendChild(team2);
    subtitle.append(' ');
    subtitle.append(suffix);
    subtitle.append(' ');
    subtitle.append(result);

    if (linkStage && (round_data.round_path in YT_DATA_PATH_MAP)) {
      const coverage = stateLink(round_data.round_path, '▶️', 'round__coverageIcon')
      tooltip(coverage, `Covered by: ${coverageChannels(round_data.round_path).join(', ')}`);
      subtitle.append(coverage);
    }

    let subtitleStage;
    if (linkStage) {
      subtitleStage = dce('span', 'round__stage', ': ');
      subtitleStage.prepend(stateLink(round_data.round_path, ROUND_MAP.get(round_data.stage)));
    } else {
      subtitleStage = dce('span', 'round__stage', `${ROUND_MAP.get(round_data.stage)}: `);
    }
    subtitle.prepend(subtitleStage);
  } else {
    subtitle.textContent = round_data.round_name;
  }

  if (result && team1 && team2) {
    let resultText = `${round_data.winning_teams[round_data.team1]} - ${round_data.winning_teams[round_data.team2]}`;
    const tieGames = round_data.games.filter(r => r.tie);
    if (tieGames.length) {
      resultText = `${resultText} - ${tieGames.length}`;
    }
    result.textContent = resultText;

    if (round_data.round_winner == round_data.team1) {
      team1.classList.add('tournamentGroupedRounds__team--winner');
      team2.classList.add('tournamentGroupedRounds__team--loser');
    } else if (round_data.round_winner == round_data.team2) {
      team1.classList.add('tournamentGroupedRounds__team--loser');
      team2.classList.add('tournamentGroupedRounds__team--winner');
    }
  }
}

function renderRoundContents (round_data, container) {
  if (round_data.games.length) {
    let gameList = renderRoundGames(round_data.games);
    container.appendChild(gameList);
  } else if (round_data.forfeit) {
    container.textContent = `${teamName(round_data.forfeit)} forfeit`;
  } else {
    container.textContent = `No games`;
  }
}

function renderRoundGames (games) {
  let gameList = dce('ol', 'mapList');
  games.forEach(game => {
    let gameEntry = dce('li', 'mapList__entry');

    let gameLink = stateLink(game.game_path);
    gameLink.className = 'mapList__link mapList__item';
    let gameInfo = dce('div', 'mapList__info', ` — `);
    let gameType = dce('span', 'mapList__type', game.game_type);
    gameInfo.prepend(gameType);

    if (game.sudden_death) {
      gameInfo.prepend('Sudden Death: ');
    }

    if (game.winning_team) {
      let gameWinner = dce('span', 'mapList__badge gameList__badge', teamNameShort(game.winning_team));
      let winningTeam = game.teams[game.winning_team];
      gameWinner.style.borderBottom = `5px solid ${winningTeam.color[0]}`;
      tooltip(gameWinner, `Winner: ${teamName(game.winning_team)}`);
      gameInfo.prepend(' ');
      gameInfo.prepend(gameWinner);
    } else if (game.tie) {
      let gameTie = dce('span', 'mapList__badge gameList__badge', 'Tie')
      gameInfo.prepend(' ');
      gameInfo.prepend(gameTie);
    }

    let gameTime = dce('span', 'mapList__time', `${Math.round(game.time_limit/30/60)} mins`);
    gameInfo.appendChild(gameTime);

    let gameMap = dce('div', 'mapList__map', stripFormat(game.map_name));

    let overheadDiv = dce('div', 'mapList__overhead');
    let overheadMap = dce('img', 'mapList__overhead_img');
    overheadMap.src = `${BASE_URL}${game.overhead_path}`;
    overheadDiv.appendChild(overheadMap)
    gameLink.appendChild(overheadDiv);

    gameLink.appendChild(gameInfo);
    gameLink.appendChild(gameMap);

    gameEntry.appendChild(gameLink);

    gameList.appendChild(gameEntry);
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

function filterUnits (d) {
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

  const marks = Array.from(PLAYER_GROUPS, ([metaserverPlayer, points]) => {
    const [teamSlug, ,] = findMetaserverPlayerTeam(metaserverPlayer);
    let filtered = true;
    if (FILTERED_PLAYER && metaserverPlayer != FILTERED_PLAYER) {
      filtered = false;
    }
    if (FILTERED_TEAM && teamSlug != FILTERED_TEAM) {
      filtered = false;
    }
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
        filter: filterUnits,
        opacity: filtered ? 1 : 0.1,
      }),
      Plot.dot(points, {
        x: "time",
        y: (d, i) => i,
        stroke: "action",
        r: filtered ? 3 : 2,
        fill: "action",
        opacity: filtered ? 1 : 0.05,
        filter: (d) => {
          if (d.action == 'MOVEMENT') {
            return false;
          }
          return filterUnits(d);
        },
      }),
    ]
  }).flat();

  const isFiltered = FILTERED_PLAYER || FILTERED_TEAM;
  let tip = Plot.tip(GAME_DATA.commands, Plot[FILTERED_PLAYER ? 'pointerX' : 'pointer']({
    x: 'time',
    y: 'index',
    maxRadius: isFiltered ? 200 : 40,
    filter: (d) => {
      if (d.action == 'MOVEMENT') {
        return false;
      }
      if (!isFiltered) {
        return filterUnits(d);
      }
      let [player, teamSlug] = findPlayer(d.player);
      if (player.metaserver_player == FILTERED_PLAYER || teamSlug == FILTERED_TEAM) {
        return filterUnits(d);
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
      let playerLine = `[${teamName}] ${stripFormat(stripOrder(player.name))} → ${ACTION_MAP[d.action] || d.action}`;
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
    if (playerId != 'invalid' && !['ambient', 'custom'].includes(playerId)) {
      let [player, ] = findPlayer(playerId);
      if (playerId == self) {
        owner = 'self';
      } else if (player) {
        owner = stripFormat(stripOrder(player.name));
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

function findPlayerTeam (playerId) {
  for (const [teamSlug, team] of Object.entries(GAME_DATA.header.teams)) {
    if (playerId in team.players) {
      return [team.players[playerId], team, teamSlug];
    }
  }
}

function findMetaserverPlayerTeam (metaserverPlayer) {
  for (const [teamSlug, team] of Object.entries(GAME_DATA.header.teams)) {
    for (const player of Object.values(team.players)) {
      if (player.metaserver_player == metaserverPlayer) {
        return [teamSlug, team, player];
      }
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
    if (game.game_num == GAME_DATA.header.game.game_num) {
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
  return node;
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
  playerListHead.colSpan = 3;

  let showDetails = dce('span', 'playerList__show_details_button');
  let showDetailsGraphs = dce('span', 'playerList__show_details_graphs', '📈 show graphs');
  let showDetailsHeatmaps = dce('span', 'playerList__show_details_heatmap', '🔥 show heatmap');
  showDetails.appendChild(showDetailsGraphs);
  showDetails.appendChild(showDetailsHeatmaps);
  showDetails.addEventListener('click', () => {
    if (showingHeatmap()) {
      document.getElementById('columns').classList.remove('show-heatmap');
    } else {
      document.getElementById('columns').classList.add('show-heatmap');
    }
  });
  playerListHead.appendChild(showDetails);

  let showStats = dce('span', 'playerList__show_stats_button');
  let showStatsShow = dce('span', 'playerList__show_stats_show', 'show stats');
  let showStatsHide = dce('span', 'playerList__show_stats_hide', 'hide stats');
  showStats.appendChild(showStatsShow);
  showStats.appendChild(showStatsHide);
  showStats.addEventListener('click', toggleStats);
  playerListHead.appendChild(showStats);

  statsHeadRow.appendChild(playerListHead);

  statsHead.appendChild(statsHeadRow);

  let statsBody = dce('tbody');
  for (const [teamSlug, team] of Object.entries(GAME_DATA.header.teams)) {
    // Team stat line
    let teamTopSpacer = dce('tr', 'playerListTopSpacerTeamRow');
    teamTopSpacer.append(dce('td', 'playerListTopSpacerTeam'));
    statsBody.append(teamTopSpacer);

    let teamRow = dce('tr', 'playerStats__team');
    if (FILTERED_TEAM == teamSlug) {
      teamRow.classList.add('playerStats__team--selected');
    }
    teamRow.dataset.team_slug = teamSlug;

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
    teamHead.addEventListener('click', (e) => {
      e.preventDefault();
      selectTeam(teamRow);
    });
    if (team.winner || team.allied_winner) {
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
      let metaserverPlayer = player.metaserver_player;
      if (FILTERED_PLAYER == metaserverPlayer) {
        playerRow.classList.add('playerStats__player--selected');
      }
      playerRow.dataset.metaserver_player = metaserverPlayer;

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

      const playerItem = dce("td", 'playerSelect__player', stripFormat(stripOrder(player.name)));
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
      playerItem.dataset.metaserver_player = metaserverPlayer;

      playerItem.addEventListener('click', (e) => {
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

  let sd = GAME_DATA.header.game.sudden_death ? 'Sudden Death: ' : '';
  let subtitle = `${sd}${GAME_DATA.header.game.game_type} on ${stripFormat(GAME_DATA.header.game.map_name)} (${GAME_DATA.header.game.difficulty}) - ${Math.round(GAME_DATA.header.game.time_limit/30/60)} mins`;

  let filmLink = dce('a');
  filmLink.target = '_blank';
  filmLink.textContent = 'download film';
  filmLink.href = `${BASE_URL}${GAME_DATA.header.game.game_path}/${GAME_DATA.header.game.film_name}`;
  // if (GAME_DATA.header.tournament.metaserver == 'gos') {
  //   filmLink.href = `http://gateofstorms.net/recordings/${GAME_DATA.header.game.film_name}`;
  // } else {
  //   filmLink.href = `https://bagrada.net/recordings/public/${GAME_DATA.header.game.film_name}`;
  // }

  titleHead.textContent = ' / ';
  let tourneyLink = stateLink(GAME_DATA.header.tournament.path, GAME_DATA.header.tournament.name);
  let roundLink = stateLink(GAME_DATA.header.round.round_path, GAME_DATA.header.round.round_name);
  titleHead.prepend(tourneyLink);
  titleHead.append(roundLink);

  subtitleHead.textContent = subtitle;

  let overheadMap = dce('img');
  overheadMap.src = `${BASE_URL}${GAME_DATA.header.game.overhead_path}`;
  overhead.innerHTML = '';
  overhead.appendChild(overheadMap);

  if (GAME_DATA.header.game.plugins && GAME_DATA.header.game.plugins.length) {
    const plugin = GAME_DATA.header.game.plugins[0];
    let plug = plugin.name;
    if (plugin.tain_url) {
      let plugLink = dce('a');
      plugLink.target = '_blank';
      plugLink.textContent = plug;
      plugLink.href = plugin.tain_url;
      plug = plugLink;
    }
    captionHead.append('plugin: ');
    captionHead.append(plug);
    captionHead.append(' / ');
  }
  captionHead.append(filmLink);
  captionHead.append(' / ');

  captionHead.append(metaserverLink({
    tourney: GAME_DATA.header.tournament,
    round: GAME_DATA.header.round.metaserver_round,
    game: GAME_DATA.header.game.metaserver_game
  }));
  captionHead.append(' / ');

  captionHead.append(stateLink(GAME_DATA.header.tournament.path + '/stats', 'tournament stats'));
  captionHead.append(' / ');

  captionHead.append(stateLink(`maps#${slugifyMapGt(GAME_DATA.header.game)}`, 'historical trades'));

  let timeRange = '';
  if (GAME_DATA.header.game.start) {
    let start = new Date(GAME_DATA.header.game.start);
    let startDate = start.toDateString();
    timeRange = `${startDate} - ${start.toLocaleTimeString('en-gb', {
      hour: '2-digit',
      minute: '2-digit',
      hour24: true,
    })}`;
  }
  if (GAME_DATA.header.game.end) {
    let end = new Date(GAME_DATA.header.game.end);
    timeRange = `${timeRange} - ${end.toLocaleTimeString('en-gb', {
      timeZoneName: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hour24: true,
    })}`;
  }
  let gameDate = '';
  if (timeRange) {
    gameDate = `${timeRange} `;
  }
  let host;
  if (GAME_DATA.header.game.host) {
    host = stripFormat(stripOrder(GAME_DATA.header.game.host.name));
  }
  if (host) {
    gameDate += `(Host: ${host})`;
  }
  captionHead.append(dce('br'), gameDate);
}

function stateLink (href, textContent, className) {
  let link = dce('a', className, textContent);
  link.href = `${BASE_URL}${href}`;
  link.addEventListener('click', (e) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    history.pushState({}, "", link.href);
    window.scrollTo(0, 0);
    routeUrl();
  });
  return link;
}

function showingHeatmap () {
  return document.getElementById('columns').classList.contains('show-heatmap');
}

function showingStats () {
  return document.getElementById('columns').classList.contains('show-stats');
}

function toggleStats () {
  if (showingStats()) {
    document.getElementById('columns').classList.remove('show-stats');
  } else {
    document.getElementById('columns').classList.add('show-stats');
  }
  renderPlots();
  renderSummary();
  renderHeatmap();
}

function renderHeatmap () {
  heatmap.innerHTML = '';

  const heatmapHead = dce('h4', 'heatmap-head', 'Heatmap');
  const heatmapImage = dce('div', 'heatmap-image');
  const heatmapLegend = dce('div', 'heatmap-legend');
  heatmapImage.addEventListener('click', toggleStats);

  const [locWidth, locHeight] = GAME_DATA.header.game.dimensions;
  const aspect = locWidth / locHeight;

  let cMap = dce('img', 'heatmap-base');
  cMap.src = `${BASE_URL}${GAME_DATA.header.game.cmap_path}`;
  cMap.style.aspectRatio = aspect;
  heatmapImage.appendChild(cMap);

  if (FILTERED_TEAM != null) {
    const teamLink = stateLink(
      `tournament/${TOURNEY_ID}/teams/${FILTERED_TEAM}`,
      teamName(FILTERED_TEAM)
    );
    heatmapHead.innerText = `Heatmap: ${teamNameShort(FILTERED_TEAM)} - `;
    heatmapHead.append(teamLink);
  } else if (FILTERED_PLAYER != null) {
    const [teamSlug, , player] = findMetaserverPlayerTeam(FILTERED_PLAYER);
    const playerLink = stateLink(
      `tournament/${TOURNEY_ID}/players/${FILTERED_PLAYER}`,
      stripFormat(stripOrder(player.name))
    );
    heatmapHead.innerText = `Heatmap: ${teamNameShort(teamSlug)} - `;
    heatmapHead.append(playerLink);
  } else {
    heatmapHead.innerText = "Heatmap: All";
  }

  // Controls
  const heatmapControls = dce('div', 'heatmap-controls');

  const heatmapTimer = dce('div', 'heatmap-timer');
  heatmapControls.append(heatmapTimer);

  const heatmapButtons = dce('div', 'heatmap-buttons');
  const heatmapRestart = dce('div', 'heatmap-button heatmap-restart', '⏮');
  heatmapRestart.addEventListener('click', resetTimeline);
  const heatmapPlay = dce('div', 'heatmap-button heatmap-play', '▶');
  heatmapPlay.addEventListener('click', playPauseTimeline);
  const heatmapPause = dce('div', 'heatmap-button heatmap-pause heatmap-button--hide', '⏸');
  heatmapPause.addEventListener('click', playPauseTimeline);
  const heatmapSkip = dce('div', 'heatmap-button heatmap-skip', '⏭');
  heatmapSkip.addEventListener('click', skipTimeline);
  heatmapButtons.append(heatmapRestart);
  heatmapButtons.append(heatmapPlay);
  heatmapButtons.append(heatmapPause);
  heatmapButtons.append(heatmapSkip);
  heatmapControls.append(heatmapButtons);

  heatmapHead.append(heatmapControls);

  if (GAME_DATA.commands.length) {
    GAME_DATA._positions = [];
    GAME_DATA.commands.forEach(c => {
      if (c.position) {
        let [player, teamSlug] = findPlayer(c.player);
        if (c.position[0] == locWidth && c.position[1] == 0) {
          return;
        }
        GAME_DATA._positions.push({
          time: c.time,
          x: c.position[0],
          y: locHeight-c.position[1],
          xFrac: c.position[0] / locWidth,
          yFrac: c.position[1] / locHeight,
          teamSlug: teamSlug,
          teamName: teamName(teamSlug),
          monsters: c.monsters,
          playerName: player.name,
          playerColor: player.color[0],
          metaserverPlayer: player.metaserver_player,
        });
      }
    });
    const densityPlot = Plot.plot({
      className: "densityPlot",
      width: locWidth,
      height: locHeight,
      x: {
        axis: false,
        domain: [0, locWidth],
      },
      y: {
        axis: false,
        domain: [0, locHeight],
      },
      marks: [
        Plot.density(GAME_DATA._positions, {
          x: "x",
          y: "y",
          bandwidth: 1,
          fill: "density",
          weight: d => {
            let filtered = true;
            let sameTeam = false;
            if (FILTERED_PLAYER && d.metaserverPlayer != FILTERED_PLAYER) {
              filtered = false;
              const [teamSlug, ,] = findMetaserverPlayerTeam(FILTERED_PLAYER)
              if (teamSlugMap(teamSlug) == teamSlugMap(d.teamSlug)) {
                sameTeam = true;
              }
            }
            if (FILTERED_TEAM && d.teamSlug != FILTERED_TEAM) {
              filtered = false;
            }
            return filtered ? 1 : (sameTeam ? 0.3 : 0.1);
          },
          opacity: 0.2,
        }),
      ]
    });
    heatmapImage.append(densityPlot);

    const dotColorMap = {};
    dotColorMap[teamName(GAME_DATA.header.round.team1)] = "crimson";
    dotColorMap[teamName(GAME_DATA.header.round.team2)] = "orange";
    const dotLegend = Plot.legend({color: {
      domain: Object.keys(dotColorMap),
      range: Object.values(dotColorMap),
      swatchSize: 10,
      marginLeft: 0,
    }});
    heatmapLegend.append(dotLegend);

    const dotPlotContainer = dce('div', 'dotPlotContainer');
    dotPlotContainer.append(renderDotPlot(dotColorMap));
    heatmapImage.append(dotPlotContainer);
  }
  if (GAME_DATA.header.game.locations) {
    const teamObservers = {};
    GAME_DATA.header.game.locations.forEach(loc => {
      if (loc.position && (loc.target || loc.observer)) {
        let x = loc.position[0] / locWidth;
        let y = loc.position[1] / locHeight;
        let type = 'location';
        if (loc.observer) {
          if (teamObservers[loc.team]) {
            return;
          }
          teamObservers[loc.team] = true;
          type = 'spawn';
        }
        if (loc.target) {
          type = `target mapLocation-${loc.type}`;
        }
        const mapLoc = dce('div', `mapLocation mapLocation-${type}`);
        if (loc.target && loc.flag_number) {
          mapLoc.innerText = loc.flag_number;

        }
        if (loc.team != null) {
          if (loc.observer) {
            mapLoc.classList.add('mapLocation--hidden');
          }
          for (const [teamSlug, team] of Object.entries(GAME_DATA.header.teams)) {
            const teamColor = teamSlugMap(teamSlug) == GAME_DATA.header.round.team1 ? 'crimson' : 'orange';
            if (team.team_index == loc.team) {
              if (loc.observer) {
                mapLoc.innerText = teamNameShort(teamSlug);
              }
              if (loc.observer || GAME_DATA.header.game.game_type != 'Capture the Flag') {
                mapLoc.style.backgroundColor = teamColor;
              }
              mapLoc.classList.remove('mapLocation--hidden');
            }
          }
        }
        mapLoc.style.top = `${y*100}%`;
        mapLoc.style.left = `${x*100}%`;
        heatmapImage.append(mapLoc);
      }
    });
  }

  const heatmapChat = dce('div', 'heatmap-chat');
  heatmapImage.append(heatmapChat);
  heatmapImage.append(dce('div', 'heatmap-chatScroll'));

  heatmap.appendChild(heatmapHead);
  heatmap.appendChild(heatmapImage);
  heatmap.appendChild(heatmapLegend);
}

function renderDotPlot (dotColorMap) {
  const dotPlot = dce('div', 'dotPlot');
  GAME_DATA._positions.forEach((d, i) => {
    const dot = dce('div', 'dotPlot__dot');
    dot.style.backgroundColor = dotColorMap[d.teamName];
    dot.style.left = `${d.xFrac*100}%`;
    dot.style.top = `${d.yFrac*100}%`;
    let filtered = true;
    if (FILTERED_PLAYER && d.metaserverPlayer != FILTERED_PLAYER) {
      filtered = false;
    }
    if (FILTERED_TEAM && d.teamSlug != FILTERED_TEAM) {
      filtered = false;
    }
    dot.dataset.idx = i;
    dot.style.opacity = filtered ? 0.5 : 0;
    dotPlot.append(dot);
  });
  return dotPlot;
}

const TIMELINE_STATE = {};

function resetTimeline () {
  console.log('Reset');
  document.querySelector('.heatmap-chat').innerHTML = '';
  document.querySelector('.heatmap-chatScroll').innerHTML = '';
  document.querySelector('.densityPlot').style.display = 'none';
  document.querySelector('.heatmap-play').classList.remove('heatmap-button--hide');
  document.querySelector('.heatmap-pause').classList.add('heatmap-button--hide');
  const TS = TIMELINE_STATE;
  TS.multiplier = 32;
  TS.pause = true;
  TS.last = performance.now();
  const game_info = GAME_DATA.header.game;
  TS.game_path = GAME_DATA.header.game.game_path;
  TS.progress = game_info.planning_time;
  const lastCommand = GAME_DATA.commands[GAME_DATA.commands.length - 1];
  TS.game_length = game_info.planning_time + Math.min(lastCommand.time, game_info.time_limit);
  TS.game_over = false;
  TS.messages = [];
  TS.lastLog = 0;
  TS.lastChat = 0;
  TS.chatIdx = -1;
  TS.lastCommand = null;
  TS.teamSpawns = {};

  if (GAME_DATA.header.game.locations) {
    GAME_DATA.header.game.locations.forEach(loc => {
      if (loc.position && loc.observer && loc.team != null) {
        if (TS.teamSpawns[loc.team]) {
          return;
        }
        TS.teamSpawns[loc.team] = loc.position;
      }
    });
  }

  timelineTick(TS.last, true);
}

function playPauseTimeline () {
  const TS = TIMELINE_STATE;
  if (TS.game_over || TS.game_path != GAME_DATA.header.game.game_path) {
    resetTimeline();
  }
  if (TS.pause) {
    console.log('Play');
    TS.last = performance.now();
    TS.pause = false;
    requestAnimationFrame(timelineTick);
  } else {
    console.log('Pause');
    TS.pause = true;
  }
  document.querySelector('.heatmap-play').classList.toggle('heatmap-button--hide', !TIMELINE_STATE.pause);
  document.querySelector('.heatmap-pause').classList.toggle('heatmap-button--hide', TIMELINE_STATE.pause);
}

function skipTimeline () {
  const TS = TIMELINE_STATE;
  if (GAME_DATA) {
    console.log('Skip');
    if (TS.game_path != GAME_DATA.header.game.game_path) {
      resetTimeline();
    }
    TS.chatIdx = -1;
    TS.last = performance.now() - 1;
    const game_info = GAME_DATA.header.game;
    if (TS.progress < game_info.planning_time) {
      TS.progress = game_info.planning_time;
    } else {
      TS.progress = TS.game_length;
    }
    timelineTick(TS.last + 1, true);
  }
}

window.TIMELINE_STATE = TIMELINE_STATE;

function timelineTick (nowRaf, once) {
  const now = performance.now();
  const TS = TIMELINE_STATE;
  if (!GAME_DATA) {
    console.log('No game abort');
    return;
  }
  const game_info = GAME_DATA.header.game;
  if (TS.pause) {
    console.log('Paused abort');
    // return;
  }
  const delta = now - TS.last;
  TS.last = now;
  const deltaTicks = (delta / 1000) * 30;
  TS.progress += deltaTicks * TS.multiplier;
  TS.progress = Math.min(TS.game_length, TS.progress);
  if (TS.progress >= TS.game_length) {
    console.log('Game Over');
    document.querySelector('.densityPlot').style.display = 'block';
    document.querySelector('.heatmap-play').classList.remove('heatmap-button--hide');
    document.querySelector('.heatmap-pause').classList.add('heatmap-button--hide');
    document.querySelectorAll('.dotPlot__dot').forEach(dot => {
      dot.classList.remove('dotPlot__dot--hidden');
    });
    TS.game_over = true;
    TS.pause = true;
  }
  const pt = TS.progress < game_info.planning_time;
  const tickStamp = TS.progress - game_info.planning_time;

  document.querySelectorAll('.heatmap-playerBadge').forEach(b => {
    b.classList.add('heatmap-playerBadge--hide');
  });
  const playerPositions = {};
  const dotTime = TS.lastCommand || tickStamp;
  document.querySelectorAll('.dotPlot__dot').forEach(dot => {
    const pos = GAME_DATA._positions[dot.dataset.idx];
    let show = true;
    if (pos.time > dotTime || pos.time < (dotTime - 30*120)) {
      show = false;
    } else {
      const msPlayer = pos.metaserverPlayer;
      if (!(msPlayer in playerPositions)) {
        let playerBadge = document.querySelector(`.heatmap-playerBadge--${msPlayer}`);
        if (!playerBadge) {
          playerBadge = dce(
            'div', `heatmap-playerBadge heatmap-playerBadge--hide heatmap-playerBadge--${msPlayer}`,
            stripFormat(stripOrder(pos.playerName))
          );
          playerBadge.style.borderLeft = `7px solid ${pos.playerColor}`;
          let bg;
          if (teamSlugMap(pos.teamSlug) == GAME_DATA.header.round.team1) {
            bg = 'rgba(220, 20, 60, 0.8)'; // crimson
          } else {
            bg = 'rgba(255, 165, 0, 0.8)'; // orange
          }
          playerBadge.style.backgroundColor = bg;
          document.querySelector('.heatmap-chat').append(playerBadge);
        }
        playerPositions[msPlayer] = {
          name: stripFormat(stripOrder(pos.playerName)),
          monsters: {},
          x: [],
          y: [],
          element: playerBadge
        };
      }
      playerPositions[msPlayer].x.push(pos.xFrac);
      playerPositions[msPlayer].y.push(pos.yFrac);
      if (pos.monsters) {
        for (const [monsterName, count] of Object.entries(pos.monsters)) {
          playerPositions[msPlayer].monsters[monsterName] = count;
        }
      }
    }
    if (!TS.game_over) {
      dot.classList.toggle('dotPlot__dot--hidden', !show);
    }
  });
  for (const playerDetails of Object.values(playerPositions)) {
    if (playerDetails.x.length > 3 && playerDetails.y.length > 3) {
      const element = playerDetails.element;
      const x = avgMean(playerDetails.x.slice(playerDetails.x.length/2));
      const y = avgMean(playerDetails.y.slice(playerDetails.x.length/2));
      const numTrow = playerDetails.monsters['Trow'] || 0;
      const numFG = playerDetails.monsters['Forest Giant'] || 0;
      const numGiants = numTrow + numFG;
      const giant = numGiants > 0;
      element.classList.toggle('heatmap-playerBadge--giant', giant);
      // const g = giant ? `${"🗿".repeat(numGiants)} ` : '';
      // element.innerText = `${g}${playerDetails.name} ${summarizeMonsters(playerDetails.monsters)}`;
      element.innerHTML = '';
      element.innerText = `${playerDetails.name}`;
      for (let i = 0; i < numTrow; i++) {
        const trowIcon = dce('img', 'unitIcon');
        trowIcon.src = `${BASE_URL}img/icons/trow.png`;
        trowIcon.width = 16;
        trowIcon.height = 16;
        element.prepend(trowIcon);
      }
      for (let i = 0; i < numFG; i++) {
        const fgIcon = dce('img', 'unitIcon');
        fgIcon.src = `${BASE_URL}img/icons/fg.png`;
        fgIcon.width = 16;
        fgIcon.height = 16;
        element.prepend(fgIcon);
      }
      element.style.left = `${x*100}%`;
      element.style.top = `${y*100}%`;
      element.classList.remove('heatmap-playerBadge--hide');
    }
  }

  const timestamp = Math.abs(tickStamp) / 30;
  const mins = Math.floor(timestamp / 60);
  const secs = Math.floor(timestamp % 60);
  const ts = `${mins}:${secs.toString().padStart(2, "0")}`;

  let lastCommand;
  if (!TS.lastCommand && GAME_DATA.commands) {
    lastCommand = GAME_DATA.commands[GAME_DATA.commands.length - 1];
    if (lastCommand && tickStamp >= lastCommand.time) {
      console.log(`END ${ts}`);
      TS.lastCommand = lastCommand.time;
    }
  }

  let chatExpiry = 30 * 6; //(speedup ? 200 : 20);
  let chatMsg;
  if (GAME_DATA.chat) {
    GAME_DATA.chat.forEach((chatLine, i) => {
      if (i > TS.chatIdx && !chatMsg && tickStamp > chatLine.time && chatLine.type == 'chat') {
        const remainingExpiry = (tickStamp - chatLine.time);
        if (remainingExpiry < chatExpiry) {
          TS.chatIdx = i;
          chatMsg = chatLine;
        }
      }
    });
    updateChat();
  }

  // Super high speed
  const speedup = (TS.lastCommand || pt);
  // Disable chat for now
  chatMsg = null;
  if (chatMsg) {
    // Time that chat should stay visible
    renderChat(chatMsg, TS.progress + chatExpiry);
    TS.lastChat = TS.progress;
    // Slow down during chat
    // TS.multiplier = 2;
  }
  // Time since chat after which to return to regular high speed
  const chatDecay = (30 * 2);
  if ((TS.progress - TS.lastChat) > chatDecay) {
    TIMELINE_STATE.multiplier = speedup ? 1000 : 32;
  }
  if (chatMsg || (TS.progress - TS.lastLog) > 30) {
    // console.log(`${pt ? 'PT:' : '   '} ${ts} ${TIMELINE_STATE.multiplier}x`, chatMsg);
  }
  let state = TS.game_over ? 'Game Over ' : '';
  document.querySelector('.heatmap-timer').innerText = `${state} ${pt ? 'PT: ' : ''}${ts}`;
  TS.lastLog = TS.progress;

  if (!TS.pause && !TS.game_over && !once) {
    requestAnimationFrame(timelineTick);
  }
}

function updateChat () {
  const TS = TIMELINE_STATE;
  const toKeep = [];
  TS.messages.forEach(msg => {
    if (TS.progress > msg.expiry) {
      msg.element.remove();
    } else {
      toKeep.push(msg);
    }
  });
  TS.messages = toKeep;
}

function renderChat (chatMsg, expiry) {
  const TS = TIMELINE_STATE;
  const [player, team, teamSlug] = findPlayerTeam(chatMsg.player);
  if (!player) {
    return;
  }
  let bg;
  if (teamSlugMap(teamSlug) == GAME_DATA.header.round.team1) {
    bg = 'rgba(220, 20, 60, 0.8)'; // crimson
  } else {
    bg = 'rgba(255, 165, 0, 0.8)'; // orange
  }
  let position = chatMsg.last_position || TS.teamSpawns[team.team_index];
  let chatEmoji = chatMsg.whisper ? '' : '🗣️'; // 🤫
  const heatmapChat = document.querySelector('.heatmap-chat');
  const chatScroll = document.querySelector('.heatmap-chatScroll');
  const element = dce('div', 'chatMessage');
  const chatDot = dce('div', 'chatMessage__dot');
  const author = dce('div', 'chatMessage__author', `${stripFormat(stripOrder(player.name))}`);
  const messageEl = dce('div', 'chatMessage__message', ` ${chatEmoji} ${chatMsg.message}`);
  if (chatMsg.whisper) {
    messageEl.classList.add('chatMessage__message--whisper');
  }
  element.append(chatDot)
  element.append(author);
  element.append(messageEl);
  author.style.backgroundColor = bg;
  if (position) {
    const [locWidth, locHeight] = GAME_DATA.header.game.dimensions;
    let x = position[0] / locWidth;
    let y = position[1] / locHeight;
    if (x > 0.7) {
      element.style.right = `${(1-x)*100}%`;
      chatDot.classList.add('chatMessage__dot--right');
    } else {
      element.style.left = `${x*100}%`;
    }
    if (y > 0.8) {
      element.style.bottom = `${(1-y)*100}%`;
      chatDot.classList.add('chatMessage__dot--bottom');
    } else {
      element.style.top = `${y*100}%`;
    }
    heatmapChat.append(element);
  } else {
    chatScroll.append(element);
    chatScroll.scrollTo(0, chatScroll.scrollHeight);
  }
  TS.messages.push({expiry, element});
}

function renderSummary () {
  summaryGraph.innerHTML = '';
  if (!GAME_DATA.commands.length) {
    return;
  }
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
  return name.replace(/[\\|]./gi, '').replace(/[\r\n]/gi, '').replace(/\uF8FF/g, '');
}

function stripBrackets (name) {
  return name.replace(/\s+\([^)]+\)/gi, '');
}

function stripOrder (name) {
  return name.trim().replace(/\s{3,}.*/, '');
}

function resetSelection () {
  document.querySelectorAll('.playerStats__player').forEach((el) => {
    el.classList.remove('playerStats__player--selected');
  });
  document.querySelectorAll('.playerStats__team').forEach((el) => {
    el.classList.remove('playerStats__team--selected');
  });
}

function resetHeatmap () {
  document.querySelector('.heatmap-head').innerText = "Heatmap: All";
}

function selectPlayerOrTeam (playerTeamEl) {
  if (playerTeamEl.classList.contains('playerStats__player')) {
    selectPlayer(playerTeamEl);
  } else if (playerTeamEl.classList.contains('playerStats__team')) {
    selectTeam(playerTeamEl);
  }
}

function selectPlayer (playerEl) {
  resetSelection();
  const metaserverPlayer = playerEl.dataset.metaserver_player;
  FILTERED_TEAM = null;
  if (FILTERED_PLAYER == metaserverPlayer) {
    FILTERED_PLAYER = null;
    resetHeatmap();
  } else {
    FILTERED_PLAYER = metaserverPlayer;
    playerEl.classList.add('playerStats__player--selected');
  }
  renderPlots();
  renderHeatmap();
}

function selectTeam (teamEl) {
  resetSelection();
  let teamSlug = teamEl.dataset.team_slug;
  FILTERED_PLAYER = null;
  if (FILTERED_TEAM == teamSlug) {
    FILTERED_TEAM = null;
    resetHeatmap();
  } else {
    FILTERED_TEAM = teamSlug;
    teamEl.classList.add('playerStats__team--selected');
  }

  renderPlots();
  renderHeatmap();
}

document.addEventListener('keydown', (e) => {
  if (FILTERED_PLAYER != null || FILTERED_TEAM != null) {
    let listPlayers = document.querySelectorAll('.playerStats__player, .playerStats__team');
    let selected = document.querySelector('.playerStats__player--selected, .playerStats__team--selected');
    // debugger;
    let index = Array.prototype.indexOf.call(listPlayers, selected);
    if (e.key == 'ArrowDown') {
      e.preventDefault();
      let next = listPlayers[index+1];
      if (next) {
        selectPlayerOrTeam(next);
      } else {
        selectPlayerOrTeam(listPlayers[0]);
      }
    } else if (e.key == 'ArrowUp') {
      e.preventDefault();
      let prev = listPlayers[index-1];
      if (prev) {
        selectPlayerOrTeam(prev);
      } else {
        selectPlayerOrTeam(listPlayers[listPlayers.length-1]);
      }
    } else if (e.key == 'Enter') {
      e.preventDefault();
      selectPlayerOrTeam(selected);
    }
  }
});

async function fetchYTData () {
  const response = await fetch(`${BASE_URL}youtube.json?v=${DATA_VERSION}`);
  YT_DATA = JSON.parse(await response.text());

  for (const [ytId, ytValue] of Object.entries(YT_DATA)) {
    ytValue.mapping.forEach(mapping => {
      if (!(mapping.path in YT_DATA_PATH_MAP)) {
        YT_DATA_PATH_MAP[mapping.path] = [];
      }
      YT_DATA_PATH_MAP[mapping.path].push({
        yt_id: ytId,
        details: mapping
      });
    });
  }

  window.YT_DATA = YT_DATA;
}

function coverageChannels (path) {
  if (path in YT_DATA_PATH_MAP) {
    return Array.from(new Set(YT_DATA_PATH_MAP[path].map(({yt_id}) => {
      return YT_DATA[yt_id].meta.channel;
    })));
  }
  return [];
}

async function init () {
  await fetchYTData();
  routeUrl();
}

init();
