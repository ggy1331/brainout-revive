package com.desertkun.brainout.menu.impl;

import com.badlogic.gdx.utils.Array;
import com.desertkun.brainout.mode.GameMode;
import com.desertkun.brainout.online.RoomSettings;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Collections;
import java.util.TreeSet;

final class HubMatchMenu extends QuickPlayOptionsMenu {
    private final JSONObject maps;

    HubMatchMenu(JSONObject maps) {
        super("Запуск матча", new Callback() {
            public void cancelled() {}
            public void selected(String name, RoomSettings settings, QuickPlayOptionsMenu menu) {
                JSONObject options = new JSONObject();
                options.put("map", settings.getMap().isDefined() ? settings.getMap().getValue() : "");
                options.put("mode", settings.getMode().isDefined() ? settings.getMode().getValue() : "");
                HomeHub.query("match", options, null);
            }
        }, new RoomSettings());
        this.maps = maps;
    }

    @Override public Object navigationKey() { return "match-form"; }
    @Override protected boolean hasExtendedOptions() { return false; }

    private boolean supports(String map, String mode) {
        JSONArray allowed = maps.getJSONArray(map);
        for (int i=0;i<allowed.length();i++) if (mode.equals(allowed.getString(i))) return true;
        return false;
    }

    @Override protected String[] getMaps() {
        ArrayList<String> compatible = new ArrayList<>();
        String mode = getSettings().getMode().getValue();
        for (String map : maps.keySet())
            if (!getSettings().getMode().isDefined() || supports(map, mode)) compatible.add(map);
        Collections.sort(compatible);
        return compatible.toArray(new String[0]);
    }

    @Override protected GameMode.ID[] getGameModes() {
        TreeSet<GameMode.ID> modes = new TreeSet<>();
        for (String map : maps.keySet()) {
            JSONArray values = maps.getJSONArray(map);
            for (int i=0;i<values.length();i++) modes.add(GameMode.ID.valueOf(values.getString(i)));
        }
        return modes.toArray(new GameMode.ID[0]);
    }

    @Override protected void renderOptions(Array<SettingsOption> options) {
        options.add(new ModeOption() {
            @Override protected void setItem(Mode item) {
                super.setItem(item);
                RoomSettings settings = getSettings();
                if (settings.getMode().isDefined() && settings.getMap().isDefined() &&
                    !supports(settings.getMap().getValue(), settings.getMode().getValue())) {
                    settings.getMap().undefine();
                    com.badlogic.gdx.Gdx.app.postRunnable(HubMatchMenu.this::reset);
                }
            }
        });
        options.add(new MapOption(name -> {}));
    }
}
