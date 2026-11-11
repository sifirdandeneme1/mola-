package me.aap.fermata.root;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.InstallSourceInfo;
import android.os.Build;
import android.util.Log;
import android.widget.Toast;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/**
 * Root-only, user-confirmed Android Auto installation repair.
 *
 * The old implementation merely ran "su -c id". This one performs the missing
 * same-package install step and checks the result. It does not bypass Android
 * Auto's own settings or promise to make an unapproved application visible.
 */
public final class RootRepair {
    private static final String TAG = "MolaRootRepair";
    private static final String VENDING = "com.android.vending";
    private static final String STATUS = "mola_root_repair.status";
    private static final String LOG = "mola_root_repair.log";
    private static boolean prompted;

    private RootRepair() {}

    public static void offer(Activity activity) {
        if (prompted || activity.isFinishing() || activity.isDestroyed()) return;
        prompted = true;
        File status = new File(activity.getFilesDir(), STATUS);
        String result = read(status);
        String source = installSourceReport(activity);
        activity.getWindow().getDecorView().post(() -> {
            if (activity.isFinishing() || activity.isDestroyed()) return;
            String message = "Android Auto kurulum tanısı\n\n"
                    + source + "\n\n"
                    + "Son root işlemi: " + (result.isEmpty() ? "Henüz yok" : result)
                    + "\n\n"
                    + "Orijinal Mola'nın kurulum oturumuna benzeyen yöntemle "
                    + "APK'yı yeniden kurmayı denemek için aşağıya bas. "
                    + "Bu işlem dosyaları silmez, ancak uygulama kapanabilir.";
            new AlertDialog.Builder(activity)
                    .setTitle("Mola Android Auto onarımı")
                    .setMessage(message)
                    .setPositiveButton("Root oturumu ile onar", (dialog, ignored) -> perform(activity))
                    .setNegativeButton("Şimdi değil", (dialog, ignored) -> { })
                    .show();
        });
    }

