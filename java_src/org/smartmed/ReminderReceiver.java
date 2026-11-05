package org.smartmed;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import org.json.JSONObject;

import java.util.Calendar;
import java.util.Map;

public class ReminderReceiver extends BroadcastReceiver {
    private static final String CHANNEL_ID = "medication_reminders";
    private static final String PREFS = "smartmed_reminders";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();

        // Phone rebooted, app updated, or clock/timezone changed: re-arm everything.
        if (Intent.ACTION_BOOT_COMPLETED.equals(action)
                || Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)
                || Intent.ACTION_TIME_CHANGED.equals(action)
                || Intent.ACTION_TIMEZONE_CHANGED.equals(action)
                || "android.app.action.SCHEDULE_EXACT_ALARM_PERMISSION_STATE_CHANGED"
                       .equals(action)) {
            rearmAll(context);
            return;
        }

        // Otherwise it is an alarm firing.
        int id = intent.getIntExtra("id", 0);
        String title = intent.getStringExtra("title");
        String text = intent.getStringExtra("text");

        // One-time notification (e.g. "time to buy"): show it and do not repeat.
        if (intent.getBooleanExtra("once", false)) {
            show(context, id, title, text);
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                   .edit().remove("o_" + id).apply();
            return;
        }

        int hour = intent.getIntExtra("hour", 0);
        int minute = intent.getIntExtra("minute", 0);

        show(context, id, title, text);

        // Re-arm for the same time tomorrow (daily repeat)
        Calendar cal = Calendar.getInstance();
        cal.set(Calendar.HOUR_OF_DAY, hour);
        cal.set(Calendar.MINUTE, minute);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        cal.add(Calendar.DAY_OF_YEAR, 1);
        setAlarm(context, id, title, text, hour, minute, cal.getTimeInMillis());
    }

    public static void show(Context ctx, int id, String title, String text) {
        NotificationManager nm =
            (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        nm.createNotificationChannel(new NotificationChannel(
            CHANNEL_ID, "Medication reminders", NotificationManager.IMPORTANCE_HIGH));

        Intent launch = ctx.getPackageManager()
            .getLaunchIntentForPackage(ctx.getPackageName());
        PendingIntent open = PendingIntent.getActivity(ctx, id, launch,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification n = new Notification.Builder(ctx, CHANNEL_ID)
            .setSmallIcon(ctx.getApplicationInfo().icon)
            .setContentTitle(title)
            .setContentText(text)
            .setContentIntent(open)
            .setAutoCancel(true)
            .build();
        nm.notify(id, n);
    }

    public static void schedule(Context ctx, int id, String title, String text,
                                int hour, int minute) {
        save(ctx, id, title, text, hour, minute);   // remember it for after reboot
        setAlarm(ctx, id, title, text, hour, minute, nextTrigger(hour, minute));
    }

    /** One-time notification at triggerAt (epoch millis). Inexact on purpose:
     *  no exact-alarm permission needed, and it may arrive a few minutes late. */
    public static void scheduleOnce(Context ctx, int id, String title, String text,
                                    long triggerAt) {
        saveOnce(ctx, id, title, text, triggerAt);
        setOnceAlarm(ctx, id, title, text, triggerAt);
    }

    public static void cancel(Context ctx, int id) {
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        PendingIntent pi = buildPending(ctx, id, new Intent(ctx, ReminderReceiver.class));
        am.cancel(pi);
        pi.cancel();
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
           .edit().remove("r_" + id).remove("o_" + id).apply();
    }

    // ---------- helpers ----------

    private static long nextTrigger(int hour, int minute) {
        Calendar cal = Calendar.getInstance();
        cal.set(Calendar.HOUR_OF_DAY, hour);
        cal.set(Calendar.MINUTE, minute);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        if (cal.getTimeInMillis() <= System.currentTimeMillis()) {
            cal.add(Calendar.DAY_OF_YEAR, 1);
        }
        return cal.getTimeInMillis();
    }

    private static void save(Context ctx, int id, String title, String text,
                             int hour, int minute) {
        try {
            JSONObject o = new JSONObject();
            o.put("title", title);
            o.put("text", text);
            o.put("hour", hour);
            o.put("minute", minute);
            ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
               .edit().putString("r_" + id, o.toString()).apply();
        } catch (Exception ignored) { }
    }

    private static void saveOnce(Context ctx, int id, String title, String text,
                                 long triggerAt) {
        try {
            JSONObject o = new JSONObject();
            o.put("title", title);
            o.put("text", text);
            o.put("at", triggerAt);
            ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
               .edit().putString("o_" + id, o.toString()).apply();
        } catch (Exception ignored) { }
    }

    private static void rearmAll(Context ctx) {
        SharedPreferences sp = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        for (Map.Entry<String, ?> e : sp.getAll().entrySet()) {
            String key = e.getKey();
            try {
                if (key.startsWith("r_")) {
                    int id = Integer.parseInt(key.substring(2));
                    JSONObject o = new JSONObject((String) e.getValue());
                    int hour = o.getInt("hour");
                    int minute = o.getInt("minute");
                    setAlarm(ctx, id, o.getString("title"), o.getString("text"),
                             hour, minute, nextTrigger(hour, minute));
                } else if (key.startsWith("o_")) {
                    int id = Integer.parseInt(key.substring(2));
                    JSONObject o = new JSONObject((String) e.getValue());
                    long at = o.getLong("at");
                    if (at <= System.currentTimeMillis()) {
                        // Its time passed while the phone was off: show it now.
                        show(ctx, id, o.getString("title"), o.getString("text"));
                        sp.edit().remove(key).apply();
                    } else {
                        setOnceAlarm(ctx, id, o.getString("title"),
                                     o.getString("text"), at);
                    }
                }
            } catch (Exception ignored) { }
        }
    }

    private static void setOnceAlarm(Context ctx, int id, String title, String text,
                                     long triggerAt) {
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        Intent i = new Intent(ctx, ReminderReceiver.class);
        i.putExtra("id", id);
        i.putExtra("title", title);
        i.putExtra("text", text);
        i.putExtra("once", true);
        PendingIntent pi = buildPending(ctx, id, i);
        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi);
    }

    private static void setAlarm(Context ctx, int id, String title, String text,
                                 int hour, int minute, long triggerAt) {
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        Intent i = new Intent(ctx, ReminderReceiver.class);
        i.putExtra("id", id);
        i.putExtra("title", title);
        i.putExtra("text", text);
        i.putExtra("hour", hour);
        i.putExtra("minute", minute);
        PendingIntent pi = buildPending(ctx, id, i);

        if (Build.VERSION.SDK_INT >= 31 && !am.canScheduleExactAlarms()) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi); // inexact fallback
        } else {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi);
        }
    }

    private static PendingIntent buildPending(Context ctx, int id, Intent i) {
        return PendingIntent.getBroadcast(ctx, id, i,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    // ---------- exact-alarm permission helpers (called from Python) ----------

    public static boolean canScheduleExact(Context ctx) {
        if (Build.VERSION.SDK_INT < 31) return true;   // not needed before Android 12
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        return am.canScheduleExactAlarms();
    }

    public static void openExactAlarmSettings(Context ctx) {
        if (Build.VERSION.SDK_INT < 31) return;
        Intent i = new Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,
                              Uri.parse("package:" + ctx.getPackageName()));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(i);
    }
}