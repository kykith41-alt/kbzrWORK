"""Arrange, mix and master the five songs from NOVYE_PESNI.md into WAV.

Usage: python3 songs.py <models_dir> <out_dir> [01,02,...]
then:  python3 remaster.py <out_dir>/<song>.wav <song>_m.wav  (-10 LUFS, -2.2 dBTP ceiling before MP3)

pip: numpy scipy librosa soundfile pyloudnorm pyworld sherpa-onnx
models_dir must contain (from github.com/k2-fsa/sherpa-onnx/releases, tag tts-models):
  vits-piper-ru_RU-dmitri-medium/
"""
import sys, os, json, subprocess
import numpy as np
import librosa
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import *  # noqa
from vocals import Voice, render_line

# ---------------------------------------------------------------- lyrics

L1_CH = ["На девятом этаже опять не гаснет свет,",
         "Я пишу тебе «привет» — и стираю: смысла нет.",
         "Снег ложится на балконы, будто белые бинты,",
         "Этот город заживает. Заживёшь ли ты?"]
L1_V = ["Лифт застрял между «вчера» и «навсегда»,",
        "В батареях кто-то плачет — это просто вода.",
        "Я считаю окна: в каждом чей-то тёплый дом,",
        "А в моём — лишь пепельница, тишина и бетон.",
        "За стеной опять скандал, посуды звон,",
        "Я убавил этот мир, как телефон.",
        "Во дворе скрипят качели в темноте —",
        "Детство где-то там, но больше не во мне."]

L2_V1 = ["Моя тень сегодня вышла без меня,",
         "Хлопнув дверью, не оставив мне огня.",
         "Она бродит по дворам, где я молчал,",
         "Обнимает тех, кого я потерял.",
         "Я стою в пустой прихожей, как в снегу,",
         "Позвал бы её обратно — не могу.",
         "В отражении витрин — она, не я:",
         "Улыбается чужая тень моя."]
L2_CH = ["Кто-то ходит в моём сером пальто,",
         "Говорит моим голосом — но не то.",
         "Отпусти меня домой, моя тень,",
         "Я устал быть кем-то каждый новый день."]
L2_BR = ["Тише, тише — это просто свет погас.",
         "Тише, тише — это я, но не сейчас."]
L2_V2 = ["Утром лужи, солнце режет по глазам,",
         "Я не верю ни часам, ни голосам.",
         "Ты звонишь — а я слышу тишину.",
         "Как сказать тебе, что я у тени в плену?"]

L3_V1 = ["Холодно, холодно — пальцы не гнутся,",
         "Окна горят, но ко мне не вернутся.",
         "Ноги хотят бежать — куда, не знаю,",
         "Я на этом льду себя теряю.",
         "Тени тянут руки, я не вижу лиц,",
         "Белый шум в ушах и тысячи границ.",
         "Я кричу в рукав, чтобы никто не слышал,",
         "Снег на капюшоне — я опять не вышел."]
L3_CH = ["Замерзаю, замерзаю,",
         "Где я, кто я — я не знаю.",
         "Позови меня по имени хоть раз —",
         "Я не вижу вас, я не вижу вас."]
L3_V2 = ["Разобрали на куски, как старый дом,",
         "В каждой комнате чужие — я не в нём.",
         "Капюшон на голову, наушники в уши,",
         "Я бы рассказал вам — только кто бы слушал.",
         "«Мама, всё в порядке», — вру опять в трубку,",
         "Я сжимаю холод, как чужую руку.",
         "Белый-белый двор и белый-белый свет,",
         "Я ищу свои следы — а их здесь нет."]

L4_V1 = ["Мокрый асфальт, апрель, ты опять без зонта,",
         "Тушь течёт по щекам, а в глазах — пустота.",
         "Ты смеёшься так громко, как смеются, когда больно,",
         "Я читаю тебя, как открытку, — невольно."]
L4_CH = ["Почему молчишь? Я же рядом — слышишь?",
         "Между нами только дождь и мокрые крыши.",
         "Скажи хоть слово — я пойму и без слов:",
         "Мы с тобой одни среди чужих дворов."]
L4_V2 = ["Солнце бьёт в окно, а нам с тобой темно,",
         "Мы как старое кино, где звук убрали давно.",
         "Твой кулон в моём кармане — тёплый, как ладонь,",
         "Я бы всё вернул назад, но ты сказала: «Не тронь»."]

