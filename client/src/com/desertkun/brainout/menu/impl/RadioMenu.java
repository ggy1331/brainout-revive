package com.desertkun.brainout.menu.impl;

import com.badlogic.gdx.scenes.scene2d.ui.*;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.menu.Menu;
import org.json.JSONArray;
import org.json.JSONObject;

public final class RadioMenu extends Menu {
    private Table rows;
    private Label status, time;
    private Slider seek;
    private TextButton pause, shuffle;
    private int revision = -1;
    private boolean dragging;
    private Label label(String text) { return new Label(text, BrainOutClient.Skin, "title-small"); }
    private void send(String op) { HubRadio.command(new JSONObject().put("op",op)); }
    public Table createUI() {
        Table box=new Table(BrainOutClient.Skin);
        box.setBackground("form-default"); box.defaults().pad(5);
        box.add(new Label("Радио",BrainOutClient.Skin,"title-yellow")).colspan(2).row();
        TextField link=new TextField("",BrainOutClient.Skin,"edit-default");
        link.setMessageText("https://www.youtube.com/watch?v=…");
        box.add(link).width(460).height(34);
        box.add(HubPanel.button(HomeHub.OWNER ? "Добавить" : "Запросить",()->HubRadio.add(link.getText()))).width(125).height(34).row();
        status=label(""); status.setWrap(true);
        box.add(status).colspan(2).width(590).height(48).row();
        time=label(""); box.add(time).colspan(2).row();
        seek=new Slider(0,3600,1,false,BrainOutClient.Skin,"slider-default");
        seek.setDisabled(!HomeHub.OWNER);
        box.add(seek).colspan(2).width(580).row();
        if(HomeHub.OWNER) {
            Table controls=new Table(); controls.defaults().pad(3).height(32);
            pause=HubPanel.button("Пауза",()->send("pause")); controls.add(pause).width(140);
            controls.add(HubPanel.button("Следующий",()->send("next"))).width(140);
            shuffle=HubPanel.button("Случайно: выкл.",()->send("shuffle")); controls.add(shuffle).width(220);
            box.add(controls).colspan(2).row();
        }
        rows=new Table(); rows.defaults().pad(2);
        box.add(new ScrollPane(rows,BrainOutClient.Skin,"scroll-default")).colspan(2).width(600).height(260).row();
        box.add(label("Заявки гостей хранятся, пока гость находится в хабе.")).colspan(2).row();
        box.add(HubPanel.button("Закрыть",this::pop)).colspan(2).width(180).height(34).row();
        return box;
    }
    public void act(float dt) {
        super.act(dt);
        if(rows==null)return;
        JSONObject state=HubRadio.state;
        status.setText(HubRadio.status);
        JSONArray tracks=state.optJSONArray("queue");
        double duration=1;
        if(tracks!=null)for(int i=0;i<tracks.length();i++) {
            JSONObject t=tracks.getJSONObject(i);
            if(t.optString("id").equals(state.optString("current")))duration=t.optDouble("duration",1);
        }
        time.setText(format(HubRadio.position())+" / "+format((float)duration));
        boolean now=seek.isDragging();
        if(dragging && !now && HomeHub.OWNER)
            HubRadio.command(new JSONObject().put("op","seek").put("position",seek.getValue()));
        if(!now && !dragging) { seek.setRange(0,(float)Math.max(1,duration)); seek.setValue(HubRadio.position()); }
        dragging=now;
        if(pause!=null)pause.setText(state.optBoolean("paused") ? "Продолжить" : "Пауза");
        if(shuffle!=null)shuffle.setText("Случайно: "+(state.optBoolean("shuffle") ? "вкл." : "выкл."));
        int next=state.optInt("revision",-1);
        if(next==revision)return;
        revision=next; rows.clear();
        if(tracks==null || tracks.length()==0)rows.add(label("Плейлист пока пуст"));
        else for(int i=0;i<tracks.length();i++) {
            JSONObject track=tracks.getJSONObject(i);
            String id=track.getString("id"); final int index=i;
            String title=(id.equals(state.optString("current")) ? "> " : "")+(i+1)+". "+track.optString("title");
            if(!track.optString("requester").isEmpty())title="[Запрошенный] "+title;
            Label name=label(title); name.setEllipsis(true);
            rows.add(name).width(HomeHub.OWNER ? 365 : 560).left();
            if(HomeHub.OWNER) {
                rows.add(HubPanel.button(">",()->HubRadio.command(new JSONObject().put("op","play").put("id",id)))).width(40);
                rows.add(HubPanel.button("^",()->HubRadio.command(new JSONObject().put("op","move").put("id",id).put("index",index-1)))).width(40);
                rows.add(HubPanel.button("v",()->HubRadio.command(new JSONObject().put("op","move").put("id",id).put("index",index+1)))).width(40);
                rows.add(HubPanel.button("X",()->HubRadio.command(new JSONObject().put("op","remove").put("id",id)))).width(40);
            }
            rows.row();
        }
    }
    private static String format(float value) { int s=Math.max(0,(int)value); return (s/60)+":"+String.format("%02d",s%60); }
    public Object navigationKey(){return "hub-radio";}
    public boolean lockInput(){return true;}
    public boolean lockRender(){return true;}
    public boolean escape(){pop();return true;}
}
