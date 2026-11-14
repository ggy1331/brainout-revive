package com.desertkun.brainout.data;

import com.badlogic.gdx.math.*;
import com.badlogic.gdx.utils.Array;
import com.desertkun.brainout.Constants;
import com.desertkun.brainout.data.active.*;
import com.desertkun.brainout.data.block.BlockData;
import com.desertkun.brainout.data.components.SimplePhysicsComponentData;

/** Swept cursor movement with optional sliding after initial aim contact; no physics bodies or per-step allocation. */
public final class AimCursorCollision
{
    private final Array<Rectangle> players = new Array<>();
    private int count;
    private final Vector2 direction = new Vector2(1, 0);
    private Map map;
    private static final int[] LAYERS={Constants.Layers.BLOCK_LAYER_FOREGROUND,Constants.Layers.BLOCK_LAYER_UPPER};

    private boolean blocked(float x, float y)
    {
        for (int i=0;i<count;i++) if (players.get(i).contains(x,y)) return true;
        for (int layer : LAYERS)
        {
            int bx=MathUtils.floor(x), by=MathUtils.floor(y);
            BlockData block=map.getBlockAt(bx,by,layer);
            if (WorldVisibility.isSolidSurface(block) &&
                block.isContact(null,x-bx,y-by,null,direction,0,map,bx,by)) return true;
        }
        return false;
    }

    public void move(Map map, PlayerData owner, float fromX, float fromY,
                     float targetX, float targetY, Vector2 result)
    {
        move(map,owner,fromX,fromY,targetX,targetY,result,true);
    }

    public void move(Map map, PlayerData owner, float fromX, float fromY,
                     float targetX, float targetY, Vector2 result, boolean slide)
    {
        this.map=map; count=0;
        for (ActiveData active : map.getActives().values())
        {
            if (!(active instanceof PlayerData) || active==owner || !((PlayerData)active).isAlive()) continue;
            SimplePhysicsComponentData physics=active.getComponentWithSubclass(SimplePhysicsComponentData.class);
            if (physics==null) continue;
            if (count==players.size) players.add(new Rectangle());
            Vector2 half=physics.getHalfSize();
            players.get(count++).set(active.getX()-half.x-.05f,active.getY()-half.y-.05f,
                half.x*2+.1f,half.y*2+.1f);
        }
        result.set(fromX,fromY);
        // A moving player can cover yesterday's cursor location. Resolve only
        // that overlap before sweeping, rather than teleporting to the target.
        if (blocked(result.x,result.y))
        {
            boolean found=false;
            for (float r=.1f;r<=4&&!found;r+=.1f) for (int i=0;i<32;i++)
            {
                float x=fromX+MathUtils.cos(i*MathUtils.PI2/32)*r;
                float y=fromY+MathUtils.sin(i*MathUtils.PI2/32)*r;
                if (!blocked(x,y)) {result.set(x,y);found=true;break;}
            }
            if (!found) return;
        }
        float dx=targetX-result.x,dy=targetY-result.y;
        int steps=Math.max(1,MathUtils.ceil(Math.max(Math.abs(dx),Math.abs(dy))/.08f));
        steps=Math.min(steps,4096);dx/=steps;dy/=steps;direction.set(dx,dy);
        for (int i=0;i<steps;i++)
        {
            if (!blocked(result.x+dx,result.y+dy)) result.add(dx,dy);
            else
            {
                if (slide)
                {
                    if (!blocked(result.x+dx,result.y)) result.x+=dx;
                    if (!blocked(result.x,result.y+dy)) result.y+=dy;
                    continue;
                }
                // Stop the whole mouse move at first contact, without projecting its
                // remaining distance onto the surface. Refine within the last step
                // so the mark touches the surface instead of stopping a step short.
                float low=0, high=1;
                for (int refinement=0;refinement<12;refinement++)
                {
                    float mid=(low+high)*.5f;
                    if (blocked(result.x+dx*mid,result.y+dy*mid)) high=mid;
                    else low=mid;
                }
                result.add(dx*low,dy*low);
                break;
            }
        }
    }
}
