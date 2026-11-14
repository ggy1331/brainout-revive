package com.desertkun.brainout.data.components;

import com.badlogic.gdx.math.MathUtils;
import com.badlogic.gdx.math.Vector2;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.Constants;
import com.desertkun.brainout.content.active.Player;
import com.desertkun.brainout.content.components.base.ContentComponent;
import com.desertkun.brainout.data.Map;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.block.BlockData;
import com.desertkun.brainout.data.components.base.Component;
import com.desertkun.brainout.data.instrument.InstrumentData;
import com.desertkun.brainout.events.AddImpulseEvent;
import com.desertkun.brainout.events.Event;
import com.desertkun.brainout.events.SetSpeedEvent;
import com.desertkun.brainout.utils.AngleDifference;
import com.desertkun.brainout.utils.GroupTimeChanges;
import com.desertkun.brainout.utils.TimedChanges;
import com.esotericsoftware.minlog.Log;

public abstract class PlayerControllerComponentData extends Component<ContentComponent>
{
    private final PlayerData playerData;
    private final GroupTimeChanges groupTimeChanges;
    private TimedChanges aimChanges, sitChanges;

    protected static Vector2 tmp = new Vector2();
    private static final float BOTTOM_CONTACT_MAX = 0.125f;

    private Vector2 moveDirection, originalDirection;
    protected Player.State state;
    private float diveTime, diveCooldown;
    // slide (Ctrl twice while running): a boost, then friction; the sit collider, so it goes under
    // low gaps; ends in a sit (or a run if Shift is held). It can't be cancelled - no jump, dive or
    // standing up out of it (no slide-cancel abuse). A single Ctrl while running sits after the
    // double-tap window.
    private float slideTime, slideCooldown, slideAir, slideTap;
    private float sinceGround = 1;     // the bottom contact flickers while running: "on the ground" = touched it lately
    private boolean slideTapExpired;
    private static final float SLIDE_TAP_WINDOW = 0.25f;
    private static final boolean SLIDE_DEBUG = System.getenv("BRAINOUT_SLIDE_DEBUG") != null;

