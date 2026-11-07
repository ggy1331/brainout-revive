package com.desertkun.brainout.content;

import com.badlogic.gdx.utils.Json;
import com.badlogic.gdx.utils.JsonValue;
import com.desertkun.brainout.content.OwnableContent;
import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;

@Reflect("content.Layout")
public class Layout extends OwnableContent
{
    private String key;
    private int order;

    @Override
    public void read(Json json, JsonValue jsonData)
    {
        super.read(json, jsonData);

        key = jsonData.getString("key", "");
        order = jsonData.getInt("order", 0);
    }

    public static Layout resolve(String id)
    {
        if (id == null || !id.startsWith("layout-")) return null;
        int number;
        try { number = Integer.parseInt(id.substring(7)); }
        catch (NumberFormatException ignored) { return null; }
        if (number < 1 || !id.equals("layout-" + number)) return null;
        Layout original = com.desertkun.brainout.BrainOut.ContentMgr.get(id, Layout.class);
        if (original != null) return original;
        Layout layout = new Layout();
        layout.setID(id);
        layout.key = Integer.toString(number);
        layout.order = number - 1;
        return layout;
    }

    public String getKey()
    {
        return key;
    }

    public int getOrder()
    {
        return order;
    }
}
