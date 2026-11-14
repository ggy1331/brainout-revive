import com.badlogic.gdx.*;
import com.badlogic.gdx.backends.lwjgl3.*;
import com.badlogic.gdx.graphics.*;
import com.badlogic.gdx.graphics.g2d.*;
import com.badlogic.gdx.graphics.glutils.*;
import com.badlogic.gdx.utils.*;
import com.desertkun.brainout.*;
import com.desertkun.brainout.desktop.*;
import com.desertkun.brainout.client.states.CSGame;
import com.desertkun.brainout.data.*;
import com.desertkun.brainout.data.active.*;
import com.desertkun.brainout.data.block.*;
import com.desertkun.brainout.data.components.*;
import com.desertkun.brainout.data.instrument.*;
import com.desertkun.brainout.data.interfaces.*;
import com.desertkun.brainout.content.instrument.*;
import com.desertkun.brainout.content.upgrades.*;
import com.desertkun.brainout.content.shop.*;
import com.desertkun.brainout.menu.ui.InstrumentIcon;
import com.esotericsoftware.spine.*;

public class MovementSmoke {
    static int ready;
    static boolean done;
    public static void main(String[] args) {
        DesktopEnvironment env=new DesktopEnvironment(args);
        Lwjgl3ApplicationConfiguration cfg=new Lwjgl3ApplicationConfiguration();
        cfg.setWindowedMode(1100,750);cfg.setInitialVisible(false);cfg.setForegroundFPS(60);
        cfg.setBackBufferConfig(8,8,8,8,16,8,0);
        Thread t=new Thread(()->{for(int i=0;i<130;i++){try{Thread.sleep(1000);}catch(Exception e){} if(Gdx.app!=null)Gdx.app.postRunnable(()->check());}if(Gdx.app!=null)Gdx.app.exit();});t.setDaemon(true);t.start();
        new Lwjgl3Application(BrainOutDesktop.initDesktopInstance(env,DesktopSettings.GetDesktopSettings(env)),cfg);
    }
    static void require(boolean v,String why){if(!v)throw new AssertionError(why);}
    static void png(String name){Pixmap p=ScreenUtils.getFrameBufferPixmap(0,0,Gdx.graphics.getWidth(),Gdx.graphics.getHeight());PixmapIO.writePNG(Gdx.files.absolute(System.getenv("GAMEPLAY_LAB")+"/"+name),p,-1,true);p.dispose();}
    static void check(){
        if(done)return;
        CSGame game;
        try { game=BrainOutClient.ClientController.getState(CSGame.class); } catch(NullPointerException startup) { return; }
        if(game==null||game.getPlayerData()==null)return;
        if(++ready<5)return;
        done=true;
        try{
            png("hub.png");
            java.nio.IntBuffer stencil=BufferUtils.newIntBuffer(1);Gdx.gl.glGetIntegerv(GL20.GL_STENCIL_BITS,stencil);
            require(stencil.get(0)>=8,"scene has no stencil buffer");
            testMovement(game.getPlayerData());
            testArmSync(game.getPlayerData());
            testSprintTimers(game.getPlayerData());
            renderPoses();
            System.out.println("MOVEMENT_SMOKE_PASS");
        }catch(Throwable ex){ex.printStackTrace();System.out.println("MOVEMENT_SMOKE_FAIL");}
        Gdx.app.exit();
    }

