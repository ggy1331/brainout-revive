using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Windows.Forms;

class Launcher {
    [STAThread] static void Main() {
        string root=AppDomain.CurrentDomain.BaseDirectory;
        using(var gate=new Mutex(false,@"Local\BrainOutHub_"+root.ToUpperInvariant().GetHashCode())) {
            try {
                try { if(!gate.WaitOne(0)) return; } catch(AbandonedMutexException) {}
                var info=new ProcessStartInfo(Path.Combine(root,@"python\python.exe"),@"support\home.py");
                info.WorkingDirectory=root; info.UseShellExecute=false; info.CreateNoWindow=true;
                using(var service=Process.Start(info)) {
                    service.WaitForExit();
                    if(service.ExitCode!=0) MessageBox.Show("Не удалось открыть игру. Подробности в logs/hub.log и client-last.log.","BrainOut");
                }
            } catch(Exception e) { MessageBox.Show(e.Message,"BrainOut"); }
        }
    }
}
