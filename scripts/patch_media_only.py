#!/usr/bin/env python3
"""Apply ONLY selected TV and radio sources to the GPL Mola 2.2.2 code.

Source code is checked out separately from the original project; this script
keeps only our own changes in the private repository.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT / "upstream"


def replace(path, old, new, count=1):
    file = UP / path
    text = file.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        raise RuntimeError(f"{path}: expected {count} occurrences but found {found}: {old[:75]!r}")
    file.write_text(text.replace(old, new), encoding="utf-8")


def insert_at(path, needle, addition):
    replace(path, needle, needle + addition)


def main():
    for sub, name in [("tv", "mola_tv.m3u"), ("radio", "mola_radio.m3u")]:
        destination = UP / "modules" / sub / "src" / "main" / "assets" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "iptv" / ("tv.m3u" if sub == "tv" else "radio.m3u"), destination)

    tv_repo = "modules/tv/src/main/java/me/aap/fermata/addon/tv/TvSourceRepository.java"
    insert_at(
        tv_repo,
        '\tstatic final String DEFAULT_PLAYLIST_URL = "https://onureroz.com/indirmeler/turk/index.m3u";',
        '\n\tstatic String molaPlaylistUrl() {\n'
        '\t\treturn new java.io.File(me.aap.utils.app.App.get().getFilesDir(), "mola_tv.m3u").getAbsolutePath();\n'
        '\t}\n'
    )
    replace(
        tv_repo,
        "seedPlaylist(DEFAULT_PLAYLIST_SEEDED, DEFAULT_PLAYLIST_URL, urlForId, createM3uId);",
        "seedPlaylist(DEFAULT_PLAYLIST_SEEDED, molaPlaylistUrl(), urlForId, createM3uId);"
    )

    tv_root = "modules/tv/src/main/java/me/aap/fermata/addon/tv/TvRootItem.java"
    replace(
        tv_root,
        '\t\tTvM3uFileSystem fs = TvM3uFileSystem.getInstance();\n\t\tsources.seedDefaultPlaylist',
        '\t\tinstallMolaTvPlaylist();\n'
        '\t\tTvM3uFileSystem fs = TvM3uFileSystem.getInstance();\n\t\tsources.seedDefaultPlaylist',
        1
    )
    replace(
        tv_root,
        'TvSourceRepository.DEFAULT_PLAYLIST_URL',
        'TvSourceRepository.molaPlaylistUrl()',
        3
    )
    replace(
        tv_root,
        '\t\ttry {\n\t\t\tsources.seedDefaultRadioPlaylist(id -> new TvM3uFile(fs.toRid(id)).getUrl(), () ->\n'
        '\t\t\t\t\tfs.toId(fs.newDefaultSource(TvSourceRepository.DEFAULT_RADIO_URL,\n'
        '\t\t\t\t\t\t\tgetLib().getContext().getString(R.string.default_turkish_radios)).getRid()));\n'
        '\t\t} catch (RuntimeException failure) {\n'
        '\t\t\tLog.e(failure, "Failed to register the default radio list");\n'
        '\t\t}\n',
        '',
        1
    )
    replace(
        tv_root,
        'return !hasDefaultPlaylist() || !hasDefaultRadioPlaylist();',
        'return !hasDefaultPlaylist();'
    )
    replace(
        tv_root,
        '\t\tif (!hasDefaultRadioPlaylist()) {\n'
        '\t\t\taddM3uSource(TvSourceRepository.DEFAULT_RADIO_URL,\n'
        '\t\t\t\t\tgetLib().getContext().getString(R.string.default_turkish_radios));\n'
        '\t\t}\n',
        '',
        1
    )
    # Put asset copy in the same TV root, so the existing playlist parser
    # continues loading the exact URI format supported by Mola.
    marker = '\t@Override\n\tprotected FutureSupplier<List<Item>> listChildren() {'
    method = (
        '\tprivate void installMolaTvPlaylist() {\n'
        '\t\tjava.io.File file = new java.io.File(getLib().getContext().getFilesDir(), "mola_tv.m3u");\n'
        '\t\ttry (java.io.InputStream source = getLib().getContext().getAssets().open("mola_tv.m3u")) {\n'
        '\t\t\tjava.nio.file.Files.copy(source, file.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);\n'
        '\t\t} catch (java.io.IOException failure) {\n'
        '\t\t\tLog.e(failure, "Could not install Mola TV channels");\n'
        '\t\t}\n'
        '\t}\n\n'
    )
    original = (UP / tv_root).read_text(encoding="utf-8")
    if original.count(marker) != 1:
        raise RuntimeError("Cannot find TV listChildren()")
    (UP / tv_root).write_text(original.replace(marker, method + marker), encoding="utf-8")

    radio_store = "modules/radio/src/main/java/me/aap/fermata/addon/radio/RadioSourceStore.java"
    marker = '\tsynchronized List<RadioSource> list() {'
    method = (
        '\t/** Install the 19 personally selected stations exactly once. */\n'
        '\tsynchronized void seedMolaStations(Context ctx) {\n'
        '\t\tif (preferences.getBoolean("MOLA_RADIO_SEEDED_V1", false)) return;\n'
        '\t\ttry (java.io.BufferedReader reader = new java.io.BufferedReader(\n'
        '\t\t\t\tnew java.io.InputStreamReader(ctx.getAssets().open("mola_radio.m3u"), java.nio.charset.StandardCharsets.UTF_8))) {\n'
        '\t\t\tString line;\n'
        '\t\t\tString name = null;\n'
        '\t\t\tint number = 0;\n'
        '\t\t\twhile ((line = reader.readLine()) != null) {\n'
        '\t\t\t\tline = line.trim();\n'
        '\t\t\t\tif (line.startsWith("#EXTINF:")) {\n'
        '\t\t\t\t\tint comma = line.lastIndexOf(\',\');\n'
        '\t\t\t\t\tname = (comma >= 0) ? line.substring(comma + 1).trim() : null;\n'
        '\t\t\t\t} else if ((name != null) && (line.startsWith("http://") || line.startsWith("https://"))) {\n'
        '\t\t\t\t\tRadioSource source = RadioSource.restore("mola-" + (++number), name, line);\n'
        '\t\t\t\t\tif (source.isValid()) save(source);\n'
        '\t\t\t\t\tname = null;\n'
        '\t\t\t\t}\n'
        '\t\t\t}\n'
        '\t\t\tif (number != 19) throw new java.io.IOException("Expected 19 radio stations, got " + number);\n'
        '\t\t\tpreferences.edit().putBoolean("MOLA_RADIO_SEEDED_V1", true).apply();\n'
        '\t\t} catch (java.io.IOException e) {\n'
        '\t\t\tandroid.util.Log.e("Mola", "Failed to install radio list", e);\n'
        '\t\t}\n'
        '\t}\n\n'
    )
    original = (UP / radio_store).read_text(encoding="utf-8")
    if original.count(marker) != 1:
        raise RuntimeError("Cannot find RadioSourceStore list()")
    (UP / radio_store).write_text(original.replace(marker, method + marker), encoding="utf-8")

    radio_root = "modules/radio/src/main/java/me/aap/fermata/addon/radio/RadioRootItem.java"
    replace(
        radio_root,
        '\t\tsourceStore = new RadioSourceStore(lib.getContext());',
        '\t\tsourceStore = new RadioSourceStore(lib.getContext());\n'
        '\t\tsourceStore.seedMolaStations(lib.getContext());'
    )
    replace(
        radio_root,
        '\t\tList<Item> items = new ArrayList<>(sources.size() + 4);',
        '\t\tList<Item> items = new ArrayList<>(sources.size());'
    )
    replace(
        radio_root,
        '\t\titems.add(turkey());\n\t\titems.add(RadioStationFolder.popular(this));\n'
        '\t\titems.add(RadioStationFolder.topVoted(this));\n'
        '\t\titems.add(RadioDirectoryFolder.countries(this));\n'
        '\t\titems.add(RadioDirectoryFolder.tags(this));\n',
        ''
    )


    # Personal front-end: keep the underlying TV, radio, YouTube and Android Auto
    # services untouched. Change the shared dashboard and projection nav only.
    dashboard_items = "fermata/src/main/java/me/aap/fermata/ui/fragment/DashboardItems.java"
    dashboard_model = "fermata/src/main/java/me/aap/fermata/ui/fragment/DashboardModelBuilder.java"
    nav_mediator = "fermata/src/main/java/me/aap/fermata/ui/fragment/NavBarMediator.java"
    replace(dashboard_items,
        "\t\tList<Item> items = new ArrayList<>();\n\t\tfor (String name : getLayout(store, false, false, false)) {\n\t\t\tItem item = getItem(ctx, name, false);\n\t\t\tif (item != null) items.add(item);\n\t\t}\n\t\treturn items;",
        "\t\tList<Item> items = new ArrayList<>();\n\t\tfor (String name : getLayout(store, false, false, false)) {\n\t\t\tItem item = getItem(ctx, name, false);\n\t\t\tif ((item != null) && isPersonalMediaAddon(item.addonInfo)) items.add(item);\n\t\t}\n\t\titems.sort((a, b) -> Integer.compare(personalMediaRank(a.addonInfo),\n\t\t\t\tpersonalMediaRank(b.addonInfo)));\n\t\treturn items;", 1)

    replace(dashboard_items,
        "\t\tList<NavItem> items = new ArrayList<>();\n\t\tfor (String name : getNavLayout(store)) {\n\t\t\tNavItem item = getNavItem(name);\n\t\t\tif (item != null) items.add(item);\n\t\t}\n\t\treturn items;",
        "\t\tList<NavItem> items = new ArrayList<>();\n\t\tfor (String name : getNavLayout(store)) {\n\t\t\tif (!DASHBOARD.equals(name) && !isPersonalMediaAddon(findAddonInfo(name))) continue;\n\t\t\tNavItem item = getNavItem(name);\n\t\t\tif (item != null) items.add(item);\n\t\t}\n\t\titems.sort((a, b) -> Integer.compare(personalMediaRank(findAddonInfo(a.name)),\n\t\t\t\tpersonalMediaRank(findAddonInfo(b.name))));\n\t\treturn items;", 1)

    replace(dashboard_items,
        "\tprivate static boolean isReorderable(String name) {",
        "\t/** Keep only the three personal media destinations visible; modules remain installed. */\n\tprivate static boolean isPersonalMediaAddon(@Nullable AddonInfo info) {\n\t\tif (info == null) return false;\n\t\treturn switch (AddonUiMetadata.role(info)) {\n\t\t\tcase TV, RADIO, YOUTUBE -> true;\n\t\t\tdefault -> false;\n\t\t};\n\t}\n\n\tprivate static int personalMediaRank(@Nullable AddonInfo info) {\n\t\tif (info == null) return -1; // Dashboard (home) stays first in the rail.\n\t\treturn switch (AddonUiMetadata.role(info)) {\n\t\t\tcase TV -> 0;\n\t\t\tcase RADIO -> 1;\n\t\t\tcase YOUTUBE -> 2;\n\t\t\tdefault -> 99;\n\t\t};\n\t}\n\n\tprivate static boolean isReorderable(String name) {", 1)

    replace(dashboard_model,
        "\tvoid rebuild(List<DashboardCard> cards, @Nullable DashboardCard smartTopCard) {\n\t\tcards.clear();\n\t\tDashboardCard visibleSmartTop = smartTopVisible ? smartTopCard : null;\n\t\tfor (DashboardItems.Item item : DashboardItems.getDashboardItems(ctx, store)) {\n\t\t\tif (shouldSuppressRecent(visibleSmartTop != null, item.id)) continue;\n\t\t\tif ((visibleSmartTop != null) && (visibleSmartTop.targetId == item.id)) continue;\n\t\t\tDashboardCard card = DashboardCard.item(item);\n\t\t\tif (automotive && (item.addonInfo != null)) card = card.withTitle(emphasizeAddonTitle(card.title));\n\t\t\tcards.add(card);\n\t\t}\n\t\tfor (DashboardItems.Item item : DashboardItems.getWebShortcutItems(ctx, store)) {\n\t\t\tcards.add(DashboardCard.item(item));\n\t\t}\n\t\tcards.add(DashboardCard.favoritesShelf(ctx));\n\t\tcards.add(DashboardCard.recentShelf(ctx));\n\t\tif (visibleSmartTop != null) cards.add(visibleSmartTop);\n\t}\n",
        "\tvoid rebuild(List<DashboardCard> cards, @Nullable DashboardCard smartTopCard) {\n\t\tcards.clear();\n\t\t// Only TV, Radio and YouTube; no web links, mirror, favorites or recent shelves.\n\t\tfor (DashboardItems.Item item : DashboardItems.getDashboardItems(ctx, store)) {\n\t\t\tDashboardCard card = DashboardCard.item(item);\n\t\t\tif (automotive && (item.addonInfo != null)) card = card.withTitle(emphasizeAddonTitle(card.title));\n\t\t\tcards.add(card);\n\t\t}\n\t}\n", 1)

    replace(nav_mediator,
        "\t\taddVoiceButton(nb);",
        "\t\t// Hide the optional voice-control shortcut in the personal three-item UI.", 2)


    # TV-only Back: stop stream and show the current channel list on first Back.
    # Radio and YouTube navigation remain unchanged.
    tv_fragment = "modules/tv/src/main/java/me/aap/fermata/addon/tv/TvFragment.java"
    replace(tv_fragment,
        "\t@Override\n\tpublic FloatingButton.Mediator getFloatingButtonMediator() {",
        "\t@Override\n\tpublic boolean onBackPressed() {\n\t\tMainActivityDelegate activity = getMainActivity();\n\t\tif (activity.isVideoMode()) {\n\t\t\t// Stop the TV stream before returning to the current channel list.\n\t\t\t// Leave the selected category unchanged for the next Back press.\n\t\t\tactivity.getMediaSessionCallback().onStop();\n\t\t\tme.aap.fermata.ui.view.VideoPresentationController.showFrame(activity);\n\t\t\treturn true;\n\t\t}\n\t\treturn super.onBackPressed();\n\t}\n\n\t@Override\n\tpublic FloatingButton.Mediator getFloatingButtonMediator() {")


    # Three equal large home cards: TV, Radio, YouTube.
    dashboard_fragment = "fermata/src/main/java/me/aap/fermata/ui/fragment/DashboardFragment.java"
    replace(
        dashboard_fragment,
        'return (role == AddonUiMetadata.Role.TV) || (role == AddonUiMetadata.Role.YOUTUBE);',
        'return (role == AddonUiMetadata.Role.TV) || (role == AddonUiMetadata.Role.YOUTUBE) ||\n'
        '\t\t\t\t(role == AddonUiMetadata.Role.RADIO);'
    )

    # Remove phone-only AA status and "Open on car" row without deleting its
    # views; the existing controller still needs those IDs. Media controls stay.
    phone_strip = "fermata/src/main/res/layout/phone_open_on_car_strip.xml"
    replace(phone_strip, 'android:layout_height="228dp"', 'android:layout_height="200dp"')
    replace(
        phone_strip,
        'android:id="@+id/phone_header_utility"\n'
        '        android:layout_width="0dp"\n'
        '        android:layout_height="28dp"',
        'android:id="@+id/phone_header_utility"\n'
        '        android:layout_width="0dp"\n'
        '        android:layout_height="28dp"\n'
        '        android:visibility="gone"'
    )

    print("Personal Mola: 3 equal hero cards, clean phone header, TV Back retained; no logo or YouTube Music changes")


if __name__ == "__main__":
    main()
