#!/usr/bin/env python3
"""Story-first film about the *real* Data Impact Graph / Relate application.

Source imagery is extracted from the original verified Playwright MP4; traced
facts come from the committed impact-review.md. Editorial graphics are
distinguished from captured application UI. No mock APIs, no copyrighted music.
"""
from __future__ import annotations
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

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"demo/data-impact-graph-demo.mp4"
RECEIPT=ROOT/"demo/impact-review.md"
OUT=ROOT/"demo/data-impact-graph-story.mp4"
MANIFEST=ROOT/"demo/story-manifest.json"
SHEET=ROOT/"demo/story-contact-sheet.png"
VOICE=os.getenv("DEMO_VOICE","en-US-AndrewNeural")
FPS=24
W,H=1600,900
BG=(10,18,30)
PAPER=(245,240,229)
INK=(16,28,40)
WHITE=(244,247,252)
SOFT=(170,190,204)
MUTED=(103,117,123)
ORANGE=(245,158,92)
TEAL=(102,214,194)
YELLOW=(252,211,102)
RED=(236,108,95)
FONT_PATHS={
    "serif":"/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
    "serifbold":"/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
    "italic":"/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
    "sans":"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "bold":"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "mono":"/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
}
FONTS={}
def font(kind,size):
    key=(kind,size)
    if key not in FONTS:
        FONTS[key]=ImageFont.truetype(FONT_PATHS[kind],size)
    return FONTS[key]
