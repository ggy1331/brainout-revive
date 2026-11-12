package com.desertkun.brainout.menu.impl;

import javax.sound.sampled.*;
import java.io.*;
import java.net.*;
import java.util.concurrent.*;
import java.util.function.DoubleSupplier;

/** Bounded PCM playback: HTTP -> 8 KiB block -> 200 ms audio buffer. No files. */
public final class RadioStream {
    private static final int RATE=48000, FRAME=4;
    private static final ExecutorService closer=Executors.newCachedThreadPool(r -> {
        Thread t=new Thread(r,"radio-stream-close");t.setDaemon(true);return t;
    });
    private volatile boolean cancelled, started, done;
    private volatile String error;
    private volatile float volume=0.7f;
    private volatile double origin;
    private volatile long startedAt;
    private volatile SourceDataLine line;
    private volatile HttpURLConnection connection;

    public RadioStream(String video, String credential, double position, DoubleSupplier target) {
        origin=position;
        Thread t=new Thread(() -> run(video,credential,position,target),"hub-radio-pcm");
        t.setDaemon(true);t.start();
    }
    public float getPosition() {
        SourceDataLine output=line;
        return (float)(origin+(output==null ? 0 : output.getLongFramePosition()/(double)RATE));
    }
    public boolean isPlaying() { return started && !cancelled && !done; }
    public boolean isDone() { return done; }
    public String getError() { return error; }
    public double age() { return started ? (System.nanoTime()-startedAt)/1e9 : 0; }
    public void setVolume(float value) { volume=Math.max(0,Math.min(1,value)); }
    public void dispose() {
        cancelled=true;
        // Do not wait for HTTP reads or a decoder on the game/render thread.
        closer.execute(() -> {
            SourceDataLine output=line;
            if(output!=null) { output.stop();output.flush();output.close(); }
            HttpURLConnection c=connection;
            if(c!=null)c.disconnect();
        });
    }
    private void run(String video,String credential,double position,DoubleSupplier target) {
        SourceDataLine output=null;
        HttpURLConnection c=null;
        try {
            c=(HttpURLConnection)new URL("http://"+HomeHub.ENDPOINT+"/hub/radio-media?video="+video+
                    "&position="+position).openConnection(Proxy.NO_PROXY);
            connection=c;
            c.setConnectTimeout(3000);c.setReadTimeout(115000);
            c.setRequestProperty("X-Token",credential);
            c.setRequestProperty("X-Hub-Key",System.getenv("BRAINOUT_OWNER_KEY"));
            c.setUseCaches(false);
            if(cancelled)return;
            try(InputStream in=c.getInputStream()) {
                if(!"audio/pcm".equals(c.getContentType()))throw new IOException("Unexpected audio format");
                c.setReadTimeout(20000);
                AudioFormat format=new AudioFormat(RATE,16,2,true,false);
                output=AudioSystem.getSourceDataLine(format);
                output.open(format,RATE*FRAME/5);
                line=output;
                if(cancelled)return;
                byte[] block=new byte[8192];
                double cursor=position;
                int carried=0;
                while(!cancelled) {
                    int n=in.read(block,carried,block.length-carried);
                    if(n<0)break;
                    n+=carried;
                    int size=n-n%FRAME;
                    carried=n-size;
                    int offset=0;
                    if(!started && target!=null) {
                        // Startup/seek can take seconds. Discard stale PCM in RAM to catch up.
                        long stale=(long)Math.max(0,(target.getAsDouble()-cursor)*RATE);
                        offset=(int)Math.min(size/FRAME,stale)*FRAME;
                    }
                    if(size>offset) {
                        if(!started) {
                            origin=cursor+offset/(double)(RATE*FRAME);
                            startedAt=System.nanoTime();started=true;output.start();
                        }
                        float gain=volume;
                        for(int i=offset;i<size;i+=2) {
                            short sample=(short)((block[i]&255)|(block[i+1]<<8));
                            int scaled=(int)(sample*gain);
                            block[i]=(byte)scaled;block[i+1]=(byte)(scaled>>8);
                        }
                        while(offset<size && !cancelled) {
                            int writable=Math.min(size-offset,output.available());
                            writable-=writable%FRAME;
                            if(writable>0)offset+=output.write(block,offset,writable);
                            else Thread.sleep(5);
                        }
                    }
                    cursor+=size/(double)(RATE*FRAME);
                    if(carried>0)System.arraycopy(block,size,block,0,carried);
                }
                if(!cancelled) {
                    // Bounded drain, cancellable even if an audio driver stops responding.
                    long deadline=System.nanoTime()+1000000000L;
                    while(!cancelled && output.available()<output.getBufferSize() && System.nanoTime()<deadline)
                        Thread.sleep(5);
                }
            }
        } catch(Exception ex) {
            if(!cancelled)error="Аудиопоток недоступен";
        } finally {
            done=true;
            if(output!=null) { output.stop();output.flush();output.close(); }
            if(c!=null)c.disconnect();
        }
    }
}
