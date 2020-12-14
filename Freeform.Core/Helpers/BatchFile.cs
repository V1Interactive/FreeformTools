/*
 * Freeform Rigging and Animation Tools
 * Copyright (C) 2020  Micah Zahm
 *
 * Freeform Rigging and Animation Tools is free software: you can redistribute it 
 * and/or modify it under the terms of the GNU General Public License as published 
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Freeform Rigging and Animation Tools is distributed in the hope that it will 
 * be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Freeform Rigging and Animation Tools.  
 * If not, see <https://www.gnu.org/licenses/>.
 */

namespace Freeform.Core.Helpers
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.IO;
    using System.Threading.Tasks;

    public static class BatchFile
    {
        public static int RunBatch(string command, string[] args)
        {
            var batchArgs = string.Join(" ", args);
            var processInfo = new ProcessStartInfo("cmd.exe", $"/c {command} {batchArgs}");
            processInfo.CreateNoWindow = true;
            processInfo.UseShellExecute = false;
            processInfo.RedirectStandardError = true;
            processInfo.RedirectStandardOutput = true;
            
            var process = Process.Start(processInfo);

            process.OutputDataReceived += (object sender, DataReceivedEventArgs e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                {
                    Console.WriteLine(e.Data);
                }
            };

            process.BeginOutputReadLine();

            process.ErrorDataReceived += (object sender, DataReceivedEventArgs e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                {
                    Console.WriteLine("err >>" + e.Data);
                }
            };

            process.BeginErrorReadLine();

            Console.CancelKeyPress += (s, e) =>
            {
                process.Kill();
            };

            process.WaitForExit();

            Console.WriteLine("ExitCode: {0}", process.ExitCode);
            var result = process.ExitCode;
            process.Close();

            return result;
        }
        
        public static int RunExe(string fullpath, string[] args)
        {
            return RunExe(fullpath, args, null);
        }

        public static int RunExe(string fullpath, string[] args, IDictionary<string, string> environment)
        {
            var batchArgs = string.Join(" ", args);
            var processInfo = new ProcessStartInfo(fullpath, batchArgs);
            processInfo.CreateNoWindow = true;
            processInfo.UseShellExecute = false;
            processInfo.RedirectStandardError = true;
            processInfo.RedirectStandardOutput = true;

            if (environment != null)
            {
                foreach(string key in environment.Keys)
                {
                    processInfo.EnvironmentVariables[key] = environment[key];
                }
            }
            
            var process = Process.Start(processInfo);

            process.OutputDataReceived += (object sender, DataReceivedEventArgs e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                {
                    Console.WriteLine(e.Data);
                }
            };
            process.BeginOutputReadLine();

            process.ErrorDataReceived += (object sender, DataReceivedEventArgs e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                {
                    Console.WriteLine("err >>" + e.Data);
                }
            };
            process.BeginErrorReadLine();

            process.WaitForExit();

            Console.WriteLine("ExitCode: {0}", process.ExitCode);
            var result = process.ExitCode;
            process.Close();

            return result;
        }


        public static Task RunExeAsync(string fullpath, string[] args)
        {
            return RunExeAsync(fullpath, args, null);
        }

        public static Task RunExeAsync(string fullpath, string[] args, IDictionary<string, string> environment)
        {
            var tcs = new TaskCompletionSource<bool>();

            var batchArgs = string.Join(" ", args);
            var processInfo = new ProcessStartInfo(fullpath, batchArgs);
            processInfo.CreateNoWindow = false;
            processInfo.UseShellExecute = false;
            processInfo.RedirectStandardError = true;
            processInfo.RedirectStandardOutput = true;

            if (environment != null)
            {
                foreach (string key in environment.Keys)
                {
                    processInfo.EnvironmentVariables[key] = environment[key];
                }
            }
            
            var process = new Process
            {
                StartInfo = processInfo,
                EnableRaisingEvents = true
            };

            process.Exited += (sender, processArgs) =>
            {
                tcs.SetResult(true);
                process.Dispose();
            };
            process.Start();

            return tcs.Task;
        }
    }



    public class DCCBatchJob
    {
        /*
          Defines a batch command for a DCC program and list of files to run the command on.
        */
        PyManager manager;
        string batchFolder;
        string script;
        string[] files;

        public DCCBatchJob(PyManager pyManager, string[] fileList, string runScript)
        {
            manager = pyManager;
            files = fileList;
            script = runScript;

            batchFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "batch");
        }

        public DCCBatchJob(PyManager pyManager, string file_path, string runScript)
        {
            manager = pyManager;
            files = File.ReadAllLines(file_path);
            script = runScript;

            batchFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "batch");
        }

        public int RunJobStatic()
        {
            WriteFileList();
            return manager.RunScriptStatic(script);
        }

        public async Task RunJob()
        {
            WriteFileList();
            await manager.RunScript(script);
        }

        void WriteFileList()
        {
            FileInfo file = new FileInfo(Path.Combine(batchFolder, "file_list.txt"));
            file.Directory.Create();
            File.WriteAllLines(file.FullName, files);
        }
    }


    public class PyManager
    {
        /* 
         Manager class for batch running python environments 
        */
        protected string interpreter;
        protected IDictionary<string, string> environment;
        protected string[] flags;

        #region Properties
        public string flagString
        {
            get
            {
                string flagString = "";
                if (flags != null)
                {
                    foreach (string flag in flags)
                    {
                        flagString = flagString + " -" + flag;
                    }
                }

                return flagString;
            }
        }
        #endregion

        #region Constructors
        public PyManager(string interpreterPath, IDictionary<string, string> environ = null, string[] flagList = null)
        {
            interpreter = interpreterPath;
            environment = environ;
            flags = flagList;
        }
        #endregion

        #region Methods
        string GetArgString(string[] args)
        {
            string argString = "";
            if (args != null)
            {
                foreach (string arg in args)
                {
                    argString = argString + " " + arg;
                }
            }

            return argString;
        }

        public int RunScriptStatic(string scriptPath, string[] scriptArgs = null)
        {
            /* 
            script      : Full path to the script to run with the interpreter 
            scriptArgs  : All string args will be passed to the python script
            */

            string[] args = new string[3] { flagString, scriptPath, GetArgString(scriptArgs) };

            return BatchFile.RunExe(interpreter, args);
        }

        public async Task RunScript(string scriptPath, string[] scriptArgs = null)
        {
            /* 
            script      : Full path to the script to run with the interpreter 
            scriptArgs  : All string args will be passed to the python script
            */

            string[] args = new string[3] { flagString, scriptPath, GetArgString(scriptArgs) };

            await BatchFile.RunExeAsync(interpreter, args);
        }
        #endregion
    }

    public class MayaPyManager : PyManager
    {
        /*
        Runs Maya Python environments with control over key variables

        mayapy.exe flags:

        See https://docs.python.org/2/tutorial/interpreter.html for more details on interpeter flags
        Here are the supported flags
        - B     : don't write .py[co] files on import; also PYTHONDONTWRITEBYTECODE=x
        - d     : debug output from parser; also PYTHONDEBUG = x
        - E     : ignore PYTHON* environment variables(such as PYTHONPATH)
        - O     : optimize generated bytecode slightly; also PYTHONOPTIMIZE = x
        - OO    : remove doc-strings in addition to the -O optimizations
        - Q arg : division options: -Qold(default), -Qwarn, -Qwarnall, -Qnew
        - s     : don't add user site directory to sys.path; also PYTHONNOUSERSITE
        - S     : don't imply 'import site' on initialization
        - t     : issue warnings about inconsistent tab usage(-tt: issue errors)
        - v     : verbose(trace import statements); also PYTHONVERBOSE = x
                    can be supplied multiple times to increase verbosity
        - W arg : warning control; arg is action:message:category:module:lineno
        */
        static readonly string defaultInterpreter = @"C:\Program Files\Autodesk\Maya2018\bin\mayapy.exe";


        public MayaPyManager(IDictionary<string, string> environ = null, string[] flagList = null) : base(defaultInterpreter, environ, flagList)
        {
            if(environ == null) { environ = new Dictionary<string, string>(); }
            
            environ["MAYA_LOCATION"] = Path.GetDirectoryName(interpreter);
            environ["PYTHONHOME"] = Path.GetDirectoryName(interpreter);
        }
    }

    public class MaxPyManager : PyManager
    {
        /*
        Runs Max permanently minimized with control over key variables
        */
        static readonly string defaultInterpreter = @"C:\Program Files\Autodesk\3ds Max 2018\3dsmax.exe";


        public MaxPyManager(IDictionary<string, string> environ = null) : base(defaultInterpreter, environ, new string[4] { "q", "silent", "mip", "U PythonHost" })
        {
        }
    }
}