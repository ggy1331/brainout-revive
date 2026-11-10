package com.desertkun.brainout.menu.impl;

import com.badlogic.gdx.Gdx;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.client.states.CSEndGame;
import com.desertkun.brainout.client.states.CSGame;
import com.desertkun.brainout.client.states.CSJoinRoom;
import com.desertkun.brainout.common.enums.DisconnectReason;
import com.desertkun.brainout.menu.Menu;
import com.desertkun.brainout.menu.popups.AlertPopup;
import org.anthillplatform.runtime.services.LoginService;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.concurrent.*;
import java.util.function.Consumer;

public final class HomeHub {
    public static final String ENDPOINT = System.getenv("BRAINOUT_HUB_ENDPOINT");
    public static boolean OWNER = System.getenv("BRAINOUT_OWNER_KEY") != null;
    private static final ExecutorService worker = Executors.newSingleThreadExecutor(r -> {
        Thread t=new Thread(r,"hub-control"); t.setDaemon(true); return t;
    });
    private static boolean waiting, polling, leaving;
    private static long nextPoll, lastSuccess=System.currentTimeMillis();
    private static String lastTarget="";
    private static long retryAt;

    private static String guestRoomToken;
    private static int generation;
    /** From the last hub state: a match is running / this player left it for the hub. */
    public static boolean MATCH_RUNNING, AWAY_FROM_MATCH;

    public static String roomToken(String localToken) {
        return guestRoomToken != null ? guestRoomToken : localToken;
    }

    private static String token() {
        LoginService login=LoginService.Get();
        return login==null || login.getCurrentAccessToken()==null ? "" : login.getCurrentAccessToken().get();
    }

    private static JSONObject request(String action, JSONObject body,String token) throws Exception {
        HttpURLConnection c=(HttpURLConnection)new URL("http://"+ENDPOINT+"/hub/"+action).openConnection(Proxy.NO_PROXY);
        try {
            c.setConnectTimeout(1800); c.setReadTimeout("leave".equals(action) ? 1500 : body==null ? 3500 : 100000);
            c.setRequestProperty("X-Token",token);
            if(System.getenv("BRAINOUT_OWNER_KEY") != null) c.setRequestProperty("X-Hub-Key",System.getenv("BRAINOUT_OWNER_KEY"));
            if(body!=null) {
                c.setRequestMethod("POST"); c.setDoOutput(true);
                c.setRequestProperty("Content-Type","application/json");
                try(OutputStream out=c.getOutputStream()){out.write(body.toString().getBytes(StandardCharsets.UTF_8));}
            }
            if(c.getResponseCode()!=200) throw new IOException("Хаб не принял запрос ("+c.getResponseCode()+").");
            try(BufferedReader r=new BufferedReader(new InputStreamReader(c.getInputStream(),StandardCharsets.UTF_8))){
                StringBuilder s=new StringBuilder(); String line;
                while((line=r.readLine())!=null)s.append(line);
                return new JSONObject(s.toString());
            }
        } finally {c.disconnect();}
    }

    public static void tick() {
        if(ENDPOINT==null || leaving || polling || waiting || System.currentTimeMillis()<nextPoll) return;
        String credential=token();
        if(credential.isEmpty())return;
        nextPoll=System.currentTimeMillis()+900;
        int epoch = generation;
        polling=true;
        worker.execute(() -> {
            try {
                JSONObject state=request("state",null,credential);
                Gdx.app.postRunnable(() -> {
                    if (epoch != generation) return;
                    polling=false; lastSuccess=System.currentTimeMillis();
                    MATCH_RUNNING=state.optBoolean("running",false);
                    AWAY_FROM_MATCH=state.optBoolean("away",false);
                    String target=state.optString("target","");
                    // also from the end-of-match results screen (CSEndGame): before, a return
                    // requested there waited for the next round and looked like "nothing happens"
                    if(!leaving && !target.isEmpty() && (BrainOutClient.ClientController.getState(CSGame.class)!=null
                        || BrainOutClient.ClientController.getState(CSEndGame.class)!=null) &&
                        (!target.equals(lastTarget)||System.currentTimeMillis()>retryAt)) {
                        lastTarget=target; retryAt=System.currentTimeMillis()+7000;
                        BrainOutClient.ClientController.setState(new CSJoinRoom(target));
                    }
                    if(target.isEmpty())lastTarget="";
                });
            } catch(Exception e) { Gdx.app.postRunnable(() -> {
                if (epoch != generation) return;
                polling=false;
                if(!OWNER && System.currentTimeMillis()-lastSuccess>12000) changeHost("home");
            }); }
        });
    }

