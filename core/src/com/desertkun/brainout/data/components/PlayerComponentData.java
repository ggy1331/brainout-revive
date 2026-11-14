package com.desertkun.brainout.data.components;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.math.MathUtils;
import com.badlogic.gdx.math.Vector2;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.content.active.Player;
import com.desertkun.brainout.content.components.InstrumentAnimationStates;
import com.desertkun.brainout.content.components.PlayerComponent;
import com.desertkun.brainout.content.instrument.Weapon;
import com.desertkun.brainout.data.active.ActiveData;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.block.BlockData;
import com.desertkun.brainout.data.components.base.Component;
import com.desertkun.brainout.data.instrument.InstrumentData;
import com.desertkun.brainout.data.instrument.WeaponData;
import com.desertkun.brainout.data.interfaces.*;
import com.desertkun.brainout.events.*;
import com.esotericsoftware.minlog.Log;
import com.esotericsoftware.spine.Animation;
import com.esotericsoftware.spine.AnimationState;
import com.esotericsoftware.spine.Bone;

import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;

@Reflect("PlayerComponent")
@ReflectAlias("data.components.PlayerComponentData")
public class PlayerComponentData extends Component<PlayerComponent> implements
        Animable, AnimationState.AnimationStateListener
{
    public static final int ANIMATION_BOTTOM = 0;
    public static final int ANIMATION_TOP = 1;

    private enum BottomAnimationState
    {
        stay,
        sit,
        squat,
        moveForward,
        moveBackward,
        runForward,
        runBackward,
        sitForward,
        sitBackward,
        wounded,
        woundedForward,
        woundedBackward,
        fly,
        diving,
        sliding,
        crouch,
        crouchForward,
        crouchBackward,
    }

    private Vector2 lastPosition;
    private Bone handsBone;
    private Bone headBone;
    private float bottomContactAccumulator;

    private PlayerAnimationComponentData animation;
    protected final PlayerData playerData;
    private AimState aim;

    private InstrumentAnimationStates states;

    private InstrumentAnimationStates.State topAnimationState;
    private BottomAnimationState bottomAnimationState;
    private float trigger;
    private float visualHeight = -1;
    private boolean animatedSprint;
    private String sprintClip;
    private float carryBlend, sampleTime, gaitSpeed;
    private Vector2 mousePosition;
    private boolean woundedRight;
    private float woundedTimer;
    private boolean forceDisplayAim = true;

    enum FetchAfter
    {
        none,
        after,
        afterSecondary
    }

    public PlayerComponentData(PlayerData playerData,
                               PlayerComponent contentComponent)
    {
        super(playerData, contentComponent);

        this.playerData = playerData;
        this.aim = AimState.none;
        this.lastPosition = new Vector2();
        this.mousePosition = new Vector2(10, 0);

        this.topAnimationState = InstrumentAnimationStates.State.hold;
        this.bottomAnimationState = BottomAnimationState.stay;
        this.bottomContactAccumulator = 0;

        this.trigger = 0;
    }

    public enum AimState
    {
        none,
        aim
    }

    @Override
    public boolean hasRender()
    {
        return false;
    }

    @Override
    public boolean hasUpdate()
    {
        return true;
    }

    public boolean isAim()
    {
        return aim == AimState.aim;
    }

    public AimState getAim()
    {
        return aim;
    }

    public Player.State getState()
    {
        return playerData.getState();
    }

    public void setState(Player.State state)
    {
        playerData.setState(state);
    }

    @Override
    public void init()
    {
        super.init();

        animation = playerData.getComponent(PlayerAnimationComponentData.class);
        animation.attachTo(this);

        handsBone = animation.getSkeleton().findBone("hands");
        headBone = animation.getSkeleton().findBone("head");

        setBottomAnimation("stay", getStayAnimationTimeScale());

        BrainOut.EventMgr.subscribe(Event.ID.instrumentAction, this);
    }

    @Override
    public void release()
    {
        super.release();

        BrainOut.EventMgr.unsubscribe(Event.ID.instrumentAction, this);
    }

    public void setInstrumentState(InstrumentAnimationStates states)
    {
        this.states = states;

        if (!isPlayingCustomAnimation())
        {
            updateAim();
        }
    }

    private int cylinderCount;

    private void updateHandAnimations(
            InstrumentAnimationStates.State state,
            boolean loop,
            boolean listen)
    {
        updateHandAnimations(state, loop, listen, 0.0f);
    }

    private void resetHandAnimations()
    {
        animation.getState().clearTrack(ANIMATION_TOP);
        animation.getState().clearTrack(2);
        animation.getState().clearTrack(3);
    }

    private void updateHandAnimations(
        InstrumentAnimationStates.State state,
        boolean loop,
        boolean listen,
        float timeToPlay)
    {
        if (states != null)
        {
            String animationName = states.getAnimation(state);
            if (animationName == null && state == InstrumentAnimationStates.State.aimHit)
                animationName = states.getAnimation(InstrumentAnimationStates.State.hit);

            InstrumentData held = playerData.getCurrentInstrument();
            if (held instanceof WeaponData)
            {
                WeaponData weapon = (WeaponData)held;
                boolean reload = state == InstrumentAnimationStates.State.reload || state == InstrumentAnimationStates.State.reloadSecondary;
                boolean cock = state == InstrumentAnimationStates.State.cock || state == InstrumentAnimationStates.State.cockSecondary;
                boolean fetch = state == InstrumentAnimationStates.State.fetch || state == InstrumentAnimationStates.State.fetchSecondary;
                if (reload || cock || fetch)
                {
                    boolean paired = weapon.getWeapon().isPaired();
                    if (paired) animationName = states.getAnimation(reload ? InstrumentAnimationStates.State.reload : fetch ? InstrumentAnimationStates.State.fetch : InstrumentAnimationStates.State.cock);
                    if (reload && weapon.usesLooseCylinder() && cylinderCount > 0)
                        animationName = (weapon.getWeapon().hasGroupEjection() ? "rsh-cylinder-" : "cylinder-") + cylinderCount;
                    if (paired)
                    {
                        boolean right = state == InstrumentAnimationStates.State.reloadSecondary || state == InstrumentAnimationStates.State.cockSecondary || state == InstrumentAnimationStates.State.fetchSecondary;
                        String name = "pair-" + (right ? "right-" : "left-") + animationName;
                        String id = weapon.getWeapon().getID();
                        if (reload && id.startsWith("paired-"))
                        {
                            String fitted = name + "-" + id.substring(7);
                            if (animation.getSkeleton().getData().findAnimation(fitted) != null) name = fitted;
                        }
                        if (animation.getSkeleton().getData().findAnimation(name) != null)
                            animationName = name;
                    }
                }
            }
            if (held instanceof WeaponData && animationName != null && !((WeaponData)held).getWeapon().isPaired())
            {
                String solo = "solo-" + held.getInstrument().getID() + "-" + animationName;
                if (animation.getSkeleton().getData().findAnimation(solo) != null) animationName = solo;
            }
            if (animationName != null)
            {
                switch (state)
                {
                    case addRound:
                    {
                        BrainOut.EventMgr.sendDelayedEvent(playerData.getCurrentInstrument(),
                            InstrumentAnimationActionEvent.obtain(state.toString(), playerData.getLaunchData()));
                        break;
                    }
                    default:
                    {
                        BrainOut.EventMgr.sendDelayedEvent(playerData.getCurrentInstrument(),
                            InstrumentAnimationActionEvent.obtain(state.toString()));
                    }
                }

                Animation anim = animation.getSkeleton().getData().findAnimation(animationName);

                if (anim != null)
                {
                    try
                    {
                        boolean pairedAction = held instanceof WeaponData && ((WeaponData)held).getWeapon().isPaired() &&
                            (state == InstrumentAnimationStates.State.reload || state == InstrumentAnimationStates.State.reloadSecondary ||
                             state == InstrumentAnimationStates.State.fetch || state == InstrumentAnimationStates.State.fetchSecondary);
                        boolean rightHand = state == InstrumentAnimationStates.State.reloadSecondary || state == InstrumentAnimationStates.State.fetchSecondary;
                        AnimationState.TrackEntry animationTop = animation.getState().setAnimation(pairedAction ? (rightHand ? 3 : 2) : ANIMATION_TOP,
                                anim, loop);
                        if (pairedAction)
                        {
                            animationTop.setMixDuration(0);
                            animationTop.setTrackEnd(anim.getDuration());
                        }

                        if (isMeleeEquipped() && (state == InstrumentAnimationStates.State.hit ||
                            state == InstrumentAnimationStates.State.aimHit)) animationTop.setMixDuration(0.025f);
                        if (timeToPlay != 0)
                        {
                            animationTop.setTimeScale(
                                (animationTop.getAnimationEnd() / timeToPlay) /
                                    animation.getContentComponent().getAnimation().getTimeScale()
                            );
                        }
                        else
                        {
                            animationTop.setTimeScale(
                                1.0f / animation.getContentComponent().getAnimation().getTimeScale());
                        }

                        if (pairedAction) return;
                        if (listen)
                        {
                            lastInterruptedTop = null;
                            animationTop.setListener(this);
                        }
                    }
                    catch (NullPointerException | IllegalStateException e)
                    {
                        // just ignore it
                    }
                }
            }
        }

        this.topAnimationState = state;
    }

    @Override
    public boolean onEvent(Event event)
    {
        switch (event.getID())
        {
            case instrumentAction:
            {
                InstrumentActionEvent actionEvent = ((InstrumentActionEvent) event);

                processAction(actionEvent);

                break;
            }
            case setInstrument:
            {
                SetInstrumentEvent ev = ((SetInstrumentEvent) event);
                InstrumentData instrumentData = ev.selected;

                if (instrumentData != null)
                {
                    InstrumentAnimationComponentData iac =
                        instrumentData.getComponentWithSubclass(InstrumentAnimationComponentData.class);

                    if (iac != null)
                    {
                        if (instrumentData != playerData.getCurrentInstrument()) break;
                        if (isMeleeEquipped() && states == iac.getStates() && isPlayingHitAnimation()) break;
                        resetHandAnimations();
                        setInstrumentState(iac.getStates());
                    }
                }

                if (!isPlayingCustomAnimation())
                {
                    updateAim();
                    updateBottomAnimation();
                }

                break;
            }
            case resetInstrument:
            {
                resetHandAnimations();

                break;
            }
        }

        return false;
    }

    private boolean isMeleeEquipped()
    {
        InstrumentData held = playerData.getCurrentInstrument();
        return held != null && held.getInstrument().getSlot() != null &&
            "slot-melee".equals(held.getInstrument().getSlot().getID());
    }

    public void ensureQuickHitPose()
    {
        if (!isMeleeEquipped() || isPlayingHitAnimation() || playerData.isWounded()) return;
        InstrumentAnimationComponentData weapon = playerData.getCurrentInstrument().getComponentWithSubclass(InstrumentAnimationComponentData.class);
        if (weapon == null) return;
        states = weapon.getStates();
        updateHandAnimations(InstrumentAnimationStates.State.hit,false,true);
    }

    public boolean isPlayingHitAnimation()
    {
        if (topAnimationState != InstrumentAnimationStates.State.hit &&
            topAnimationState != InstrumentAnimationStates.State.aimHit) return false;
        AnimationState.TrackEntry track = animation.getState().getCurrent(ANIMATION_TOP);
        return track != null && !track.getLoop() && !track.isComplete();
    }

    private void processAction(InstrumentActionEvent action)
    {
        if (isPlayingCustomAnimation())
            return;

        if (isWounded())
            return;

        if (action == null || action.action == null)
            return;

        switch (action.action)
        {
            case hit:
            {
                updateHandAnimations(isAim()
                    ? InstrumentAnimationStates.State.aimHit
                    : InstrumentAnimationStates.State.hit, false, false);

                break;
            }
            case reload:
            {
                cylinderCount = (int)action.data1;
                animateReload(InstrumentAnimationStates.State.reload, action.data0, true);
                break;
            }
            case fetch:
            {
                animateReload(InstrumentAnimationStates.State.fetch, action.data0, true);
                break;
            }
            case reloadSecondary:
            {
                cylinderCount = (int)action.data1;
                animateReload(InstrumentAnimationStates.State.reloadSecondary, action.data0, true);
                break;
            }
            case fetchSecondary:
            {
                animateReload(InstrumentAnimationStates.State.fetchSecondary, action.data0, true);
                break;
            }
            case reloadBoth:
            {
                animateReload(InstrumentAnimationStates.State.reloadBoth, action.data0, true);
                break;
            }
            case cock:
            {
                animateCocking(true, action.data0);

                BrainOut.EventMgr.sendDelayedEvent(playerData.getCurrentInstrument(),
                        InstrumentAnimationActionEvent.obtain("cock"));
                break;
            }
            case reset:
            {
                animateReset(action.data0);
                break;
            }
            case cockSecondary:
            {
                animateCocking(false, action.data0);

                break;
            }
            case buildUp:
            {
                updateHandAnimations(InstrumentAnimationStates.State.buildUp, false, true);

                break;
            }
            case loadMagazineRound:
            {
                setDisplayAim(false);
                animateReload(InstrumentAnimationStates.State.addRound, action.data0, true);
                break;
            }
        }
    }

    public void setDisplayAim(boolean displayAim) {}

    public void playCustomHandAnimation(String animationName, boolean loop)
    {
        if (states != null)
        {
            if (animationName != null)
            {
                Animation anim = animation.getSkeleton().getData().findAnimation(animationName);

                if (anim != null)
                {
                    try
                    {
                        AnimationState.TrackEntry animationTop =
                            animation.getState().setAnimation(ANIMATION_TOP,
                                    anim, loop);

                        lastInterruptedTop = null;
                        animationTop.setListener(this);
                        animationTop.setTimeScale(0.5f);
                    }
                    catch (NullPointerException | IllegalStateException e)
                    {
                        // just ignore it
                    }
                }
            }
        }

        this.topAnimationState = InstrumentAnimationStates.State.custom;
    }

    @Override
    public void update(float dt)
    {
        super.update(dt);

        Player.PlayerState pose = playerData.getCurrentState();
        if (pose != null)
        {
            if (visualHeight < 0 || playerData.isWounded()) visualHeight = pose.height;
            else visualHeight += MathUtils.clamp(pose.height - visualHeight, -3.6f * dt, 3.6f * dt);
        }

        float origAngle = playerData.getAngle();

        origAngle = processPlayerAngle(origAngle);

        while (origAngle > 180) origAngle -= 360;
        while (origAngle < -180) origAngle += 360;

        boolean sectorA = origAngle > 90,
                sectorB = origAngle < -90;
        boolean right = sectorA || sectorB;

        if (right) {
            if (sectorA) {
                origAngle = -origAngle + 180f;
            } else {
                origAngle = -origAngle - 180;
            }
        }

        InstrumentData held = playerData.getCurrentInstrument();
        boolean carrying = getState() == Player.State.tacticalRun && held instanceof WeaponData
            && held.getInstrument().getSlot() != null && !"slot-melee".equals(held.getInstrument().getSlot().getID())
            // both weapon stances: low (hold, cursor close) and high (aim, cursor far)
            && (topAnimationState == InstrumentAnimationStates.State.hold || topAnimationState == InstrumentAnimationStates.State.aim);
        float rate = carrying ? 5.5f : 6.5f;
        carryBlend = MathUtils.clamp(carryBlend + (carrying ? dt : -dt) * rate, 0, 1);
        boolean sidearm = held != null && held.getInstrument().getSlot() != null &&
            "slot-secondary".equals(held.getInstrument().getSlot().getID());
        String wanted = carrying && states != null ? (sidearm ? "sprint-short-" : "sprint-long-") +
            states.getAnimation(InstrumentAnimationStates.State.hold) : null;
        if (!java.util.Objects.equals(wanted,sprintClip))
        {
            Animation clip = wanted == null ? null : animation.getSkeleton().getData().findAnimation(wanted);
            if (clip != null)
            {
                if (animation.getState().getCurrent(4) == null) animation.getState().setEmptyAnimation(4,0);
                AnimationState.TrackEntry arms = animation.getState().setAnimation(4,clip,true);
                arms.setMixDuration(0.13f);
                arms.setTimeScale(1 / animation.getContentComponent().getAnimation().getTimeScale());
            }
            else if (sprintClip != null)
                animation.getState().setEmptyAnimation(4,0.12f);
            sprintClip = wanted;
        }
        float weight = carryBlend * carryBlend * (3 - 2 * carryBlend);
        if (isWounded())
        {
            if (handsBone != null)
                handsBone.setRotation(0);

            if (woundedRight != right)
            {
                woundedTimer += dt;

                if (woundedTimer > 1.0f)
                {
                    woundedRight = right;
                    woundedTimer = 0;

                    animation.getSkeleton().setFlipX(right);
                }
            }
            else
            {
                if (headBone != null)
                    headBone.setRotation(MathUtils.clamp(origAngle, -90, 0));

                woundedTimer = 0;
            }
        }
        else
        {
            if (isCrouching())
            {
                float c = MathUtils.clamp(origAngle, -90, 20);

                if (handsBone != null)
                    handsBone.setRotation(c);

                if (headBone != null)
                    headBone.setRotation(c);
            }
            else
            {
                if (handsBone != null)
                    handsBone.setRotation(origAngle * (1 - weight));

                if (headBone != null)
                    headBone.setRotation(origAngle);
            }

            animation.getSkeleton().setFlipX(right);
        }

        // update moving animation
        BottomAnimationState newState;

        SimplePhysicsComponentData phy = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

        if (phy == null)
            return;

        boolean hasBottomContact = phy.hasContact(SimplePhysicsComponentData.Contact.bottom);
        boolean hasFixture = phy.hasFixture();

        if (hasBottomContact)
        {
            bottomContactAccumulator = 0.1f;
        }
        else
        {
            bottomContactAccumulator -= dt;
        }

        hasBottomContact = bottomContactAccumulator > 0;

        sampleTime += dt;
        trigger -= dt;

        if (trigger < 0)
        {
            float distance = Math.abs(lastPosition.x - getX());
            float speed = distance / Math.max(sampleTime, 0.001f);
            sampleTime = 0;
            gaitSpeed = MathUtils.lerp(gaitSpeed, speed, 0.6f);
            if (getState() == Player.State.dive)
                newState = BottomAnimationState.diving;
            else if (getState() == Player.State.slide)
                newState = BottomAnimationState.sliding;
            else if (!hasBottomContact && !hasFixture && !playerData.isWounded())
            {
                newState = BottomAnimationState.fly;
            }
            else if (distance > 0.012f)
            {
                if (hasBottomContact || hasFixture)
                {
                    switch (getState())
                    {
                        case sit:
                        {
                            if (getX() > lastPosition.x != getFlipX())
                            {
                                newState = BottomAnimationState.sitForward;
                            }
                            else
                            {
                                newState = BottomAnimationState.sitBackward;
                            }

                            break;
                        }
                        case crawl:
                        {
                            if (getX() > lastPosition.x != getFlipX())
                            {
                                newState = BottomAnimationState.crouchForward;
                            }
                            else
                            {
                                newState = BottomAnimationState.crouchBackward;
                            }

                            break;
                        }
                        case wounded:
                        {
                            if (getX() > lastPosition.x != getFlipX())
                            {
                                newState = BottomAnimationState.woundedForward;
                            }
                            else
                            {
                                newState = BottomAnimationState.woundedBackward;
                            }

                            break;
                        }
                        case tacticalRun:
                        case run:
                        {
                            if (getX() > lastPosition.x != getFlipX())
                            {
                                newState = BottomAnimationState.runForward;
                            }
                            else
                            {
                                newState = BottomAnimationState.runBackward;
                            }

                            break;
                        }
                        case normal:
                        default:
                        {
                            if (getX() > lastPosition.x != getFlipX())
                            {
                                newState = BottomAnimationState.moveForward;
                            }
                            else
                            {
                                newState = BottomAnimationState.moveBackward;
                            }

                            break;
                        }
                    }
                }
                else
                {

                    switch (getState())
                    {
                        case wounded:
                        {
                            newState = BottomAnimationState.wounded;

                            break;
                        }

                        default:
                        {
                            newState = BottomAnimationState.fly;
                        }
                    }
                }
            }
            else
            {
                switch (getState())
                {
                    case sit:
                    {
                        newState = BottomAnimationState.sit;

                        break;
                    }
                    case squat:
                    {
                        newState = BottomAnimationState.squat;

                        break;
                    }
                    case crawl:
                    {
                        newState = BottomAnimationState.crouch;

                        break;
                    }
                    case wounded:
                    {
                        newState = BottomAnimationState.wounded;

                        break;
                    }
                    case normal:
                    default:
                    {
                        newState = BottomAnimationState.stay;

                        break;
                    }
                }
            }

            boolean sprint = getState() == Player.State.tacticalRun;
            if (newState != bottomAnimationState || sprint != animatedSprint)
            {
                animatedSprint = sprint;
                bottomAnimationState = newState;

                updateBottomAnimation();
            }

            AnimationState.TrackEntry legs = animation.getState().getCurrent(ANIMATION_BOTTOM);
            if (legs != null && legs.getLoop())
            {
                String gait = legs.getAnimation().getName();
                float nominal = gaitSpeedAtNormalTempo(gait);
                if (nominal > 0)
                    legs.setTimeScale(MathUtils.clamp(gaitSpeed / nominal, 0.12f, 2.6f) * gaitTempo(gait) /
                        animation.getContentComponent().getAnimation().getTimeScale());
            }
            lastPosition.set(getX(), getY());
            trigger = 0.05f;
        }
    }

    protected boolean isWounded()
    {
        return bottomAnimationState == BottomAnimationState.wounded ||
            bottomAnimationState == BottomAnimationState.woundedForward ||
            bottomAnimationState == BottomAnimationState.woundedBackward;
    }

    protected boolean isCrouching()
    {
        return bottomAnimationState == BottomAnimationState.crouch ||
            bottomAnimationState == BottomAnimationState.crouchBackward ||
            bottomAnimationState == BottomAnimationState.crouchForward;
    }

    protected float processPlayerAngle(float origAngle)
    {
        return origAngle;
    }

    private float getStayAnimationTimeScale()
    {
        PlayerAnimationComponentData pl = playerData.getComponent(PlayerAnimationComponentData.class);
        if (pl != null && pl.getContentComponent() != null)
        {
            return pl.getContentComponent().getStayAnimationTimeScale().getValue();
        }

        return 1;
    }

    public void updateBottomAnimation()
    {
        float speedScale = playerData.getSpeedCoef();

        if (playerData.getCurrentInstrument() instanceof WeaponData)
        {
            Weapon weapon = ((WeaponData) playerData.getCurrentInstrument()).getWeapon();
            speedScale *= weapon.getSpeedCoef();
        }

        switch (bottomAnimationState)
        {
            case stay:
            {
                setBottomAnimation("stay", getStayAnimationTimeScale());
                break;
            }
            case sit:
            {
                setBottomAnimation("sit");
                break;
            }
            case squat:
            {
                setBottomAnimation("sit2");
                break;
            }
            case moveForward:
            {
                setBottomAnimation("move-forward", speedScale);
                break;
            }
            case moveBackward:
            {
                setBottomAnimation("move-backward", speedScale);

                break;
            }
            case sitForward:
            {
                setBottomAnimation("sit-forward", speedScale);
                break;
            }
            case sitBackward:
            {
                setBottomAnimation("sit-backward", speedScale);

                break;
            }
            case runForward:
            {
                setBottomAnimation("run-forward", speedScale);
                break;
            }
            case runBackward:
            {
                setBottomAnimation("run-backward", speedScale);

                break;
            }
            case diving:
            {
                AnimationState rig = animation.getState();
                AnimationState.TrackEntry active = rig.getCurrent(ANIMATION_BOTTOM);
                if (active != null && active.getAnimation().getName().equals("dolphin-dive") &&
                    active.getNext() != null) break;
                Animation clip = animation.getSkeleton().getData().findAnimation("dolphin-dive");
                if (clip == null) { setBottomAnimation("crouch"); break; }
                AnimationState.TrackEntry launch = rig.setAnimation(ANIMATION_BOTTOM, clip, false);
                launch.setTimeScale(1f / animation.getContentComponent().getAnimation().getTimeScale());
                launch.setMixDuration(0.05f);
                rig.addAnimation(ANIMATION_BOTTOM,"crouch",true,clip.getDuration()).setMixDuration(0.04f);
                break;
            }
            case sliding:
            {
                AnimationState rig = animation.getState();
                AnimationState.TrackEntry active = rig.getCurrent(ANIMATION_BOTTOM);
                if (active != null && active.getAnimation().getName().startsWith("slide")) break;
                Animation clip = animation.getSkeleton().getData().findAnimation("slide-enter");
                if (clip == null) { setBottomAnimation("sit"); break; }
                AnimationState.TrackEntry enter = rig.setAnimation(ANIMATION_BOTTOM, clip, false);
                enter.setTimeScale(1f / animation.getContentComponent().getAnimation().getTimeScale());
                enter.setMixDuration(0.05f);
                rig.addAnimation(ANIMATION_BOTTOM, "slide", true, clip.getDuration()).setMixDuration(0.03f);
                break;
            }
            case fly:
            {
                setBottomAnimation("fly");

                break;
            }
            case wounded:
            {
                setBottomAnimation("wounded");
                break;
            }
            case woundedForward:
            {
                setBottomAnimation("wounded-forward");
                break;
            }
            case woundedBackward:
            {
                setBottomAnimation("wounded-backward");
                break;
            }
            case crouch:
            {
                setBottomAnimation("crouch");
                break;
            }
            case crouchForward:
            {
                setBottomAnimation("crouch-forward");
                break;
            }
            case crouchBackward:
            {
                setBottomAnimation("crouch-backward");
                break;
            }
        }
    }

    private void setBottomAnimation(String anim)
    {
        setBottomAnimation(anim, 1);
    }

    private float gaitSpeedAtNormalTempo(String name)
    {
        if (!name.endsWith("-forward") && !name.endsWith("-backward")) return 0;
        if (name.startsWith("run-")) return 12f;
        if (name.startsWith("move-")) return 10f;
        if (name.startsWith("sit-")) return 4f;
        if (name.startsWith("crouch-")) return 1.5f;
        if (name.startsWith("wounded-")) return 3f;
        return 0;
    }

    private float gaitTempo(String clip)
    {
        return clip.startsWith("move-") || clip.startsWith("run-") ? .88f : 1f;
    }

    private String stanceForClip(String name)
    {
        if (name.startsWith("crouch")) return "prone";
        if (name.startsWith("sit")) return "sit";
        if (name.equals("stay") || name.startsWith("run-") || name.startsWith("move-")) return "stand";
        return null;
    }

    private void setBottomAnimation(String anim, float timeScale)
    {
        Animation a = animation.getSkeleton().getData().findAnimation(anim);

        if (a != null)
        {
            try
            {
                AnimationState state = animation.getState();
                AnimationState.TrackEntry current = state.getCurrent(ANIMATION_BOTTOM);
                AnimationState.TrackEntry queued = current == null ? null : current.getNext();
                String previous = current == null ? null : stanceForClip(
                    (queued == null ? current : queued).getAnimation().getName());
                String target = stanceForClip(anim);
                float rigSpeed = animation.getContentComponent().getAnimation().getTimeScale();
                float nominal = gaitSpeedAtNormalTempo(anim);
                if (nominal > 0) timeScale = MathUtils.clamp(gaitSpeed / nominal, 0.12f, 2.6f) * gaitTempo(anim);
                AnimationState.TrackEntry next;
                if (queued != null && current.getAnimation().getName().startsWith("stance-") &&
                    target != null && target.equals(previous))
                {
                    next = queued;
                    next.setAnimation(a);
                    next.setAnimationEnd(a.getDuration());
                }
                else
                {
                    Animation change = previous == null || target == null || target.equals(previous) ? null :
                        animation.getSkeleton().getData().findAnimation("stance-" + previous + "-" + target);
                    if (change == null)
                    {
                        String oldName = current == null ? "" : current.getAnimation().getName();
                        float phase = -1;
                        if (nominal > 0 && gaitSpeedAtNormalTempo(oldName) > 0 &&
                            current.getAnimationEnd() > 0)
                        {
                            phase = current.getAnimationTime() / current.getAnimationEnd();
                            if (oldName.endsWith("-forward") != anim.endsWith("-forward")) phase = 1 - phase;
                        }
                        next = state.setAnimation(ANIMATION_BOTTOM, a, true);
                        if (current != null) next.setMixDuration(0.14f);
                        if (phase >= 0)
                        {
                            float t = phase * a.getDuration();
                            next.setTrackTime(t);
                            next.setAnimationLast(t);
                        }
                    }
                    else
                    {
                        AnimationState.TrackEntry transition = state.setAnimation(ANIMATION_BOTTOM, change, false);
                        transition.setMixDuration(0.06f);
                        transition.setTimeScale(1 / rigSpeed);
                        next = state.addAnimation(ANIMATION_BOTTOM, a, true, change.getDuration());
                        next.setMixDuration(0.08f);
                    }
                }
                next.setEventThreshold(0);
                next.setTimeScale(timeScale / rigSpeed);
            }
            catch (NullPointerException | IllegalStateException | ArrayIndexOutOfBoundsException e)
            {
                // just ignore it
            }
        }
    }

    @Override
    public float getX()
    {
        return playerData.getX();
    }

    @Override
    public float getY()
    {
        Player.PlayerState pose = playerData.getCurrentState();
        float offset = pose == null || visualHeight < 0 ? 0 : (visualHeight - pose.height) * 0.5f;
        return playerData.getY() + offset + 0.16f;
    }

    @Override
    public float getAngle()
    {
        return 0; // don't want to consumableContainer is rotate
    }

    public boolean getFlipX()
    {
        return animation.getSkeleton().getFlipX();
    }

    public void setAim(boolean aim)
    {
        if (topAnimationState == InstrumentAnimationStates.State.reload ||
            topAnimationState == InstrumentAnimationStates.State.reloadSecondary ||
            topAnimationState == InstrumentAnimationStates.State.fetchSecondary ||
            topAnimationState == InstrumentAnimationStates.State.fetch ||
            topAnimationState == InstrumentAnimationStates.State.addRound ||
            topAnimationState == InstrumentAnimationStates.State.custom)
        {
            return;
        }

        if (!canSetAim())
        {
            return;
        }

        AimState toSet;
        if (aim)
        {
            toSet = AimState.aim;
        }
        else
        {
            toSet = AimState.none;
        }

        if (this.aim != toSet)
        {
            this.aim = toSet;
            updateAim();
        }
    }

    protected boolean canSetAim()
    {
        return true;
    }

    public void setForceDisplayAim(boolean forceDisplayAim)
    {
        this.forceDisplayAim = forceDisplayAim;
    }

    public void updateAim()
    {
        if (isMeleeEquipped() && isPlayingHitAnimation()) return;
        if (animation != null && (topAnimationState == InstrumentAnimationStates.State.reload ||
            topAnimationState == InstrumentAnimationStates.State.reloadSecondary))
        {
            AnimationState.TrackEntry current = animation.getState().getCurrent(ANIMATION_TOP);
            if (current != null && !current.isComplete() && !isWounded()) return;
        }
        setDisplayAim(forceDisplayAim);

        if (isWounded())
        {
            resetHandAnimations();
        }
        else
        {
            if (isPlayingCustomAnimation())
            {
                return;
            }

            switch (getAim())
            {
                case aim:
                {
                    updateHandAnimations(InstrumentAnimationStates.State.aim, true, false);
                    break;
                }
                case none:
                {
                    updateHandAnimations(InstrumentAnimationStates.State.hold, true, false);
                }
            }
        }
    }

    private void animateReload(InstrumentAnimationStates.State state, float time, boolean listen)
    {
        if (isPlayingCustomAnimation())
            return;

        if (isWounded())
            return;

        updateHandAnimations(state, false, listen, time);
    }

    private void animateCocking(boolean primary, float time)
    {
        if (isPlayingCustomAnimation())
        {
            return;
        }

        if (isWounded())
            return;

        InstrumentData held = playerData.getCurrentInstrument();
        if (held instanceof WeaponData && ((WeaponData)held).getWeapon().isPaired() && animation != null && states != null)
        {
            String name = states.getAnimation(InstrumentAnimationStates.State.cock);
            Animation clip = animation.getSkeleton().getData().findAnimation("pair-" + (primary ? "left-" : "right-") + name);
            if (clip != null)
            {
                // Separate tracks let both thumbs cock their revolvers at the same time.
                AnimationState.TrackEntry track = animation.getState().setAnimation(primary ? 2 : 3, clip, false);
                track.setTrackEnd(clip.getDuration());
                if (time > 0)
                    track.setTimeScale(clip.getDuration() / (time * animation.getContentComponent().getAnimation().getTimeScale()));
                return;
            }
        }

        if (primary)
        {
            updateHandAnimations(InstrumentAnimationStates.State.cock, false, true, time);
        }
        else
        {
            updateHandAnimations(InstrumentAnimationStates.State.cockSecondary, false, true, time);
        }
    }

    private void animateReset(float time)
    {
        if (isPlayingCustomAnimation())
        {
            return;
        }

        if (isWounded())
            return;

        updateHandAnimations(InstrumentAnimationStates.State.reset, false, true, time);
    }

    public boolean isPlayingCustomAnimation()
    {
        return topAnimationState == InstrumentAnimationStates.State.custom;
    }

    @Override
    public void event(AnimationState.TrackEntry entry, com.esotericsoftware.spine.Event event)
    {
        //
    }

    private AnimationState.TrackEntry lastInterruptedTop = null;

    @Override
    public void interrupt(AnimationState.TrackEntry entry)
    {
        switch (entry.getTrackIndex())
        {
            case ANIMATION_TOP:
            {
                lastInterruptedTop = entry;
                break;
            }
        }
    }

    @Override
    public void complete(AnimationState.TrackEntry entry)
    {
        switch (entry.getTrackIndex())
        {
            case ANIMATION_TOP:
            {
                if (lastInterruptedTop == entry || animation.getState().getCurrent(ANIMATION_TOP) != entry)
                {
                    return;
                }

                if (isWounded())
                {
                    resetHandAnimations();
                }
                else
                {
                    switch (topAnimationState)
                    {
                        case aimHit:
                        {
                            updateHandAnimations(InstrumentAnimationStates.State.aim, true, false);

                            break;
                        }
                        case hit:
                        {
                            updateHandAnimations(InstrumentAnimationStates.State.hold, true, false);

                            break;
                        }
                        case fetchSecondary:
                        case reloadSecondary:
                        case reloadBoth:
                        case reload:
                        case fetch:
                        case pull:
                        case buildUp:
                        {
                            updateAim();
                            break;
                        }
                        case custom:
                        {
                            customAnimationComplete();
                            break;
                        }
                    }
                }

                break;
            }
        }
    }

    public void customAnimationComplete()
    {
        resetHandAnimations();
        topAnimationState = InstrumentAnimationStates.State.aim;
        updateAim();

        if (playerData.getCurrentInstrument() != null)
        {
            BrainOut.EventMgr.sendDelayedEvent(playerData.getCurrentInstrument(),
                SetInstrumentEvent.obtain(playerData.getCurrentInstrument(), playerData));
        }
    }

    @Override
    public void start(AnimationState.TrackEntry entry)
    {
        //
    }

    @Override
    public void end(AnimationState.TrackEntry entry)
    {
        //
    }

    @Override
    public void dispose(AnimationState.TrackEntry entry)
    {

    }

    public Vector2 getMousePosition()
    {
        return mousePosition;
    }
}
