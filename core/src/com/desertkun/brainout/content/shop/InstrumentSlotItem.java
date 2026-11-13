package com.desertkun.brainout.content.shop;

import com.desertkun.brainout.content.bullet.Bullet;
import com.desertkun.brainout.content.instrument.Weapon;
import com.badlogic.gdx.assets.AssetManager;
import com.badlogic.gdx.utils.Array;
import com.badlogic.gdx.utils.Json;
import com.badlogic.gdx.utils.JsonValue;
import com.badlogic.gdx.utils.ObjectMap;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.Constants;
import com.desertkun.brainout.components.PlayerOwnerComponent;
import com.desertkun.brainout.content.Content;
import com.desertkun.brainout.content.Layout;
import com.desertkun.brainout.content.Skin;
import com.desertkun.brainout.content.consumable.impl.InstrumentConsumableItem;
import com.desertkun.brainout.content.instrument.Instrument;
import com.desertkun.brainout.content.upgrades.Upgrade;
import com.desertkun.brainout.content.upgrades.UpgradeChain;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.components.DurabilityComponentData;
import com.desertkun.brainout.data.instrument.InstrumentData;
import com.desertkun.brainout.data.instrument.InstrumentInfo;
import com.desertkun.brainout.data.interfaces.WithBadge;
import com.desertkun.brainout.online.UserProfile;

import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;

@Reflect("content.shop.InstrumentSlotItem")
public class InstrumentSlotItem extends ConsumableSlotItem implements WithBadge
{
    private Instrument instrumentContent;
    private Array<Skin> skins;
    private Skin defaultSkin;
    private int amount;
    private ObjectMap<String, Array<Upgrade>> upgrades;

    private ObjectMap<String, Array<String>> upgradeSlotNames;

    public InstrumentSlotItem()
    {
        this.upgrades = new ObjectMap<>();
        this.upgradeSlotNames = new ObjectMap<>();
        this.skins = new Array<>();
        this.defaultSkin = null;
        this.amount = 1;
    }

    /** The title of the weapon these upgrades make: a selected conversion is named after its model. */
    public String getDisplayTitle(ObjectMap<String, Upgrade> selected)
    {
        Upgrade conversion = selected == null ? null : selected.get("conversion");
        if (conversion != null && conversion.getConversion() != null && upgrades.containsKey("conversion") &&
            upgrades.get("conversion").contains(conversion, true) && conversion.getTitle().isValid())
            return conversion.getTitle().get();
        return getTitle().get();
    }

    public class InstrumentSelection extends ConsumableSelection
    {
        private InstrumentInfo info;

        public InstrumentSelection()
        {
            info = new InstrumentInfo();

            info.instrument = instrumentContent;
            info.skin = defaultSkin;
        }

        public InstrumentInfo getInfo()
        {
            return info;
        }

        @Override
        public void init(UserProfile userProfile)
        {
            info.upgrades.clear();
            for (String slot : upgrades.keys())
            {
                String key = getKey(slot);
                String keys = userProfile.getSelection(key);

                if (keys != null)
                {
                    Upgrade upgrade = ((Upgrade) BrainOut.ContentMgr.get(keys));

                    if (upgrade != null)
                    {
                        getSelectedUpgrades().put(slot, upgrade);
                    }
                }
            }

            String skinSelection = getSkinSelection(userProfile);
            if (skinSelection != null)
            {
                Skin skin = ((Skin) BrainOut.ContentMgr.get(skinSelection));

                if (skins.contains(skin, true))
                {
                    setSkin(skin);
                }
            }
        }

        public void setSkin(Skin skin)
        {
            info.skin = skin;
        }

        public Skin getSelectedSkin()
        {
            return info.skin;
        }

