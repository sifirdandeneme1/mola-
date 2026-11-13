#!/usr/bin/env python3
"""Patch only Web dashboard visibility and manually added radio station artwork."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
def target(rel):
    matches=list(root.glob("smali*/me/aap/fermata/"+rel+".smali"))
    if len(matches)!=1: raise RuntimeError(f"Expected exactly one {rel}: {matches}")
    return matches[0]
def once(s,old,new):
    if s.count(old)!=1: raise RuntimeError(f"Expected unique patch point: {old[:100]!r}; found {s.count(old)}")
    return s.replace(old,new,1)

web="me.aap.fermata.addon.web.WebBrowserAddon"
p=target("ui/fragment/DashboardItems")
s=p.read_text()
method=".method public static getDashboardItems(Landroid/content/Context;Lme/aap/utils/pref/PreferenceStore;)Ljava/util/List;"
i=s.index(method); j=s.index(".end method",i); fragment=s[i:j]
fragment=once(fragment,"    .locals 3","    .locals 4")
needle="""    .line 79
    invoke-static {p0, v2, v1}, Lme/aap/fermata/ui/fragment/DashboardItems;->getItem(Landroid/content/Context;Ljava/lang/String;Z)Lme/aap/fermata/ui/fragment/DashboardItems$Item;"""
replacement=f"""    # Custom: hide Web dashboard item, keep browser infrastructure intact
    const-string v3, "{web}"
    invoke-virtual {{v3, v2}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v3
    if-nez v3, :cond_0

"""+needle
fragment=once(fragment,needle,replacement); s=s[:i]+fragment+s[j:]
needle="""    :goto_3
    iget-object p1, p1, Lme/aap/fermata/addon/AddonInfo;->className:Ljava/lang/String;

    invoke-virtual {v0, p1}, Ljava/util/LinkedHashSet;->add(Ljava/lang/Object;)Z"""
replacement=f"""    :goto_3
    iget-object p1, p1, Lme/aap/fermata/addon/AddonInfo;->className:Ljava/lang/String;

    const-string v1, "{web}"
    invoke-virtual {{v1, p1}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v1
    if-nez v1, :goto_2

    invoke-virtual {{v0, p1}}, Ljava/util/LinkedHashSet;->add(Ljava/lang/Object;)Z"""
s=once(s,needle,replacement);p.write_text(s)

radio=target("addon/radio/RadioStageView")
s=radio.read_text()
needle="""    :cond_a
    move-object p1, v2

    :goto_5
    invoke-direct {p0, p1}, Lme/aap/fermata/addon/radio/RadioStageView;->setLogo(Ljava/lang/String;)V"""
replacement="""    :cond_a
    # Custom radio list: use station name to find original PNG from our logo repository
    invoke-interface {p1}, Lme/aap/fermata/media/lib/MediaLib$PlayableItem;->getName()Ljava/lang/String;
    move-result-object p1
    invoke-static {p1}, Lme/aap/fermata/addon/radio/MolaCustomLogos;->find(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1

    :goto_5
    invoke-direct {p0, p1}, Lme/aap/fermata/addon/radio/RadioStageView;->setLogo(Ljava/lang/String;)V"""
radio.write_text(once(s,needle,replacement))

stations=[
("Kral FM","kral_fm.png"),("Kral Pop","kral_pop.png"),("Power Türk FM","power_turk_fm.png"),
("PowerTürk Slow","powerturk_slow.png"),("Süper FM","super_fm.png"),("Best FM","best_fm.png"),
("JoyTürk","joyturk.png"),("Joy FM","joy_fm.png"),("Alem FM","alem_fm.png"),
("Show Radyo","show_radyo.png"),("Radyo 7","radyo_7.png"),("Radyo D","radyo_d.png"),
("NTV Radyo","ntv_radyo.png"),("Radyo Spor","radyo_spor.png"),("Slow Türk","slow_turk.png"),
("Kafa Radyo","kafa_radyo.png"),("Number One Türk","number_one_turk.png"),
("Radyo Voyage","radyo_voyage.png"),("Radyo Eksen","radyo_eksen.png")]
base="https://raw.githubusercontent.com/sifirdandeneme1/mola-/main/Radyo%20Logolar%C4%B1/"
lines=[".class public final Lme/aap/fermata/addon/radio/MolaCustomLogos;",".super Ljava/lang/Object;","",
".method public static find(Ljava/lang/String;)Ljava/lang/String;","    .locals 2","    if-eqz p0, :none"]
for n,(name,png) in enumerate(stations):
    lines+= [f'    const-string v0, "{name}"',
'    invoke-virtual {v0, p0}, Ljava/lang/String;->equalsIgnoreCase(Ljava/lang/String;)Z',
'    move-result v1',f'    if-eqz v1, :next_{n}',
f'    const-string v0, "{base}{png}"','    return-object v0',f'    :next_{n}']
lines+=["    :none","    const/4 v0, 0x0","    return-object v0",".end method",""]
out=radio.with_name("MolaCustomLogos.smali")
if out.exists(): raise RuntimeError("Already patched")
out.write_text("\n".join(lines))
print("PATCH APPLIED: hide Web dashboard tile; supply 19 logos for manually-added radio stations.")
