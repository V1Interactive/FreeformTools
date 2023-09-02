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
    using System.Windows.Controls;
    using System.Windows.Data;
    using Freeform.Core.UI;


    public class ExportProperty : INotifyPropertyChanged
    {
        Guid _guid;
        public Guid Guid
        {
            get { return _guid; }
            set
            {
                _guid = value;
                RaisePropertyChanged("Guid");
                RaisePropertyChanged("GuidString");
            }
        }
        public string GuidString { get { return Guid.ToString(); } }

        private string _nodeName;
        public string NodeName
        {
            get { return _nodeName; }
            set
            {
                if (_nodeName != value)
                {
                    _nodeName = value;
                    RaisePropertyChanged("NodeName");
                }
            }
        }

        private string _icon;
        public string Icon
        {
            get { return _icon; }
            set
            {
                if (_icon != value)
                {
                    _icon = value;
                    RaisePropertyChanged("Icon");
                }
            }
        }

        protected string _propertyType;
        public string PropertyType
        {
            get { return _propertyType; }
        }

        public ExportProperty(string guid, string nodeName)
        {
            // This will need to be different per ExportProperty type
            _propertyType = "Base Export Property";

            Guid = new Guid(guid);
            NodeName = nodeName;
        }

        public void SetPropertyType(string value)
        {
            // Separated as method to make setting this an explicit choice and not just a variable assignment.
            _propertyType = value;
        }


        public class AttributeStringEventArgs : EventArgs
        {
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "string";
            public string Value = "";
        }

        public class AttributeIntEventArgs : EventArgs
        {
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "short";
            public int Value = 0;
        }

        public class AttributeFloatEventArgs : EventArgs
        {
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "short";
            public float Value = 0;
        }

        public class AttributeBoolEventArgs : EventArgs
        {
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "bool";
            public bool Value = false;
        }


        protected void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }


    public class RemoveRootAnimProperty : ExportProperty
    {
        public RemoveRootAnimProperty(string guid, string nodeName) : base(guid, nodeName)
        {
            _propertyType = "Remove Root Animation";
            Icon = "../../Resources/export_remove_root_anim.ico";
        }
    }


    public class ZeroCharacterProperty : ExportProperty
    {
        public ZeroCharacterProperty(string guid, string nodeName) : base(guid, nodeName)
        {
            _propertyType = "Zero Translate";
            Icon = "../../Resources/zero_rig.ico";
        }
    }

    public class ZeroCharacterRotateProperty : ExportProperty
    {
        public ZeroCharacterRotateProperty(string guid, string nodeName) : base(guid, nodeName)
        {
            _propertyType = "Zero Rotate";
            Icon = "../../Resources/zero_rig.ico";
        }
    }

    public class ZeroAnimCurvesProperty : ExportProperty
    {
        public ZeroAnimCurvesProperty(string guid, string nodeName) : base(guid, nodeName)
        {
            _propertyType = "Zero Animation Curves";
            Icon = "../../Resources/zero_rig.ico";
        }
    }

    public class ZeroMocapProperty : ExportProperty
    {
        public event EventHandler AttributeChangedHandler;

        private float _rotateValue;
        public float RotateValue
        {
            get { return _rotateValue; }
            set
            {
                if (_rotateValue != value)
                {
                    _rotateValue = value;
                    RaisePropertyChanged("RotateValue");

                    AttributeFloatEventArgs eventArgs = new AttributeFloatEventArgs()
                    {
                        NodeName = NodeName,
                        Attribute = "rotate_value",
                        Value = RotateValue
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }

        private float _alignKeyframe;
        public float AlignKeyframe
        {
            get { return _alignKeyframe; }
            set
            {
                if (_alignKeyframe != value)
                {
                    _alignKeyframe = value;
                    RaisePropertyChanged("AlignKeyframe");

                    AttributeFloatEventArgs eventArgs = new AttributeFloatEventArgs()
                    {
                        NodeName = NodeName,
                        Attribute = "align_keyframe",
                        Value = AlignKeyframe
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }

        public ZeroMocapProperty(string guid, string nodeName, float rotateValue, int alignKeyframe) : base(guid, nodeName)
        {
            _propertyType = "Zero Mocap";
            Icon = "../../Resources/zero_rig.ico";
            RotateValue = rotateValue;
            AlignKeyframe = alignKeyframe;
        }
    }


    public class AnimCurveExporterProperty : ExportProperty
    {
        public event EventHandler AttributeChangedHandler;
        public event EventHandler SetFrameHandler;
        public event EventHandler GetCurrentFrameHandler;
        public event EventHandler RefreshNamesHandler;
        public event EventHandler PickControlHandler;

        public RelayCommand SetFrameCommand { get; set; }
        public RelayCommand SetStartFrameCommand { get; set; }
        public RelayCommand SetEndFrameCommand { get; set; }
        public RelayCommand RefreshNamesCommand { get; set; }
        public RelayCommand PickControlCommand { get; set; }

        private bool _useSpeedCurve;
        public bool UseSpeedCurve
        {
            get { return _useSpeedCurve; }
            set
            {
                if (_useSpeedCurve != value)
                {
                    _useSpeedCurve = value;
                    RaisePropertyChanged("UseSpeedCurve");
                    RaisePropertyChanged("UseDistanceCurve");

                    AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs()
                    {
                        NodeName = NodeName,
                        Attribute = "use_speed_curve",
                        Value = UseSpeedCurve
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }
        public bool UseDistanceCurve
        {
            get { return !_useSpeedCurve; }
        }

        private bool _fromZero;
        public bool FromZero
        {
            get { return _fromZero; }
            set
            {
                if (_fromZero != value)
                {
                    _fromZero = value;
                    RaisePropertyChanged("FromZero");
                    RaisePropertyChanged("ToZero");

                    AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs()
                    {
                        NodeName = NodeName,
                        Attribute = "from_zero",
                        Value = FromZero
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }
        public bool ToZero
        {
            get { return !_fromZero; }
        }

        private string _targetName;
        public string TargetName
        {
            get { return _targetName; }
            set
            {
                if (_targetName != value)
                {
                    _targetName = value;
                    RaisePropertyChanged("TargetName");

                    AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                    {
                        NodeName = NodeName,
                        Attribute = "target_name",
                        Value = TargetName
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }

        private string _controlName;
        public string ControlName
        {
            get { return _controlName; }
            set
            {
                if (_controlName != value)
                {
                    _controlName = value;
                    RaisePropertyChanged("ControlName");

                    //AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                    //{
                    //    NodeName = NodeName,
                    //    Attribute = "control_name",
                    //    Value = ControlName
                    //};
                    //AttributeChangedHandler?.Invoke(this, eventArgs);
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
                        NodeName = NodeName,
                        Attribute = "start_frame",
                        Value = StartFrame
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
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
                        NodeName = NodeName,
                        Attribute = "end_frame",
                        Value = EndFrame
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
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
                        NodeName = NodeName,
                        Attribute = "frame_range",
                        Value = UseFrameRange
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }

        public Guid CurveTypeID { get; private set; }
        public Guid FromZeroID { get; private set; }


        public AnimCurveExporterProperty(string guid, string nodeName, string controlName, string targetName, bool useSpeedCurve, bool fromZero, int startFrame, int endFrame, bool useFrameRange) : base(guid, nodeName)
        {
            // This will need to be different per ExportProperty type
            _propertyType = "Animation Curves";
            Icon = "../../Resources/export_anim_curve.ico";

            ControlName = controlName;
            TargetName = targetName;
            UseSpeedCurve = useSpeedCurve;
            FromZero = fromZero;
            StartFrame = startFrame;
            EndFrame = endFrame;
            UseFrameRange = useFrameRange;

            SetFrameCommand = new RelayCommand(SetFrameCall);
            SetStartFrameCommand = new RelayCommand(SetStartFrameCall);
            SetEndFrameCommand = new RelayCommand(SetEndFrameCall);
            RefreshNamesCommand = new RelayCommand(RefreshNamesCall);
            PickControlCommand = new RelayCommand(PickControlCall);

            CurveTypeID = Guid.NewGuid();
            FromZeroID = Guid.NewGuid();
        }

        public void SetFrameCall(object sender)
        {
            SetFrameHandler?.Invoke(this, null);
        }

        public void RefreshNamesCall(object sender)
        {
            RefreshNamesEventArgs eventArgs = new RefreshNamesEventArgs();
            RefreshNamesHandler?.Invoke(this, eventArgs);

            TargetName = eventArgs.Target;
        }

        public void PickControlCall(object sender)
        {
            AttributeStringEventArgs eventArgs = new AttributeStringEventArgs();
            PickControlHandler?.Invoke(this, eventArgs);
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

        public class RefreshNamesEventArgs : EventArgs
        {
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "string";
            public string Target = "";
            public string Control = "";
        }
    }


    public class RotationExporterProperty : ExportProperty
    {
        public event EventHandler AttributeChangedHandler;
        public event EventHandler PickControlHandler;

        public RelayCommand PickControlCommand { get; set; }


        private string _attributeName;
        public string AttributeName
        {
            get { return _attributeName; }
            set
            {
                if (_attributeName != value)
                {
                    _attributeName = value;
                    RaisePropertyChanged("AttributeName");

                    AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                    {
                        NodeName = NodeName,
                        Attribute = "attribute_name",
                        Value = AttributeName
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }

        private string _targetName;
        public string TargetName
        {
            get { return _targetName; }
            set
            {
                if (_targetName != value)
                {
                    _targetName = value;
                    RaisePropertyChanged("TargetName");

                    AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                    {
                        NodeName = NodeName,
                        Attribute = "target_name",
                        Value = TargetName
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }


        private float _rotateValue;
        public float RotateValue
        {
            get { return _rotateValue; }
            set
            {
                if (_rotateValue != value)
                {
                    _rotateValue = value;
                    RaisePropertyChanged("RotateValue");

                    AttributeFloatEventArgs eventArgs = new AttributeFloatEventArgs()
                    {
                        NodeName = NodeName,
                        Attribute = "rotate_value",
                        Value = RotateValue
                    };
                    AttributeChangedHandler?.Invoke(this, eventArgs);
                }
            }
        }

        private bool _xAxis;
        public bool XAxis
        {
            get { return _xAxis; }
            set
            {
                if (_xAxis != value)
                {
                    _xAxis = value;
                    RaisePropertyChanged("XAxis");

                    if (value)
                    {
                        AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                        {
                            NodeName = NodeName,
                            Attribute = "axis",
                            Value = "rx"
                        };
                        AttributeChangedHandler?.Invoke(this, eventArgs);
                    }

                }
            }
        }

        private bool _yAxis;
        public bool YAxis
        {
            get { return _yAxis; }
            set
            {
                if (_yAxis != value)
                {
                    _yAxis = value;
                    RaisePropertyChanged("YAxis");

                    if (value)
                    {
                        AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                        {
                            NodeName = NodeName,
                            Attribute = "axis",
                            Value = "ry"
                        };
                        AttributeChangedHandler?.Invoke(this, eventArgs);
                    }

                }
            }
        }

        private bool _zAxis;
        public bool ZAxis
        {
            get { return _zAxis; }
            set
            {
                if (_zAxis != value)
                {
                    _zAxis = value;
                    RaisePropertyChanged("ZAxis");

                    if (value)
                    {
                        AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                        {
                            NodeName = NodeName,
                            Attribute = "axis",
                            Value = "rz"
                        };
                        AttributeChangedHandler?.Invoke(this, eventArgs);
                    }

                }
            }
        }


        public Guid AxisID { get; private set; }


        public RotationExporterProperty(string guid, string nodeName, string attributeName, string targetName, string axis, float rotateValue) : base(guid, nodeName)
        {
            _propertyType = "Rotation Curve";
            Icon = "pack://application:,,,/HelixResources;component/Resources/refresh.ico";

            AttributeName = attributeName;
            TargetName = targetName;
            SetAxis(axis);
            RotateValue = rotateValue;

            PickControlCommand = new RelayCommand(PickControlCall);

            AxisID = Guid.NewGuid();
        }

        string GetAxis()
        {
            if (XAxis) { return "rx"; }
            if (YAxis) { return "ry"; }
            if (ZAxis) { return "rz"; }

            return "ry";
        }

        void SetAxis(string value)
        {
            if (value == "rx")
            {
                XAxis = true;
            }
            else if (value == "ry")
            {
                YAxis = true;
            }
            else
            {
                ZAxis = true;
            }
        }

        public void PickControlCall(object sender)
        {
            AttributeStringEventArgs eventArgs = new AttributeStringEventArgs();
            PickControlHandler?.Invoke(this, eventArgs);
        }
    }
}
