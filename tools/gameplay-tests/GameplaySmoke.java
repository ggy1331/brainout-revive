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

public class GameplaySmoke {
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
            validateAttachments();
            contactSheets();
            testHands(game.getPlayerData());
            testRules(game.getPlayerData());
            testMask(game);
            attachmentMenu();
            System.out.println("GAMEPLAY_SMOKE_PASS");
        }catch(Throwable ex){ex.printStackTrace();System.out.println("GAMEPLAY_SMOKE_FAIL");}
        Gdx.app.exit();
    }
    static void validateAttachments(){
        OrthographicCamera camera=new OrthographicCamera();camera.setToOrtho(false,1100,750);
        SpriteBatch b=new SpriteBatch();b.setProjectionMatrix(camera.combined);
        Gdx.gl.glClearColor(.11f,.12f,.13f,1);Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);
        b.begin();
        int row=0;
        for(String w:new String[]{"stg","mp40"}){
            InstrumentSlotItem item=BrainOut.ContentMgr.get("sl-pri-"+w,InstrumentSlotItem.class);
            int total=0;
            com.desertkun.brainout.content.Animation animation=BrainOut.ContentMgr.get("anim-"+w,com.desertkun.brainout.content.Animation.class);
            for(ObjectMap.Entry<String,Array<Upgrade>> slot:item.getUpgrades())for(Upgrade u:slot.value){
                total++;
                for(String skinName:w.equals("stg")?new String[]{"weapon-default","weapon-emile","weapon-wunderwaffe"}:new String[]{"weapon-default","weapon-orange"}){
                    Skeleton skeleton=new Skeleton(animation.getSkeletonData());skeleton.setSkin(skinName);skeleton.setSlotsToSetupPose();
                    com.desertkun.brainout.content.components.ReplaceSlotComponent replace=u.getComponent(com.desertkun.brainout.content.components.ReplaceSlotComponent.class);
                    replace.upgradeSkeleton(skeleton);
                    for(ObjectMap.Entry<String,String> r:replace.getReplace())require(skeleton.findSlot(r.key).getAttachment().getName().equals(r.value),"missing module "+u.getID()+" / "+skinName);
                }
            }
            require(total==61,w+" expected61 actual"+total);
            for(int variant=0;variant<3;variant++){
                InstrumentInfo info=new InstrumentInfo();info.instrument=BrainOut.ContentMgr.get("weapon-"+w,Instrument.class);info.skin=info.instrument.getDefaultSkin();
                if(variant>0)for(ObjectMap.Entry<String,Array<Upgrade>> slot:item.getUpgrades())info.upgrades.put(slot.key,slot.value.get(variant==1?0:Math.min(3,slot.value.size-1)));
                InstrumentIcon icon=new InstrumentIcon(info,1.5f,true);icon.setBounds(15+variant*360,540-row*350,350,170);icon.resetAnimation();icon.draw(b,1);
            }
            System.out.println("ATTACHMENTS_PASS "+w+" 61 choices, every skin");row++;
        }
        b.end();png("weapons.png");b.dispose();
        require(BrainOut.ContentMgr.get("paired-weapon-supershorty",Weapon.class).hasSequentialPairedReload(),"Serbu exception");
        require(BrainOut.ContentMgr.get("paired-weapon-peacemaker",Weapon.class).hasSequentialPairedReload(),"Peacemaker exception");
        require(!BrainOut.ContentMgr.get("paired-weapon-colt",Weapon.class).hasSequentialPairedReload(),"Colt parallel rule");
    }
    static class TestSlot extends com.desertkun.brainout.components.ClientWeaponSlotComponent {
        TestSlot(WeaponData data,Weapon.WeaponProperties props,String slot,GetOtherSlot other){super(data,new com.desertkun.brainout.data.consumable.ConsumableRecord(),props,slot,"",other);}
        protected void onReload(Instrument.Action action){}
        protected void onFetch(Instrument.Action action){}
        protected void onLoadMagazine(){}
        protected void onFetchRounds(){}
        protected void onUpdateState(){}
        void reset(int rounds){state=State.idle;setRounds(rounds,-1);setChambered(0,-1);}
    }
    static void testRules(PlayerData player) throws Exception {
        PlayerControllerComponentData control=player.getComponentWithSubclass(PlayerControllerComponentData.class);
        java.lang.reflect.Method dive=PlayerControllerComponentData.class.getDeclaredMethod("startSlide");dive.setAccessible(true);
        require(!(Boolean)dive.invoke(control),"slide must be disabled");
        com.desertkun.brainout.content.bullet.Bullet buck=BrainOut.ContentMgr.get("bullet-12-76",com.desertkun.brainout.content.bullet.Bullet.class);
        com.desertkun.brainout.data.bullet.BulletData data=buck.getData(new PointLaunchData(1,1,0,player.getDimension()),100,player.getDimension());
        require(buck.getAmountPerLaunch()==9,"buckshot pellet count");
        require(Math.abs(data.getDamage()-100*buck.getDamageCoeficient()*1.3f/9)<0.001f,"pellet buff +30%");
        System.out.println("RULES_PASS pellets="+data.getDamage()+" slide disabled");
    }
    static void contactSheets(){
        for(String w:new String[]{"stg","mp40"}){
            FrameBuffer f=new FrameBuffer(Pixmap.Format.RGBA8888,1100,1760,false);f.begin();
            Gdx.gl.glClearColor(.14f,.15f,.15f,1);Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);
            OrthographicCamera camera=new OrthographicCamera();camera.setToOrtho(false,1100,1760);
            SpriteBatch b=new SpriteBatch();b.setProjectionMatrix(camera.combined);BitmapFont font=new BitmapFont();font.setColor(.7f,.7f,.65f,1);b.begin();
            InstrumentSlotItem item=BrainOut.ContentMgr.get("sl-pri-"+w,InstrumentSlotItem.class);int index=0;
            for(ObjectMap.Entry<String,Array<Upgrade>> slot:item.getUpgrades())for(Upgrade upgrade:slot.value){
                InstrumentInfo info=new InstrumentInfo();info.instrument=BrainOut.ContentMgr.get("weapon-"+w,Instrument.class);info.skin=info.instrument.getDefaultSkin();info.upgrades.put(slot.key,upgrade);
                int x=(index%4)*275,y=1760-(index/4+1)*110;
                InstrumentIcon icon=new InstrumentIcon(info,1.7f,true);icon.setBounds(x,y+5,270,90);icon.resetAnimation();icon.draw(b,1);
                font.draw(b,upgrade.getID(),x+8,y+14);index++;
            }
            b.end();Pixmap p=ScreenUtils.getFrameBufferPixmap(0,0,1100,1760);PixmapIO.writePNG(Gdx.files.absolute(System.getenv("GAMEPLAY_LAB")+"/"+w+"-mounted.png"),p,-1,true);p.dispose();f.end();f.dispose();font.dispose();b.dispose();
        }
    }
    static void attachmentMenu() {
        InstrumentSlotItem item=BrainOut.ContentMgr.get("sl-pri-stg",InstrumentSlotItem.class);
        Instrument w=BrainOut.ContentMgr.get("weapon-stg",Instrument.class);
        InstrumentSlotItem.InstrumentSelection selection=(InstrumentSlotItem.InstrumentSelection)item.getStaticSelection();
        selection.getInfo().skin=w.getDefaultSkin();
        selection.getSelectedUpgrades().put("clip",BrainOut.ContentMgr.get("vg-stg-clip-2",Upgrade.class));
        selection.getSelectedUpgrades().put("scope",BrainOut.ContentMgr.get("vg-stg-scope-1",Upgrade.class));
        com.desertkun.brainout.menu.impl.UpgradeInstrumentMenu menu=new com.desertkun.brainout.menu.impl.UpgradeInstrumentMenu(item,w,()->{});
        menu.onInit();menu.getViewport().update(1100,750,true);menu.act(.1f);menu.draw();png("attachment-menu.png");menu.onRelease();menu.dispose();
        System.out.println("ATTACHMENT_MENU_PASS");
    }
    static void testHands(PlayerData player){
        for(String id:new String[]{"colt","welrod","supershorty","peacemaker"}){
            Weapon w=BrainOut.ContentMgr.get("paired-weapon-"+id,Weapon.class);
            WeaponData d=w.getWeaponData(player.getDimension());InstrumentInfo info=new InstrumentInfo();info.instrument=w;info.skin=w.getDefaultSkin();d.setInfo(info);d.setOwner(player);
            TestSlot[] slots=new TestSlot[2];
            slots[0]=new TestSlot(d,w.getPrimaryProperties(),Constants.Properties.SLOT_PRIMARY,n->slots[1]);
            slots[1]=new TestSlot(d,w.getComponent(com.desertkun.brainout.content.components.SecondaryWeaponSlotComponent.class).getWeaponProperties(),Constants.Properties.SLOT_SECONDARY,n->slots[0]);
            for(TestSlot slot:slots) player.getComponent(com.desertkun.brainout.components.PlayerOwnerComponent.class).putAmmo(100,slot.getBullet(),-1);
            for(TestSlot slot:slots)slot.reset(0);
            boolean a=slots[0].doReload(true),b=slots[1].doReload(true);
            require(a,"left reload "+id);
            require(b!=w.hasSequentialPairedReload(),"right reload policy "+id+" "+b);
            if(id.equals("welrod")||id.equals("supershorty")){
                for(TestSlot slot:slots)slot.reset(2);
                slots[0].doFetch();slots[1].doFetch();
                require(slots[0].getState()==com.desertkun.brainout.components.WeaponSlotComponent.State.fetching && slots[1].getState()==com.desertkun.brainout.components.WeaponSlotComponent.State.fetching,"simultaneous chambering "+id);
            }
            System.out.println("HANDS_PASS "+id);
        }
    }
    static void testMask(CSGame game) throws Exception {
        PlayerData player=game.getPlayerData();ClientMap map=(ClientMap)player.getMap();
        float px=player.getX(),py=player.getY();
        BlockData solid=null;
        for(int x=0;x<map.getWidth()&&solid==null;x++)for(int y=0;y<map.getHeight();y++){
            BlockData candidate=map.getBlockAt(x,y,Constants.Layers.BLOCK_LAYER_FOREGROUND);
            if(candidate!=null&&!candidate.getCreator().isCanBeSeenTrough()){solid=candidate;break;}
        }
        require(solid!=null,"no test wall found");
        // Save/restore a local test rectangle; no changes are sent to the server.
        int ox=10,oy=10;
        BlockData[][][] saved=new BlockData[2][24][18];int[] layers={Constants.Layers.BLOCK_LAYER_FOREGROUND,Constants.Layers.BLOCK_LAYER_UPPER};
        for(int l=0;l<2;l++)for(int x=0;x<24;x++)for(int y=0;y<18;y++){
            saved[l][x][y]=map.getBlockAt(ox+x,oy+y,layers[l]);map.setBlockNoRefresh(ox+x,oy+y,null,layers[l],false);
        }
        for(int y=7;y<18;y++)map.setBlockNoRefresh(ox+10,oy+y,solid, layers[0],false);
        player.setX(ox+5);player.setY(oy+6);
        FrameBuffer f=new FrameBuffer(Pixmap.Format.RGBA8888,720,540,true,true);f.begin();
        OrthographicCamera cam=new OrthographicCamera();cam.setToOrtho(false,24,18);cam.position.set(ox+12,oy+9,0);cam.update();
        SpriteBatch b=new SpriteBatch();b.setProjectionMatrix(cam.combined);RenderContext context=new RenderContext(720,540);context.camera=cam;
        Gdx.gl.glClearColor(.5f,.5f,.5f,1);Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);
        b.begin();map.visibilityMask.begin(b,context);map.visibilityMask.clip(b,true);b.end();
        ShapeRenderer shape=new ShapeRenderer();shape.setProjectionMatrix(cam.combined);shape.begin(ShapeRenderer.ShapeType.Filled);shape.setColor(1,0,0,1);shape.rect(ox+12,oy+4,1,8);shape.end();
        b.begin();map.visibilityMask.clip(b,false);map.visibilityMask.shade(b,context);b.end();
        Pixmap p=ScreenUtils.getFrameBufferPixmap(0,0,720,540);
        int red=0,hidden=0;for(int y=4*30;y<12*30;y++) {int rgba=p.getPixel((int)(12.5*30),y);if(((rgba>>>24)&255)>220&&((rgba>>>16)&255)<30)red++;else hidden++;}
        require(red>20&&hidden>20,"partial actor must contain visible AND hidden fragments: "+red+"/"+hidden);
        PixmapIO.writePNG(Gdx.files.absolute(System.getenv("GAMEPLAY_LAB")+"/visibility.png"),p,-1,true);p.dispose();f.end();f.dispose();b.dispose();shape.dispose();
        player.setX(px);player.setY(py);
        for(int l=0;l<2;l++)for(int x=0;x<24;x++)for(int y=0;y<18;y++)map.setBlockNoRefresh(ox+x,oy+y,saved[l][x][y],layers[l],false);
        System.out.println("PIXEL_CLIP_PASS visible="+red+" hidden="+hidden);
    }
}
