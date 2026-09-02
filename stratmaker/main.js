import * as THREE from 'three/webgpu';
// import * as TSL from 'three/tsl';
import { MapControls } from 'three/addons/controls/MapControls.js';
import { shader } from './cmap_shader.js';

const BASE_URL = import.meta.env.BASE_URL;
const DATA_VERSION = '2026-09-01';
const MAP_RE = /^maps\/([^/]+)/;
let MAP_SLUG = '';
let STRAT;

const STATE = {
  stratIdx: 0,
  strats: [{
    mapViews: [],
    splits: [],
    game_type: null,
    counts: {},
    notes: null,
    time_limit: null,
  }],
  three: {}
};
window.STATE = STATE;
function dce (element, className, textContent) {
  const el = document.createElement(element);
  if (className) {
    el.className = className;
  }
  if (textContent != null) {
    el.textContent = textContent;
  }
  return el;
}


function initTooltips () {
  tooltip(document.querySelector('.notrading_toggle'), 'Toggle trading');
  tooltip(document.querySelector('.noclutter_toggle'), 'Toggle Clutter');
  tooltip(document.querySelector('.nodrawings_toggle'), 'Toggle Drawings');
  const terrainTT = tooltip(document.querySelector('.terrain_toggle'));
  const terrainLegend = dce('img', 'tooltip_img');
  terrainLegend.src = `${BASE_URL}img/terrain_legend.png`;
  terrainLegend.width = 225;
  terrainLegend.height = 425;
  let ttContent = dce('span', 'tooltipContent', 'Toggle Terrain (T)');
  ttContent.append(dce('br'));
  ttContent.append(terrainLegend);
  terrainTT.append(ttContent);
  tooltip(document.querySelector('.noshadow_toggle'), 'Toggle Shadows (S)');
  tooltip(document.querySelector('.download_state'), 'Data export');
  tooltip(document.querySelector('.all_maps'), 'Map list');

  tooltip(document.querySelector('.map__status_draw_help'), [
    'Toggle draw mode with the 🖍️ draw icon or by pressing D.',
    'With draw mode active, click on the map with the crosshair cursor to start a line.\nFurther clicks will create straight line segments.\nDouble click or press escape to end the line.\nPressing escape again will exit draw mode.',
    'With draw mode inactive, select lines with click and shift click.\nPress backspace/delete to delete selected lines.',
    'Use the draw icons next to players or the number keys to start drawing with their colour.',
    'Double click behaviour:\n• Draw mode active, line started: adds a final segment and ends the line\n• Draw mode active: draws a single dot\n• Draw mode inactive, double click a line: selects all lines of the same colour.\n• Draw mode inactive, empty space: activates draw mode and starts a new line.'
  ].join('\n\n'));
  tooltip(document.querySelector('.map__status_draw_active'), 'Toggle draw mode (D)');
  tooltip(document.querySelector('.map__status_add_view'), 'Add a map view');
}

function route () {
  let match = window.location.pathname.slice(BASE_URL.length).match(MAP_RE);
  if (!match) {
    return fetchIndex();
  }
  MAP_SLUG = match[1];
  return fetchMap();
}

function fetchIndex () {
  fetch(`${BASE_URL}maps.json?v=${DATA_VERSION}`).then(response => {
    response.text().then(txt => {
      const mapData = JSON.parse(txt);
      hideTooltip();
      const container = document.getElementById('container');
      document.getElementById('toolbar').innerHTML = '';
      container.innerHTML = '';
      const mapList = dce('div', 'mapList');
      mapList.append(dce('h1', 'mapList__head', 'Myth Strategy Maker'));
      mapList.append(dce('h2', 'mapList__subhead', 'Map list'));
      mapData.sort((a, b) => {
        const plug = (a.plugins[0] || '').localeCompare(b.plugins[0] || '');
        if (plug == 0) {
          return a.mesh_name.localeCompare(b.mesh_name);
        }
        return plug;
      });
      mapData.forEach(map => {
        const mapItem = dce('div', 'mapList__map');
        const mapLink = dce('a', 'mapList__link', map.name);
        if (map.plugins.length) {
          mapLink.append(dce('span', 'mapList__plugins', map.plugins.join(', ')));
        }

        const mapImg = dce('img', 'mapList__image');
        mapImg.height = 30;
        mapImg.src = `${BASE_URL}${map.overhead_path}`;
        mapLink.prepend(mapImg);

        mapLink.href = `${BASE_URL}${map.mesh_dir}`;

        const tt = tooltip(mapLink);
        tt.classList.add('tooltip__noborder');
        tt.classList.add('tooltip__nobg');
        let overhead = dce('img');
        overhead.src = `${BASE_URL}${map.overhead_path}`;
        tt.append(overhead);

        mapItem.append(mapLink);
        mapList.append(mapItem);
      });
      container.append(mapList);
    });
  });
}

function processTradeableUnits () {
  if (STATE.meshData.units && STRAT.game_type) {
    for (const [, units] of Object.entries(STATE.meshData.units)) {
      let i = 0;
      Object.entries(units).forEach(([tagId, unit]) => {
        if (!unitInGameType(unit)) {
          delete units[tagId];
          return;
        }
        Object.assign(unit, unit.counts[STRAT.game_type] || unit.counts.all)
        i++;
        if (i > 8) {
          unit.tradeable = false;
          unit.max = unit.initial_count;
          unit.markers = unit.markers.filter(m => {
            return !m['flags'].includes('invis');
          });
        }
      });
    }
  }
}

function fetchMap () {
  fetch(`${BASE_URL}maps/${MAP_SLUG}/data.json?v=${DATA_VERSION}`).then(response => {
    response.text().then(txt => {
      STATE.meshData = JSON.parse(txt);
      setFavicon();
      fetch(`${BASE_URL}maps/${MAP_SLUG}/state.json?v=${DATA_VERSION}`).then(stateResp => {
        if (stateResp.ok) {
          stateResp.text().then(stateTxt => {
            let fsState;
            try {
              fsState = JSON.parse(stateTxt);
            } catch {
              // pass
            }
            if (fsState) {
              Object.assign(STATE, fsState);
            }
            buildMap();
          });
        } else {
          buildMap();
        }
      });
    });
  });
}

function renderNotes (notes) {
  if (notes) {
    const stratNotes = document.querySelector('.strat_notes');
    stratNotes.value = notes;
    stratNotes.style.height = '44px';
    stratNotes.style.height = `${stratNotes.scrollHeight}px`;
  }
}

function renderTimeLimit (timeLimit) {
  if (timeLimit) {
    document.querySelector('.map__time').value = timeLimit;
  }
}

function renderNoGametype () {
  if (STRAT.game_type) {
    document.body.classList.remove('nogametype');
  }
}

function selectGameType (gameType) {
  STRAT.game_type = gameType;
  saveState();
  window.location.reload();
}

function renderRest () {
  setTitle();
  renderNoTrading();
  renderNoClutter();
  renderTerrain();
  renderNoShadow();
  if (!STRAT.game_type) {
    return;
  }
  updateTrade(STRAT.counts, true);
  renderNotes(STRAT.notes);
  const gt = getGameType();
  document.querySelectorAll('.gtLink').forEach((el) => {
    el.classList.remove('gtLink--active');
  });
  document.querySelector(`.gtLink-${gt.game_type}`).classList.add('gtLink--active');
  renderTradeUnits();
  renderSplits();
}

function renderTradeUnits () {
  renderTrade();
  renderUnits();
}

function setTradeMin (target) {
  const counts = {};
  counts[target.dataset.tag] = 0;
  updateTrade(counts);
  renderTrade();
}
function setTradeMax (target) {
  const counts = {};
  counts[target.dataset.tag] = 'max';
  updateTrade(counts);
  renderTrade();
}
function setTradeAuto (target) {
  const counts = {};
  counts[target.dataset.tag] = 'auto';
  updateTrade(counts);
  renderTrade();
}

function resetTrade () {
  const counts = {};
  for (const [tagId, unit] of Object.entries(STATE.meshData.units[0])) {
    if (unitInGameType(unit)) {
      counts[tagId] = unit.initial_count;
    }
  }
  updateTrade(counts);
  renderTrade();
}

function updateTrade (counts, norender) {
  const units = STATE.meshData.units[0];
  for (const [tagId, count] of Object.entries(counts)) {
    const unit = units[tagId];
    if (unit.tradeable) {
      if (count == 'max') {
        unit.count = unit.max;
      } else if (count == 'auto') {
        const remaining = pointsRemaining();
        const currentValue = unit.count * unit.cost;
        unit.count = Math.min(Math.max(0, Math.floor((remaining + currentValue) / unit.cost)), unit.max);
      } else {
        unit.count = Math.min(count, unit.max);
      }
      STRAT.counts[tagId] = unit.count;
      let remaining = unit.count;
      unit.markers.forEach(marker => {
        if (!marker.flags.includes('invis')) {
          if (remaining) {
            remaining--;
          } else {
            marker.flags.push('invis');
          }
        }
      });
      if (remaining) {
        unit.markers.forEach(marker => {
          if (remaining) {
            let idx = marker.flags.indexOf('invis');
            if (idx !== -1) {
              marker.flags.splice(idx, 1);
              remaining--;
            }
          }
        });
      }
      if (!norender) {
        const unitCount = document.querySelector(`.tradeUnit__count-${tagId}`);
        unitCount.value = unit.count;
      }
    }
  }

  if (!norender) {
    saveState();
    renderPointsRemaining();
    renderUnits();
    renderTradeResult();
    if (STATE.detach) {
      showDetach();
    }
  }
}

