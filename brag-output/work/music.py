"""Synthesize the brag soundtrack: 120 BPM, A minor (Am-F-C-G), effects on the same grid.

Everything is placed on a beat grid counted from t=0 so music, SFX and cuts line up.
Writes soundtrack.wav (48 kHz, 16-bit stereo).
"""
import wave
import numpy as np

SR = 48000
BPM = 120
BEAT = 60 / BPM          # 0.5 s
BAR = 4 * BEAT           # 2.0 s
LENGTH = 22.0
N = int(SR * LENGTH)
rng = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff):
    """Brick-ish FFT low-pass with a soft roll-off."""
    X = np.fft.rfft(x, axis=-1)
    f = np.fft.rfftfreq(x.shape[-1], 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, x.shape[-1], axis=-1)


def highpass(x, cutoff):
    X = np.fft.rfft(x, axis=-1)
    f = np.fft.rfftfreq(x.shape[-1], 1 / SR)
    X *= 1 - 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, x.shape[-1], axis=-1)


def place(track, sig, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(track):
        return
    j = min(len(track), i + len(sig))
    track[i:j] += gain * sig[: j - i]


def env_exp(dur, decay, attack=0.002):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    e = np.exp(-tt / decay)
    a = int(attack * SR)
    if a > 0:
        e[:a] *= np.linspace(0, 1, a)
    return tt, e


# ---------------------------------------------------------------- instruments
def kick():
    tt, e = env_exp(0.45, 0.12)
    f = 45 + 105 * np.exp(-tt / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    click = rng.standard_normal(len(tt)) * np.exp(-tt / 0.002) * 0.15
    return (np.sin(ph) * e + click) * 0.9


def clap():
    tt, _ = env_exp(0.25, 1)
    noise = highpass(rng.standard_normal(len(tt)), 900)
    noise = lowpass(noise, 6000)
    e = np.zeros_like(tt)
    for k, off in enumerate((0.0, 0.011, 0.022)):
        e += np.where(tt >= off, np.exp(-(tt - off) / (0.006 if k < 2 else 0.07)), 0)
    return noise * e * 0.35


def hat(open_=False):
    tt, e = env_exp(0.2 if open_ else 0.06, 0.06 if open_ else 0.015)
    n = highpass(rng.standard_normal(len(tt)), 7000)
    return lowpass(n, 11000) * e * 0.18


def bass_note(midi, dur):
    tt, e = env_exp(dur, dur * 0.8, attack=0.004)
    f = hz(midi)
    sig = sum(np.sin(2 * np.pi * f * k * tt) / k ** 1.6 for k in range(1, 6))
    release = np.clip((dur - tt) / 0.03, 0, 1)
    return sig * e * release * 0.45


def pluck(midi, bright=1.0, dur=0.35):
    tt, e = env_exp(dur, 0.12)
    f = hz(midi)
    sig = np.sin(2 * np.pi * f * tt) + 0.35 * bright * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt / 0.05) \
        + 0.12 * bright * np.sin(2 * np.pi * 3 * f * tt) * np.exp(-tt / 0.03)
    return sig * e * 0.22


def pad_chord(midis, dur):
    tt = np.arange(int(dur * SR)) / SR
    a = np.clip(tt / 0.25, 0, 1)
    r = np.clip((dur - tt) / 0.3, 0, 1)
    sig = np.zeros_like(tt)
    for m in midis:
        f = hz(m)
        for det in (-0.12, 0.0, 0.12):
            ff = f * 2 ** (det / 12)
            sig += sum(np.sin(2 * np.pi * ff * k * tt + k) / k ** 1.3 for k in range(1, 5))
    sig = lowpass(sig, 2200)
    return sig * a * r * 0.035


def chime(midi):
    tt, e = env_exp(1.2, 0.35)
    f = hz(midi)
    sig = np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * 2.0 * f * tt) * np.exp(-tt / 0.2) \
        + 0.15 * np.sin(2 * np.pi * 3.01 * f * tt) * np.exp(-tt / 0.08)
    return sig * e * 0.16


def tick():
    tt, e = env_exp(0.03, 0.004, attack=0.0005)
    n = lowpass(highpass(rng.standard_normal(len(tt)), 1500), 5000)
    return n * e * 0.07


def boom(midi=33):
    tt, e = env_exp(1.4, 0.35)
    f = hz(midi) * (1 + 0.6 * np.exp(-tt / 0.04))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tail = lowpass(rng.standard_normal(len(tt)), 900) * np.exp(-tt / 0.25) * 0.25
    return (np.sin(ph) + tail) * e * 0.55


def riser(dur):
    tt = np.arange(int(dur * SR)) / SR
    p = tt / dur
    n = rng.standard_normal(len(tt))
    # Rising band of noise: crossfade through progressively brighter filtered copies.
    lo, mid, hi = lowpass(n, 800), lowpass(n, 2500), lowpass(n, 6000)
    sig = lo * (1 - p) + mid * np.sin(np.pi * p) + hi * p
    return sig * p ** 2 * 0.12


# ---------------------------------------------------------------- arrangement
chords = {  # bar -> (bass root midi, pad triad)
    "Am": (45, (57, 60, 64)), "F": (41, (57, 60, 65)), "C": (48, (55, 60, 64)), "G": (43, (55, 59, 62)),
}
prog = ["Am", "F", "C", "G", "Am", "F", "C", "G", "Am", "F", "Am"]
arp_shape = [0, 1, 2, 1, 2, 3, 2, 1]  # index into chord tones (+octave)

