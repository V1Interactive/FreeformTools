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

    public class ExportLayer : INotifyPropertyChanged
    {
        public event EventHandler ToggleExportHandler;

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

        protected bool _export;
        public bool Export
        {
            get { return _export; }
            set
            {
                if (_export != value)
                {
                    ExportToggleEventArgs eventArgs = new ExportToggleEventArgs() { Value = value };
                    ToggleExportHandler?.Invoke(this, eventArgs);

                    _export = value;
                    RaisePropertyChanged("Export");
                }
            }
        }


        public ExportLayer(string nodeName)
        {
            NodeName = nodeName;
            Export = true;
        }

        public class ExportToggleEventArgs : EventArgs
        {
            public bool Value = false;
        }

        protected void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
