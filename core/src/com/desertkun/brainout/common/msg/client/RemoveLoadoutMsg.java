package com.desertkun.brainout.common.msg.client;

public class RemoveLoadoutMsg
{
    public int number, expectedCount;

    public RemoveLoadoutMsg() {}

    public RemoveLoadoutMsg(int number, int expectedCount)
    {
        this.number = number;
        this.expectedCount = expectedCount;
    }
}
