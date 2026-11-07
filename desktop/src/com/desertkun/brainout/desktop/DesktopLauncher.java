package com.desertkun.brainout.desktop;

import com.badlogic.gdx.Graphics;
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3Application;
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3ApplicationConfiguration;
import com.badlogic.gdx.graphics.glutils.HdpiMode;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.ClientEnvironment;
import com.desertkun.brainout.client.settings.ClientSettings;
import com.desertkun.brainout.client.settings.ScreenResolutionProperty;
import com.esotericsoftware.minlog.Log;

import java.io.*;


public class DesktopLauncher
{
    public static void main(String[] args)
    {
        try
        {
            System.setErr(new PrintStream(new FileOutputStream("error.log")));
        }
        catch (FileNotFoundException e)
        {
            //
        }

        System.setProperty("java.awt.headless", "true");

        ClientEnvironment environment = new DesktopEnvironment(args);
        ClientSettings settings;

        try
        {
            settings = DesktopSettings.GetDesktopSettings(environment);
        }
        catch (Exception e)
        {
            e.printStackTrace();

            if (Log.ERROR) Log.error("Error loading settings: " + e.getMessage());
            return;
        }

        Lwjgl3ApplicationConfiguration cfg = new Lwjgl3ApplicationConfiguration();

        String name = System.getenv("DESKTOP_PROFILE_NAME");

        if (name != null)
        {
            cfg.setTitle(environment.getAppName() + " - " + name);
        }
        else
        {
            cfg.setTitle(environment.getAppName());
        }

        // revive: "fullscreen" = borderless window over the whole monitor. Exclusive fullscreen
        // switched the monitor video mode and got auto-minimized by Windows on Alt+Tab.
        // Old behaviour: env BRAINOUT_EXCLUSIVE_FULLSCREEN=1
        boolean exclusiveFullscreen = System.getenv("BRAINOUT_EXCLUSIVE_FULLSCREEN") != null;

        if (settings.getFullscreen().getValue() && !exclusiveFullscreen)
        {
            Graphics.DisplayMode desktopMode = Lwjgl3ApplicationConfiguration.getDisplayMode();

            // A borderless OpenGL window exactly the size of the monitor is promoted by Windows / the GPU
            // driver to direct "fullscreen" presentation that bypasses the desktop compositor: OBS display
            // capture and screenshots get a black frame. One extra pixel of height (off screen, invisible)
            // keeps it a normal composited window. -1 would show the taskbar on top.
            // env BRAINOUT_WINDOW_HEIGHT_DELTA overrides it (0 = exactly the monitor size).
            int heightDelta = 1;
            try
            {
                String d = System.getenv("BRAINOUT_WINDOW_HEIGHT_DELTA");
                if (d != null) heightDelta = Integer.parseInt(d.trim());
            }
            catch (NumberFormatException ignored) {}

            cfg.setDecorated(false);
            cfg.setWindowedMode(desktopMode.width, desktopMode.height + heightDelta);
            cfg.setWindowPosition(0, 0);
        }
        else if (settings.getFullscreen().getValue())
        {
            ScreenResolutionProperty dm = settings.getDisplayMode();
            Graphics.DisplayMode selected = null;
            for (Graphics.DisplayMode displayMode : Lwjgl3ApplicationConfiguration.getDisplayModes())
            {
                if (dm.getWidth() == displayMode.width && dm.getHeight() == displayMode.height && dm.getHz() == displayMode.refreshRate
                    && dm.getBpp() == displayMode.bitsPerPixel)
                {
                    selected = displayMode;
                    break;
                }
            }

            if (selected == null)
            {
                for (Graphics.DisplayMode displayMode : Lwjgl3ApplicationConfiguration.getDisplayModes())
                {
                    if (displayMode.width < 1024)
                        continue;
                    if (displayMode.width >= 2200)
                        continue;
                    if (displayMode.refreshRate > 60)
                        continue;
                    if (selected != null && (selected.width > displayMode.width))
                        continue;
                    selected = displayMode;
                }
            }

            if (selected != null)
            {
                environment.setTargetFullScreenDisplayMode(selected);
            }

            cfg.setWindowedMode(1024, 768);
        }
        else
        {
            cfg.setWindowedMode(settings.getDisplayMode().getWidth(), settings.getDisplayMode().getHeight());
        }

        if (System.getenv("FORCE_X") != null && System.getenv("FORCE_Y") != null)
        {
            cfg.setWindowPosition(Integer.valueOf(System.getenv("FORCE_X")),
                    Integer.valueOf(System.getenv("FORCE_Y")));
        }

        /*
        cfg.addIcon("icons/icon-128.png", Files.FileType.Internal);
        cfg.addIcon("icons/icon-64.png", Files.FileType.Internal);
        cfg.addIcon("icons/icon-32.png", Files.FileType.Internal);
        cfg.addIcon("icons/icon-16.png", Files.FileType.Internal);
         */

        // revive: never minimize the window just because it lost focus
        cfg.setAutoIconify(false);

        cfg.useVsync(settings.getvSync().getValue());
        cfg.setAudioConfig(64, 512, 9);

        new Lwjgl3Application(BrainOutDesktop.initDesktopInstance(environment, settings), cfg);
    }
}