function renderTradeResult () {
  const units = STATE.meshData.units[0];
  hideTooltip();
  const tradeResult = document.getElementById('tradeResult');
  tradeResult.style.height = `${tradeResult.scrollHeight}px`;
  tradeResult.innerHTML = '';
  const tradeResultUntrade = document.getElementById('tradeResultUntrade');
  tradeResultUntrade.style.height = `${tradeResultUntrade.scrollHeight}px`;
  tradeResultUntrade.innerHTML = '';

  let allocated = {};
  STRAT.splits.forEach(split => {
    split.units.forEach(splitUnit => {
      if (!(splitUnit.tag in allocated)) {
        allocated[splitUnit.tag] = 0;
      }
      allocated[splitUnit.tag] += splitUnit.count;
    });
  });

  Object.entries(units).forEach(([tagId, unit]) => {
    if (!unitInGameType(unit)) {
      return;
    }
    const splitUnit = dce('div', 'split__unit', `${unit.count}x ${unitName(unit, unit.count)}`);
    splitUnit.dataset.tag = tagId;
    if (unit.count == 0) {
      splitUnit.classList.add('split__unit--zero');
    }
    const diff = unit.count - (allocated[tagId] || 0); 
    if (diff != 0) {
      const splitDiff = dce('div', 'split__unit_diff', Math.abs(diff));
      if (diff > 0) {
        splitDiff.classList.add('split__unit_diff--under');
      } else if (diff < 0) {
        splitDiff.classList.add('split__unit_diff--over');
      }
      splitUnit.append(splitDiff);
    }
    let container = unit.tradeable ? tradeResult : tradeResultUntrade;
    container.append(splitUnit);
  });
  tradeResult.style.height = 'auto';
  tradeResultUntrade.style.height = 'auto';
}

function unitInGameType (unit) {
  return unit.markers.some(marker => {
    return marker.game_types.includes('all') || marker.game_types.includes(STRAT.game_type);
  });
}

function renderUnits () {
  if (!STRAT.game_type) {
    return;
  }
  const gt = getGameType();
  const gtMarkers = document.querySelector(`.mapLocations-${gt.game_type}`);
  document.querySelectorAll('.mapLocation-unit').forEach(el => {
    el.remove();
  });
  for (const [, units] of Object.entries(STATE.meshData.units)) {
    Object.values(units).forEach((unit, i) => {
      if (!unitInGameType(unit)) {
        return;
      }
      unit.markers.forEach(marker => {
        if (!marker.flags.includes('invis')) {
          let x = marker.position[0] / STATE.meshData.width;
          let y = marker.position[1] / STATE.meshData.height;
          const mapLoc = dce('div', 'mapLocation mapLocation-unit');
          mapLoc.style.backgroundColor = UNIT_COLORS[i % UNIT_COLORS.length];
          mapLoc.style.top = `${y*100}%`;
          mapLoc.style.left = `${x*100}%`;
          gtMarkers.prepend(mapLoc);
        }
      });
    });
  }
}

function unitName (unit, count) {
  let spellings = unit.spellings;
  if (!spellings) {
    Object.entries(STATE.meshData.units[0]).forEach(([tagId, u]) => {
      if (tagId == unit.tag) {
        spellings = u.spellings;
      }
    });
  }
  if (count == 1) {
    return spellings[0];
  } else {
    return spellings[1] || spellings[0];
  }
}

function renderTrade (focusTag) {
  const units = STATE.meshData.units[0];
  hideTooltip();
  const tradeable = document.getElementById('tradeable');
  tradeable.style.height = `${tradeable.scrollHeight}px`;
  tradeable.innerHTML = '';
  const untradeable = document.getElementById('untradeable');
  untradeable.style.height = `${untradeable.scrollHeight}px`;
  untradeable.innerHTML = '';
  let hasUntradeable = false;
  Object.entries(units).forEach(([tagId, unit], i) => {
    if (!unitInGameType(unit)) {
      return;
    }
    const uName = unitName(unit, unit.max);
    if (unit.tradeable || unit.count) {
      const tradeUnit = dce('div', 'tradeUnit');
      tradeUnit.dataset.tag = tagId;

      const tradeUnitColor = dce('div', 'tradeUnit__color');
      tradeUnitColor.style.backgroundColor = UNIT_COLORS[i % UNIT_COLORS.length];
      tradeUnit.append(tradeUnitColor);

      tradeUnit.append(dce('span', 'tradeUnit__name', uName));
      if (unit.tradeable) {
        const tradeUnitRange = dce('input', 'tradeUnit__range');
        tradeUnit.append(dce('span', 'tradeUnit__cost', ` • Cost: ${unit.cost}`));
        tradeUnit.append(dce('br'));

        tradeUnitRange.type = 'range';
        tradeUnitRange.name = tagId;
        tradeUnitRange.max = unit.max;
        tradeUnitRange.value = unit.count;
        tradeUnit.append(tradeUnitRange);

        const unitCountField = dce('input', `tradeUnit__count tradeUnit__count-${tagId}`);
        unitCountField.type = 'number';
        unitCountField.name = tagId;
        unitCountField.max = unit.max;
        unitCountField.min = 0;
        unitCountField.value = unit.count;
        tradeUnit.append(unitCountField);
        tradeUnit.append(dce('span', 'tradeUnit__max', ` / ${unit.max}`));

        tradeUnit.prepend(dce('span', 'tradeUnit__set tradeUnit__set_min', 'None'));
        tradeUnit.prepend(dce('span', 'tradeUnit__set tradeUnit__set_max', 'Max'));
        tradeUnit.prepend(dce('span', 'tradeUnit__set tradeUnit__set_auto', 'Auto'));

        tradeable.append(tradeUnit);

        if (focusTag != null && focusTag == tagId) {
          unitCountField.focus();
        }
      } else {
        hasUntradeable = true;
        tradeUnit.append(dce('span', 'tradeUnit__count', `: ${unit.count}`));
        // tradeUnit.append(dce('span', 'tradeUnit__cost', ' • Untradeable'));
        untradeable.append(tradeUnit);
      }
      tradeUnit.prepend(dce('span', 'tradeUnit__set tradeUnit__set_detach', 'Detach'));
    }
  });
  if (hasUntradeable) {
    untradeable.prepend(dce('h4', 'untradeable__head', 'Untradeable'));
  }
  tradeable.style.height = 'auto';
  untradeable.style.height = 'auto';
  renderPointsRemaining();
  renderTradeResult();
}

function pointsRemaining () {
  const units = STATE.meshData.units[0];
  let total = 0;
  let maxPoints = 0;
  Object.values(units).forEach(unit => {
    if (!unitInGameType(unit)) {
      return;
    }
    if (unit.tradeable) {
      total += unit.cost * unit.count;
      maxPoints += unit.cost * unit.initial_count;
    }
  });
  return maxPoints - total;
}

function renderPointsRemaining () {
  const remaining = pointsRemaining();
  const pr = document.getElementById('pointsRemaining');
  pr.classList.toggle('pointsRemaining--debt', remaining < 0);
  pr.classList.toggle('pointsRemaining--surplus', remaining > 0);
  pr.innerText = `Points remaining: ${remaining}`;
}

const UNIT_COLORS = [
  '#FFA100',
  '#D63031',
  '#00B894',
  '#0984E3',
  '#1A347B',
  '#A29BFE',
  '#FF7675',
  '#6C3483',
  '#FDE87E',
  '#007F39',
];

function setFavicon () {
  var link = document.querySelector("link[rel~='icon']");
  if (!link) {
    link = dce('link');
    link.rel = 'icon';
    document.head.appendChild(link);
  }
  link.href = `${BASE_URL}${STATE.meshData.overhead_path}`;
}

function getGameType () {
  if (STRAT.game_type) {
    return STATE.meshData.game_types.find(gt => gt.game_type == STRAT.game_type);
  }
}

function setTitle () {
  let title = STATE.meshData.name;
  if (STRAT.game_type) {
    title += ` - ${getGameType().game_type_long}`;
  }
  title += ' - Myth Strategy Maker';
  document.title = title;
}

function clearDrawPreview () {
  document.querySelectorAll('.map-draw').forEach(canvas => {
    canvas.style.cursor = null;
  });
  document.querySelectorAll('.map-draw-preview').forEach(previewCanvas => {
    const ctx = previewCanvas.getContext("2d");
    ctx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
  });
}

const TERRAIN_COLORS = {
  '255-255-0-255': 'Water (Dwarf Depth)',
  '255-165-0-255': 'Water (Human Depth)',
  '255-0-0-255': 'Water (Giant Depth)',
  '128-0-128-255': 'Water (Deep)',
  '100-100-100-255': 'Sloped',
  '255-192-203-255': 'Steep',
  '0-0-0-0': 'Grass',
  '245-245-150-255': 'Desert',
  '200-200-200-255': 'Rocky',
  '215-175-135-255': 'Marsh',
  '200-230-250-255': 'Snow',
  '100-200-100-255': 'Forest',
  '0-255-255-255': 'Loathing Special',
  '255-0-255-255': 'Unused',
  '0-0-255-255': 'Walking Impassable',
  '0-255-0-255': 'Scenery Impassable',
};

function mapMouseLeave (e, mapTT) {
  const map = e.target.closest('.map-image');
  const idx = map.dataset.idx - 0;
  const mapInfo = document.querySelector(`.map-info-${idx}`);
  mapInfo.innerHTML = '';
  mapInfo.classList.remove('map-info--show');
}

