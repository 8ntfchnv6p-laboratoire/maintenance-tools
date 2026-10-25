package ca.maison.naturehome;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Point;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.format.DateFormat;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.animation.LinearInterpolator;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Écran d'accueil : fond nature en fondu, horloge, dock d'applis favorites. */
public class MainActivity extends Activity {
    static final String EXTRA_NEXT_WALLPAPER = "next_wallpaper";
    private static final int TILE_DP = 196;
    private static final long FADE_MS = 1500;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();

    private Prefs prefs;
    private Wallpapers walls;
    private ImageView bgLower, bgUpper;
    private boolean upperShown;
    private boolean hasWallpaper;
    private TextView clock, date;
    private LinearLayout dockRow;
    private HorizontalScrollView dockScroll;
    private int screenW, screenH;
    private int focusIndex;

    private final Runnable rotate = new Runnable() {
        @Override
        public void run() {
            loadNextWallpaper();
            ui.postDelayed(this, prefs.intervalSeconds() * 1000L);
        }
    };

    private final BroadcastReceiver timeReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            updateClock();
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = new Prefs(this);
        walls = new Wallpapers(this);

        Point size = new Point();
        getWindowManager().getDefaultDisplay().getRealSize(size);
        screenW = Math.max(size.x, size.y);
        screenH = Math.min(size.x, size.y);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(0xFF000000);
        root.setClipChildren(false);

        bgLower = newBackground();
        bgUpper = newBackground();
        bgUpper.setAlpha(0f);
        root.addView(bgLower, matchParent());
        root.addView(bgUpper, matchParent());

