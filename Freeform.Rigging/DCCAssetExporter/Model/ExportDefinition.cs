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
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.Windows.Data;
    using Freeform.Core.UI;



    public class ExportDefinition : ExportObject
    {
        public event EventHandler SetFrameHandler;
        public event EventHandler GetCurrentFrameHandler;
        public event EventHandler GetSceneNameHandler;
        public event EventHandler GetFrameRangeHandler;


        public RelayCommand SetFrameCommand { get; set; }
        public RelayCommand SetStartFrameCommand { get; set; }
        public RelayCommand SetEndFrameCommand { get; set; }

        public List<ExportAsset> ExportAssetList;

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
                        Attribute = "definition_name",
                        Value = _name
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        int _startFrame;
        public int StartFrame
        {
            get { return _startFrame; }
            set
            {
                if (_startFrame != value)
                {
                    _startFrame = value;
                    RaisePropertyChanged("StartFrame");

                    AttributeIntEventArgs eventArgs = new AttributeIntEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "start_frame",
                        Type = "short",
                        Value = _startFrame
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        int _endFrame;
        public int EndFrame
        {
            get { return _endFrame; }
            set
            {
                if (_endFrame != value)
                {
                    _endFrame = value;
                    RaisePropertyChanged("EndFrame");

                    AttributeIntEventArgs eventArgs = new AttributeIntEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "end_frame",
                        Type = "short",
                        Value = _endFrame
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        bool _useFrameRange;
        public bool UseFrameRange
        {
            get { return _useFrameRange; }
            set
            {
                if (_useFrameRange != value)
                {
                    _useFrameRange = value;
                    RaisePropertyChanged("UseFrameRange");

                    AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "frame_range",
                        Type = "bool",
                        Value = _useFrameRange
                    };
                    OnAttributeChanged(eventArgs);

                    if(_useFrameRange == true)
                    {
                        FrameRangeEventArgs frameRangeEventArgs = new FrameRangeEventArgs()
                        {
                            StartValue = StartFrame,
                            EndValue = EndFrame
                        };
                        GetFrameRangeHandler?.Invoke(this, frameRangeEventArgs);

                        StartFrame = frameRangeEventArgs.StartValue;
                        EndFrame = frameRangeEventArgs.EndValue;
                    }
                }
            }
        }

        bool _useSceneName;
        public bool UseSceneName
        {
            get { return _useSceneName; }
            set
            {
                _useSceneName = value;
                RaisePropertyChanged("UseSceneName");

                AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs()
                {
                    Guid = Guid.ToString(),
                    NodeName = NodeName,
                    Attribute = "use_scene_name",
                    Type = "bool",
                    Value = _useSceneName
                };
                OnAttributeChanged(eventArgs);

                if (value)
                {
                    StringEventArgs stringEventArgs = new StringEventArgs();
                    GetSceneNameHandler?.Invoke(this, stringEventArgs);
                    if(stringEventArgs.Value != null && stringEventArgs.Value != string.Empty)
                        Name = stringEventArgs.Value;
                }
            }
        }

        bool _doExport;
        public bool DoExport
        {
            get { return _doExport; }
            set
            {
                if (_doExport != value)
                {
                    _doExport = value;
                    RaisePropertyChanged("DoExport");
                    TextOpacity = value ? 1f : 0.25f;

                    AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "do_export",
                        Type = "bool",
                        Value = _doExport
                    };
                    OnAttributeChanged(eventArgs);
                }
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
                    GridStyle = value ? "SelectedGrid" : "V1Grid";
                }
            }
        }


        public ExportDefinition(string guid, int index, string nodeName, string name, int startFrame, int endFrame, bool useFrameRange, bool useSceneName) : base(guid, nodeName)
        {
            Name = name;
            Index = index;
            StartFrame = startFrame;
            EndFrame = endFrame;
            UseFrameRange = useFrameRange;
            UseSceneName = useSceneName;

            DoExport = true;
            GridStyle = "V1Grid";

            SetFrameCommand = new RelayCommand(SetFrameCall);
            SetStartFrameCommand = new RelayCommand(SetStartFrameCall);
            SetEndFrameCommand = new RelayCommand(SetEndFrameCall);

            ExportAssetList = new List<ExportAsset>();
        }


        public void SetFrameCall(object sender)
        {
            SetFrameHandler?.Invoke(this, null);
        }

        public void SetStartFrameCall(object sender)
        {
            AttributeIntEventArgs eventArgs = new AttributeIntEventArgs();
            GetCurrentFrameHandler?.Invoke(this, eventArgs);

            StartFrame = eventArgs.Value;
        }

        public void SetEndFrameCall(object sender)
        {
            AttributeIntEventArgs eventArgs = new AttributeIntEventArgs();
            GetCurrentFrameHandler?.Invoke(this, eventArgs);

            EndFrame = eventArgs.Value;
        }

        public class FrameRangeEventArgs : EventArgs
        {
            public int StartValue = 0;
            public int EndValue = 0;
        }
    }
}