function mapMouseMove (e, mapTT) {
  const map = e.target.closest('.map-image');
  const idx = map.dataset.idx - 0;

  const terrainCanvas = document.querySelector(`.map-terrain-${idx}`);
  const u = e.offsetX / terrainCanvas.offsetWidth;
  const v = e.offsetY / terrainCanvas.offsetHeight;
  const x = Math.round(u * terrainCanvas.width);
  const y = Math.round(v * terrainCanvas.height);

  const terrainCtx = terrainCanvas.getContext("2d");
  let [r, g, b, a] = Array.from(terrainCtx.getImageData(x, y, 1, 1).data);
  if (a > 0) {
    a = 255;
  }

  const closestLine = getLineAtPoint(terrainCanvas, u, v);

  const closestUnit = getUnitAtPoint(terrainCanvas, u, v);

  const mapInfo = document.querySelector(`.map-info-${idx}`);
  const terrain = TERRAIN_COLORS[`${r}-${g}-${b}-${a}`];
  if (terrain || closestLine || closestUnit) {
    if (terrain) {
      mapInfo.innerText = `Terrain: ${terrain}`;
      mapInfo.classList.add('map-info--show');
      const terrainColorSquare = dce('span', 'map-terrain-color-square');
      const color = `rgb(${r},${g},${b})`;
      if (a != 0) {
        terrainColorSquare.style.backgroundColor = color;
      }
      mapInfo.prepend(terrainColorSquare);
    }
    if (closestLine) {
      if (terrain) {
        mapInfo.append(' / ');
      }
      if (closestLine.line.split != null) {
        let splitName = `P${closestLine.line.split+1}`;
        const split = STRAT.splits[closestLine.line.split];
        if (split && split.name) {
          splitName += `: ${split.name} - `;
        }
        mapInfo.append(dce('span', 'lineSplit', splitName));
      }
      const ll = lineLength(closestLine.line);
      mapInfo.append('distance: ');
      const llEl = dce('span', 'lineLength', ll.toFixed(2));
      if (closestLine.line.color) {
        llEl.style.borderColor = closestLine.line.color;
      }
      mapInfo.append(llEl);
    }
    if (closestUnit) {
      const unitDot = dce('span', 'unitDot');
      unitDot.style.backgroundColor = UNIT_COLORS[closestUnit.i % UNIT_COLORS.length];
      mapInfo.append(unitDot);
      mapInfo.append(unitName(closestUnit, 1));
    }
  } else {
    mapInfo.innerHTML = '';
    mapInfo.classList.remove('map-info--show');
  }
}

function lineLength (line) {
  if (line.points.length < 2) {
    return 0;
  } else {
    let len = 0;
    for (let i = 1; i < line.points.length; i++) {
      const du = (line.points[i-1].u - line.points[i].u) * STATE.meshData.width;
      const dv = (line.points[i-1].v - line.points[i].v) * STATE.meshData.height;
      len += Math.sqrt((du * du) + (dv * dv));
    }
    return len;
  }
}

function drawMouseMove (e) {
  const canvas = e.target;
  const idx = canvas.dataset.idx - 0;
  const lines = STRAT.mapViews[idx].lines;
  let line = lines[lines.length-1];
  const previewCanvas = document.querySelector(`.map-draw-preview-${idx}`);
  const ctx = previewCanvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const u = e.offsetX / canvas.offsetWidth;
  const v = e.offsetY / canvas.offsetHeight;

  if (STATE.drawMode && line && !line.complete) {
    let lastPoint = line.points[line.points.length - 1];
    ctx.beginPath();
    ctx.moveTo(
      lastPoint.u * canvas.width,
      lastPoint.v * canvas.height
    );
    ctx.lineTo(
      u * canvas.width,
      v * canvas.height
    );
    ctx.lineWidth = 15;
    ctx.strokeStyle = line.color;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.stroke();
  }
}

function renderLines () {
  if (!STRAT.mapViews) {
    return;
  }
  STRAT.mapViews.forEach((mapView, i) => {
    const canvas = document.querySelector(`.map-draw-${i}`);
    const ctx = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    const lines = mapView.lines;
    lines.forEach(({color, points, selected}) => {
      if (points.length > 1) {
        ctx.beginPath();
        ctx.moveTo(
          points[0].u * canvas.width,
          points[0].v * canvas.height
        );
        for (let i = 1; i < points.length; i++) {
          ctx.lineTo(
            points[i].u * canvas.width,
            points[i].v * canvas.height
          );
        }
        if (selected) {
          ctx.lineWidth = 35;
          ctx.strokeStyle = '#000';
          ctx.stroke();
          ctx.lineWidth = 25;
          ctx.strokeStyle = '#fff';
          ctx.stroke();
        }
        ctx.lineWidth = 15;
        if (!color) {
          color = '#fff';
        }
        ctx.strokeStyle = color;
        ctx.stroke();
      }
    });
  });
}

function addMapView () {
  const mapView = {
    lines: [],
  };
  STRAT.mapViews.push(mapView);
  renderMapViews();
  saveState();
  return mapView;
}

function deleteMapView (target) {
  const idx = target.dataset.idx - 0;
  if (confirm(`Delete map view? ID: ${idx+1} (lines: ${STRAT.mapViews[idx].lines.length})`)) {
    STRAT.mapViews.splice(idx, 1);
    renderMapViews();
    saveState();
  }
}

function startLine (lines, color, split) {
  if (!color) {
    color = '#ffffff';
  }
  const line = {
    color: color,
    split: split,
    points: [],
  };
  lines.push(line);
  return line;
}

function drawEscape () {
  if (!endLine()) {
    drawModeOff();
  }
}

function endLine () {
  let wasChanged = false;
  let lastWasCompleted = false;
  STRAT.mapViews.forEach(mapView => {
    const lines = mapView.lines;
    // Loop in reverse cos we're potentially splicing
    const lastIdx = lines.length - 1;
    for (let i = lastIdx; i > -1; i--) {
      const line = lines[i];
      if ('completed' in line) {
        delete line.completed;
        wasChanged = true;
      }
      if (line.points.length < 2) {
        // Clean up dud lines
        lines.splice(i, 1);
        wasChanged = true;
      } else if (!line.complete) {
        line.complete = true;
        wasChanged = true;
        if (i == lastIdx) {
          lastWasCompleted = true;
        }
      }
    }
  });

  document.querySelectorAll('.map-draw').forEach(canvas => {
    canvas.style.cursor = null;
  });

  if (wasChanged) {
    saveState();
  }

  return lastWasCompleted;
}

function distanceToSegment (px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(px - ax, py - ay); // degenerate segment
  
  // project point onto segment, clamped to 0-1
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lenSq));
  
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

function getLineAtPoint (canvas, u, v, threshold = 8) {
  // work in buffer pixels so threshold is meaningful
  const px = u * canvas.width;
  const py = v * canvas.height;
  // scale threshold to buffer space too
  const t = threshold * (canvas.width / canvas.offsetWidth);

  let closest = null;
  let closestDist = Infinity;

  const idx = canvas.dataset.idx - 0;

  STRAT.mapViews[idx].lines.forEach((line, index) => {
    const { points } = line;
    for (let i = 0; i < points.length - 1; i++) {
      const dist = distanceToSegment(
        px, py,
        points[i].u * canvas.width, points[i].v * canvas.height,
        points[i+1].u * canvas.width, points[i+1].v * canvas.height
      );
      if (dist < t && dist < closestDist) {
        closestDist = dist;
        closest = { line, index };
      }
    }
  });

  return closest;
}

function getUnitAtPoint (canvas, u, v, threshold = 6) {
  if (!STRAT.game_type) {
    return;
  }
  // work in buffer pixels so threshold is meaningful
  const px = u * canvas.width;
  const py = v * canvas.height;
  // scale threshold to buffer space too
  const t = threshold * (canvas.width / canvas.offsetWidth);
  const t2 = t * t;

  let closest = null;
  let closestDistSq = Infinity;

  for (const units of Object.values(STATE.meshData.units)) {
    Object.entries(units).forEach(([tag, unit], i) => {
      if (unitInGameType(unit)) {
        unit.markers.forEach(marker => {
          if (marker.flags.includes('invis')) {
            return;
          }
          const mu = (marker.position[0] / STATE.meshData.width) * canvas.width;
          const mv = (marker.position[1] / STATE.meshData.height) * canvas.height;
          const du = mu - px;
          const dv = mv - py;
          const distSq = (du * du) + (dv * dv);
          if (distSq < t2 && distSq < closestDistSq) {
            closestDistSq = distSq;
            closest = { tag, i, unit, marker };
          }
        });
      }
    });
  }

  return closest;
}

function selectLineAtPoint (shift, double, canvas, u, v) {
  const result = getLineAtPoint(canvas, u, v);
  const idx = canvas.dataset.idx - 0;
  let selectColor;
  STRAT.mapViews[idx].lines.forEach((line, i) => {
    if (result && result.index == i) {
      line.selected = !line.selected;
      selectColor = line.color;
    } else if (!shift) {
      delete line.selected;
    }
  });
  if (double && selectColor) {
    STRAT.mapViews[idx].lines.forEach(line => {
      if (line.color == selectColor) {
        line.selected = true;
      }
    });
  }
  renderLines();
  return result;
}


