package com.desertkun.brainout.data;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.math.MathUtils;
import com.badlogic.gdx.math.Vector2;
import com.badlogic.gdx.utils.FloatArray;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.Constants;
import com.desertkun.brainout.client.states.CSGame;
import com.desertkun.brainout.data.active.PlayerData;
import com.desertkun.brainout.data.block.BlockData;
import com.desertkun.brainout.data.components.SimplePhysicsComponentData;
import com.desertkun.brainout.data.interfaces.RenderContext;
import com.desertkun.brainout.data.interfaces.Renderable;

/** A world-space visibility polygon, rasterized into the scene's stencil buffer.
 * The GPU clips fragments, not whole actors: a foot through a doorway stays visible.
 * Terrain is always drawn; only dynamic layers are stencil-tested. */
public final class WorldVisibility
{
    private static final int[] WALL_LAYERS = {Constants.Layers.BLOCK_LAYER_FOREGROUND, Constants.Layers.BLOCK_LAYER_UPPER};
    private final ClientMap map;
    private ShapeRenderer shapes;
    private final FloatArray angles = new FloatArray();
    private final FloatArray points = new FloatArray();
    private final Vector2 direction = new Vector2();
    private float eyeX, eyeY, radius;
    private boolean enabled;
    private long polygonFrame = -1;
    private float polygonX, polygonY, polygonRadius;

    public WorldVisibility(ClientMap map) { this.map = map; }

    private boolean opaque(int x, int y)
    {
        for (int layer : WALL_LAYERS)
        {
            BlockData block = map.getBlockAt(x, y, layer);
            if (block != null && !block.getCreator().isCanBeSeenTrough()) return true;
        }
        return false;
    }

    /** Grid DDA never skips a one-tile wall, even on diagonal rays. */
    private float cast(float angle)
    {
        float dx = MathUtils.cos(angle), dy = MathUtils.sin(angle);
        direction.set(dx, dy);
        int x = MathUtils.floor(eyeX), y = MathUtils.floor(eyeY);
        int sx = dx >= 0 ? 1 : -1, sy = dy >= 0 ? 1 : -1;
        float stepX = Math.abs(dx) < 0.000001f ? Float.POSITIVE_INFINITY : Math.abs(1 / dx);
        float stepY = Math.abs(dy) < 0.000001f ? Float.POSITIVE_INFINITY : Math.abs(1 / dy);
        float tx = (dx >= 0 ? x + 1 - eyeX : eyeX - x) * stepX;
        float ty = (dy >= 0 ? y + 1 - eyeY : eyeY - y) * stepY;
        float entered = 0;
        while (entered < radius)
        {
            float leave = Math.min(radius, Math.min(tx, ty));
            if (opaque(x, y))
            {
                // Respect partial blocks/slopes instead of treating every tile as a solid square.
                for (float t = entered + 0.001f; t <= leave + 0.001f; t += 0.04f)
                {
                    float px = eyeX + dx * t, py = eyeY + dy * t;
                    for (int layer : WALL_LAYERS)
                    {
                        BlockData b = map.getBlockAt(x, y, layer);
                        if (b != null && !b.getCreator().isCanBeSeenTrough() &&
                            b.isContact(null, px - x, py - y, null, direction, 0, map, x, y)) return t;
                    }
                }
            }
            if (tx < ty) { entered = tx; tx += stepX; x += sx; }
            else { entered = ty; ty += stepY; y += sy; }
        }
        return radius;
    }

    public void begin(Batch batch, RenderContext context)
    {
        CSGame game = BrainOutClient.ClientController.getState(CSGame.class);
        PlayerData player = game == null ? null : game.getPlayerData();
        enabled = player != null && player.isAlive() && player.getMap() == map;
        if (!enabled) return;
        SimplePhysicsComponentData physics = player.getComponentWithSubclass(SimplePhysicsComponentData.class);
        eyeX = player.getX();
        eyeY = player.getY() + (physics == null ? 0.5f : physics.getHalfSize().y * 0.8f);
        // Cover the entire camera, including a camera panned away from the player.
        float w = ((com.badlogic.gdx.graphics.OrthographicCamera)context.camera).viewportWidth * ((com.badlogic.gdx.graphics.OrthographicCamera)context.camera).zoom;
        float h = ((com.badlogic.gdx.graphics.OrthographicCamera)context.camera).viewportHeight * ((com.badlogic.gdx.graphics.OrthographicCamera)context.camera).zoom;
        radius = (float)Math.hypot(w, h) + (float)Math.hypot(context.camera.position.x - eyeX, context.camera.position.y - eyeY) + 2;
        if (polygonFrame != Gdx.graphics.getFrameId() || polygonX != eyeX || polygonY != eyeY || polygonRadius != radius)
        {
        polygonFrame = Gdx.graphics.getFrameId();
        polygonX = eyeX; polygonY = eyeY; polygonRadius = radius;
        angles.clear(); points.clear();
        for (int i = 0; i < 720; i++) angles.add(i * MathUtils.PI2 / 720);
        int minX = Math.max(0, MathUtils.floor(eyeX - radius)), maxX = Math.min(map.getWidth()-1, MathUtils.ceil(eyeX + radius));
        int minY = Math.max(0, MathUtils.floor(eyeY - radius)), maxY = Math.min(map.getHeight()-1, MathUtils.ceil(eyeY + radius));
        for (int x = minX; x <= maxX; x++) for (int y = minY; y <= maxY; y++)
        {
            if (!opaque(x,y) || (opaque(x-1,y) && opaque(x+1,y) && opaque(x,y-1) && opaque(x,y+1))) continue;
            for (int cx=0; cx<=1; cx++) for (int cy=0; cy<=1; cy++)
            {
                float a = MathUtils.atan2(y+cy-eyeY,x+cx-eyeX);
                angles.add(a-0.00002f); angles.add(a); angles.add(a+0.00002f);
            }
        }
        // atan2 and regular rays must share the same angular interval.
        for (int i=0; i<angles.size; i++) angles.set(i, (angles.get(i)+MathUtils.PI2)%MathUtils.PI2);
        angles.sort();
        for (int i=0; i<angles.size; i++)
        {
            float a=angles.get(i), distance=cast(a);
            points.add(eyeX+MathUtils.cos(a)*distance); points.add(eyeY+MathUtils.sin(a)*distance);
        }
        }
        batch.end();
        rasterize(context.camera);
        batch.begin();
    }

