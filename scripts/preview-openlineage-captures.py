#!/usr/bin/env python3
"""Visual QA sheet made exclusively from the genuine Playwright screenshots."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root=Path("demo/film-working/screens")
names=["hero","overview-map","climate-route","climate-evidence","finance-route",
       "finance-evidence","negative-route","negative-evidence","results"]
size=(1440,1050)
image=Image.new("RGB",size,(11,20,33));d=ImageDraw.Draw(image)
font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",20)
bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",25)
d.text((32,16),"OPENLINEAGE / REAL RELATE BROWSER CAPTURE",fill=(240,244,246),font=bold)
d.text((32,53),"Captured via Playwright against the imported SDK-generated events. Never mocked.",fill=(169,196,202),font=font)
for i,name in enumerate(names):
    source=Image.open(root/(name+".png")).convert("RGB")
    source.thumbnail((462,263),Image.Resampling.LANCZOS)
    col=i%3;row=i//3
    x=20+col*478+(462-source.width)//2
    y=100+row*316
    image.paste(source,(x,y))
    d.text((24+col*478,y+267),name.upper().replace("-","  /  "),font=font,fill=(244,169,98))
destination=Path("demo/openlineage-browser-contact-sheet.png")
image.save(destination,optimize=True)
print("REAL_BROWSER_CONTACT_SHEET_OK",destination)
