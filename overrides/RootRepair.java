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

        if (hasPlayInstaller(activity)) return;

        File status = new File(activity.getFilesDir(), STATUS);
        String result = read(status);
        if ("SUCCESS".equals(result)) {
            // The install shell completed, but the OS still reports another
            // installer. Do not silently retry in a loop.
            message(activity, "Kurulum kontrolü",
                    "Root ile yeniden kurulum tamamlandı; ancak Android henüz Play Store "
                    + "kaynağını doğrulamıyor. Android Auto'yu yeniden bağlayın ve "
                    + "Başlatıcıyı özelleştir bölümünü kontrol edin.");
            return;
        }

        final String heading = result.startsWith("FAIL:")
                ? "Android Auto onarımı yeniden dene" : "Android Auto kurulum onarımı";
        activity.getWindow().getDecorView().post(() -> {
            if (activity.isFinishing() || activity.isDestroyed()) return;
            new AlertDialog.Builder(activity)
                    .setTitle(heading)
                    .setMessage("Android Auto uygulama listesinde Mola görünmüyor olabilir. "
                            + "Orijinal Mola'nın yaptığı gibi mevcut uygulamanın aynı APK'sını "
                            + "root izniyle yeniden kurabiliriz. TV, radyo ve ayarlar korunur. "
                            + "Magisk'in root onayı istenir.\n\n"
                            + (result.startsWith("FAIL:") ? "Önceki deneme: "
                                + result.substring(5) + "\n\n" : "")
                            + "Onarım sırasında uygulama kapanıp yeniden açılabilir.")
                    .setPositiveButton("Root ile onar", (d, which) -> perform(activity))
                    .setNegativeButton("Şimdi değil", (d, which) -> { })
                    .show();
        });
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

        // All shell values are single-quote escaped. No playlist URLs or
        // IPTV account details are passed to a shell or written into logs.
        String commands =
                "#!/system/bin/sh\n"
                + "if [ \"$(id -u)\" != 0 ]; then echo 'FAIL:root denied' > "
                + q(status.getAbsolutePath()) + "; exit 31; fi\n"
                + "echo 'RUNNING' > " + q(status.getAbsolutePath()) + "\n"
                + "pm install -r -i " + VENDING + " " + q(source.getAbsolutePath())
                + " > " + q(log.getAbsolutePath()) + " 2>&1\n"
                + "code=$?\n"
                + "if [ \"$code\" -ne 0 ]; then\n"
                + "  echo \"FAIL:pm install exit $code\" > "
                + q(status.getAbsolutePath()) + "\n"
                + "  exit \"$code\"\n"
                + "fi\n"
                + "cmd package set-installer " + q(packageName) + " " + VENDING
                + " >> " + q(log.getAbsolutePath()) + " 2>&1 || true\n"
                + "echo 'SUCCESS' > " + q(status.getAbsolutePath()) + "\n"
                + "sleep 2\n"
                + "am start -n " + q(packageName + "/me.app.fermatax.auto.PhoneLauncherActivity")
                + " >> " + q(log.getAbsolutePath()) + " 2>&1\n";

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
            int result = -1;
            try {
                Process process = new ProcessBuilder("su", "-c", "sh " + q(script.getAbsolutePath()))
                        .redirectErrorStream(true).start();
                result = process.waitFor();
                Log.i(TAG, "Root installer exit: " + result);
            } catch (Exception e) {
                Log.e(TAG, "Root installer failed to start", e);
            }
            int code = result;
            activity.runOnUiThread(() -> {
                if (activity.isFinishing() || activity.isDestroyed()) return;
                String current = read(status);
                if (code == 0 && "SUCCESS".equals(current)) {
                    message(activity, "Onarım tamamlandı",
                            "Uygulama root üzerinden yeniden kuruldu. Android Auto'yu "
                            + "yeniden bağlayın ve Başlatıcıyı özelleştir bölümünü kontrol edin.");
                } else {
                    message(activity, "Onarım başarısız",
                            "Yeniden kurulum tamamlanamadı. Root iznini ve Android "
                            + "kurulum kısıtlamalarını kontrol edin. Hata: "
                            + (current.isEmpty() ? "root/kurulum işlemi, kod " + code : current));
                }
            });
        }, "Mola-Root-Reinstall").start();
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
