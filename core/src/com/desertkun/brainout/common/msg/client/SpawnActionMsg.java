package com.desertkun.brainout.common.msg.client;

public class SpawnActionMsg {
    public int playerId, dimension;
    public SpawnActionMsg() {}
    public SpawnActionMsg(com.desertkun.brainout.data.active.PlayerData player) {
        playerId = player.getId();
        dimension = player.getDimensionId();
    }
}