drums, bass, pad, arp, sfx = (np.zeros(N) for _ in range(5))
kick_env = np.zeros(N)  # for sidechain

for bar, name in enumerate(prog):
    t0 = bar * BAR
    root, triad = chords[name]
    tones = [triad[0] + 12, triad[1] + 12, triad[2] + 12, triad[0] + 24]

    # Pad from the drop onward, held chord in the outro.
    if t0 >= 6.0 and t0 < 20.0:
        place(pad, pad_chord(triad, BAR + 0.05), t0)

    for step in range(16):  # 16th grid
        t = t0 + step * BEAT / 4
        if t >= 21.0:
            break
        full = 6.0 <= t < 21.0
        # Arp on 8ths (16ths after the drop), duller in the intro.
        if step % 2 == 0 or full:
            note = tones[arp_shape[step % 8]]
            place(arp, pluck(note, bright=1.0 if full else 0.4), t, 1.0 if full else 0.8)
        # Bass: 8th pulse from 0, octave bounce after the drop.
        if step % 2 == 0 and t < 19.5:
            m = root + (12 if (full and step % 4 == 2) else 0)
            place(bass, bass_note(m, BEAT / 2 - 0.01), t, 1.0 if t >= 3.0 else 0.6)
        # Drums.
        if step % 4 == 0 and 3.0 <= t < 21.0:
            g = 1.0 if full else 0.7
            place(drums, kick(), t, g)
            place(kick_env, np.exp(-np.arange(int(0.25 * SR)) / SR / 0.08), t)
        if full and step % 8 == 4 and t < 19.5:
            place(drums, clap(), t)
        # Hats: closed 8ths after 3s; after the drop the offbeat 8th opens up.
        if 3.0 <= t < 21.0 and step % 2 == 0:
            place(drums, hat(open_=full and step % 4 == 2), t, 0.8 if full else 0.5)

# Sidechain: duck music under the kick.
duck = 1 - 0.55 * np.clip(kick_env, 0, 1)
bass *= duck
pad *= duck
arp *= 1 - 0.3 * np.clip(kick_env, 0, 1)

# ---------------------------------------------------------------- SFX (in key, on the grid)
# Typing in the hook: "winget upgrade" over 0.25-1.0s, then 16th-note table rows.
for k in range(14):
    place(sfx, tick(), 0.25 + k * (0.75 / 14), 0.8)
for i in range(7):
    place(sfx, tick(), 1.0 + i * 0.125, 0.6)
place(sfx, boom(33), 0.0, 0.7)                 # hook slam
place(sfx, pluck(69, bright=1.2, dur=0.6), 1.5, 1.3)   # "= attack surface."
place(sfx, boom(33), 3.0, 0.4)                 # cut into the gap
place(sfx, pluck(64, dur=0.5), 3.5, 1.0)       # "No Proactive Remediation."
place(sfx, riser(1.5), 4.5)                    # into the drop
place(sfx, boom(33), 6.0, 0.8)                 # drop / "Deploy once."
for i, m in enumerate((69, 72, 76, 81)):       # diagram nodes: A C E A
    place(sfx, chime(m), 9.5 + i, 0.9)
for i in range(11):                            # log lines
    place(sfx, tick(), 14.25 + i * 0.125, 0.5)
for i, m in enumerate((76, 79, 81)):           # feature cards: E G A
    place(sfx, chime(m), 17.0 + i * 0.5, 0.9)
place(sfx, boom(33), 19.5, 1.0)                # outro
place(sfx, chime(81), 19.5, 0.8)
place(pad, pad_chord((57, 60, 64, 69), 2.5), 19.5, 1.4)  # Am ring-out

# ---------------------------------------------------------------- shared space + mix
def reverb(x, seconds=1.1, mix=0.18):
    n = int(seconds * SR)
    tt = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-tt / (seconds / 5))
    ir = lowpass(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    wet = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)]
    return x + mix * wet

music_bus = reverb(arp * 0.9 + pad, mix=0.25) + bass * 0.65 + drums
sfx_bus = reverb(sfx, mix=0.3) * 0.75
mix = music_bus + sfx_bus

# Stereo: slight width on arp/pad via a short delay on the right channel.
d = int(0.012 * SR)
right = mix.copy()
right[d:] = mix[:-d] * 0.15 + mix[d:] * 0.85

stereo = np.stack([mix, right], axis=1)
stereo = lowpass(stereo.T, 14000).T  # tame harsh highs
fade = np.ones(N)
fs, fe = int(21.3 * SR), N
fade[fs:fe] = np.linspace(1, 0, fe - fs) ** 1.5
fade[: int(0.01 * SR)] = np.linspace(0, 1, int(0.01 * SR))
stereo *= fade[:, None]
stereo = np.tanh(stereo * 0.9) / np.tanh(0.9)
stereo /= np.max(np.abs(stereo)) / 0.89  # -1 dBFS

pcm = (stereo * 32767).astype(np.int16)
with wave.open("soundtrack.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote soundtrack.wav", pcm.shape[0] / SR, "s")