L5_V1 = ["Здесь не бывает лета — только серый март,",
         "Дым из труб ТЭЦ и следы от петард.",
         "Я знаю здесь любую трещину в асфальте,",
         "Любое «навсегда», что нацарапано на парте.",
         "Пацаны разъехались — кто в Питер, кто в Москву,",
         "А я остался с этим небом, с этим серым — и живу.",
         "Мама говорит: «Сынок, тебе бы уезжать»,",
         "Но кто тогда здесь будет фонари считать?"]
L5_CH = ["Мой город — туман, мой город — бетон,",
         "Я сто раз уезжал, но я снова в нём.",
         "Пусть он холодный — он всё равно родной,",
         "Я здесь останусь, город, я останусь с тобой."]
L5_V2 = ["Ночью остановки светятся, как маяки,",
         "Я иду по лужам, а внутри — гудки.",
         "На балконе у соседки сохнет чьё-то лето,",
         "Я бы всё отдал, чтоб снова верить в это.",
         "Пусть здесь сыро и серо, пусть здесь мало солнца —",
         "Здесь мой первый поцелуй и первые бессонницы.",
         "Пусть меня запомнят стены и подъезд:",
         "Я не просто здесь живу — я этот город весь."]

FULL = dict(drums='full', bass=True, pad=True)

