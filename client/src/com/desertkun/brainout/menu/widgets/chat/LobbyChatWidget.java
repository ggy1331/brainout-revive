package com.desertkun.brainout.menu.widgets.chat;

import com.badlogic.gdx.utils.ObjectMap;
import com.desertkun.brainout.BrainOut;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.ClientConstants;
import com.desertkun.brainout.L;
import com.desertkun.brainout.client.SocialController;
import com.desertkun.brainout.client.SocialMessages;
import com.desertkun.brainout.content.consumable.impl.InstrumentConsumableItem;
import com.desertkun.brainout.data.consumable.ConsumableRecord;
import com.desertkun.brainout.events.Event;
import com.desertkun.brainout.events.SimpleEvent;
import com.desertkun.brainout.events.SocialMessageDeletedEvent;
import com.desertkun.brainout.events.SocialMessageEvent;
import com.desertkun.brainout.gs.GameState;
import com.desertkun.brainout.menu.impl.ClanMenu;
import com.desertkun.brainout.menu.impl.ConflictApprovePreviewMenu;
import com.desertkun.brainout.menu.impl.JoinClanMenu;
import com.desertkun.brainout.menu.impl.RemoteAccountMenu;
import com.desertkun.brainout.menu.popups.AlertPopup;
import com.desertkun.brainout.menu.widgets.chat.msg.ActionMessage;
import com.desertkun.brainout.menu.widgets.chat.msg.SimpleChatMessage;
import com.desertkun.brainout.menu.widgets.chat.msg.StatusMessage;
import com.desertkun.brainout.online.Clan;
import com.desertkun.brainout.online.RoomSettings;
import com.desertkun.brainout.utils.MarketUtils;
import org.anthillplatform.runtime.services.LoginService;
import org.json.JSONObject;

import java.util.TimerTask;

public class LobbyChatWidget extends ChatWidget
{
    private ObjectMap<String, ObjectMap<String, SocialMessages.ClientMessage>> lastSocialMessages;
    private ObjectMap<String, TimerTask> readTasks;

    public LobbyChatWidget(float x, float y, float w, float h)
    {
        super(x, y, w, h);

        lastSocialMessages = new ObjectMap<>();
        readTasks = new ObjectMap<>();
    }

    @Override
    protected boolean validateView(Object key)
    {
        return !("server".equals(key));
    }

    @Override
    public void init()
    {
        super.init();

        addTab(L.get("MENU_CHAT_SERVER"), "server").defSize();


        BrainOut.EventMgr.subscribeAt(Event.ID.socialMessage, this, true);
        BrainOut.EventMgr.subscribeAt(Event.ID.socialMessageUpdated, this, true);
        BrainOut.EventMgr.subscribeAt(Event.ID.socialMessageDeleted, this, true);
        BrainOut.EventMgr.subscribeAt(Event.ID.simple, this, true);
    }

    @Override
    public void release()
    {
        super.release();

        BrainOut.EventMgr.unsubscribe(Event.ID.socialMessage, this);
        BrainOut.EventMgr.unsubscribe(Event.ID.socialMessageDeleted, this);
        BrainOut.EventMgr.unsubscribe(Event.ID.socialMessageUpdated, this);
        BrainOut.EventMgr.unsubscribe(Event.ID.simple, this);
    }

    @Override
    public boolean onEvent(Event event)
    {
        switch (event.getID())
        {
            case simple:
            {
                SimpleEvent e = ((SimpleEvent) event);

                if (e.getAction() == SimpleEvent.Action.socialMessagesReceived)
                {
                    socialMessagesReceived();
                }

                break;
            }
            case socialMessage:
            {
                SocialMessageEvent e = ((SocialMessageEvent) event);

                if (process(e.message, e.notify))
                {
                    return true;
                }

                break;
            }
            case socialMessageDeleted:
            {
                SocialMessageDeletedEvent e = ((SocialMessageDeletedEvent) event);

                deleteMessage(e.messageId);

                break;
            }
        }

        return super.onEvent(event);
    }

    private void socialMessagesReceived()
    {
        for (ObjectMap.Entry<String, SocialMessages.ClientMessage> entry :
                BrainOutClient.SocialController.getMessages().getMessages())
        {
            SocialMessages.ClientMessage message = entry.value;

            if (message != null)
            {
                process(message, false);
            }
        }
    }

    private boolean process(SocialMessages.ClientMessage e, boolean notify)
    {
        return false;
    }

    @Override
    protected void tabChanged(ChatTab chatTab)
    {
        super.tabChanged(chatTab);

        notifyMessageRead(chatTab.getName());
    }

    private void addMessageRead(String group, SocialMessages.ClientMessage e)
    {
        ObjectMap<String, SocialMessages.ClientMessage> m = lastSocialMessages.get(group);

        if (m == null)
        {
            m = new ObjectMap<>();
            lastSocialMessages.put(group, m);
        }

        String key = e.recipientClass + "." + e.recipientKey;

        m.put(key, e);

        if (isOpened() && group.equals(getCurrentTab()))
        {
            notifyMessageRead(group);
        }
        else
        {
            BrainOutClient.EventMgr.sendDelayedEvent(SimpleEvent.obtain(SimpleEvent.Action.updateSocialMessages));
        }
    }



