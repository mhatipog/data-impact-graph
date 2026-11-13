#!/usr/bin/env python3
"""Original, procedurally composed score for the Data Impact Graph film.

No samples, third-party compositions, downloaded loops or copyrighted melodies.
A minor cinematic/electronic palette: evolving chords, glass plucks, bass pulse,
off-grid percussion, stereo echoes, and short transition risers. Seeded output.
"""
from __future__ import annotations
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 102
BEAT = 60.0 / BPM
RNG = np.random.default_rng(1206)

def midi(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))

class Score:
    def __init__(self, seconds):
        self.seconds = seconds
        n = int(math.ceil(seconds * SR))
        self.left = np.zeros(n, dtype=np.float32)
        self.right = np.zeros(n, dtype=np.float32)

    def put(self, seconds, audio, vol=1.0, pan=0.0):
        off = round(max(0, seconds) * SR)
        if off >= len(self.left): return
        sig = (np.asarray(audio, dtype=np.float32) * vol)[:len(self.left)-off]
        if len(sig) == 0: return
        # Equal-power pan, with a quiet centre leak for natural stereo.
        a = math.cos((pan + 1) * math.pi / 4) * 1.30
        b = math.sin((pan + 1) * math.pi / 4) * 1.30
        self.left[off:off+len(sig)] += sig * a
        self.right[off:off+len(sig)] += sig * b

    def note(self, at, dur, pitch, volume, voice="glass", pan=0.0):
        n = max(2, int(dur * SR))
        t = np.arange(n, dtype=np.float32) / SR
        f = midi(pitch)
        if voice == "pad":
            sig = (np.sin(2*np.pi*f*t) + 0.30*np.sin(2*np.pi*f*1.003*t)
                   + 0.17*np.sin(2*np.pi*f*2*t))
            env = np.minimum(1, t / 0.24) * np.minimum(1, (dur-t) / 0.48)
        elif voice == "glass":
            sig = (np.sin(2*np.pi*f*t) + 0.28*np.sin(2*np.pi*f*2.003*t)
                   + 0.10*np.sin(2*np.pi*f*3.008*t))
            env = np.minimum(1, t / 0.006) * np.exp(-3.5 * t / max(dur,0.1))
            env *= np.minimum(1,(dur-t)/0.05)
        elif voice == "bass":
            phi = 2*np.pi*f*t
            sig = 0.85*np.sin(phi)+0.22*np.sin(2*phi)+0.10*np.sin(3*phi)
            env = np.minimum(1,t/0.02)*np.exp(-2.1*t/max(dur,0.1))
            env *= np.minimum(1,(dur-t)/0.08)
        else: # Rhodes-like muted octave pulse
            sig = (np.sin(2*np.pi*f*t)+0.26*np.sin(2*np.pi*2*f*t))
            env = np.minimum(1,t/0.014)*np.exp(-4*t/max(dur,0.1))
        self.put(at, sig * env, volume, pan)

    def kick(self, at, amp):
        dur=.34
        t=np.arange(int(SR*dur),dtype=np.float32)/SR
        phase=2*np.pi*(48*t+65/18*(1-np.exp(-18*t)))
        sub=np.sin(phase)*np.exp(-t*17)
        click=RNG.standard_normal(len(t)).astype(np.float32)*np.exp(-t*90)*.11
        self.put(at,sub+click,amp)

    def clap(self, at, amp):
        dur=.26
        t=np.arange(int(SR*dur),dtype=np.float32)/SR
        noise=RNG.standard_normal(len(t)).astype(np.float32)
        # Layered, short noise impulses with a slight flam.
        env=(np.exp(-t*34)+.40*np.exp(-np.maximum(t-.026,0)*43)*(t>.026)
             +.25*np.exp(-np.maximum(t-.054,0)*50)*(t>.054))
        self.put(at,noise*env*.17+np.sin(2*np.pi*210*t)*np.exp(-t*28)*.16,amp,pan=.08)

    def hat(self, at, amp, pan):
        dur=.12
        t=np.arange(int(SR*dur),dtype=np.float32)/SR
        noise=RNG.standard_normal(len(t)).astype(np.float32)
        # Discrete differentiator brightens without external samples.
        bright=noise-np.roll(noise,7)
        self.put(at,bright*np.exp(-t*54)*.09,amp,pan=pan)

    def transition(self, at, amp=1.0):
        dur=.42
        t=np.arange(int(dur*SR),dtype=np.float32)/SR
        noise=RNG.standard_normal(len(t)).astype(np.float32)
        bright=noise-np.roll(noise,18)
        env=(t/dur)**2*np.maximum(0,1-t/dur)**.4
        self.put(max(0,at-dur),bright*.11*env,amp,pan=.7)
        self.note(at, .5, 81, .17*amp, "glass", pan=-.45)

    def write(self, out):
        # Small stereo echoes create depth; melody is entirely generated.
        for d,g in [(.13,.12),(.31,.075),(.48,.045)]:
            n=round(SR*d)
            left=self.left[:-n].copy()
            right=self.right[:-n].copy()
            self.left[n:] += g*right
            self.right[n:] += g*left
        # Soft limiter instead of harsh clipping.
        peak=max(float(np.max(np.abs(self.left))),float(np.max(np.abs(self.right))),1e-6)
        gain=0.82/peak
        stereo=np.stack((np.tanh(self.left*gain*1.1),
                         np.tanh(self.right*gain*1.1)),axis=-1)
        pcm=np.int16(np.clip(stereo,-1,1)*32767)
        out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
        with wave.open(str(out),"wb") as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        return {"bpm":BPM,"key":"A minor","duration_seconds":self.seconds,
                "source":"original procedural composition; no external samples",
                "bytes":out.stat().st_size}

