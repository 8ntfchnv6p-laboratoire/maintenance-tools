package ca.maison.naturehome;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Environment;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Fonds d'écran : photos poussées par tvtool.py, sinon paysages générés.
 * Emplacements lus, dans l'ordre :
 *   /sdcard/Android/data/ca.maison.naturehome/files/wallpapers  (aucune permission requise)
 *   /sdcard/Pictures/NatureHome                                  (permission accordée par adb)
 */
final class Wallpapers {
    private final Context ctx;
    private final List<File> files = new ArrayList<>();
    private int cursor = -1;

    Wallpapers(Context ctx) {
        this.ctx = ctx;
    }

    /** Relit les dossiers ; ordre aléatoire pour varier à chaque démarrage. */
    void rescan() {
        files.clear();
        File own = ctx.getExternalFilesDir("wallpapers");
        addImages(own);
        addImages(new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), "NatureHome"));
        Collections.shuffle(files);
        cursor = -1;
    }

    int photoCount() {
        return files.size();
    }

    private void addImages(File dir) {
        if (dir == null) return;
        File[] list;
        try {
            list = dir.listFiles();
        } catch (SecurityException e) {
            return;
        }
        if (list == null) return;
        for (File f : list) {
            String n = f.getName().toLowerCase(Locale.ROOT);
            if (f.isFile() && (n.endsWith(".jpg") || n.endsWith(".jpeg") || n.endsWith(".png") || n.endsWith(".webp"))) {
                files.add(f);
            }
        }
    }

    /** Image suivante, décodée à la taille de l'écran. Appelé hors du thread UI. */
    Bitmap next(int w, int h) {
        for (int attempt = 0; attempt < files.size(); attempt++) {
            cursor = (cursor + 1) % files.size();
            Bitmap b = decode(files.get(cursor), w, h);
            if (b != null) return b;
        }
        cursor++;
        // Générés en demi-résolution : les dégradés restent lisses une fois agrandis.
        return NatureArt.render(cursor, Math.max(640, w / 2), Math.max(360, h / 2), System.nanoTime());
    }

    private static Bitmap decode(File f, int w, int h) {
        BitmapFactory.Options o = new BitmapFactory.Options();
        o.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(f.getPath(), o);
        if (o.outWidth <= 0 || o.outHeight <= 0) return null;
        int sample = 1;
        while (o.outWidth / (sample * 2) >= w && o.outHeight / (sample * 2) >= h) sample *= 2;
        o.inJustDecodeBounds = false;
        o.inSampleSize = sample;
        o.inPreferredConfig = Bitmap.Config.ARGB_8888;
        try {
            return BitmapFactory.decodeFile(f.getPath(), o);
        } catch (OutOfMemoryError e) {
            return null;
        }
    }
}