SONGS = [
    dict(file='01_devyatyj_etazh', title='Девятый этаж', bpm=105, chords=['Am', 'D', 'F', 'E'],
         scale=(9, 'dorian'), center=57, style='postpunk', voice='dmitri',
         sections=[
             dict(name='chorus', bars=8, **FULL, keys=True, crash=True, lyrics=L1_CH, line_bars=2, part='chorus'),
             dict(name='verse', bars=16, **FULL, lyrics=L1_V, line_bars=2, part='verse'),
             dict(name='stop', bars=1, lyrics=['Заживёшь ли ты?'], line_bars=1, mode='spoken'),
             dict(name='chorus', bars=8, **FULL, keys=True, crash=True, lyrics=L1_CH, line_bars=2, part='chorus'),
             dict(name='outro', bars=2, pad=True, keys=True, lyrics=['На девятом этаже… не гаснет свет…'], line_bars=2, part='verse', fade=True),
         ]),
    dict(file='02_chuzhaya_ten', title='Чужая тень', bpm=120, chords=['Am', 'G', 'Dm', 'Am'],
         scale=(9, 'minor'), center=57, style='house', voice='dmitri',
         sections=[
             dict(name='intro', bars=4, **FULL, filter_in=(300, 4)),
             dict(name='verse', bars=16, **FULL, lyrics=L2_V1, line_bars=2, part='verse'),
             dict(name='chorus', bars=8, **FULL, bells=True, crash=True, lyrics=L2_CH, line_bars=2, part='chorus'),
             dict(name='break', bars=4, pad=True, bells=True, lowpass=1800, lyrics=L2_BR, line_bars=2, mode='whisper'),
             dict(name='verse', bars=8, **FULL, crash=True, lyrics=L2_V2, line_bars=2, part='verse'),
             dict(name='chorus', bars=8, **FULL, bells=True, crash=True, lyrics=L2_CH, line_bars=2, part='chorus'),
             dict(name='chorus', bars=8, **FULL, bells=True, filter_in=(700, 2), lyrics=L2_CH, line_bars=2, part='chorus'),
             dict(name='outro', bars=4, pad=True, bells=True, lyrics=['Моя тень сегодня вышла без меня…'], at=[0], line_bars=2, part='verse', fade=True),
         ]),
    dict(file='03_zamerzayu', title='Замерзаю', bpm=142, chords=['C#m', 'F#m', 'A', 'G#'],
         scale=(1, 'minor'), center=56, style='trap', voice='dmitri',
         sections=[
             dict(name='intro', bars=4, pad=True, bells=True, lowpass=2500, lyrics=['Слышишь? Слышишь меня?'], at=[2], line_bars=2, mode='whisper'),
             dict(name='verse', bars=8, **FULL, crash=True, lyrics=L3_V1, line_bars=1, part='verse'),
             dict(name='chorus', bars=8, **FULL, bells=True, lyrics=L3_CH, line_bars=2, part='chorus'),
             dict(name='break', bars=7, pad=True, bells=True, lowpass=1500, lyrics=['Тише… я ещё здесь…', 'Тише… я ещё здесь…'], at=[1, 4], line_bars=2, mode='whisper'),
             dict(name='verse', bars=8, **FULL, crash=True, lyrics=L3_V2, line_bars=1, part='verse'),
             dict(name='chorus', bars=8, **FULL, bells=True, lyrics=L3_CH, line_bars=2, part='chorus'),
             dict(name='outro', bars=8, pad=True, bells=True, lyrics=['Я не вижу вас…', 'Я не вижу вас…'], at=[1, 5], line_bars=2, part='chorus', fade=True),
         ]),
    dict(file='04_pochemu_molchish', title='Почему молчишь', bpm=120, chords=['F', 'C', 'G', 'Am'],
         scale=(9, 'minor'), center=57, style='dancepop', voice='dmitri',
         sections=[
             dict(name='intro', bars=4, drums='light', keys=True, filter_in=(400, 4)),
             dict(name='verse', bars=8, drums='full', bass=True, keys=True, lyrics=L4_V1, line_bars=2, part='verse'),
             dict(name='chorus', bars=8, **FULL, keys=True, crash=True, lyrics=L4_CH, line_bars=2, part='chorus'),
             dict(name='verse', bars=8, drums='full', bass=True, keys=True, lyrics=L4_V2, line_bars=2, part='verse'),
             dict(name='break', bars=4, bass=True, lyrics=['Скажи хоть слово…', 'Хоть одно…'], at=[0, 2], line_bars=2, part='verse'),
             dict(name='chorus', bars=8, **FULL, keys=True, crash=True, lyrics=L4_CH, line_bars=2, part='chorus'),
             dict(name='chorus', bars=8, **FULL, keys=True, bells=True, lyrics=L4_CH, line_bars=2, part='chorus'),
             dict(name='outro', bars=4, pad=True, keys=True, lyrics=['Почему молчишь?'], at=[1], line_bars=2, part='chorus', fade=True),
         ]),
    dict(file='05_moj_gorod', title='Мой город', bpm=105, chords=['Em', 'C', 'G', 'D'],
         scale=(4, 'minor'), center=55, style='postpunk', voice='dmitri',
         sections=[
             dict(name='intro', bars=2, pad=True, keys=True),
             dict(name='verse', bars=16, **FULL, keys=True, crash=True, lyrics=L5_V1, line_bars=2, part='verse'),
             dict(name='chorus', bars=8, **FULL, keys=True, crash=True, lyrics=L5_CH, line_bars=2, part='chorus'),
             dict(name='stop', bars=2, pad=True, lyrics=['Я останусь…'], at=[0], line_bars=2, mode='spoken'),
             dict(name='verse', bars=16, **FULL, keys=True, crash=True, lyrics=L5_V2, line_bars=2, part='verse'),
             dict(name='chorus', bars=8, **FULL, keys=True, crash=True, lyrics=L5_CH, line_bars=2, part='chorus'),
             dict(name='outro', bars=2, pad=True, keys=True, lyrics=['Я останусь с тобой…'], at=[0], line_bars=2, part='chorus', fade=True),
         ]),
]

# relative stem levels (dB vs drums bus) inside the sections where each stem plays
LEVELS = {
    'postpunk': dict(bass=-4, pad=-11, keys=-9, bells=-12),
    'house': dict(bass=-5, pad=-10, keys=-10, bells=-10),
    'trap': dict(bass=-1, pad=-12, keys=-10, bells=-9),
    'dancepop': dict(bass=-5, pad=-13, keys=-8, bells=-12),
}
PAD_CUTOFF = dict(postpunk=3500, house=2600, trap=1600, dancepop=2400)


def voicing(ch, center=60):
    r, q = parse_chord(ch)
    pcs = sorted(((r + i) % 12) for i in q)
    return sorted(center - 6 + ((p - (center - 6)) % 12) for p in pcs)


def in_range(pc, lo, hi):
    return lo + ((pc - lo) % 12)