    private boolean itWasMe(SocialMessages.ClientMessage e)
    {
        String myAccount = BrainOutClient.ClientController.getMyAccount();

        return e.sender.equals(myAccount);
    }

    private boolean eGroupRequest(SocialMessages.ClientMessage e, boolean notify)
    {
        Clan myClan = BrainOutClient.SocialController.getMyClan();
        LoginService loginService = LoginService.Get();

        if (myClan != null && loginService != null)
        {
            Clan.ClanMember me = myClan.getMembers().get(BrainOutClient.ClientController.getMyAccount());

            if (me != null && (me == myClan.getOwner() || me.hasPermission("request_approval")))
            {
                String author = e.payload.optString("name", "unknown");
                String credential = e.payload.optString("credential", null);

                String key = e.payload.optString("key", null);

                if (key == null)
                    return true;

                ActionMessage msg = new ActionMessage(
                        L.get("MENU_CLAN_EVENT_JOIN_REQUEST", author),
                        e.messageId);

                msg.addAction(L.get("MENU_CONNECT_ACCOUNT"),
                    (button) ->
                {
                    GameState top = BrainOutClient.getInstance().topState();

                    if (!(top.topMenu() instanceof RemoteAccountMenu))
                    {
                        top.pushMenu(new RemoteAccountMenu(e.sender, credential));
                    }
                });

                msg.addIconAction("button-approve",
                    (button) ->
                {
                    JSONObject args = new JSONObject();

                    args.put("message_id", e.messageId);
                    args.put("account_id", e.sender);
                    args.put("key", key);
                    args.put("player_name", author);
                    args.put("method", "approve");

                    button.setDisabled(true);

                    BrainOutClient.SocialController.sendRequest("respond_clan_request", args,
                        new SocialController.RequestCallback()
                    {
                        @Override
                        public void success(JSONObject response)
                        {
                            button.setDisabled(false);
                        }

                        @Override
                        public void error(String reason)
                        {
                            button.setDisabled(false);
                        }
                    });
                });

                msg.addIconAction("button-reject",
                    (button) ->
                {
                    JSONObject args = new JSONObject();

                    args.put("message_id", e.messageId);
                    args.put("account_id", e.sender);
                    args.put("key", key);
                    args.put("method", "reject");

                    button.setDisabled(true);

                    BrainOutClient.SocialController.sendRequest("respond_clan_request", args,
                        new SocialController.RequestCallback()
                    {
                        @Override
                        public void success(JSONObject response)
                        {
                            button.setDisabled(false);
                        }

                        @Override
                        public void error(String reason)
                        {
                            button.setDisabled(false);
                        }
                    });
                });

                addChatMessage("clan", msg, notify);
            }
        }

        return true;
    }

    private boolean eGroupInvite(SocialMessages.ClientMessage e, boolean notify)
    {
        if (itWasMe(e))
            return true;

        String clanId = e.payload.optString("group_id");
        String clanName = e.payload.optString("group_name");
        String avatar = e.payload.optString("group_avatar");
        String author = e.payload.optString("name", "unknown");

        String key = e.payload.optString("key", null);

        if (clanId == null || key == null)
            return true;

        ActionMessage msg = new ActionMessage(
            L.get("MENU_CLAN_EVENT_INVITE", author, clanName),
            e.messageId);

        msg.addAction(L.get("MENU_CHAT_CLAN"),
            (button) ->
        {
            GameState top = BrainOutClient.getInstance().topState();

            if (!(top.topMenu() instanceof ClanMenu))
            {
                top.pushMenu(new ClanMenu(clanId));
            }
        });

        msg.addIconAction("button-approve",
            (button) ->
        {
            GameState top = BrainOutClient.getInstance().topState();

            closeChatFromReply();

            top.pushMenu(new JoinClanMenu(clanName, avatar,
                () ->
            {
                JSONObject args = new JSONObject();

                args.put("message_id", e.messageId);
                args.put("clan_id", clanId);
                args.put("key", key);
                args.put("method", "accept");

                button.setDisabled(true);

                BrainOutClient.SocialController.sendRequest("respond_clan_invite", args,
                    new SocialController.RequestCallback()
                {
                    @Override
                    public void success(JSONObject response)
                    {
                        button.setDisabled(false);
                    }

                    @Override
                    public void error(String reason)
                    {
                        button.setDisabled(false);

                        top.pushMenu(new AlertPopup(L.get(reason)));
                    }
                });
            }));
        });

        msg.addIconAction("button-reject",
            (button) ->
        {
            JSONObject args = new JSONObject();

            args.put("message_id", e.messageId);
            args.put("clan_id", clanId);
            args.put("key", key);
            args.put("method", "reject");

            button.setDisabled(true);

            BrainOutClient.SocialController.sendRequest("respond_clan_invite", args,
                new SocialController.RequestCallback()
            {
                @Override
                public void success(JSONObject response)
                {
                    button.setDisabled(false);
                }

                @Override
                public void error(String reason)
                {
                    button.setDisabled(false);

                    GameState top = BrainOutClient.getInstance().topState();
                    top.pushMenu(new AlertPopup(L.get(reason)));
                }
            });
        });

        addChatMessage("clan", msg, notify);
        addMessageRead("clan", e);

        return true;
    }