    static java.lang.reflect.Field field(String name) throws Exception {java.lang.reflect.Field f=PlayerControllerComponentData.class.getDeclaredField(name);f.setAccessible(true);return f;}
    static java.lang.reflect.Method method(String name,Class<?>... types) throws Exception {java.lang.reflect.Method m=PlayerControllerComponentData.class.getDeclaredMethod(name,types);m.setAccessible(true);return m;}
    static void testMovement(PlayerData p)throws Exception {
        PlayerControllerComponentData c=p.getComponentWithSubclass(PlayerControllerComponentData.class);
        java.lang.reflect.Method set=method("setState",com.desertkun.brainout.content.active.Player.State.class);
        java.lang.reflect.Method scale=method("horizontalScale");
        com.desertkun.brainout.content.active.Player.State[] states={com.desertkun.brainout.content.active.Player.State.normal,com.desertkun.brainout.content.active.Player.State.sit,com.desertkun.brainout.content.active.Player.State.crawl};
        for(var a:states)for(var b:states)if(a!=b){
            set.invoke(c,a);field("stanceProgress").setFloat(c,1);
            float from=p.getCurrentState().speed.x*(Float)scale.invoke(c);
            set.invoke(c,b);float start=p.getCurrentState().speed.x*(Float)scale.invoke(c);
            require(Math.abs(start-from)<.001,"speed snapped "+a+" -> "+b);
            field("stanceProgress").setFloat(c,.5f);float mid=p.getCurrentState().speed.x*(Float)scale.invoke(c);
            field("stanceProgress").setFloat(c,1);float end=p.getCurrentState().speed.x*(Float)scale.invoke(c);
            require(mid>=Math.min(from,end)&&mid<=Math.max(from,end),"non-monotonic transition");
            System.out.println("STANCE_PASS "+a+" -> "+b+" "+start+" / "+mid+" / "+end);
        }
        set.invoke(c,com.desertkun.brainout.content.active.Player.State.tacticalRun);field("stanceProgress").setFloat(c,1);c.setMoveDirection(1,0);p.setAngle(0);
        require(Math.abs(p.getCurrentState().speed.x*(Float)scale.invoke(c)-16)<.001,"sprint !=16");
        set.invoke(c,com.desertkun.brainout.content.active.Player.State.crawl);c.setMoveDirection(new com.badlogic.gdx.math.Vector2(0,0));c.setMoveDirection(new com.badlogic.gdx.math.Vector2(1,1));
        require(p.getState()==com.desertkun.brainout.content.active.Player.State.sit,"W prone->sit");
        c.setMoveDirection(new com.badlogic.gdx.math.Vector2(-1,1));require(p.getState()==com.desertkun.brainout.content.active.Player.State.sit&&c.getOriginalDirection().y==0,"held W repeated");
        c.setMoveDirection(new com.badlogic.gdx.math.Vector2(1,0));c.setMoveDirection(new com.badlogic.gdx.math.Vector2(1,1));
        require(p.getState()==com.desertkun.brainout.content.active.Player.State.normal,"W sit->stand");
        System.out.println("W_AND_SPRINT_PASS");
    }
    static void testSprintTimers(PlayerData p)throws Exception {
        PlayerControllerComponentData c=p.getComponentWithSubclass(PlayerControllerComponentData.class);
        var set=method("setState",com.desertkun.brainout.content.active.Player.State.class);
        var tick=method("updateSprintTimers",float.class);
        require(Math.abs(field("SPRINT_SECONDS").getFloat(null)-2.4f)<.00001,"sprint duration");
        set.invoke(c,com.desertkun.brainout.content.active.Player.State.tacticalRun);
        field("sprintRemaining").setFloat(c,2.4f);field("sprintCooldown").setFloat(c,0);
        tick.invoke(c,2.39f);require(p.getState()==com.desertkun.brainout.content.active.Player.State.tacticalRun,"ended early");
        tick.invoke(c,.011f);require(p.getState()==com.desertkun.brainout.content.active.Player.State.run,"did not expire");
        require(field("sprintCooldown").getFloat(c)==1f,"cooldown not one second");
        tick.invoke(c,.99f);require(field("sprintCooldown").getFloat(c)>0&&!(Boolean)method("startTacticalRun").invoke(c),"cooldown bypass");
        tick.invoke(c,.011f);require(field("sprintCooldown").getFloat(c)==0,"cooldown did not clear");
        set.invoke(c,com.desertkun.brainout.content.active.Player.State.tacticalRun);
        set.invoke(c,com.desertkun.brainout.content.active.Player.State.sit);
        require(field("sprintCooldown").getFloat(c)==1f,"early cancel bypass");
        System.out.println("SPRINT_TIMERS_PASS 2.4s duration, 1s cooldown, early cancellation protected");
    }
    static void testArmSync(PlayerData player) throws Exception {
        PlayerComponentData component=player.getComponentWithSubclass(PlayerComponentData.class);
        java.lang.reflect.Method sync=PlayerComponentData.class.getDeclaredMethod("synchronizeSprintArmTracks",AnimationState.TrackEntry.class,AnimationState.TrackEntry.class);sync.setAccessible(true);
        SkeletonData data=BrainOut.ContentMgr.get("anim-actor",com.desertkun.brainout.content.Animation.class).getSkeletonData();
        AnimationState state=new AnimationState(new AnimationStateData(data));
        AnimationState.TrackEntry legs=state.setAnimation(0,"run-forward",true), arms=state.setAnimation(4,"sprint-short-refined-low-weapon-colt-hold",true);
        float duration=legs.getAnimationEnd(), armDuration=arms.getAnimationEnd();
        sync.invoke(component,legs,arms);
        for(int i=1;i<=240;i++){
            legs.setTrackTime(i*duration/40);sync.invoke(component,legs,arms);
            require(Math.abs(arms.getTrackTime()/armDuration-i/80f)<.0001,"arm phase drift");
            require(arms.getTimeScale()==0,"independent arm clock still running");
        }
        float before=arms.getTrackTime();legs=state.setAnimation(0,"run-backward",true);legs.setTrackTime(.13f);sync.invoke(component,legs,arms);
        require(Math.abs(arms.getTrackTime()-before)<.0001,"gait switch snapped arm");
        sync.invoke(component,legs,arms);require(Math.abs(arms.getTrackTime()-before)<.0001,"paused legs moved arms");
        System.out.println("ARM_SYNC_PASS 6 leg cycles = 3 arm cycles; gait switch continuous; pause stable");
    }
    static void renderPoses()throws Exception {
        com.desertkun.brainout.content.Animation actor=BrainOut.ContentMgr.get("anim-actor",com.desertkun.brainout.content.Animation.class);
        SkeletonData data=actor.getSkeletonData();
        int masks=0;
        for(Skin skin:data.getSkins()){
            Skeleton s=new Skeleton(data);s.setSkin(skin);s.setSlotsToSetupPose();
            if(s.getAttachment("hat","package")!=null){require(s.getAttachment("mask","anon-package")!=null,"missing mask "+skin.getName());masks++;}
        }
        require(BrainOut.ContentMgr.get("sl-msk-anon")!=null,"mask not in content");
        System.out.println("MASK_PASS skins="+masks);
        OrthographicCamera camera=new OrthographicCamera();camera.setToOrtho(false,1100f/80,750f/80);
        PolygonSpriteBatch batch=new PolygonSpriteBatch();batch.setProjectionMatrix(camera.combined);SkeletonRenderer renderer=new SkeletonRenderer();
        for(int frame=0;frame<24;frame++){
            Gdx.gl.glClearColor(.09f,.13f,.17f,1);Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);batch.begin();
            for(int k=0;k<3;k++){
                Skeleton s=new Skeleton(data);s.setSkin("bear");s.setSlotsToSetupPose();
                AnimationState st=new AnimationState(new AnimationStateData(data));st.setAnimation(0,k==2?"run-forward":"stay",true);
                String clip=k==0?"refined-low-weapon-colt-hold":k==1?"solo-weapon-colt-aim-weapon-1hand":"sprint-short-refined-low-weapon-colt-hold";
                st.setAnimation(1,clip,true);st.update(frame*.64f/24);st.apply(s);
                s.findBone("hands").setRotation(0);s.findBone("head").setRotation(0);s.setPosition((140+k*350)/80f,4);
                com.desertkun.brainout.content.Animation gun=BrainOut.ContentMgr.get("anim-weapon-colt",com.desertkun.brainout.content.Animation.class);
                if(gun==null)gun=BrainOut.ContentMgr.get("anim-colt",com.desertkun.brainout.content.Animation.class);
                if(gun!=null){Skeleton w=new Skeleton(gun.getSkeletonData());w.setSkin("weapon-default");w.setSlotsToSetupPose();com.esotericsoftware.spine.attachments.SkeletonAttachment a=new com.esotericsoftware.spine.attachments.SkeletonAttachment("gun");a.setSkeleton(w);s.findSlot("slot-primary").setAttachment(a);}
                renderer.update(s,null);renderer.draw(batch,s);
            }
            batch.end();png(String.format("pose-%02d.png",frame));
        }
        batch.dispose();System.out.println("ANIMATION_PASS");
    }
}
