#!/usr/bin/env python3
"""Render a narrated, story-led cut of the real Relate-backed Playwright recording.

Inputs: committed demo/data-impact-graph-demo.mp4, no synthetic UI recording.
Voice: Microsoft Edge Neural TTS (fails rather than silently substituting a bad voice).
Output: demo/data-impact-graph-narrated.mp4 + JSON manifest.
"""
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "demo" / "data-impact-graph-demo.mp4"
OUTPUT = ROOT / "demo" / "data-impact-graph-narrated.mp4"
MANIFEST = ROOT / "demo" / "narrated-manifest.json"
VOICE = os.getenv("DEMO_VOICE", "en-US-AndrewNeural")
FPS = 30
W, H = 1920, 1080
VIDEO_X, VIDEO_Y, VIDEO_W, VIDEO_H = 38, 144, 1314, 739
INK = (242, 247, 255)
PALE = (176, 193, 215)
ACCENT = (246, 166, 93)
AQUA = (96, 220, 205)
CARD = (15, 28, 45)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# The source recording's original chapter boundaries; nothing in the UI is simulated.
# Different crops deliberately reveal only one area at a time, at a readable scale.
SCENES = [
    dict(key="hook", src=(0.0, 10.1), crop=(0, 0),
         label="01 / THE QUESTION", title="One small\nfield change.",
         body="What business decisions depend on this lab measurement?",
         voice="A lab changes moisture percent from a percentage to a fraction. Sounds routine. But what actually breaks downstream?",
         steps=[("SOURCE", "LabTrack / moisture_pct"), ("CHANGE", "0 to 100  becomes  0 to 1")],
         caption="A routine lab change can have unexpected consequences."),
    dict(key="paths", src=(10.1, 24.1), crop=(330, 40),
         label="02 / FOLLOW THE DATA", title="Trace the\nreal path.",
         body="Dependencies are traversed inside Relate, not guessed by an AI.",
         voice="Data Impact Graph queries Relate, the embedded graph database, for real dependency paths. Follow the moisture measurement into assay normalization and dry mass.",
         steps=[("1", "moisture_pct"), ("2", "Normalize assay"), ("3", "Calculate dry mass")],
         caption="The graph explains each hop with a recorded dependency."),
    dict(key="esg", src=(36.0, 46.1), crop=(370, 28),
         label="03 / THE REVEAL", title="It reaches\ncarbon reports.",
         body="An upstream field crosses systems and influences a board-level output.",
         voice="Keep following the graph. Dry mass becomes the denominator for carbon intensity, which flows into Scope Three assurance. That's the first surprise.",
         steps=[("INPUT", "Dry tonnes"), ("METRIC", "CO2e per dry tonne"), ("OUTPUT", "Scope 3 assurance")],
         caption="A moisture conversion reaches a sustainability dashboard."),
    dict(key="payout", src=(24.1, 36.0), crop=(330, 38),
         label="04 / THE SECOND REVEAL", title="And supplier\npayments.",
         body="A change in the lab also crosses into FinanceMart.",
         voice="But the same dry mass also influences supplier payouts. One source column, two very different business teams, and a hidden shared dependency.",
         steps=[("LAB", "Moisture percentage"), ("FINANCE", "Supplier payout"), ("CLIMATE", "Carbon intensity")],
         caption="One changed field, multiple affected business outcomes."),
    dict(key="precision", src=(58.0, 70.2), crop=(320, 24),
         label="05 / LESS NOISE", title="Avoid false\nalarms.",
         body="Column-level edges distinguish genuine downstream paths.",
         voice="Precision matters. Change an unrelated field identifier instead, and the payout and carbon outputs disappear from the results. No noisy sibling-column assumptions.",
         steps=[("CHANGE", "field_id"), ("REACHES", "Yield reporting"), ("DOES NOT REACH", "Payouts or Scope 3")],
         caption="The narrower change does not falsely implicate finance or ESG."),
    dict(key="receipt", src=(70.2, 84.4), crop=(320, 25),
         label="06 / SHARE THE EVIDENCE", title="Make impact\nreviewable.",
         body="Export a Markdown impact receipt for the change request.",
         voice="Before merging, export a change impact receipt. It lists each affected output, the exact graph route, and the reason behind every dependency.",
         steps=[("EVIDENCE", "Traversed source-to-output paths"), ("REVIEW", "Why each edge matters"), ("EXPORT", "Markdown change receipt")],
         caption="Attach reproducible graph evidence to your pull request."),
    dict(key="close", src=(84.4, 99.0), crop=(320, 15),
         label="07 / BUILT ON RELATE", title="Know what\nbreaks first.",
         body="A local graph you can reopen, query, and inspect.",
         voice="Forty-nine assets. Sixty dependencies. One persistent local Relate graph, with real Cypher traversals. Data Impact Graph. Know what breaks before you change it.",
         steps=[("49", "Assets"), ("60", "Relationships"), ("1", "Embedded Relate graph")],
         caption="Open source. Real Relate. No hosted graph server."),
]

