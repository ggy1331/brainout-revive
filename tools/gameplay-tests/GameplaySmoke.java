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
            attachmentShowcase("stg");
            attachmentShowcase("mp40");
            testHands(game.getPlayerData());
            testRules(game.getPlayerData());
            testAimMode(game.getPlayerData());
            testConversions();
            loadoutMenu();
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
                for(String skinName:new String[]{"weapon-default"}){
                    Skeleton skeleton=new Skeleton(animation.getSkeletonData());skeleton.setSkin(skinName);skeleton.setSlotsToSetupPose();
                    com.desertkun.brainout.content.components.ReplaceSlotComponent replace=u.getComponent(com.desertkun.brainout.content.components.ReplaceSlotComponent.class);
                    replace.upgradeSkeleton(skeleton);
                    for(ObjectMap.Entry<String,String> r:replace.getReplace())require(skeleton.findSlot(r.key).getAttachment().getName().equals(r.value),"missing module "+u.getID()+" / "+skinName);
                }
            }
            require(total==(w.equals("stg")?36:37),w+" active module count "+total);
            require(item.getSkins().size==1,w+" retired skins");
            for(int variant=0;variant<3;variant++){
                InstrumentInfo info=new InstrumentInfo();info.instrument=BrainOut.ContentMgr.get("weapon-"+w,Instrument.class);info.skin=info.instrument.getDefaultSkin();
                if(variant>0)for(ObjectMap.Entry<String,Array<Upgrade>> slot:item.getUpgrades())info.upgrades.put(slot.key,slot.value.get(variant==1?0:Math.min(3,slot.value.size-1)));
                InstrumentIcon icon=new InstrumentIcon(info,1.5f,true);icon.setBounds(15+variant*360,540-row*350,350,170);icon.resetAnimation();icon.draw(b,1);
            }
            System.out.println("ATTACHMENTS_PASS "+w+" "+total+" choices, default skin only");row++;
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
    static void testConversions(){
        InstrumentSlotItem base=BrainOut.ContentMgr.get("sl-pri-ak74",InstrumentSlotItem.class);
        InstrumentSlotItem.InstrumentSelection selection=(InstrumentSlotItem.InstrumentSelection)base.getSelection();
        Upgrade conversion=BrainOut.ContentMgr.get("conversion-ak74-ak12",Upgrade.class);
        selection.getSelectedUpgrades().put("conversion",conversion);
        Instrument target=BrainOut.ContentMgr.get("weapon-ak12",Instrument.class);
        require(selection.getSkinItem()==target.getSlotItem(),"conversion skin catalog");
        com.desertkun.brainout.content.Skin skin=BrainOut.ContentMgr.get("skin-weapon-ak12-boom",com.desertkun.brainout.content.Skin.class);
        require(selection.getAvailableSkins().contains(skin,true),"AK12 skin visible");
        selection.setSkin(skin);
        require(selection.getInfo().skinFor(target)==skin,"converted skin applied");
        Json json=new Json();String encoded=json.toJson(selection);
        InstrumentSlotItem.InstrumentSelection restored=(InstrumentSlotItem.InstrumentSelection)base.getSelection();
        restored.read(json,new JsonReader().parse(encoded));
        require(restored.getSelectedSkin()==skin,"conversion skin serialized");
        restored.getSelectedUpgrades().remove("conversion");restored.setSkin(restored.getSelectedSkin());
        require(restored.getSelectedSkin()==base.getDefaultSkin(),"base skin restored after conversion removed");
        require(!restored.getAvailableSkins().contains(skin,true),"foreign skins removed");
        System.out.println("CONVERSION_SKINS_PASS catalog, application, save, removal");
    }
    static void testAimMode(PlayerData player) throws Exception {
        com.desertkun.brainout.components.my.MyPlayerComponent mine=player.getComponent(com.desertkun.brainout.components.my.MyPlayerComponent.class);
        com.desertkun.brainout.components.ClientPlayerComponent cpc=player.getComponent(com.desertkun.brainout.components.ClientPlayerComponent.class);
        require(mine!=null&&player.getCurrentInstrument() instanceof WeaponData,"aim test needs equipped local weapon");
        Input original=Gdx.input;com.badlogic.gdx.math.Vector2 old=new com.badlogic.gdx.math.Vector2(cpc.getMousePosition());
        java.lang.reflect.Field held=com.desertkun.brainout.controllers.KeyboardController.class.getDeclaredField("aimHeld");held.setAccessible(true);
        java.lang.reflect.Method constrain=mine.getClass().getDeclaredMethod("constrainAim",float.class);constrain.setAccessible(true);
        try{
            Gdx.input=(Input)java.lang.reflect.Proxy.newProxyInstance(Input.class.getClassLoader(),new Class[]{Input.class},(proxy,method,args)->{
                if(method.getName().equals("isButtonPressed")&&((Integer)args[0])==Input.Buttons.RIGHT)return true;
                return method.invoke(original,args);
            });
            held.setBoolean(null,true);cpc.getMousePosition().set(1,0);constrain.invoke(mine,30f);
            require(mine.isHighStanceHeld(),"aim hold not active");
            cpc.update(.1f);
            require(cpc.getAimOffset().epsilonEquals(cpc.getMousePosition(), .01f),"camera must follow actual aim marker");
            cpc.getMousePosition().set(.1f,0);constrain.invoke(mine,30f);
            require(cpc.getMousePosition().len()<1,"inner aim circle still blocks cursor: "+cpc.getMousePosition());
            System.out.println("AIM_MODE_PASS camera follows marker, no inner limit");
        }finally{Gdx.input=original;held.setBoolean(null,false);constrain.invoke(mine,30f);cpc.getMousePosition().set(old);}
    }
    static void loadoutMenu(){
        ShopCart cart=new ShopCart();cart.addDefaultItems();
        com.desertkun.brainout.menu.impl.PlayerSelectionMenu menu=new com.desertkun.brainout.menu.impl.PlayerSelectionMenu(cart);
        menu.onInit();menu.getViewport().update(1100,750,true);menu.act(.1f);menu.draw();png("loadout-tuning.png");
        require(hasTuningButton(menu.getRoot()),"loadout tuning gear missing");
        menu.onRelease();menu.dispose();System.out.println("LOADOUT_TUNING_PASS");
    }
    static boolean hasTuningButton(com.badlogic.gdx.scenes.scene2d.Group root){
        for(com.badlogic.gdx.scenes.scene2d.Actor child:root.getChildren()){
            if(child.getName()!=null&&child.getName().startsWith("loadout-tuning-"))return true;
            if(child instanceof com.badlogic.gdx.scenes.scene2d.Group&&hasTuningButton((com.badlogic.gdx.scenes.scene2d.Group)child))return true;
        }return false;
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
        selection.getSelectedUpgrades().put("scope",BrainOut.ContentMgr.get("vg-stg-scope-7",Upgrade.class));
        com.desertkun.brainout.menu.impl.UpgradeInstrumentMenu menu=new com.desertkun.brainout.menu.impl.UpgradeInstrumentMenu(item,w,()->{});
        menu.onInit();menu.getViewport().update(1100,750,true);menu.act(.1f);menu.draw();png("attachment-menu.png");
        com.badlogic.gdx.scenes.scene2d.ui.Table tooltip=(com.badlogic.gdx.scenes.scene2d.ui.Table)
            new com.desertkun.brainout.menu.ui.UnlockTooltip.UnlockTooltipCreator(
                BrainOut.ContentMgr.get("vg-stg-butt-0",Upgrade.class),null).get();
        tooltip.pack();tooltip.setPosition(15,350);menu.addActor(tooltip);
        menu.act(.1f);menu.draw();png("attachment-tooltip.png");
        tooltip.remove();
        tooltip=(com.badlogic.gdx.scenes.scene2d.ui.Table)new com.desertkun.brainout.menu.ui.UnlockTooltip.UnlockTooltipCreator(
            BrainOut.ContentMgr.get("vg-stg-clip-2",Upgrade.class),null).get();
        tooltip.pack();tooltip.setPosition(15,350);menu.addActor(tooltip);
        menu.act(.1f);menu.draw();png("magazine-tooltip.png");menu.onRelease();menu.dispose();
        System.out.println("ATTACHMENT_MENU_PASS");
    }
    static void attachmentShowcase(String weapon){
        FrameBuffer f=new FrameBuffer(Pixmap.Format.RGBA8888,1400,420,false);f.begin();
        Gdx.gl.glClearColor(.13f,.14f,.14f,1);Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);
        OrthographicCamera camera=new OrthographicCamera();camera.setToOrtho(false,1400,420);
        SpriteBatch b=new SpriteBatch();b.setProjectionMatrix(camera.combined);b.begin();
        String[] slots={"barrel","butt","clip","scope","silencer","grip"};
        int[][] choices=weapon.equals("stg") ? new int[][]{{0,0,1,7,0,1},{1,3,0,8,4,3},{2,4,2,18,1,0},{3,1,3,9,2,6}}
            : new int[][]{{0,0,0,1,0,1},{1,3,0,5,4,3},{2,4,2,11,1,0},{3,2,3,9,2,6}};
        for(int i=0;i<choices.length;i++){
            InstrumentInfo info=new InstrumentInfo();info.instrument=BrainOut.ContentMgr.get("weapon-"+weapon,Instrument.class);info.skin=info.instrument.getDefaultSkin();
            for(int j=0;j<slots.length;j++)info.upgrades.put(slots[j],BrainOut.ContentMgr.get("vg-"+weapon+"-"+slots[j]+"-"+choices[i][j],Upgrade.class));
            InstrumentIcon icon=new InstrumentIcon(info,3f,true);icon.setBounds(15+(i%2)*700,20+(1-i/2)*210,500,180);icon.resetAnimation();icon.draw(b,1);
        }
        b.end();Pixmap p=ScreenUtils.getFrameBufferPixmap(0,0,1400,420);PixmapIO.writePNG(Gdx.files.absolute(System.getenv("GAMEPLAY_LAB")+"/"+weapon+"-showcase.png"),p,-1,true);p.dispose();f.end();f.dispose();b.dispose();
    }
    static void testHands(PlayerData player) throws Exception {
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
            if(id.equals("colt")){
                com.desertkun.brainout.components.my.MyWeaponComponent mwc=new com.desertkun.brainout.components.my.MyWeaponComponent(d,new com.desertkun.brainout.data.consumable.ConsumableRecord());
                mwc.getSlots().put(Constants.Properties.SLOT_PRIMARY,slots[0]);mwc.getSlots().put(Constants.Properties.SLOT_SECONDARY,slots[1]);mwc.setCurrentSlot(slots[0]);
                java.lang.reflect.Field equipped=PlayerData.class.getDeclaredField("currentInstrument");equipped.setAccessible(true);Object previous=equipped.get(player);equipped.set(player,d);
                try{
                    for(TestSlot slot:slots)slot.reset(0);
                    mwc.onEvent(com.desertkun.brainout.events.GameControllerEvent.obtain(com.desertkun.brainout.events.GameControllerEvent.Action.reload));
                    require(slots[0].isReloadingOrChambering()&&!slots[1].isReloadingOrChambering(),"right reload must not start together with left");
                    mwc.update(.016f);
                    require(!slots[1].isReloadingOrChambering(),"right reload must wait at least next animation frame");
                    java.lang.reflect.Field frame=mwc.getClass().getDeclaredField("rightReloadFrame");frame.setAccessible(true);frame.setLong(mwc,Gdx.graphics.getFrameId()-1);
                    mwc.update(.016f);
                    require(slots[1].isReloadingOrChambering(),"right reload did not start after microdelay");
                    System.out.println("PAIRED_MICRODELAY_PASS first hand, next frame second hand");
                }finally{equipped.set(player,previous);}
            }
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
            if(WorldVisibility.isSolidSurface(candidate)&&!candidate.getCreator().isCanBeSeenTrough()){solid=candidate;break;}
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
        Gdx.gl.glClearColor(.6f,.4f,.2f,1);Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);
        b.begin();map.visibilityMask.begin(b,context);map.visibilityMask.clip(b,true);b.end();
        ShapeRenderer shape=new ShapeRenderer();shape.setProjectionMatrix(cam.combined);shape.begin(ShapeRenderer.ShapeType.Filled);shape.setColor(1,0,0,1);shape.rect(ox+12,oy+4,1,8);shape.end();
        b.begin();map.visibilityMask.clip(b,false);map.visibilityMask.shade(b,context);b.end();
        Pixmap p=ScreenUtils.getFrameBufferPixmap(0,0,720,540);
        int red=0,hidden=0;for(int y=4*30;y<12*30;y++) {int rgba=p.getPixel((int)(12.5*30),y);if(((rgba>>>24)&255)>220&&((rgba>>>16)&255)<30)red++;else hidden++;}
        require(red>20&&hidden>20,"partial actor must contain visible AND hidden fragments: "+red+"/"+hidden);
        int shaded=p.getPixel(20*30,12*30);int sr=(shaded>>>24)&255,sg=(shaded>>>16)&255,sb=(shaded>>>8)&255;
        require(Math.abs(sr-116)<=3&&Math.abs(sg-78)<=3&&Math.abs(sb-39)<=3,"shade must preserve hue and darken only 24%: "+Integer.toHexString(shaded));
        System.out.println("VISIBILITY_COLOR_PASS hue preserved, 24% darker");
        ActiveData fire=new com.desertkun.brainout.content.active.Active().getData(player.getDimension());
        fire.addComponent(new com.desertkun.brainout.content.components.SimplePhysicsComponent().getComponent(fire));
        require(!WorldVisibility.isMapDecoration(fire),"physics object must remain clipped");
        com.desertkun.brainout.content.components.ClientCampFireComponent fireComponent=new com.desertkun.brainout.content.components.ClientCampFireComponent();
        fireComponent.read(new com.badlogic.gdx.utils.Json(),new com.badlogic.gdx.utils.JsonReader().parse("{}"));
        fire.addComponent(fireComponent.getComponent(fire));
        require(WorldVisibility.isMapDecoration(fire),"physics campfire must remain environment");
        require(!WorldVisibility.isMapDecoration(player),"player must not be environment");
        // Environment particles and allied identity widgets survive the same stencil that hides bodies.
        com.desertkun.brainout.data.containers.CompleteDataContainer<com.desertkun.brainout.data.effect.EffectData> fx = new com.desertkun.brainout.data.containers.CompleteDataContainer<>();
        for (int i=0;i<2;i++) {
            final int index=i;
            com.desertkun.brainout.data.effect.EffectData effect=new com.desertkun.brainout.data.effect.EffectData(null,null) {
                public void render(com.badlogic.gdx.graphics.g2d.Batch batch,RenderContext rc) {
                    batch.end();shape.begin(ShapeRenderer.ShapeType.Filled);shape.setColor(0,1,0,1);
                    shape.rect(ox+17+index*2,oy+12,1,1);shape.end();batch.begin();
                }
                public void init(){} public void update(float dt){} public boolean hasUpdate(){return false;}
                public boolean hasRender(){return true;} public boolean done(){return false;}
            };
            effect.setEnvironment(i==0);fx.add(effect);
        }
        b.begin();map.visibilityMask.effects(fx).render(b,context);b.end();
        Pixmap effectsImage=ScreenUtils.getFrameBufferPixmap(0,0,720,540);
        require(((effectsImage.getPixel(525,375)>>>16)&255)>240,"environment hidden behind wall");
        require(((effectsImage.getPixel(585,375)>>>16)&255)<150,"combat effect leaked behind wall");
        effectsImage.dispose();
        com.desertkun.brainout.data.components.ActiveStatsComponentData stats=new com.desertkun.brainout.data.components.ActiveStatsComponentData(player,new com.desertkun.brainout.content.components.ActiveStatsComponent());
        com.badlogic.gdx.scenes.scene2d.Group parent=new com.badlogic.gdx.scenes.scene2d.Group();parent.setPosition(ox+17,oy+14);
        com.badlogic.gdx.scenes.scene2d.Actor badge=new com.badlogic.gdx.scenes.scene2d.Actor(){
            public void draw(com.badlogic.gdx.graphics.g2d.Batch batch,float alpha){
                batch.end();shape.begin(ShapeRenderer.ShapeType.Filled);shape.setColor(0,0,1,1);
                shape.rect(getX(),getY(),1,1);shape.end();batch.begin();
            }
        };parent.addActor(badge);
        java.lang.reflect.Method identity=stats.getClass().getDeclaredMethod("renderIdentity",com.badlogic.gdx.graphics.g2d.Batch.class,com.badlogic.gdx.scenes.scene2d.Actor[].class);identity.setAccessible(true);
        b.begin();map.visibilityMask.clip(b,true);identity.invoke(stats,b,new com.badlogic.gdx.scenes.scene2d.Actor[]{badge});
        require(Gdx.gl.glIsEnabled(GL20.GL_STENCIL_TEST),"identity did not restore body stencil");
        require(badge.getX()==0&&badge.getY()==0,"identity changed widget layout");map.visibilityMask.clip(b,false);b.end();
        Pixmap identityImage=ScreenUtils.getFrameBufferPixmap(0,0,720,540);
        require(((identityImage.getPixel(525,435)>>>8)&255)>240,"allied identity hidden behind wall");identityImage.dispose();
        System.out.println("ENVIRONMENT_IDENTITY_PASS environment and badge visible; combat effect hidden; stencil restored");
        PixmapIO.writePNG(Gdx.files.absolute(System.getenv("GAMEPLAY_LAB")+"/visibility.png"),p,-1,true);p.dispose();f.end();f.dispose();b.dispose();shape.dispose();
        player.setX(px);player.setY(py);
        for(int l=0;l<2;l++)for(int x=0;x<24;x++)for(int y=0;y<18;y++)map.setBlockNoRefresh(ox+x,oy+y,saved[l][x][y],layers[l],false);
        System.out.println("PIXEL_CLIP_PASS visible="+red+" hidden="+hidden);
        AimCursorCollision cursor=new AimCursorCollision();com.badlogic.gdx.math.Vector2 result=new com.badlogic.gdx.math.Vector2();
        // Restore the isolated wall after testing the stencil, for cursor sweeps.
        for(int l=0;l<2;l++)for(int x=0;x<24;x++)for(int y=0;y<18;y++)map.setBlockNoRefresh(ox+x,oy+y,null,layers[l],false);
        for(int y=7;y<18;y++)map.setBlockNoRefresh(ox+10,oy+y,solid,layers[0],false);
        cursor.move(map,player,ox+5,oy+8,ox+18,oy+10,result);
        require(result.x<ox+10 && result.y>oy+9.8f,"cursor must stop and slide along wall: "+result);
        cursor.move(map,player,result.x,result.y,ox+13,oy+5,result);
        require(result.x>ox+10&&result.y<oy+7,"cursor must round wall edge: "+result);
        com.desertkun.brainout.content.block.Concrete platform=BrainOut.ContentMgr.queryOneContentTpl(
            com.desertkun.brainout.content.block.Concrete.class,c->c.getContactShape() instanceof com.desertkun.brainout.content.block.contact.CSPlatform);
        require(platform!=null,"platform test content");
        map.setBlockNoRefresh(ox+10,oy+8,platform.getBlock(),layers[0],false);
        require(!WorldVisibility.isSolidSurface(platform.getBlock()),"platform must not block visibility");
        cursor.move(map,player,ox+5,oy+8.5f,ox+15,oy+8.5f,result);
        require(result.x>ox+14.9f,"platform must not block cursor");
        for(int y=7;y<18;y++)map.setBlockNoRefresh(ox+10,oy+y,null,layers[0],false);
        PlayerData target=new PlayerData((com.desertkun.brainout.content.active.Player)player.getCreator(),player.getDimension());
        target.setId(-90321);target.setX(ox+10);target.setY(oy+8);
        target.getComponentWithSubclass(SimplePhysicsComponentData.class).getHalfSize().set(.5f,1);
        java.lang.reflect.Field alive=ActiveData.class.getDeclaredField("alive");alive.setAccessible(true);alive.set(target,true);
        map.getActives().addItem(target.getId(),target);
        try{
            cursor.move(map,player,ox+7,oy+8,ox+13,oy+8,result);
            require(result.x<ox+9.6f,"cursor passed through player: "+result);
            cursor.move(map,player,result.x,result.y,ox+12,oy+10,result);
            require(result.x>ox+10.5f && result.y>oy+9,"cursor did not go around player: "+result);
        }finally{map.getActives().removeItem(target.getId());}
        for(int l=0;l<2;l++)for(int x=0;x<24;x++)for(int y=0;y<18;y++)map.setBlockNoRefresh(ox+x,oy+y,saved[l][x][y],layers[l],false);
        System.out.println("CURSOR_COLLISION_PASS wall sweep, sliding, platform, player");
    }
}
