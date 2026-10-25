package ca.maison.naturehome;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Outline;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.view.ViewOutlineProvider;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Tuiles 16:9 à coins arrondis, agrandies au focus (façon Apple TV). */
final class Tiles {
    static final float FOCUS_SCALE = 1.12f;

    static int dp(Context c, float v) {
        return Math.round(v * c.getResources().getDisplayMetrics().density);
    }

    /**
     * @param banner bannière plein cadre, ou null pour afficher {@code icon} centrée
     */
    static LinearLayout make(Context c, String label, Drawable banner, Drawable icon, int widthDp) {
        final int w = dp(c, widthDp), h = w * 9 / 16, radius = dp(c, 12);

        LinearLayout box = new LinearLayout(c);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        box.setFocusable(true);
        box.setClipChildren(false);
        box.setClipToPadding(false);

        FrameLayout card = new FrameLayout(c);
        GradientDrawable bg = new GradientDrawable();
        bg.setCornerRadius(radius);
        bg.setColor(0xCC2A2D34);
        card.setBackground(bg);
        card.setOutlineProvider(new ViewOutlineProvider() {
            @Override
            public void getOutline(View view, Outline outline) {
                outline.setRoundRect(0, 0, view.getWidth(), view.getHeight(), radius);
            }
        });
        card.setClipToOutline(true);
        card.setElevation(dp(c, 2));

        ImageView img = new ImageView(c);
        if (banner != null) {
            img.setScaleType(ImageView.ScaleType.CENTER_CROP);
            img.setImageDrawable(banner);
            card.addView(img, new FrameLayout.LayoutParams(w, h));
        } else {
            img.setScaleType(ImageView.ScaleType.FIT_CENTER);
            img.setImageDrawable(icon);
            int s = h * 55 / 100;
            card.addView(img, new FrameLayout.LayoutParams(s, s, Gravity.CENTER));
        }
        box.addView(card, new LinearLayout.LayoutParams(w, h));

        final TextView name = new TextView(c);
        name.setText(label);
        name.setTextColor(0xFFFFFFFF);
        name.setTextSize(15);
        name.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        name.setSingleLine(true);
        name.setEllipsize(TextUtils.TruncateAt.END);
        name.setGravity(Gravity.CENTER);
        name.setShadowLayer(6, 0, 1, 0xCC000000);
        name.setAlpha(0f);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(w, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(c, 14);
        box.addView(name, lp);

        final float lift = dp(c, 16);
        box.setOnFocusChangeListener((v, focused) -> {
            float sc = focused ? FOCUS_SCALE : 1f;
            card.animate().scaleX(sc).scaleY(sc).translationZ(focused ? lift : 0).setDuration(150).start();
            name.animate().alpha(focused ? 1f : 0f).setDuration(150).start();
        });
        return box;
    }

    /** Pictogramme « toutes les applis » : grille 3×3 de carrés arrondis. */
    static Drawable gridIcon() {
        return new Drawable() {
            private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
            private final RectF r = new RectF();

            @Override
            public void draw(Canvas canvas) {
                float size = Math.min(getBounds().width(), getBounds().height());
                float cell = size / 3f, gap = cell * 0.22f;
                float ox = getBounds().centerX() - size / 2, oy = getBounds().centerY() - size / 2;
                p.setColor(0xFFFFFFFF);
                for (int i = 0; i < 9; i++) {
                    float x = ox + (i % 3) * cell, y = oy + (i / 3) * cell;
                    r.set(x + gap, y + gap, x + cell - gap, y + cell - gap);
                    canvas.drawRoundRect(r, gap, gap, p);
                }
            }

            @Override public void setAlpha(int a) { p.setAlpha(a); }
            @Override public void setColorFilter(ColorFilter cf) { p.setColorFilter(cf); }
            @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }
            @Override public int getIntrinsicWidth() { return 96; }
            @Override public int getIntrinsicHeight() { return 96; }
        };
    }
}
