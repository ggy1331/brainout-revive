package com.desertkun.brainout.bot;

import com.desertkun.brainout.data.consumable.ConsumableRecord;

/**
 * revive: an enemy has just ducked behind cover - the bot switches to its grenade, lobs it at
 * the last place the enemy was seen and takes its gun back. The throw itself is
 * BotControllerComponentData.throwGrenadeAt (the same server path a player's throw takes).
 */
public class TaskThrowGrenade extends Task
{
    private final float x, y;
    private final ConsumableRecord previous;
    private float timer;
    private boolean thrown;

    public TaskThrowGrenade(TaskStack stack, float x, float y)
    {
        super(stack);
        this.x = x;
        this.y = y;
        this.previous = getController().getCurrentWeaponRecord();
        getController().stopFollowing();
        openFire(false);
    }

    @Override
    protected void update(float dt)
    {
        timer += dt;
        if (!thrown)
        {
            // a short wind-up: the grenade in hand before it flies
            if (timer < 0.35f) return;
            thrown = true;
            if (!getController().throwGrenadeAt(x, y))
            {
                back();
                return;
            }
            timer = 0;
            return;
        }
        if (timer > 0.45f) back();
    }

    private void back()
    {
        if (previous != null && previous.getAmount() > 0) selectInstrument(previous);
        pop();
    }
}
