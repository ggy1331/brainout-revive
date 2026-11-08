package com.desertkun.brainout.data.components;

import com.badlogic.gdx.math.MathUtils;
import com.badlogic.gdx.utils.Array;
import com.badlogic.gdx.utils.ObjectMap;
import com.badlogic.gdx.utils.Queue;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.Constants;
import com.desertkun.brainout.content.components.ClientWeaponComponent;
import com.desertkun.brainout.content.effect.EffectSet;
import com.desertkun.brainout.content.instrument.Instrument;
import com.desertkun.brainout.content.instrument.Weapon;
import com.desertkun.brainout.content.upgrades.UpgradableProperty;
import com.desertkun.brainout.content.upgrades.Upgrade;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.bullet.BulletData;
import com.desertkun.brainout.data.effect.EffectData;
import com.desertkun.brainout.data.instrument.WeaponData;
import com.desertkun.brainout.data.interfaces.LaunchData;
import com.desertkun.brainout.data.interfaces.LengthBonePointData;
import com.desertkun.brainout.data.interfaces.PointLaunchData;
import com.desertkun.brainout.events.*;
import com.desertkun.brainout.utils.Pair;
import com.esotericsoftware.spine.Bone;

import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;

@Reflect("ClientWeaponComponent")
@ReflectAlias("data.components.ClientWeaponComponentData")
public class ClientWeaponComponentData extends ClientInstrumentComponentData<ClientWeaponComponent>
{
    private static Queue<String> removeList = new Queue<>();

    private final WeaponData weaponData;
    private EffectSet.EffectAttacher attacher;
    private EffectSet.EffectAttacher offHandAttacher;
    private WeaponAnimationComponentData wac;

    private UpgradableProperty silent;
    private UpgradableProperty fireBoneOffset;
    protected UpgradableProperty damage;

    public class ClientWeaponComponentAttacher extends EffectSet.EffectAttacher
    {
        private ObjectMap<String, Pair<EffectData, Float>> boundEffects = new ObjectMap<>();

        private final boolean right;
        public ClientWeaponComponentAttacher() { this(false); }
        public ClientWeaponComponentAttacher(boolean right) { this.right = right; }

        @Override
        public LaunchData attachDefault()
        {
            return right ? wac.getLaunchPointData("secondary") : wac.getLaunchPointData();
        }

        public ClientWeaponComponentData getWCD()
        {
            return ClientWeaponComponentData.this;
        }

        @Override
        public void bindEffect(String key, float time, EffectData effectData)
        {
            boundEffects.put(key, new Pair<>(effectData, time));
        }

        @Override
        public EffectData getBoundEffect(String key)
        {
            Pair<EffectData, Float> pair = boundEffects.get(key);

            if (pair == null)
                return null;

            return pair.first;
        }

        @Override
        public void updateBoundEffects(float dt)
        {
            for (ObjectMap.Entry<String, Pair<EffectData, Float>> entry : boundEffects)
            {
                Pair<EffectData, Float> pair = entry.value;

                pair.second -= dt;

                if (pair.second <= 0)
                {
                    removeList.addLast(entry.key);
                }
            }

            if (removeList.size > 0)
            {
                for (String s : removeList)
                {
                    boundEffects.remove(s);
                }

                removeList.clear();
            }
        }

        @Override
        public LaunchData attachTo(String attachObject)
        {
            if (weaponData.getOwner() == null) return null;

            Array<String> suppressedAttachments = wac.getSuppressedAttachments();

            if (suppressedAttachments != null && suppressedAttachments.contains(attachObject, false))
            {
                return null;
            }

            Bone bone = wac.actionSkeleton(right).findBone(attachObject);

            if (bone == null)
            {
                return null;
            }

            return new LengthBonePointData(
                    bone,
                    wac.actionOrigin(right),
                    fireBoneOffset.asFloat());
        }
    }

    public ClientWeaponComponentData(WeaponData weaponData,
        ClientWeaponComponent contentComponent)
    {
        super(weaponData, contentComponent);

        this.weaponData = weaponData;

        silent = new UpgradableProperty(Constants.Properties.SILENT, 0);
        damage = new UpgradableProperty(Constants.Properties.DAMAGE, 1.0f);
        fireBoneOffset = new UpgradableProperty(Constants.Properties.FIRE_BONE_OFFSET, 0.0f);
    }

