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
            string returnDirectory = "";

            if (UseExportPath && ExportPath != string.Empty)
            {
                returnDirectory = ExportPath;
                if (returnDirectory.Contains(".."))
                {
                    returnDirectory = returnDirectory.Replace("..", Environment.GetEnvironmentVariable("CONTENT_ROOT"));
                }
            }
            else
            {
                string exportPattern = exporterConfig.ExportPattern;
                string sceneDirectory = Path.GetDirectoryName(scenePath);
                returnDirectory = Path.GetDirectoryName(scenePath);

                int nextIndex = 0;
                List<string> splitPattern = new List<string>(exportPattern.Split(Path.DirectorySeparatorChar));
                foreach (string pattern in splitPattern)
                {
                    nextIndex += 1;
                    if(pattern == "..") // Remove 1 directory from the path
                    {
                        int splitIndex = returnDirectory.LastIndexOf(Path.DirectorySeparatorChar);
                        returnDirectory = returnDirectory.Substring(0, splitIndex);
                    }
                    else if(pattern == "...") // Search back until we find the directory name that matches the next pattern
                    {
                        string nextPattern = nextIndex < splitPattern.Count ? splitPattern[nextIndex] : string.Empty;
                        if(nextPattern != string.Empty && returnDirectory.Contains(nextPattern))
                        {
                            List<string> splitReturnDirectory = new List<string>(returnDirectory.Split(Path.DirectorySeparatorChar));

                            string driveLetter = string.Empty;
                            if (splitReturnDirectory[0].Contains(":"))
                            {
                                driveLetter = splitReturnDirectory[0];
                                splitReturnDirectory.RemoveAt(0);
                            }

                            int patternIndex = splitReturnDirectory.IndexOf(nextPattern);
                            returnDirectory = Path.Combine(splitReturnDirectory.GetRange(0, patternIndex).ToArray());

                            if (driveLetter != string.Empty) { returnDirectory = driveLetter + Path.DirectorySeparatorChar + returnDirectory; }
                        }
                    }
                    else // Add the pattern to the path as a new directory
                    {
                        returnDirectory = Path.Combine(returnDirectory, pattern);
                    }
                }

                if(exporterConfig.MatchDirectory == true)
                {
                    string removedDirectory = sceneDirectory.Remove(0, returnDirectory.Length + 1); // + 1 accounts for 0 based index and 1 based length count
                    removedDirectory = removedDirectory.TrimStart(Path.DirectorySeparatorChar);
                    List<string> removedList = new List<string>(removedDirectory.Split(Path.DirectorySeparatorChar));
                    string[] addList = removedList.GetRange(1, removedList.Count - 1).ToArray();
                    foreach(string addDirectory in addList)
                    {
                        returnDirectory = Path.Combine(returnDirectory, addDirectory);
                    }
                }
            }

            string fileNamePattern = exporterConfig.FileNamePattern;
            string animationExportName = fileNamePattern.Replace("<Asset>", Name).Replace("<Definition>", definitionName);
            string exportName = is_animation ? (animationExportName + ".fbx") : (Name + ".fbx");

            return Path.Combine(returnDirectory, exportName).ToString().Replace("/", Path.DirectorySeparatorChar.ToString());
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
