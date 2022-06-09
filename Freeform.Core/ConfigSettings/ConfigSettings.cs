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

namespace Freeform.Core.ConfigSettings
{
    using Newtonsoft.Json;
    using System;
    using System.Collections.Generic;
    using System.IO;
    using System.Linq;
    using System.Text;
    using System.Threading.Tasks;


    public enum SettingsCategories
    {
        DEVELOP,
        PROJECT,
        EXPORTER,
        PERFORCE
    }


    public class ConfigManager
    {
        readonly string ConfigPath = Path.Combine(Environment.GetEnvironmentVariable("V1TOOLSROOT"), "tools_config.json");
        readonly string UserSettingsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "V1", "user_settings.json");

        readonly ConfigSettings InitSettings;
        public readonly ConfigSettings UserSettings;

        public ConfigManager()
        {
            InitSettings = JsonConvert.DeserializeObject<ConfigSettings>(File.ReadAllText(ConfigPath));
            if (File.Exists(UserSettingsPath))
            {
                UserSettings = JsonConvert.DeserializeObject<ConfigSettings>(File.ReadAllText(UserSettingsPath));
                InitSettings.Copy(UserSettings);
            }
        }

        public ConfigGroup GetCategory(string categoryName)
        {
            if (Enum.TryParse(categoryName.ToUpper(), out SettingsCategories choice))
            {
                return GetCategory(choice);
            }
            return null;
        }

        public ConfigGroup GetCategory(SettingsCategories category)
        {
            ConfigGroup returnGroup = null;

            if(category == SettingsCategories.DEVELOP) { returnGroup = InitSettings.Developer; }
            else if (category == SettingsCategories.PROJECT) { returnGroup = InitSettings.Project; }
            else if (category == SettingsCategories.EXPORTER) { returnGroup = InitSettings.Exporter; }
            else if (category == SettingsCategories.PERFORCE) { returnGroup = InitSettings.Perforce; }

            return returnGroup;
        }

        public string GetContentRoot()
        {
            return InitSettings.Project.GetContentRoot();
        }

        public string GetProjectRoot()
        {
            return InitSettings.Project.GetProjectRoot();
        }

