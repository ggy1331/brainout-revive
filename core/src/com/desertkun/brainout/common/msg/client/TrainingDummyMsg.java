package com.desertkun.brainout.common.msg.client;

/** Hub: place a training dummy with my current loadout, or remove the nearest one. */
public class TrainingDummyMsg
{
    public static final int PLACE = 0;
    public static final int REMOVE = 1;

    public int action;

    public TrainingDummyMsg() {}

    public TrainingDummyMsg(int action)
    {
        this.action = action;
    }
}