        @Override
        public void apply(ShopCart shopCart, PlayerData playerData, UserProfile profile, Slot slot, Selection selection)
        {
            if (instrumentContent == null)
            {
                return;
            }

            PlayerOwnerComponent ownerComponent = playerData.getComponent(PlayerOwnerComponent.class);

            Instrument equipped = shopCart.equippedInstrument(InstrumentSlotItem.this);
            Upgrade conversion = activeConversion(profile);
            if (conversion != null)
            {
                Instrument target = BrainOut.ContentMgr.get(conversion.getConversion(), Instrument.class);
                if (target != null) equipped = target;
            }
            InstrumentData instrumentData = equipped.getData(playerData.getDimension());

            DurabilityComponentData dcd = instrumentData.getComponentWithSubclass(DurabilityComponentData.class);

            if (dcd != null)
            {
                if (profile != null)
                {
                    float d = profile.getStats().get(instrumentContent.getDurabilityStat(),
                            dcd.getDurability());
                    dcd.setDurability(d);
                }
            }

            instrumentData.secondSpecial = "slot-special-extra".equals(slot.getID());
            instrumentData.setSkin(conversion == null || equipped == instrumentContent ? info.skin : equipped.getDefaultSkin());

            if (profile != null)
            {
                if (info.skin != getDefaultSkin())
                {
                    profile.setSelection(getSkinKey(), info.skin.getID());
                }
                else
                {
                    profile.removeSelection(getSkinKey());
                }

                for (ObjectMap.Entry<String, Array<Upgrade>> upgrade : upgrades)
                {
                    profile.removeSelection(getKey(upgrade.key));
                }
            }

            for (ObjectMap.Entry<String, Upgrade> upgradeSlot : info.upgrades)
            {
                Upgrade upgrade = upgradeSlot.value;

                if (upgrade != null && upgrades.containsKey(upgradeSlot.key) && upgrades.get(upgradeSlot.key).contains(upgrade, true) && (profile == null || upgrade.hasItem(profile)))
                {
                    instrumentData.getUpgrades().put(upgradeSlot.key, upgrade);

                    if (profile != null)
                    {
                        profile.setSelection(getKey(upgradeSlot.key), upgrade.getID());
                    }
                }
            }

            ownerComponent.getConsumableContainer().putConsumable(getAmount(),
                    new InstrumentConsumableItem(instrumentData, playerData.getDimension()));

            super.apply(shopCart, playerData, profile, slot, selection);
        }

        /** The selected conversion (weapon family model), if it is one of this item's and owned. */
        private Upgrade activeConversion(UserProfile profile)
        {
            Upgrade conversion = info.upgrades.get("conversion");
            if (conversion != null && conversion.getConversion() != null && upgrades.containsKey("conversion") &&
                upgrades.get("conversion").contains(conversion, true) && (profile == null || conversion.hasItem(profile)))
                return conversion;
            return null;
        }

        /** A conversion to another calibre gets its own ammo instead of the base weapon's. */
        private Upgrade ammoConversion(ItemCargo cargo)
        {
            if (!(cargo.getContent() instanceof Bullet)) return null;
            Upgrade conversion = activeConversion(null);
            return conversion != null && conversion.getConversionAmmo() != null ? conversion : null;
        }

        @Override
        protected Content cargoContent(ItemCargo cargo, ShopCart cart, Slot slot)
        {
            Upgrade conversion = ammoConversion(cargo);
            if (conversion != null)
            {
                Content ammo = BrainOut.ContentMgr.get(conversion.getConversionAmmo());
                if (ammo != null) return ammo;
            }
            return super.cargoContent(cargo, cart, slot);
        }

        @Override
        protected int cargoAmount(ItemCargo cargo, ShopCart cart, Slot slot)
        {
            Upgrade conversion = ammoConversion(cargo);
            if (conversion != null && conversion.getConversionAmmoAmount() > 0)
                return conversion.getConversionAmmoAmount();
            Instrument equipped = cart.equippedInstrument(InstrumentSlotItem.this);
            if (!(cargo.getContent() instanceof Bullet) || !(equipped instanceof Weapon) ||
                !"slot-secondary".equals(slot.getID())) return super.cargoAmount(cargo,cart,slot);
            Weapon weapon = (Weapon)equipped;
            if (weapon.getPrimaryProperties().property(Constants.Properties.BULLET).asContent(Bullet.class) != cargo.getContent())
                return super.cargoAmount(cargo,cart,slot);
            com.desertkun.brainout.content.upgrades.UpgradableProperty capacity =
                new com.desertkun.brainout.content.upgrades.UpgradableProperty(
                    weapon.getPrimaryProperties().property(Constants.Properties.CLIP_SIZE),info.upgrades.values());
            return capacity.asInt() * (weapon.isPaired() ? 6 : 3);
        }