    public static void query(String action,JSONObject body,Consumer<JSONObject> done) {
        if(waiting||leaving)return;
        waiting=true; String credential=token();
        worker.execute(() -> {
            try {
                JSONObject result=request(action,body,credential);
                Gdx.app.postRunnable(() -> {waiting=false;nextPoll=0;if(done!=null)done.accept(result);});
            } catch(Exception e) {
                Gdx.app.postRunnable(() -> {waiting=false;Menu m=BrainOutClient.getInstance().topState().topMenu();
                    if(m!=null)m.pushMenu(new AlertPopup("Ошибка соединения с хабом: "+e.getMessage()));});
            }
        });
    }
    public static void openMatch(Menu menu, Runnable open) {
        if (OWNER) open.run();
        else menu.pushMenu(new AlertPopup("Матч может запустить только хозяин хаба."));
    }
    public static void zone(){query("zone",new JSONObject(),null);}
    public static void back(){
        if(!OWNER)changeHost("home");
        else query("return",new JSONObject(),null);
    }
    /** Owner: go to the hub alone, the match goes on for the others. */
    public static void home(){
        if(!OWNER)changeHost("home");
        else {nextPoll=0;query("home",new JSONObject(),null);}
    }
    /** Owner: end the running match, everybody goes to the hub. */
    public static void endMatch(){nextPoll=0;query("return",new JSONObject(),null);}
    /** Back into the running match after leaving it for the hub. */
    public static void rejoin(){nextPoll=0;query("rejoin",new JSONObject(),null);}
    public static void confirmEndMatch(){
        Menu popup = new com.desertkun.brainout.menu.popups.ConfirmationPopup(
            "Завершить матч для всех? Все игроки вернутся в хаб.") {
            @Override public void yes(){endMatch();}
        };
        com.desertkun.brainout.gs.GameState gs = BrainOutClient.getInstance().topState();
        if (gs == null) return;
        Menu top = gs.topMenu();
        if (top != null) top.pushMenu(popup); else gs.pushMenu(popup);
    }
    public static void changeHost(String endpoint) {
        if (leaving || waiting) return;
        boolean home = "home".equals(endpoint);
        if (home && OWNER) return;
        leaving = true;
        generation++;
        polling = false;
        String localToken = token();
        Runnable switchRoom = () -> worker.execute(() -> {
            boolean detached = false;
            try {
                JSONObject result = null;
                if (!OWNER) {
                    result = request("unvisit", new JSONObject(), localToken);
                    detached = true;
                }
                if (!home) result = request("visit", new JSONObject().put("endpoint",endpoint), localToken);
                final String target = result.getString("target");
                final String ticket = home ? null : result.getString("roomToken");
                Gdx.app.postRunnable(() -> {
                    OWNER = home;
                    guestRoomToken = ticket;
                    lastTarget = "";
                    nextPoll = retryAt = 0;
                    lastSuccess = System.currentTimeMillis();
                    leaving = false;
                    BrainOutClient.ClientController.setState(new CSJoinRoom(target));
                });
            } catch(Exception ex) {
                final boolean returnHome = detached;
                Gdx.app.postRunnable(() -> {
                    leaving = false;
                    if (returnHome) {
                        guestRoomToken = null;
                        OWNER = true;
                        BrainOutClient.ClientController.setState(new com.desertkun.brainout.client.states.CSFindLobby());
                    }
                    Menu m = BrainOutClient.getInstance().topState().topMenu();
                    if (m != null) m.pushMenu(new AlertPopup("Не удалось перейти в хаб: "+ex.getMessage()));
                });
            }
        });
        if (!OWNER && BrainOutClient.ClientController.isConnected())
            BrainOutClient.ClientController.disconnect(DisconnectReason.leave, switchRoom);
        else switchRoom.run();
    }
    static void installUpdate() { switchEndpoint("install-update"); }

    private static void switchEndpoint(String endpoint) {
        try {
            Path file=Paths.get(System.getenv("BRAINOUT_HUB_NEXT"));
            Path temp=file.resolveSibling("next.tmp");
            Files.write(temp,endpoint.getBytes(StandardCharsets.UTF_8));
            Files.move(temp,file,StandardCopyOption.REPLACE_EXISTING);
            leaving=true;
            if(BrainOutClient.ClientController.getState(CSGame.class)!=null)
                BrainOutClient.ClientController.disconnect(DisconnectReason.leave,()->Gdx.app.exit());
            else Gdx.app.exit();
        } catch(IOException e){ throw new IllegalStateException(e); }
    }
}
