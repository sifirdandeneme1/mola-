#!/usr/bin/env python3
"""Mola four-card test edition, applied to pinned upstream after patch_media_only."""
from pathlib import Path
import patch_media_only

UP = Path(__file__).resolve().parents[1] / "upstream"

def change(path, old, new, count=1):
    p = UP / path
    s = p.read_text(encoding="utf-8")
    if s.count(old) != count:
        raise RuntimeError(f"{path}: expected {count}, found {s.count(old)} for {old[:110]!r}")
    p.write_text(s.replace(old, new), encoding="utf-8")

def main():
    patch_media_only.main()
    items = "fermata/src/main/java/me/aap/fermata/ui/fragment/DashboardItems.java"
    change(items,
        "if ((item != null) && isPersonalMediaAddon(item.addonInfo)) items.add(item);",
        "if ((item != null) && isPersonalMediaAddon(item.addonInfo)) items.add(item);")
    change(items,
        "\t\titems.sort((a, b) -> Integer.compare(personalMediaRank(a.addonInfo),\n"
        "\t\t\t\tpersonalMediaRank(b.addonInfo)));\n\t\treturn items;",
        "\t\t// Local files are an actual folders destination, not an addon.\n"
        "\t\titems.add(getItem(ctx, FOLDERS, false));\n"
        "\t\titems.sort((a, b) -> Integer.compare(personalMediaRank(a.name, a.addonInfo),\n"
        "\t\t\t\tpersonalMediaRank(b.name, b.addonInfo)));\n\t\treturn items;",1)
    change(items,
        "if (!DASHBOARD.equals(name) && !isPersonalMediaAddon(findAddonInfo(name))) continue;",
        "if (!DASHBOARD.equals(name) && !FOLDERS.equals(name) && "
        "!isPersonalMediaAddon(findAddonInfo(name))) continue;")
    change(items,
        "\t\titems.sort((a, b) -> Integer.compare(personalMediaRank(findAddonInfo(a.name)),\n"
        "\t\t\t\tpersonalMediaRank(findAddonInfo(b.name))));",
        "\t\tif (items.stream().noneMatch(i -> FOLDERS.equals(i.name))) "
        "items.add(getNavItem(FOLDERS));\n"
        "\t\titems.sort((a, b) -> Integer.compare(personalMediaRank(a.name, findAddonInfo(a.name)),\n"
        "\t\t\t\tpersonalMediaRank(b.name, findAddonInfo(b.name))));")
    change(items,
        "\tprivate static int personalMediaRank(@Nullable AddonInfo info) {\n"
        "\t\tif (info == null) return -1; // Dashboard (home) stays first in the rail.\n"
        "\t\treturn switch (AddonUiMetadata.role(info)) {\n"
        "\t\t\tcase TV -> 0;\n\t\t\tcase RADIO -> 1;\n"
        "\t\t\tcase YOUTUBE -> 2;\n\t\t\tdefault -> 99;\n\t\t};\n\t}",
        "\tprivate static int personalMediaRank(String name, @Nullable AddonInfo info) {\n"
        "\t\tif (DASHBOARD.equals(name)) return -1;\n"
        "\t\tif (FOLDERS.equals(name)) return 2;\n"
        "\t\tif (info == null) return 99;\n"
        "\t\treturn switch (AddonUiMetadata.role(info)) {\n"
        "\t\t\tcase TV -> 0;\n\t\t\tcase RADIO -> 1;\n"
        "\t\t\tcase YOUTUBE -> 3;\n\t\t\tdefault -> 99;\n\t\t};\n\t}")
    # Preserve local file browser and navigation; rename only its visible title.
    change(items,
        "ctx.getString(R.string.folders), ctx.getString(R.string.dashboard_folders_sub), null);",
        '"Medya", ctx.getString(R.string.dashboard_folders_sub), null);')
    change(items,
        "R.string.folders);\n\t\t\tcase FAVORITES:",
        "R.string.mola_media);\n\t\t\tcase FAVORITES:")
    strings = "fermata/src/main/res/values/strings.xml"
    change(strings, "</resources>", '    <string name="mola_media">Medya</string>\n</resources>')
    grid = "fermata/src/main/java/me/aap/fermata/ui/fragment/DashboardGridPolicy.java"
    change(grid,
        "return columns >= 3 ? 15 : Math.max(1, columns);",
        "return columns >= 4 ? 4 : (columns >= 3 ? 3 : Math.max(1, columns));")
    change(grid,
        "if (spans == 15) return featured ? 5 : 3;",
        "// Four equal hero cards on landscape projection; 2x2 on mobile.")
    dashboard = "fermata/src/main/java/me/aap/fermata/ui/fragment/DashboardFragment.java"
    change(dashboard,
        "if (widthDp < 460F) return 1;\n"
        "\t\tint spans = (int) (widthDp / 220F);\n"
        "\t\treturn Math.max(2, Math.min(3, spans));",
        "if (widthDp < 320F) return 1;\n"
        "\t\treturn widthDp >= 620F ? 4 : 2;")
    change(dashboard,
        "if (DashboardItems.MIRROR.equals(item.name)) return true;",
        "if (DashboardItems.MIRROR.equals(item.name) || "
        "DashboardItems.FOLDERS.equals(item.name)) return true;")
    change(dashboard,
        "holder.heroArt.setImageDrawable(DashboardArtwork.hero(ctx, role));",
        "if (DashboardItems.FOLDERS.equals(card.item.name)) {\n"
        "\t\t\t\tholder.heroArt.setScaleType(android.widget.ImageView.ScaleType.FIT_CENTER);\n"
        "\t\t\t\tholder.heroArt.setImageDrawable(ctx.getDrawable(me.aap.utils.R.drawable.folder));\n"
        "\t\t\t} else {\n"
        "\t\t\t\tholder.heroArt.setScaleType(android.widget.ImageView.ScaleType.FIT_XY);\n"
        "\t\t\t\tholder.heroArt.setImageDrawable(DashboardArtwork.hero(ctx, role));\n"
        "\t\t\t}")
    dims="fermata/src/main/res/values/dimens.xml"
    change(dims, '<dimen name="dashboard_tile_height">244dp</dimen>',
          '<dimen name="dashboard_tile_height">122dp</dimen>')
    featured="fermata/src/main/res/layout/dashboard_featured_item.xml"
    change(featured, 'android:textSize="26sp"', 'android:textSize="17sp"')
    change(featured, 'android:layout_marginStart="22dp"', 'android:layout_marginStart="10dp"')
    change(featured, 'android:layout_marginEnd="18dp"', 'android:layout_marginEnd="7dp"')
    change(featured, 'android:layout_marginBottom="22dp"', 'android:layout_marginBottom="7dp"')
    change(featured, 'android:id="@+id/dashboard_hero_arrow"\n        android:layout_width="48dp"\n        android:layout_height="48dp"',
          'android:id="@+id/dashboard_hero_arrow"\n        android:layout_width="32dp"\n        android:layout_height="32dp"')
    change(featured, 'android:padding="12dp"\n        android:background="@drawable/dashboard_hero_arrow_bg"',
          'android:padding="8dp"\n        android:background="@drawable/dashboard_hero_arrow_bg"')
    # Radio Back: first Back stops the radio stream, subsequent Back exits to dashboard.
    radio="modules/radio/src/main/java/me/aap/fermata/addon/radio/RadioFragment.java"
    change(radio,
        "\t@Override\n\tpublic boolean isAddSourceSupported() {",
        "\t@Override\n\tpublic boolean onBackPressed() {\n"
        "\t\tif (getMainActivity().getMediaServiceBinder().isPlaying() &&\n"
        "\t\t\t\t(getMainActivity().getMediaServiceBinder().getCurrentItem() "
        "instanceof RadioPlayableItem)) {\n"
        "\t\t\tgetMainActivity().getMediaSessionCallback().onStop();\n"
        "\t\t\tgetAdapter().setParent(getRootItem());\n"
        "\t\t\treturn true;\n"
        "\t\t}\n\t\treturn super.onBackPressed();\n\t}\n\n"
        "\t@Override\n\tpublic boolean isAddSourceSupported() {")
    # Stamp station artwork into metadata; original m3u logo links are preserved.
    source="modules/radio/src/main/java/me/aap/fermata/addon/radio/RadioSourceItem.java"
    change(source, '\t\tmeta.putString(METADATA_KEY_ALBUM, "Internet Radio");',
        '\t\tmeta.putString(METADATA_KEY_ALBUM, "Internet Radio");\n'
        '\t\tString logo = molaLogoUri(current.getName());\n'
        '\t\tif (logo != null) meta.setImageUri(logo);')
    change(source,
        "\tprivate static String toId(RadioSource source) {",
        '\t/** Read tvg-logo from bundled 19-station playlist, without changing URLs. */\n'
        '\t@Nullable private static String molaLogoUri(String name) {\n'
        '\t\ttry (java.io.BufferedReader reader = new java.io.BufferedReader(\n'
        '\t\t\t\tnew java.io.InputStreamReader(me.aap.utils.app.App.get().getAssets().open("mola_radio.m3u"),\n'
        '\t\t\t\t\t\tjava.nio.charset.StandardCharsets.UTF_8))) {\n'
        '\t\t\tString line;\n'
        '\t\t\twhile ((line = reader.readLine()) != null) {\n'
        '\t\t\t\tif (!line.startsWith("#EXTINF:") || !line.endsWith("," + name)) continue;\n'
        '\t\t\t\tint pos = line.indexOf("tvg-logo=\\\"");\n'
        '\t\t\t\tif (pos < 0) return null;\n'
        '\t\t\t\tint start = pos + 10, end = line.indexOf(\'\\\"\', start);\n'
        '\t\t\t\treturn end > start ? line.substring(start, end) : null;\n'
        '\t\t\t}\n'
        '\t\t} catch (java.io.IOException ignored) { }\n'
        '\t\treturn null;\n'
        '\t}\n\n'
        '\tprivate static String toId(RadioSource source) {')
    print("Mola trial: 54 economical TV selections, 19 radios unchanged, four landing cards, Medya folder browser, compact cards, radio Back and station artwork metadata.")

if __name__ == "__main__":
    main()
