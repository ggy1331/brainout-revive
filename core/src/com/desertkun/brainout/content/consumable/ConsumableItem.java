package com.desertkun.brainout.content.consumable;

import com.badlogic.gdx.utils.Json;
import com.badlogic.gdx.utils.JsonValue;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.content.Content;
import com.desertkun.brainout.data.active.ActiveData;

public abstract class ConsumableItem implements Json.Serializable
{
    private int private_ = -1;

    public abstract Content getContent();
    public abstract boolean stacks(ConsumableItem item);
    public void stackWith(ConsumableItem item, int amount) {}
    public boolean splits() { return true; }

    @Override
    public void write(Json json)
    {
        json.writeValue("class", BrainOut.R.getClassName(getClass()));

        if (isPrivate())
        {
            json.writeValue("private", getPrivate());
        }
    }

    public boolean hasAutoQuality()
    {
        return false;
    }

    public int pickAutoQuality()
    {
        return 0;
    }

    @Override
    public void read(Json json, JsonValue jsonData)
    {
        if (jsonData.has("private"))
        {
            private_ = jsonData.getInt("private", -1);
        }
        else
        {
            private_ = -1;
        }
    }

    public boolean isPrivate()
    {
        return private_ != -1;
    }

    public int getPrivate()
    {
        return private_;
    }

    public void setPrivate(int private_)
    {
        this.private_ = private_;
    }

    public boolean isValid()
    {
        Content content = getContent();
        if (content instanceof com.desertkun.brainout.content.gamecase.Case) return false;
        if (content instanceof ConsumableToOwnableContent &&
            ((ConsumableToOwnableContent)content).getOwnableContent() instanceof com.desertkun.brainout.content.gamecase.Case)
            return false;
        return content != null;
    }

    public void init() {}
    public void release() {}

    public void setOwner(ActiveData activeData) {}

}
