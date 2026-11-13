package com.desertkun.brainout.data.effect;

import com.badlogic.gdx.graphics.g2d.Batch;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.data.interfaces.LaunchData;
import com.desertkun.brainout.data.interfaces.RenderContext;
import com.desertkun.brainout.graphics.CenterSprite;

import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;

@Reflect("data.effect.DamageEffectData")
public class DamageEffectData extends EffectData
{
    private final CenterSprite sprite;
    private float time;
    private final float initTime;
    // the share of the time at the end over which it fades out (1 = fades all the time)
    private float fadeShare = 1;

    /** Fully visible, fading out only over the last fadeShare of the time (the shot marker). */
    public DamageEffectData(LaunchData launchData, String sprite, float time, float fadeShare)
    {
        this(launchData, sprite, time);
        this.fadeShare = Math.max(0.01f, Math.min(1, fadeShare));
    }

    public DamageEffectData(LaunchData launchData, String sprite, float time)
    {
        super(null, launchData);

        this.time = time;
        this.initTime = time;
        this.sprite = new CenterSprite(BrainOutClient.getRegion(sprite), launchData);
    }

    @Override
    public void render(Batch batch, RenderContext context)
    {
        sprite.draw(batch);
    }

    @Override
    public boolean hasRender()
    {
        return true;
    }

    @Override
    public boolean done()
    {
        return time <= 0;
    }

    @Override
    public void init()
    {

    }

    @Override
    public void update(float dt)
    {
        time -= dt;

        if (time > 0)
        {
            sprite.setAlpha(Math.min(1, time / (initTime * fadeShare)));
        }
    }

    @Override
    public boolean hasUpdate()
    {
        return true;
    }
}