    private boolean eGroupEngageConflict(SocialMessages.ClientMessage e, boolean notify)
    {
        if (itWasMe(e))
            return true;

        String clanId = e.payload.optString("group_id");
        String clanName = e.payload.optString("group_name");
        String avatar = e.payload.optString("group_avatar");
        JSONObject roomSettings = e.payload.optJSONObject("room_settings");
        int conflictSize = e.payload.optInt("conflict_size", 8);

        if (clanId == null)
            return true;

        ActionMessage msg = new ActionMessage(
            L.get("MENU_CLAN_CHALLENGES_YOU", clanName),
            e.messageId);

        msg.addAction(L.get("MENU_CHAT_CLAN"),
            (button) ->
        {
            GameState top = BrainOutClient.getInstance().topState();

            if (!(top.topMenu() instanceof ClanMenu))
            {
                top.pushMenu(new ClanMenu(clanId));
            }
        });

        Clan myClan = BrainOutClient.SocialController.getMyClan();
        LoginService loginService = LoginService.Get();

        if (myClan != null && loginService != null)
        {
            Clan.ClanMember me = myClan.getMembers().get(BrainOutClient.ClientController.getMyAccount());

            if (me != null && (me == myClan.getOwner() || me.hasPermission(Clan.Permissions.ENGAGE_CONFLICT)))
            {
                msg.addIconAction("button-approve",
                    (button) ->
                {
                    GameState top = BrainOutClient.getInstance().topState();

                    RoomSettings roomSettings_ = new RoomSettings();
                    roomSettings_.init(BrainOutClient.ClientController.getUserProfile(), false);
                    roomSettings_.read(roomSettings);

                    closeChatFromReply();

                    top.pushMenu(new ConflictApprovePreviewMenu(roomSettings_, conflictSize, () ->
                    {
                        JSONObject args = new JSONObject();

                        args.put("message_id", e.messageId);
                        args.put("group_id", clanId);
                        args.put("room_settings", roomSettings);
                        args.put("method", "accept");
                        args.put("conflict_size", conflictSize);

                        button.setDisabled(true);

                        BrainOutClient.SocialController.sendRequest("clan_engage_result", args,
                            new SocialController.RequestCallback()
                        {
                            @Override
                            public void success(JSONObject response)
                            {
                                button.setDisabled(false);
                            }

                            @Override
                            public void error(String reason)
                            {
                                button.setDisabled(false);

                                top.pushMenu(new AlertPopup(L.get(reason)));
                            }
                        });
                    }));
                });

                msg.addIconAction("button-reject",
                    (button) ->
                {
                    JSONObject args = new JSONObject();

                    args.put("message_id", e.messageId);
                    args.put("group_id", clanId);
                    args.put("method", "reject");

                    button.setDisabled(true);

                    BrainOutClient.SocialController.sendRequest("clan_engage_result", args,
                        new SocialController.RequestCallback()
                    {
                        @Override
                        public void success(JSONObject response)
                        {
                            button.setDisabled(false);
                        }

                        @Override
                        public void error(String reason)
                        {
                            button.setDisabled(false);

                            GameState top = BrainOutClient.getInstance().topState();
                            top.pushMenu(new AlertPopup(L.get(reason)));
                        }
                    });
                });
            }
        }
        addChatMessage("clan", msg, notify);
        addMessageRead("clan", e);

        return true;
    }

    private void notifyMessageRead(String group)
    {
        if (group == null)
            return;

        ObjectMap<String, SocialMessages.ClientMessage> m = lastSocialMessages.get(group);

        if (m == null)
            return;

        for (ObjectMap.Entry<String, SocialMessages.ClientMessage> entry : m)
        {
            SocialMessages.ClientMessage socialMessage = entry.value;

            String taskKey = group + "." + entry.key;

            TimerTask readTask = readTasks.get(taskKey);

            if (readTask != null)
            {
                readTask.cancel();
            }

            readTask = new TimerTask()
            {
                private SocialMessages.ClientMessage notify = socialMessage;

                @Override
                public void run()
                {
                    notify.markAsRead();
                    readTasks.remove(taskKey);

                    BrainOutClient.EventMgr.sendDelayedEvent(SimpleEvent.obtain(SimpleEvent.Action.updateSocialMessages));
                }
            };

            BrainOutClient.Timer.schedule(readTask, 2000);

            readTasks.put(taskKey, readTask);
        }

    }

    @Override
    public void openChatForReply(String tab)
    {
        super.openChatForReply(tab);

        notifyMessageRead(getCurrentTab());
    }


}
