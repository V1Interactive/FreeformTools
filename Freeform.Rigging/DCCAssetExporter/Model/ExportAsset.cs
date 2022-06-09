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

namespace Freeform.Rigging.DCCAssetExporter
{
    using System;
    using System.Collections.Generic;
    using System.ComponentModel;
    using System.IO;
    using System.Windows.Forms;

    using Freeform.Core.ConfigSettings;
    using Freeform.Core.UI;


    public class ExportAsset : ExportObject
    {
        public event EventHandler ExportEventHandler;
        public event EventHandler ToggleAssetExportHandler;
        public event EventHandler SwapGeometryHandler;


        public RelayCommand SetExportPathCommand { get; set; }


        string _gridStyle;
        public string GridStyle
        {
            get { return _gridStyle; }
            set
            {
                _gridStyle = value;
                RaisePropertyChanged("GridStyle");
            }
        }

        float _textOpacity;
        public float TextOpacity
        {
            get { return _textOpacity; }
            set
            {
                _textOpacity = value;
                RaisePropertyChanged("TextOpacity");
            }
        }

        string _name;
        public string Name
        {
            get { return _name; }
            set
            {
                if (_name != value)
                {
                    _name = value;
                    RaisePropertyChanged("Name");

                    AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "asset_name",
                        Value = Name
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        string _type;
        public string Type
        {
            get { return _type; }
            set
            {
                if (_type != value)
                {
                    _type = value;
                    RaisePropertyChanged("Type");
                }
            }
        }

        string _exportPath;
        public string ExportPath
        {
            get { return _exportPath; }
            set
            {
                if (_exportPath != value)
                {
                    _exportPath = value;
                    RaisePropertyChanged("ExportPath");

                    AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "export_path",
                        Value = ExportPath
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        string _fileType;
        public string FileType
        {
            get { return _fileType; }
            set
            {
                if (_fileType != value)
                {
                    _fileType = value;
                    RaisePropertyChanged("FileType");

                    AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "file_type",
                        Value = FileType
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        bool _zeroExport;
        public bool ZeroExport
        {
            get { return _zeroExport; }
            set
            {
                if (_zeroExport != value)
                {
                    _zeroExport = value;
                    RaisePropertyChanged("ZeroExport");

                    AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "zero_export",
                        Value = ZeroExport
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        bool _useExportPath;
        public bool UseExportPath
        {
            get { return _useExportPath; }
            set
            {
                if (_useExportPath != value)
                {
                    _useExportPath = value;
                    RaisePropertyChanged("UseExportPath");

                    AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "use_export_path",
                        Value = UseExportPath
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        bool _assetExport;
        public bool AssetExport
        {
            get { return _assetExport; }
            set
            {
                AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs() { Value = value };
                ToggleAssetExportHandler?.Invoke(this, eventArgs);

                _assetExport = value;
                RaisePropertyChanged("AssetExport");

                GridStyle = value ? "SelectedGrid" : "V1Grid";
                TextOpacity = value ? 1f : 0.25f;
            }
        }

        bool _isSelected;
        public bool IsSelected
        {
            get { return _isSelected; }
            set
            {
                if (_isSelected != value)
                {
                    _isSelected = value;
                    RaisePropertyChanged("IsSelected");
                }
            }
        }


        public ExportAsset(string guid, int index, string nodeName, string name, string type, string exportPath, bool zeroExport, 
                            bool useExportPath) : base(guid, nodeName)
        {
            Name = name;
            Index = index;
            Type = type;
            ExportPath = exportPath;
            ZeroExport = zeroExport;
            UseExportPath = useExportPath;
            AssetExport = false;
            FileType = "";

            SetExportPathCommand = new RelayCommand(SetExportPathCall);
        }

        public void SwapGeometry()
        {
            SwapGeometryHandler?.Invoke(this, null);
        }

        public void Export(ExportDefinition definition)
        {
            ExportDefinitionEventArgs eventArgs = new ExportDefinitionEventArgs()
            {
                Asset = this,
                Definition = definition
            };
            ExportEventHandler?.Invoke(this, eventArgs);
        }

        public string GetExportPath(string definitionName, string scenePath, bool is_animation)
        {
            ExporterConfig exporterConfig = (ExporterConfig)new ConfigManager().GetCategory(SettingsCategories.EXPORTER);
            ProjectConfig projectConfig = (ProjectConfig)new ConfigManager().GetCategory(SettingsCategories.PROJECT);
            string exportPattern = exporterConfig.ExportPattern;
            char sep_char = Path.DirectorySeparatorChar;

            string returnDirectory;
            if (UseExportPath && ExportPath != string.Empty)
            {
                returnDirectory = ExportPath;
                if (returnDirectory.Contains(".."))
                {
                    returnDirectory = returnDirectory.Replace("..", projectConfig.GetContentRoot());
                }
            }
            else
            {
                // Start the export path as the scene file path
                returnDirectory = Path.GetDirectoryName(scenePath);
                string sceneDirectory = Path.GetDirectoryName(scenePath);

                int nextIndex = 0;
                List<string> splitPattern = new List<string>(exportPattern.Split(sep_char));
                bool skipNext = false;
                foreach (string pattern in splitPattern)
                {
                    nextIndex += 1;
                    if (skipNext == true)
                    {
                        skipNext = false;
                        continue;
                    }

                    // Start the export path with the Content Root path
                    if (pattern == "<>")
                    {
                        returnDirectory = "";
                    }
                    // Start the export path with the Project Root path
                    else if (pattern == "<PROJECT_ROOT>")
                    {
                        returnDirectory = projectConfig.GetProjectRoot();
                    }
                    // Start the export path with the Project Root path
                    else if (pattern == "<CONTENT_ROOT>")
                    {
                        returnDirectory = projectConfig.GetContentRoot();
                    }
                    // Start the export path as an empty string
                    else if (pattern == "<ENGINE_CONTENT_ROOT>")
                    {
                        returnDirectory = projectConfig.GetEngineContentRoot();
                    }
                    // Remove 1 directory from the path
                    else if (pattern == "..")
                    {
                        int splitIndex = returnDirectory.LastIndexOf(sep_char);
                        returnDirectory = returnDirectory.Substring(0, splitIndex);
                    }
                    // Search back until we find the directory name that matches the next pattern, removing all directories above
                    else if (pattern == "...")
                    {
                        string nextPattern = nextIndex < splitPattern.Count ? splitPattern[nextIndex] : string.Empty;
                        if (nextPattern != string.Empty && returnDirectory.Contains(nextPattern))
                        {
                            List<string> splitReturnDirectory = new List<string>(returnDirectory.Split(sep_char));

                            int patternIndex = splitReturnDirectory.IndexOf(nextPattern);
                            returnDirectory = Path.Combine(splitReturnDirectory.GetRange(0, patternIndex).ToArray());
                            skipNext = true;
                        }
                    }
                    // Search the sceneDirectory for the next pattern and append all directories including the pattern to the path
                    else if (pattern == ">...>" || pattern == "<...<")
                    {
                        string nextPattern = nextIndex < splitPattern.Count ? splitPattern[nextIndex] : string.Empty;
                        if (nextPattern != string.Empty && sceneDirectory.Contains(nextPattern))
                        {
                            List<string> splitSceneDirectory = new List<string>(sceneDirectory.Split(sep_char));

                            int patternIndex = splitSceneDirectory.IndexOf(nextPattern);
                            string matchingDirectory = "";
                            if (pattern == ">...>")
                            {
                                matchingDirectory = Path.Combine(splitSceneDirectory.GetRange(patternIndex, splitSceneDirectory.Count - patternIndex).ToArray());
                            }
                            else if (pattern == "<...<")
                            {
                                matchingDirectory = Path.Combine(splitSceneDirectory.GetRange(0, patternIndex).ToArray());
                            }

                            returnDirectory = Path.Combine(returnDirectory, matchingDirectory);
                            skipNext = true;
                        }
                    }
                    // Add the pattern to the path as a new directory
                    else
                    {
                        returnDirectory = Path.Combine(returnDirectory, pattern);
                    }
                }
            }
            // Add the ExportDirectory to the end
            returnDirectory = Path.Combine(returnDirectory, exporterConfig.ExportDirectory);

            string fileNamePattern = exporterConfig.FileNamePattern;
            string animationExportName = fileNamePattern.Replace("<Asset>", Name).Replace("<Definition>", definitionName);
            string exportName = is_animation ? (animationExportName + ".fbx") : (Name + ".fbx");

            return Path.Combine(returnDirectory, exportName).ToString().Replace("/", sep_char.ToString());
        }

        public void SetExportPathCall(object sender)
        {
            using (var fbd = new FolderBrowserDialog())
            {
                fbd.Description = "Pick Export Path";
                DialogResult result = fbd.ShowDialog();

                if (result == DialogResult.OK && !string.IsNullOrWhiteSpace(fbd.SelectedPath))
                {
                    string fullPath = fbd.SelectedPath;

                    string contentRoot = Environment.GetEnvironmentVariable("CONTENT_ROOT");
                    if(contentRoot != null)
                    {
                        fullPath = fullPath.Replace(contentRoot, "..");
                    }

                    ExportPath = fullPath;
                }
            }
        }
    }
}
