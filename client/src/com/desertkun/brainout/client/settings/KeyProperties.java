package com.desertkun.brainout.client.settings;

import com.badlogic.gdx.utils.ObjectMap;
import com.desertkun.brainout.L;

public class KeyProperties extends Properties
{
    public enum Keys
    {
        up,
        down,
        left,
        right,
        sit,
        run,
        reload,

        playerList,
        dropWeapon,
        dropAmmo,
        changeTeam,
        shootMode,
        unloadWeapon,
        zoom,
        chat,
        teamChat,
        console,
        voiceChat,
        hideInterface,

        slotPrimary,
        slotSecondary,
        slotSpecial,
        slotSpecialTwo,
        slotKnifeAlt,
        slotKnife,
        slotBinoculars,
        slotFlashlight,
        previousSlot,

        activate,
        squat,
        freePlayFriends
    }

    private ObjectMap<Integer, Keys> keys;
    private ObjectMap<Keys, Integer> codes;

    public KeyProperties(String name, String localization)
    {
        super(name, localization);

        keys = new ObjectMap<>();
        codes = new ObjectMap<>();
    }

    public KeyProperties(String name, String localization, Properties parent)
    {
        super(name, localization, parent);

        keys = new ObjectMap<>();
        codes = new ObjectMap<>();
    }

    public Keys getKey(int keyCode)
    {
        return keys.get(keyCode);
    }

    public int getKeyCode(Keys keys, int def)
    {
        return this.codes.get(keys, def);
    }

    @Override
    public void read(com.badlogic.gdx.utils.Json json, com.badlogic.gdx.utils.JsonValue data)
    {
        super.read(json, data);
        com.badlogic.gdx.utils.JsonValue group = data.get(getName());
        if (group == null) return;
        for (Property property : getProperties())
        {
            if (!(property instanceof KeycodeProperty) || group.has(property.getName())) continue;
            KeycodeProperty binding = (KeycodeProperty) property;
            if (binding.getKey() == Keys.slotKnife && group.has("slot-4"))
            {
                int old = group.getInt("slot-4");
                if (old != com.badlogic.gdx.Input.Keys.NUM_4) binding.setValue(old);
            }
            if (binding.getKey() == Keys.shootMode && group.has("shoot-mode"))
            {
                int old = group.getInt("shoot-mode");
                if (old != com.badlogic.gdx.Input.Keys.V) binding.setValue(old);
            }
        }
        update();
    }

    public void update()
    {
        keys.clear();

        for (Property property : getProperties())
        {
            if (!(property instanceof KeycodeProperty))
                continue;

            KeycodeProperty keycodeProperty = (KeycodeProperty) property;

            keys.put(keycodeProperty.getValue(), keycodeProperty.getKey());
            codes.put(keycodeProperty.getKey(), keycodeProperty.getValue());
        }
    }
}
