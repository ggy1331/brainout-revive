package com.desertkun.brainout.data.components;

import com.desertkun.brainout.events.Event;
import com.esotericsoftware.spine.attachments.SkeletonAttachment;
import com.esotericsoftware.spine.Slot;
import com.esotericsoftware.spine.Bone;
import com.esotericsoftware.spine.Animation;
import com.esotericsoftware.spine.AnimationState;
import com.esotericsoftware.spine.Skeleton;
import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.utils.Array;
import com.desertkun.brainout.content.components.WeaponAnimationComponent;
import com.desertkun.brainout.data.instrument.WeaponData;
import com.desertkun.brainout.data.interfaces.*;

import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;

@Reflect("WeaponAnimationComponent")
@ReflectAlias("data.components.WeaponAnimationComponentData")
public class WeaponAnimationComponentData extends InstrumentAnimationComponentData<WeaponAnimationComponent>
    implements Animable
{
    protected final WeaponData weaponData;
    protected Array<String> suppressedAttachments;
    public WeaponAnimationComponentData(WeaponData weaponData, WeaponAnimationComponent contentComponent)
    {
        super(weaponData, contentComponent);

        this.weaponData = weaponData;
    }
    private static final class MagazineMotion
    {
        final Bone travel;
        final Slot magazine;
        final Slot handMarker;
        final Bone markerBone;

        MagazineMotion(Skeleton gun, Skeleton actor, String side)
        {
            travel = gun.findBone("pair-mag-travel");
            Slot mounted = null;
            if (travel != null)
            {
                for (Slot slot : gun.getSlots())
                    if (slot.getBone() == travel) { mounted = slot; break; }
            }
            magazine = mounted;
            handMarker = actor.findSlot("pair-magazine-" + side);
            markerBone = handMarker == null ? null : handMarker.getBone();
        }

        void apply()
        {
            if (magazine == null || markerBone == null) return;
            boolean nativeMagazine = magazine.getAttachment() != null;
            handMarker.getColor().a = nativeMagazine ? 0 : 1;
            boolean betweenMagazines = markerBone.getY() < -0.01f && handMarker.getAttachment() == null;
            travel.setX(markerBone.getX());
            travel.setY(markerBone.getY());
            travel.setScale(betweenMagazines ? 0f : 1f);
        }

        void release()
        {
            if (handMarker != null) handMarker.getColor().a = 1;
            if (travel != null) { travel.setX(0); travel.setY(0); travel.setScale(1); }
        }
    }

    private MagazineMotion leftMagazine, rightMagazine;
    private BonePointData offHandMuzzle;
    private Skeleton offHand;

    public LaunchData getLaunchPointData(String slot)
    {
        return offHandMuzzle != null && "secondary".equals(slot) ? offHandMuzzle : getLaunchPointData();
    }
    private AnimationState offHandState;
    private Slot offHandSlot;
    private SkeletonAttachment offHandAttachment;

    @Override
    public boolean onEvent(Event event)
    {
        boolean handled = super.onEvent(event);
        if (event.getID() == Event.ID.setInstrument &&
            weaponData != null && weaponData.getWeapon().isPaired() &&
            getAttachedTo() instanceof PlayerAnimationComponentData)
        {
            offHandSlot = ((PlayerAnimationComponentData)getAttachedTo()).getSecondarySlot();
            if (offHandSlot != null)
            {
                offHand = new Skeleton(getSkeleton());
                if (offHand.findBone("fire-bone") != null)
                    offHandMuzzle = new BonePointData(offHand.findBone("fire-bone"),
                        ((PlayerAnimationComponentData)getAttachedTo()).getSecondaryBonePointData());
                offHandState = new AnimationState(getState().getData());
                offHandAttachment = new SkeletonAttachment("paired-sidearm");
                offHandAttachment.setSkeleton(offHand);
                offHandSlot.setAttachment(offHandAttachment);
                Skeleton actor = getAttachedTo().getSkeleton();
                leftMagazine = new MagazineMotion(getSkeleton(), actor, "left");
                rightMagazine = new MagazineMotion(offHand, actor, "right");
            }
        }
        return handled;
    }

    @Override
    protected void deselected()
    {
        if (offHandSlot != null && offHandSlot.getAttachment() == offHandAttachment)
            offHandSlot.setAttachment(null);
        if (leftMagazine != null) leftMagazine.release();
        if (rightMagazine != null) rightMagazine.release();
        leftMagazine = rightMagazine = null;
        offHandMuzzle = null;
        offHand = null;
        offHandSlot = null;
        offHandState = null;
        offHandAttachment = null;
        super.deselected();
    }

    public boolean hasOffHand() { return offHand != null; }

    public Skeleton actionSkeleton(boolean right)
    {
        return right && offHand != null ? offHand : getSkeleton();
    }

    public AnimationState actionState(boolean right)
    {
        return right && offHandState != null ? offHandState : getState();
    }

    public BonePointData actionOrigin(boolean right)
    {
        return right && offHand != null ? ((PlayerAnimationComponentData)getAttachedTo()).getSecondaryBonePointData() : getInstrumentLaunch();
    }

    public void animateHand(boolean right, String action, float duration)
    {
        if (weaponData == null || !weaponData.getWeapon().isPaired()) return;
        Animation animation = getSkeleton().getData().findAnimation("pair-" + action);
        AnimationState state = right ? offHandState : getState();
        if (animation == null || state == null) return;
        AnimationState.TrackEntry track = state.setAnimation(1, animation, false);
        if (duration > 0) track.setTimeScale(animation.getDuration() / duration);
    }

    @Override
    public void update(float dt)
    {
        super.update(dt);
        if (offHand != null)
        {
            for (int i = 0; i < getSkeleton().getSlots().size; i++)
                offHand.getSlots().get(i).setAttachment(getSkeleton().getSlots().get(i).getAttachment());
            offHandState.update(dt);
            offHandState.apply(offHand);
            leftMagazine.apply();
            rightMagazine.apply();
        }
    }

    @Override
    public void render(Batch batch, RenderContext context)
    {
        super.render(batch, context);
    }

    @Override
    public float getX()
    {
        return launchPointData.getX();
    }

    @Override
    public float getY() {
        return launchPointData.getY();
    }

    @Override
    public float getAngle()
    {
        return launchPointData.getAngle();
    }

    @Override
    public boolean getFlipX()
    {
        return launchPointData.getFlipX();
    }

    public Array<String> getSuppressedAttachments()
    {
        return suppressedAttachments;
    }

    public void suppressAttachments(Array<String> suppress)
    {
        this.suppressedAttachments = suppress;
    }
}
