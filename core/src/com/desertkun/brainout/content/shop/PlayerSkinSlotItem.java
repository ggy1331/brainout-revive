package com.desertkun.brainout.content.shop;

import com.badlogic.gdx.assets.AssetManager;
import com.badlogic.gdx.utils.Json;
import com.badlogic.gdx.utils.JsonValue;
import com.badlogic.gdx.utils.ObjectMap;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.components.PlayerOwnerComponent;
import com.desertkun.brainout.content.PlayerSkin;
import com.desertkun.brainout.content.active.Player;
import com.desertkun.brainout.content.bullet.Bullet;
import com.desertkun.brainout.content.instrument.Instrument;
import com.desertkun.brainout.content.instrument.Weapon;
import com.desertkun.brainout.content.upgrades.Upgrade;
import com.desertkun.brainout.content.Layout;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.components.PlayerAnimationComponentData;
import com.desertkun.brainout.online.UserProfile;
import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;

@Reflect("content.shop.PlayerSkinSlotItem")
public class PlayerSkinSlotItem extends ConsumableSlotItem
{
    private PlayerSkin skin;

    public static final String[] PART_NAMES = {"legs", "torso", "head"};

    public class PlayerSkinSlotSelection extends ConsumableSelection
    {
        // skins for the parts legs / torso / head; null = this item's skin
        private final PlayerSkinSlotItem[] parts = new PlayerSkinSlotItem[3];

        public PlayerSkinSlotItem getItem()
        {
            return ((PlayerSkinSlotItem) super.getItem());
        }

        /** @param part 0 = legs, 1 = torso with arms, 2 = head */
        public PlayerSkinSlotItem getPart(int part)
        {
            return parts[part] != null ? parts[part] : PlayerSkinSlotItem.this;
        }

        public void setPart(int part, PlayerSkinSlotItem item)
        {
            parts[part] = item == PlayerSkinSlotItem.this ? null : item;
        }

        public boolean hasParts()
        {
            return parts[0] != null || parts[1] != null || parts[2] != null;
        }

        public void copyPartsFrom(PlayerSkinSlotSelection other)
        {
            for (int i = 0; i < parts.length; i++)
            {
                setPart(i, other == null ? null : other.getPart(i));
            }
        }

        @Override
        public void write(Json json)
        {
            super.write(json);

            for (int i = 0; i < parts.length; i++)
            {
                if (parts[i] != null)
                {
                    json.writeValue("part-" + PART_NAMES[i], parts[i].getID());
                }
            }
        }

        @Override
        public void read(Json json, JsonValue jsonData)
        {
            super.read(json, jsonData);

            for (int i = 0; i < parts.length; i++)
            {
                setPart(i, BrainOut.ContentMgr.get(
                    jsonData.getString("part-" + PART_NAMES[i], null), PlayerSkinSlotItem.class));
            }
        }

        @Override
        public void init(UserProfile userProfile, String selectionKey)
        {
            super.init(userProfile, selectionKey);

            for (int i = 0; i < parts.length; i++)
            {
                setPart(i, userProfile == null ? null : BrainOut.ContentMgr.get(
                    userProfile.getSelection(partKey(selectionKey, i)), PlayerSkinSlotItem.class));
            }
        }

        @Override
        public void saveSelection(UserProfile profile, Selection selection, String layout)
        {
            super.saveSelection(profile, selection, layout);

            if (profile == null || slot == null)
                return;

            Layout layout_ = Layout.resolve(layout);
            String key = slot.getID() + (layout_ != null && !layout_.getKey().isEmpty() ? "-" + layout_.getKey() : "");

            PlayerSkinSlotSelection s = selection instanceof PlayerSkinSlotSelection ?
                ((PlayerSkinSlotSelection) selection) : this;

            for (int i = 0; i < parts.length; i++)
            {
                PlayerSkinSlotItem part = s.parts[i];

                if (part != null)
                {
                    profile.setSelection(partKey(key, i), part.getID());
                }
                else
                {
                    profile.removeSelection(partKey(key, i));
                }
            }
        }

        /** Puts this skin with its parts on the player (parts must be owned). */
        public void applySkin(PlayerAnimationComponentData pac, UserProfile profile)
        {
            if (pac == null)
                return;

            pac.setSkin(skin);

            PlayerSkin[] skins = new PlayerSkin[3];

            for (int i = 0; i < parts.length; i++)
            {
                PlayerSkinSlotItem part = parts[i];

                if (part != null && part.getSkin() != null && (profile == null || part.hasItem(profile)))
                {
                    skins[i] = part.getSkin();
                }
            }

            pac.setSkinParts(skins[0], skins[1], skins[2]);
        }

        @Override
        public void apply(ShopCart shopCart, PlayerData playerData, UserProfile profile, Slot slot, Selection selection)
        {
            PlayerAnimationComponentData pac = playerData.getComponent(PlayerAnimationComponentData.class);

            applySkin(pac, profile);

            super.apply(shopCart, playerData, profile, slot, selection);
        }
    }

    /** Profile selection key of a part, e.g. "slot-player-skin-layout-2/legs". */
    public static String partKey(String selectionKey, int part)
    {
        return selectionKey + "/" + PART_NAMES[part];
    }

    @Override
    public void read(Json json, JsonValue jsonData)
    {
        super.read(json, jsonData);

        skin = BrainOut.ContentMgr.get(jsonData.getString("skin"), PlayerSkin.class);
    }

    @Override
    public void loadContent(AssetManager assetManager)
    {
        super.loadContent(assetManager);

        if (skin != null)
        {
            skin.setSlotItem(this);
        }
    }

    public PlayerSkin getSkin()
    {
        return skin;
    }

    @Override
    public Selection getSelection()
    {
        return new PlayerSkinSlotSelection();
    }
}
