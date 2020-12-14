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
    using System.IO;
    using System.Windows.Forms;
    using Freeform.Core.UI;

    public class ExportObject : INotifyPropertyChanged
    {
        public event EventHandler AttributeChangedHandler;

        protected Guid _guid;
        public Guid Guid
        {
            get { return _guid; }
            set
            {
                _guid = value;
                RaisePropertyChanged("Guid");
            }
        }

        DateTime _dateCreated;
        public DateTime DateCreated
        {
            get { return _dateCreated; }
            set
            {
                _dateCreated = value;
                RaisePropertyChanged("DateCreated");
            }
        }

        int _index;
        public int Index
        {
            get { return _index; }
            set
            {
                if (_index != value)
                {
                    _index = value;
                    RaisePropertyChanged("Index");

                    AttributeIntEventArgs eventArgs = new AttributeIntEventArgs()
                    {
                        Guid = Guid.ToString(),
                        NodeName = NodeName,
                        Attribute = "ui_index",
                        Type = "short",
                        Value = Index
                    };
                    OnAttributeChanged(eventArgs);
                }
            }
        }

        protected string _nodeName;
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

        protected ObservableCollection<ExportProperty> _exportProperties;
        public ObservableCollection<ExportProperty> ExportProperties
        {
            get { return _exportProperties; }
            set
            {
                if (_exportProperties != value)
                {
                    _exportProperties = value;
                    RaisePropertyChanged("ExportProperties");
                }
            }
        }


        public ExportObject(string guid, string nodeName)
        {
            Guid = new Guid(guid);
            NodeName = nodeName;

            ExportProperties = new ObservableCollection<ExportProperty>();
        }


        public void AddExportProperty(ExportProperty exportProperty)
        {
            if (GetType() == typeof(ExportDefinition))
            {
                exportProperty.SetPropertyType(exportProperty.PropertyType + " (Group)");
            }

            ExportProperties.Add(exportProperty);
        }


        protected void OnAttributeChanged(EventArgs args)
        {
            AttributeChangedHandler?.Invoke(this, args);
        }


        public class AttributeIntEventArgs : EventArgs
        {
            public string Guid = "";
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "short";
            public int Value = 0;
        }

        public class AttributeStringEventArgs : EventArgs
        {
            public string Guid = "";
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "string";
            public string Value = "";
        }

        public class AttributeBoolEventArgs : EventArgs
        {
            public string Guid = "";
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "bool";
            public bool Value = false;
        }

        public class ExportDefinitionEventArgs : EventArgs
        {
            public ExportAsset Asset = null;
            public ExportDefinition Definition = null;
        }

        public class StringEventArgs : EventArgs
        {
            public string Value = "";
        }


        protected void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
