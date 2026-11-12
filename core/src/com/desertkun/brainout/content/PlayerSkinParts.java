package com.desertkun.brainout.content;

import com.badlogic.gdx.utils.Array;
import com.badlogic.gdx.utils.ObjectMap;
import com.badlogic.gdx.utils.ObjectSet;
import com.esotericsoftware.spine.Skeleton;
import com.esotericsoftware.spine.SkeletonData;
import com.esotericsoftware.spine.Skin;
import com.esotericsoftware.spine.Slot;
import com.esotericsoftware.spine.SlotData;
import com.esotericsoftware.spine.attachments.Attachment;

/**
 * A player skin split into three parts: legs (with the pelvis), torso with arms, head.
 * Each part can come from a different {@link PlayerSkin}; the parts are combined into one
 * runtime Spine skin (cached per skeleton data).
 */
public final class PlayerSkinParts
{
    public enum Part
    {
        legs("gleg1", "gleg2", "gknee1", "gknee2", "gfoot1", "gfoot2", "torso", "skirt"),
        // everything that is not legs / head goes with the torso (backpack, hooks, physics slots...)
        torso("body", "torso-back", "ghand1", "ghand2", "gpalm1", "gpalm2"),
        head("ghead", "hat", "mask");

        private final ObjectSet<String> slots = new ObjectSet<>();

        Part(String... slots)
        {
            this.slots.addAll(slots);
        }

        public static Part of(String slotName)
        {
            if (legs.slots.contains(slotName)) return legs;
            if (head.slots.contains(slotName)) return head;
            return torso;
        }
    }

    private static final ObjectMap<SkeletonData, ObjectMap<String, Skin>> CACHE = new ObjectMap<>();

    private PlayerSkinParts() {}

    private static Skin find(SkeletonData data, PlayerSkin skin)
    {
        if (skin == null || skin.getData() == null)
            return null;

        return data.findSkin(skin.getData());
    }

    /** Spine skin for given parts; a null part means "same as torso". */
    public static Skin compose(SkeletonData data, PlayerSkin legs, PlayerSkin torso, PlayerSkin head)
    {
        if (legs == null) legs = torso;
        if (head == null) head = torso;

        Skin torsoSkin = find(data, torso);

        if (legs == torso && head == torso)
            return torsoSkin;

        Skin legsSkin = find(data, legs);
        Skin headSkin = find(data, head);

        if (torsoSkin == null) torsoSkin = legsSkin != null ? legsSkin : headSkin;
        if (torsoSkin == null) return null;
        if (legsSkin == null) legsSkin = torsoSkin;
        if (headSkin == null) headSkin = torsoSkin;

        String key = legsSkin.getName() + "|" + torsoSkin.getName() + "|" + headSkin.getName();

        ObjectMap<String, Skin> perData = CACHE.get(data);

        if (perData == null)
        {
            perData = new ObjectMap<>();
            CACHE.put(data, perData);
        }

        Skin result = perData.get(key);

        if (result != null)
            return result;

        result = new Skin(key);
        result.getBones().addAll(torsoSkin.getBones());
        result.getConstraints().addAll(torsoSkin.getConstraints());

        Array<SlotData> slots = data.getSlots();

        add(result, torsoSkin, slots, Part.torso);
        add(result, legsSkin, slots, Part.legs);
        add(result, headSkin, slots, Part.head);

        perData.put(key, result);
        return result;
    }

    private static void add(Skin to, Skin from, Array<SlotData> slots, Part part)
    {
        for (Skin.SkinEntry entry : from.getAttachments())
        {
            String slotName = slots.get(entry.getSlotIndex()).getName();

            if (Part.of(slotName) == part)
            {
                to.setAttachment(entry.getSlotIndex(), entry.getName(), entry.getAttachment());
            }
        }
    }

    /**
     * Sets the skin and removes attachments that came from the previous skin but have
     * no counterpart in the new one (e.g. a hat when switching to a head without a hat).
     */
    public static void apply(Skeleton skeleton, Skin newSkin)
    {
        if (newSkin == null)
            return;

        Skin oldSkin = skeleton.getSkin();

        if (oldSkin == newSkin)
            return;

        skeleton.setSkin(newSkin);

        if (oldSkin == null)
            return;

        Array<Slot> slots = skeleton.getSlots();

        for (Skin.SkinEntry entry : oldSkin.getAttachments())
        {
            Slot slot = slots.get(entry.getSlotIndex());
            Attachment current = slot.getAttachment();

            if (current == null || current != entry.getAttachment())
                continue;

            if (newSkin.getAttachment(entry.getSlotIndex(), entry.getName()) != null)
                continue;

            // stale attachment from the old skin; fall back to the setup pose one
            String setup = slot.getData().getAttachmentName();
            slot.setAttachment(setup == null ? null : skeleton.getAttachment(entry.getSlotIndex(), setup));
        }
    }
}