    /** Restore the same polygon on the current framebuffer after post-processing. */
    public void rasterize(com.badlogic.gdx.graphics.Camera camera)
    {
        if (!enabled) return;
        if (shapes == null) shapes = new ShapeRenderer();
        Gdx.gl.glEnable(GL20.GL_STENCIL_TEST);
        Gdx.gl.glStencilMask(0xff);
        Gdx.gl.glClearStencil(0);
        Gdx.gl.glClear(GL20.GL_STENCIL_BUFFER_BIT);
        Gdx.gl.glStencilFunc(GL20.GL_ALWAYS, 1, 0xff);
        Gdx.gl.glStencilOp(GL20.GL_KEEP, GL20.GL_KEEP, GL20.GL_REPLACE);
        Gdx.gl.glColorMask(false,false,false,false);
        shapes.setProjectionMatrix(camera.combined);
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        for (int i=0; i<points.size; i+=2)
        {
            int next=(i+2)%points.size;
            shapes.triangle(eyeX,eyeY,points.get(i),points.get(i+1),points.get(next),points.get(next+1));
        }
        shapes.end();
        Gdx.gl.glColorMask(true,true,true,true);
        Gdx.gl.glStencilMask(0);
        Gdx.gl.glStencilOp(GL20.GL_KEEP,GL20.GL_KEEP,GL20.GL_KEEP);
        Gdx.gl.glDisable(GL20.GL_STENCIL_TEST);
    }

    public void clip(Batch batch, boolean on)
    {
        if (!enabled) return;
        batch.flush();
        clip(on);
    }

    public void clip(boolean on)
    {
        if (!enabled) return;
        if (on) { Gdx.gl.glEnable(GL20.GL_STENCIL_TEST); Gdx.gl.glStencilFunc(GL20.GL_EQUAL,1,0xff); }
        else Gdx.gl.glDisable(GL20.GL_STENCIL_TEST);
    }

    public void shade(Batch batch, RenderContext context)
    {
        if (!enabled) return;
        batch.end();
        Gdx.gl.glEnable(GL20.GL_STENCIL_TEST);
        Gdx.gl.glStencilFunc(GL20.GL_EQUAL,0,0xff);
        Gdx.gl.glEnable(GL20.GL_BLEND);
        Gdx.gl.glBlendFunc(GL20.GL_SRC_ALPHA,GL20.GL_ONE_MINUS_SRC_ALPHA);
        shapes.setProjectionMatrix(context.camera.combined);
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.22f,0.23f,0.25f,0.35f);
        shapes.rect(eyeX-radius,eyeY-radius,radius*2,radius*2);
        shapes.end();
        Gdx.gl.glDisable(GL20.GL_STENCIL_TEST);
        Gdx.gl.glStencilMask(0xff);
        batch.begin();
    }

    public Renderable marker(final boolean first)
    {
        return new Renderable() {
            public void render(Batch b, RenderContext c) { if(first) begin(b,c); else shade(b,c); }
            public boolean hasRender() { return true; }
            public int getZIndex() { return 0; }
            public int getLayer() { return 0; }
        };
    }

    public Renderable wrap(final Renderable original)
    {
        return new Renderable() {
            public void render(Batch b, RenderContext c) {
                clip(b,true);
                try { original.render(b,c); } finally { clip(b,false); }
            }
            public boolean hasRender() { return true; }
            public int getZIndex() { return original.getZIndex(); }
            public int getLayer() { return original.getLayer(); }
        };
    }

    public void dispose() { if(shapes != null) shapes.dispose(); }
}
