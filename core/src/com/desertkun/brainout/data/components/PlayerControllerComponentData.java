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
    private float hasJumped;
    private float runTapWindow, sprintRemaining;
    private boolean runHeld;
    private float groundSpeed, groundedSinceJump, jumpScale = 1;
    private boolean jumpedBefore;
    private static final float WALK_SCALE = 0.8f;
    private static final float SPRINT_SCALE = 1.32f;
    private static final float SPRINT_SECONDS = 1.8f;
    private static final float HOP_RECOVERY = 0.24f;
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
        com.desertkun.brainout.components.PlayerOwnerComponent owner =
            playerData.getComponent(com.desertkun.brainout.components.PlayerOwnerComponent.class);
        if (owner != null && owner.getConsumableContainer().queryRecords(record ->
            record.getItem().getContent() instanceof com.desertkun.brainout.content.instrument.Weapon &&
            ((com.desertkun.brainout.content.instrument.Weapon)record.getItem().getContent()).isPaired()).size > 0)
            return false;
        sprintRemaining = SPRINT_SECONDS;

        return true;
    }

    protected void setRun(boolean pressed)
    {
        if (pressed && runHeld) return;
        runHeld = pressed;
        if (state == Player.State.dive) return;
        if (isWounded()) return;
        if (!pressed)
        {
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
        runTapWindow = sprint ? 0 : 0.42f;
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
        groundSpeed = heading * Math.max(Math.abs(speed) * 1.12f, grounded ? 0 : 7f);
        body.getSpeed().set(groundSpeed, grounded ? 8.5f : Math.min(0, body.getSpeed().y));
        return true;
    }

    protected void setPositionMode(PositionMode mode)
    {
        if (isWounded())
            return;

        if (state == Player.State.dive) return;
        if (mode == PositionMode.crouch && startDive()) return;
        if (mode == PositionMode.normal && hasTopContact()) return;

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

        diveCooldown = Math.max(0, diveCooldown - dt);
        runTapWindow = Math.max(0, runTapWindow - dt);
        sprintRemaining = Math.max(0, sprintRemaining - dt);
        if (state == Player.State.tacticalRun && sprintRemaining == 0) setState(Player.State.run);
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
        else if (playerData.getPlayer().isFlying())
        {
            pcd.getSpeed().x = moveDirection.x;
            pcd.getSpeed().y = moveDirection.y;
        }
        else
        {
            if (hadBottomContact || hasFixture)
            {
                if (hasBottomContact() || hasFixture)
                {
                    float target = moveDirection.x * horizontalScale();
                    float step = (target == 0 ? 110f : 95f) * dt;
                    groundSpeed += MathUtils.clamp(target - groundSpeed, -step, step);
                    pcd.getSpeed().x = groundSpeed;
                }

                if (hasFixture)
                {
                    pcd.getSpeed().y = moveDirection.y;
                }
                else
                {
                    if (moveDirection.y > 0.2f && hasJumped <= 0)
                    {
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
                if (moveDirection.y > 0)
                {
                    forceX = moveDirection.x * horizontalScale() * dt * 0.5f;
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

    private void setState(Player.State state)
    {
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
                SetSpeedEvent.obtain(0, Math.min(playerData.getPlayer().getJumpForce() * 0.86f, 19.5f) * jumpScale, 0, 1));

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

    private float horizontalScale()
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
        if (isCrouching() && direction.y > 0.5f)
        {
            setPositionMode(PositionMode.normal);
            return;
        }

        this.originalDirection.set(direction);

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