def cmd(*args):
    p = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f"Command failed: {' '.join(map(str,args))}\n{p.stderr[-4000:]}")
    return p.stdout

def duration(p):
    return float(cmd("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                     "default=noprint_wrappers=1:nokey=1", str(p)).strip())

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def wrapped(draw, text, face, width):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            next_line = (line + " " + word).strip()
            if draw.textbbox((0, 0), next_line, font=face)[2] > width and line:
                lines.append(line); line = word
            else:
                line = next_line
        lines.append(line)
    return lines

def textlines(draw, xy, text, face, fill, maxwidth, spacing=10):
    x,y=xy
    for line in wrapped(draw, text, face, maxwidth):
        draw.text((x,y), line, font=face, fill=fill, stroke_width=0)
        y += face.size + spacing
    return y

def bg_for_scene(s, idx, out):
    im=Image.new("RGB",(W,H),(5,12,22))
    d=ImageDraw.Draw(im)
    for y in range(0,H,4):
        color=(5+int(y/H*5),12+int(y/H*5),22+int(y/H*6))
        d.rectangle((0,y,W,y+4),fill=color)
    d.text((43,35),"DATA IMPACT",font=font(28,True),fill=INK)
    d.text((258,35),"GRAPH",font=font(28,True),fill=ACCENT)
    d.text((1455,42),"REAL RELATE  /  LIVE CYPHER",font=font(20,True),fill=AQUA)
    d.rounded_rectangle((VIDEO_X-2, VIDEO_Y-2, VIDEO_X+VIDEO_W+2, VIDEO_Y+VIDEO_H+2),
                        radius=18,fill=(26,47,65),outline=(61,89,111),width=3)
    d.rounded_rectangle((1390,144,1882,883),radius=23,fill=CARD,
                        outline=(51,77,99),width=2)
    d.rectangle((1418,188,1476,193),fill=ACCENT)
    d.text((1417,209),s["label"],font=font(19,True),fill=ACCENT)
    yy=textlines(d,(1417,255),s["title"],font(56,True),INK,418,spacing=1)
    yy=textlines(d,(1417,yy+25),s["body"],font(24),PALE,416,spacing=9)+36
    for n,(tag,value) in enumerate(s["steps"]):
        if yy>809: break
        d.rounded_rectangle((1417,yy,1850,yy+76),radius=13,fill=(24,43,63),
                            outline=(62,86,106),width=2)
        d.text((1432,yy+10),tag,font=font(16,True),fill=AQUA)
        textlines(d,(1432,yy+33),value,font(23,True),INK,405,spacing=3)
        yy+=91
    d.text((45,907),"WHAT TO NOTICE",font=font(18,True),fill=ACCENT)
    textlines(d,(45,945),s["caption"],font(34,True),INK,1815,spacing=3)
    d.rounded_rectangle((42,1041,1879,1050),radius=4,fill=(39,59,77))
    d.rounded_rectangle((42,1041,42+round((idx+1)/len(SCENES)*1837),1050),
                        radius=4,fill=ACCENT)
    im.save(out,quality=95)

async def narration(s, dest):
    # Neural TTS: require actual voice media rather than replacing with silence/espeak.
    for attempt in range(3):
        try:
            speaker=edge_tts.Communicate(text=s["voice"],voice=VOICE,rate="+2%")
            await speaker.save(str(dest))
            if dest.stat().st_size < 2000: raise RuntimeError("Voice too small")
            return
        except Exception:
            if attempt==2: raise
            await asyncio.sleep(2+attempt*3)

def render_scene(s, still, audio, target):
    audio_length=duration(audio)
    target_length=round(audio_length+1.0,3)
    st,en=s["src"]; source_length=en-st
    x,y=s["crop"]
    x=min(x,1600-1120); y=min(y,900-630)
    # A slight camera push combines with cuts between areas. Old large recording
    # captions sit at the bottom of the source: the crop favors the app above them.
    lens=f"crop=1120:630:{x}:{y},zoompan=z='min(zoom+0.0004,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={VIDEO_W}x{VIDEO_H}:fps={FPS}"
    graph=(f"[0:v]setpts={target_length/source_length:.7f}*(PTS-STARTPTS),fps={FPS},"
           f"{lens},setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=1[v];"
           f"[1:v][v]overlay={VIDEO_X}:{VIDEO_Y}:shortest=0:format=auto,"
           f"format=yuv420p[out]")
    cmd("ffmpeg","-hide_banner","-loglevel","error","-y",
        "-ss",str(st),"-t",str(source_length),"-i",str(SOURCE),
        "-loop","1","-framerate",str(FPS),"-i",str(still),
        "-i",str(audio),
        "-filter_complex",graph,
        "-map","[out]","-map","2:a:0",
        "-t",str(target_length),"-r",str(FPS),
        "-c:v","libx264","-preset","veryfast","-crf","20",
        "-pix_fmt","yuv420p",
        "-c:a","aac","-ar","48000","-ac","2","-b:a","160k",
        "-af","loudnorm=I=-16:TP=-1.5:LRA=9,apad",
        "-movflags","+faststart",str(target))
    return target_length

async def main():
    if not SOURCE.is_file(): raise RuntimeError(f"Missing source: {SOURCE}")
    if duration(SOURCE)<98: raise RuntimeError("Source video is truncated")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="impact-editorial-") as tmp:
        work=Path(tmp); segments=[]; scenes=[]
        for idx,s in enumerate(SCENES):
            audio=work/f"{idx:02d}.mp3"
            still=work/f"{idx:02d}.png"
            clip=work/f"{idx:02d}.mp4"
            print(f"[{idx+1}/{len(SCENES)}] neural narration: {s['key']}",flush=True)
            await narration(s,audio)
            bg_for_scene(s,idx,still)
            length=render_scene(s,still,audio,clip)
            print(f"[{idx+1}/{len(SCENES)}] clip {length:.1f}s",flush=True)
            scenes.append({"key":s["key"],"duration":length,"narration":s["voice"]})
            segments.append(clip)
        manifest=work/"concat.txt"
        manifest.write_text("".join(f"file '{p}'\n" for p in segments))
        cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
            "-i",str(manifest),"-c","copy","-movflags","+faststart",str(OUTPUT))
        real_length=duration(OUTPUT)
        if not (55<=real_length<=105): raise RuntimeError(f"Unexpected duration: {real_length}")
        if OUTPUT.stat().st_size < 500_000: raise RuntimeError("Render is unreasonably small")
        # Decode first, middle and last frames to guard against container-only success.
        for time in [1,real_length/2,real_length-2]:
            cmd("ffmpeg","-hide_banner","-loglevel","error","-ss",str(time),"-i",str(OUTPUT),
                "-frames:v","1","-f","null","-")
        # A contact sheet lets reviewers assess text size and focal points at a glance.
        contact=Image.new("RGB",(1200,1352),(8,16,28))
        cursor=0.0
        for i,chapter in enumerate(scenes):
            stamp=work/f"review-{i:02d}.png"
            midpoint=cursor+chapter["duration"]/2
            cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(midpoint),
                "-i",str(OUTPUT),"-frames:v","1",str(stamp))
            pic=Image.open(stamp).convert("RGB").resize((600,338),Image.Resampling.LANCZOS)
            contact.paste(pic,((i%2)*600,(i//2)*338))
            cursor+=chapter["duration"]
        contact.save(ROOT/"demo"/"narrated-contact-sheet.png",optimize=True)
        sha=hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
        out={"source":"committed Playwright capture of real Relate application",
             "video_seconds":real_length,"resolution":"1920x1080","framerate":FPS,
             "voice":VOICE,"voice_engine":"Microsoft Edge Neural TTS",
             "video_bytes":OUTPUT.stat().st_size,"sha256":sha,"chapters":scenes}
        MANIFEST.write_text(json.dumps(out,indent=2)+"\n")
        print("NARRATED_DEMO_VERIFIED",json.dumps(out),flush=True)

if __name__=="__main__":
    asyncio.run(main())