        public string GetEngineContentRoot()
        {
            return InitSettings.Project.GetEngineContentRoot();
        }
    }


    public class ConfigSettings
    {
        public DeveloperConfig Developer { get; set; }
        public ProjectConfig Project { get; set; }
        public ExporterConfig Exporter { get; set; }
        public PerforceConfig Perforce { get; set; }

        public void Copy(ConfigSettings copySettings)
        {
            Developer.Copy(copySettings.Developer);
            Project.Copy(copySettings.Project);
            Exporter.Copy(copySettings.Exporter);
            Perforce.Copy(copySettings.Perforce);
        }
    }

    public class ConfigGroup
    {
        public void Copy(ConfigGroup copyGroup)
        {
            if(copyGroup != null) { OnCopy(copyGroup); }
        }

        virtual public void OnCopy(ConfigGroup copyGroup) { }
    }


    public class DeveloperConfig : ConfigGroup
    {
        public bool DeveloperMode { get; set; }

        string _projectDrive;
        public string ProjectDrive
        {
            get { return _projectDrive != null ? _projectDrive.Replace('/', Path.DirectorySeparatorChar) : _projectDrive; }
            set { _projectDrive = value; }
        }

        string _devToolsPath;
        public string DevToolsPath
        {
            get { return _devToolsPath != null ? _devToolsPath.Replace('/', Path.DirectorySeparatorChar) : _devToolsPath; }
            set { _devToolsPath = value; }
        }

        override public void OnCopy(ConfigGroup copyGroup)
        {
            DeveloperConfig copy = (DeveloperConfig)copyGroup;

            DeveloperMode = copy.DeveloperMode ? copy.DeveloperMode : DeveloperMode;
            ProjectDrive = copy.ProjectDrive ?? ProjectDrive;
            DevToolsPath = copy.DevToolsPath ?? DevToolsPath;
        }
    }

    public class ProjectConfig : ConfigGroup
    {
        public bool UseProject { get; set; }

        string _projectDrive;
        public string ProjectDrive
        {
            get { return _projectDrive != null ?_projectDrive.Replace('/', Path.DirectorySeparatorChar) : _projectDrive; }
            set { _projectDrive = value; }
        }

        string _projectRootPath;
        public string ProjectRootPath
        {
            get { return _projectRootPath != null ? _projectRootPath.Replace('/', Path.DirectorySeparatorChar) : _projectRootPath; }
            set { _projectRootPath = value; }
        }

        string _contentRootPath;
        public string ContentRootPath
        {
            get { return _contentRootPath != null ? _contentRootPath.Replace('/', Path.DirectorySeparatorChar) : _contentRootPath; }
            set { _contentRootPath = value; }
        }

        string _engineContentPath;
        public string EngineContentPath
        {
            get { return _engineContentPath != null ? _engineContentPath.Replace('/', Path.DirectorySeparatorChar) : _engineContentPath; }
            set { _engineContentPath = value; }
        }

        string _characterFolder;
        public string CharacterFolder
        {
            get { return _characterFolder != null ? _characterFolder.Replace('/', Path.DirectorySeparatorChar) : _characterFolder; }
            set { _characterFolder = value; }
        }

        public string[] RigSearchPathList { get; set; }

        public string[] PropSearchPathList { get; set; }
        public string[] PropFolderList { get; set; }

        override public void OnCopy(ConfigGroup copyGroup)
        {
            ProjectConfig copy = (ProjectConfig)copyGroup;

            UseProject = copy.UseProject ? copy.UseProject : UseProject;
            ProjectDrive = copy.ProjectDrive ?? ProjectDrive;
            ProjectRootPath = copy.ProjectRootPath ?? ProjectRootPath;
            ContentRootPath = copy.ContentRootPath ?? ContentRootPath;
            EngineContentPath = copy.EngineContentPath ?? EngineContentPath;
            CharacterFolder = copy.CharacterFolder ?? CharacterFolder;
            RigSearchPathList = copy.RigSearchPathList ?? RigSearchPathList;
        }

        public string GetContentRoot()
        {
            return Path.Combine(ProjectDrive, ProjectRootPath, ContentRootPath);
        }

        public string GetProjectRoot()
        {
            return Path.Combine(ProjectDrive, ProjectRootPath);
        }

        public string GetEngineContentRoot()
        {
            return Path.Combine(ProjectDrive, ProjectRootPath, EngineContentPath);
        }
    }

    public class ExporterConfig : ConfigGroup
    {
        public string FileNamePattern { get; set; }
        public string ExportDirectory { get;set; }

        string _exportPattern;
        public string ExportPattern {
            get { return _exportPattern != null ? _exportPattern.Replace('/', Path.DirectorySeparatorChar) : _exportPattern; }
            set { _exportPattern = value; }
        }

        override public void OnCopy(ConfigGroup copyGroup)
        {
            ExporterConfig copy = (ExporterConfig)copyGroup;

            FileNamePattern = copy.FileNamePattern ?? FileNamePattern;
            ExportPattern = copy.ExportPattern ?? ExportPattern;
            ExportDirectory = copy.ExportDirectory ?? ExportDirectory;
        }
    }

    public class PerforceConfig : ConfigGroup
    {
        public bool Enabled { get; set; }
        public string Host { get; set; }
        public string Server { get; set; }

        public string UserName { get; set; }
        public string ClientHostName { get; set; }
        public string WorkspaceName { get; set; }

        override public void OnCopy(ConfigGroup copyGroup)
        {
            PerforceConfig copy = (PerforceConfig)copyGroup;

            Enabled = copy.Enabled ? copy.Enabled : Enabled;
            Host = copy.Host ?? Host;
            Server = copy.Server ?? Server;
            UserName = copy.UserName ?? UserName;
            ClientHostName = copy.ClientHostName ?? ClientHostName;
            WorkspaceName = copy.WorkspaceName ?? WorkspaceName;
        }
    }
}