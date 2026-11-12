package com.desertkun.brainout.client;

import com.badlogic.gdx.utils.Array;
import com.badlogic.gdx.utils.ObjectMap;
import com.desertkun.brainout.content.SpawnTarget;
import com.desertkun.brainout.content.Team;
import com.desertkun.brainout.content.shop.ShopCart;
import com.desertkun.brainout.content.shop.Slot;
import com.desertkun.brainout.content.shop.SlotItem;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.interfaces.Spawnable;
import com.desertkun.brainout.server.ServerController;

/**
 * Hub training dummy: a bot that stands still on the spot where it was placed, never shoots,
 * carries the loadout (weapon, skin, perk...) its owner had when placing it, takes damage
 * (the shooter sees the damage numbers) and comes back on the same spot after a death.
 * Placed / removed with TrainingDummyMsg (ServerLobbyRealization).
 */
public class TrainingDummyClient extends BotClient
{
    private static final float RESPAWN_DELAY = 2f;

    private final PlayerClient owner;
    private final Array<Slot> slots = new Array<>();
    private final Array<SlotItem.Selection> selections = new Array<>();
    private final Spawnable spot;
    private final boolean faceRight;
    private float respawnIn;

    public TrainingDummyClient(int id, ServerController serverController, PlayerClient owner,
                               final float x, final float y, final String dimension, boolean faceRight)
    {
        super(id, serverController);

        this.owner = owner;
        this.faceRight = faceRight;

        // the selections are immutable once in a cart (a change replaces them), so keeping
        // references is a snapshot of the owner's loadout at the moment of placing
        for (ObjectMap.Entry<Slot, SlotItem.Selection> entry : owner.getShopCart().getItems())
        {
            slots.add(entry.key);
            selections.add(entry.value);
        }

        final TrainingDummyClient self = this;

        spot = new Spawnable()
        {
            @Override public float getSpawnX() { return x; }
            @Override public float getSpawnY() { return y; }
            @Override public Team getTeam() { return self.getTeam(); }
            @Override public float getSpawnRange() { return 0; }
            @Override public String getDimension() { return dimension; }
            @Override public boolean canSpawn(Team teamFor) { return true; }
            @Override public SpawnTarget getTarget() { return SpawnTarget.normal; }
        };
    }

    public PlayerClient getOwner()
    {
        return owner;
    }

    @Override
    public String getName()
    {
        return "Манекен";
    }

    @Override
    protected void setupShopCart()
    {
        ShopCart cart = getShopCart();
        cart.clear();

        for (int i = 0; i < slots.size; i++)
        {
            cart.selectItem(slots.get(i), selections.get(i));
        }
    }

    @Override
    protected void applySelection(ShopCart shopCart, PlayerData playerData, Slot slot, SlotItem.Selection selection)
    {
        // weapon skins / upgrades are resolved against the owner's profile
        selection.apply(shopCart, playerData, owner.getProfile(), slot, selection);
    }

    @Override
    protected void beforeInit(PlayerData playerData)
    {
        super.beforeInit(playerData);

        // no bot brain at all: a dummy never aims, never shoots, never moves
        com.desertkun.brainout.data.components.BotControllerComponentData brain =
            playerData.getComponent(com.desertkun.brainout.data.components.BotControllerComponentData.class);
        if (brain != null)
        {
            playerData.removeComponent(brain);
        }
    }

    private float visibilityTimer;

    @Override
    protected void makeSureIsSpawned(float dt)
    {
        if (isAlive())
        {
            respawnIn = RESPAWN_DELAY;

            // keep telling the players the dummy is visible (see resendVisible)
            visibilityTimer -= dt;
            if (visibilityTimer <= 0)
            {
                visibilityTimer = 1f;
                PlayerData body = getPlayerData();
                com.desertkun.brainout.data.components.ServerTeamVisibilityComponentData vis = body == null ? null :
                    body.getComponent(com.desertkun.brainout.data.components.ServerTeamVisibilityComponentData.class);
                if (vis != null)
                    vis.resendVisible();
            }
            return;
        }

        respawnIn -= dt;
        if (respawnIn > 0)
            return;

        respawnIn = RESPAWN_DELAY;
        spawnNow();
    }

    public void spawnNow()
    {
        if (isAlive())
            return;

        setupShopCart();
        setSpawnAt(spot);
        doSpawn();

        PlayerData playerData = getPlayerData();
        if (playerData != null)
        {
            playerData.setAngle(faceRight ? 0 : 180);
            playerData.setSpawnProtection(0); // can be shot right away
        }
    }
}