    private void slideLog(String what)
    {
        if (!SLIDE_DEBUG) return;
        SimplePhysicsComponentData b = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);
        System.out.println("[slide] " + (BrainOut.getInstance().getController().isServer() ? "server " : "client ") +
            what + " state=" + state + " tap=" + slideTap + " cd=" + slideCooldown +
            " vx=" + (b == null ? 0 : b.getSpeed().x) + " sinceGround=" + sinceGround);
    }
    private static final float SLIDE_MIN_SPEED = 7f;     // |vx| needed to start (run is 12)
    private static final float SLIDE_BOOST = 1.12f;      // start speed = run speed x this
    private static final float SLIDE_FRICTION = 13f;     // speed lost per second
    private static final float SLIDE_BRAKE = 22f;        // more while pressing the other way
    private static final float SLIDE_END_SPEED = 4.5f;   // slower than this: the slide is over
    private static final float SLIDE_MAX_TIME = 1.2f;
    private static final float SLIDE_COOLDOWN = 0.8f;
    // Share transition timings with stance_animations.py. Interrupted transitions start
    // at their current speed, rather than snapping back to a stance endpoint.
    private float stanceProgress = 1, stanceDuration = .26f, stanceFromSpeed;
    private boolean upHeld, upConsumed;
    private float hasJumped;
    private float runTapWindow, sprintRemaining;
    private boolean runHeld;
    private float groundSpeed, groundedSinceJump, jumpScale = 1;
    private boolean jumpedBefore;
    private static final float WALK_SCALE = 0.8f;
    private static final float SPRINT_SCALE = 16f / 12f;
    private static final float SPRINT_SECONDS = 1.8f;
    private static final float SPRINT_TAP_WINDOW = 0.35f; // release -> press again within this = sprint
    private static final float HOP_RECOVERY = 0.24f;
    // Ladder inertia: only up/down reversals are slowed down (against fast ladder "strafing");
    // starting and stopping stay almost instant. Vertical speed on a ladder is ~15 × LADDER_SPEED.
    // climbing speed relative to the movement input (v0.13.2: 15 % slower)
    private static final float LADDER_SPEED = 0.85f;
    private static final float LADDER_ACCEL = 200f;    // gain per second: full speed in ~0.08 s
    private static final float LADDER_BRAKE = 260f;    // loss per second when stopping: ~0.06 s
    private static final float LADDER_REVERSE = 75f;   // loss per second when reversing: ~0.2 s to turn
    private static final float LADDER_REVERSE_MEMORY = 0.35f; // a stop shorter than this still counts as a reversal
    private static final float LADDER_REVERSE_TIME = 0.18f;  // slow acceleration after a reversal
    private float ladderSpeed, ladderSinceMove = 1, ladderReverseTimer;
    private int ladderLastDir;
    private boolean wasOnLadder, ladderExitHold;
    // a held "up" after stepping off the top of a ladder doesn't fly the player up, but only for a
    // moment: then it is a normal jump again. At the very top of a ladder (no more ladder over
    // the head) a held "up" jumps off it; the ladder doesn't hold the player for that jump.
    private float ladderExitTimer, ladderJumpTimer;
    private static final float LADDER_EXIT_HOLD = 0.3f;
    // standing on the top of a ladder like on a platform (it used to drop the player back into it)
    private boolean onLadderTop;
    // in the air the player can still steer a little: towards AIR_SHARE of the ground speed
    private static final float AIR_CONTROL = 26f, AIR_SHARE = 0.6f;
    private float bottomContactAccumulator;
    private boolean jumpDirty;
    private Boost boost;

    public enum PositionMode
    {
        normal,
        sit,
        squat,
        crouch
    }

    private class Boost
    {
        private float time;
        private Vector2 velocity;

        public Boost(float time, float x, float y)
        {
            this.time = time;
            this.velocity = new Vector2(x, y);
        }

        private boolean update(float dt)
        {
            time -= dt;

            if (time < 0)
                return true;

            /*
            playerData.setPosition(
                playerData.getX() + velocity.x * dt,
                playerData.getY() + velocity.y * dt
            );
            */

            SimplePhysicsComponentData pcd = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

            if (pcd != null)
            {
                pcd.applyForce(velocity);
            }

            return false;
        }
    }
    public PlayerControllerComponentData(final PlayerData playerData,
         ContentComponent contentComponent)
    {
        super(playerData, contentComponent);

        this.playerData = playerData;
        this.hasJumped = 0;
        this.bottomContactAccumulator = 0;

        this.state = Player.State.normal;

        this.groupTimeChanges = new GroupTimeChanges();
        this.moveDirection = new Vector2();
        this.originalDirection = new Vector2();

        this.boost = null;
    }

    @Override
    public void init()
    {
        super.init();

        initChanges();
    }

    private void initChanges()
    {
        PlayerComponentData pcd = getComponentObject().getComponentWithSubclass(PlayerComponentData.class);

        groupTimeChanges.getChild().add(new TimedChanges("prevMousePosition", Constants.Moves.CHANGE_TIME_MOUSE)
        {
            private Vector2 prevMousePosition = new Vector2(pcd.getMousePosition());

            @Override
            public void reset(TimedChanges who)
            {
                prevMousePosition.set(pcd.getMousePosition());
            }

            @Override
            public boolean changesMade()
            {
                return prevMousePosition.dst2(pcd.getMousePosition()) > 4 * 4;
            }

            @Override
            public void sendChanges()
            {
                prevMousePosition.set(pcd.getMousePosition());
                sendPlayerData(true, 0);
            }
        });

        groupTimeChanges.getChild().add(new TimedChanges("angle", Constants.Moves.CHANGE_TIME_MOUSE)
        {
            private float angle = playerData.getAngle();

            @Override
            public void reset(TimedChanges who)
            {
                angle = playerData.getAngle();
            }

            @Override
            public boolean changesMade()
            {
                return AngleDifference.diff(angle, playerData.getAngle()) > 20;
            }

            @Override
            public void sendChanges()
            {
                angle = playerData.getAngle();
                sendPlayerData(false, 1);
            }
        });

        if (BrainOut.getInstance().getController().isServer())
        {
            groupTimeChanges.getChild().add(new TimedChanges("anyway", Constants.Moves.CHANGE_TIME_ANYWAY)
            {
                @Override
                public void reset(TimedChanges who)
                {
                    //
                }

                @Override
                public boolean changesMade()
                {
                    return true;
                }

                @Override
                public void sendChanges()
                {
                    sendPlayerData(false, 2);
                }
            });
        }

        groupTimeChanges.getChild().add(new TimedChanges("anyway_slow", Constants.Moves.CHANGE_TIME_ANYWAY_SLOW)
        {
            @Override
            public void reset(TimedChanges who)
            {
                //
            }

            @Override
            public boolean changesMade()
            {
                return true;
            }

            @Override
            public void sendChanges()
            {
                sendPlayerData(false, 1);
            }
        });

        groupTimeChanges.getChild().add(new TimedChanges("dimension_change", 0)
        {
            int dimension = playerData.getDimensionId();

            @Override
            public void reset(TimedChanges who)
            {
                dimension = playerData.getDimensionId();
            }

            @Override
            public boolean changesMade()
            {
                return dimension != playerData.getDimensionId();
            }

            @Override
            public void sendChanges()
            {
                sendPlayerData(false, 0);
            }
        });

        groupTimeChanges.getChild().add(new TimedChanges("fixtures", Constants.Moves.CHANGE_TIME_ANYWAY)
        {
            SimplePhysicsComponentData cmp = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

            @Override
            public boolean changesMade()
            {
                return cmp.hasFixture();
            }

            @Override
            public boolean canBeResetByOthers()
            {
                return false;
            }

            @Override
            public void reset(TimedChanges who)
            {
            }

            @Override
            public void sendChanges()
            {
                sendPlayerData(false, 1);
            }
        });

        //commented because now this function done in prevPosX/prevSpeedX and prevPosY/prevSpeedY sections
        /*
        groupTimeChanges.getChild().add(new TimedChanges("zeroSpeed", 0)
        {
            SimplePhysicsComponentData cmp = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

            private boolean zeroSpeed = calc();

            @Override
            public boolean changesMade()
            {
                return zeroSpeed != calc();
            }

            private boolean calc()
            {
                return Math.abs(cmp.getSpeed().x) < 0.02f;
            }

            @Override
            public boolean canBeResetByOthers()
            {
                return false;
            }

            @Override
            public void reset(TimedChanges who)
            {
                zeroSpeed = calc();
            }

            @Override
            public void sendChanges()
            {
                sendPlayerData(false);
            }
        });
        */

        groupTimeChanges.getChild().add(new TimedChanges("prevPosX/prevSpeedX", 0.05f)
        {
            SimplePhysicsComponentData cmp = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

            private float
                    prevPosX = playerData.getX(),
                    prevSpeedX = cmp.getSpeed().x;

            @Override
            public boolean changesMade()
            {
                return Math.abs(prevPosX - playerData.getX()) > Constants.Moves.CHANGE_MOVE_DIST ||
                        Math.abs(prevSpeedX - cmp.getSpeed().x) > Constants.Moves.CHANGE_SPEED_DIST;
            }

            @Override
            public boolean isForceUpdate()
            {
                float currentSpeedX = cmp.getSpeed().x;

                float prevDirection = Math.signum(prevSpeedX);
                float currentDirection = Math.signum(currentSpeedX);

                if (prevDirection != currentDirection)
                {
                    return true;
                }

                return false;
            }

            @Override
            public boolean canBeResetByOthers()
            {
                return false;
            }

            @Override
            public void reset(TimedChanges who)
            {
                prevPosX = playerData.getX();
                prevSpeedX = cmp.getSpeed().x;
            }

            @Override
            public void sendChanges()
            {
                sendPlayerData(false, 1);
            }
        });

        groupTimeChanges.getChild().add(new TimedChanges("prevPosY/prevSpeedY", 0.1f)
        {
            SimplePhysicsComponentData cmp = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

            private float
                    prevPosY = playerData.getY(),
                    prevSpeedY = cmp.getSpeed().y;

            @Override
            public boolean changesMade()
            {
                return Math.abs(prevPosY - playerData.getY()) > Constants.Moves.CHANGE_MOVE_DIST ||
                        Math.abs(prevSpeedY - cmp.getSpeed().y) > Constants.Moves.CHANGE_SPEED_DIST;
            }

            @Override
            public boolean isForceUpdate()
            {
                float currentSpeedY = cmp.getSpeed().y;

                float prevDirection = Math.signum(prevSpeedY);
                float currentDirection = Math.signum(currentSpeedY);

                if (prevDirection != currentDirection)
                {
                    return true;
                }

                return false;
            }

            @Override
            public boolean canBeResetByOthers()
            {
                return false;
            }

            @Override
            public void reset(TimedChanges who)
            {
                prevPosY = playerData.getY();
                prevSpeedY = cmp.getSpeed().y;
            }

            @Override
            public void sendChanges()
            {
                sendPlayerData(false, 1);
            }
        });

        groupTimeChanges.getChild().add(new TimedChanges("onGround")
        {
            SimplePhysicsComponentData cmp = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

            private boolean onGround = cmp.hasContact(SimplePhysicsComponentData.Contact.bottom);

            @Override
            public boolean changesMade()
            {
                return onGround != cmp.hasContact(SimplePhysicsComponentData.Contact.bottom);
            }

            @Override
            public void reset(TimedChanges who)
            {
                onGround = cmp.hasContact(SimplePhysicsComponentData.Contact.bottom);
            }

            @Override
            public void sendChanges()
            {
                sendPlayerData(false, 1);
            }
        });

        groupTimeChanges.getChild().add(new TimedChanges("jump", 0)
        {
            @Override
            public boolean changesMade()
            {
                return jumpDirty;
            }

            @Override
            public void sendChanges()
            {
                sendPlayerData(false, 1);
            }

            @Override
            public void reset(TimedChanges who)
            {
                jumpDirty = false;
            }
        });

        aimChanges = new TimedChanges("aim", 0)
        {
            PlayerComponentData cpc = playerData.getComponentWithSubclass(PlayerComponentData.class);

            private boolean aim = cpc.isAim();

            @Override
            public boolean changesMade()
            {
                return aim != cpc.isAim();
            }

            @Override
            public void sendChanges()
            {
                sendAim(aim);
            }

            @Override
            public void reset(TimedChanges who)
            {
                aim = cpc.isAim();
            }
        };

        sitChanges = new TimedChanges("state", 0)
        {
            PlayerComponentData cpc = playerData.getComponentWithSubclass(PlayerComponentData.class);

            private Player.State state = cpc.getState();

            @Override
            public boolean changesMade()
            {
                return state != cpc.getState();
            }

            @Override
            public void sendChanges()
            {
                sendState(state);
            }

            @Override
            public void reset(TimedChanges who)
            {
                state = cpc.getState();
            }
        };
    }

    protected abstract void sendPlayerData(boolean spectatorsOnly, int priority);
    protected abstract void sendAim(boolean aim);
    protected abstract void sendState(Player.State state);

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

    @Override
    public boolean onEvent(Event event)
    {
        return false;
    }

    public PlayerData getPlayerData()
    {
        return playerData;
    }

    public boolean hasTopContact()
    {
        SimplePhysicsComponentData pcd = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

        if (pcd != null)
        {
            Map map = getMap();
            if (map == null) return false;
            float bottom = playerData.getY() - pcd.getHalfSize().y;
            int firstY = MathUtils.floor(playerData.getY() + pcd.getHalfSize().y + 0.01f);
            int lastY = MathUtils.floor(bottom + playerData.getPlayer().getState(Player.State.normal).height - 0.01f);
            int left = MathUtils.floor(playerData.getX() - pcd.getHalfSize().x + 0.01f);
            int right = MathUtils.floor(playerData.getX() + pcd.getHalfSize().x - 0.01f);
            for (int y = firstY; y <= lastY; y++)
            {
                for (int x = left; x <= right; x++)
                {
                    BlockData block = map.getBlockAt(x, y, Constants.Layers.BLOCK_LAYER_FOREGROUND);
                    if (block != null && block.isConcrete()) return true;
                }
            }
        }

        return false;
    }

    public boolean hasBottomContact()
    {
        SimplePhysicsComponentData pcd = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

        return pcd != null && pcd.hasContact(SimplePhysicsComponentData.Contact.bottom);
    }

    protected boolean startTacticalRun()
    {
        if (isWounded() || !playerData.canRun() ||
            !"player-fast".equals(playerData.getPlayer().getID())) return false;
        InstrumentData held = playerData.getCurrentInstrument();
        if (held instanceof com.desertkun.brainout.data.instrument.WeaponData &&
            ((com.desertkun.brainout.data.instrument.WeaponData)held).getWeapon().isPaired()) return false;
        if (weaponBusyForSprint()) return false;
        sprintRemaining = SPRINT_SECONDS;

        return true;
    }

    /**
     * Shooting or reloading (incl. chambering) the held weapon: the tactical sprint stops and
     * can't start. Only the local player's client knows its weapon state (MyPlayerComponent);
     * the resulting state change reaches the server as usual (sendState).
     */
    protected boolean weaponBusyForSprint()
    {
        return false;
    }

    protected void setRun(boolean pressed)
    {
        if (pressed && runHeld) return;
        runHeld = pressed;
        if (state == Player.State.dive || state == Player.State.slide) return;
        if (isWounded()) return;
        if (!pressed)
        {
            // Double tap = release and press again within SPRINT_TAP_WINDOW. The window opens
            // on release (not on press), so it doesn't matter how long the key was held before.
            // Releasing an active sprint opens no window: a sprint can't be chained by re-tapping.
            runTapWindow = state == Player.State.tacticalRun ? 0 : SPRINT_TAP_WINDOW;
            if (state == Player.State.run || state == Player.State.tacticalRun) setState(Player.State.normal);
            return;
        }
        if (state == Player.State.sit || state == Player.State.squat || isCrouching())
        {
            setPositionMode(PositionMode.normal);
            if (state != Player.State.normal) return;
        }
        if (!playerData.canRun()) return;
        boolean sprint = runTapWindow > 0 && startTacticalRun();
        runTapWindow = 0;
        setState(sprint ? Player.State.tacticalRun : Player.State.run);
    }

    protected boolean isWounded()
    {
        return playerData.isWounded();
    }

    protected boolean isCrouching()
    {
        return state == Player.State.crawl;
    }

    protected boolean startDive()
    {
        if (isWounded() || diveCooldown > 0 || playerData.getPlayer().isFlying() ||
            BrainOut.PackageMgr.getDefine("crawl", "").equals("disabled")) return false;
        SimplePhysicsComponentData body = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);
        if (body == null) return false;
        boolean grounded = hasBottomContact();
        if (grounded && ((state != Player.State.run && state != Player.State.tacticalRun) ||
            Math.abs(body.getSpeed().x) < 2)) return false;
        if (!grounded && (state == Player.State.crawl || state == Player.State.sit ||
            state == Player.State.squat || state == Player.State.dive)) return false;
        float speed = body.getSpeed().x;
        setState(Player.State.dive);
        diveTime = 0;
        diveCooldown = 1.15f;
        float heading = Math.abs(speed) > 1 ? Math.signum(speed) :
            Math.signum(MathUtils.cosDeg(playerData.getAngle()));
        // a bit farther than before (x1.12 / 8.5 up); from a jump: a dash along the dive
        groundSpeed = heading * (grounded ? Math.abs(speed) * 1.25f : Math.max(Math.abs(speed) + 4.5f, 9f));
        body.getSpeed().set(groundSpeed, grounded ? 9.2f : Math.min(1.5f, body.getSpeed().y + 1.5f));
        return true;
    }

    protected boolean startSlide()
    {
        return false;
    }

    /** The slide is over: a sit, or a run when Shift is held (or a jump) and there is headroom. */
    private void endSlide(boolean jumping)
    {
        slideLog("end t=" + slideTime + " v=" + groundSpeed);
        slideCooldown = SLIDE_COOLDOWN;
        Player.State next = runHeld ? Player.State.run : (jumping ? Player.State.normal : Player.State.sit);
        if (next != Player.State.sit && hasTopContact()) next = Player.State.sit;
        setState(next);
    }

    protected void setPositionMode(PositionMode mode)
    {
        if (isWounded())
            return;

        if (state == Player.State.dive) return;
        if (mode == PositionMode.crouch && startDive()) return;
        if (mode == PositionMode.normal && hasTopContact()) return;
        Player.State next = mode == PositionMode.crouch ? Player.State.crawl :
            mode == PositionMode.sit ? Player.State.sit : mode == PositionMode.squat ? Player.State.squat : Player.State.normal;
        if (mode == PositionMode.crouch && BrainOut.PackageMgr.getDefine("crawl", "").equals("disabled")) return;
        beginStanceTransition(next);

        switch (mode)
        {
            case normal:
            {
                this.state = Player.State.normal;
                break;
            }
            case sit:
            {
                this.state = Player.State.sit;
                break;
            }
            case squat:
            {
                this.state = Player.State.squat;
                break;
            }
            case crouch:
            {
                if (BrainOut.PackageMgr.getDefine("crawl", "").equals("disabled"))
                {
                    return;
                }

                this.state = Player.State.crawl;
                break;
            }
        }



        PlayerComponentData cpc = playerData.getComponentWithSubclass(PlayerComponentData.class);

        if (cpc != null)
        {
            cpc.setState(this.state);
            updateMoveDirection();
        }
    }

    protected boolean isEnabled()
    {
        return true;
    }

    protected boolean applyMoveDirection()
    {
        return true;
    }

    @Override
    public void update(float dt)
    {
        if (!isEnabled())
            return;

        Map map = getMap();

        if (map == null)
            return;

        SimplePhysicsComponentData pcd = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

        boolean hasBottomContact = pcd.hasContact(SimplePhysicsComponentData.Contact.bottom);
        boolean hasFixture = pcd.hasFixture();
        if (ladderJumpTimer > 0)
        {
            ladderJumpTimer -= dt;
            hasFixture = false;
        }
        onLadderTop = standOnLadderTop(map, pcd, hasFixture);
        if (onLadderTop)
        {
            hasFixture = false;
            hasBottomContact = true;
            bottomContactAccumulator = BOTTOM_CONTACT_MAX;
        }

        if (hasBottomContact)
        {
            bottomContactAccumulator = BOTTOM_CONTACT_MAX;
        }
        else
        {
            if (BrainOut.getInstance().getController().isServer())
            {
                if (bottomContactAccumulator > 0)
                {
                    bottomContactAccumulator = Math.max(bottomContactAccumulator - dt, 0);
                }
            }
            else
            {
                bottomContactAccumulator = 0;
            }
        }

        sinceGround = hasBottomContact ? 0 : sinceGround + dt;
        diveCooldown = Math.max(0, diveCooldown - dt);
        slideCooldown = Math.max(0, slideCooldown - dt);
        if (slideTap > 0 && (slideTap -= dt) <= 0)
        {
            // a single Ctrl while running: sit, as before (just after the double-tap window)
            slideTap = 0;
            if (state == Player.State.run || state == Player.State.tacticalRun || state == Player.State.normal)
            {
                slideTapExpired = true;
                setPositionMode(PositionMode.sit);
                slideTapExpired = false;
            }
        }
        stanceProgress = Math.min(1, stanceProgress + dt / stanceDuration);
        runTapWindow = Math.max(0, runTapWindow - dt);
        sprintRemaining = Math.max(0, sprintRemaining - dt);
        if (state == Player.State.tacticalRun && (sprintRemaining == 0 || weaponBusyForSprint()))
            setState(Player.State.run);
        if (!hasFixture)
        {
            if (wasOnLadder && ladderJumpTimer <= 0)
            {
                // leaving a ladder (e.g. over the top): no upward momentum, and the held "up"
                // must not turn into a jump — the player stops on the edge instead of flying up
                if (pcd.getSpeed().y > 0) pcd.getSpeed().y = 0;
                ladderExitHold = moveDirection.y > 0.2f;
                ladderExitTimer = LADDER_EXIT_HOLD;
            }
            ladderSpeed = 0; ladderSinceMove = 1; ladderReverseTimer = 0; // a ladder starts fresh
        }
        wasOnLadder = hasFixture;
        ladderExitTimer = Math.max(0, ladderExitTimer - dt);
        if (ladderExitHold && (moveDirection.y <= 0.2f || ladderExitTimer <= 0)) ladderExitHold = false;
        if (hasBottomContact || hasFixture)
        {
            groundedSinceJump += dt;
            if (groundedSinceJump >= HOP_RECOVERY || hasFixture)
            {
                jumpScale = 1;
                jumpedBefore = false;
            }
        }
        boolean hadBottomContact = bottomContactAccumulator > 0;

        float forceX = 0, forceY = 0;

        if (state == Player.State.dive)
        {
            diveTime += dt;
            if (diveTime >= 0.12f && ((hasBottomContact && pcd.getSpeed().y <= 0) || hasFixture))
            {
                groundSpeed = pcd.getSpeed().x * 0.45f;
                pcd.getSpeed().x = groundSpeed;
                setState(Player.State.crawl);
            }
        }
        else if (state == Player.State.slide)
        {
            slideTime += dt;
            hasJumped = Math.max(hasJumped - dt, 0);
            boolean ended = false;
            if (hasFixture)
            {
                endSlide(false);                                  // onto a ladder
                ended = true;
            }
            else if (hasBottomContact || hadBottomContact || (slideAir += dt) < 0.12f)
            {
                if (hasBottomContact || hadBottomContact) slideAir = 0;  // a frame without contact isn't an edge
                // ran into a wall: the physics stopped us
                if (slideTime > 0.05f && Math.abs(pcd.getSpeed().x) < 1f) groundSpeed = 0;
                float brake = SLIDE_FRICTION + (moveDirection.x * groundSpeed < 0 ? SLIDE_BRAKE : 0);
                groundSpeed = Math.signum(groundSpeed) * Math.max(0, Math.abs(groundSpeed) - brake * dt);
                pcd.getSpeed().x = groundSpeed;
            }
            else
            {
                endSlide(true);                                   // off an edge: falls as usual
                ended = true;
            }
            if (!ended && (Math.abs(groundSpeed) <= SLIDE_END_SPEED || slideTime >= SLIDE_MAX_TIME))
                endSlide(false);
        }
        else if (playerData.getPlayer().isFlying())
        {
            pcd.getSpeed().x = moveDirection.x;
            pcd.getSpeed().y = moveDirection.y;
        }
        else
        {
            if (hadBottomContact || hasFixture || onLadderTop)
            {
                if (hasBottomContact() || hasFixture || onLadderTop)
                {
                    float target = moveDirection.x * horizontalScale();
                    float step = (target == 0 ? 110f : 95f) * dt;
                    groundSpeed += MathUtils.clamp(target - groundSpeed, -step, step);
                    pcd.getSpeed().x = groundSpeed;
                }

                if (hasFixture)
                {
                    // ladder inertia: a reversal brakes slowly, a start / stop is quick
                    float target = moveDirection.y * LADDER_SPEED;
                    int targetDir = target > 0.01f ? 1 : (target < -0.01f ? -1 : 0);
                    // a reversal: against the current motion, or right after moving the other way
                    // (a quick stop-and-go counts too)
                    if (targetDir != 0 && (target * ladderSpeed < 0 ||
                        (targetDir == -ladderLastDir && ladderSinceMove < LADDER_REVERSE_MEMORY)))
                    {
                        ladderReverseTimer = LADDER_REVERSE_TIME;
                    }
                    ladderReverseTimer = Math.max(0, ladderReverseTimer - dt);
                    float rate;
                    if (target * ladderSpeed < 0) rate = LADDER_REVERSE;
                    else if (Math.abs(target) < Math.abs(ladderSpeed)) rate = LADDER_BRAKE;
                    else if (ladderReverseTimer > 0) rate = LADDER_REVERSE;
                    else rate = LADDER_ACCEL;
                    float step = rate * dt;
                    ladderSpeed += MathUtils.clamp(target - ladderSpeed, -step, step);
                    if (Math.abs(ladderSpeed) > 1f)
                    {
                        ladderLastDir = ladderSpeed > 0 ? 1 : -1;
                        ladderSinceMove = 0;
                    }
                    else
                    {
                        ladderSinceMove += dt;
                    }
                    pcd.getSpeed().y = ladderSpeed;
                }
                else
                {
                    if (moveDirection.y > 0.2f && hasJumped <= 0 && !ladderExitHold)
                    {
                        if (onLadderTop) ladderJumpTimer = 0.25f;
                        jump();
                    }
                    else
                    {
                        hasJumped = Math.max(hasJumped - dt, 0);
                    }
                }
            }
            else
            {
                // a little steering in the air: towards a share of the ground speed, never
                // faster than that (a running jump keeps its speed), so a jump against a ledge
                // still carries the player over it
                float target = moveDirection.x * horizontalScale() * AIR_SHARE;
                float vx = pcd.getSpeed().x;
                if (target != 0 && (Math.signum(vx) != Math.signum(target) || Math.abs(vx) < Math.abs(target)))
                {
                    float step = AIR_CONTROL * dt;
                    vx += MathUtils.clamp(target - vx, -step, step);
                    pcd.getSpeed().x = vx;
                    groundSpeed = vx;
                }

                hasJumped = Math.max(hasJumped - dt, 0);
            }
        }

        float pW = 0.1f + pcd.getHalfSize().x, pH = 0.9f - pcd.getHalfSize().y,
                pX = playerData.getX(), pY = playerData.getY();
        float sign = Math.signum(moveDirection.x);
        float blockCheck = sign * pW;

        /*
        if (Math.abs(moveDirection.x) > 0.01f && moveDirection.y >= 0)
        {
            float checkX = pX + blockCheck, checkY = pY + pH;
            BlockData block = map.getBlockAt(checkX, checkY, Constants.Layers.BLOCK_LAYER_FOREGROUND);

            tmp.set(pcd.getSpeed());

            if (block != null && block.isConcrete() &&
                    block.isContact(null, checkX % 1, checkY % 1, tmp, tmp, 0))
            {
                boolean good = true;

                int checks = (int)(pcd.getHalfSize().y * 2.f + 0.1f);
                for (int i = 1; i <= checks; i++)
                {
                    BlockData neighbor = block.getNeightbor(0, i);
                    if (neighbor != null && neighbor.isConcrete())
                    {
                        good = false;
                        break;
                    }
                }

                if (good && boost == null)
                {
                    switch (block.getNeighborsMask())
                    {
                        case 0:
                        case 1:
                        case 2:
                        case 4:
                        case 8:
                        {
                            BlockData bottom = map.getBlockAt(pX, checkY - 1, Constants.Layers.BLOCK_LAYER_FOREGROUND);

                            if (bottom instanceof ConcreteBD)
                            {
                                jump();
                            }
                            break;
                        }
                        default:
                        {
                            //boost(0.25f, sign * 5.0f, 5.0f);
                        }
                    }
                }
            }
        }
        */

        boolean w = isWounded();

        if ((state == Player.State.wounded) != w)
        {
            if (w)
            {
                setState(Player.State.wounded);
            }
            else
            {
                setState(Player.State.normal);
            }
        }

        if (boost != null)
        {
            if (boost.update(dt))
            {
                boost = null;
            }
        }

        BrainOut.EventMgr.sendDelayedEvent(playerData, AddImpulseEvent.obtain(forceX, forceY));

        groupTimeChanges.update(dt);

        if (aimChanges != null)
            aimChanges.update(dt);

        if (sitChanges != null)
            sitChanges.update(dt);
    }

    /**
     * The top of a ladder holds the player like a platform: the feet on the top ladder block
     * (nothing of the ladder above it), not falling, not pressing "down" (that climbs down).
     * The player is put on it and may walk off or jump from it.
     */
    private boolean standOnLadderTop(Map map, SimplePhysicsComponentData pcd, boolean hasFixture)
    {
        if (ladderJumpTimer > 0 || moveDirection.y < -0.2f || pcd.getSpeed().y > 0.5f) return false;
        if (state == Player.State.dive || playerData.getPlayer().isFlying()) return false;
        float x = playerData.getX(), feet = playerData.getY() - pcd.getHalfSize().y;
        BlockData under = map.getBlockAt(x, feet - 0.05f, Constants.Layers.BLOCK_LAYER_FOREGROUND);
        if (under == null || !under.isFixture()) return false;
        float top = MathUtils.floor(feet - 0.05f) + 1;
        BlockData over = map.getBlockAt(x, top + 0.5f, Constants.Layers.BLOCK_LAYER_FOREGROUND);
        if (over != null && over.isFixture()) return false;              // still inside the ladder
        if (feet < top - 0.6f) return false;                             // climbing, not on top yet
        if (pcd.getSpeed().y < 0) pcd.getSpeed().y = 0;
        playerData.setPosition(x, top + pcd.getHalfSize().y);
        return true;
    }

    private void setState(Player.State state)
    {
        beginStanceTransition(state);
        this.state = state;

        PlayerComponentData cpc = playerData.getComponentWithSubclass(PlayerComponentData.class);

        if (cpc != null)
        {
            cpc.setState(this.state);
            updateMoveDirection();
        }
    }

    private void boost(float time, float x, float y)
    {
        this.boost = new Boost(time, x, y);
    }

    private void jump()
    {
        if (isWounded())
            return;

        if (state == Player.State.sit)
            return;

        if (state == Player.State.squat)
            return;

        if (state == Player.State.crawl)
            return;

        if (hasJumped > 0)
            return;

        SimplePhysicsComponentData pcd = playerData.getComponentWithSubclass(SimplePhysicsComponentData.class);

        if (pcd != null)
        {
            float previousScale = jumpScale;
            jumpScale = jumpedBefore ? Math.max(0.55f, jumpScale - 0.15f) : 1;
            jumpedBefore = true;
            groundedSinceJump = 0;
            groundSpeed *= jumpScale / previousScale;
            pcd.getSpeed().x = groundSpeed;
            BrainOut.EventMgr.sendDelayedEvent(playerData,
                SetSpeedEvent.obtain(0, Math.min(playerData.getPlayer().getJumpForce() * 0.9f, 20.4f) * jumpScale, 0, 1)); // a bit higher (was 0.86 / 19.5)

            hasJumped = 0.5f;
            bottomContactAccumulator = BOTTOM_CONTACT_MAX;
            setJumpDirty();
        }
    }

    private void setJumpDirty()
    {
        jumpDirty = true;
    }

    protected void updateMoveDirection()
    {
        PlayerData pl = playerData;

        if (pl.getCurrentState() == null)
            return;

        this.moveDirection.set(originalDirection);
        this.moveDirection.scl(pl.getCurrentState().speed);

        if (pl.getCurrentInstrument() != null)
        {
            InstrumentData current = pl.getCurrentInstrument();
            this.moveDirection.x *= getInstrumentSpeedCoef(current);
        }

        this.moveDirection.x *= pl.getSpeedCoef();
    }

    private static int posture(Player.State value)
    {
        if (value == Player.State.crawl) return 0;
        if (value == Player.State.sit || value == Player.State.squat) return 1;
        if (value == Player.State.normal || value == Player.State.run || value == Player.State.tacticalRun) return 2;
        return -1;
    }

    protected void beginStanceTransition(Player.State next)
    {
        int from = posture(state), to = posture(next);
        if (from == to) return;
        if (from < 0 || to < 0) { stanceProgress = 1; return; }
        float base = playerData.getPlayer().getState(state).speed.x;
        stanceFromSpeed = Math.abs(base * horizontalScale());
        stanceDuration = from + to == 1 ? .47f : from + to == 2 ? .66f : .26f;
        stanceProgress = 0;
    }

    private float horizontalScale()
    {
        float base = Math.abs(playerData.getPlayer().getState(state).speed.x);
        float target = base * stanceScale();
        if (stanceProgress >= 1 || base <= 0) return stanceScale();
        float k = stanceProgress * stanceProgress * (3 - 2 * stanceProgress);
        return (stanceFromSpeed + (target - stanceFromSpeed) * k) / base;
    }

    private float stanceScale()
    {
        if (state == Player.State.normal) return WALK_SCALE * jumpScale;
        if (state == Player.State.run || state == Player.State.tacticalRun)
        {
            boolean backward = originalDirection.x * MathUtils.cosDeg(playerData.getAngle()) < 0;
            if (backward)
            {
                float walk = playerData.getPlayer().getState(Player.State.normal).speed.x * WALK_SCALE;
                float run = playerData.getPlayer().getState(Player.State.run).speed.x;
                return (run > 0 ? (walk + run) / (2 * run) : 1) * jumpScale;
            }
            if (state == Player.State.tacticalRun) return SPRINT_SCALE * jumpScale;
        }
        return jumpScale;
    }

    public Vector2 getMaximumSpeed()
    {
        tmp.set(playerData.getCurrentState().speed);

        if (playerData.getCurrentInstrument() != null)
        {
            InstrumentData current = playerData.getCurrentInstrument();
            tmp.x *= getInstrumentSpeedCoef(current);
        }

        tmp.x *= playerData.getSpeedCoef() * horizontalScale();
        if (state == Player.State.slide) tmp.x = Math.max(tmp.x, Math.abs(groundSpeed));

        return tmp;
    }

    protected float getInstrumentSpeedCoef(InstrumentData current)
    {
        return current.getInstrument().getSpeedCoef();
    }

    public void setMoveDirection(float moveX, float moveY)
    {
        this.originalDirection.set(
            MathUtils.clamp(moveX, -1.0f, 1.0f),
            MathUtils.clamp(moveY, -1.0f, 1.0f));

        updateMoveDirection();
    }

    public void setMoveDirection(Vector2 direction)
    {
        boolean pressed = direction.y > .5f;
        if (pressed && !upHeld && !isWounded() &&
            (state == Player.State.crawl || state == Player.State.sit || state == Player.State.squat))
        {
            upConsumed = true;
            if (!hasTopContact()) setPositionMode(state == Player.State.crawl ? PositionMode.sit : PositionMode.normal);
        }
        upHeld = pressed;
        if (!pressed) upConsumed = false;
        // One press raises one stance. Holding W must not immediately jump or stand again.
        this.originalDirection.set(direction.x, upConsumed ? 0 : direction.y);
        updateMoveDirection();
    }

    public Vector2 getOriginalDirection()
    {
        return originalDirection;
    }

    public Vector2 getMoveDirection()
    {
        return moveDirection;
    }
}
