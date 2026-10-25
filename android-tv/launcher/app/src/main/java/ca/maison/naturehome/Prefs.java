package ca.maison.naturehome;

import android.content.Context;
import android.content.SharedPreferences;
import android.text.TextUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Réglages persistants : dock (liste ordonnée de paquets) et intervalle de rotation. */
final class Prefs {
    private static final String FILE = "naturehome";
    private static final String KEY_DOCK = "dock";
    private static final String KEY_INTERVAL = "interval_s";
    static final int DEFAULT_INTERVAL_S = 90;

    /** Dock initial si l'utilisateur n'a rien choisi : premiers présents de cette liste. */
    static final String[] DEFAULT_DOCK = {
            "com.google.android.youtube.tv",
            "com.netflix.ninja",
            "com.amazon.amazonvideo.livingroom",
            "com.disney.disneyplus",
            "com.plexapp.android",
            "com.spotify.tv.android",
    };

    private final SharedPreferences sp;

    Prefs(Context c) {
        sp = c.getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    /** null = jamais configuré. */
    List<String> dock() {
        String raw = sp.getString(KEY_DOCK, null);
        if (raw == null) return null;
        List<String> out = new ArrayList<>();
        for (String p : raw.split(",")) {
            p = p.trim();
            if (!p.isEmpty() && !out.contains(p)) out.add(p);
        }
        return out;
    }

    void setDock(List<String> pkgs) {
        sp.edit().putString(KEY_DOCK, TextUtils.join(",", pkgs)).apply();
    }

    void setDock(String csv) {
        setDock(new ArrayList<>(Arrays.asList(csv.split(","))));
    }

    int intervalSeconds() {
        return Math.max(15, sp.getInt(KEY_INTERVAL, DEFAULT_INTERVAL_S));
    }

    void setIntervalSeconds(int s) {
        sp.edit().putInt(KEY_INTERVAL, s).apply();
    }
}
