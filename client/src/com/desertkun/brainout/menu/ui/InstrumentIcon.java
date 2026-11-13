package com.desertkun.brainout.menu.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.*;
import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.graphics.glutils.FrameBuffer;
import com.badlogic.gdx.math.Vector2;
import com.badlogic.gdx.scenes.scene2d.ui.WidgetGroup;
import com.badlogic.gdx.utils.Disposable;
import com.badlogic.gdx.utils.ObjectMap;
import com.badlogic.gdx.utils.ObjectSet;
import com.badlogic.gdx.utils.OrderedMap;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.ClientConstants;
import com.desertkun.brainout.content.Skin;
import com.desertkun.brainout.content.instrument.Instrument;
import com.desertkun.brainout.content.components.InstrumentAnimationComponent;
import com.desertkun.brainout.content.components.ReplaceSlotComponent;
import com.desertkun.brainout.content.upgrades.Upgrade;
import com.desertkun.brainout.data.components.InstrumentAnimationComponentData;
import com.desertkun.brainout.data.instrument.InstrumentInfo;
import com.esotericsoftware.spine.AnimationState;
import com.esotericsoftware.spine.Bone;
import com.esotericsoftware.spine.Skeleton;
import com.esotericsoftware.spine.Slot;
import com.esotericsoftware.spine.attachments.Attachment;

public class InstrumentIcon extends WidgetGroup implements Disposable
{
    private final InstrumentInfo info;
    private InstrumentAnimationComponentData data;
    private Instrument displayed;
    private final float instrumentScale;
    private final Vector2 location;
    private Bone centerBone;
    private final boolean dynamic;
    private boolean drawPair;
    private final Vector2 pairOrigin = new Vector2();
    private final Vector2 pairSize = new Vector2();
    private final com.badlogic.gdx.utils.FloatArray pairVertices = new com.badlogic.gdx.utils.FloatArray();
    private boolean measurePair = true;

    public void setDrawPair(boolean value) { drawPair = value; dirty = true; }

    private FrameBuffer cached;
    private TextureRegion cachedTexture;
    private boolean dirty;
    private OrthographicCamera camera;
    private Batch cacheBatch;

    private ObjectSet<String> disabledAttachments;
    private OrderedMap<Slot, Attachment> originalAttachments;

    public InstrumentIcon(InstrumentInfo info, float instrumentScale, boolean dynamic)
    {
        this.info = info;
        this.dynamic = dynamic;
        drawPair = info.instrument.getID().startsWith("paired-");
        this.dirty = false;

        this.instrumentScale = instrumentScale;
        location = new Vector2();
        if (dynamic) originalAttachments = new OrderedMap<>();
        loadModel(displayInstrument());
    }

    private Instrument displayInstrument()
    {
        Upgrade conversion = info.upgrades.get("conversion");
        if (conversion != null && conversion.getConversion() != null)
        {
            Instrument target = BrainOutClient.ContentMgr.get(conversion.getConversion(), Instrument.class);
            if (target != null) return target;
        }
        return info.instrument;
    }

    private void loadModel(Instrument model)
    {
        displayed = model;
        InstrumentAnimationComponent animation = model.getComponentFrom(InstrumentAnimationComponent.class);

        if (animation == null)
        {
            throw new RuntimeException("Instrument " + info.instrument.getID() + " should have some animation.");
        }

        data = animation.getComponent(null);

        float scale = ClientConstants.Graphics.RES_SIZE * instrumentScale * (1f / 0.4f);

        data.setSkin(displayed == info.instrument ? info.skin : displayed.getDefaultSkin());
        data.getSkeleton().getRootBone().setScale(data.getSkeleton().getRootBone().getScaleX() * scale);

        data.init();

        centerBone = data.getSkeleton().findBone("center-bone");

        if (dynamic)
        {
            updateOriginalAttachments();
        }
        else
        {
            updateLocation();
        }
    }

    public void animateTo(String animation, int frame, int frames)
    {
        AnimationState.TrackEntry track = data.getState().setAnimation(0, animation, false);
        track.setTimeScale(0);
        track.setAnimationEnd(((float)frame / (float)frames) * track.getAnimationEnd());

        data.getState().apply(data.getSkeleton());
        data.getSkeleton().updateWorldTransform();
    }

    private void updateOriginalAttachments()
    {
        if (dynamic)
        {
            originalAttachments.clear();

            for (Slot slot : data.getSkeleton().getSlots())
            {
                originalAttachments.put(slot, slot.getAttachment());
            }
        }
    }

    public void resetAnimation()
    {
        Instrument target = displayInstrument();
        if (displayed != target)
        {
            loadModel(target);
            updateLocation();
        }
        clearToOriginalArrachments();

        for (String key : info.upgrades.orderedKeys())
        {
            Upgrade upgrade = info.upgrades.get(key);
            ReplaceSlotComponent replaceSlot = upgrade.getComponent(ReplaceSlotComponent.class);

            if (replaceSlot != null)
            {
                replaceSlot.upgradeSkeleton(data.getSkeleton());
            }
        }

        if (disabledAttachments != null)
        {
            for (String name : disabledAttachments)
            {
                Skeleton skeleton = data.getSkeleton();
                if (skeleton.findSlot(name) != null)
                    skeleton.setAttachment(name, null);
            }
        }

        measurePair = true;
        if (cached != null)
        {
            dirty = true;
        }
    }