    @Override
    public void init()
    {
        super.init();

        if (weaponData != null)
        {
            this.wac = getComponentObject().getComponent(WeaponAnimationComponentData.class);

            ObjectMap.Values<Upgrade> upgrades = weaponData.getUpgrades().values();

            Weapon weapon = weaponData.getWeapon();
            Weapon.WeaponProperties primary = weapon.getPrimaryProperties();

            silent.set(primary.property(Constants.Properties.SILENT));
            damage.set(primary.property(Constants.Properties.DAMAGE));

            silent.init(upgrades);
            damage.init(upgrades);
            fireBoneOffset.init(upgrades);

            this.attacher = new ClientWeaponComponentAttacher();
            if (weapon.isPaired()) offHandAttacher = new ClientWeaponComponentAttacher(true);
        }
    }

    public boolean isSilent()
    {
        return silent.asBoolean();
    }

    public UpgradableProperty getDamage()
    {
        return damage;
    }

    @Override
    public boolean onEvent(Event event)
    {
        switch (event.getID())
        {
            case customInstrumentEffect:
            {
                CustomInstrumentEffectEvent e = ((CustomInstrumentEffectEvent) event);
                launchCustomEffect(e.effect);

                return false;
            }
            case launchBullet:
            {
                LaunchBulletEvent e = (LaunchBulletEvent)event;

                BulletData bulletData = null;

                if (e.angles == null || e.bullet == null)
                    return false;

                for (float angle: e.angles)
                {
                    // offset angles by half a block
                    float x_ = e.x - MathUtils.cosDeg(angle) * 0.5f;
                    float y_ = e.y - MathUtils.sinDeg(angle) * 0.5f;

                    bulletData = e.bullet.getData(new PointLaunchData(
                        x_, y_, angle, getComponentObject().getDimension()
                    ), damage.asFloat(), getComponentObject().getDimension());
                    bulletData.setSilent(e.silent);

                    bulletData.setOwnerId(e.ownerId);
                    bulletData.setInstrumentInfo(weaponData.getInfo());

                    if (weaponData.getOwner() instanceof PlayerData)
                    {
                        bulletData.setPlayerData((PlayerData) weaponData.getOwner());
                    }

                    if (getMap() != null)
                    {
                        getMap().addBullet(bulletData);
                    }
                }

                if (wac != null) wac.animateHand(e.slot == com.desertkun.brainout.content.bullet.Bullet.BulletSlot.secondary, "fire", 0);

                EffectSet.EffectAttacher shot = offHandAttacher != null &&
                    e.slot == com.desertkun.brainout.content.bullet.Bullet.BulletSlot.secondary ? offHandAttacher : attacher;
                String eventKind;

                switch (e.slot)
                {
                    case secondary:
                    {
                        eventKind = weaponData.getWeapon().isPaired() ? "shoot" : "shootSecondary";
                        break;
                    }
                    case primary:
                    default:
                    {
                        eventKind = "shoot";
                        break;
                    }
                }

                BrainOut.EventMgr.sendDelayedEvent(weaponData,
                        LaunchAttachedEffectEvent.obtain(eventKind, shot));
                BrainOut.EventMgr.sendDelayedEvent(bulletData,
                        LaunchAttachedEffectEvent.obtain("launch", shot));

                if (weaponData.getWeapon().getPrimaryProperties().hasShellAutoEject())
                {
                    BrainOut.EventMgr.sendDelayedEvent(bulletData,
                            LaunchAttachedEffectEvent.obtain("shell", shot));
                }

                BrainOut.EventMgr.sendDelayedEvent(weaponData.getOwner(),
                    InstrumentActionEvent.obtain(Instrument.Action.hit));

                break;
            }

            case instrumentAnimationAction:
            {
                InstrumentAnimationActionEvent actionEvent = ((InstrumentAnimationActionEvent) event);

                processAction(actionEvent.action, actionEvent.customLaunchData);

                break;
            }
        }

        return super.onEvent(event);
    }

    @Override
    public void update(float dt)
    {
        attacher.updateBoundEffects(dt);
        if (offHandAttacher != null) offHandAttacher.updateBoundEffects(dt);
    }

    @Override
    public boolean hasUpdate()
    {
        return true;
    }

    private void processAction(String action, LaunchData customLaunchData)
    {
        if (action == null)
            return;

        InstrumentEffectsComponentData cmp =
            weaponData.getComponentWithSubclass(InstrumentEffectsComponentData.class);

        if (cmp != null)
        {
            if (customLaunchData != null)
            {
                cmp.launchEffect(action, customLaunchData);
            }
            else
            {
                cmp.launchEffect(action, attacher);
            }
        }
    }

    public EffectSet.EffectAttacher getAttacher()
    {
        return attacher;
    }
}