function mapClick (e, clickState) {
  const ts = performance.now();
  let double = false;
  if (
    clickState.lastClick &&
    (ts - clickState.lastClick) < 450 &&
    clickState.x == e.x &&
    clickState.y == e.y
  ) {
    double = true;
  }
  clickState.lastClick = ts;
  clickState.x = e.x;
  clickState.y = e.y;

  const canvas = e.target;

  const u = e.offsetX / canvas.offsetWidth;
  const v = e.offsetY / canvas.offsetHeight;

  if (!STATE.drawMode) {
    const selected = selectLineAtPoint(e.shiftKey, double, canvas, u, v);
    if (double && !selected) {
      drawModeOn();
      double = false;
    } else {
      return;
    }
  }

  const idx = canvas.dataset.idx - 0;
  const lines = STRAT.mapViews[idx].lines;
  let line = lines[lines.length-1];
  if (!line || line.complete) {
    line = startLine(lines, STATE.drawColor, STATE.drawSplit);
  }

  if (double && line.points.length > 1) {
    endLine();
  } else {
    if (line.points.length) {
      let lastPoint = line.points[line.points.length - 1];
      const ctx = canvas.getContext("2d");
      ctx.beginPath();

      if (line.points.length > 1) {
        let penultPoint = line.points[line.points.length - 2];
        ctx.moveTo(
          penultPoint.u * canvas.width,
          penultPoint.v * canvas.height
        );
        ctx.lineTo(
          lastPoint.u * canvas.width,
          lastPoint.v * canvas.height
        );
      } else {
        ctx.moveTo(
          lastPoint.u * canvas.width,
          lastPoint.v * canvas.height
        );
      }
      ctx.lineTo(
        u * canvas.width,
        v * canvas.height
      );
      ctx.strokeStyle = line.color;
      ctx.lineWidth = 15;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.stroke();
    }
    const point = {u, v};
    line.points.push(point);

    if (double) {
      endLine();
    } else {
      saveState();
    }
  }
}

function stripFormat (name) {
  // The private use symbol (often the apple symbol) \uF8FF is sometimes used
  // but isn't displayable in game without interface changes (e.g. JINN) Just strip it
  return name.replace(/[\\|]./gi, '').replace(/[\r\n]/gi, '').replace(/\uF8FF/g, '');
}

const LIGATURES = {
    'æ': 'ae', 'Æ': 'AE',
    'œ': 'oe', 'Œ': 'OE',
    'ß': 'ss',
    'ð': 'd',  'Ð': 'D',
    'þ': 'th', 'Þ': 'Th',
    'ł': 'l',  'Ł': 'L',
    'ĳ': 'ij', 'Ĳ': 'IJ',
};
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

function slugifyMapGt (map, gt) {
  let typeSlug = slugify(gt.game_type_long);
  let mapSlug = slugify(map.name);
  return `${typeSlug}-${mapSlug}`;
}

async function buildMap () {
  initLocalState();

  document.querySelector('.map__title').innerText = STATE.meshData.name;
  if (STATE.meshData.plugins && STATE.meshData.plugins.length) {
    document.querySelector('.map__plugin').innerText = `Plugins: ${STATE.meshData.plugins.join(', ')}`;
  }
  renderTimeLimit(STRAT.time_limit);

  const mapHead = document.querySelector('.map__gt');
  // TODO link to stratIdx
  if (STRAT.game_type) {
    const gt = getGameType();
    const gtLink = dce('a', `gtLink gtLink-${gt.game_type}`, gt.game_type_long);
    mapHead.append(gtLink);

    mapHead.append(' ');

    const mapUrl = `https://mythstats.bagrada.net/maps#${slugifyMapGt(STATE.meshData, gt)}`;
    const mapLink = dce('a', 'map__status_button historicalLink', '📜');
    mapLink.href = mapUrl;
    mapLink.target = '_blank';
    tooltip(mapLink, 'Look up historical trades');
    mapHead.append(mapLink);
  } else {
    mapHead.append(dce('span', 'gtChoose', 'Choose game type:'));
    STATE.meshData.game_types.forEach((gt, i) => {
      const gtLink = dce('a', `gtLink gtLink-${gt.game_type}`, gt.game_type_long);
      gtLink.addEventListener('click', (e) => {
        e.preventDefault();
        // TODO re-render all the things
        selectGameType(gt.game_type);
      });

      if (i > 0) {
        mapHead.append(' • ');
      }
      mapHead.append(gtLink);
    });
  }

  // await render3d();
  
  renderMapViews();

  renderRest();
}

