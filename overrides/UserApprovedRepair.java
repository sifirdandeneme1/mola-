package me.aap.fermata.root;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.ProgressDialog;
import android.content.ClipData;
import android.content.Intent;
import android.content.pm.InstallSourceInfo;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;

import androidx.core.content.FileProvider;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.util.Arrays;

/**
 * User-confirmed Android Package Installer flow, instead of an unverified
 * detached "pm install-create" command. Retains the package name and signing
 * identity: it copies the very APK already installed on the device and asks
 * the Android Package Installer to update it with the user's approval.
 *
 * Does NOT claim Play Store provenance or bypass Android Auto restrictions.
 */
public final class UserApprovedRepair {
    private static final String TAG = "MolaUserRepair";
    private static final String PREFS = "mola_user_repair";
    private static final String KEY_STARTED = "user_approved_update_started";
    private static boolean shown;
    private static boolean permissionReturn;

    private UserApprovedRepair() {}

    public static void offer(Activity activity) {
        if (activity.isFinishing() || activity.isDestroyed()) return;
        if (permissionReturn) {
            permissionReturn = false;
            if (canInstall(activity)) {
                copyAndOpenInstaller(activity);
            } else {
                message(activity, "Kurulum izni eksik",
                        "Bu kaynaktan yükleme izni verilmedi. İstersen uygulamayı "
                        + "yeniden açıp onarımı tekrar başlatabilirsin.");
            }
            return;
        }
        if (shown) return;
        shown = true;

        boolean started = activity.getSharedPreferences(PREFS, Activity.MODE_PRIVATE)
                .getBoolean(KEY_STARTED, false);
        // Opening the installer is NOT proof the installation succeeded.
        // Avoid asking the user to reinstall again on every application launch.
        // This diagnostic build tests the corrected Android Auto media manifest.
        if (started) return;
        String source = installSourceReport(activity);
        String body = started
                ? "Önceki denemede Android'in güncelleme ekranı açıldı.\n\n"
                    + "Mevcut kaynak:\n" + source + "\n\n"
                    + "Android Auto'nun Başlatıcıyı özelleştir bölümünde Mola'yı "
                    + "kontrol edebilirsin. Tekrar güncelleme yapmak ister misin?"
                : "Android Auto'da görünmeyen bu uygulamayı orijinal Mola gibi "
                    + "Android'in kendi yükleme ekranıyla güncellemeyi deneyeceğiz.\n\n"
                    + "Kaynak:\n" + source + "\n\n"
                    + "Açılan sistem ekranında 'Güncelle'ye sen basacaksın. "
                    + "Root komutu kullanılmaz. Dosyaların ve kanal ayarların korunur.";

        activity.getWindow().getDecorView().post(() -> {
            if (activity.isFinishing() || activity.isDestroyed()) return;
            new AlertDialog.Builder(activity)
                    .setTitle("Mola Android Auto onarımı")
                    .setMessage(body)
                    .setPositiveButton("Onarımı başlat", (dialog, which) -> start(activity))
                    .setNegativeButton("Şimdi değil", (dialog, which) -> { })
                    .show();
        });
    }