        // Voile sombre en bas (lisibilité du dock) et léger en haut (horloge).
        View scrim = new View(this);
        scrim.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{0x66000000, 0x00000000, 0x00000000, 0xB3000000}));
        root.addView(scrim, matchParent());

        LinearLayout clockBox = new LinearLayout(this);
        clockBox.setOrientation(LinearLayout.VERTICAL);
        clockBox.setGravity(Gravity.END);
        clock = text(52, "sans-serif-light");
        date = text(18, "sans-serif");
        date.setAlpha(0.85f);
        clockBox.addView(clock);
        clockBox.addView(date);
        FrameLayout.LayoutParams clp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.TOP | Gravity.END);
        clp.setMargins(0, Tiles.dp(this, 36), Tiles.dp(this, 56), 0);
        root.addView(clockBox, clp);

        dockScroll = new HorizontalScrollView(this);
        dockScroll.setHorizontalScrollBarEnabled(false);
        dockScroll.setClipChildren(false);
        dockScroll.setClipToPadding(false);
        dockScroll.setFillViewport(false);
        dockRow = new LinearLayout(this);
        dockRow.setOrientation(LinearLayout.HORIZONTAL);
        dockRow.setClipChildren(false);
        dockRow.setClipToPadding(false);
        int pad = Tiles.dp(this, 56);
        dockRow.setPadding(pad, Tiles.dp(this, 24), pad, Tiles.dp(this, 8));
        dockScroll.addView(dockRow);
        FrameLayout.LayoutParams dlp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        dlp.bottomMargin = Tiles.dp(this, 40);
        root.addView(dockScroll, dlp);

        setContentView(root);
    }

    private ImageView newBackground() {
        ImageView v = new ImageView(this);
        v.setScaleType(ImageView.ScaleType.CENTER_CROP);
        return v;
    }

    private static FrameLayout.LayoutParams matchParent() {
        return new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT);
    }

    private TextView text(float sp, String family) {
        TextView t = new TextView(this);
        t.setTextColor(0xFFFFFFFF);
        t.setTextSize(sp);
        t.setTypeface(Typeface.create(family, Typeface.NORMAL));
        t.setShadowLayer(8, 0, 2, 0x99000000);
        return t;
    }

    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter f = new IntentFilter(Intent.ACTION_TIME_TICK);
        f.addAction(Intent.ACTION_TIME_CHANGED);
        f.addAction(Intent.ACTION_TIMEZONE_CHANGED);
        registerReceiver(timeReceiver, f);
        updateClock();
        rebuildDock();

        int before = walls.photoCount();
        walls.rescan();
        ui.removeCallbacks(rotate);
        if (!hasWallpaper || before != walls.photoCount()) {
            ui.post(rotate);
        } else {
            ui.postDelayed(rotate, prefs.intervalSeconds() * 1000L);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(timeReceiver);
        ui.removeCallbacks(rotate);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        worker.shutdownNow();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (intent.getBooleanExtra(EXTRA_NEXT_WALLPAPER, false)) {
            ui.removeCallbacks(rotate);
            ui.post(rotate);
        } else {
            // Touche Accueil alors qu'on y est déjà : retour au début du dock.
            focusIndex = 0;
            dockScroll.smoothScrollTo(0, 0);
            if (dockRow.getChildCount() > 0) dockRow.getChildAt(0).requestFocus();
        }
    }

    @Override
    public void onBackPressed() {
        // Écran d'accueil : Retour ne ferme rien.
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_MENU) {
            View v = getCurrentFocus();
            if (v != null) return v.performLongClick();
        }
        return super.onKeyDown(keyCode, event);
    }

    private void updateClock() {
        Date now = new Date();
        clock.setText(DateFormat.getTimeFormat(this).format(now));
        String d = new SimpleDateFormat("EEEE d MMMM", Locale.getDefault()).format(now);
        date.setText(d.isEmpty() ? d : Character.toUpperCase(d.charAt(0)) + d.substring(1));
    }

    // ---------- Fonds d'écran ----------

    private void loadNextWallpaper() {
        worker.execute(() -> {
            Bitmap b = walls.next(screenW, screenH);
            if (b != null) ui.post(() -> showWallpaper(b));
        });
    }

    private void showWallpaper(Bitmap b) {
        if (!hasWallpaper) {
            // Première image : affichage immédiat, sans fondu.
            hasWallpaper = true;
            upperShown = false;
            bgLower.setImageBitmap(b);
            slowZoom(bgLower);
            return;
        }
        final ImageView incoming = upperShown ? bgLower : bgUpper;
        final ImageView outgoing = upperShown ? bgUpper : bgLower;
        incoming.setImageBitmap(b);
        slowZoom(incoming);
        // bgUpper est au-dessus : on le fait apparaître ou disparaître selon le sens.
        float target = upperShown ? 0f : 1f;
        bgUpper.animate().alpha(target).setDuration(FADE_MS).withEndAction(() -> {
            outgoing.animate().cancel();
            outgoing.setImageDrawable(null);
        }).start();
        upperShown = !upperShown;
    }

    /** Léger zoom lent (effet « Ken Burns ») pendant l'affichage. */
    private void slowZoom(ImageView v) {
        v.animate().cancel();
        v.setScaleX(1f);
        v.setScaleY(1f);
        v.animate().scaleX(1.06f).scaleY(1.06f)
                .setDuration(prefs.intervalSeconds() * 1000L + FADE_MS)
                .setInterpolator(new LinearInterpolator()).start();
    }

    // ---------- Dock ----------

    private void rebuildDock() {
        View focused = getCurrentFocus();
        if (focused != null && focused.getParent() == dockRow) focusIndex = dockRow.indexOfChild(focused);

        List<Apps.Entry> all = Apps.load(this);
        Map<String, Apps.Entry> idx = Apps.index(all);
        List<String> dock = prefs.dock();
        if (dock == null) {
            dock = new ArrayList<>();
            for (String p : Prefs.DEFAULT_DOCK) if (idx.containsKey(p)) dock.add(p);
            for (Apps.Entry e : all) {
                if (dock.size() >= 6) break;
                if (e.tv && !dock.contains(e.pkg)) dock.add(e.pkg);
            }
            prefs.setDock(dock);
        }

        dockRow.removeAllViews();
        PackageManager pm = getPackageManager();
        final List<String> current = dock;
        for (String pkg : dock) {
            final Apps.Entry e = idx.get(pkg);
            if (e == null) continue; // désinstallée ou désactivée : on la garde en réserve
            View t = Tiles.make(this, e.label, e.banner(pm), e.icon(pm), TILE_DP);
            t.setOnClickListener(v -> launch(e.launchIntent()));
            t.setOnLongClickListener(v -> {
                dockMenu(current, e);
                return true;
            });
            addTile(t);
        }

        View allApps = Tiles.make(this, "Toutes les applis", null, Tiles.gridIcon(), TILE_DP);
        allApps.setOnClickListener(v -> startActivity(new Intent(this, AllAppsActivity.class)));
        addTile(allApps);

        Intent settings = new Intent(Settings.ACTION_SETTINGS);
        Drawable gear;
        try {
            gear = pm.getActivityIcon(settings);
        } catch (PackageManager.NameNotFoundException ex) {
            gear = getDrawable(android.R.drawable.ic_menu_preferences);
        }
        View st = Tiles.make(this, "Réglages", null, gear, TILE_DP);
        st.setOnClickListener(v -> launch(settings.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)));
        addTile(st);

        int i = Math.min(focusIndex, dockRow.getChildCount() - 1);
        if (i >= 0) dockRow.getChildAt(i).requestFocus();
    }

    private void addTile(View t) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.rightMargin = Tiles.dp(this, 28);
        dockRow.addView(t, lp);
    }

    private void dockMenu(List<String> dock, Apps.Entry e) {
        final int pos = dock.indexOf(e.pkg);
        String[] items = {"Déplacer à gauche", "Déplacer à droite", "Retirer du dock", "Infos sur l'appli"};
        new AlertDialog.Builder(this, android.R.style.Theme_Material_Dialog_Alert)
                .setTitle(e.label)
                .setItems(items, (d, which) -> {
                    List<String> next = new ArrayList<>(dock);
                    switch (which) {
                        case 0:
                            if (pos > 0) { next.remove(pos); next.add(pos - 1, e.pkg); focusIndex = pos - 1; }
                            break;
                        case 1:
                            if (pos >= 0 && pos < next.size() - 1) { next.remove(pos); next.add(pos + 1, e.pkg); focusIndex = pos + 1; }
                            break;
                        case 2:
                            next.remove(e.pkg);
                            break;
                        case 3:
                            launch(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                    Uri.fromParts("package", e.pkg, null)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                            return;
                    }
                    prefs.setDock(next);
                    rebuildDock();
                })
                .show();
    }

    private void launch(Intent i) {
        try {
            startActivity(i);
        } catch (ActivityNotFoundException | SecurityException ex) {
            Toast.makeText(this, "Impossible d'ouvrir cette appli", Toast.LENGTH_SHORT).show();
        }
    }
}
