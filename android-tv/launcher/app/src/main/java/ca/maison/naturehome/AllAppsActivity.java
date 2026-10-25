package ca.maison.naturehome;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.KeyEvent;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.List;

/** Grille de toutes les applis ; appui long (ou Menu) : ajouter/retirer du dock. */
public class AllAppsActivity extends Activity {
    private static final int COLUMNS = 5;
    private static final int TILE_DP = 156;

    private Prefs prefs;
    private LinearLayout grid;
    private String focusPkg;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = new Prefs(this);

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(0xF0101114);
        scroll.setClipChildren(false);
        scroll.setClipToPadding(false);
        scroll.setVerticalScrollBarEnabled(false);

        grid = new LinearLayout(this);
        grid.setOrientation(LinearLayout.VERTICAL);
        grid.setClipChildren(false);
        grid.setClipToPadding(false);
        int pad = Tiles.dp(this, 56);
        grid.setPadding(pad, Tiles.dp(this, 32), pad, pad);
        scroll.addView(grid);
        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        build();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_MENU) {
            View v = getCurrentFocus();
            if (v != null) return v.performLongClick();
        }
        return super.onKeyDown(keyCode, event);
    }

    private void build() {
        grid.removeAllViews();
        TextView title = new TextView(this);
        title.setText("Applications");
        title.setTextColor(0xFFFFFFFF);
        title.setTextSize(28);
        title.setPadding(0, 0, 0, Tiles.dp(this, 20));
        grid.addView(title);

        PackageManager pm = getPackageManager();
        List<String> dock = prefs.dock();
        if (dock == null) dock = new ArrayList<>();
        final List<String> current = dock;

        LinearLayout row = null;
        View toFocus = null;
        List<Apps.Entry> all = Apps.load(this);
        for (int i = 0; i < all.size(); i++) {
            if (i % COLUMNS == 0) {
                row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setClipChildren(false);
                row.setClipToPadding(false);
                LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
                rlp.bottomMargin = Tiles.dp(this, 8);
                grid.addView(row, rlp);
            }
            final Apps.Entry e = all.get(i);
            String label = current.contains(e.pkg) ? "★ " + e.label : e.label;
            View t = Tiles.make(this, label, e.banner(pm), e.icon(pm), TILE_DP);
            t.setOnClickListener(v -> {
                try {
                    startActivity(e.launchIntent());
                } catch (ActivityNotFoundException | SecurityException ex) {
                    Toast.makeText(this, "Impossible d'ouvrir cette appli", Toast.LENGTH_SHORT).show();
                }
            });
            t.setOnLongClickListener(v -> {
                menu(current, e);
                return true;
            });
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
            lp.rightMargin = Tiles.dp(this, 24);
            row.addView(t, lp);
            if (toFocus == null || e.pkg.equals(focusPkg)) toFocus = t;
        }
        if (toFocus != null) toFocus.requestFocus();
    }

    private void menu(List<String> dock, Apps.Entry e) {
        final boolean inDock = dock.contains(e.pkg);
        String[] items = {inDock ? "Retirer du dock" : "Ajouter au dock", "Infos sur l'appli"};
        new AlertDialog.Builder(this, android.R.style.Theme_Material_Dialog_Alert)
                .setTitle(e.label)
                .setItems(items, (d, which) -> {
                    if (which == 0) {
                        List<String> next = new ArrayList<>(dock);
                        if (inDock) next.remove(e.pkg); else next.add(e.pkg);
                        prefs.setDock(next);
                        focusPkg = e.pkg;
                        build();
                    } else {
                        startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                Uri.fromParts("package", e.pkg, null)));
                    }
                })
                .show();
    }
}