def cmd(*args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode:
        raise RuntimeError("Command failed: "+" ".join(map(str,args))+"\n"+p.stderr[-2500:])
    return p.stdout
def duration(path):
    return float(cmd("ffprobe","-v","error","-show_entries","format=duration",
                     "-of","default=noprint_wrappers=1:nokey=1",str(path)).strip())
def ease(x):
    x=max(0,min(1,x))
    return x*x*(3-2*x)
def paint(d,xy,msg,face,col,anchor=None,stroke=0):
    d.text(xy,msg,font=face,fill=col,anchor=anchor,stroke_width=stroke)
def line_progress(d,points,col,width,amount):
    n=max(0,min(len(points)-1,int((len(points)-1)*ease(amount))))
    if n>=1: d.line(points[:n+1],fill=col,width=width,joint="curve")
def squiggle(d,x,y,w,color,progress=1,width=5):
    p=[]
    for i in range(48):
        t=i/47
        p.append((int(x+w*t),int(y+3*math.sin(t*math.pi*4.4)+2*math.sin(t*math.pi*12.3))))
    line_progress(d,p,color,width,progress)
def polygon_arrow(d,start,end,color,width=7):
    d.line((start,end),fill=color,width=width)
    dx=end[0]-start[0];dy=end[1]-start[1]
    angle=math.atan2(dy,dx)
    for diff in (-.65,.65):
        point=(int(end[0]-22*math.cos(angle+diff)),int(end[1]-22*math.sin(angle+diff)))
        d.line((point,end),fill=color,width=width)
def frame_base(paper=False):
    im=Image.new("RGB",(W,H),PAPER if paper else BG)
    d=ImageDraw.Draw(im)
    if paper:
        for i in range(18):
            yy=65+i*48
            d.line((35,yy,1570,yy),fill=(239,232,219),width=1)
    else:
        for i in range(0,W,120):
            d.line((i,0,i,H),fill=(15,27,40),width=1)
    return im
def paper_stamp(im,msg,x,y,angle=-7,fill=ORANGE):
    w,h=420,102
    top=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(top)
    d.rounded_rectangle((6,8,w-8,h-8),radius=9,fill=(*fill,236))
    paint(d,(22,26),msg,font("mono",37),(18,27,37))
    top=top.rotate(angle,expand=True,resample=Image.Resampling.BICUBIC)
    im.paste(top,(x,y),top)
def paste_screen(frame,snap,crop,rect,t=0,zoom=.03):
    # Every displayed pixel is from the genuine verified recorded app.
    original=snap
    x1,y1,x2,y2=crop
    cx=(x1+x2)/2;cy=(y1+y2)/2
    scale=1+zoom*ease(t)
    cw=(x2-x1)/scale; ch=(y2-y1)/scale
    src=(int(cx-cw/2),int(cy-ch/2),int(cx+cw/2),int(cy+ch/2))
    panel=original.crop(src).resize((rect[2],rect[3]),Image.Resampling.BICUBIC)
    d=ImageDraw.Draw(frame)
    x,y,w,h=rect
    d.rounded_rectangle((x+9,y+11,x+w+11,y+h+13),radius=13,fill=(49,59,64))
    frame.paste(panel,(x,y))
    d.rectangle((x,y,x+w,y+h),outline=TEAL,width=3)
    return (x,y,w,h)
def note(d,msg,x,y,ink=ORANGE,size=31):
    paint(d,(x,y),msg,font("italic",size),ink)
def graph_box(d,rect,label,caption,fill,kind="sans"):
    x,y,w,h=rect
    d.rounded_rectangle((x,y,x+w,y+h),radius=12,fill=fill)
    paint(d,(x+18,y+13),label,font(kind,30),INK if fill in (ORANGE,TEAL,YELLOW) else WHITE)
    if caption: paint(d,(x+18,y+h-31),caption,font("mono",17),INK if fill in (ORANGE,TEAL,YELLOW) else SOFT)
def show_intro(im,t):
    d=ImageDraw.Draw(im)
    paint(d,(78,63),"A short story about a dependency nobody saw",font("mono",22),TEAL)
    lift=int(28*(1-ease(t/.9)))
    paint(d,(78,170+lift),"One column.",font("serifbold",133),WHITE)
    paint(d,(172,325+int(28*(1-ease((t-.5)/.9)))),"Two consequences.",font("serifbold",124),ORANGE)
    squiggle(d,181,481,1010,YELLOW,(t-.8)/.65,8)
    paint(d,(82,572),"moisture_pct",font("mono",40),WHITE)
    line_progress(d,[(415,594),(660,594),(726,535)],TEAL,6,(t-1.6)/.6)
    line_progress(d,[(660,594),(726,679)],ORANGE,6,(t-1.8)/.65)
    if t>2.2:
        paint(d,(755,509),"Finance?",font("italic",43),ORANGE)
        paint(d,(756,650),"Climate?",font("italic",43),TEAL)
    paint(d,(82,829),"DATA IMPACT GRAPH  /  FICTIONAL DATA  /  REAL RELATE",font("mono",20),SOFT)
def show_change(im,t,snaps):
    d=ImageDraw.Draw(im)
    paint(d,(74,64),"In LabTrack / lot_assays",font("mono",23),MUTED)
    paint(d,(72,151),"moisture_pct",font("mono",78),INK)
    squiggle(d,78,253,619,ORANGE,(t-.35)/.7,7)
    paint(d,(76,303),"The name stays.",font("serif",54),INK)
    note(d,"The meaning doesn't.",82,376,(158,75,58),39)
    d.rounded_rectangle((77,506,344,668),radius=12,fill=INK)
    d.rounded_rectangle((455,506,723,668),radius=12,fill=ORANGE)
    paint(d,(108,543),"0–100",font("bold",63),WHITE)
    paint(d,(495,543),"0–1",font("bold",63),INK)
    polygon_arrow(d,(361,591),(437,591),INK,7)
    paint(d,(86,711),"percent  ->  fraction",font("mono",27),MUTED)
    paste_screen(im,snaps["change"],(0,130,315,795),(894,137,588,660),t,zoom=.06)
    d=ImageDraw.Draw(im)
    paint(d,(901,821),"REAL APP / SOURCE ASSET SELECTED",font("mono",20),MUTED)
def show_path(im,t,snaps):
    d=ImageDraw.Draw(im)
    paint(d,(70,53),"Not a guess. A Cypher traversal.",font("serifbold",66),WHITE)
    note(d,"Look closely...",1103,92,ORANGE,39)
    paste_screen(im,snaps["path"],(340,320,1568,817),(85,183,1434,588),t,zoom=.075)
    d=ImageDraw.Draw(im)
    x=int(145+round(1120*ease((t-.4)/2.2)))
    squiggle(d,144,786,min(1250,x-144),ORANGE,1,7)
    paint(d,(92,815),"moisture_pct  /  normalize assay  /  calculate dry mass",font("mono",26),WHITE)
    paint(d,(1170,850),"REAL RELATE STORE  •  .rl",font("mono",18),TEAL)
def show_fork(im,t):
    d=ImageDraw.Draw(im)
    paint(d,(82,64),"And then the path splits.",font("serifbold",90),INK)
    note(d,"This is the twist.",1177,148,(172,91,51),37)
    graph_box(d,(552,251,493,111),"Calculate dry mass","shared upstream transformation",INK)
    line_progress(d,[(800,362),(800,427),(478,427),(478,506)],ORANGE,8,(t-.3)/1.8)
    line_progress(d,[(800,362),(800,427),(1118,427),(1118,506)],TEAL,8,(t-.7)/2.0)
    if t>1.6:
        graph_box(d,(119,508,677,181),"FinanceMart","payable dry kg  ->  payout forecast",ORANGE,"serif")
        paint(d,(157,595),"Money",font("serifbold",75),INK)
    if t>2.2:
        graph_box(d,(850,508,629,181),"ClimateMart","dry tonnes  ->  carbon intensity",TEAL,"serif")
        paint(d,(910,595),"Carbon",font("serifbold",75),INK)
    paint(d,(88,780),"One intermediate. Two departments that rarely share a dashboard.",font("sans",31),INK)
    squiggle(d,992,824,381,ORANGE,(t-2.2)/1.4,5)
def show_finance(im,t,snaps):
    d=ImageDraw.Draw(im)
    paint(d,(83,52),"FIRST  /  the money",font("mono",23),ORANGE)
    paint(d,(78,135),"€",font("serifbold",192),ORANGE)
    paint(d,(80,351),"Supplier",font("serifbold",82),WHITE)
    paint(d,(80,453),"payouts.",font("serifbold",85),WHITE)
    squiggle(d,84,560,468,ORANGE,(t-.4)/1.4,7)
    paint(d,(86,620),"Dry kilograms set the",font("sans",32),SOFT)
    paint(d,(86,671),"settlement volume.",font("sans",32),SOFT)
    paste_screen(im,snaps["finance"],(325,205,1555,805),(675,169,848,615),t,.05)
    d=ImageDraw.Draw(im)
    note(d,"Not just a quality metric.",875,805,ORANGE,37)
def show_climate(im,t,snaps):
    d=ImageDraw.Draw(im)
    paint(d,(84,67),"SECOND  /  the carbon report",font("mono",23),(51,124,117))
    paste_screen(im,snaps["climate"],(340,295,1568,810),(69,171,988,589),t,.055)
    d=ImageDraw.Draw(im)
    paint(d,(1100,210),"Scope 3",font("serifbold",71),INK)
    squiggle(d,1102,307,382,ORANGE,(t-.3)/1.3,7)
    paint(d,(1104,354),"CO2e per",font("sans",39),INK)
    paint(d,(1104,414),"dry tonne.",font("sans",39),INK)
    note(d,"Watch the",1100,533,(161,82,51),42)
    note(d,"denominator.",1089,589,(161,82,51),42)
    polygon_arrow(d,(1171,664),(1054,688),ORANGE,7)
    paint(d,(86,810),"One lab value can reach an ESG assurance dashboard.",font("serif",46),INK)
def show_negative(im,t,snaps):
    d=ImageDraw.Draw(im)
    paint(d,(79,61),"And here's the better part.",font("italic",51),TEAL)
    paint(d,(82,152),"A good graph can",font("serifbold",69),WHITE)
    paint(d,(82,240),"also say  NO.",font("serifbold",88),ORANGE)
    graph_box(d,(78,388,393,100),"field_id","FieldOps source column",TEAL)
    if t>.8:
        polygon_arrow(d,(478,438),(552,438),TEAL,7)
        graph_box(d,(566,387,404,101),"Yield reporting","related output",TEAL)
    d.rounded_rectangle((1046,344,1467,427),radius=11,outline=(125,141,153),width=3)
    d.rounded_rectangle((1046,460,1467,543),radius=11,outline=(125,141,153),width=3)
    paint(d,(1082,360),"Supplier payout",font("sans",28),SOFT)
    paint(d,(1082,477),"Scope 3 assurance",font("sans",28),SOFT)
    if t>1.6:
        for y in (347,462):
            d.line((1019,y,1085,y+80),fill=RED,width=9)
            d.line((1085,y,1019,y+80),fill=RED,width=9)
    paste_screen(im,snaps["negative"],(350,345,1545,795),(84,607,936,216),t,.025)
    d=ImageDraw.Draw(im)
    paint(d,(1056,663),"No unrelated",font("serif",43),WHITE)
    paint(d,(1056,715),"false positives.",font("serif",43),WHITE)
def show_receipt(im,t,receipt_text):
    d=ImageDraw.Draw(im)
    paint(d,(77,45),"The change request gets a receipt.",font("serifbold",69),INK)
    note(d,"Not a vague red flag.",83,132,(174,86,52),35)
    d.rounded_rectangle((91,206,919,826),radius=7,fill=(255,253,245))
    d.rectangle((111,225,899,805),outline=(218,209,193),width=2)
    paint(d,(139,258),"DATA IMPACT REVIEW",font("mono",30),INK)
    d.line((140,316,858,316),fill=ORANGE,width=5)
    items=[
        "Asset: lab.assays.moisture_pct",
        "19 connected assets",
        "7 business outputs",
        "Supplier payout forecast",
        "LabTrack -> dry mass -> FinanceMart",
        "Scope 3 assurance",
        "LabTrack -> dry mass -> ClimateMart",
    ]
    for i,msg in enumerate(items):
        if t < .6+i*.19: continue
        y=348+i*58
        label=("• " if i in (0,1,2) else "→ " if i in (4,6) else "✓ ")
        col=(140,96,62) if i in (3,5) else INK
        paint(d,(150,y),label+msg,font("mono",26 if i in (0,1,2,4,6) else 31),col)
    paint(d,(133,786),"Source: demo/impact-review.md",font("mono",19),MUTED)
    paint(d,(986,277),"Exact paths.",font("serifbold",64),INK)
    paint(d,(989,374),"Reasons for",font("serifbold",62),INK)
    paint(d,(988,461),"every hop.",font("serifbold",62),INK)
    if t>2:
        paper_stamp(im,"READY TO REVIEW",979,591,-8,YELLOW)
    d=ImageDraw.Draw(im)
    paint(d,(997,772),"Attach to the PR.",font("italic",39),(155,78,54))
def show_outro(im,t):
    d=ImageDraw.Draw(im)
    paint(d,(85,72),"DATA  /  IMPACT  /  GRAPH",font("mono",27),TEAL)
    paint(d,(81,180),"Know what",font("serifbold",117),WHITE)
    paint(d,(81,305),"breaks",font("serifbold",132),ORANGE)
    paint(d,(79,455),"before you change it.",font("serifbold",93),WHITE)
    squiggle(d,81,576,1305,YELLOW,(t-.4)/1.25,8)
    d.rounded_rectangle((82,646,556,736),radius=10,outline=TEAL,width=3)
    paint(d,(107,666),"REAL RELATE / LOCAL",font("mono",31),TEAL)
    paint(d,(84,797),"github.com/mhatipog/data-impact-graph",font("mono",29),WHITE)
    paint(d,(1200,797),"APACHE-2.0",font("mono",21),SOFT)
    # Nonuniform moving mark: same line-and-branch motif as the opening.
    line_progress(d,[(1180,205),(1289,270),(1462,186)],ORANGE,11,(t-.2)/1.7)
    line_progress(d,[(1289,270),(1465,354)],TEAL,11,(t-.9)/1.3)
    for x,y,color in [(1180,205,WHITE),(1289,270,ORANGE),(1462,186,TEAL),(1465,354,TEAL)]:
        d.ellipse((x-12,y-12,x+12,y+12),fill=color)
def scene_image(scene,t,snaps,receipt):
    k=scene["key"]
    im=frame_base(k in ("change","fork","climate","receipt"))
    if k=="intro":show_intro(im,t)
    elif k=="change":show_change(im,t,snaps)
    elif k=="path":show_path(im,t,snaps)
    elif k=="fork":show_fork(im,t)
    elif k=="finance":show_finance(im,t,snaps)
    elif k=="climate":show_climate(im,t,snaps)
    elif k=="negative":show_negative(im,t,snaps)
    elif k=="receipt":show_receipt(im,t,receipt)
    elif k=="outro":show_outro(im,t)
    return im
SCENES=[
    dict(key="intro",minimum=5.6,voice="Most data problems don't begin with a dramatic failure. They begin with one small change."),
    dict(key="change",minimum=9.0,voice="Here, a lab field called moisture percent changes from a number out of a hundred to a fraction. The column name stays. Its meaning doesn't."),
    dict(key="path",minimum=10.0,voice="Data Impact Graph opens a real, embedded Relate database, and follows its Cypher paths. First the assay is normalized. Then dry mass is calculated."),
    dict(key="fork",minimum=8.0,voice="And now, the interesting part. That same dry-mass calculation feeds two teams that might never speak to each other."),
    dict(key="finance",minimum=7.0,voice="Finance uses payable dry kilograms to forecast supplier payouts. A quiet unit change can reach the money."),
    dict(key="climate",minimum=8.0,voice="Climate uses dry tonnes to calculate carbon intensity. The dependency chain reaches the Scope Three assurance dashboard."),
    dict(key="negative",minimum=8.0,voice="Change the field identifier instead, and neither payout nor carbon is affected. Good lineage analysis needs to know when not to raise the alarm."),
    dict(key="receipt",minimum=9.0,voice="Before merging, export the impact receipt. It gives a reviewer the affected outputs, actual dependency paths, and why every connection matters."),
    dict(key="outro",minimum=7.0,voice="One embedded graph. Forty-nine assets. Sixty relationships. Know what breaks before you change it. Data Impact Graph."),
]

async def speak(text,path):
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text=text,voice=VOICE,rate="-1%").save(str(path))
            if path.stat().st_size<1500:raise RuntimeError("Empty neural voice track")
            return
        except Exception:
            if attempt==2:raise
            await asyncio.sleep(3+attempt*2)
