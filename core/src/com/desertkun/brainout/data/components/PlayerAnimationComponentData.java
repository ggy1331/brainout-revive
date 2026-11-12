package com.desertkun.brainout.data.components;

import com.badlogic.gdx.utils.Json;
import com.badlogic.gdx.utils.JsonValue;
import com.badlogic.gdx.utils.ObjectMap;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.content.PlayerSkin;
import com.desertkun.brainout.content.PlayerSkinParts;
import com.desertkun.brainout.content.active.Player;
import com.desertkun.brainout.content.components.AnimationComponent;
import com.desertkun.brainout.content.components.PlayerAnimationComponent;
import com.desertkun.brainout.content.upgrades.Upgrade;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.instrument.InstrumentData;
import com.desertkun.brainout.data.interfaces.BonePointData;
import com.desertkun.brainout.data.interfaces.FlippedLaunchData;
import com.desertkun.brainout.data.interfaces.LaunchData;
import com.desertkun.brainout.events.Event;
import com.desertkun.brainout.events.SimpleEvent;
import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;
import com.esotericsoftware.spine.AnimationState;
import com.esotericsoftware.spine.Bone;
import com.esotericsoftware.spine.Skeleton;
import com.esotericsoftware.spine.Slot;
import com.esotericsoftware.spine.attachments.Attachment;

