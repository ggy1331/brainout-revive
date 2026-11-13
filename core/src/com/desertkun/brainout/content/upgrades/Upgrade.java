package com.desertkun.brainout.content.upgrades;

import com.badlogic.gdx.utils.Json;
import com.badlogic.gdx.utils.JsonValue;
import com.badlogic.gdx.utils.ObjectMap;
import com.desertkun.brainout.components.PlayerOwnerComponent;
import com.desertkun.brainout.content.ContentLockTree;
import com.desertkun.brainout.content.OwnableContent;
import com.desertkun.brainout.content.components.base.ContentComponent;
import com.desertkun.brainout.content.components.interfaces.UpgradeComponent;
import com.desertkun.brainout.content.shop.Shop;
import com.desertkun.brainout.data.components.base.Component;
import com.desertkun.brainout.data.instrument.InstrumentData;
import com.desertkun.brainout.online.UserProfile;

import com.desertkun.brainout.reflection.Reflect;
import com.desertkun.brainout.reflection.ReflectAlias;

@Reflect("content.upgrades.Upgrade")
public class Upgrade extends OwnableContent
{
    private String conversion;
    // weapon families (launcher/conversions.py): the shop item this conversion replaced (old
    // loadouts that selected it are translated), the base shop item, and the converted weapon's
    // own ammo (another calibre / amount than the base weapon's)
    private String convertsFrom, conversionBase, ammo;
    private int ammoAmount;

    public String getConversion() { return conversion; }
    public String getConvertsFrom() { return convertsFrom; }
    public String getConversionBase() { return conversionBase; }
    public String getConversionAmmo() { return ammo; }
    public int getConversionAmmoAmount() { return ammoAmount; }

    private enum UpgradeKind
    {
        add,
        multiply,
        set
    }

    public class UpgradeProperty
    {
        private UpgradeKind kind;
        private String value;

        public void set(String value)
        {
            char kind = value.charAt(0);

            this.kind = UpgradeKind.add;
            this.value = value.substring(1);

            switch (kind)
            {
                case '=': this.kind = UpgradeKind.set; break;
                case '+': this.kind = UpgradeKind.add; break;
                case '-': this.kind = UpgradeKind.add; this.value = "-" + this.value; break;
                case '*': this.kind = UpgradeKind.multiply; break;
            }
        }

        public float applyFloat(float in)
        {
            return Float.valueOf(apply(String.valueOf(in)));
        }

        public String apply(String in)
        {
            switch (kind)
            {
                case set:
                {
                    return value;
                }

                case multiply:
                {
                    try
                    {
                        float a = Float.valueOf(in);
                        float b = Float.valueOf(value);

                        float result = a * b;

                        return Float.toString(result);
                    }
                    catch (NumberFormatException ignored)
                    {
                        return value;
                    }
                }

                case add:
                default:
                {
                    try
                    {
                        float a = Float.valueOf(in);
                        float b = Float.valueOf(value);

                        float result = a + b;

                        return Float.toString(result);
                    }
                    catch (NumberFormatException ignored)
                    {
                        return value;
                    }
                }
            }
        }
    }

    protected ObjectMap<String, UpgradeProperty> properties;

    public Upgrade()
    {
        this.properties = new ObjectMap<>();
    }

    public void preApply(InstrumentData instrumentData)
    {
        for (ContentComponent contentComponent: getComponents())
        {
            if (!(contentComponent instanceof UpgradeComponent))
            {
                if (contentComponent instanceof DoNotApply)
                {
                    continue;
                }

                if (contentComponent instanceof ForOwnerOnly)
                {
                    if ((instrumentData.getOwner() == null) ||
                            (instrumentData.getOwner().getComponent(PlayerOwnerComponent.class) == null))
                    {
                        continue;
                    }
                }

                Component component = contentComponent.getComponent(instrumentData);
                if (component != null)
                {
                    instrumentData.addComponent(component);
                    component.init();
                }
            }
        }

        if (getComponents() == null) return;

        for (ContentComponent contentComponent: getComponents())
        {
            // just apply upgrade component instead of copying
            if (contentComponent instanceof UpgradeComponent)
            {
                UpgradeComponent upgradeComponent = ((UpgradeComponent) contentComponent);

                if (upgradeComponent.pre())
                {
                    upgradeComponent.upgrade(instrumentData);
                }
            }
        }
    }

    public void postApply(InstrumentData instrumentData)
    {
        if (getComponents() == null) return;

        for (ContentComponent contentComponent: getComponents())
        {
            // just apply upgrade component instead of copying
            if (contentComponent instanceof UpgradeComponent)
            {
                UpgradeComponent upgradeComponent = ((UpgradeComponent) contentComponent);

                if (!upgradeComponent.pre())
                {
                    upgradeComponent.upgrade(instrumentData);
                }
            }
        }
    }

    @Override
    public void read(Json json, JsonValue jsonData)
    {
        super.read(json, jsonData);
        conversion = jsonData.getString("conversion", null);
        convertsFrom = jsonData.getString("convertsFrom", null);
        conversionBase = jsonData.getString("conversionBase", null);
        if (jsonData.has("ammo"))
        {
            ammo = jsonData.get("ammo").getString("id", null);
            ammoAmount = jsonData.get("ammo").getInt("amount", 0);
        }

        if (jsonData.has("properties"))
        {
            for (JsonValue p : jsonData.get("properties"))
            {
                UpgradeProperty property = new UpgradeProperty();
                property.set(p.asString());

                properties.put(p.name(), property);
            }
        }
    }

    public UpgradeProperty getProperty(String property)
    {
        return properties.get(property);
    }

    public ObjectMap<String, UpgradeProperty> getProperties()
    {
        return properties;
    }
}
