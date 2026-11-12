package com.desertkun.brainout.menu.popups;

import com.badlogic.gdx.scenes.scene2d.InputEvent;
import com.badlogic.gdx.scenes.scene2d.ui.Label;
import com.badlogic.gdx.scenes.scene2d.ui.ProgressBar;
import com.badlogic.gdx.scenes.scene2d.ui.Table;
import com.badlogic.gdx.utils.Align;
import com.badlogic.gdx.utils.ArrayMap;
import com.desertkun.brainout.BrainOutClient;
import com.desertkun.brainout.menu.Popup;
import com.desertkun.brainout.menu.ui.ClickOverListener;

/**
 * Game update from the hub: what the updater (support/release_update.py prepare) is doing and how
 * much of the release archive is downloaded. "Hide" only closes the window, the download goes on.
 */
public class UpdateProgressPopup extends Popup
{
    private Label status, amount;
    private ProgressBar bar;
    private boolean closed;
    private String statusText = "Проверяю обновления…";
    private long done = -1, total = -1;

    public UpdateProgressPopup()
    {
        super("");

        ArrayMap<String, PopupButtonStyle> buttons = new ArrayMap<>();
        buttons.put("Скрыть", new PopupButtonStyle(new ClickOverListener()
        {
            @Override
            public void clicked(InputEvent event, float x, float y)
            {
                playSound(MenuSound.back);
                pop();
            }
        }));
        setButtons(buttons);
    }

    @Override
    public String getTitle()
    {
        return "Обновление игры";
    }

    @Override
    protected void initContent(Table data)
    {
        status = new Label(statusText, BrainOutClient.Skin, "title-medium");
        status.setAlignment(Align.center);
        status.setWrap(true);
        data.add(status).pad(8).expandX().fillX().row();

        bar = new ProgressBar(0, 1, 0.001f, false, BrainOutClient.Skin, "progress-event");
        bar.setAnimateDuration(0.2f);
        data.add(bar).pad(8).height(12).expandX().fillX().row();

        amount = new Label("", BrainOutClient.Skin, "title-small");
        amount.setAlignment(Align.center);
        data.add(amount).pad(4).expandX().fillX().row();

        refresh();
    }

    /** a new stage of the update: checking, downloading, unpacking */
    public void setStatus(String text)
    {
        statusText = text;
        refresh();
    }

    /** downloaded bytes of the archive; total <= 0 when GitHub did not tell the size */
    public void setProgress(long done, long total)
    {
        this.done = done;
        this.total = total;
        refresh();
    }

    private void refresh()
    {
        if (status == null) return;
        status.setText(statusText);
        if (done < 0)
        {
            bar.setValue(0);
            amount.setText("");
            return;
        }
        float mb = done / 1048576f;
        if (total > 0)
        {
            bar.setValue(Math.min(1f, done / (float) total));
            amount.setText(String.format("%d%%  ·  %.0f / %.0f МБ", Math.min(100, done * 100 / total),
                mb, total / 1048576f));
        }
        else
        {
            amount.setText(String.format("%.0f МБ", mb));
        }
    }

    public boolean isClosed()
    {
        return closed;
    }

    @Override
    public void onRelease()
    {
        super.onRelease();
        closed = true;
    }
}