function buildAlternatingPlane (width, depth, segmentsX, segmentsZ) {
  const positions = [];
  const uvs = [];
  const indices = [];

  const sx = width / segmentsX;
  const sz = depth / segmentsZ;

  for (let j = 0; j <= segmentsZ; j++) {
    for (let i = 0; i <= segmentsX; i++) {
      const x = i * sx - width / 2;
      const z = j * sz - depth / 2;
      positions.push(x, 0, z);

      uvs.push(i / segmentsX, 1 - j / segmentsZ); // flip v to match PlaneGeometry convention
    }
  }

  const vertsPerRow = segmentsX + 1;

  for (let j = 0; j < segmentsZ; j++) {
    for (let i = 0; i < segmentsX; i++) {
      const a = j * vertsPerRow + i;
      const b = a + 1;
      const c = a + vertsPerRow;
      const d = c + 1;

      const flip = (i + j) % 2 === 1;

      if (!flip) {
        indices.push(a, c, d);
        indices.push(a, d, b);
      } else {
        indices.push(a, c, b);
        indices.push(c, d, b);
      }
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setAttribute('uv1', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function placeTarget (target) {
  if (!STATE.three.scene) {
    return;
  }
  [
    [0.3, 5, 0xffff00, 1, true],
    [5, 1, 0xffff00, 0.6, false],
  ].forEach(([radius, height, color, opacity, shadow]) => {
    const cylinderHeight = height * (2 / 3);
    const geometry = new THREE.CylinderGeometry(radius, radius, cylinderHeight, 16);
    const material = new THREE.MeshPhongMaterial({
      transparent: opacity != 1,
      color,
      opacity,
    });
    const cylinder = new THREE.Mesh(geometry, material);
    if (shadow) {
      cylinder.castShadow = true;
    }
    cylinder.position.set(
      target.position[0] - STATE.meshData.width/2,
      target.position[2] + cylinderHeight / 3,
      target.position[1] - STATE.meshData.height/2,
    );
    STATE.three.scene.add(cylinder);
  });
}

async function render3d () {
  document.getElementById('map3d').style.display = 'block';
  // Set up renderer and canvas
  const width = 1440;
  const height = 864;
  STATE.three.canvas = document.getElementById('map3d_canvas');
  STATE.three.canvas.width = width;
  STATE.three.canvas.height = height;
  STATE.three.renderer = new THREE.WebGPURenderer({
    canvas: STATE.three.canvas,
    antialias: true,
    // powerPreference: 'high-performance',
  });
  STATE.three.renderer.toneMapping = THREE.NoToneMapping;
  STATE.three.renderer.setPixelRatio(window.devicePixelRatio);
  STATE.three.renderer.setSize(width, height);
  STATE.three.renderer.setAnimationLoop(threeRender);
  STATE.three.renderer.shadowMap.enabled = true;
  STATE.three.renderer.shadowMap.type = THREE.PCFShadowMap;

  // Camera
  const fov = 50;
  const near = 1;
  const far = 90000;
  STATE.three.camera = new THREE.PerspectiveCamera(
    fov,
    width / height,
    near,
    far
  );
  STATE.three.camera.position.set(0, STATE.meshData.height * 1.2, STATE.meshData.height);
  STATE.three.camera.rotation.x = -Math.PI/2;
  // STATE.three.camera.lookAt(0, 0, 0);

  // Controls
  STATE.three.controls = new MapControls(STATE.three.camera, document.getElementById('map3d'));
  STATE.three.controls.enableDamping = true;
  STATE.three.controls.dampingFactor = 0.05;
  STATE.three.controls.maxDistance = STATE.meshData.height * 3;
  STATE.three.controls.maxPolarAngle = (Math.PI / 2) - (Math.PI / 64);
  STATE.three.controls.saveState();

  // Scene + lighting
  STATE.three.scene = new THREE.Scene();

  STATE.three.dirLight = new THREE.DirectionalLight(0xffffff, 1);
  STATE.three.dirLight.position.set(
    STATE.meshData.width * 2,
    STATE.meshData.height,
    -STATE.meshData.height * 2,
  );

  STATE.three.dirLight.castShadow = true;
  STATE.three.dirLight.shadow.camera.left = -STATE.meshData.width;
  STATE.three.dirLight.shadow.camera.right = STATE.meshData.width;
  STATE.three.dirLight.shadow.camera.top = STATE.meshData.height;
  STATE.three.dirLight.shadow.camera.bottom = -STATE.meshData.height;

  STATE.three.dirLight.shadow.camera.near = STATE.meshData.height * 2;
  STATE.three.dirLight.shadow.camera.far = STATE.meshData.height * 4;

  STATE.three.dirLight.shadow.intensity = 1;

  STATE.three.dirLight.shadow.bias = 0;
  // STATE.three.dirLight.shadow.bias = 0.001;
  STATE.three.dirLight.shadow.normalBias = 0;
  // STATE.three.dirLight.shadow.normalBias = 0.0001;
  STATE.three.dirLight.shadow.radius = 3;
  STATE.three.dirLight.shadow.blurSamples = 16;

  STATE.three.dirLight.shadow.mapSize.width = STATE.meshData.width * 10;
  STATE.three.dirLight.shadow.mapSize.height = STATE.meshData.height * 10;

  STATE.three.dirLight.shadow.camera.updateProjectionMatrix();

  // STATE.three.scene.add(new THREE.CameraHelper(STATE.three.dirLight.shadow.camera));

  STATE.three.scene.add(STATE.three.dirLight);
  STATE.three.scene.add(new THREE.AmbientLight(0xffffff, 0.8));

  // Terrain
  const terrainW = STATE.meshData.width;
  const terrainH = STATE.meshData.height;
  const segW = STATE.meshData.width;
  const segH = STATE.meshData.height;
  const heightRange = STATE.meshData.height_range;
  const maxHeight = STATE.meshData.max_height;
  const minHeight = STATE.meshData.min_height;
  const terrainGeom = buildAlternatingPlane(
    terrainW, terrainH,
    segW, segH
  );

  const loader = new THREE.TextureLoader();
  const colormap = await loader.loadAsync(`${BASE_URL}${STATE.meshData.cmap_path}`);
  colormap.colorSpace = THREE.SRGBColorSpace;
  const shadowmap = await loader.loadAsync(`${BASE_URL}${STATE.meshData.shadow_path}`);
  shadowmap.colorSpace = THREE.LinearSRGBColorSpace;

  const heightmap = await loader.loadAsync(`${BASE_URL}${STATE.meshData.height_path}`);
  heightmap.offset.set(
    -0.5 / segW,
    -0.5 / segH
  );

  const terrainMat = new THREE.MeshToonNodeMaterial({
    // wireframe: true,
    fragmentNode: shader(
      colormap, shadowmap,
      STATE.meshData.lighting.dark_color, STATE.meshData.lighting.light_color,
      STATE.meshData.lighting.dark_fraction, STATE.meshData.lighting.light_fraction,
      STATE.meshData.lighting.transition_point
    ),
    // lightMap: shadowmap,
    displacementMap: heightmap,
    displacementScale: heightRange,
    displacementBias: minHeight,
    // side: THREE.DoubleSide,
  });
  STATE.three.terrain = new THREE.Mesh(terrainGeom, terrainMat);
  STATE.three.terrain.receiveShadow = true;
  // STATE.three.scene.add(new THREE.AxesHelper(Math.max(terrainW*2, terrainH*2)));
  STATE.three.scene.add(STATE.three.terrain);

  // Border
  const borderDepth = 2;
  const borderY = (maxHeight + minHeight)/2;
  const borderMat = new THREE.MeshStandardMaterial({
    color: 0x444444,
  });
  
  const borderGeomTop = new THREE.BoxGeometry(
    terrainW + borderDepth*2,
    heightRange,
    borderDepth
  );
  const borderTop = new THREE.Mesh(borderGeomTop, borderMat);
  borderTop.position.z = -terrainH/2 - borderDepth/2;
  borderTop.position.y = borderY;
  STATE.three.scene.add(borderTop);

  const borderGeomRight = new THREE.BoxGeometry(
    borderDepth,
    heightRange,
    terrainH + borderDepth * 2
  );
  const borderRight = new THREE.Mesh(borderGeomRight, borderMat);
  borderRight.position.x = -terrainW/2 - borderDepth/2;
  borderRight.position.y = borderY;
  STATE.three.scene.add(borderRight);
  
  const borderGeomBottom = new THREE.BoxGeometry(
    terrainW + borderDepth * 2,
    heightRange,
    borderDepth
  );
  const borderBottom = new THREE.Mesh(borderGeomBottom, borderMat);
  borderBottom.position.z = terrainH/2 + borderDepth/2;
  borderBottom.position.y = borderY;
  STATE.three.scene.add(borderBottom);
  
  const borderGeomLeft = new THREE.BoxGeometry(
    borderDepth,
    heightRange,
    terrainH + borderDepth * 2
  );
  const borderLeft = new THREE.Mesh(borderGeomLeft, borderMat);
  borderLeft.position.x = terrainW/2 + borderDepth/2;
  borderLeft.position.y = borderY;
  STATE.three.scene.add(borderLeft);

  await STATE.three.renderer.init();
}

function threeRender () {
  // STATE.three.dirLight.shadow.camera.updateProjectionMatrix();
  // STATE.three.controls.update();
  STATE.three.renderer.render(STATE.three.scene, STATE.three.camera);
}

function renderMapViews () {
  if (STRAT.mapViews && STRAT.mapViews.length) {
    hideTooltip();
    const mapImages = document.querySelector('.mapImages');
    mapImages.innerHTML = '';
    STRAT.mapViews.forEach((mapView, i) => {
      // const name = mapView.name || (i+1);
      const mapImage = dce('div', 'map-image');
      mapImage.dataset.idx = i;
      let cMap = dce('img', 'map-base');
      cMap.src = `${BASE_URL}${STATE.meshData.cmap_path}`;
      cMap.width = STATE.meshData.width;
      cMap.height = STATE.meshData.height;
      mapImage.appendChild(cMap);

      let terrainMap = new Image();
      let scenMap = new Image();
      var terrainCanvas = dce('canvas', `map-overlay map-terrain map-terrain-${i}`);
      terrainCanvas.dataset.idx = i;
      const terrainCtx = terrainCanvas.getContext("2d", {willReadFrequently: true});
      terrainMap.onload = () => {
        terrainCanvas.width = mapImage.offsetWidth;
        terrainCanvas.height = mapImage.offsetHeight;
        terrainCtx.imageSmoothingEnabled = false;
        terrainCtx.drawImage(terrainMap, 0, 0, mapImage.offsetWidth, mapImage.offsetHeight);
        scenMap.src = `${BASE_URL}${STATE.meshData.impassable_scenery_path}`;
      };
      scenMap.onload = () => {
        terrainCtx.imageSmoothingEnabled = false;
        terrainCtx.drawImage(scenMap, 0, 0, mapImage.offsetWidth, mapImage.offsetHeight);
      };
      mapImage.appendChild(terrainCanvas);
      terrainMap.src = `${BASE_URL}${STATE.meshData.terrain_path}`;

      let sMap = dce('img', 'map-overlay map-shadow');
      sMap.src = `${BASE_URL}${STATE.meshData.shadow_path}`;
      sMap.width = STATE.meshData.width;
      sMap.height = STATE.meshData.height;
      mapImage.appendChild(sMap);

      STATE.meshData.game_types.forEach(gt => {
        if (gt.game_type != STRAT.game_type) {
          return;
        }
        const gtMarkers = dce('div', `mapLocations mapLocations-${gt.game_type}`);
        const teamObservers = {};
        gt.locations.forEach(loc => {
          if (loc.position) {
            let x = loc.position[0] / STATE.meshData.width;
            let y = loc.position[1] / STATE.meshData.height;
            let type = 'location';
            if (loc.observer) {
              if (teamObservers[loc.team]) {
                return;
              }
              teamObservers[loc.team] = true;
              type = 'spawn';
            } else if (loc.target) {
              placeTarget(loc);
              type = `target mapLocation-${loc.type}`;
            } else if (loc.projectile) {
              type = `projectile mapLocation-${loc.type.replace(/ /g, '-')}`;
            }
            const mapLoc = dce('div', `mapLocation mapLocation-${type}`);
            if (loc.target && loc.flag_number) {
              mapLoc.innerText = loc.flag_number;
            }
            if (loc.team != null) {
              if (loc.observer || gt.game_type != 'stamp') {
                mapLoc.innerText = `Team ${loc.team+1}`;
              }
              if (gt.game_type == 'ctf' && loc.observer) {
                mapLoc.classList.add('mapLocation--hidden');
              }
            }
            mapLoc.style.top = `${y*100}%`;
            mapLoc.style.left = `${x*100}%`;
            gtMarkers.append(mapLoc);
          }
          mapImage.append(gtMarkers);
        });

      });

      let drawMapPreview = dce('canvas', `map-overlay map-draw-preview map-draw-preview-${i}`);
      drawMapPreview.width = STATE.meshData.width * 8;
      drawMapPreview.height = STATE.meshData.height * 8;
      mapImage.appendChild(drawMapPreview);

      let drawMap = dce('canvas', `map-overlay map-draw map-draw-${i}`);
      drawMap.dataset.idx = i;
      drawMap.width = STATE.meshData.width * 8;
      drawMap.height = STATE.meshData.height * 8;
      mapImage.appendChild(drawMap);

      const mapInfo = dce('div', `map-info map-info-${i}`);
      mapImage.append(mapInfo);

      const mapDetails = dce('div', 'map-details');
      if (STRAT.mapViews.length > 1) {
        const mapDelete = dce('span', 'map_button map_delete', '🗑️');
        tooltip(mapDelete, 'Delete map view');
        mapDetails.append(mapDelete);
      }
      mapImage.append(mapDetails);

      const clickState = {};
      drawMap.addEventListener('click', (e) => mapClick(e, clickState));
      drawMap.addEventListener('mouseenter', drawMouseMove);
      drawMap.addEventListener('mousemove', drawMouseMove);
      drawMap.addEventListener('mouseleave', drawMouseMove);

      // const mapTT = tooltip(mapImage);
      const mapTT = null;
      mapImage.addEventListener('mouseenter', (e) => mapMouseMove(e, mapTT));
      mapImage.addEventListener('mousemove', (e) => mapMouseMove(e, mapTT));
      mapImage.addEventListener('mouseleave', (e) => mapMouseLeave(e, mapTT));


      mapImages.append(mapImage);
    });
  }

  renderMapLocations();
  renderLines();
}

function renderMapLocations () {
  if (!STRAT.game_type) {
    return;
  }
  const gt = getGameType();
  document.querySelectorAll('.mapLocations').forEach((el) => {
    el.classList.remove('mapLocations--show');
  });
  document.querySelectorAll(`.mapLocations-${gt.game_type}`).forEach((el) => {
    el.classList.add('mapLocations--show');
  });
}

function summarizeAllocation (allocation) {
  if (!allocation) {
    return '';
  }
  let summaryParts = [];
  allocation.forEach(u => {
    if (u.count) {
      let summaryPart = `${u.count}x ${unitName(u, u.count)}`;
      summaryParts.push(summaryPart);
    }
  });
  return summaryParts.join(', ');
}

function addPlayer () {
  STRAT.splits.push({
    units: [],
    color: UNIT_COLORS[STRAT.splits.length % UNIT_COLORS.length],
  });
  saveState();
  renderSplits();
  return STRAT.splits.length - 1;
}

function toggleEditSplit (target, cancel) {
  const input = target.querySelector('.split__name_input');
  if (cancel) {
    input.value = target.dataset.initialName;
    saveSplit(target);
  } else {
    if (target.classList.contains('split--edit')) {
      saveSplit(target);
    } else {
      showEditSplit(target);
    }
  }
}

function toggleDrawMode (idx) {
  let newColor;
  if (idx != null) {
    newColor = STRAT.splits[idx].color;
  } else {
    newColor = null;
  }
  if (!STATE.drawMode || (newColor && STATE.drawColor != newColor)) {
    STATE.drawMode = true;
    STATE.drawColor = newColor;
    STATE.drawSplit = idx;
  } else {
    STATE.drawColor = null;
    STATE.drawSplit = null;
    STATE.drawMode = false;
  }
  document.querySelector('.map__status_draw_active').style.backgroundColor = STATE.drawColor;
  endLine();
  document.body.classList.toggle('drawMode', STATE.drawMode);
}

function drawModeOn () {
  if (!STRAT.game_type) {
    return;
  }
  STATE.drawMode = true;
  STATE.drawColor = null;
  STATE.drawSplit = null;
  document.querySelector('.map__status_draw_active').style.backgroundColor = STATE.drawColor;
  document.body.classList.add('drawMode');
}

function drawModeOff () {
  // Note, this doesn't call endLine because the call site already does.
  // Change if we reuse this elsewhere
  STATE.drawColor = null;
  STATE.drawSplit = null;
  STATE.drawMode = false;
  document.querySelector('.map__status_draw_active').style.backgroundColor = null;
  document.body.classList.remove('drawMode');
  clearDrawPreview();
}

function showEditSplit (target, initialName) {
  const input = target.querySelector('.split__name_input');
  let idx = target.dataset.idx - 0;
  input.value = STRAT.splits[idx].name || '';
  target.dataset.initialName = (initialName != null) ? initialName : input.value;
  target.classList.add('split--edit');
  input.focus();
}

function deleteSplit (target) {
  let idx = target.dataset.idx - 0;
  if (confirm(`Delete split? ID: ${idx+2}`)) {
    STRAT.splits.splice(idx, 1);
    saveState();
    renderSplits();
    renderTradeResult();
  }
}

function moveSplitUp (target) {
  let idx = target.dataset.idx - 0;
  if (STRAT.splits.length > 1 && idx > 0) {
    const split = STRAT.splits.splice(idx, 1)[0];
    STRAT.splits.splice(idx-1, 0, split);
  }
  saveState();
  renderSplits();
}

function moveSplitDown (target) {
  let idx = target.dataset.idx - 0;
  if (STRAT.splits.length > 1 && idx < STRAT.splits.length - 1) {
    const split = STRAT.splits.splice(idx, 1)[0];
    STRAT.splits.splice(idx+1, 0, split);
  }
  saveState();
  renderSplits();
}

function setSplitColorCustom (target) {
  const split = target.closest('.split');
  let idx = split.dataset.idx - 0;
  STRAT.splits[idx].color = target.value;
  saveState();
  split.querySelector('.split__head').style.backgroundColor = target.value;
}

function setSplitColor (target) {
  let colorIdx = target.dataset.idx - 0;
  if (colorIdx == null) {
    return;
  }
  const split = target.closest('.split');
  let idx = split.dataset.idx - 0;
  STRAT.splits[idx].color = UNIT_COLORS[colorIdx % UNIT_COLORS.length];
  saveState();
  const initialName = split.dataset.initialName;
  renderSplits(idx, initialName);
}

function saveSplit (target) {
  let idx = target.dataset.idx - 0;
  const val = target.querySelector('.split__name_input').value;
  STRAT.splits[idx].name = val;
  saveState();
  renderSplits();
}

function hideDetach () {
  document.querySelector('.detach').classList.remove('detach--show');
  STATE.detach = null;
}

function removeDetachSplit (target) {
  STATE.detach.splits.splice(target.dataset.idx - 0, 1);
  hideTooltip();
  showDetach();
}

function editDetach (target) {
  const tagId = target.dataset.tag;
  document.querySelectorAll('.tradeUnit').forEach(tradeUnit => {
    if (tagId == tradeUnit.dataset.tag) {
      initDetach(tradeUnit.querySelector('.tradeUnit__set_detach'), target.dataset.split, target);
    }
  });
}

function initDetach (target, focusSplit, editTarget) {
  STATE.detach = {
    el: target,
    balanced: true,
  };
  showDetach(focusSplit, editTarget);
}

function showDetach (focusSplit, editTarget) {
  const detach = document.querySelector('.detach');

  if (!STATE.detach.pos) {
    if (editTarget) {
      const cr = editTarget.getBoundingClientRect();
      STATE.detach.pos = {
        top: window.scrollY + cr.top + 'px',
        left: '395px',
      };
    } else {
      const cr = STATE.detach.el.getBoundingClientRect();
      STATE.detach.pos = {
        top: STATE.detach.el.offsetTop + 'px',
        left: (STATE.detach.el.offsetLeft + cr.width + 10) + 'px',
      };
    }
  }

  if (!STATE.detach.unit) {
    const tradeUnit = STATE.detach.el.closest('.tradeUnit');
    const tagId = tradeUnit.dataset.tag;
    if (!tagId) {
      return;
    }
    STATE.detach.unit = tagId;
  }

  const units = STATE.meshData.units[0];
  const unit = units[STATE.detach.unit];

  hideTooltip();
  const splitsEl = document.querySelector('.detach__splits');
  splitsEl.innerHTML = '';

  if (!STATE.detach.splits) {
    STATE.detach.splits = [];
    STATE.detach.players = [];
    const filtered = STRAT.splits.filter(s => s.units.some(u => u.tag == STATE.detach.unit));
    const balanceCheck = unit.count / Math.max(1, filtered.length);
    STRAT.splits.forEach((split, i) => {
      STATE.detach.players.push(split);
      split.units.forEach(splitUnit => {
        if (splitUnit.tag == STATE.detach.unit) {
          if (splitUnit.count != balanceCheck) {
            STATE.detach.balanced = false;
          }
          STATE.detach.splits.push({
            count: splitUnit.count,
            player: i,
          });
        }
      });
    });
  }

  if (!STATE.detach.splits.length) {
    const firstSplit = {
      new: true,
      count: unit.count,
      player: 0,
    };
    if (STATE.detach.players.length == 1) {
      firstSplit.player = 0;
    }
    STATE.detach.splits.push(firstSplit);
  }

  const perSplit = Math.floor(unit.count / Math.max(1, STATE.detach.splits.length));
  let surplus = unit.count - (perSplit * STATE.detach.splits.length);

  document.querySelector('.detach__balanced').checked = !!STATE.detach.balanced;

  let focusCount;

  let lastPlayer;
  let ordered = true;
  let splitsAllocated = true;
  STATE.detach.splits.forEach((split, i) => {
    const splitEl = dce('div', 'detach__split');
    const splitCountField = dce('input', 'detach__count_field');
    if (!focusCount || focusSplit == i) {
      focusCount = splitCountField;
    }
    if (ordered && lastPlayer != null && split.player == null) {
      split.player = lastPlayer + 1;
    }

    if (split.player != null && lastPlayer != null && (split.player - lastPlayer) != 1) {
      ordered = false;
    }
    lastPlayer = split.player;

    if (STATE.detach.balanced || split.count == null) {
      split.count = perSplit;
      if (surplus > 0) {
        split.count++;
        surplus--;
      }
    }

    splitCountField.type = 'number';
    splitCountField.max = unit.max;
    splitCountField.min = 0;
    splitCountField.name = `count_${i}`;
    splitCountField.value = split.count;

    if (STATE.detach.players.length < STATE.detach.splits.length) {
      for (let extraI = STATE.detach.players.length; extraI < STATE.detach.splits.length; extraI++) {
        STATE.detach.players.push({
          new: true,
          color: UNIT_COLORS[STATE.detach.players.length % UNIT_COLORS.length],
        });
        STATE.detach.splits[extraI].player = extraI;
      }
    }

    const splitPlayers = dce('div', 'detach__players');

    let allocated = false;
    STATE.detach.players.forEach((player, playerI) => {
      const playerNum = `P${playerI+1}`;
      const splitPlayer = dce('div', 'detach__player', playerNum);
      splitPlayer.dataset.player = playerI;
      let bg = player.color;
      if (playerI == split.player) {
        allocated = true;
        splitPlayer.classList.add('detach__player--selected');
      }
      splitPlayer.style.backgroundColor = bg;
      let playerTitle = playerNum;
      if (player.new) {
        splitPlayer.classList.add('detach__player--new');
        playerTitle += ' (New)';
      }
      if (player.name) {
        playerTitle += `: ${player.name}`;
      }
      const alloc = summarizeAllocation(player.units);
      if (alloc) {
        playerTitle += ` - ${alloc}`;
      }
      tooltip(splitPlayer, playerTitle);
      splitPlayers.append(splitPlayer);
    });
    if (!allocated) {
      splitEl.classList.add('detach__split--unallocated');
      splitsAllocated = false;
    }

    if (STATE.detach.splits.length < 8) {
      const addPlayer = dce('div', 'detach__player detach__player_add', '+');
      tooltip(addPlayer, 'Add player');
      splitPlayers.append(addPlayer);
    }

    const splitRemove = dce('div', 'detach__split_remove', '×');
    tooltip(splitRemove, 'Remove split');

    splitEl.append(splitCountField);
    splitEl.append(dce('div', 'detach__arrow', '➔'));
    splitEl.append(splitPlayers);
    splitEl.append(splitRemove);

    splitEl.dataset.idx = i;

    splitsEl.append(splitEl);
  });

  document.querySelector('.detach__submit').disabled = !splitsAllocated;


  document.querySelector('.detach__unit').innerText = `${unitName(unit, unit.max)}: ${unit.count} / ${unit.max}`;

  detach.classList.add('detach--show');
  detach.style.top = STATE.detach.pos.top;
  detach.style.left = STATE.detach.pos.left;
  if (focusCount) {
    focusCount.focus();
    focusCount.select();
  }
}

function setDetachPlayer (target) {
  const split = target.closest('.detach__split');
  let player = target.dataset.player;
  if (player == null) {
    STATE.detach.players.push({
      new: true,
      color: UNIT_COLORS[STATE.detach.players.length % UNIT_COLORS.length],
    });
    player = STATE.detach.players.length - 1;
  }
  STATE.detach.splits[split.dataset.idx].player = (player - 0);
  showDetach(split.dataset.idx);
}

function detachUnit () {
  STRAT.splits.forEach((currentSplit, i) => {
    if (!STATE.detach.splits.some(split => split.player == i)) {
      let unitIdx = -1;
      currentSplit.units.forEach((unit, i) => {
        if (unit.tag == STATE.detach.unit) {
          unitIdx = i;
        }
      });
      if (unitIdx != -1) {
        currentSplit.units.splice(unitIdx, 1);
      }
    }
  });
  STATE.detach.splits.forEach(split => {
    if (split.player == null) {
      return;
    }
    const player = STATE.detach.players[split.player];
    let splitPlayer;
    let found = false;
    if (player.new) {
      const playerId = addPlayer();
      splitPlayer = STRAT.splits[playerId];
    } else {
      splitPlayer = STRAT.splits[split.player];
      splitPlayer.units.forEach(unit => {
        if (unit.tag == STATE.detach.unit) {
          found = true;
          unit.count = split.count;
        }
      });
    }
    if (!found) {
      splitPlayer.units.push({
        tag: STATE.detach.unit,
        count: split.count,
      });
    }
  });

  saveState();

  renderSplits();
  renderTradeResult();
  hideDetach();
}

function renderSplits (editIdx, editInitialName) {
  hideTooltip();
  const splits = document.getElementById('splits');
  // splits.style.height = `${splits.scrollHeight}px`;
  splits.innerHTML = '';
  const addButton = dce('div', 'split__add', '+ Add player');
  splits.append(addButton);

  const units = STATE.meshData.units[0];
  let totalValue = 0;
  for (const unit of Object.values(units)) {
    if (unitInGameType(unit)) {
      totalValue += (unit.count * unit.cost);
    }
  }
  STRAT.splits.forEach((split, i) => {
    const splitEl = dce('div', 'split');
    splitEl.dataset.idx = i;
    const splitHead = dce('div', 'split__head', `P${i+1}: `);
    if (split.name) {
      const splitName = dce('div', 'split__name', split.name);
      splitHead.append(splitName);
    }
    const splitNameForm = dce('form', 'split__edit_form');
    const splitNameInput = dce('input', 'split__name_input');
    splitNameInput.name = 'split_name';
    splitNameInput.value = split.name;
    splitNameForm.append(splitNameInput);

    const splitColorPicker = dce('div', 'split__colorpicker');
    for (let colorI = 0; colorI < 8; colorI++) {
      const splitColor = dce('div', 'split__color');
      const splitColorCircle = dce('div', 'split__color_circle');
      splitColorCircle.style.backgroundColor = UNIT_COLORS[colorI % UNIT_COLORS.length];
      splitColor.append(splitColorCircle);
      splitColor.dataset.idx = colorI;
      splitColorPicker.append(splitColor);
    }
    const splitColorCustom = dce('div', 'split__color');
    const splitColorCircleCustom = dce('div', 'split__color_circle split__color_circle--custom');
    splitColorCircleCustom.append(dce('div', 'split__color_text', '+'));
    splitColorCustom.append(splitColorCircleCustom);
    const splitColorInput = dce('input', 'split__color_input');
    splitColorInput.type = 'color';
    if (split.color) {
      splitColorInput.value = split.color;
    }
    splitColorCustom.append(splitColorInput);
    splitColorPicker.append(splitColorCustom);

    splitNameForm.append(splitColorPicker);
    splitHead.append(splitNameForm);

    if (split.color) {
      splitHead.style.backgroundColor = split.color;
    }
    if (STRAT.splits.length > 1) {
      if (i > 0) {
        const splitUp = dce('div', 'split__button split__up', '↑');
        splitHead.prepend(splitUp);
        tooltip(splitUp, 'Move player up');
      }
      if (i < STRAT.splits.length - 1) {
        const splitDown = dce('div', 'split__button split__down', '↓');
        splitHead.prepend(splitDown);
        tooltip(splitDown, 'Move player down');
      }
    }
    const splitEdit = dce('div', 'split__button split__edit', '🏷️');
    splitHead.prepend(splitEdit);
    tooltip(splitEdit, 'Edit split');

    const splitDraw = dce('div', 'split__button split__draw', '🖍️');
    splitHead.prepend(splitDraw);
    tooltip(splitDraw, `Draw split (${i+1})`);

    const splitDelete = dce('div', 'split__button split__delete', '🗑️');
    splitHead.prepend(splitDelete);
    tooltip(splitDelete, 'Delete split');

    const splitAllocation = dce('div', 'split__allocation');
    let hasUnits = false;
    let value = 0;
    split.units.forEach(u => {
      if (u.count) {
        const unit = units[u.tag];
        value += (u.count * unit.cost);
        hasUnits = true;
        const splitUnit = dce('div', 'split__unit', `${u.count}x ${unitName(u, u.count)}`);
        splitUnit.dataset.tag = u.tag;
        splitUnit.dataset.split = i;
        splitUnit.dataset.splitCount = u.count;
        splitAllocation.append(splitUnit);
      }
    });
    const pct = (value / totalValue) * 100;
    splitHead.append(` — ${Math.round(pct)}%`);
    if (!hasUnits) {
      splitAllocation.append(dce('p', 'help', 'Use the Detach buttons to allocate units'));
    }
    const splitNotes = dce('textarea', 'split__notes', split.notes);
    splitNotes.placeholder = 'Add notes…';

    splitEl.append(splitHead);
    splitEl.append(splitAllocation);
    splitEl.append(splitNotes);
    splits.append(splitEl);

    splitNotes.style.height = '38px';
    splitNotes.style.height = `${splitNotes.scrollHeight}px`;

    if (editIdx != null && editIdx == i) {
      showEditSplit(splitEl, editInitialName);
      splitNameInput.focus();
    }
  });
  // splits.style.height = 'auto';
}

function toggleNoDrawings () {
  STATE.nodrawings = !STATE.nodrawings;
  saveState();
  renderNoDrawings();
}

function toggleNoTrading () {
  STATE.notrading = !STATE.notrading;
  saveState();
  renderNoTrading();
}

function toggleNoClutter () {
  STATE.noclutter = !STATE.noclutter;
  saveState();
  renderNoClutter();
}

function toggleTerrain () {
  STATE.terrain = !STATE.terrain;
  saveState();
  renderTerrain();
}

function toggleNoShadow () {
  STATE.noshadow = !STATE.noshadow;
  saveState();
  renderNoShadow();
}

function renderNoDrawings () {
  document.body.classList.toggle('nodrawings', !!STATE.nodrawings);
}

function renderNoTrading () {
  document.body.classList.toggle('notrading', !!STATE.notrading);
}

function renderNoClutter () {
  document.body.classList.toggle('noclutter', !!STATE.noclutter);
}

function renderTerrain () {
  document.body.classList.toggle('terrain', !!STATE.terrain);
}

function renderNoShadow () {
  document.body.classList.toggle('noshadow', !!STATE.noshadow);
}

function serialiseState () {
  const obj = {};
  [
    'stratIdx', 'strats',
    
    'notrading', 'terrain', 'noclutter', 'nodrawings', 'noshadow',
  ].forEach(k => {
    obj[k] = STATE[k];
  });
  return JSON.stringify(obj);
}

function initLocalState () {
  const localState = fetchState();
  if (localState) {
    Object.assign(STATE, localState);
  } else {
    saveState();
  }
  STRAT = STATE.strats[STATE.stratIdx];
  renderNoGametype();
  processTradeableUnits();
  if (STRAT.mapViews && !STRAT.mapViews.length) {
    addMapView();
  }
}

function stateKey () {
  return `${STATE.meshData.mesh_dir}|${STATE.stratIdx}`;
}

function saveState () {
  const key = stateKey();
  const content = serialiseState();
  localStorage.setItem(key, content);
}

window.saveState = saveState;

function fetchState () {
  const key = stateKey();
  const value = localStorage.getItem(key);
  if (value) {
    const parsed = JSON.parse(value);
    return parsed;
  }
}

function downloadState () {
  const content = serialiseState();

  const link = dce('a');
  const file = new Blob([content], { type: 'text/plain' });
  link.href = URL.createObjectURL(file);
  link.download = "state.json";
  link.click();
  URL.revokeObjectURL(link.href);
}

const TOOLTIP = dce('div', 'tooltip');
document.body.appendChild(TOOLTIP);
let TOOLTIP_ID = 1;
let TOOLTIP_CONTENTS = {};

let lastClientX, lastClientY;

document.addEventListener("mousemove", (e) => {
  lastClientX = e.clientX;
  lastClientY = e.clientY;
  positionTooltip();
});

window.addEventListener("scroll", () => {
  requestAnimationFrame(positionTooltip);
}, { passive: true });

function positionTooltip () {
  const offset = 10;
  const smudge = 10;
  const tooltipWidth = TOOLTIP.offsetWidth;
  const tooltipHeight = TOOLTIP.offsetHeight;

  const willOverflowRight = lastClientX + offset + smudge + tooltipWidth > window.innerWidth;
  const willOverflowBottom = lastClientY + offset + smudge + tooltipHeight > window.innerHeight;

  const left = willOverflowRight
    ? lastClientX - tooltipWidth - offset
    : lastClientX + offset;

  const top = willOverflowBottom
    ? lastClientY - tooltipHeight - offset
    : lastClientY + offset;

  TOOLTIP.style.left = `${Math.max(left, offset)}px`;
  TOOLTIP.style.top = `${Math.max(top, offset)}px`;
}

function tooltip (el, content) {
  let node = dce('span', 'tooltip__plain', content);
  tooltipNode(el, node);
  return node;
}

function tooltipNode (el, node) {
  TOOLTIP.innerHTML = '';
  let tipId = TOOLTIP_ID++;
  el.dataset.tooltip_id = tipId;
  TOOLTIP_CONTENTS[tipId] = node;
  el.classList.add('tooltip__target');
  el.addEventListener("mouseenter", () => {
    showTooltip(el);
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

document.addEventListener('click', (e) => {
  if (e.target.classList.contains('split__add')) {
    addPlayer();
  } else if (e.target.classList.contains('split__delete')) {
    deleteSplit(e.target.closest('.split'));
  } else if (e.target.classList.contains('split__edit')) {
    toggleEditSplit(e.target.closest('.split'));
  } else if (e.target.classList.contains('split__draw')) {
    const split = e.target.closest('.split');
    let idx = split.dataset.idx - 0;
    toggleDrawMode(idx);
  } else if (e.target.classList.contains('map__status_draw_active')) {
    toggleDrawMode();
  } else if (e.target.classList.contains('map__status_add_view')) {
    addMapView();
  } else if (e.target.classList.contains('map_delete')) {
    deleteMapView(e.target.closest('.map-image'));
  } else if (e.target.classList.contains('split__up')) {
    moveSplitUp(e.target.closest('.split'));
  } else if (e.target.classList.contains('split__down')) {
    moveSplitDown(e.target.closest('.split'));
  } else if (e.target.classList.contains('split__color')) {
    setSplitColor(e.target);
  } else if (e.target.classList.contains('split__color_circle')) {
    setSplitColor(e.target.closest('.split__color'));
  } else if (e.target.classList.contains('tradeUnit__set_min')) {
    setTradeMin(e.target.closest('.tradeUnit'));
  } else if (e.target.classList.contains('tradeUnit__set_max')) {
    setTradeMax(e.target.closest('.tradeUnit'));
  } else if (e.target.classList.contains('tradeUnit__set_auto')) {
    setTradeAuto(e.target.closest('.tradeUnit'));
  } else if (e.target.classList.contains('tradeUnit__set_detach')) {
    initDetach(e.target);
  } else if (e.target.classList.contains('split__unit')) {
    editDetach(e.target);
  } else if (e.target.classList.contains('split__unit_diff')) {
    editDetach(e.target.closest('.split__unit'));
  } else if (e.target.classList.contains('detach__cancel')) {
    hideDetach();
  } else if (e.target.classList.contains('detach__player')) {
    setDetachPlayer(e.target);
  } else if (e.target.classList.contains('detach__add_split')) {
    STATE.detach.splits.push({
      new: true,
      count: 0,
    });
    showDetach();
  } else if (e.target.classList.contains('detach__split_remove')) {
    removeDetachSplit(e.target.closest('.detach__split'));
  } else if (e.target.classList.contains('terrain_toggle')) {
    toggleTerrain();
  } else if (e.target.classList.contains('noshadow_toggle')) {
    toggleNoShadow();
  } else if (e.target.classList.contains('notrading_toggle')) {
    toggleNoTrading();
  } else if (e.target.classList.contains('nodrawings_toggle')) {
    toggleNoDrawings();
  } else if (e.target.classList.contains('noclutter_toggle')) {
    toggleNoClutter();
  } else if (e.target.classList.contains('download_state')) {
    downloadState();
  } else if (e.target.id == 'resetTrade') {
    resetTrade();
  }
});

document.addEventListener('submit', (e) => {
  if (e.target.classList.contains('split__edit_form')) {
    e.preventDefault();
    saveSplit(e.target.closest('.split'));
  } else if (e.target.classList.contains('detach__form')) {
    e.preventDefault();
    detachUnit();
  }
});

function inputFocused () {
  const activeTag = document.activeElement.tagName.toLowerCase();
  if (
    activeTag === 'input' ||
    activeTag === 'textarea' ||
    document.activeElement.isContentEditable
  ) {
    return true;
  }
  return false;
}

document.addEventListener('keyup', (e) => {
  if (e.key == 'Escape') {
    if (STATE.detach) {
      hideDetach();
    } else if (e.target.classList.contains('split__name_input')) {
      toggleEditSplit(e.target.closest('.split'), true);
    } else if (STATE.drawMode) {
      drawEscape();
    }
  } else if (!inputFocused()) {
    if (e.key == 'd') {
      toggleDrawMode();
    } else if (e.key == 't') {
      toggleTerrain();
    } else if (e.key == 's') {
      toggleNoShadow();
    } else if (e.code.match(/Digit\d/)) {
      const idx = (e.key - 0) - 1;
      if (idx > -1 && idx < STRAT.splits.length) {
        toggleDrawMode(idx);
      }
    } else if (e.key == 'Backspace' || e.key == 'Delete') {
      if (inputFocused()) {
        return;
      }
      let didDelete = false;
      STRAT.mapViews.forEach(mapView => {
        const toDelete = [];
        const lines = mapView.lines;
        lines.forEach((line, i) => {
          if (line.selected) {
            // Unshift so that sequential splices always take place from
            // largest idx to smallest, and so can be done in one pass
            toDelete.unshift(i);
          }
        });
        toDelete.forEach(delIdx => {
          lines.splice(delIdx, 1);
          didDelete = true;
        });
      });
      if (didDelete) {
        renderLines();
        saveState();
      }
    }
  }
});

document.addEventListener('input', (e) => {
  if (e.target.classList.contains('tradeUnit__range')) {
    const counts = {};
    counts[e.target.name] = e.target.value;
    updateTrade(counts);
  } else if (e.target.classList.contains('tradeUnit__count')) {
    const tradeUnit = e.target.closest('.tradeUnit');
    const tagId = tradeUnit.dataset.tag;
    const counts = {};
    counts[tagId] = e.target.value;
    updateTrade(counts);
    renderTrade(tagId);
  } else if (e.target.classList.contains('split__notes')) {
    e.target.style.height = '38px';
    e.target.style.height = `${e.target.scrollHeight}px`;
    const split = e.target.closest('.split');
    const idx = split.dataset.idx;
    STRAT.splits[idx].notes = e.target.value;
    saveState();
  } else if (e.target.classList.contains('strat_notes')) {
    e.target.style.height = '44px';
    e.target.style.height = `${e.target.scrollHeight}px`;
    STRAT.notes = e.target.value;
    saveState();
  } else if (e.target.classList.contains('map__time')) {
    STRAT.time_limit = e.target.value;
    saveState();
  } else if (e.target.classList.contains('split__name_input')) {
    const split = e.target.closest('.split');
    const idx = split.dataset.idx;
    STRAT.splits[idx].name = e.target.value;
    saveState();
  } else if (e.target.classList.contains('detach__count_field')) {
    const split = e.target.closest('.detach__split');
    STATE.detach.splits[split.dataset.idx].count = (e.target.value - 0);
    STATE.detach.balanced = false;
    document.querySelector('.detach__balanced').checked = false;
  } else if (e.target.classList.contains('split__color_input')) {
    setSplitColorCustom(e.target);
  }
});

document.addEventListener('change', (e) => {
  if (e.target.classList.contains('detach__balanced')) {
    STATE.detach.balanced = document.querySelector('.detach__balanced').checked;
    showDetach();
  }
});

initTooltips();
route();