def frame_snapshot(path,time):
    cmd("ffmpeg","-hide_banner","-loglevel","error","-y",
        "-ss",str(time),"-i",str(SOURCE),"-frames:v","1",str(path))
    return Image.open(path).convert("RGB")
def render(scene,voice,filepath,seconds,snaps,receipt):
    total_frames=int(round(seconds*FPS))
    args=["ffmpeg","-hide_banner","-loglevel","error","-y",
          "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}",
          "-framerate",str(FPS),"-i","pipe:0","-i",str(voice),
          "-map","0:v:0","-map","1:a:0",
          "-c:v","libx264","-preset","veryfast","-crf","21",
          "-vf","scale=1920:1080:flags=lanczos",
          "-pix_fmt","yuv420p","-r",str(FPS),
          "-c:a","aac","-b:a","160k","-ar","44100",
          "-af",f"adelay=330|330,apad,atrim=duration={seconds:.3f}",
          "-t",str(seconds),"-movflags","+faststart",str(filepath)]
    proc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE)
    try:
        for i in range(total_frames):
            img=scene_image(scene,i/FPS,snaps,receipt)
            proc.stdin.write(img.tobytes())
        proc.stdin.close()
        error=proc.stderr.read().decode(errors="replace")
        rc=proc.wait()
        if rc:raise RuntimeError(f"Render failed: {scene['key']}\n"+error[-3200:])
    except Exception:
        proc.kill()
        raise