    private static String installSourceReport(Activity activity) {
        try {
            PackageManager pm = activity.getPackageManager();
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                InstallSourceInfo source = pm.getInstallSourceInfo(activity.getPackageName());
                return "Yükleyen: " + readable(source.getInstallingPackageName())
                        + "\nBaşlatan: " + readable(source.getInitiatingPackageName())
                        + "\nKaynak: " + readable(source.getOriginatingPackageName());
            }
            return "Yükleyen: " + readable(pm.getInstallerPackageName(activity.getPackageName()));
        } catch (Exception e) {
            return "Kurulum kaynağı okunamıyor: " + e.getClass().getSimpleName();
        }
    }

    private static String readable(String value) {
        return (value == null || value.isEmpty()) ? "(belirtilmemiş)" : value;
    }

    private static boolean canInstall(Activity activity) {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.O
                || activity.getPackageManager().canRequestPackageInstalls();
    }

    private static void start(Activity activity) {
        if (!canInstall(activity)) {
            permissionReturn = true;
            try {
                Intent settings = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:" + activity.getPackageName()));
                activity.startActivity(settings);
            } catch (Exception error) {
                permissionReturn = false;
                Log.e(TAG, "Cannot open unknown app sources settings", error);
                message(activity, "Kurulum izni", "Bilinmeyen uygulama yükleme ayarları açılamadı.");
            }
            return;
        }
        copyAndOpenInstaller(activity);
    }

    private static void copyAndOpenInstaller(Activity activity) {
        File installed = new File(activity.getApplicationInfo().sourceDir);
        if (!installed.isFile()) {
            message(activity, "APK bulunamadı", "Yüklü uygulamanın APK dosyası okunamıyor.");
            return;
        }
        ProgressDialog progress = new ProgressDialog(activity);
        progress.setTitle("Onarım hazırlanıyor");
        progress.setMessage("Mevcut APK sistem yükleyicisine hazırlanıyor.");
        progress.setIndeterminate(true);
        progress.setCancelable(false);
        progress.show();

        new Thread(() -> {
            File copy = new File(new File(activity.getCacheDir(), "updates"), "mola-repair.apk");
            String error = null;
            try {
                File parent = copy.getParentFile();
                if (parent == null || (!parent.isDirectory() && !parent.mkdirs())) {
                    throw new IOException("APK önbelleği oluşturulamadı");
                }
                copyAndVerify(installed, copy);
            } catch (Exception ex) {
                error = ex.getMessage();
                Log.e(TAG, "Could not prepare original APK for system installer", ex);
            }
            final String problem = error;
            activity.runOnUiThread(() -> {
                progress.dismiss();
                if (activity.isFinishing() || activity.isDestroyed()) return;
                if (problem != null) {
                    message(activity, "Onarım hazırlanamadı",
                            "APK kopyalanamadı veya doğrulanamadı: " + problem);
                    return;
                }
                openInstaller(activity, copy);
            });
        }, "Mola-PackageInstaller-Copy").start();
    }

    private static void copyAndVerify(File source, File dest) throws Exception {
        MessageDigest originalDigest = MessageDigest.getInstance("SHA-256");
        long bytes = 0;
        try (FileInputStream input = new FileInputStream(source);
             FileOutputStream output = new FileOutputStream(dest)) {
            byte[] buffer = new byte[1024 * 256];
            int n;
            while ((n = input.read(buffer)) != -1) {
                output.write(buffer, 0, n);
                originalDigest.update(buffer, 0, n);
                bytes += n;
            }
            output.getFD().sync();
        }
        if (bytes != source.length() || bytes != dest.length()) {
            throw new IOException("APK boyutu eşleşmiyor");
        }
        MessageDigest copyDigest = MessageDigest.getInstance("SHA-256");
        try (FileInputStream input = new FileInputStream(dest)) {
            byte[] buffer = new byte[1024 * 256];
            int n;
            while ((n = input.read(buffer)) != -1) copyDigest.update(buffer, 0, n);
        }
        if (!Arrays.equals(originalDigest.digest(), copyDigest.digest())) {
            throw new IOException("APK SHA-256 eşleşmiyor");
        }
    }

    private static void openInstaller(Activity activity, File apk) {
        try {
            Uri uri = FileProvider.getUriForFile(activity,
                    activity.getPackageName() + ".UpdateFileProvider", apk);
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, "application/vnd.android.package-archive");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            intent.setClipData(ClipData.newUri(activity.getContentResolver(), "Mola APK", uri));
            activity.getSharedPreferences(PREFS, Activity.MODE_PRIVATE).edit()
                    .putBoolean(KEY_STARTED, true).apply();
            activity.startActivity(intent);
        } catch (Exception e) {
            Log.e(TAG, "Android package installer could not be opened", e);
            message(activity, "Kurulum ekranı açılamadı",
                    "Android'in Güncelle ekranı açılmadı: "
                    + e.getClass().getSimpleName() + ". " + e.getMessage());
        }
    }

    private static void message(Activity activity, String title, String body) {
        activity.getWindow().getDecorView().post(() -> {
            if (activity.isFinishing() || activity.isDestroyed()) return;
            new AlertDialog.Builder(activity).setTitle(title).setMessage(body)
                    .setPositiveButton("Tamam", null).show();
        });
    }
}
