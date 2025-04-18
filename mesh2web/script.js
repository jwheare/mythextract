(function () {

const AUTOADVANCE = true;

let start = document.querySelector('.start');
let audio = document.querySelector('.narration_audio');
let narration = document.querySelector('.narration');
let bg_initial = document.querySelector('.bg_initial');
let text = document.querySelector('.narration_text');
let pre_cutscene = document.querySelector('.pre_cutscene_video');
let post_cutscene = document.querySelector('.post_cutscene_video');
let nextLink = document.querySelector('.next_link');
let skip = document.querySelector('.skip');

let START_TIME = 0;
let PLAYING = false;
let CURRENT_MEDIA;

function showPregame (num) {
    console.log('show pregame', num);
    let selector = `pregame-${num}`;
    let pregame = document.querySelector(`.${selector}`);
    if (pregame) {
        pregame.classList.add('pregame--show');
    }
    document.querySelectorAll('.pregame').forEach((pre) => {
        if (!pre.classList.contains(selector)) {
            pre.classList.remove('pregame--show');
        }
    });
}

async function cyclePregames (start_time) {
    for (let i = 1; i < DURATIONS.length; i++) {
        let dur = DURATIONS[i-1];
        console.log(`next pregame in ${dur}s`);
        await new Promise(resolve => setTimeout(resolve, dur*1000));
        if (start_time != START_TIME) {
            console.log('start time changed, abort cycle', start_time, START_TIME);
            return;
        }
        showPregame(i);
    }
}

function resetPage () {
    console.log('resetPage');

    document.body.classList.remove('playing');

    START_TIME = 0
    PLAYING = false;
    CURRENT_MEDIA = null;

    console.log('reset audio');
    audio.pause();
    audio.currentTime = 0;

    if (post_cutscene) {
        console.log('reset post video after timeout');
        setTimeout(() => {
            console.log('reset post video');
            post_cutscene.pause();
            post_cutscene.currentTime = 0;
            post_cutscene.classList.remove('video--show');
        }, 0);
    }
    if (pre_cutscene) {
        console.log('reset pre video after timeout');
        setTimeout(() => {
            console.log('reset pre video');
            pre_cutscene.pause();
            pre_cutscene.currentTime = 0;
            pre_cutscene.classList.remove('video--show');
        }, 0);
    }
    onEndCutscene();

    console.log('reset narration');
    narration.style.transition = 'none';
    narration.classList.remove('narration--show');
    narration.offsetHeight;
    narration.style.transition = '';

    bg_initial.style.transition = 'none';
    bg_initial.classList.remove('bg_initial--show');
    bg_initial.offsetHeight;
    bg_initial.style.transition = '';

    text.style.transition = '';
    text.style.transform = '';

    console.log('reset start');
    start.classList.remove('start--hide');

    console.log('reset pregame');
    showPregame(0);
}

window.addEventListener('pageshow', (e) => {
    console.log(`pageshow ${window.location.href} prerender=${document.prerendering} persisted=${e.persisted} document.wasDiscarded=${document.wasDiscarded}`); 
    if (e.persisted && !document.prerendering) {
        resetPage();
    }
});

function startNarration (start_time) {
    setTimeout(() => {
        if (start_time != START_TIME) {
            console.log('start time changed, abort', start_time, START_TIME);
            return;
        }
        let distance = (430+text.clientHeight);
        let duration = distance/SCROLL_RATE;
        console.log('start narration', start_time, `transition duration=${duration} audio=${audio.duration}s`);
        text.style.transition = `transform ${duration}s linear`;
        text.style.transform = `translateY(${-distance}px)`;
        narration.classList.add('narration--show');

        // Hide initial background after delay to avoid transition clashing
        setTimeout(() => {
            bg_initial.classList.remove('bg_initial--show');
        }, 1000);

        cyclePregames(START_TIME);
    }, INITIAL_DELAY);
}

function play () {
    if (PLAYING) {
        return;
    }

    if (pre_cutscene) {
        console.log('play pre cutscene');
        pre_cutscene.play().then(() => {
            console.log('play pre cutscene success');
            onPlayCutscene(pre_cutscene);
            playing();
        }).catch(playCatch);
    } else {
        startJournal().then(playing);
    }
}

function onPlayCutscene (cutscene) {
    CURRENT_MEDIA = cutscene;
    cutscene.classList.add('video--show');
    if (cutscene == pre_cutscene) {
        skip.classList.add('skip--show');
    }
}
function onEndCutscene (cutscene) {
    if (cutscene) {
        cutscene.classList.remove('video--show');
    }
    CURRENT_MEDIA = null;
    if (cutscene == pre_cutscene) {
        skip.classList.remove('skip--show');
    }
}
skip.addEventListener('click', (e) => {
    if (CURRENT_MEDIA) {
        console.log('skip');
        CURRENT_MEDIA.currentTime = CURRENT_MEDIA.duration;
    }
});

function playCatch (e) {
    console.warn('play failed', e);
}

function playing () {
    PLAYING = true;
    document.body.classList.add('playing');
    start.classList.add('start--hide');
}

document.querySelector('.container').addEventListener('click', (e) => {
    play();
});

function startJournal () {
    console.log('play audio');
    return audio.play().then(() => {
        console.log('play audio success');

        START_TIME = Date.now();
        console.log('start journal', START_TIME, 'delay', INITIAL_DELAY);
        bg_initial.classList.add('bg_initial--show');
        startNarration(START_TIME);

    }).catch(playCatch);
}

audio.addEventListener('ended', (e) => {
    console.log('audio end');

    narration.classList.remove('narration--show');

    if (post_cutscene) {
        setTimeout(() => {
            console.log('play post cutscene');
            post_cutscene.play().then(() => {
                console.log('play post cutscene success');
                onPlayCutscene(post_cutscene);
            }).catch(playCatch);
        }, 2000);
    } else {
        autoAdvance();
    }
});

function autoAdvance () {
    if (AUTOADVANCE && nextLink) {
        setTimeout(() => {
            console.log('autoadvance', nextLink.href);
            window.location.href = nextLink.href;
        }, 2000);
    }
}

if (post_cutscene) {
    post_cutscene.addEventListener('ended', (e) => {
        console.log('post cutscene end');
        onEndCutscene(post_cutscene);
        autoAdvance();
    });
}
if (pre_cutscene) {
    pre_cutscene.addEventListener('ended', (e) => {
        console.log('pre cutscene end');
        onEndCutscene(pre_cutscene);
        startJournal();
    });
}

// function buildScript () {
//     let script = [];
//     let time = 0;
//     let duration = 0;
//     if (pre_cutscene) {
//         duration = pre_cutscene.duration * 1000;
//         end_time = time + duration;
//         script.push({
//             start_time: time,
//             duration: duration,
//             end_time: end_time,
//             actions: ['video'],
//             video: pre_cutscene,
//         });
//         time = end_time;
//     }

//     let audio_remaining = (audio.duration * 1000);

//     duration = INITIAL_DELAY;
//     end_time = time + duration;
//     script.push({
//         start_time: time,
//         duration: duration,
//         end_time: end_time,
//         actions: ['audio'],
//         audio: audio,
//     });
//     audio_remaining-= duration;
//     time = end_time;

//     let narration_start = time;

//     for (let i = 0; i < DURATIONS.length; i++) {
//         duration = DURATIONS[i] * 1000;
//         if (duration > audio_remaining) {
//             duration = audio_remaining;
//         } else if (i == (DURATIONS.length - 1) && duration < audio_remaining) {
//             duration = audio_remaining;
//         }
//         end_time = time + duration;
//         script.push({
//             start_time: time,
//             duration: duration,
//             end_time: end_time,
//             actions: ['audio', 'narration', 'pregame'],
//             audio: audio,
//             narration_start: narration_start,
//             pregame: i
//         });
//         audio_remaining-= duration;
//         time = end_time;
//     }
//     if (audio_remaining) {
//         duration = audio_remaining;
//         end_time = time + duration;
//         script.push({
//             start_time: time,
//             duration: duration,
//             end_time: end_time,
//             actions: ['audio', 'narration'],
//             audio: audio,
//             narration_start: narration_start,
//         });
//         audio_remaining-= duration;
//         time = end_time;
//     }

//     if (post_cutscene) {
//         duration = post_cutscene.duration * 1000;
//         end_time = time + duration;
//         script.push({
//             start_time: time,
//             duration: duration,
//             end_time: end_time,
//             actions: ['video'],
//             video: post_cutscene,
//         });
//         time = end_time;
//     }

//     console.log(script);
//     return script;
// }

// let media_loaded = new Promise(resolve => {
//     let media_durations = 0;
//     if (pre_cutscene) {
//         media_durations++;
//         pre_cutscene.addEventListener('durationchange', (e) => {
//             console.log('pre_cutscene durationchange', pre_cutscene.duration);
//             if (!--media_durations) {
//                 resolve();
//             }
//         });
//     }
//     media_durations++;
//     audio.addEventListener('durationchange', (e) => {
//         console.log('audio durationchange', audio.duration);
//         if (!--media_durations) {
//             resolve();
//         }
//     });
//     if (post_cutscene) {
//         media_durations++;
//         post_cutscene.addEventListener('durationchange', (e) => {
//             console.log('post_cutscene durationchange', post_cutscene.duration);
//             if (!--media_durations) {
//                 resolve();
//             }
//         });
//     }
// });
// media_loaded.then(buildScript);

})();