package com.desertkun.brainout.components.my;

import com.badlogic.gdx.utils.Array;
import com.badlogic.gdx.utils.ObjectMap;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.Constants;
import com.desertkun.brainout.common.msg.client.SwitchShootModeMsg;
import com.desertkun.brainout.components.ClientWeaponSlotComponent;
import com.desertkun.brainout.components.PlayerOwnerComponent;
import com.desertkun.brainout.components.WeaponSlotComponent;
import com.desertkun.brainout.content.bullet.Bullet;
import com.desertkun.brainout.content.components.SecondaryWeaponSlotComponent;
import com.desertkun.brainout.content.instrument.Weapon;
import com.desertkun.brainout.data.active.ActiveData;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.components.SecondaryWeaponSlotComponentData;
import com.desertkun.brainout.data.components.WeaponAnimationComponentData;
import com.desertkun.brainout.data.components.base.Component;
import com.desertkun.brainout.data.consumable.ConsumableRecord;
import com.desertkun.brainout.data.instrument.WeaponData;
import com.desertkun.brainout.events.*;
import com.desertkun.brainout.gs.ActionPhaseState;
import com.desertkun.brainout.gs.GameState;

public class MyWeaponComponent extends Component
{
    private final ConsumableRecord record;
    private final WeaponData data;
    private WeaponSlotComponent currentSlot;
    private boolean reloadRightAfterLeft;
    private float rightReloadDelay = -1;
    private long rightReloadFrame;
    public static final float PAIRED_RELOAD_DELAY = 0.002f;
    private ObjectMap<String, WeaponSlotComponent> slots;

    public MyWeaponComponent(WeaponData weaponData, ConsumableRecord record)
    {
        super(weaponData, null);

        this.data = weaponData;
        this.record = record;
        this.slots = new ObjectMap<>();
    }

    public WeaponSlotComponent getCurrentSlot()
    {
        return currentSlot;
    }

    public WeaponSlotComponent getSlot(String slot)
    {
        if (slots.containsKey(slot))
        {
            return slots.get(slot);
        }

        return null;
    }

    public ObjectMap<String, WeaponSlotComponent> getSlots()
    {
        return slots;
    }

    public WeaponSlotComponent addSlot(Weapon.WeaponProperties properties, String name, String icon)
    {
        WeaponSlotComponent slot =
            new ClientWeaponSlotComponent(data, record, properties, name, icon, this::getSlot);

        slots.put(name, slot);
        slot.init();

        return slot;
    }

    @Override
    public void init()
    {
        super.init();

        WeaponSlotComponent slot = addSlot(data.getWeapon().getPrimaryProperties(),
                Constants.Properties.SLOT_PRIMARY, null);

        setCurrentSlot(slot);

        SecondaryWeaponSlotComponentData secondary =
                data.getComponent(SecondaryWeaponSlotComponentData.class);

        if (secondary != null)
        {
            SecondaryWeaponSlotComponent content = secondary.getContentComponent();

            addSlot(secondary.getWeaponProperties(), Constants.Properties.SLOT_SECONDARY, content.getIcon());
        }
    }

    public boolean setCurrentSlot(WeaponSlotComponent currentSlot)
    {
        if (this.currentSlot != currentSlot)
        {
            this.currentSlot = currentSlot;
            return true;
        }

        return false;
    }

    @Override
    public boolean onEvent(Event event)
    {
        WeaponSlotComponent current = getCurrentSlot();
        if (current == null)
        {
            throw new IllegalStateException("Current slot shouldn't be null");
        }

        switch (event.getID())
        {
            case gameController:
            {
                GameControllerEvent gcEvent = ((GameControllerEvent) event);

                if (isPaired())
                {
                    WeaponSlotComponent right = getSlot(Constants.Properties.SLOT_SECONDARY);
                    switch (gcEvent.action)
                    {
                        case beginLaunch: current.beginLaunching(); return true;
                        case endLaunch: current.endLaunching(); return true;
                        // paired pistols: RMB still fires the second pistol (no high-stance aiming)
                        case beginAimHold:
                        case beginLaunchSecondary: rightReloadDelay=-1; right.beginLaunching(); return true;
                        case endAimHold:
                        case endLaunchSecondary: right.endLaunching(); return true;
                        case reload:
                            if (!data.getWeapon().hasSequentialPairedReload())
                            {
                                reloadRightAfterLeft = false;
                                if (rightReloadDelay >= 0) return true;
                                boolean startedLeft = current.getLoadedRounds() < current.getClipSize().asInt() && current.doReload(true);
                                if (right.getLoadedRounds() < right.getClipSize().asInt())
                                {
                                    if (startedLeft)
                                    {
                                        rightReloadDelay = PAIRED_RELOAD_DELAY;
                                        rightReloadFrame = com.badlogic.gdx.Gdx.graphics.getFrameId();
                                    }
                                    else right.doReload(true);
                                }
                                return true;
                            }
                            if (right.isReloadingOrChambering()) return true;
                            if (current.isReloadingOrChambering())
                            {
                                reloadRightAfterLeft = right.getLoadedRounds() < right.getClipSize().asInt();
                                return true;
                            }
                            boolean rightNeedsAmmo = right.getLoadedRounds() < right.getClipSize().asInt();
                            if (current.getLoadedRounds() < current.getClipSize().asInt() && current.doReload(true))
                                reloadRightAfterLeft = rightNeedsAmmo;
                            else if (rightNeedsAmmo)
                                right.doReload(true);
                            return true;
                    }
                }
                switch (gcEvent.action)
                {
                    case beginLaunchSecondary:
                    {
                        if (!current.getWeaponProperties().isAutoSwitchSecondary())
                            return true;

                        boolean allow = !current.isReloading() || current.getChambered() > 0;

                        if (current.getSlot().equals(Constants.Properties.SLOT_PRIMARY) && allow)
                        {
                            current = switchWeaponSlot(Constants.Properties.SLOT_SECONDARY);
                        }

                        current.beginLaunching();

                        return true;
                    }

                    case beginLaunch:
                    {
                        if (!checkOtherSlots(current))
                            return false;

                        boolean allow = !current.isReloading() || current.getChambered() > 0;

                        if (current.getSlot().equals(Constants.Properties.SLOT_SECONDARY) &&
                            current.getWeaponProperties().isAutoSwitchSecondary() && allow)
                        {
                            current = switchWeaponSlot(Constants.Properties.SLOT_PRIMARY);
                        }

                        current.beginLaunching();

                        return true;
                    }

                    case endLaunchSecondary:
                    {
                        if (!current.getWeaponProperties().isAutoSwitchSecondary())
                            return true;
                    }
                    case endLaunch:
                    {
                        current.endLaunching();

                        return true;
                    }

                    case switchShootMode:
                    {
                        current.nextShootMode();
                        BrainOutClient.ClientController.sendTCP(new SwitchShootModeMsg(
                            current.getShootMode(), current.getSlot()));

                        BrainOutClient.ClientController.getUserProfile().setPreferableShooMode(
                            data.getWeapon().getID(), current.getShootMode());

                        return false;
                    }

                    case reload:
                    {
                        if (!checkOtherSlots(current))
                            return false;

                        current.doReload(true);

                        return true;
                    }

                    case unload:
                    {
                        current.doUnload();

                        BrainOut.EventMgr.sendDelayedEvent(SimpleEvent.obtain(SimpleEvent.Action.instrumentUpdated));

                        return true;
                    }
                }

                return false;
            }

            case setInstrument:
            {
                break;
            }

            case hookInstrument:
            {
                current.setLaunching(false);
                break;
            }

            case simple:
            {
                SimpleEvent simpleEvent = (SimpleEvent)event;

                switch (simpleEvent.getAction())
                {
                    case reload:
                    {
                        current.doReload(true);

                        return false;
                    }
                    case deselected:
                    {
                        deselected();

                        return false;
                    }
                }
            }
        }

        return false;
    }