        public ObjectMap<String, Upgrade> getSelectedUpgrades()
        {
            return info.upgrades;
        }

        /** The name of the model this selection is: a selected conversion is named after its model. */
        public String getDisplayTitle()
        {
            return InstrumentSlotItem.this.getDisplayTitle(info.upgrades);
        }

        @Override
        public void write(Json json)
        {
            super.write(json);

            json.writeObjectStart("u");

            for (ObjectMap.Entry<String, Upgrade> selectedUpgrade : info.upgrades)
            {
                json.writeValue(selectedUpgrade.key,
                    selectedUpgrade.value != null ? selectedUpgrade.value.getID() : -1);
            }

            json.writeObjectEnd();

            json.writeValue("s", getSelectedSkin().getID());
        }

        @Override
        public void read(Json json, JsonValue jsonData)
        {
            super.read(json, jsonData);

            info.upgrades.clear();

            if (jsonData.has("u"))
            {
                JsonValue u = jsonData.get("u");

                if (u.isObject())
                {
                    for (JsonValue selectedUpgrade: u)
                    {
                        String id = selectedUpgrade.asString();
                        Upgrade upgrade = id != null ? BrainOut.ContentMgr.get(id, Upgrade.class) : null;

                        if (upgrade != null)
                        {
                            info.upgrades.put(selectedUpgrade.name(), upgrade);
                        }
                    }
                }
            }

            if (jsonData.has("s"))
            {
                String skinId = jsonData.getString("s");
                Skin skin = BrainOut.ContentMgr.get(skinId, Skin.class);
                setSkin(skin != null ? skin : getDefaultSkin());
            }
        }

        @Override
        public void saveSelection(UserProfile profile, Selection selection, String layout)
        {
            super.saveSelection(profile, selection, layout);

            if (profile != null)
            {
                if (info.skin != getDefaultSkin())
                {
                    profile.setSelection(getSkinKey(), info.skin.getID());
                }
                else
                {
                    profile.removeSelection(getSkinKey());
                }

                for (ObjectMap.Entry<String, Array<Upgrade>> upgrade : upgrades)
                {
                    profile.removeSelection(getKey(upgrade.key));
                }
            }

            for (ObjectMap.Entry<String, Upgrade> upgradeSlot : info.upgrades)
            {
                Upgrade upgrade = upgradeSlot.value;

                if (upgrade != null && upgrades.containsKey(upgradeSlot.key) && upgrades.get(upgradeSlot.key).contains(upgrade, true) && (profile == null || upgrade.hasItem(profile)))
                {
                    if (profile != null)
                    {
                        profile.setSelection(getKey(upgradeSlot.key), upgrade.getID());
                    }
                }
            }
        }

        public String getKey(String slot)
        {
            return getItem().getID() + "-upgrade-" + slot;
        }

        public String getSkinKey()
        {
            return getItem().getID() + "-skin";
        }
    }

    public String getSkinSelection(UserProfile profile)
    {
        return profile.getSelection(getID() + "-skin");
    }

    public String getUpgradeSelection(UserProfile profile, String slot)
    {
        return profile.getSelection(getID() + "-upgrade-" + slot);
    }

    @Override
    public void read(Json json, JsonValue jsonData)
    {
        super.read(json, jsonData);

        JsonValue instrument = jsonData.get("instrument");

        if (instrument != null)
        {
            readInstrumentSection(instrument);
        }
    }

