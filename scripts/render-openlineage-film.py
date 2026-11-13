#!/usr/bin/env python3
"""Edit a fact-checked, voice-led mini-film from an executed SQL -> SDK OpenLineage
-> embedded Relate -> Playwright -> review-receipt workflow.

All UI stills are authentic captures of the imported local application.
All illustrative graphics are explicitly editorial. The narration never calls
the local SQLite demonstration a real customer platform. The soundtrack is
composed locally and is original (scripts/original-story-score.py).
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
import sys

# Allow direct execution from scripts/ without requiring a pip editable install.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageOps
from data_impact_graph.core import overview

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"demo/data-impact-graph-openlineage-film.mp4"
SHEET=ROOT/"demo/openlineage-film-contact-sheet.png"
MANIFEST=ROOT/"demo/openlineage-film-manifest.json"
FPS=24
W,H=1600,900
BLACK=(10,19,30)
DARK=(17,33,46)
WHITE=(249,246,238)
PAPER=(245,239,226)
INK=(20,33,44)
COPPER=(243,151,91)
TEAL=(90,214,198)
YELLOW=(252,215,127)
MIST=(175,192,204)
RED=(224,105,91)
FACES={
 "display":"/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
 "serif":"/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
 "italic":"/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
 "sans":"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
 "strong":"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
 "mono":"/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
}
FONTS={}
def font(name,sz):
    key=(name,sz)
    if key not in FONTS:
        FONTS[key]=ImageFont.truetype(FACES[name],sz)
    return FONTS[key]

def run(*args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode:
        raise RuntimeError(" ".join(map(str,args))+" failed: "+p.stderr[-2400:])
    return p.stdout

def length(file):
    return float(run("ffprobe","-v","error","-show_entries","format=duration","-of",
              "default=noprint_wrappers=1:nokey=1",str(file)).strip())

def ease(v):
    v=max(0,min(1,v))
    return v*v*(3-2*v)

def t(draw,x,y,message,face,size,color,anchor=None):
    draw.text((int(x),int(y)),str(message),font=font(face,size),fill=color,anchor=anchor)

def wrapped(draw,x,y,message,face,size,color,width,gap=8,limit=10):
    words=message.split();lines=[];line=""
    for word in words:
        test=(line+" "+word).strip()
        if line and draw.textbbox((0,0),test,font=font(face,size))[2]>width:
            lines.append(line);line=word
        else:line=test
    if line:lines.append(line)
    for i,text in enumerate(lines[:limit]):
        t(draw,x,y+i*(size+gap),text,face,size,color)
    return y+len(lines[:limit])*(size+gap)

def scribble(draw,x,y,width,color,amount=1,thickness=6):
    pts=[]
    for i in range(60):
        phase=i/59
        pts.append((int(x+width*phase),
                    int(y+4*math.sin(phase*11.2)+1.8*math.sin(phase*39))))
    n=max(0,min(len(pts),round((len(pts)-1)*ease(amount))+1))
    if n>1:draw.line(pts[:n],fill=color,width=thickness,joint="curve")

def arrow(draw,a,b,color,width=6):
    draw.line((a,b),fill=color,width=width)
    phi=math.atan2(b[1]-a[1],b[0]-a[0])
    for dd in (-.6,.6):
        end=(b[0]-19*math.cos(phi+dd),b[1]-19*math.sin(phi+dd))
        draw.line((end,b),fill=color,width=width)

def bg(kind="night",accent=False):
    shade=PAPER if kind=="paper" else BLACK
    img=Image.new("RGB",(W,H),shade)
    d=ImageDraw.Draw(img)
    if kind=="paper":
        for y in range(37,H,42):
            d.line((37,y,W-37,y),fill=(234,228,214),width=1)
    else:
        for x in range(0,W,112):
            d.line((x,0,x,H),fill=(15,31,45),width=1)
        for y in range(0,H,112):
            d.line((0,y,W,y),fill=(15,31,45),width=1)
    return img

def mark(img,words,x,y,angle=-6,fill=YELLOW,scale=1.0):
    width=int(570*scale);height=int(90*scale)
    layer=Image.new("RGBA",(width,height),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    d.rounded_rectangle((4,5,width-5,height-4),radius=6,fill=(*fill,230))
    t(d,18,19,words,"mono",round(29*scale),INK)
    layer=layer.rotate(angle,expand=True,resample=Image.Resampling.BICUBIC)
    img.paste(layer,(int(x),int(y)),layer)

def actual_screenshot(img,source,xywh,zoom_at=0.0,focus=(.5,.5),border=TEAL,zoom_factor=1.0):
    """Crop only genuine Playwright pixels; never recreate or synthesize the UI."""
    x,y,w,h=map(int,xywh)
    sw,sh=source.size
    # Show the whole element where possible. Dynamic 3.5% camera push.
    ratio=max(w/sw,h/sh)*zoom_factor*(1+0.035*ease(zoom_at))
    nw=max(w,round(sw*ratio));nh=max(h,round(sh*ratio))
    frame=source.resize((nw,nh),Image.Resampling.LANCZOS)
    ox=min(max(0,round((nw-w)*focus[0])),nw-w)
    oy=min(max(0,round((nh-h)*focus[1])),nh-h)
    crop=frame.crop((ox,oy,ox+w,oy+h))
    d=ImageDraw.Draw(img)
    d.rounded_rectangle((x+14,y+16,x+w+14,y+h+16),radius=17,fill=(52,63,73))
    img.paste(crop,(x,y))
    d.rectangle((x,y,x+w,y+h),outline=border,width=3)

def pill(d,xywh,label,fill,face="mono",sz=24,color=INK):
    x,y,w,h=xywh
    d.rounded_rectangle((x,y,x+w,y+h),radius=12,fill=fill)
    t(d,x+17,y+(h-sz)//2-2,label,face,sz,color)

def get_evidence(work):
    capture=json.loads((work/"capture-manifest.json").read_text())
    proof=json.loads((work/"instrumented-run.json").read_text())
    imported=json.loads((work/"import-log.json").read_text())
    replay=json.loads((work/"replay-log.json").read_text())
    receipt=(work/"real-impact-receipt.md").read_text()
    rows=[json.loads(line) for line in (work/"instrumented-openlineage.jsonl").read_text().splitlines() if line.strip()]
    screens={n:Image.open(work/"screens"/(n+".png")).convert("RGB")
             for n in capture["captured"]}
    graph=overview(work/"imported.rl")
    names={a["id"]:a["name"] for a in graph["assets"]}
    finance=[names[x] for x in capture["finance_path"]]
    climate=[names[x] for x in capture["climate_path"]]
    assert finance[0]=="moisture_pct" and finance[-1]=="payout_eur"
    assert climate[0]=="moisture_pct" and climate[-1]=="co2e_per_dry_tonne"
    assert proof["events_count"]==10
    assert imported["unchanged"] is False and replay["unchanged"] is True
    assert capture["origin"].startswith("Playwright") and not capture["errors"]
    assert "ColumnLineage" in receipt or "columnLineage" in receipt
    assert "payout_eur" in receipt and "co2e_per_dry_tonne" in receipt
    assert any(r.get("eventType")=="COMPLETE" and
               "columnLineage" in r["outputs"][0]["facets"] for r in rows)
    return {"capture":capture,"proof":proof,"imported":imported,"replay":replay,
            "receipt":receipt,"events":rows,"screens":screens,
            "finance":finance,"climate":climate}

SCENES=[
 dict(name="hook",minimum=7.0,voice="A developer proposes changing one lab field from a percentage to a fraction. Before merging, there's one question: what else depends on it?"),
 dict(name="sql",minimum=9.0,voice="We begin with an actual local SQL pipeline. It executes normalization, dry mass, settlements, and carbon intensity. These aren't invented connections on a diagram."),
 dict(name="sdk",minimum=9.0,voice="The official OpenLineage client emits job and column lineage from those executed SQL expressions. These events identify precisely which input fields feed each output."),
 dict(name="import",minimum=8.0,voice="One import command turns those events into a persistent embedded Relate graph. No graph server, hosted account, or database credentials."),
 dict(name="question",minimum=9.0,voice="Now imagine reviewing that proposed moisture change. Search for the original column and ask Relate for its actual downstream paths."),
 dict(name="finance",minimum=9.0,voice="The first branch reaches supplier payouts, through normalized moisture and dry mass. It's an explicit, inspectable path, not an AI guess."),
 dict(name="climate",minimum=9.0,voice="The same calculation also reaches carbon intensity. Two business consequences, discovered while the engineer can still change the plan."),
 dict(name="precision",minimum=9.0,voice="Try field I D instead. That column leads toward field yield, not these finance or climate outputs. Missing lineage is still unknown, not a safety guarantee."),
 dict(name="review",minimum=9.0,voice="And the engineer can export a real Markdown impact receipt, showing downstream fields and every documented reason. Share it with reviewers before the merge."),
 dict(name="outro",minimum=7.5,voice="Bring the lineage you already have. Relate makes it locally queryable. Data Impact Graph makes the consequences reviewable, before you change the data."),
]

def scene(img,part,seconds,ev):
    k=part["name"];d=ImageDraw.Draw(img);s=ev["screens"];proof=ev["proof"]
    progress=min(1,seconds/2.0)
    if k=="hook":
        t(d,80,67,"THE CHANGE REQUEST  /  14:07", "mono",24,TEAL)
        t(d,74,178,"One column.", "display",122,WHITE)
        t(d,100,338,"Whose problem", "display",121,COPPER)
        t(d,102,478,"tomorrow?", "italic",112,WHITE)
        scribble(d,103,624,965,YELLOW,(seconds-.7)/1.4,8)
        pill(d,(94,716,543,65),"moisture_pct   0-100",DARK,"mono",28,WHITE)
        arrow(d,(680,752),(778,752),TEAL,7)
        pill(d,(801,716,421,65),"moisture_ratio  0-1",TEAL,"mono",24,INK)
        t(d,103,839,"BEFORE THE MERGE   •   FICTIONAL DATA", "mono",20,MIST)
    elif k=="sql":
        t(d,78,66,"01  /  THE SOURCE", "mono",24,(116,94,71))
        t(d,80,147,"The SQL", "display",121,INK)
        t(d,82,272,"really ran.", "italic",102,(167,79,56))
        scribble(d,82,401,525,COPPER,(seconds-.6)/1.5,7)
        t(d,86,491,"Executed locally in SQLite.", "sans",34,INK)
        t(d,88,546,"Column dependencies extracted", "sans",30,(82,88,88))
        t(d,88,593,"from the SQL expressions.", "sans",30,(82,88,88))
        pill(d,(87,701,486,82),"SQLGLOT  /  REAL QUERIES",YELLOW,"mono",25,INK)
        d.rounded_rectangle((677,118,1519,800),radius=16,fill=DARK)
        t(d,716,149,"NORMALIZE ASSAY  /  executed", "mono",21,TEAL)
        lines=proof["jobs"][0]["sql"].splitlines()
        yy=210
        for line in lines:
            color=COPPER if "moisture_pct" in line else WHITE
            t(d,716,yy,line.strip(),"mono",27,color);yy+=54
        d.line((715,452,1464,452),fill=(91,117,121),width=2)
        t(d,718,484,"CALCULATE DRY MASS  /  executed", "mono",21,TEAL)
        lines=proof["jobs"][1]["sql"].splitlines()
        yy=546
        for line in lines[:4]:
            txt=line.strip()
            t(d,716,yy,txt[:45],"mono",23,COPPER if "dry_kg" in txt else WHITE)
            yy+=46
        t(d,716,772,"3 fictional lots processed", "mono",18,MIST)
    elif k=="sdk":
        t(d,73,64,"02  /  EXISTING LINEAGE SIGNALS", "mono",23,TEAL)
        t(d,75,161,"OpenLineage", "display",119,WHITE)
        t(d,84,294,"did the talking.", "italic",99,COPPER)
        d.rounded_rectangle((85,465,1490,783),radius=16,fill=(25,43,59))
        t(d,115,488,"ACTUAL SDK-EMITTED EVENT   /   readable excerpt", "mono",20,MIST)
        event=next(e for e in ev["events"] if e.get("eventType")=="COMPLETE")
        field=event["outputs"][0]["facets"]["columnLineage"]["fields"]["moisture_ratio"]["inputFields"][0]
        t(d,122,551,'"eventType": "COMPLETE",', "mono",31,WHITE)
        t(d,122,610,'"job": "'+event["job"]["name"]+'",', "mono",31,WHITE)
        t(d,122,669,'moisture_ratio  <-  '+field["name"]+"."+field["field"],"mono",31,TEAL)
        scribble(d,120,723,1205,COPPER,(seconds-.5)/1.6,7)
        t(d,92,834,"Official OpenLineage Python SDK • columnLineage facet", "mono",21,MIST)
    elif k=="import":
        t(d,76,61,"03  /  FROM EVENTS TO A GRAPH", "mono",23,(134,89,64))
        t(d,81,156,"One command.", "display",134,INK)
        t(d,84,310,"No server to run.", "italic",88,(160,76,54))
        d.rounded_rectangle((91,464,1514,663),radius=14,fill=DARK)
        t(d,120,489,"$ python -m data_impact_graph import openlineage", "mono",30,WHITE)
        t(d,169,553,"events.jsonl --store graph.rl", "mono",37,TEAL)
        pill(d,(109,711,432,78),"OPENLINEAGE  EVENTS",YELLOW,"mono",22,INK)
        arrow(d,(571,751),(672,751),INK,7)
        pill(d,(698,711,431,78),"RELATE GRAPH   .rl",TEAL,"mono",24,INK)
        t(d,1193,732,"local • persistent", "mono",22,(84,89,88))
        t(d,96,839,"Replay tested • same events do not duplicate paths", "mono",20,(96,104,103))
    elif k=="question":
        t(d,78,50,"04  /  IN THE ACTUAL APP", "mono",24,TEAL)
        t(d,83,126,"Before changing the field,", "display",71,WHITE)
        t(d,81,208,"ask what depends on it.", "italic",73,COPPER)
        actual_screenshot(img,s["overview-map"],(73,347,1192,447),seconds/2.7,focus=(.13,.55),zoom_factor=1.72)
        d=ImageDraw.Draw(img)
        t(d,1301,406,"Search:", "mono",25,MIST)
        t(d,1283,462,"moisture", "display",52,WHITE)
        t(d,1293,526,"_pct", "display",57,COPPER)
        scribble(d,1294,598,212,TEAL,(seconds-1)/1.3,6)
        t(d,92,842,"LIVE RELATE TRAVERSAL   /   PLAYWRIGHT CAPTURE", "mono",19,MIST)
    elif k=="finance":
        t(d,81,55,"05  /  CONSEQUENCE 01", "mono",25,(132,78,55))
        t(d,82,145,"The money", "display",115,INK)
        t(d,84,290,"moves too.", "italic",100,(164,77,50))
        actual_screenshot(img,s["finance-route"],(67,445,1188,353),seconds/3,
                          focus=(.45,.28),border=COPPER)
        d=ImageDraw.Draw(img)
        pill(d,(1295,478,245,77),"PAYOUT EUR",COPPER,"mono",25,INK)
        t(d,1315,603,"dry_kg", "mono",26,INK)
        arrow(d,(1342,649),(1342,699),INK,5)
        t(d,1286,729,"payout_eur", "mono",25,(150,75,49))
        t(d,92,842,"From real Relate path evidence, not inferred by a language model", "mono",18,(89,96,95))
    elif k=="climate":
        t(d,75,54,"06  /  CONSEQUENCE 02", "mono",24,TEAL)
        t(d,78,143,"Now the carbon", "display",107,WHITE)
        t(d,82,266,"denominator.", "italic",93,COPPER)
        actual_screenshot(img,s["climate-route"],(77,412,1162,388),seconds/3,
                          focus=(.51,.30),border=TEAL)
        d=ImageDraw.Draw(img)
        t(d,1282,457,"dry_kg", "mono",28,WHITE)
        arrow(d,(1330,513),(1330,585),TEAL,7)
        t(d,1268,607,"CO2e per", "serif",49,TEAL)
        t(d,1283,677,"dry tonne", "serif",46,WHITE)
        scribble(d,1280,757,236,COPPER,(seconds-.6)/1.8,7)
        t(d,95,848,"Source: SDK-emitted column lineage / native Relate Cypher", "mono",20,MIST)
    elif k=="precision":
        t(d,71,56,"07  /  THE CONTRAST", "mono",24,(127,78,53))
        t(d,73,148,"Not every field", "display",102,INK)
        t(d,77,268,"is connected.", "italic",98,(158,76,51))
        d.rounded_rectangle((83,446,760,726),radius=15,fill=(252,247,235))
        d.rounded_rectangle((804,446,1523,726),radius=15,fill=DARK)
        t(d,112,469,"moisture_pct", "mono",33,INK)
        arrow(d,(344,566),(453,566),COPPER,8)
        t(d,465,519,"payout_eur", "mono",28,INK)
        t(d,465,581,"CO2e / tonne", "mono",26,(152,77,52))
        t(d,840,468,"field_id", "mono",33,WHITE)
        arrow(d,(1041,558),(1150,558),TEAL,8)
        t(d,1161,524,"field yield", "mono",26,TEAL)
        t(d,861,626,"No documented route to", "sans",25,MIST)
        t(d,861,666,"these two outputs.", "sans",25,MIST)
        t(d,85,803,"ABSENCE OF A PATH ≠ PROOF OF SAFETY", "mono",24,(168,72,50))
        scribble(d,85,847,665,COPPER,(seconds-.8)/1.6,6)
    elif k=="review":
        t(d,78,52,"08  /  PRE-MERGE REVIEW", "mono",23,TEAL)
        t(d,76,146,"The graph becomes", "display",97,WHITE)
        t(d,82,270,"a review receipt.", "italic",94,COPPER)
        d.rounded_rectangle((77,429,1181,829),radius=13,fill=PAPER)
        d.rounded_rectangle((106,456,1153,804),radius=7,outline=(208,192,171),width=2)
        t(d,128,482,"IMPACT RECEIPT   /   moisture_pct", "strong",34,INK)
        d.line((129,542,1118,542),fill=COPPER,width=4)
        t(d,131,560,"PROPOSED CHANGE   percent 0-100  ->  fraction 0-1", "mono",21,(110,91,77))
        d.ellipse((135,625,157,647),fill=COPPER)
        t(d,169,611,"Supplier settlement  /  "+ev["finance"][-1], "mono",29,INK)
        t(d,171,657,str(len(ev["finance"])-1)+" documented dependencies", "mono",21,(111,115,112))
        d.ellipse((135,723,157,745),fill=TEAL)
        t(d,169,709,"Carbon intensity  /  "+ev["climate"][-1], "mono",27,INK)
        t(d,171,761,str(len(ev["climate"])-1)+" documented dependencies", "mono",21,(111,115,112))
        t(d,1224,492,"Copy into", "italic",45,TEAL)
        t(d,1213,551,"the PR.", "display",67,WHITE)
        scribble(d,1218,655,271,COPPER,(seconds-.6)/1.8,7)
        t(d,1219,715,"Exact paths", "sans",30,MIST)
        t(d,1219,761,"and reasons.", "sans",30,MIST)
    elif k=="outro":
        t(d,80,69,"DATA IMPACT GRAPH  /  OPEN SOURCE", "mono",23,TEAL)
        t(d,80,184,"Your lineage.", "display",122,WHITE)
        t(d,80,324,"Local Relate.", "display",116,COPPER)
        t(d,80,470,"Better reviews.", "italic",104,WHITE)
        scribble(d,86,606,1090,YELLOW,(seconds-.5)/1.5,9)
        pill(d,(87,688,385,72),"OPENLINEAGE",TEAL,"mono",27,INK)
        pill(d,(501,688,346,72),"EMBEDDED GRAPH",YELLOW,"mono",22,INK)
        pill(d,(874,688,454,72),"EXPLAINABLE IMPACT",COPPER,"mono",21,INK)
        t(d,91,836,"github.com/mhatipog/data-impact-graph", "mono",26,WHITE)
        t(d,1370,839,"APACHE 2.0", "mono",18,MIST)

async def speak(line,out):
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text=line,voice="en-US-AndrewNeural",
                                       rate="-2%").save(str(out))
            if out.stat().st_size<1200:raise RuntimeError("Empty voice file")
            return
        except Exception:
            if attempt==2:raise
            await asyncio.sleep(2+attempt*2)

def make_segment(scene_spec,ev,voice,output,seconds):
    total=round(seconds*FPS)
    command=["ffmpeg","-hide_banner","-loglevel","error","-y",
             "-f","rawvideo","-pixel_format","rgb24",
             "-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0",
             "-i",str(voice),
             "-map","0:v:0","-map","1:a:0",
             "-c:v","libx264","-preset","veryfast","-crf","19",
             "-vf","scale=1920:1080:flags=lanczos",
             "-pix_fmt","yuv420p","-r",str(FPS),
             "-c:a","aac","-b:a","160k","-ar","44100",
             "-af",f"adelay=230|230,apad,atrim=duration={seconds:.3f}",
             "-t",f"{seconds:.3f}","-movflags","+faststart",str(output)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE,
                          stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for i in range(total):
            elapsed=i/FPS
            look="paper" if scene_spec["name"] in ("sql","import","finance","precision") else "night"
            img=bg(look)
            scene(img,scene_spec,elapsed,ev)
            proc.stdin.write(img.tobytes())
        proc.stdin.close()
        stderr=proc.stderr.read().decode(errors="replace")
        if proc.wait():raise RuntimeError(scene_spec["name"]+": "+stderr[-2500:])
    except Exception:
        proc.kill()
        raise

async def main(work):
    work=Path(work)
    ev=get_evidence(work)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dig-film-v4-") as tmp:
        workdir=Path(tmp)
        parts=[]
        cues={}
        elapsed=0.0
        for idx,item in enumerate(SCENES):
            voice=workdir/f"{idx:02d}-voice.mp3"
            await speak(item["voice"],voice)
            seconds=math.ceil(max(item["minimum"],length(voice)+.9)*FPS)/FPS
            cue_name=("intro" if idx==0 else "outro" if item["name"]=="outro" else item["name"])
            cues[cue_name]=round(elapsed,3)
            elapsed+=seconds
            item["duration"]=round(seconds,3)
            mp4=workdir/f"{idx:02d}-scene.mp4"
            print(f"SCENE {idx+1}/{len(SCENES)}: {item['name']} ({seconds:.2f}s)",flush=True)
            make_segment(item,ev,voice,mp4,seconds)
            parts.append(mp4)
        listing=workdir/"concat.txt"
        listing.write_text("".join("file '"+str(p)+"'\n" for p in parts))
        combined=workdir/"combined.mp4"
        run("ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
            "-i",str(listing),"-c","copy",str(combined))
        seconds=length(combined)
        cuefile=workdir/"cues.json";cuefile.write_text(json.dumps(cues))
        music=workdir/"original-score.wav"
        audio=json.loads(run("python","scripts/original-story-score.py",
                             str(seconds),str(cuefile),str(music)).strip())
        run("ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(combined),
            "-i",str(music),"-filter_complex",
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            "asplit=2[speechsc][speechmix];"
            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.68[score];"
            "[score][speechsc]sidechaincompress=threshold=0.020:ratio=6:attack=22:release=440[duck];"
            "[speechmix][duck]amix=inputs=2:duration=first:weights='1 0.53':normalize=0,"
            "alimiter=limit=0.94[a]",
            "-map","0:v:0","-map","[a]",
            "-c:v","copy","-c:a","aac","-b:a","192k",
            "-movflags","+faststart",str(OUT))
        actual=length(OUT)
        if abs(actual-seconds)>.8:raise RuntimeError("AV length mismatch")
        if not (77<=actual<=145):raise RuntimeError("Unexpected duration "+str(actual))
        if OUT.stat().st_size<500_000:raise RuntimeError("Video file implausibly small")
        tracks=json.loads(run("ffprobe","-v","error","-show_streams","-of","json",str(OUT)))["streams"]
        if sorted(t["codec_name"] for t in tracks)!=["aac","h264"]:
            raise RuntimeError("Expected H.264 video + AAC voice/music")
        # Decode beginning, middle, and final pictures as a media integrity check.
        for when in (1,actual*.5,actual-1.0):
            run("ffmpeg","-hide_banner","-loglevel","error","-ss",str(when),"-i",str(OUT),
                "-frames:v","1","-f","null","-")
        audio_probe=subprocess.run(["ffmpeg","-hide_banner","-i",str(OUT),
                          "-vn","-af","volumedetect","-f","null","-"],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        if audio_probe.returncode or "mean_volume" not in audio_probe.stderr:
            raise RuntimeError("Could not verify mixed audio")
        # A final-sheet frame is extracted from the finished MP4 for each scene.
        sheet=Image.new("RGB",(1600,1080),(9,18,28))
        offset=0
        for i,item in enumerate(SCENES):
            stamp=workdir/f"final-{i:02d}.png"
            run("ffmpeg","-hide_banner","-loglevel","error","-y",
                "-ss",str(offset+item["duration"]*.58),"-i",str(OUT),
                "-frames:v","1",str(stamp))
            picture=Image.open(stamp).convert("RGB")
            picture=picture.resize((400,225),Image.Resampling.LANCZOS)
            x=(i%4)*400;y=(i//4)*270
            sheet.paste(picture,(x,y))
            d=ImageDraw.Draw(sheet)
            t(d,x+10,y+228,item["name"].upper().replace("_"," / "),"mono",19,COPPER)
            offset+=item["duration"]
        sheet=sheet.crop((0,0,1600,810))
        sheet.save(SHEET,optimize=True)
        manifest={
          "title":"Before the Merge — Data Impact Graph",
          "source":"executed SQLite ETL + official OpenLineage SDK + native Relate + real Playwright browser",
          "source_data":"fictional sample lots; no customer data",
          "events_generated_by_sdk":len(ev["events"]),
          "event_sha256":hashlib.sha256((work/"instrumented-openlineage.jsonl").read_bytes()).hexdigest(),
          "replay_idempotent":ev["replay"]["unchanged"],
          "browser_assertions":ev["capture"]["origin"],
          "native_paths":{"finance":ev["finance"],"climate":ev["climate"]},
          "music":audio,"narration_voice":"en-US-AndrewNeural",
          "duration_seconds":actual,"fps":FPS,"resolution":"1920x1080",
          "video_bytes":OUT.stat().st_size,
          "sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
          "scenes":[{"name":it["name"],"duration_seconds":it["duration"],
                     "voice":it["voice"]} for it in SCENES],
          "verification":"source events/graph paths, Playwright, H264/AAC, decoded frames, volume"
        }
        MANIFEST.write_text(json.dumps(manifest,indent=2)+"\n")
        print("OPENLINEAGE_HACKATHON_FILM_VERIFIED "+json.dumps({
          "seconds":actual,"bytes":OUT.stat().st_size,
          "scenes":len(SCENES),"sdk_events":len(ev["events"]),
          "audio":"original score + AndrewNeural"}),flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--work",default="demo/film-working")
    asyncio.run(main(parser.parse_args().work))
