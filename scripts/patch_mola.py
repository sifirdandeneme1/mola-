#!/usr/bin/env python3
"""Patch the GPL Mola 2.2.2 sources inside GitHub Actions.

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
        '\t\t\t\tfs.toId(fs.newDefaultSource(TvSourceRepository.DEFAULT_RADIO_URL,\n'
        '\t\t\t\t\t\tgetLib().getContext().getString(R.string.default_turkish_radios)).getRid()));\n'
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
    insert_at(
        tv_root,
        '\t@Override\n\tprotected void itemAdded(TvSourceItem item) {',
        ''
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

    manager = "fermata/src/main/java/me/aap/fermata/media/engine/MediaEngineManager.java"
    replace(
        manager,
        'if (!prefs.hasPref(VIDEO_ENGINE) && isProviderAvailable(VLC_PROV_CLASS)) {\n'
        '\t\t\tprefs.setVideoEnginePref(MEDIA_ENG_VLC);\n'
        '\t\t}',
        'if (!prefs.hasPref(VIDEO_ENGINE) && isProviderAvailable(EXO_PROV_CLASS)) {\n'
        '\t\t\tprefs.setVideoEnginePref(MEDIA_ENG_EXO);\n'
        '\t\t}'
    )

    root_dir = UP / "fermata/src/main/java/me/aap/fermata/root"
    root_dir.mkdir(parents=True, exist_ok=True)
    (root_dir / "RootBootstrap.java").write_text(
        """package me.aap.fermata.root;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;

/** One-time, user-authorized su request on rooted personal devices. */
public final class RootBootstrap {
    private static final String TAG = "MolaRoot";
    private static final String PREF = "mola_root_bootstrap";
    private RootBootstrap() {}

    public static void requestOnce(Context context) {
        Context app = context.getApplicationContext();
        SharedPreferences prefs = app.getSharedPreferences(PREF, Context.MODE_PRIVATE);
        if (prefs.getBoolean("granted", false)) return;
        new Thread(() -> {
            try {
                Process process = new ProcessBuilder("su", "-c", "id")
                        .redirectErrorStream(true).start();
                int code = process.waitFor();
                if (code == 0) {
                    prefs.edit().putBoolean("granted", true).apply();
                    Log.i(TAG, "Root access granted");
                } else {
                    Log.w(TAG, "Root access not granted, code: " + code);
                }
            } catch (Exception e) {
                Log.w(TAG, "su not available or root denied", e);
            }
        }, "MolaRootBootstrap").start();
    }
}
""", encoding="utf-8"
    )
    activity = "fermata/src/main/java/me/aap/fermata/ui/activity/MainActivity.java"
    insert_at(
        activity,
        '\t\tPhoneConnectionObservation.observe(this, this);',
        '\n\t\tif (!isCarActivity()) me.aap.fermata.root.RootBootstrap.requestOnce(this);'
    )

    print("Mola personalization patched: 54 TV, 19 radio, Exo first, root request on first launch")


if __name__ == "__main__":
    main()