async def main():
    if not SOURCE.exists():raise RuntimeError("No original real-app screen recording")
    if duration(SOURCE)<98:raise RuntimeError("Original screen recording is truncated")
    text=RECEIPT.read_text()
    if ("Connected assets requiring review: 19" not in text or
        "Business outputs requiring review: 7" not in text or
        "Supplier payout forecast" not in text or
        "Scope 3 assurance" not in text):
        raise RuntimeError("Receipt provenance mismatch")
    with tempfile.TemporaryDirectory(prefix="story-v3-") as tmp:
        p=Path(tmp)
        samples={"change":3.7,"path":15.5,"finance":29.9,
                 "climate":43.0,"negative":63.0}
        snaps={k:frame_snapshot(p/(k+".png"),v) for k,v in samples.items()}
        segments=[]
        timeline={}
        at=0.
        for i,scene in enumerate(SCENES):
            print(f"SCENE {i+1}/{len(SCENES)}: {scene['key']}",flush=True)
            speech=p/f"{i:02d}-voice.mp3"
            await speak(scene["voice"],speech)
            spoken=duration(speech)
            seconds=max(scene["minimum"],spoken+1.00)
            seconds=round(math.ceil(seconds*FPS)/FPS,3)
            output=p/f"{i:02d}-scene.mp4"
            render(scene,speech,output,seconds,snaps,text)
            segments.append(output)
            timeline[scene["key"]]=round(at,3)
            at+=seconds
            scene["duration"]=seconds
            print(f"  done: {seconds:.2f}s, voice {spoken:.2f}s",flush=True)
        entries=p/"playlist.txt"
        entries.write_text("".join("file '"+str(x)+"'\n" for x in segments))
        assembled=p/"assembled.mp4"
        cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat",
            "-safe","0","-i",str(entries),"-c","copy",str(assembled))
        length=duration(assembled)
        cues=p/"cues.json"; cues.write_text(json.dumps(timeline))
        soundtrack=p/"original-score.wav"
        audio_info=json.loads(cmd("python","scripts/original-story-score.py",
                                  str(length),str(cues),str(soundtrack)).strip())
        # Side-chain duck the original score whenever the neural narration speaks.
        cmd("ffmpeg","-hide_banner","-loglevel","error","-y",
            "-i",str(assembled),"-i",str(soundtrack),
            "-filter_complex",
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[speech];"
            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.36[score];"
            "[score][speech]sidechaincompress=threshold=0.020:ratio=6:attack=22:release=380[duck];"
            "[speech][duck]amix=inputs=2:duration=first:weights='1 0.46':normalize=0,"
            "alimiter=limit=0.94[a]",
            "-map","0:v:0","-map","[a]","-c:v","copy",
            "-c:a","aac","-b:a","192k","-movflags","+faststart",str(OUT))
        actual=duration(OUT)
        if abs(actual-length)>1.0:raise RuntimeError("Bad final AV duration")
        if OUT.stat().st_size<3_000_000:raise RuntimeError("Unexpectedly small final video")
        streams=json.loads(cmd("ffprobe","-v","error","-show_streams","-of","json",str(OUT)))["streams"]
        if {x["codec_type"] for x in streams}!={"video","audio"}:
            raise RuntimeError("Missing narration/music or video stream")
        if any(x.get("codec_name") not in ("h264","aac") for x in streams):
            raise RuntimeError("Unexpected video or audio codec")
        # Review exactly one representative frame per actual chapter, not a mockup.
        sheet=Image.new("RGB",(1200,2025),(15,24,34))
        offset=0
        for i,scene in enumerate(SCENES):
            when=offset+scene["duration"]*.55
            imagepath=p/f"review-{i:02d}.png"
            cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(when),
                "-i",str(OUT),"-frames:v","1",str(imagepath))
            img=Image.open(imagepath).convert("RGB").resize((400,225),Image.Resampling.LANCZOS)
            sheet.paste(img,((i%3)*400,(i//3)*225))
            offset+=scene["duration"]
        # Keep visible blanks away: last 3 rows use 675 pixels.
        sheet=sheet.crop((0,0,1200,675))
        sheet.save(SHEET,optimize=True)
        sha=hashlib.sha256(OUT.read_bytes()).hexdigest()
        manifest={"kind":"story-first human-directed editorial cut",
                  "source":"genuine OCI Playwright screen recording and original Relate impact receipt",
                  "music":audio_info,"voice_engine":"Microsoft Edge Neural TTS","voice":VOICE,
                  "screen_capture_pivots":samples,"duration_seconds":actual,
                  "resolution":"1920x1080","fps":FPS,
                  "includes_intro":True,"includes_outro":True,
                  "video_bytes":OUT.stat().st_size,"sha256":sha,
                  "scenes":[{"name":s["key"],"duration":s["duration"],
                             "voice":s["voice"]} for s in SCENES]}
        MANIFEST.write_text(json.dumps(manifest,indent=2)+"\n")
        print("STORY_VIDEO_VERIFIED "+json.dumps({
              "duration":actual,"bytes":OUT.stat().st_size,"music":audio_info["source"],
              "scenes":len(SCENES),"sha256":sha}),flush=True)
if __name__=="__main__":
    asyncio.run(main())
