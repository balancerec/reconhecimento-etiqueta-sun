using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
class Installer {
    static int Main() {
        try {
            Console.Title = "PRO-ACT Etiquetas - Instalador";
            string folder = Path.Combine(Path.GetTempPath(), "PROACT-Etiquetas-Setup-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(folder);
            string zip = Path.Combine(folder, "payload.zip");
            using (Stream input=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
            using (FileStream output=File.Create(zip)) { if(input==null)throw new Exception("Pacote ausente");input.CopyTo(output); }
            string source=Path.Combine(folder,"source");ZipFile.ExtractToDirectory(zip,source);
            string script=Path.Combine(source,"windows","install.ps1");
            var start = new ProcessStartInfo("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -File \"" + script + "\" -SourcePath \"" + source + "\"");
            start.UseShellExecute=false;start.WorkingDirectory=source;
            using(var process=Process.Start(start)) {process.WaitForExit();return process.ExitCode;}
        } catch(Exception e) {Console.WriteLine(e.Message);Console.WriteLine("Enter para fechar");Console.ReadLine();return 1;}
    }
}