    public boolean isHandlingReload()
    {
        if (reloadRightAfterLeft) return true;
        for (WeaponSlotComponent slot : slots.values())
        {
            if (slot.isReloadingOrChambering() ||
                slot.getState() == WeaponSlotComponent.State.loadMagazineRound ||
                slot.getState() == WeaponSlotComponent.State.cocking) return true;
        }
        return false;
    }

    private boolean checkOtherSlots(WeaponSlotComponent current)
    {
        for (ObjectMap.Entry<String, WeaponSlotComponent> entry : slots)
        {
            WeaponSlotComponent slot = entry.value;

            if (slot == current)
                continue;

            if (slot.isReloading() && current.getChambered() == 0)
            {
                return false;
            }
        }

        return true;
    }

    private void deselected()
    {
        reloadRightAfterLeft = false;
        WeaponSlotComponent slot = getCurrentSlot();

        if (slot == null)
            return;

        if (slot.getState() == WeaponSlotComponent.State.cocked ||
            slot.getState() == WeaponSlotComponent.State.cocking)
        {
            slot.doReset(false);
        }
    }

    public boolean isPaired()
    {
        return data.getWeapon().isPaired();
    }

    public WeaponSlotComponent switchWeaponSlot(String name)
    {
        if (name == null || isPaired())
        {
            name = Constants.Properties.SLOT_PRIMARY;
        }

        if (slots.containsKey(name))
        {
            WeaponSlotComponent slot = getSlot(name);
            if (setCurrentSlot(slot))
            {
                WeaponAnimationComponentData cwcd = data.getComponent(WeaponAnimationComponentData.class);

                if (cwcd != null)
                {
                    BrainOut.EventMgr.sendDelayedEvent(data,
                            LaunchEffectEvent.obtain(LaunchEffectEvent.Kind.switchMode, cwcd.getLaunchPointData()));
                }
            }
            return slot;
        }

        return null;
    }

    @Override
    public void update(float dt)
    {
        super.update(dt);

        getCurrentSlot().update(dt);
        if (isPaired())
        {
            WeaponSlotComponent right = getSlot(Constants.Properties.SLOT_SECONDARY);
            right.update(dt);
            if (rightReloadDelay >= 0)
            {
                if (!(data.getOwner() instanceof PlayerData) ||
                    ((PlayerData)data.getOwner()).getCurrentInstrument() != data ||
                    !((PlayerData)data.getOwner()).isAlive()) rightReloadDelay = -1;
                else if (com.badlogic.gdx.Gdx.graphics.getFrameId() > rightReloadFrame)
                {
                    rightReloadDelay -= dt;
                    if (rightReloadDelay <= 0)
                    {
                        rightReloadDelay = -1;
                        if (right.getLoadedRounds() < right.getClipSize().asInt()) right.doReload(true);
                    }
                }
            }
            if (reloadRightAfterLeft && !currentSlot.isReloadingOrChambering())
            {
                reloadRightAfterLeft = false;
                if (right.getLoadedRounds() < right.getClipSize().asInt()) right.doReload(true);
            }
        }
    }

    private void updatePlayerData()
    {
        BrainOut.EventMgr.sendDelayedEvent(MyPlayerSetEvent.obtain(((PlayerData) data.getOwner())));
    }

    @Override
    public boolean hasUpdate()
    {
        return true;
    }

    @Override
    public boolean hasRender()
    {
        return false;
    }

    public ConsumableRecord getRecord()
    {
        return record;
    }
}