    private void clearToOriginalArrachments()
    {
        // Attachment geometry may move the muzzle; deselecting a barrel restores it.
        for (com.esotericsoftware.spine.Bone bone : data.getSkeleton().getBones())
            if (bone.getData().getName().equals("fire-bone") || bone.getData().getName().equals("vg-tip"))
            {
                bone.setX(bone.getData().getX()); bone.setY(bone.getData().getY());
            }
        if (dynamic)
        {
            for (ObjectMap.Entry<Slot, Attachment> entry : originalAttachments)
            {
                entry.key.setAttachment(entry.value);
            }
        }
    }

    protected float getCenterX()
    {
        return 0.5f;
    }

    protected float getCenterY()
    {
        return 0.5f;
    }

    private void updateLocation()
    {
        location.set(getWidth() * getCenterX(), getHeight() * getCenterY());

        if (centerBone != null)
        {
            location.add(data.getSkeleton().getX(), data.getSkeleton().getY());
            location.sub(centerBone.getWorldX(), centerBone.getWorldY());
        }
    }

    public void setSkin(Skin skin)
    {
        info.skin = skin;

        resetSkin();
    }

    public void resetSkin()
    {
        clearToOriginalArrachments();

        data.setSkin(displayed == info.instrument ? info.skin : displayed.getDefaultSkin());
        data.updateSkin();

        updateOriginalAttachments();

        resetAnimation();
    }

    public void disableAttachment(String attachment)
    {
        if (disabledAttachments == null)
        {
            disabledAttachments = new ObjectSet<>();
        }

        disabledAttachments.add(attachment);

        resetAnimation();
    }

    public void enableUpgrade(String key, Upgrade upgrade)
    {
        info.upgrades.put(key, upgrade);

        resetAnimation();
    }

    public void disableUpgrade(String key)
    {
        info.upgrades.remove(key);

        resetAnimation();
    }

    @Override
    protected void drawChildren(Batch batch, float parentAlpha)
    {
        super.drawChildren(batch, parentAlpha);

        if (cachedTexture != null)
        {
            if (dirty)
            {
                dirty = false;

                batch.end();

                cached.begin();

                Gdx.gl.glClearColor(0, 0, 0, 0);
                Gdx.gl.glClear(GL30.GL_COLOR_BUFFER_BIT);

                cacheBatch.begin();
                cacheBatch.enableBlending();

                renderIcon(cacheBatch);

                cacheBatch.end();

                cached.end();

                batch.begin();
            }

            batch.draw(cachedTexture, 0, 0, getWidth(), getHeight());
        }
        else
        {
            renderIcon(batch);
        }
    }

    private void renderIcon(Batch batch)
    {
        Skeleton rig = data.getSkeleton();
        if (!drawPair || getWidth() <= 0 || getHeight() <= 0)
        {
            rig.setPosition(location.x, location.y);
            rig.updateWorldTransform();
            data.render(batch, null);
            return;
        }
        if (measurePair)
        {
            rig.setPosition(0, 0);
            rig.updateWorldTransform();
            rig.getBounds(pairOrigin, pairSize, pairVertices);
            measurePair = false;
        }
        float spread = Math.min(7f, Math.min(getWidth(), getHeight()) * .10f);
        float fit = Math.min(1f, Math.min((getWidth() - 2 * spread - 2) / Math.max(1, pairSize.x),
            (getHeight() - 2 * spread - 2) / Math.max(1, pairSize.y)));
        fit = Math.max(.01f, fit);
        float sx = rig.getScaleX(), sy = rig.getScaleY();
        float x = getWidth() * getCenterX() - fit * (pairOrigin.x + pairSize.x / 2);
        float y = getHeight() * getCenterY() - fit * (pairOrigin.y + pairSize.y / 2);
        rig.setScale(sx * fit, sy * fit);
        rig.setPosition(x + spread, y + spread);
        rig.updateWorldTransform();
        float r = rig.getColor().r, g = rig.getColor().g, b = rig.getColor().b;
        rig.getColor().set(r * .62f, g * .67f, b * .73f, rig.getColor().a);
        data.render(batch, null);
        rig.getColor().set(r, g, b, rig.getColor().a);
        rig.setPosition(x - spread, y - spread);
        rig.updateWorldTransform();
        data.render(batch, null);
        rig.setScale(sx, sy);
        rig.setPosition(location.x, location.y);
        rig.updateWorldTransform();
    }

    @Override
    public void act(float delta)
    {
        super.act(delta);

        data.update(delta);
    }

    @Override
    public void validate()
    {
        super.validate();

        updateLocation();
    }

    public void init()
    {
        data.getSkeleton().updateWorldTransform();

        resetAnimation();
    }

    @Override
    public void dispose()
    {
        if (cached != null)
        {
            cached.dispose();
            cacheBatch.dispose();
        }
    }

    public void setCached(int width, int height)
    {
        try
        {
            cached = new FrameBuffer(Pixmap.Format.RGBA8888, width, height, false);
        }
        catch (IllegalStateException ignored)
        {
            cached = null;
            return;
        }

        cachedTexture = new TextureRegion(cached.getColorBufferTexture());
        cachedTexture.flip(false, true);

        camera = new OrthographicCamera(width, height);

        camera.position.x = width / 2;
        camera.position.y = height / 2;

        cacheBatch = BrainOutClient.ClientSett.allocateNewBatch();

        camera.update();
        cacheBatch.setProjectionMatrix(camera.combined);
    }

    @Override
    public float getPrefWidth()
    {
        return getWidth();
    }

    @Override
    public float getMinHeight()
    {
        return getHeight();
    }

    public TextureRegion getCachedTexture()
    {
        return cachedTexture;
    }
}
