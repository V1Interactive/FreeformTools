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
    // https://www.perforce.com/perforce/doc.current/manuals/p4api.net/p4api.net_reference/Index.html
    using System;
    using global::Perforce.P4;
    using Freeform.Core.ConfigSettings;
    using Freeform.Core.Utilities;
    using Freeform.Core.Network;
    using System.Collections.Generic;
    using System.Linq;

    //:RunStatus
    //"%P4%" status %~dp0Config\...
    //"%P4%" status %~dp0Source\...
    //goto Done

    //:RunRecon
    //set RECON_OPTIONS=-n
    //if "%2"=="run" set RECON_OPTIONS =
    //"%P4%" reconcile -l %RECON_OPTIONS% %~dp0Config\...
    //"%P4%" reconcile -l %RECON_OPTIONS% %~dp0Source\...
    //goto Done

    //:Done
    //echo bye.

    public class P4Status
    {
        private P4Status(string value) { Value = value; }

        public string Value { get; set; }

        public static P4Status Null { get { return new P4Status("../../Resources/null.ico"); } }
        public static P4Status CheckedIn { get { return new P4Status("../../Resources/p4_checkedin.ico"); } }
        public static P4Status CheckedOut { get { return new P4Status("../../Resources/p4_checkout.ico"); } }
        public static P4Status CheckedOutOther { get { return new P4Status("../../Resources/p4_checkout_other.ico"); } }
        public static P4Status Add { get { return new P4Status("../../Resources/p4_add.ico"); } }
        public static P4Status Delete { get { return new P4Status("../../Resources/p4_delete.ico"); } }
        public static P4Status Unknown { get { return new P4Status("../../Resources/p4_unknown.ico"); } }
    }
    
    public class FileWriteStatus
    {
        private FileWriteStatus(string value) { Value = value; }

        public string Value { get; set; }

        public static FileWriteStatus Null { get { return new FileWriteStatus("../../Resources/null.ico"); } }
        public static FileWriteStatus Locked { get { return new FileWriteStatus("../../Resources/p4_locked.ico"); } }
        public static FileWriteStatus Unlocked { get { return new FileWriteStatus("../../Resources/p4_unlocked.ico"); } }
    }


    public class Perforce
    {
        private bool Enabled { get; set; }
        private string PerforceHost { get; set; }
        private string PerforceServer { get; set; }
        private string ClientName { get; set; }
        private string ClientHostName { get; set; }
        private string WorkspaceName { get; set; }

        //private const string PerforceHost = "snowlion";
        //private static readonly string PerforceServer = $"ssl:{PerforceHost}:1666";

        public static Perforce ConnectToPath(string path)
        {
            var result = new Perforce();

            if (result.Server == null)
            {
                return null;
            }

            if (result.Repository == null)
            {
                return null;
            }

            try
            {
                result.DiscoverClient(path);
            }
            catch (Exception)
            {
                return null;
            }

            return result;
        }

        public static List<string> FileOperation(List<string> filePathList, FileAction action)
        {
            IList<FileSpec> filesEdited = null;
            Perforce server = new Perforce();

            if (server.Enabled == false)
            {
                return new List<string>();
            }

            try
            {
                server.DiscoverClient(GetFilePath(filePathList[0]));
                // connect to the server
                server.Connect();

                foreach (string filePath in filePathList)
                {
                    string fixedFilePath = GetFilePath(filePath);
                    FileSpec fileToAdd = new FileSpec(new ClientPath(fixedFilePath));

                    if (System.IO.File.Exists(fixedFilePath) == true)
                    {
                        EditCmdOptions options = new EditCmdOptions(EditFilesCmdFlags.None, 0, null);
                        // run the command with the current connection
                        if (action == FileAction.Add) { filesEdited = server.Repository.Connection.Client.AddFiles(options, fileToAdd); }
                        else if (action == FileAction.Edit) { filesEdited = server.Repository.Connection.Client.EditFiles(options, fileToAdd); }
                        else if (action == FileAction.Delete) { filesEdited = server.Repository.Connection.Client.DeleteFiles(options, fileToAdd); }
                        else if (action == FileAction.Reverted) { filesEdited = server.Repository.Connection.Client.RevertFiles(options, fileToAdd); }
                    }
                }
            }
            finally
            {
                server.Disconnect();
            }

            List<FileSpec> fileSpecList = new List<FileSpec>();
            if (filesEdited != null)
            {
                fileSpecList = new List<FileSpec>(filesEdited);
            }
            return fileSpecList.Select(x => x.ClientPath.ToString()).ToList();
        }


        public static List<string> CheckoutFiles(List<string> filePathList)
        {
            return FileOperation(filePathList, FileAction.Edit);
        }
        

        public static List<string> AddFiles(List<string> filePathList)
        {
            return FileOperation(filePathList, FileAction.Add);
        }

        public static List<string> DeleteFiles(List<string> filePathList)
        {
            return FileOperation(filePathList, FileAction.Delete);
        }

        public static List<string> RevertFiles(List<string> filePathList)
        {
            return FileOperation(filePathList, FileAction.Reverted);
        }


        public static List<FileMetaData> FileStatus(string filePath)
        {
            IList<FileMetaData> filesMetaData = null;
            Perforce server = new Perforce();

            try
            {
                string fixedFilePath = GetFilePath(filePath);
                server.DiscoverClient(fixedFilePath);
                // connect to the server
                server.Connect();

                FileSpec[] fileToCheck = new FileSpec[] { new ClientPath(fixedFilePath) };
                GetFileMetaDataCmdOptions options = new GetFileMetaDataCmdOptions(GetFileMetadataCmdFlags.None, null, null, 0, null, null, null);
                filesMetaData = server.Repository.GetFileMetaData(options, fileToCheck);
            }
            finally
            {
                server.Disconnect();
            }

            return filesMetaData != null ? new List<FileMetaData>(filesMetaData) : null ;
        }

        public static List<FileMetaData> FileStatus(string[] filePathList)
        {
            IList<FileMetaData> filesMetaData = null;
            Perforce server = new Perforce();

            try
            {
                string fixedFilePath = GetFilePath(filePathList.FirstOrDefault());
                server.DiscoverClient(fixedFilePath);
                // connect to the server
                server.Connect();

                List<FileSpec> filesToCheck = new List<FileSpec>();
                foreach(string filePath in filePathList)
                {
                    fixedFilePath = GetFilePath(filePath);
                    filesToCheck.Add(new ClientPath(fixedFilePath));
                }

                GetFileMetaDataCmdOptions options = new GetFileMetaDataCmdOptions(GetFileMetadataCmdFlags.None, null, null, 0, null, null, null);
                filesMetaData = server.Repository.GetFileMetaData(options, filesToCheck.ToArray());
            }
            finally
            {
                server.Disconnect();
            }

            return filesMetaData != null ? new List<FileMetaData>(filesMetaData) : null;
        }

        public static string GetUserRoot()
        {
            var result = new Perforce();

            var con = result.Repository?.Connection;

            if (con == null)
            {
                return null;
            }

            con.UserName = result.Username;

            IList<Client> clients = null;

            try
            {
                con.Connect(null);
                var options = new ClientsCmdOptions(ClientsCmdFlags.None, result.Username, string.Empty, 64, string.Empty);
                clients = result.Repository.GetClients(options);
            }
            finally
            {
                con.Disconnect();
            }

            string rootPath = string.Empty;
            if(clients != null)
            {
                rootPath = clients[0].Root;
            }

            return rootPath;
        }

        public static IList<Client> GetClientList()
        {
            var result = new Perforce();

            var con = result.Repository?.Connection;

            if (con == null)
            {
                return null;
            }

            con.UserName = result.Username;

            IList<Client> clients = null;

            try
            {
                con.Connect(null);
                var options = new ClientsCmdOptions(ClientsCmdFlags.None, result.Username, string.Empty, 64, string.Empty);
                clients = result.Repository.GetClients(options);
            }
            finally
            {
                con.Disconnect();
            }

            return clients;
        }

        //public static Perforce ConnectToProject(Project project)
        //{
        //    return ConnectToPath(project.ProjectPath);
        //}

        public Perforce()
        {
            ConfigManager configManager = new ConfigManager();
            PerforceConfig perforceConfig = (PerforceConfig)configManager.GetCategory(SettingsCategories.PERFORCE);
            Enabled = perforceConfig.Enabled;
            if(Enabled == true)
            {
                PerforceHost = perforceConfig.Host;
                PerforceServer = perforceConfig.Server.Replace("<Host>", PerforceHost);

                ClientName = perforceConfig.UserName ?? Environment.UserName;
                ClientHostName = perforceConfig.ClientHostName ?? Environment.MachineName;
                WorkspaceName = perforceConfig.WorkspaceName ?? string.Format("{0}_{1}", ClientName, ClientHostName);

                //if (NetworkHost.CanConnect(perforceHost))
                //{
                //    this.Server = new Server(new ServerAddress(perforceServer));
                //    this.Repository = new Repository(this.Server);
                //    this.Username = Environment.UserName;
                //}

                this.Server = new Server(new ServerAddress(PerforceServer));
                this.Repository = new Repository(this.Server);
                this.Username = ClientName;
            }
        }

        public string Username { get; private set; }

        public bool IsConnected { get; private set; }

        private Client Client { get; set; }

        public Server Server { get; }

        public Repository Repository { get; }

        public Client Connect()
        {
            if (this.IsConnected)
            {
                throw new NotSupportedException("Already connected.");
            }

            var con = this.Repository.Connection;
            con.UserName = this.Username;
            con.Client = this.Client;
            this.IsConnected = con.Connect(null);
            return this.IsConnected ? con.Client : null;
        }

        public void Disconnect()
        {
            if (this.IsConnected)
            {
                this.Repository.Connection.Disconnect();
                this.IsConnected = false;
            }
        }

        public override string ToString()
        {
            if (this.Client == null)
            {
                return "Client not found.";
            }

            var c = this.Client;
            return $"{c.Name}, {c.OwnerName}, {c.Host}, {c.Root}, {c.Stream}.";
        }

        public static string NormalizePath(string path)
        {
            var result = path.Replace('\\', '/');  // normalize in perforce space (unix).
            if (result.EndsWith($"{'/'}"))
            {
                return result.TrimEnd('/');
            }

            return result;
        }

        public static string GetFilePath(string filePath)
        {
            if (filePath.Contains("V:"))
            {
                filePath = filePath.Replace("V:", GetUserRoot());
            }

            return filePath;
        }

        private void DiscoverClient(string path)
        {
            var con = this.Repository?.Connection;

            if (con == null)
            {
                return;
            }

            con.UserName = this.Username;

            try
            {
                if (!con.Connect(new Options()))
                {
                    return;
                }

                var options = new ClientsCmdOptions(ClientsCmdFlags.None, this.Username, string.Empty, 64, string.Empty);

                var clients = this.Repository.GetClients(options);

                foreach (var c in clients)
                {
                    if (c.Host == ClientHostName && c.Name == WorkspaceName)
                    {
                        if (PathHelper.PathIsChild(c.Root, path))
                        {
                            this.Client = c;
                            break;
                        }
                    }
                }
            }
            finally
            {
                con.Disconnect();
            }
        }

        public int GetCurrentChangeList(Client client)
        {
            var opt = new ChangesCmdOptions(ChangesCmdFlags.None, client.Name, 1, ChangeListStatus.Submitted, this.Username);
            var ret = this.Repository.GetChangelists(opt);
            return ret?.Count == 1 ? ret[0].Id : 0;
        }

        public Changelist CreateChangeList(string description)
        {
            var cl = this.Repository.CreateChangelist(new Changelist { Description = description }, null);
            cl.Description = description;
            return cl;
        }

        public void DeleteChangeList(Changelist changelist)
        {
            this.Repository.DeleteChangelist(changelist, new Options());
        }

        public void Checkout(FileSpec filespec, Changelist cl)
        {
            var options = new EditCmdOptions(EditFilesCmdFlags.None, cl?.Id ?? 0, null);
            var list = this.Repository.Connection.Client.EditFiles(options, filespec);

            if (list != null)
            {
                foreach (var fn in list)
                {
                    //Logger.Log($"Checked out: {fn}");
                }
            }
        }
    }
}