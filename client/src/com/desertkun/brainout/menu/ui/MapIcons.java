package com.desertkun.brainout.menu.ui;

import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.scenes.scene2d.ui.Image;
import com.desertkun.brainout.BrainOutClient;

/**
 * revive: map preview images ("map-<name>" in the skin). Maps without a preview
 * (halloween, duel, bunker_ctf, maps made in the editor) used to crash the client
 * on the end-game vote screen; now they get an empty image (the map name is shown
 * as a label next to it anyway).
 */
public final class MapIcons
{
    private MapIcons() {}

    public static boolean has(String map)
    {
        return BrainOutClient.Skin.has("map-" + map, TextureRegion.class);
    }

    public static Image create(String map)
    {
        if (has(map))
        {
            return new Image(BrainOutClient.Skin, "map-" + map);
        }

        if ("duel".equals(map) || "halloween".equals(map) || "bunker_ctf".equals(map))
        {
            com.badlogic.gdx.graphics.Texture texture = new com.badlogic.gdx.graphics.Texture(
                com.badlogic.gdx.Gdx.files.classpath("map-previews/" + map + ".png"));
            BrainOutClient.Skin.add("map-" + map, texture, com.badlogic.gdx.graphics.Texture.class);
            TextureRegion region = new TextureRegion(texture);
            BrainOutClient.Skin.add("map-" + map, region, TextureRegion.class);
            return new Image(region);
        }
        return new Image();
    }
}
