package com.desertkun.brainout.menu.impl;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.scenes.scene2d.Actor;
import com.badlogic.gdx.scenes.scene2d.InputEvent;
import com.badlogic.gdx.scenes.scene2d.ui.*;
import com.badlogic.gdx.scenes.scene2d.utils.ChangeListener;
import com.badlogic.gdx.scenes.scene2d.utils.ClickListener;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.menu.Menu;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public final class HubPanel extends Menu {
    private final boolean browser;
    private Table box, list;
    private boolean scanning, closed;
    private float timeout;
    private Label status;
    private boolean checkingAddress;
    public HubPanel(boolean browser){this.browser=browser;}
    static TextButton button(String title,Runnable action) {
        TextButton b=new TextButton(title,BrainOutClient.Skin,"button-default");
        b.addListener(new ClickListener(){public void clicked(InputEvent e,float x,float y){action.run();}});
        return b;
    }
    static void add(Table t,String name,Runnable r){
        t.add(button(name,r)).colspan(3).expandX().fillX().height(32).row();
    }
    private Label label(String text){return new Label(text,BrainOutClient.Skin,"title-small");}
    public Table createUI() {
        box=new Table(BrainOutClient.Skin); box.setBackground("form-default"); box.defaults().pad(4);
        box.add(new Label(browser ? "Серверы локальной сети" : "Запуск матча", BrainOutClient.Skin,"title-yellow")).pad(12).row();
        list = new Table(BrainOutClient.Skin);
        if (browser) {
            status = label("Поиск доступных хабов…");
            box.add(status).left().padLeft(12).row();
            list.setBackground("form-gray");
            box.add(list).width(500).height(195).pad(8).row();
            Table actions = new Table();
            actions.defaults().height(36).pad(3);
            actions.add(button("Обновить", () -> {timeout = 0; status.setText("Поиск доступных хабов…");})).width(120);
            actions.add(button("Прямое подключение", this::direct)).width(210);
            actions.add(button("Назад", this::pop)).width(110);
            box.add(actions).row();
        } else {
            box.add(list).minWidth(360).row();
            list.add(label("Загрузка карт…"));
            HomeHub.query("maps",null,r->{if(!closed)popMeAndPushMenu(new HubMatchMenu(r.getJSONObject("maps")));});
            box.add(button("Назад",this::pop)).width(180).height(36).row();
        }
        return box;
    }
    private void direct() {
        pushMenu(new Menu() {
            public Table createUI() {
                Table form = new Table(BrainOutClient.Skin);
                form.setBackground("form-default");
                form.defaults().pad(6);
                form.add(label("Прямое подключение")).colspan(2).row();
                TextField address = new TextField("", BrainOutClient.Skin, "edit-default");
                address.setMessageText("IP или IP:порт");
                form.add(address).colspan(2).width(360).height(36).row();
                Label message = label("Порт хаба по умолчанию — 9511");
                form.add(message).colspan(2).row();
                form.add(button("Подключиться", () -> {
                    if (checkingAddress) return;
                    String[] parts = address.getText().trim().split(":", -1);
                    String endpoint;
                    try {
                        if (parts.length > 2) throw new IllegalArgumentException();
                        String[] octets = parts[0].split("\\.", -1);
                        if (octets.length != 4) throw new IllegalArgumentException();
                        for (String octet : octets)
                            if (!octet.matches("0|[1-9][0-9]{0,2}") || Integer.parseInt(octet)>255)
                                throw new IllegalArgumentException();
                        int port = parts.length == 2 ? Integer.parseInt(parts[1]) : 9511;
                        if (port < 1 || port > 65535) throw new IllegalArgumentException();
                        endpoint = parts[0] + ":" + port;
                    } catch (IllegalArgumentException e) {
                        message.setText("Проверьте IP и порт"); return;
                    }
                    checkingAddress = true;
                    message.setText("Проверка хаба…");
                    Thread probe = new Thread(() -> {
                        boolean available = false;
                        HttpURLConnection connection = null;
                        try {
                            connection = (HttpURLConnection)new URL("http://"+endpoint+"/hub/info").openConnection(Proxy.NO_PROXY);
                            connection.setInstanceFollowRedirects(false);
                            connection.setConnectTimeout(1800); connection.setReadTimeout(1800);
                            try (java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(connection.getInputStream(),StandardCharsets.UTF_8))) {
                                JSONObject info = new JSONObject(reader.readLine());
                                available = "brainout-hub-10".equals(info.optString("protocol")) &&
                                    !info.optString("id").equals(System.getenv("BRAINOUT_HUB_ID"));
                            }
                        } catch (Exception ignored) {
                        } finally { if(connection != null)connection.disconnect(); }
                        final boolean ready = available;
                        Gdx.app.postRunnable(() -> {
                            checkingAddress = false;
                            if (BrainOutClient.getInstance().topState().topMenu() != this) return;
                            if (ready) HomeHub.changeHost(endpoint);
                            else message.setText("Доступный хаб по этому адресу не найден");
                        });
                    }, "Direct hub connection");
                    probe.setDaemon(true); probe.start();
                })).width(175).height(36);
                form.add(button("Назад",this::pop)).width(175).height(36);
                return form;
            }
            public Object navigationKey(){return "direct-connect";}
            public boolean lockInput(){return true;}
            public boolean escape(){pop();return true;}
        });
    }
    public void act(float dt){
        super.act(dt); if(!browser || closed || scanning)return;
        timeout-=dt;if(timeout>0)return;
        scanning=true;timeout=3;
        Thread thread=new Thread(()->{
            Map<String,String> found=new TreeMap<>();
            Set<String> instances=new HashSet<>();
            try(DatagramSocket socket=new DatagramSocket()){
                socket.setBroadcast(true);socket.setSoTimeout(180);
                byte[] query="BrainOut hub discovery/10".getBytes(StandardCharsets.US_ASCII);
                Set<InetAddress> addresses=new HashSet<>();addresses.add(InetAddress.getByName("255.255.255.255"));
                for(NetworkInterface ni:Collections.list(NetworkInterface.getNetworkInterfaces())){
                    if(!ni.isUp()||ni.isLoopback())continue;
                    for(InterfaceAddress ia:ni.getInterfaceAddresses())if(ia.getBroadcast()!=null)addresses.add(ia.getBroadcast());
                }
                for(InetAddress a:addresses)try{socket.send(new DatagramPacket(query,query.length,a,39518));}catch(java.io.IOException ignored){}
                long until=System.currentTimeMillis()+850;
                while(System.currentTimeMillis()<until){
                    DatagramPacket packet=new DatagramPacket(new byte[1024],1024);
                    try{socket.receive(packet);}catch(SocketTimeoutException e){continue;}
                    try {
                        JSONObject host=new JSONObject(new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8));
                        if(!"brainout-hub-10".equals(host.optString("protocol")) || host.optString("id").equals(System.getenv("BRAINOUT_HUB_ID")))continue;
                        int port=host.getInt("port");if(port<1||port>65535)continue;
                        if(!instances.add(host.getString("id")))continue;
                        String endpoint=packet.getAddress().getHostAddress()+":"+port;
                        found.put(endpoint,host.optString("name")+(host.optBoolean("match") ? " · В матче" : " · Хаб")+"   ·   "+host.optInt("players")+" игр.   ·   "+endpoint);
                    }catch(RuntimeException ignored){}
                }
            }catch(java.io.IOException ignored){}
            Gdx.app.postRunnable(()->{
                scanning=false;if(closed)return;
                status.setText("Доступные хабы: " + found.size());
                list.clear();if(found.isEmpty())list.add(label("Пока нет других открытых хабов")).pad(12);
                else{Table rows=new Table();for(Map.Entry<String,String> row:found.entrySet())
                    rows.add(button(row.getValue(),()->HomeHub.changeHost(row.getKey()))).width(470).height(38).row();
                    list.add(new ScrollPane(rows,BrainOutClient.Skin,"scroll-default")).width(490).height(185);}
            });
        },"LAN hub discovery");thread.setDaemon(true);thread.start();
    }
    public Object navigationKey(){return browser ? "lan-browser" : "match-form";}
    public boolean lockInput(){return true;}
    public boolean escape(){pop();return true;}
    public void onRelease(){closed=true;super.onRelease();}
}
