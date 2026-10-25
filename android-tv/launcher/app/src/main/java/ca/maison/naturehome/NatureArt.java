package ca.maison.naturehome;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.Shader;

import java.util.Random;

/**
 * Paysages générés localement : utilisés quand aucune photo n'a été poussée
 * sur la télé, pour que l'accueil ne soit jamais vide (aucun réseau requis).
 */
final class NatureArt {

    private static final class Scene {
        final int skyTop, skyBottom, sun, haze;
        final int[] ridges; // du plus lointain au plus proche
        final boolean stars, aurora, lake;
        final float sunX, sunY;

        Scene(int skyTop, int skyBottom, int sun, int haze, int[] ridges,
              boolean stars, boolean aurora, boolean lake, float sunX, float sunY) {
            this.skyTop = skyTop; this.skyBottom = skyBottom; this.sun = sun; this.haze = haze;
            this.ridges = ridges; this.stars = stars; this.aurora = aurora; this.lake = lake;
            this.sunX = sunX; this.sunY = sunY;
        }
    }

    private static final Scene[] SCENES = {
            // Aube alpine
            new Scene(0xFF2B3A67, 0xFFF4B183, 0xFFFFE2A8, 0x66FFD1A0,
                    new int[]{0xFF7A6F9B, 0xFF544D7A, 0xFF35335A, 0xFF1F1F3A}, false, false, true, 0.72f, 0.58f),
            // Forêt boréale, brume
            new Scene(0xFF9CC3C9, 0xFFE6EEE4, 0xFFFFFBEA, 0x55FFFFFF,
                    new int[]{0xFF8FB0A4, 0xFF5E8A78, 0xFF355E4E, 0xFF1C3A2F}, false, false, false, 0.30f, 0.30f),
            // Aurore boréale
            new Scene(0xFF050B1F, 0xFF0F2C40, 0xFFDDE8FF, 0x2238F2C0,
                    new int[]{0xFF1A3346, 0xFF122636, 0xFF0B1A26, 0xFF050E16}, true, true, true, 0.82f, 0.18f),
            // Crépuscule désertique
            new Scene(0xFF3D2C5C, 0xFFF08A5D, 0xFFFFD27A, 0x55F7A26B,
                    new int[]{0xFFB45A57, 0xFF8A3F4B, 0xFF5E2A3F, 0xFF34182B}, false, false, false, 0.50f, 0.62f),
            // Lac glaciaire, midi
            new Scene(0xFF3E7CB1, 0xFFBFE3F2, 0xFFFFFFFF, 0x44FFFFFF,
                    new int[]{0xFFA9C6D8, 0xFF6F98B3, 0xFF3F6A86, 0xFF22445C}, false, false, true, 0.20f, 0.22f),
    };

    static int count() {
        return SCENES.length;
    }

    /** Rendu en basse résolution (lissé ensuite par l'ImageView) pour rester rapide. */
    static Bitmap render(int index, int width, int height, long seed) {
        Scene s = SCENES[((index % SCENES.length) + SCENES.length) % SCENES.length];
        Bitmap bmp = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(bmp);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        Random rnd = new Random(seed);
        float horizon = s.lake ? height * 0.70f : height;

        p.setShader(new LinearGradient(0, 0, 0, horizon, s.skyTop, s.skyBottom, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, width, horizon, p);
        p.setShader(null);

        if (s.stars) {
            p.setColor(0xFFFFFFFF);
            for (int i = 0; i < width / 6; i++) {
                p.setAlpha(60 + rnd.nextInt(180));
                c.drawCircle(rnd.nextFloat() * width, rnd.nextFloat() * horizon * 0.7f,
                        0.4f + rnd.nextFloat() * 1.1f, p);
            }
            p.setAlpha(255);
        }

        if (s.aurora) {
            for (int band = 0; band < 3; band++) {
                Path path = new Path();
                float base = height * (0.18f + band * 0.07f);
                float amp = height * 0.05f, ph = rnd.nextFloat() * 6.28f;
                path.moveTo(0, base);
                for (int x = 0; x <= width; x += 8) {
                    path.lineTo(x, base + (float) Math.sin(x * 0.006f + ph) * amp);
                }
                for (int x = width; x >= 0; x -= 8) {
                    path.lineTo(x, base + height * 0.16f + (float) Math.sin(x * 0.004f + ph) * amp);
                }
                path.close();
                p.setShader(new LinearGradient(0, base, 0, base + height * 0.2f,
                        band == 1 ? 0x5566E0FF : 0x5538F2A0, 0x0038F2A0, Shader.TileMode.CLAMP));
                c.drawPath(path, p);
            }
            p.setShader(null);
        }

        float sx = s.sunX * width, sy = s.sunY * height, sr = height * 0.06f;
        p.setShader(new RadialGradient(sx, sy, sr * 6, s.haze, 0x00FFFFFF, Shader.TileMode.CLAMP));
        c.drawCircle(sx, sy, sr * 6, p);
        p.setShader(null);
        p.setColor(s.sun);
        c.drawCircle(sx, sy, sr, p);

        int n = s.ridges.length;
        for (int i = 0; i < n; i++) {
            float t = (float) i / (n - 1);
            float base = horizon * (0.52f + 0.13f * t) + (s.lake ? 0 : height * 0.12f * t);
            float amp = height * (0.16f - 0.07f * t);
            float f1 = 0.0025f + rnd.nextFloat() * 0.002f, f2 = f1 * 2.7f, f3 = f1 * 7.3f;
            float p1 = rnd.nextFloat() * 6.28f, p2 = rnd.nextFloat() * 6.28f, p3 = rnd.nextFloat() * 6.28f;
            Path ridge = new Path();
            ridge.moveTo(0, horizon);
            for (int x = 0; x <= width; x += 4) {
                double y = Math.sin(x * f1 + p1) * 0.6 + Math.sin(x * f2 + p2) * 0.3 + Math.sin(x * f3 + p3) * 0.1;
                ridge.lineTo(x, (float) (base - amp * (0.5 + 0.5 * y)));
            }
            ridge.lineTo(width, horizon);
            ridge.close();
            p.setColor(s.ridges[i]);
            c.drawPath(ridge, p);
        }

        if (s.lake) {
            // Reflet : copie miroir assombrie du ciel et des crêtes sous l'horizon.
            int h = (int) horizon, reflectH = height - h;
            Bitmap top = Bitmap.createBitmap(bmp, 0, Math.max(0, h - reflectH), width, reflectH);
            c.save();
            c.scale(1, -1, 0, h + reflectH / 2f);
            c.drawBitmap(top, 0, h, null);
            c.restore();
            top.recycle();
            p.setShader(new LinearGradient(0, h, 0, height, 0x66000814, 0xCC000814, Shader.TileMode.CLAMP));
            c.drawRect(0, h, width, height, p);
            p.setShader(null);
            p.setColor(0x22FFFFFF);
            for (int i = 0; i < 40; i++) {
                float y = h + rnd.nextFloat() * reflectH, x = rnd.nextFloat() * width;
                c.drawRect(x, y, x + 20 + rnd.nextFloat() * 120, y + 1.2f, p);
            }
        }
        return bmp;
    }
}