def render(song, voices, outdir):
    bpm = song['bpm']
    beat = 60.0 / bpm
    bar = 4 * beat
    step = beat / 4
    style = song['style']
    secs = song['sections']
    total_bars = sum(s['bars'] for s in secs)
    tail = 4.0
    n = int((total_bars * bar + tail) * SR)

    # per-bar info
    bars = []
    for si, s in enumerate(secs):
        for i in range(s['bars']):
            bars.append(dict(sec=s, si=si, i=i, chord=song['chords'][i % len(song['chords'])]))
    pos = lambda b, st=0.0: int(round((b * bar + st * step) * SR))

    stems = {k: np.zeros((2, n)) for k in ('drums', 'bass', 'pad', 'keys', 'bells')}
    active = {k: np.zeros(n, bool) for k in stems}
    kicks = []

    tonic = song['scale'][0]
    K = kick(f_lo=tuned_hz(tonic, 52)) if style != 'trap' else kick(0.35, 200, tuned_hz(tonic, 55), 2.0)
    SN, CL, HC, HO, CR = snare(tone_hz=tuned_hz(tonic, 200)), clap(), hat(False), hat(True), crash()

    for b, info in enumerate(bars):
        s = info['sec']
        d = s.get('drums')
        nxt = bars[b + 1]['sec'] if b + 1 < len(bars) else None
        last_of_sec = info['i'] == s['bars'] - 1
        if d:
            active['drums'][pos(b):pos(b + 1)] = True
            if info['i'] == 0 and s.get('crash'):
                put(stems['drums'], CR * 0.5, pos(b))
            if style == 'trap':
                ks = (0, 8, 11, 14) if b % 2 == 0 else (0, 3, 8, 11)
                for st in ks:
                    put(stems['drums'], K, pos(b, st)); kicks.append(pos(b, st))
                for st in (4, 12):
                    put(stems['drums'], pan(CL, 0.0) * 0.9, pos(b, st))
                    put(stems['drums'], SN * 0.35, pos(b, st))
                for st in range(0, 16, 2):
                    put(stems['drums'], pan(HC, 0.25) * (0.45 if st % 4 else 0.55), pos(b, st))
                if info['i'] % 4 == 3:
                    for k in range(8):
                        put(stems['drums'], pan(HC, 0.25) * (0.25 + 0.04 * k), pos(b, 12 + k * 0.5))
                if info['i'] % 4 == 1:  # triplet hats on beat 3
                    for k in range(3):
                        put(stems['drums'], pan(HC, 0.25) * 0.35, pos(b, 8 + k * 4 / 3))
            else:
                for st in (0, 4, 8, 12):
                    put(stems['drums'], K, pos(b, st)); kicks.append(pos(b, st))
                if d == 'full':
                    for st in (4, 12):
                        put(stems['drums'], CL * 0.7, pos(b, st))
                        put(stems['drums'], SN * 0.6, pos(b, st))
                if style in ('house', 'dancepop'):
                    for st in range(0, 16):
                        if st % 4 == 2:
                            put(stems['drums'], pan(HO, -0.2) * 0.35, pos(b, st))
                        elif st % 2 == 1:
                            put(stems['drums'], pan(HC, 0.3) * 0.22, pos(b, st))
                else:
                    for st in range(0, 16, 2):
                        put(stems['drums'], pan(HC, 0.3) * (0.4 if st % 4 else 0.25), pos(b, st))
                    if info['i'] % 2 == 1:
                        put(stems['drums'], pan(HO, -0.3) * 0.3, pos(b, 14))
                # fill into a new drum section
                if d == 'full' and last_of_sec and nxt is not None and nxt.get('drums') and info['i'] >= 3:
                    for k, st in enumerate((12, 13, 14, 15)):
                        put(stems['drums'], SN * (0.3 + 0.12 * k), pos(b, st))

        root_pc, _ = parse_chord(info['chord'])
        # bass
        if s.get('bass'):
            active['bass'][pos(b):pos(b + 1)] = True
            root = in_range(root_pc, 36, 48)
            if style == 'trap':
                ks = (0, 8, 11, 14) if b % 2 == 0 else (0, 3, 8, 11)
                for j, st in enumerate(ks):
                    end = ks[j + 1] if j + 1 < len(ks) else 16
                    put(stems['bass'], b808(hz(root), (end - st) * step), pos(b, st))
            elif style == 'postpunk':
                for st in range(0, 16, 2):
                    note = root + (12 if st == 14 and info['i'] % 2 else 0)
                    put(stems['bass'], synth_bass(hz(note), 2 * step * 0.95, 1100), pos(b, st))
            else:
                for st in (2, 6, 10, 14):
                    put(stems['bass'], synth_bass(hz(root), 1.6 * step, 700, pluck=False), pos(b, st))
        # pad
        if s.get('pad'):
            active['pad'][pos(b):pos(b + 1)] = True
            notes = voicing(info['chord'], 62) + [in_range(root_pc, 48, 60)]
            for m in notes:
                put(stems['pad'], supersaw_note(hz(m), bar + 0.5, cutoff=PAD_CUTOFF[style]), pos(b))
        # keys: plucked guitar arps (postpunk) / e-piano stabs (others)
        if s.get('keys'):
            active['keys'][pos(b):pos(b + 1)] = True
            tones = voicing(info['chord'], 66)
            tones = tones + [tones[0] + 12]
            if style == 'postpunk':
                order = [0, 1, 2, 3, 2, 1, 2, 3]
                for k, st in enumerate(range(0, 16, 2)):
                    put(stems['keys'], pan(pluck(hz(tones[order[k]]), 1.0), 0.35 if k % 2 else -0.35) * 0.8, pos(b, st))
            else:
                for st, dur in ((0, 3), (6, 2), (10, 4)):
                    for m in voicing(info['chord'], 63):
                        put(stems['keys'], epiano(hz(m), dur * step + 0.25) * 0.5, pos(b, st))
        # bells motif (2-bar phrase on chord tones)
        if s.get('bells'):
            active['bells'][pos(b):pos(b + 1)] = True
            tones = voicing(info['chord'], 78)
            motif = [(0, 2, 0), (3, 1, 0), (6, 0, 0), (10, 1, 0), (12, 2, 0)] if info['i'] % 2 == 0 else \
                    [(0, 0, 1), (3, 2, 0), (6, 1, 0), (8, 0, 0), (14, 1, 0)]
            for st, deg, octv in motif:
                put(stems['bells'], pan(bell(hz(tones[deg] + 12 * octv)), 0.2 * (1 if st % 2 else -1)) * 0.6, pos(b, st))

    # effects per stem
    stems['keys'] = chorus(stems['keys'], mix=0.4) if style == 'postpunk' else stems['keys']
    if style == 'postpunk':
        stems['bass'] = chorus(stems['bass'], depth=0.002, rate=0.6, mix=0.35)
    stems['keys'] = stems['keys'] + reverb(stems['keys'], 2.2, 2.8) * 0.5
    stems['bells'] = stems['bells'] + reverb(stems['bells'], 3.0, 2.0) * 0.7 + pingpong(stems['bells'], 0.75 * beat, 0.4) * 0.35
    stems['pad'] = stems['pad'] + reverb(stems['pad'], 3.0, 2.2) * 0.4
    stems['drums'] = stems['drums'] + reverb(stems['drums'], 1.2, 5.0, lp=5000) * 0.12
    stems['bass'] = filt(stems['bass'], 'low', 5000, 2)

    if kicks:
        sc = sidechain(n, kicks, depth=0.55 if style in ('house', 'dancepop') else 0.35)
        for k in ('pad', 'keys') + (('bass',) if style != 'trap' else ()):
            stems[k] = stems[k] * sc

    # level each stem relative to the drums bus
    ref = rms_db(stems['drums'], active['drums']) if active['drums'].any() else -20.0
    for k, rel in LEVELS[style].items():
        if active[k].any():
            stems[k] *= 10 ** ((ref + rel - rms_db(stems[k], active[k])) / 20)
    if not active['drums'].any():
        stems['drums'][:] = 0

    inst = sum(stems.values())

    # section filters on the instrumental (lowpass breaks, filter-in intros)
    hop = 512
    nfr = n // hop + 2
    fc = np.full(nfr, 20000.0)
    for b, info in enumerate(bars):
        s = info['sec']
        f0, f1 = pos(b) // hop, pos(b + 1) // hop
        if s.get('lowpass'):
            fc[f0:f1] = s['lowpass']
        if s.get('filter_in'):
            start_hz, nb = s['filter_in']
            if info['i'] < nb:
                a = (info['i'] + np.linspace(0, 1, f1 - f0, endpoint=False)) / nb
                fc[f0:f1] = start_hz * (16000 / start_hz) ** (a ** 1.6)
    if (fc < 19999).any():
        inst = lowpass_curve(inst, fc, hop=hop)

    # ---------------------------------------------------------------- vocals
    sc_lo, sc_mode = song['scale']
    scale_pcs = [(sc_lo + d) % 12 for d in SCALES[sc_mode]]

    def allowed_fn(bar0):
        def f(t):
            b = min(len(bars) - 1, int(bar0 + t // bar))
            cp = chord_pcs(bars[b]['chord'])
            pcs = set(cp) | {p for p in scale_pcs if min((p - c) % 12 for c in cp) >= 2 and min((c - p) % 12 for c in cp) >= 2}
            return np.array([m for m in range(36, 84) if m % 12 in pcs], float)
        return f

    vox = np.zeros((2, n))
    vox_fx_src = np.zeros(n)
    vox_active = np.zeros(n, bool)
    voice = voices[song['voice']]
    b0 = 0
    for s in secs:
        lyr = s.get('lyrics') or []
        lb = s.get('line_bars', 2)
        at = s.get('at') or [i * lb for i in range(len(lyr))]
        mode = s.get('mode', 'sing')
        part = s.get('part', 'verse')
        for line, off in zip(lyr, at):
            start_bar = b0 + off
            slot = lb * bar
            y = render_line(voice, line, slot * (0.92 if mode == 'sing' else 0.85), mode, allowed_fn(start_bar),
                            center=song['center'] + (2 if part == 'chorus' else 0),
                            spread=1.7 if part == 'chorus' else 1.3)
            st = pos(start_bar) + int(0.02 * SR)
            if mode == 'whisper':
                y = y * 0.9
            put(vox, y, st)
            vox_active[st:st + len(y)] = True
            if part == 'chorus' and mode == 'sing':
                dbl = librosa.resample(y, orig_sr=SR, target_sr=int(SR * 2 ** (-9 / 1200)))
                put(vox, pan(dbl, -0.7) * 0.32, st + int(0.017 * SR))
                put(vox, pan(dbl, 0.7) * 0.32, st + int(0.029 * SR))
                fx = np.zeros(n); fx[st:st + len(y)] = y[:max(0, min(len(y), n - st))]
                vox_fx_src += fx
        b0 += s['bars']

    # vocal chain: presence + soft saturation, reverb, delay throws on choruses
    v = vox + filt(vox, 'high', 2800, 2) * 0.45
    v = np.tanh(v * 4) / 4
    wet = reverb(v, 1.8, 3.6, lp=6500) * 0.28 + pingpong(vox_fx_src, 0.75 * beat, 0.35, lp=3500) * 0.22
    v_total = v + wet
    target = rms_db(inst, vox_active) - 1.0
    gain = 10 ** ((target - rms_db(v, vox_active)) / 20)
    v_total *= gain

    mix = inst + v_total
    # fade outro
    for s_i, s in enumerate(secs):
        if s.get('fade'):
            start = pos(sum(x['bars'] for x in secs[:s_i]) + max(0, s['bars'] - 2))
            fl = n - start
            mix[:, start:] *= np.linspace(1, 0, fl) ** 1.5
    # trim to total + tail
    out = master(mix, -10.0, -1.3)
    wav = os.path.join(outdir, song['file'] + '.wav')
    sf.write(wav, out.T, SR, subtype='PCM_24')
    sf.write(os.path.join(outdir, song['file'] + '_vox.wav'), (v_total * 0.5).T, SR)
    sf.write(os.path.join(outdir, song['file'] + '_inst.wav'), (inst * 0.5).T, SR)
    return wav


if __name__ == '__main__':
    models, outdir = sys.argv[1], sys.argv[2]
    only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
    os.makedirs(outdir, exist_ok=True)
    voices = {}
    for song in SONGS:
        if only and song['file'][:2] not in only:
            continue
        if song['voice'] not in voices:
            voices[song['voice']] = Voice(models, song['voice'])
        wav = render(song, voices, outdir)
        print('rendered', wav, flush=True)