def compose(seconds, cues, output):
    s=Score(seconds)
    prog=[
        [45,48,52,55],   # Am7
        [41,45,48,52],   # Fmaj7
        [48,52,55,59],   # Cmaj9
        [43,47,50,52],   # G6
    ]
    melody=[69,72,76,79,76,72,74,72, 69,72,77,76,72,69,67,69]
    bars=int(math.ceil(seconds / (BEAT*4)))
    for bar in range(bars):
        start=bar*BEAT*4
        chord=prog[bar%4]
        middle=min(seconds,start+BEAT*2)
        state=("opening" if start<12 else "break" if any(
            abs(start-cues.get(k,-99))<2.0 for k in ("negative","receipt"))
            else "full")
        amp=.055 if state=="opening" else (.052 if state=="break" else .075)
        for i,p in enumerate(chord):
            s.note(start, BEAT*4.5, p+12, amp*(.72 if i==3 else 1), "pad",
                   pan=(-.68+i*.42))
        if start > 9:
            for k in range(4):
                at=start+k*BEAT
                if at>=seconds: break
                s.note(at,.4, chord[0]+(-12 if k in (0,2) else 0),.13,"bass")
            if state=="full":
                for k in range(4):
                    at=start+k*BEAT
                    if at>=seconds: break
                    s.kick(at, .24 if k==0 else .16)
                    if k in (1,3): s.clap(at, .26)
                for k in range(8):
                    at=start+k*BEAT/2 +(0.03 if k%2 else 0)
                    if at>=seconds: break
                    s.hat(at,.45 if k%2 else .27, -.25 if k%2 else .25)
        # Evolving pluck line, with one unplayed beat each phrase.
        for k in range(8):
            at=start+k*BEAT/2
            if at>=seconds or (bar%2==1 and k==5):continue
            n=melody[(bar*3+k)%len(melody)]
            s.note(at,.31,n,.11 if state=="opening" else .085,"glass",
                   pan=(-.55 if k%2 else .5))
        # A restrained bell counterline on alternate bars.
        if bar%2==1 and state=="full":
            s.note(middle,.7,chord[-1]+24,.06,"glass",pan=.66)
    for name,at in cues.items():
        if name not in ("intro","outro") and at>1 and at<seconds-1:
            s.transition(at, .75 if name=="negative" else 1.1)
    outro=cues.get("outro",seconds-6)
    for j, pitch in enumerate([69,72,76,81]):
        when=outro+.28+j*.24
        if when<seconds: s.note(when,1.5,pitch,.19,"glass",pan=(-.45+j*.3))
    return s.write(output)

if __name__ == "__main__":
    target=float(sys.argv[1])
    timestamps=json.loads(Path(sys.argv[2]).read_text())
    print(json.dumps(compose(target,timestamps,sys.argv[3])),flush=True)
