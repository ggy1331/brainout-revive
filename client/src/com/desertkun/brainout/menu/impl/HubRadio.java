package com.desertkun.brainout.menu.impl;

import com.badlogic.gdx.Gdx;
import com.desertkun.brainout.BrainOutClient;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;

/** Hub state stays on the render thread; diskless PCM playback runs in its own worker. */
public final class HubRadio {
    private static final ExecutorService worker = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "hub-radio-media"); t.setDaemon(true); return t;
    });
    private static final ExecutorService controls = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "hub-radio-control"); t.setDaemon(true); return t;
    });
    public static JSONObject state = new JSONObject();
    public static String status = "Очередь пуста";
    public static boolean adding;
    private static boolean active;
    private static int revision = -1;
    private static volatile int session;
    private static volatile long receivedAt;
    private static volatile double anchor;
    private static volatile boolean paused = true;
    private static RadioStream music;
    private static int corrections;
    private static String playing = "", desired = "";
    private static final Set<String> failed = new HashSet<>();

    public static void enter() { active = true; }
    public static void leave() {
        active = false; session++; revision = -1;
        state = new JSONObject(); desired = ""; receivedAt=0; failed.clear(); stop();
        if(BrainOutClient.MusicMng!=null)BrainOutClient.MusicMng.setRadioOverride(false);
    }
    private static void stop() {
        if (music != null) { music.dispose(); music = null; }

        playing = "";
    }
    public static boolean replacesBackground() {
        return active && state.optJSONArray("queue") != null && state.getJSONArray("queue").length() > 0;
    }
    public static void accept(JSONObject value, double travelSeconds) {
        if (!active || value == null) return;
        float previous=position();
        boolean wasPaused=paused;
        state=value;
        paused=value.optBoolean("paused",true);
        anchor=value.optDouble("position",0)+(paused?0:travelSeconds);
        receivedAt=System.nanoTime();
        int next=value.optInt("revision");
        String current=value.optString("current");
        if(revision!=next || !desired.equals(current)) {
            boolean discontinuity=wasPaused!=paused || Math.abs(previous-anchor)>.45;
            revision=next;desired=current;failed.clear();corrections=0;
            if(!playing.equals(current) || discontinuity)stop();
        }
    }
    public static float position() {
        return (float)(anchor+(paused || receivedAt==0?0:(System.nanoTime()-receivedAt)/1e9));
    }
    public static void tick() {
        if(!active)return;
        BrainOutClient.MusicMng.setRadioOverride(replacesBackground());
        if(receivedAt!=0 && (System.nanoTime()-receivedAt)/1e9>12) {
            stop();status="Нет связи с радио хаба";return;
        }
        if(desired.isEmpty()) { stop();status="Очередь пуста";return; }
        if(paused) { stop();status="Пауза";return; }
        if(music!=null) {
            music.setVolume(BrainOutClient.ClientSett.getRadioVolume().getFloatValue());
            JSONObject track=find(playing);
            if(music.isDone()) {
                if(playing.equals(desired) && track!=null && position()>=track.optDouble("duration")-.5)
                    return; // Wait for the authoritative next-track snapshot.
                failed.add(playing);stop();status="Поток недоступен, ищем замену";
            } else if(music.isPlaying()) {
                status=(playing.equals(desired)?"Играет: ":"Временная замена: ")+(track==null?"":track.optString("title"));
                if(playing.equals(desired) && music.age()>1 && Math.abs(music.getPosition()-position())>.3) {
                    if(++corrections>=3)failed.add(playing);
                    stop();status="Синхронизация потока…";
                }
            }
        }
        if(music==null) {
            JSONObject track=failed.contains(desired)?null:find(desired);
            if(track!=null && position()>=track.optDouble("duration")-.05)return;
            if(track==null) {
                JSONArray tracks=state.optJSONArray("queue");
                if(tracks!=null)for(int i=0;i<tracks.length();i++) {
                    JSONObject t=tracks.getJSONObject(i);
                    if(!failed.contains(t.getString("id"))) { track=t;break; }
                }
            }
            if(track!=null)load(track);
            else status="Нет доступных треков. Ожидание переключения хозяином.";
        }
    }
    private static JSONObject find(String id) {
        JSONArray tracks = state.optJSONArray("queue");
        if (tracks != null) for (int i=0; i<tracks.length(); i++)
            if (id.equals(tracks.getJSONObject(i).optString("id"))) return tracks.getJSONObject(i);
        return null;
    }
    private static void load(JSONObject track) {
        playing=track.getString("id");
        boolean shared=playing.equals(desired);
        status="Подключение к потоку: "+track.optString("title");
        music=new RadioStream(track.getString("video"),HomeHub.token(),shared?position():0,
                shared?HubRadio::position:null);
        music.setVolume(BrainOutClient.ClientSett.getRadioVolume().getFloatValue());
    }
    public static void command(JSONObject body) {
        if(!active || HomeHub.ENDPOINT==null)return;
        int generation=session;
        String credential=HomeHub.token();
        controls.execute(() -> {
            if(generation!=session)return;
            try { HomeHub.request("radio",body,credential); }
            catch(Exception ex) { Gdx.app.postRunnable(() -> {
                if(generation==session)status=ex.getMessage();
            }); }
        });
    }
    public static void add(String url) {
        if (adding || HomeHub.ENDPOINT == null) return;
        adding=true; status="Проверка ссылки…";
        String credential=HomeHub.token();
        int generation=session;
        worker.execute(() -> {
            try {
                JSONObject track=HomeHub.request("radio-resolve",new JSONObject().put("url",url),credential);
                Gdx.app.postRunnable(() -> {
                    adding=false;
                    if(generation!=session || !active)return;
                    track.put("op","add"); command(track); status="Трек подготовлен";
                });
            } catch(Exception ex) { Gdx.app.postRunnable(() -> {
                adding=false; if(generation==session)status=ex.getMessage();
            }); }
        });
    }
}