    protected void readInstrumentSection(JsonValue instrument)
    {
        this.instrumentContent = ((Instrument) BrainOut.ContentMgr.get(instrument.getString("id")));

        if (this.instrumentContent != null)
        {
            if (getSlot() == null || !"slot-special-extra".equals(getSlot().getID())) this.instrumentContent.setSlotItem(this);
        }

        if (instrument.has("skin"))
        {
            Skin skin = (Skin) BrainOut.ContentMgr.get(instrument.getString("skin"));
            defaultSkin = skin;
            skins.add(skin);
        }

        else if (instrument.has("skins"))
        {
            if (instrument.get("skins").isArray())
            {
                for (JsonValue value : instrument.get("skins"))
                {
                    Skin skin = (Skin) BrainOut.ContentMgr.get(value.asString());
                    skins.add(skin);
                }
            }
            else
            {
                Skin skin = (Skin) BrainOut.ContentMgr.get(instrument.get("skins").asString());
                skins.add(skin);
            }

            if (instrument.has("defaultSkin"))
            {
                defaultSkin = (Skin) BrainOut.ContentMgr.get(instrument.getString("defaultSkin"));
            }
            else
            {
                defaultSkin = skins.size > 0 ? skins.get(0) : null;
            }
        }

        this.amount = instrument.getInt("amount", this.amount);

        if (instrument.has("upgrades"))
        {
            JsonValue upgradesValue = instrument.get("upgrades");

            if (upgradesValue.isObject())
            {
                for (JsonValue slot: upgradesValue)
                {
                    String slotId = slot.name();
                    Array<String> values = new Array<>();

                    if (slot.isArray())
                    {
                        for (JsonValue u: slot)
                        {
                            values.add(u.asString());
                        }
                    }
                    else
                    {
                        values.add(slot.asString());
                    }

                    upgradeSlotNames.put(slotId, values);
                }
            }
        }
    }

    @Override
    public void completeLoad(AssetManager assetManager)
    {
        super.completeLoad(assetManager);

        for (ObjectMap.Entry<String, Array<String>> entry : upgradeSlotNames)
        {
            Array<Upgrade> slotValues = new Array<>();

            for (String id : entry.value)
            {
                Content content = BrainOut.ContentMgr.get(id);

                if (content instanceof UpgradeChain)
                {
                    if (!((UpgradeChain) content).isEnabled())
                    {
                        continue;
                    }

                    slotValues.clear();
                    slotValues.addAll(((UpgradeChain) content).getUpgrades());
                    break;
                }
                else
                {
                    Upgrade upgrade = BrainOut.ContentMgr.get(id, Upgrade.class);

                    if (upgrade != null)
                    {
                        slotValues.add(upgrade);
                    }
                }
            }

            upgrades.put(entry.key, slotValues);
        }
    }

    @Override
    public InstrumentSelection getSelection()
    {
        return new InstrumentSelection();
    }

    public ObjectMap<String, Array<Upgrade>> getUpgrades()
    {
        return upgrades;
    }

    public Instrument getInstrument()
    {
        return instrumentContent;
    }

    public Array<Skin> getSkins()
    {
        return skins;
    }

    public Skin getDefaultSkin()
    {
        return defaultSkin;
    }

    public int getAmount()
    {
        return amount;
    }

    @Override
    public boolean hasBadge(UserProfile profile, Involve involve)
    {
        if (!hasItem(profile))
        {
            return false;
        }

        switch (involve)
        {
            case withChild:
            {
                if (super.hasBadge(profile, involve))
                {
                    return true;
                }

                for (ObjectMap.Entry<String, Array<Upgrade>> entry : upgrades)
                {
                    for (Upgrade upgrade : entry.value)
                    {
                        if (upgrade.hasBadge(profile, Involve.itemOnly))
                        {
                            return true;
                        }
                    }
                }

                for (Skin skin : skins)
                {
                    if (skin == null)
                        continue;

                    if (skin.hasBadge(profile, Involve.itemOnly))
                    {
                        return true;
                    }
                }

                break;
            }
            case childOnly:
            {
                for (ObjectMap.Entry<String, Array<Upgrade>> entry : upgrades)
                {
                    for (Upgrade upgrade : entry.value)
                    {
                        if (upgrade.hasBadge(profile, Involve.withChild))
                        {
                            return true;
                        }
                    }
                }

                for (Skin skin : skins)
                {
                    if (skin == null)
                        continue;

                    if (skin.hasBadge(profile, Involve.withChild))
                    {
                        return true;
                    }
                }

                return false;
            }
        }

        return super.hasBadge(profile, involve);
    }
}
