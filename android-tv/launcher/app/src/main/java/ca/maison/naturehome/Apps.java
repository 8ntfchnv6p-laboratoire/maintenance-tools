package ca.maison.naturehome;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.drawable.Drawable;

import java.text.Collator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Inventaire des applis lançables (TV d'abord, puis applis « mobiles »). */
final class Apps {

    static final class Entry {
        final String pkg;
        final ComponentName component;
        final String label;
        final boolean tv;
        private final ActivityInfo info;

        Entry(ActivityInfo info, String label, boolean tv) {
            this.info = info;
            this.pkg = info.packageName;
            this.component = new ComponentName(info.packageName, info.name);
            this.label = label;
            this.tv = tv;
        }

        /** Bannière 16:9 si l'appli en fournit une, sinon null. */
        Drawable banner(PackageManager pm) {
            Drawable d = info.loadBanner(pm);
            return d != null ? d : info.applicationInfo.loadBanner(pm);
        }

        Drawable icon(PackageManager pm) {
            return info.loadIcon(pm);
        }

        Intent launchIntent() {
            Intent i = new Intent(Intent.ACTION_MAIN);
            i.addCategory(tv ? Intent.CATEGORY_LEANBACK_LAUNCHER : Intent.CATEGORY_LAUNCHER);
            i.setComponent(component);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            return i;
        }
    }

    /** Une entrée par paquet, sans Nature Home lui-même, triée par libellé. */
    static List<Entry> load(Context c) {
        PackageManager pm = c.getPackageManager();
        Map<String, Entry> byPkg = new LinkedHashMap<>();
        collect(pm, Intent.CATEGORY_LEANBACK_LAUNCHER, true, byPkg);
        collect(pm, Intent.CATEGORY_LAUNCHER, false, byPkg);
        byPkg.remove(c.getPackageName());
        List<Entry> out = new ArrayList<>(byPkg.values());
        Collator col = Collator.getInstance();
        Collections.sort(out, (a, b) -> col.compare(a.label, b.label));
        return out;
    }

    private static void collect(PackageManager pm, String category, boolean tv, Map<String, Entry> out) {
        Intent q = new Intent(Intent.ACTION_MAIN).addCategory(category);
        for (ResolveInfo ri : pm.queryIntentActivities(q, 0)) {
            ActivityInfo ai = ri.activityInfo;
            if (ai == null || out.containsKey(ai.packageName)) continue;
            out.put(ai.packageName, new Entry(ai, String.valueOf(ri.loadLabel(pm)), tv));
        }
    }

    static Map<String, Entry> index(List<Entry> all) {
        Map<String, Entry> m = new LinkedHashMap<>();
        for (Entry e : all) m.put(e.pkg, e);
        return m;
    }
}