@Reflect("playeranimcom")
@ReflectAlias("data.components.PlayerAnimationComponentData")
public class PlayerAnimationComponentData extends AnimationComponentData<PlayerAnimationComponent>
    implements Json.Serializable
{
    private final Slot primarySlot;
    private final Slot hookSlot;
    private final Slot primarySlotUpper;
    private final Slot secondarySlot;

    private final PlayerData playerData;
    private PlayerSkin skin;
    // optional per-part skins (null = same as skin)
    private PlayerSkin legsSkin, torsoSkin, headSkin;
    private BonePointData primaryBonePointData;
    private BonePointData secondaryBonePointData;
    private BonePointData bleedingBonePointData;

    private boolean isEnemy;

    public static final String PLAYER_HOLDER_PRIMARY = "holder-primary";
    public static final String PLAYER_HOLDER_SECONDARY = "holder-secondary";

    public static final String PLAYER_SLOT_HOOK = "hook";
    public static final String PLAYER_SLOT_PRIMARY = "slot-primary";
    public static final String PLAYER_SLOT_PRIMARY_UPPER = "slot-primary-upper";
    public static final String PLAYER_SLOT_SECONDARY = "slot-secondary";

    private ObjectMap<String, String> attachments;

    public PlayerAnimationComponentData(final PlayerData playerData, PlayerAnimationComponent animation)
    {
        super(playerData, animation);

        this.primarySlot = getSkeleton().findSlot(PLAYER_SLOT_PRIMARY);
        this.hookSlot = getSkeleton().findSlot(PLAYER_SLOT_HOOK);
        this.primarySlotUpper = getSkeleton().findSlot(PLAYER_SLOT_PRIMARY_UPPER);
        this.secondarySlot = getSkeleton().findSlot(PLAYER_SLOT_SECONDARY);

        this.playerData = playerData;
        this.isEnemy = false;

        this.attachments = new ObjectMap<>(2);
        this.skin = playerData.getPlayer().getDefaultSkin();
    }

    public PlayerSkin getSkin()
    {
        return skin;
    }

    public void setSkin(PlayerSkin skin)
    {
        if (skin == null)
            return;

        this.skin = skin;
        this.legsSkin = null;
        this.torsoSkin = null;
        this.headSkin = null;
    }

    /** Parts of the skin taken from other skins; null = same as the main skin. */
    public void setSkinParts(PlayerSkin legs, PlayerSkin torso, PlayerSkin head)
    {
        this.legsSkin = legs == skin ? null : legs;
        this.torsoSkin = torso == skin ? null : torso;
        this.headSkin = head == skin ? null : head;
    }

    public PlayerSkin getLegsSkin()
    {
        return legsSkin != null ? legsSkin : skin;
    }

    public PlayerSkin getTorsoSkin()
    {
        return torsoSkin != null ? torsoSkin : skin;
    }

    public PlayerSkin getHeadSkin()
    {
        return headSkin != null ? headSkin : skin;
    }

    public boolean hasSkinParts()
    {
        return legsSkin != null || torsoSkin != null || headSkin != null;
    }

    @Override
    public void init()
    {
        super.init();

        Bone primaryBone = getSkeleton().findBone(PLAYER_HOLDER_PRIMARY);
        Bone secondaryBone = getSkeleton().findBone(PLAYER_HOLDER_SECONDARY);

        if (primaryBone != null)
        {
            primaryBonePointData = new BonePointData(primaryBone, playerData.getLaunchData());
        }
        else
        {
            primaryBonePointData = new BonePointData(getSkeleton().getRootBone(), playerData.getLaunchData());
        }

        Bone bleedingBone = getSkeleton().findBone("bleeding");

        if (bleedingBone != null)
        {
            this.bleedingBonePointData = new BonePointData(bleedingBone, playerData.getLaunchData());
        }

        if (secondaryBone != null)
        {
            secondaryBonePointData = new BonePointData(secondaryBone, playerData.getLaunchData());
        }
        else
        {
            secondaryBonePointData = new BonePointData(getSkeleton().getRootBone(), playerData.getLaunchData());
        }
    }

    @Override
    public boolean onEvent(Event event)
    {
        switch (event.getID())
        {
            case animationAction:
            {
                InstrumentData currentInstrument = playerData.getCurrentInstrument();

                if (currentInstrument != null && currentInstrument.onEvent(event))
                {
                    return true;
                }

                break;
            }
            case resetInstrument:
            {
                detachCurrentInstrument();

                break;
            }
        }

        return super.onEvent(event);
    }

    private void detachCurrentInstrument()
    {
        if (getPrimarySlot() != null)
        {
            getPrimarySlot().setAttachment(null);
        }

        if (getPrimarySlotUpper() != null)
        {
            getPrimarySlotUpper().setAttachment(null);
        }

        if (getSecondarySlot() != null)
        {
            getSecondarySlot().setAttachment(null);
        }
    }

    public boolean isEnemy()
    {
        return isEnemy;
    }

    public void setEnemy(boolean isEnemy)
    {
        this.isEnemy = isEnemy;
    }

    @Override
    public void render(com.badlogic.gdx.graphics.g2d.Batch batch,
                       com.desertkun.brainout.data.interfaces.RenderContext context) {
        Skeleton skeleton = getSkeleton();
        if (skeleton == null || !playerData.hasSpawnProtection()) {
            super.render(batch, context);
            return;
        }
        com.badlogic.gdx.graphics.Color tint = skeleton.getColor();
        float r = tint.r, g = tint.g, b = tint.b, a = tint.a;
        tint.set(0.35f, 0.88f, 1f, 0.72f + 0.20f * (float)Math.sin(System.nanoTime() / 90000000.0));
        super.render(batch, context);
        tint.set(r, g, b, a);
    }

    @Override
    protected void updateSkin(AnimationComponent animation, Skeleton skeleton)
    {
        PlayerData playerData = ((PlayerData) getComponentObject());

        if (playerData.getTeam() != null && skeleton != null && getSkin() != null)
        {
            com.esotericsoftware.spine.Skin composed = PlayerSkinParts.compose(skeleton.getData(),
                getLegsSkin(), getTorsoSkin(), getHeadSkin());

            if (composed != null)
            {
                PlayerSkinParts.apply(skeleton, composed);
            }
            else
            {
                skeleton.setSkin(getSkin().getData());
            }
        }
    }

    public LaunchData getPrimaryLaunchData()
    {
        return primaryBonePointData;
    }

    public BonePointData getPrimaryBonePointData()
    {
        return primaryBonePointData;
    }

    public BonePointData getSecondaryBonePointData()
    {
        return secondaryBonePointData;
    }

    public BonePointData getBleedingBonePointData()
    {
        return bleedingBonePointData;
    }

    public Slot getPrimarySlot()
    {
        return primarySlot;
    }

    public Slot getHookSlot()
    {
        return hookSlot;
    }

    public Slot getPrimarySlotUpper()
    {
        return primarySlotUpper;
    }

    public Slot getSecondarySlot()
    {
        return secondarySlot;
    }

    @Override
    public void detach()
    {
        super.detach();

        detachCurrentInstrument();

        if (getHookSlot() != null)
        {
            getHookSlot().setAttachment(null);
        }
    }

    @Override
    public void write(Json json)
    {
        if (attachments.size > 0)
        {
            json.writeObjectStart("att");

            for (ObjectMap.Entry<String, String> entry : attachments)
            {
                json.writeValue(entry.key, entry.value);
            }

            json.writeObjectEnd();
        }

        if (skin != null)
        {
            json.writeValue("skin", skin.getID());

            if (legsSkin != null) json.writeValue("skin-legs", legsSkin.getID());
            if (torsoSkin != null) json.writeValue("skin-torso", torsoSkin.getID());
            if (headSkin != null) json.writeValue("skin-head", headSkin.getID());
        }
    }

    @Override
    public void read(Json json, JsonValue jsonData)
    {
        attachments.clear();

        if (jsonData.has("att"))
        {
            for (JsonValue att : jsonData.get("att"))
            {
                attachments.put(att.name(), att.asString());
            }
        }

        if (jsonData.has("skin"))
        {
            PlayerSkin previousSkin = skin;
            PlayerSkin previousLegs = getLegsSkin(), previousTorso = getTorsoSkin(), previousHead = getHeadSkin();

            setSkin(BrainOut.ContentMgr.get(jsonData.getString("skin"), PlayerSkin.class));
            setSkinParts(
                BrainOut.ContentMgr.get(jsonData.getString("skin-legs", null), PlayerSkin.class),
                BrainOut.ContentMgr.get(jsonData.getString("skin-torso", null), PlayerSkin.class),
                BrainOut.ContentMgr.get(jsonData.getString("skin-head", null), PlayerSkin.class));
            updateSkin();

            if (previousSkin != skin || previousLegs != getLegsSkin() ||
                previousTorso != getTorsoSkin() || previousHead != getHeadSkin())
            {
                BrainOut.EventMgr.sendDelayedEvent(getComponentObject(),
                    SimpleEvent.obtain(SimpleEvent.Action.skinUpdated));
            }
        }
    }

    public ObjectMap<String, String> getAttachments()
    {
        return attachments;
    }
}
