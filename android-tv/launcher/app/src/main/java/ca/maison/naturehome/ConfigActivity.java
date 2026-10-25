package ca.maison.naturehome;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;

/**
 * Point d'entrée de configuration pour tvtool.py (protégé par la permission DUMP,
 * donc lançable par « adb shell am start » mais pas par une autre appli) :
 *
 *   am start -n ca.maison.naturehome/.ConfigActivity --es dock "pkg1,pkg2" --ei interval 120 --ez next true
 */
public class ConfigActivity extends Activity {
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Intent in = getIntent();
        Prefs prefs = new Prefs(this);
        String dock = in.getStringExtra("dock");
        if (dock != null) prefs.setDock(dock);
        int interval = in.getIntExtra("interval", 0);
        if (interval > 0) prefs.setIntervalSeconds(interval);

        Intent home = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                .putExtra(MainActivity.EXTRA_NEXT_WALLPAPER, in.getBooleanExtra("next", false));
        startActivity(home);
        finish();
    }
}