    private static String installSourceReport(Activity activity) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                InstallSourceInfo info = activity.getPackageManager()
                        .getInstallSourceInfo(activity.getPackageName());
                return "Kurulum kaynağı: " + value(info.getInstallingPackageName())
                        + "\nBaşlatan paket: " + value(info.getInitiatingPackageName())
                        + "\nKaynak paket: " + value(info.getOriginatingPackageName());
            }
            return "Kurulum kaynağı: " + value(activity.getPackageManager()
                    .getInstallerPackageName(activity.getPackageName()));
        } catch (Exception e) {
            return "Kurulum kaynağı okunamadı: " + e.getClass().getSimpleName();
        }
    }

    private static String value(String input) {
        return (input == null || input.isEmpty()) ? "(belirtilmemiş)" : input;
    }

    private static boolean hasPlayInstaller(Activity activity) {
        try {
            String installer;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                InstallSourceInfo info = activity.getPackageManager()
                        .getInstallSourceInfo(activity.getPackageName());
                installer = info.getInstallingPackageName();
            } else {
                installer = activity.getPackageManager()
                        .getInstallerPackageName(activity.getPackageName());
            }
            Log.i(TAG, "Reported installing package: " + installer);
            return VENDING.equals(installer);
        } catch (Exception e) {
            Log.w(TAG, "Could not query Android installation source", e);
            return false;
        }
    }

    private static void perform(Activity activity) {
        File source = new File(activity.getApplicationInfo().sourceDir);
        if (!source.isFile()) {
            message(activity, "Onarım hatası", "Yüklü APK dosyasına ulaşılamadı.");
            return;
        }

        File files = activity.getFilesDir();
        File status = new File(files, STATUS);
        File log = new File(files, LOG);
        File script = new File(files, "mola_root_repair.sh");
        String packageName = activity.getPackageName();

        // Build the original app's session-based installer sequence. Never log
        // the embedded IPTV playlist or use any playlist value as shell input.
        String commands = "#!/system/bin/sh\n"
                + "apk=" + q(source.getAbsolutePath()) + "\n"
                + "status=" + q(status.getAbsolutePath()) + "\n"
                + "log=" + q(log.getAbsolutePath()) + "\n"
                + "pkg=" + q(packageName) + "\n"
                + "vending=com.android.vending\n"
                + "echo RUNNING > \"$status\"\n"
                + "if [ \"$(id -u)\" != 0 ]; then echo FAIL:root-not-granted > \"$status\"; exit 1; fi\n"
                + "size=$(stat -c %s \"$apk\")\n"
                + "if [ -z \"$size\" ]; then echo FAIL:cannot-read-apk > \"$status\"; exit 1; fi\n"
                + "session_info=$(pm install-create -r -i \"$vending\" -S \"$size\" "
                + " --initiating-package \"$vending\" "
                + " --originating-uri 'android-app://com.android.vending' "
                + " --referrer 'android-app://com.android.vending' --install-reason 4 2>&1)\n"
                + "echo \"$session_info\" > \"$log\"\n"
                + "session=$(printf '%s\\\n' \"$session_info\" | sed -n 's/.*\\\\[\\\\([0-9][0-9]*\\\\)\\\\].*/\\\\1/p')\n"
                + "if [ -z \"$session\" ]; then echo FAIL:session-create > \"$status\"; exit 1; fi\n"
                + "pm install-write -S \"$size\" \"$session\" base.apk \"$apk\" >> \"$log\" 2>&1\n"
                + "if [ $? -ne 0 ]; then pm install-abandon \"$session\"; echo FAIL:session-write > \"$status\"; exit 1; fi\n"
                + "pm install-commit \"$session\" >> \"$log\" 2>&1\n"
                + "if [ $? -ne 0 ]; then echo FAIL:session-commit > \"$status\"; exit 1; fi\n"
                + "cmd package set-installer \"$pkg\" \"$vending\" >> \"$log\" 2>&1 || true\n"
                + "echo SUCCESS > \"$status\"\n"
                + "sleep 2\n"
                + "am start -n \"$pkg/me.app.fermatax.auto.PhoneLauncherActivity\" >> \"$log\" 2>&1\n";

        try {
            Files.write(script.toPath(), commands.getBytes(StandardCharsets.UTF_8));
            Files.deleteIfExists(status.toPath());
        } catch (Exception e) {
            Log.e(TAG, "Failed preparing root repair script", e);
            message(activity, "Onarım hatası", "Root onarım dosyası hazırlanamadı.");
            return;
        }

        Toast.makeText(activity, "Magisk root iznini onaylayın.", Toast.LENGTH_LONG).show();
        new Thread(() -> {
            try {
                // Reinstallation can kill our own Android process. The root
                // script must continue detached from this app process.
                String command = "sh " + q(script.getAbsolutePath())
                        + " </dev/null >/dev/null 2>&1 &";
                Process process = new ProcessBuilder("su", "-c", command)
                        .redirectErrorStream(true).start();
                int result = process.waitFor();
                Log.i(TAG, "Detached root installer launched: " + result);
                if (result != 0) {
                    activity.runOnUiThread(() -> message(activity, "Onarım başlatılamadı",
                            "Magisk root işlemi başlatılamadı. Çıkış kodu: " + result));
                }
            } catch (Exception e) {
                Log.e(TAG, "Root installer failed to start", e);
                activity.runOnUiThread(() -> message(activity, "Onarım başlatılamadı",
                        "Magisk root iznini ve komut çalıştırmayı kontrol et."));
            }
        }, "Mola-Root-Session-Installer").start();
    }

    private static String q(String value) {
        return "'" + value.replace("'", "'\\''") + "'";
    }

    private static String read(File file) {
        try {
            if (!file.isFile()) return "";
            String value = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8).trim();
            return value.length() <= 120 ? value : value.substring(0, 120);
        } catch (Exception e) {
            return "";
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
